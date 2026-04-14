from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.api_server.models import (
    AuditEvent,
    Customer,
    DeploymentRecord,
    License,
    LicenseAccount,
    Session as UserSession,
)
from shared.constants.domain import ALLOWED_MULTI_SEATS, PlanType


class AdminService:
    def __init__(self, db: Session):
        self.db = db

    def create_customer(self, name: str, email: str, plan_type: str, seat_limit: int) -> Customer:
        if plan_type == PlanType.SINGLE_ACCOUNT.value:
            seat_limit = 1
        elif seat_limit not in ALLOWED_MULTI_SEATS:
            raise ValueError("invalid_seat_limit")
        customer = Customer(name=name, email=email, plan_type=plan_type, seat_limit=seat_limit)
        self.db.add(customer)
        self.db.add(AuditEvent(actor="admin", event_type="customer.create", payload={"email": email}))
        self.db.commit()
        self.db.refresh(customer)
        return customer

    def create_license(self, customer_id: int, license_key: str, expires_at: datetime) -> License:
        lic = License(customer_id=customer_id, license_key=license_key, expires_at=expires_at)
        self.db.add(lic)
        self.db.add(AuditEvent(actor="admin", event_type="license.create", payload={"license_key": license_key}))
        self.db.commit()
        self.db.refresh(lic)
        return lic

    def extend_license(self, license_key: str, expires_at: datetime) -> None:
        lic = self.db.scalar(select(License).where(License.license_key == license_key))
        if lic:
            lic.expires_at = expires_at
            self.db.add(AuditEvent(actor="admin", event_type="license.extend", payload={"license_key": license_key}))
            self.db.commit()

    def revoke_license(self, license_key: str) -> None:
        lic = self.db.scalar(select(License).where(License.license_key == license_key))
        if lic:
            lic.revoked = True
            self.db.add(AuditEvent(actor="admin", event_type="license.revoke", payload={"license_key": license_key}))
            self.db.commit()

    def bind_account(self, license_key: str, account_login: str, account_server: str) -> None:
        lic = self.db.scalar(select(License).where(License.license_key == license_key))
        if not lic:
            raise ValueError("license_missing")
        row = LicenseAccount(license_id=lic.id, account_login=account_login, account_server=account_server)
        self.db.add(row)
        self.db.add(AuditEvent(actor="admin", event_type="account.bind", payload={"account_login": account_login}))
        self.db.commit()

    def unbind_account(self, license_key: str, account_login: str, account_server: str) -> None:
        lic = self.db.scalar(select(License).where(License.license_key == license_key))
        row = self.db.scalar(select(LicenseAccount).where(LicenseAccount.license_id == lic.id, LicenseAccount.account_login == account_login, LicenseAccount.account_server == account_server)) if lic else None
        if row:
            self.db.delete(row)
            self.db.commit()

    def suspend_account(self, license_key: str, account_login: str, account_server: str, suspended: bool) -> None:
        lic = self.db.scalar(select(License).where(License.license_key == license_key))
        row = self.db.scalar(select(LicenseAccount).where(LicenseAccount.license_id == lic.id, LicenseAccount.account_login == account_login, LicenseAccount.account_server == account_server)) if lic else None
        if row:
            row.suspended = suspended
            self.db.commit()

    def sessions(self) -> list[UserSession]:
        return list(self.db.scalars(select(UserSession)).all())

    def audit(self) -> list[AuditEvent]:
        return list(self.db.scalars(select(AuditEvent).order_by(AuditEvent.id.desc())).all())

    def promote(self, environment: str, version: str) -> DeploymentRecord:
        rec = DeploymentRecord(environment=environment, version=version, status="promoted")
        self.db.add(rec)
        self.db.commit()
        self.db.refresh(rec)
        return rec
