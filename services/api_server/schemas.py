from datetime import datetime

from pydantic import BaseModel, Field


class ActivateRequest(BaseModel):
    license_key: str
    account_login: str
    account_server: str


class ActivateResponse(BaseModel):
    token: str
    expires_at: datetime
    mode: str


class HeartbeatRequest(BaseModel):
    token: str


class LogoutRequest(BaseModel):
    token: str


class CustomerCreateRequest(BaseModel):
    name: str
    email: str
    plan_type: str
    seat_limit: int = 1


class LicenseCreateRequest(BaseModel):
    customer_id: int
    license_key: str
    expires_at: datetime


class ExtendLicenseRequest(BaseModel):
    license_key: str
    expires_at: datetime


class RevokeLicenseRequest(BaseModel):
    license_key: str


class BindAccountRequest(BaseModel):
    license_key: str
    account_login: str
    account_server: str


class AccountControlRequest(BindAccountRequest):
    pass


class DeploymentPromoteRequest(BaseModel):
    environment: str = Field(pattern="^(develop|research|shadow|staging|live)$")
    version: str


class ExecutionReportRequest(BaseModel):
    token: str
    signal_id: str
    status: str
    payload: dict = Field(default_factory=dict)


class EAHealthRequest(BaseModel):
    token: str
    terminal: str
    payload: dict = Field(default_factory=dict)
