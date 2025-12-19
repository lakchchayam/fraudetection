from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api_v1 import audit, cases, transactions, alerts, demo
from app import ui


def create_app() -> FastAPI:
    """
    Application factory.

    API is versioned under /api/v1.
    """
    app = FastAPI(
        title="Risk Management & Fraud Detection",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # Static files (CSS for dashboard and 3D card)
    app.mount("/static", StaticFiles(directory="static"), name="static")

    # API v1 routers
    app.include_router(transactions.router, prefix="/api/v1")
    app.include_router(cases.router, prefix="/api/v1")
    app.include_router(alerts.router, prefix="/api/v1")
    app.include_router(audit.router, prefix="/api/v1")
    app.include_router(demo.router, prefix="/api/v1")
    # Pro Feature: Analytics
    from app.api_v1 import analytics
    app.include_router(analytics.router, prefix="/api/v1")

    # Internal analyst UI
    app.include_router(ui.router)

    @app.get("/health", tags=["system"])
    def health_check() -> dict:
        return {"status": "ok"}

    return app


app = create_app()


