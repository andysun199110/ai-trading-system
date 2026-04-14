from enum import Enum


class EnvironmentMode(str, Enum):
    DEVELOP = "develop"
    RESEARCH = "research"
    SHADOW = "shadow"
    STAGING = "staging"
    LIVE = "live"


class PlanType(str, Enum):
    SINGLE_ACCOUNT = "single_account"
    MULTI_ACCOUNT = "multi_account"


ALLOWED_MULTI_SEATS = {3, 5, 10}
SYMBOL_XAUUSD = "XAUUSD"
BROKER_TYPE = "mt5"
DEFAULT_SESSION_MINUTES = 15
