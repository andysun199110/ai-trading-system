from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.api_server.models import AuditEvent, EAHeartbeat, License, LicenseAccount, Session as Sess
from shared.config.settings import get_settings


class AuthError(Exception):
    pass


class AuthLicenseService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def activate(self, license_key: str, account_login: str, account_server: str) -> Sess:
        lic = self.db.scalar(select(License).where(License.license_key == license_key))
        if not lic:
            raise AuthError("license_not_found")
        if lic.revoked or lic.suspended:
            raise AuthError("license_blocked")
        if lic.expires_at <= datetime.utcnow():
            raise AuthError("license_expired")
        binding = self.db.scalar(
            select(LicenseAccount).where(
                LicenseAccount.license_id == lic.id,
                LicenseAccount.account_login == account_login,
                LicenseAccount.account_server == account_server,
            )
        )
        if not binding or binding.suspended:
            raise AuthError("account_not_authorized")

        token = str(uuid4())
        ttl = timedelta(minutes=self.settings.session_ttl_minutes)
        sess = Sess(
            token=token,
            license_id=lic.id,
            account_login=account_login,
            account_server=account_server,
            expires_at=datetime.utcnow() + ttl,
            last_heartbeat_at=datetime.utcnow(),
        )
        self.db.add(sess)
        self.db.add(AuditEvent(actor=account_login, event_type="auth.activate", payload={"server": account_server}))
        self.db.commit()
        self.db.refresh(sess)
        return sess

    def heartbeat(self, token: str) -> Sess:
        sess = self.db.scalar(select(Sess).where(Sess.token == token))
        if not sess:
            raise AuthError("session_not_found")
        sess.last_heartbeat_at = datetime.utcnow()
        sess.expires_at = datetime.utcnow() + timedelta(minutes=self.settings.session_ttl_minutes)
        self.db.add(EAHeartbeat(account_login=sess.account_login))
        self.db.commit()
        return sess

    def logout(self, token: str) -> None:
        sess = self.db.scalar(select(Sess).where(Sess.token == token))
        if sess:
            self.db.delete(sess)
            self.db.commit()
