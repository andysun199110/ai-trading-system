from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from services.api_server.admin_service import AdminService
from services.api_server.db import get_db
from services.api_server.models import TradingCommand, TradingExecutionReport
from services.api_server.schemas import (
    AccountControlRequest,
    BindAccountRequest,
    CustomerCreateRequest,
    DeploymentPromoteRequest,
    ExtendLicenseRequest,
    LicenseCreateRequest,
    RevokeLicenseRequest,
    AdminCommandsQuery,
    AdminExecutionReportsQuery,
)
from shared.schemas.common import APIResponse

router = APIRouter(prefix="/admin")


@router.post("/customers", response_model=APIResponse)
def create_customer(req: CustomerCreateRequest, db: Session = Depends(get_db)) -> APIResponse:
    c = AdminService(db).create_customer(req.name, req.email, req.plan_type, req.seat_limit)
    return APIResponse(message="customer_created", payload={"customer_id": c.id})


@router.post("/licenses", response_model=APIResponse)
def create_license(req: LicenseCreateRequest, db: Session = Depends(get_db)) -> APIResponse:
    lic = AdminService(db).create_license(req.customer_id, req.license_key, req.expires_at)
    return APIResponse(message="license_created", payload={"license_id": lic.id})


@router.post("/licenses/extend", response_model=APIResponse)
def extend_license(req: ExtendLicenseRequest, db: Session = Depends(get_db)) -> APIResponse:
    AdminService(db).extend_license(req.license_key, req.expires_at)
    return APIResponse(message="license_extended")


@router.post("/licenses/revoke", response_model=APIResponse)
def revoke_license(req: RevokeLicenseRequest, db: Session = Depends(get_db)) -> APIResponse:
    AdminService(db).revoke_license(req.license_key)
    return APIResponse(message="license_revoked")


@router.post("/accounts/bind", response_model=APIResponse)
def bind(req: BindAccountRequest, db: Session = Depends(get_db)) -> APIResponse:
    AdminService(db).bind_account(req.license_key, req.account_login, req.account_server)
    return APIResponse(message="account_bound")


@router.post("/accounts/unbind", response_model=APIResponse)
def unbind(req: BindAccountRequest, db: Session = Depends(get_db)) -> APIResponse:
    AdminService(db).unbind_account(req.license_key, req.account_login, req.account_server)
    return APIResponse(message="account_unbound")


@router.post("/accounts/suspend", response_model=APIResponse)
def suspend(req: AccountControlRequest, db: Session = Depends(get_db)) -> APIResponse:
    AdminService(db).suspend_account(req.license_key, req.account_login, req.account_server, True)
    return APIResponse(message="account_suspended")


@router.post("/accounts/unsuspend", response_model=APIResponse)
def unsuspend(req: AccountControlRequest, db: Session = Depends(get_db)) -> APIResponse:
    AdminService(db).suspend_account(req.license_key, req.account_login, req.account_server, False)
    return APIResponse(message="account_unsuspended")


@router.get("/sessions", response_model=APIResponse)
def sessions(db: Session = Depends(get_db)) -> APIResponse:
    rows = AdminService(db).sessions()
    return APIResponse(payload={"count": len(rows), "items": [{"token": r.token, "account_login": r.account_login} for r in rows]})


@router.get("/audit", response_model=APIResponse)
def audit(db: Session = Depends(get_db)) -> APIResponse:
    rows = AdminService(db).audit()
    return APIResponse(payload={"count": len(rows), "items": [{"event_type": r.event_type, "actor": r.actor} for r in rows[:50]]})


@router.get("/health", response_model=APIResponse)
def health() -> APIResponse:
    return APIResponse(message="admin_ok", payload={"time": datetime.utcnow().isoformat()})


@router.post("/deployments/promote", response_model=APIResponse)
def promote(req: DeploymentPromoteRequest, db: Session = Depends(get_db)) -> APIResponse:
    rec = AdminService(db).promote(req.environment, req.version)
    return APIResponse(message="deployment_promoted", payload={"id": rec.id})


@router.get("/commands", response_model=APIResponse)
def list_commands(
    account_login: str | None = Query(None),
    status: str | None = Query(None),
    command_type: str | None = Query(None),
    signal_id: str | None = Query(None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> APIResponse:
    """
    Query trading commands for operations/monitoring.
    
    Filters:
    - account_login: Filter by MT5 account login
    - status: Filter by command status (PENDING, SENT, EXECUTED, etc.)
    - command_type: Filter by command type (OPEN, CLOSE_FULL, etc.)
    - signal_id: Filter by source signal ID
    - limit: Max results (1-500, default 100)
    """
    stmt = select(TradingCommand).order_by(TradingCommand.issued_at.desc()).limit(limit)
    
    if account_login:
        stmt = stmt.where(TradingCommand.account_login == account_login)
    if status:
        stmt = stmt.where(TradingCommand.status == status)
    if command_type:
        stmt = stmt.where(TradingCommand.command_type == command_type)
    if signal_id:
        stmt = stmt.where(TradingCommand.signal_id == signal_id)
    
    results = db.execute(stmt).scalars().all()
    
    commands = []
    for cmd in results:
        commands.append({
            "command_id": cmd.command_id,
            "account_login": cmd.account_login,
            "account_server": cmd.account_server,
            "command_type": cmd.command_type,
            "symbol": cmd.symbol,
            "side": cmd.side,
            "volume": float(cmd.volume) if cmd.volume else None,
            "sl": float(cmd.sl) if cmd.sl else None,
            "tp": float(cmd.tp) if cmd.tp else None,
            "status": cmd.status,
            "signal_id": cmd.signal_id,
            "source_module": cmd.source_module,
            "issued_at": cmd.issued_at.isoformat() + "Z" if cmd.issued_at else None,
            "expires_at": cmd.expires_at.isoformat() + "Z" if cmd.expires_at else None,
            "priority": cmd.priority,
            "reason": cmd.reason,
        })
    
    return APIResponse(
        payload={
            "count": len(commands),
            "items": commands,
        }
    )


@router.get("/execution-reports", response_model=APIResponse)
def list_execution_reports(
    command_id: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> APIResponse:
    """
    Query execution reports for operations/monitoring.
    
    Filters:
    - command_id: Filter by command ID
    - status: Filter by execution status (EXECUTED, REJECTED, etc.)
    - limit: Max results (1-500, default 100)
    """
    stmt = select(TradingExecutionReport).order_by(TradingExecutionReport.created_at.desc()).limit(limit)
    
    if command_id:
        stmt = stmt.where(TradingExecutionReport.command_id == command_id)
    if status:
        stmt = stmt.where(TradingExecutionReport.status == status)
    
    results = db.execute(stmt).scalars().all()
    
    reports = []
    for rpt in results:
        reports.append({
            "report_id": rpt.report_id,
            "command_id": rpt.command_id,
            "ea_terminal": rpt.ea_terminal,
            "status": rpt.status,
            "broker_retcode": rpt.broker_retcode,
            "broker_comment": rpt.broker_comment,
            "executed_price": float(rpt.executed_price) if rpt.executed_price else None,
            "executed_volume": float(rpt.executed_volume) if rpt.executed_volume else None,
            "sl": float(rpt.sl) if rpt.sl else None,
            "tp": float(rpt.tp) if rpt.tp else None,
            "server_time": rpt.server_time.isoformat() + "Z" if rpt.server_time else None,
            "created_at": rpt.created_at.isoformat() + "Z" if rpt.created_at else None,
        })
    
    return APIResponse(
        payload={
            "count": len(reports),
            "items": reports,
        }
    )
