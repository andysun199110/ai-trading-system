from sqlalchemy.orm import Session

from services.api_server.models import AuditEvent


class AuditStoreService:
    def __init__(self, db: Session):
        self.db = db

    def record(self, actor: str, event_type: str, payload: dict) -> None:
        self.db.add(AuditEvent(actor=actor, event_type=event_type, payload=payload))
        self.db.commit()
