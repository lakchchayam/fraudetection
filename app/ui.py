from typing import Any, Dict

import httpx
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates


templates = Jinja2Templates(directory="templates")

router = APIRouter(tags=["ui"])


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    """
    Internal analyst dashboard.

    Fetches data via the public API endpoints (no direct DB access).
    """
    async with httpx.AsyncClient(app=request.app, base_url="http://test") as client:
        tx_resp = await client.get(
            "/api/v1/transactions", params={"limit": 10, "offset": 0}
        )
        tx_data: Dict[str, Any] = tx_resp.json()

        alerts_resp = await client.get(
            "/api/v1/alerts", params={"limit": 10, "offset": 0, "status": "OPEN"}
        )
        alerts_data: list[Dict[str, Any]] = alerts_resp.json()

        cases_resp = await client.get(
            "/api/v1/cases", params={"limit": 10, "offset": 0, "status": "OPEN"}
        )
        cases_data: list[Dict[str, Any]] = cases_resp.json()

        # Pro Feature: Analytics
        analytics_resp = await client.get("/api/v1/analytics/rules")
        rule_stats = analytics_resp.json()

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "transactions": tx_data.get("items", []),
            "total_transactions": tx_data.get("total", 0),
            "alerts": alerts_data,
            "cases": cases_data,
            "rule_stats": rule_stats,
            "show_3d_card": True,
        },
    )


@router.post("/dashboard/seed-demo")
async def dashboard_seed_demo(request: Request) -> RedirectResponse:
    """
    One-click demo data loader from the UI.
    """
    async with httpx.AsyncClient(app=request.app, base_url="http://test") as client:
        await client.post("/api/v1/demo/seed")
    return RedirectResponse(url="/dashboard", status_code=303)


@router.post("/dashboard/ingest-tx")
async def dashboard_ingest_transaction(
    request: Request,
    external_id: str = Form(...),
    account_id: str = Form(...),
    amount: float = Form(...),
    currency: str = Form("INR"),
    merchant_id: str = Form("M-UI"),
) -> RedirectResponse:
    """
    Simple form-based transaction ingestion from the dashboard.
    """
    async with httpx.AsyncClient(app=request.app, base_url="http://test") as client:
        await client.post(
            "/api/v1/transactions",
            json={
                "external_id": external_id,
                "account_id": account_id,
                "amount": amount,
                "currency": currency,
                "merchant_id": merchant_id,
            },
        )
    return RedirectResponse(url="/dashboard", status_code=303)


@router.get("/dashboard/transaction/{transaction_id}", response_class=HTMLResponse)
async def transaction_detail(request: Request, transaction_id: int) -> HTMLResponse:
    """
    Detailed view for a single transaction.
    """
    async with httpx.AsyncClient(app=request.app, base_url="http://test") as client:
        resp = await client.get(f"/api/v1/transactions/{transaction_id}")
        if resp.status_code == 404:
            return HTMLResponse(content="Transaction not found", status_code=404)
        
        tx_data = resp.json()

    return templates.TemplateResponse(
        "transaction_detail.html",
        {"request": request, "tx": tx_data}
    )


