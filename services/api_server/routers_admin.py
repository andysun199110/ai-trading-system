from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from services.api_server.admin_service import AdminService
from services.api_server.db import get_db
from services.api_server.schemas import (
    AccountControlRequest,
    BindAccountRequest,
    CustomerCreateRequest,
    DeploymentPromoteRequest,
    ExtendLicenseRequest,
    LicenseCreateRequest,
    RevokeLicenseRequest,
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
