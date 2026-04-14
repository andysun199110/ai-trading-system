from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from services.api_server.db import Base


class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    plan_type: Mapped[str] = mapped_column(String(32), nullable=False)
    seat_limit: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class License(Base):
    __tablename__ = "licenses"
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    license_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    suspended: Mapped[bool] = mapped_column(Boolean, default=False)


class LicenseAccount(Base):
    __tablename__ = "license_accounts"
    __table_args__ = (UniqueConstraint("license_id", "account_login", "account_server"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    license_id: Mapped[int] = mapped_column(ForeignKey("licenses.id"), nullable=False)
    account_login: Mapped[str] = mapped_column(String(32), nullable=False)
    account_server: Mapped[str] = mapped_column(String(64), nullable=False)
    suspended: Mapped[bool] = mapped_column(Boolean, default=False)


class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)
    license_id: Mapped[int] = mapped_column(ForeignKey("licenses.id"), nullable=False)
    account_login: Mapped[str] = mapped_column(String(32), nullable=False)
    account_server: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_heartbeat_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Signal(Base):
    __tablename__ = "signals"
    id: Mapped[int] = mapped_column(primary_key=True)
    signal_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="new")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)


class SignalReview(Base): __tablename__ = "signal_reviews"; id: Mapped[int] = mapped_column(primary_key=True); signal_id: Mapped[str] = mapped_column(String(64)); decision: Mapped[str] = mapped_column(String(32)); notes: Mapped[str] = mapped_column(Text, default="")
class RiskDecision(Base): __tablename__ = "risk_decisions"; id: Mapped[int] = mapped_column(primary_key=True); signal_id: Mapped[str] = mapped_column(String(64)); decision: Mapped[str] = mapped_column(String(32)); payload: Mapped[dict] = mapped_column(JSON, default=dict)
class Order(Base): __tablename__ = "orders"; id: Mapped[int] = mapped_column(primary_key=True); account_login: Mapped[str] = mapped_column(String(32)); payload: Mapped[dict] = mapped_column(JSON, default=dict)
class Position(Base): __tablename__ = "positions"; id: Mapped[int] = mapped_column(primary_key=True); account_login: Mapped[str] = mapped_column(String(32)); symbol: Mapped[str] = mapped_column(String(16)); state: Mapped[str] = mapped_column(String(32), default="open")
class PositionAction(Base): __tablename__ = "position_actions"; id: Mapped[int] = mapped_column(primary_key=True); position_id: Mapped[int] = mapped_column(Integer); action: Mapped[str] = mapped_column(String(32)); payload: Mapped[dict] = mapped_column(JSON, default=dict)
class EventWindow(Base): __tablename__ = "event_windows"; id: Mapped[int] = mapped_column(primary_key=True); event_type: Mapped[str] = mapped_column(String(64)); starts_at: Mapped[datetime] = mapped_column(DateTime); ends_at: Mapped[datetime] = mapped_column(DateTime)
class EtfBiasSnapshot(Base): __tablename__ = "etf_bias_snapshots"; id: Mapped[int] = mapped_column(primary_key=True); snapshot_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow); payload: Mapped[dict] = mapped_column(JSON, default=dict)
class WeeklyReview(Base): __tablename__ = "weekly_reviews"; id: Mapped[int] = mapped_column(primary_key=True); week_label: Mapped[str] = mapped_column(String(32)); payload: Mapped[dict] = mapped_column(JSON, default=dict)
class OptimizationProposal(Base): __tablename__ = "optimization_proposals"; id: Mapped[int] = mapped_column(primary_key=True); proposal: Mapped[dict] = mapped_column(JSON, default=dict); status: Mapped[str] = mapped_column(String(32), default="new")
class DeploymentRecord(Base): __tablename__ = "deployment_records"; id: Mapped[int] = mapped_column(primary_key=True); environment: Mapped[str] = mapped_column(String(16)); version: Mapped[str] = mapped_column(String(64)); status: Mapped[str] = mapped_column(String(32)); created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
class EAHeartbeat(Base): __tablename__ = "ea_heartbeats"; id: Mapped[int] = mapped_column(primary_key=True); account_login: Mapped[str] = mapped_column(String(32)); heartbeat_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
class TelegramEvent(Base): __tablename__ = "telegram_events"; id: Mapped[int] = mapped_column(primary_key=True); event_type: Mapped[str] = mapped_column(String(64)); payload: Mapped[dict] = mapped_column(JSON, default=dict)
class KillSwitchEvent(Base): __tablename__ = "kill_switch_events"; id: Mapped[int] = mapped_column(primary_key=True); enabled: Mapped[bool] = mapped_column(Boolean, default=False); reason: Mapped[str] = mapped_column(Text, default="")
class SystemHealthEvent(Base): __tablename__ = "system_health_events"; id: Mapped[int] = mapped_column(primary_key=True); service: Mapped[str] = mapped_column(String(64)); status: Mapped[str] = mapped_column(String(16)); payload: Mapped[dict] = mapped_column(JSON, default=dict)
class AuditEvent(Base): __tablename__ = "audit_events"; id: Mapped[int] = mapped_column(primary_key=True); actor: Mapped[str] = mapped_column(String(64)); event_type: Mapped[str] = mapped_column(String(64)); payload: Mapped[dict] = mapped_column(JSON, default=dict); created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class AIInvocation(Base): __tablename__ = "ai_invocations"; id: Mapped[int] = mapped_column(primary_key=True); module: Mapped[str] = mapped_column(String(64)); latency_ms: Mapped[float] = mapped_column(); model_version: Mapped[str] = mapped_column(String(64)); prompt_version: Mapped[str] = mapped_column(String(64)); created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
class ValidationReport(Base): __tablename__ = "validation_reports"; id: Mapped[int] = mapped_column(primary_key=True); mode: Mapped[str] = mapped_column(String(16)); payload: Mapped[dict] = mapped_column(JSON, default=dict); created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
