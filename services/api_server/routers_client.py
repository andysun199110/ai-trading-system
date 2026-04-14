from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from services.api_server.db import get_db
from services.api_server.schemas import (
    ActivateRequest,
    ActivateResponse,
    EAHealthRequest,
    ExecutionReportRequest,
    HeartbeatRequest,
    LogoutRequest,
)
from services.auth_license.service import AuthError, AuthLicenseService
from shared.constants.domain import SYMBOL_XAUUSD
from shared.schemas.common import APIResponse

router = APIRouter(prefix="/api/v1")


@router.post("/auth/activate", response_model=ActivateResponse)
def activate(req: ActivateRequest, db: Session = Depends(get_db)) -> ActivateResponse:
    svc = AuthLicenseService(db)
    try:
        sess = svc.activate(req.license_key, req.account_login, req.account_server)
    except AuthError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return ActivateResponse(token=sess.token, expires_at=sess.expires_at, mode="active")


@router.post("/auth/heartbeat", response_model=APIResponse)
def heartbeat(req: HeartbeatRequest, db: Session = Depends(get_db)) -> APIResponse:
    svc = AuthLicenseService(db)
    try:
        sess = svc.heartbeat(req.token)
    except AuthError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return APIResponse(message="heartbeat_ok", payload={"expires_at": sess.expires_at.isoformat()})


@router.post("/auth/logout", response_model=APIResponse)
def logout(req: LogoutRequest, db: Session = Depends(get_db)) -> APIResponse:
    AuthLicenseService(db).logout(req.token)
    return APIResponse(message="logout_ok")


@router.get("/config", response_model=APIResponse)
def config() -> APIResponse:
    return APIResponse(payload={"symbol": SYMBOL_XAUUSD, "timeframe": "M15", "modes": ["develop", "research", "shadow", "staging", "live"]})


@router.get("/signals/poll", response_model=APIResponse)
def poll_signals() -> APIResponse:
    return APIResponse(payload={"signals": [], "entries_enabled": False, "protective_mode_only": True})


@router.post("/execution/report", response_model=APIResponse)
def report_execution(req: ExecutionReportRequest) -> APIResponse:
    return APIResponse(message="execution_reported", payload={"signal_id": req.signal_id, "status": req.status})


@router.post("/health/ea", response_model=APIResponse)
def ea_health(req: EAHealthRequest) -> APIResponse:
    return APIResponse(message="ea_health_recorded", payload={"terminal": req.terminal, "at": datetime.utcnow().isoformat()})
