from datetime import datetime

from fastapi import FastAPI

from services.api_server.routers_admin import router as admin_router
from services.api_server.routers_client import router as client_router
from shared.schemas.common import HealthResponse
from shared.utils.logging import setup_logging

setup_logging()
app = FastAPI(title="Gold AI Trading API", version="0.1.0")
app.include_router(client_router)
app.include_router(admin_router)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="api_server", timestamp=datetime.utcnow())
