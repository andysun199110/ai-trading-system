from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any

from services.ai_orchestrator.provider import get_provider

REQUIRED_FIELDS = {"decision", "confidence", "reasons", "risk_notes", "action", "model_version", "prompt_version"}


@dataclass
class ServiceResult:
    status: str
    payload: dict[str, Any]


class ContractValidationError(Exception):
    """Raised when AI response contract validation fails."""
    def __init__(self, message: str, missing_fields: list[str] | None = None, invalid_fields: list[str] | None = None):
        self.message = message
        self.missing_fields = missing_fields or []
        self.invalid_fields = invalid_fields or []
        super().__init__(self.message)


class Service:
    """Routes AI calls through configured provider with strict JSON contract enforcement."""

    def run(self, payload: dict[str, Any] | None = None) -> ServiceResult:
        data = payload or {}
        module = data.get("module", "candidate_signal_reviewer")
        context = data.get("context", {})

        if module not in {"candidate_signal_reviewer", "event_analyst", "position_supervisor_ai", "weekly_review_ai"}:
            return ServiceResult(
                status="blocked", 
                payload={
                    "reason": "unsupported_module", 
                    "module": module,
                    "valid_modules": ["candidate_signal_reviewer", "event_analyst", "position_supervisor_ai", "weekly_review_ai"]
                }
            )

        start = perf_counter()
        
        try:
            provider = get_provider()
            response = provider.generate(module, context)
            latency_ms = round((perf_counter() - start) * 1000, 3)
            
            # Validate contract and collect field-level errors
            validation_errors = self._validate_contract(response)
            
            if validation_errors:
                return ServiceResult(
                    status="contract_error",
                    payload={
                        "module": module,
                        "error": "Contract validation failed",
                        "validation_errors": validation_errors,
                        "latency_ms": latency_ms,
                        "provider": response.provider,
                    }
                )
            
            return ServiceResult(
                status="ok",
                payload={
                    "module": module,
                    "response": {
                        "decision": response.decision,
                        "confidence": response.confidence,
                        "reasons": response.reasons,
                        "risk_notes": response.risk_notes,
                        "action": response.action,
                        "model_version": response.model_version,
                        "prompt_version": response.prompt_version,
                    },
                    "latency_ms": latency_ms,
                    "valid_contract": True,
                    "provider": response.provider,
                },
            )
        except ContractValidationError as e:
            latency_ms = round((perf_counter() - start) * 1000, 3)
            return ServiceResult(
                status="contract_error",
                payload={
                    "module": module,
                    "error": e.message,
                    "missing_fields": e.missing_fields,
                    "invalid_fields": e.invalid_fields,
                    "latency_ms": latency_ms,
                    "provider": "unknown",
                },
            )
        except Exception as e:
            latency_ms = round((perf_counter() - start) * 1000, 3)
            return ServiceResult(
                status="error",
                payload={
                    "module": module,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "latency_ms": latency_ms,
                    "provider": "unknown",
                },
            )
    
    def _validate_contract(self, response: Any) -> list[dict[str, Any]]:
        """Validate AI response contract and return field-level errors."""
        errors = []
        
        # Check required fields
        for field in REQUIRED_FIELDS:
            if not hasattr(response, field) or getattr(response, field) is None:
                errors.append({
                    "field": field,
                    "error": "missing_required_field",
                    "message": f"Required field '{field}' is missing"
                })
        
        # Validate field types and values
        if hasattr(response, "confidence"):
            if not isinstance(response.confidence, (int, float)):
                errors.append({
                    "field": "confidence",
                    "error": "invalid_type",
                    "message": "confidence must be a number"
                })
            elif not 0 <= response.confidence <= 1:
                errors.append({
                    "field": "confidence",
                    "error": "out_of_range",
                    "message": f"confidence must be between 0 and 1, got {response.confidence}"
                })
        
        if hasattr(response, "reasons"):
            if not isinstance(response.reasons, list):
                errors.append({
                    "field": "reasons",
                    "error": "invalid_type",
                    "message": "reasons must be an array"
                })
        
        if hasattr(response, "risk_notes"):
            if not isinstance(response.risk_notes, list):
                errors.append({
                    "field": "risk_notes",
                    "error": "invalid_type",
                    "message": "risk_notes must be an array"
                })
        
        if hasattr(response, "decision"):
            valid_decisions = {"approve", "adjust", "restrict", "reject"}
            if response.decision not in valid_decisions:
                errors.append({
                    "field": "decision",
                    "error": "invalid_value",
                    "message": f"decision must be one of {valid_decisions}, got '{response.decision}'"
                })
        
        if hasattr(response, "action"):
            valid_actions = {"proceed", "modify", "block", "tighten_risk", "breakeven", "trailing", "hold", "block_entries"}
            if response.action not in valid_actions:
                errors.append({
                    "field": "action",
                    "error": "invalid_value",
                    "message": f"action must be one of {valid_actions}, got '{response.action}'"
                })
        
        return errors
