import json
import time
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, text, and_
from sqlalchemy.orm import Session

from services.api_server.db import get_db
from services.api_server.models import (
    Session as AuthSession, 
    Signal,
    TradingCommand,
    TradingExecutionReport,
    AuditEvent,
    PositionSnapshot,
)
from services.api_server.schemas import (
    ActivateRequest,
    ActivateResponse,
    EAHealthRequest,
    ExecutionReportRequest,
    HeartbeatRequest,
    LogoutRequest,
    PollCommandsResponse,
    AdminCommandsQuery,
    AdminExecutionReportsQuery,
    PositionSnapshotRequest,
)
from services.auth_license.service import AuthError, AuthLicenseService
from shared.constants.domain import SYMBOL_XAUUSD
from shared.schemas.common import APIResponse

router = APIRouter(prefix="/api/v1")

# Command status constants (v1.1)
CMD_STATUS_PENDING = "PENDING"
CMD_STATUS_SENT = "SENT"
CMD_STATUS_DISPATCHED = "DISPATCHED"
CMD_STATUS_EXECUTED = "EXECUTED"
CMD_STATUS_FAILED = "FAILED"
CMD_STATUS_EXPIRED = "EXPIRED"
CMD_STATUS_REJECTED = "REJECTED"
CMD_STATUS_DUPLICATE = "DUPLICATE"
CMD_STATUS_CANCELLED = "CANCELLED"
CMD_STATUS_SHADOW_SKIPPED = "SHADOW_SKIPPED"
CMD_STATUS_TRADING_DISABLED = "TRADING_DISABLED"
CMD_STATUS_AVAILABLE = "AVAILABLE"

# Terminal statuses (not returned in poll)
TERMINAL_STATUSES = [
    CMD_STATUS_EXECUTED,
    CMD_STATUS_FAILED,
    CMD_STATUS_EXPIRED,
    CMD_STATUS_REJECTED,
    CMD_STATUS_DUPLICATE,
    CMD_STATUS_CANCELLED,
    CMD_STATUS_SHADOW_SKIPPED,
    CMD_STATUS_TRADING_DISABLED,
]

# Active statuses (returned in poll)
ACTIVE_STATUSES = [CMD_STATUS_AVAILABLE, CMD_STATUS_DISPATCHED]

# Command type constants
CMD_TYPE_OPEN = "OPEN"
CMD_TYPE_MODIFY_SL = "MODIFY_SL"
CMD_TYPE_MODIFY_TP = "MODIFY_TP"
CMD_TYPE_CLOSE_PARTIAL = "CLOSE_PARTIAL"
CMD_TYPE_CLOSE_FULL = "CLOSE_FULL"
CMD_TYPE_CANCEL_OPEN = "CANCEL_OPEN"

# Source module constants
SOURCE_SIGNAL_ENGINE = "signal_engine"
SOURCE_POSITION_SUPERVISOR = "position_supervisor"
SOURCE_MANUAL_ADMIN = "manual_admin"


@router.post("/auth/activate", response_model=ActivateResponse)
def activate(req: ActivateRequest, db: Session = Depends(get_db)) -> ActivateResponse:
    """Activate EA session with license validation."""
    svc = AuthLicenseService(db)
    try:
        sess = svc.activate(req.license_key, req.account_login, req.account_server)
    except AuthError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return ActivateResponse(token=sess.token, expires_at=sess.expires_at, mode="active")


@router.post("/auth/heartbeat", response_model=APIResponse)
def heartbeat(req: HeartbeatRequest, db: Session = Depends(get_db)) -> APIResponse:
    """Send heartbeat to keep session alive."""
    svc = AuthLicenseService(db)
    try:
        sess = svc.heartbeat(req.token)
    except AuthError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return APIResponse(message="heartbeat_ok", payload={"expires_at": sess.expires_at.isoformat()})


@router.post("/auth/logout", response_model=APIResponse)
def logout(req: LogoutRequest, db: Session = Depends(get_db)) -> APIResponse:
    """Logout and invalidate session."""
    AuthLicenseService(db).logout(req.token)
    return APIResponse(message="logout_ok")


@router.get("/config", response_model=APIResponse)
def config() -> APIResponse:
    """Get EA configuration."""
    return APIResponse(payload={"symbol": SYMBOL_XAUUSD, "timeframe": "M15", "modes": ["develop", "research", "shadow", "staging", "live"]})


@router.get("/signals/poll", response_model=APIResponse)
def poll_commands(token: str, db: Session = Depends(get_db)) -> APIResponse:
    """
    Poll trading commands for authenticated EA client (v1.1).
    
    Returns active commands for the authenticated account.
    Filters by account_login + account_server + license active + status + expiry.
    NO symbol filtering (dispatch by account, not by symbol).
    Does not return terminal state commands.
    
    Response format (v1.1):
    {
     "message":"ok",
     "payload":{
     "server_time_epoch": <int>,
     "commands":[ ... ]
     }
    }
    
    Each command includes:
    - command_id, idempotency_key, signal_id
    - account_login, account_server
    - command_type, side, volume, sl, tp
    - entry_ref_price, max_adverse_move_price
    - created_at_epoch, expires_at_epoch
    - priority
    
    OPEN replacement logic:
    - If new OPEN arrives and old OPEN still unexecuted: old OPEN -> cancelled, new OPEN enqueued
    - If old OPEN already executed to position: keep it, position supervisor generates CLOSE_FULL/MODIFY_SL
    """
    # Validate session and get account info
    sess = db.scalar(select(AuthSession).where(AuthSession.token == token))
    if not sess:
        raise HTTPException(status_code=403, detail="invalid_session")
    
    account_login = sess.account_login
    account_server = sess.account_server
    server_time = datetime.utcnow()
    server_time_epoch = int(server_time.timestamp())
    
    # Expire old commands (background cleanup)
    db.execute(
        text("""
            UPDATE trading_commands 
            SET status = :status, reason = :reason
            WHERE status IN (:available, :dispatched) 
            AND expires_at_epoch < :now_epoch
        """),
        {
            "status": CMD_STATUS_EXPIRED,
            "reason": "Command expired",
            "available": CMD_STATUS_AVAILABLE,
            "dispatched": CMD_STATUS_DISPATCHED,
            "now_epoch": server_time_epoch,
        }
    )
    db.commit()
    
    # Fetch active commands for this account (v1.1 contract)
    # Filter:
    # - account_login + account_server match
    # - status IN (AVAILABLE, DISPATCHED) - NOT terminal statuses
    # - expires_at_epoch > now_epoch
    # NO symbol filtering (dispatch by account)
    stmt = text("""
        SELECT command_id, idempotency_key, signal_id, command_type, side, 
               volume, sl, tp, entry_ref_price, max_adverse_move_price,
               created_at_epoch, expires_at_epoch, priority, payload
        FROM trading_commands
        WHERE account_login = :account_login
          AND account_server = :account_server
          AND status IN (:available, :dispatched)
          AND expires_at_epoch > :now_epoch
        ORDER BY priority ASC, created_at_epoch ASC
        LIMIT :limit
    """)
    
    result = db.execute(
        stmt,
        {
            "account_login": account_login,
            "account_server": account_server,
            "available": CMD_STATUS_AVAILABLE,
            "dispatched": CMD_STATUS_DISPATCHED,
            "now_epoch": server_time_epoch,
            "limit": 20,
        }
    )
    
    commands = []
    
    for row in result:
        payload = row[13] if isinstance(row[13], dict) else {}
        
        command = {
            "command_id": row[0],
            "idempotency_key": row[1],
            "signal_id": row[2],
            "account_login": account_login,
            "account_server": account_server,
            "command_type": row[3],
            "side": row[4],
            "volume": float(row[5]) if row[5] else None,
            "sl": float(row[6]) if row[6] else None,
            "tp": float(row[7]) if row[7] else None,
            "entry_ref_price": float(row[8]) if row[8] else None,
            "max_adverse_move_price": float(row[9]) if row[9] else None,
            "created_at_epoch": row[10],
            "expires_at_epoch": row[11],
            "priority": row[12] if isinstance(row[12], int) else 100,
            "payload": payload,
        }
        commands.append(command)
    
    # Legacy signals removed in v1.1 - use trading_commands only
    
    return APIResponse(
        message="ok",
        payload={
            "server_time_epoch": server_time_epoch,
            "commands": commands,
        }
    )


@router.post("/execution/report", response_model=APIResponse)
def report_execution(req: ExecutionReportRequest, db: Session = Depends(get_db)) -> APIResponse:
    """
    Report command execution status from EA (v1.1).
    
    Accepts status: executed / failed / expired / rejected / duplicate / shadow_skipped / trading_disabled
    
    Rules:
    - command_id exists + status valid -> 200 and update command status
    - expired/rejected/duplicate do NOT return 400
    - Idempotent: same command_id + same status returns 200
    
    Payload should include:
    - broker_retcode: MT5 return code
    - broker_comment: MT5 comment
    - executed_price: Fill price (if applicable)
    - executed_volume: Fill volume (if applicable)
    - executed_symbol: Symbol executed (audit field)
    - sl: Stop loss set (if applicable)
    - tp: Take profit set (if applicable)
    - server_time: EA server time
    """
    # Validate session
    sess = db.scalar(select(AuthSession).where(AuthSession.token == req.token))
    if not sess:
        raise HTTPException(status_code=403, detail="invalid_session")
    
    # Find the command
    cmd = db.scalar(select(TradingCommand).where(TradingCommand.command_id == req.command_id))
    if not cmd:
        raise HTTPException(status_code=404, detail="command_not_found")
    
    # v1.1: Accept terminal statuses without state machine validation
    # expired/rejected/duplicate/shadow_skipped/trading_disabled are all valid
    VALID_STATUSES = [
        CMD_STATUS_EXECUTED,
        CMD_STATUS_FAILED,
        CMD_STATUS_EXPIRED,
        CMD_STATUS_REJECTED,
        CMD_STATUS_DUPLICATE,
        CMD_STATUS_SHADOW_SKIPPED,
        CMD_STATUS_TRADING_DISABLED,
    ]
    
    req_status_upper = req.status.upper()
    if req_status_upper not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"invalid_status: {req.status} not in {VALID_STATUSES}"
        )
    
    # Idempotency check: same command_id + same status returns 200
    if cmd.status.upper() == req_status_upper:
        return APIResponse(
            message="execution_reported_idempotent",
            payload={
                "command_id": req.command_id,
                "status": req.status,
                "note": "Duplicate report ignored (idempotent)",
            }
        )
    
    # Create execution report
    report_id = f"rpt-{uuid.uuid4().hex[:12]}"
    exec_payload = req.payload.copy()
    
    report = TradingExecutionReport(
        report_id=report_id,
        command_id=req.command_id,
        ea_terminal=sess.account_login,
        status=req.status,
        broker_retcode=exec_payload.get("broker_retcode"),
        broker_comment=exec_payload.get("broker_comment"),
        executed_price=exec_payload.get("executed_price"),
        executed_volume=exec_payload.get("executed_volume"),
        executed_symbol=exec_payload.get("executed_symbol"),  # v1.1 audit field
        sl=exec_payload.get("sl"),
        tp=exec_payload.get("tp"),
        server_time=datetime.fromisoformat(exec_payload["server_time"].replace("Z", "+00:00")) if exec_payload.get("server_time") else None,
        raw_payload=exec_payload,
    )
    
    db.add(report)
    
    # Update command status
    cmd.status = req_status_upper
    now = datetime.utcnow()
    cmd.executed_at = now
    
    # Set reason for terminal statuses
    if req_status_upper in [CMD_STATUS_REJECTED, CMD_STATUS_FAILED, CMD_STATUS_EXPIRED]:
        cmd.reason = exec_payload.get("broker_comment", f"Status: {req.status}")
    elif req_status_upper == CMD_STATUS_DUPLICATE:
        cmd.reason = "Duplicate command detected by EA"
    elif req_status_upper == CMD_STATUS_SHADOW_SKIPPED:
        cmd.reason = "Shadow mode - command skipped"
    elif req_status_upper == CMD_STATUS_TRADING_DISABLED:
        cmd.reason = "Trading disabled by EA"
    
    db.add(cmd)
    db.commit()
    
    # Audit log
    db.add(AuditEvent(
        actor=f"ea:{sess.account_login}",
        event_type="command_execution_reported",
        payload={
            "command_id": req.command_id,
            "status": req.status,
            "report_id": report_id,
            "broker_retcode": exec_payload.get("broker_retcode"),
            "executed_symbol": exec_payload.get("executed_symbol"),
        }
    ))
    db.commit()
    
    return APIResponse(
        message="execution_reported",
        payload={
            "command_id": req.command_id,
            "report_id": report_id,
            "status": req.status,
        }
    )


@router.post("/health/ea", response_model=APIResponse)
def ea_health(req: EAHealthRequest) -> APIResponse:
    """Record EA health status."""
    return APIResponse(message="ea_health_recorded", payload={"terminal": req.terminal, "at": datetime.utcnow().isoformat()})


@router.post("/positions/snapshot", response_model=APIResponse)
def submit_position_snapshot(req: PositionSnapshotRequest, db: Session = Depends(get_db)) -> APIResponse:
    """
    Submit position snapshot for audit and supervision input (v1.1).
    
    Receives account_login/account_server/positions[]
    Positions minimum fields: ticket, symbol, side, volume, entry_price, current_price, sl, tp, swap, profit
    
    Used for:
    - Audit trail of EA position state
    - Position supervisor input (not used for symbol filtering in dispatch)
    - Reconciliation between server commands and EA state
    
    Does NOT participate in symbol dispatch filtering.
    """
    # Validate session
    sess = db.scalar(select(AuthSession).where(AuthSession.token == req.token))
    if not sess:
        raise HTTPException(status_code=403, detail="invalid_session")
    
    # Validate account matches session
    if req.account_login != sess.account_login or req.account_server != sess.account_server:
        raise HTTPException(status_code=403, detail="account_mismatch")
    
    # Create position snapshot
    snapshot_time_epoch = int(datetime.utcnow().timestamp())
    
    snapshot = PositionSnapshot(
        account_login=req.account_login,
        account_server=req.account_server,
        snapshot_time_epoch=snapshot_time_epoch,
        positions=req.positions,
    )
    
    db.add(snapshot)
    db.commit()
    
    return APIResponse(
        message="snapshot_recorded",
        payload={
            "account_login": req.account_login,
            "account_server": req.account_server,
            "positions_count": len(req.positions),
            "snapshot_time_epoch": snapshot_time_epoch,
        }
    )
