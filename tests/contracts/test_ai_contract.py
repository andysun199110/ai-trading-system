"""AI Orchestrator Contract Tests - Comprehensive field-level validation."""
from dataclasses import dataclass

import pytest

from services.ai_orchestrator.service import (
    REQUIRED_FIELDS,
    ContractValidationError,
    Service,
)
from services.ai_orchestrator.provider import AIResponse, MockProvider


class TestAIOutputContractBasic:
    """Basic contract validation tests."""

    def test_ai_output_contract_basic(self) -> None:
        """Test basic contract with valid module."""
        out = Service().run({"module": "candidate_signal_reviewer", "context": {}})
        # Status can be ok or contract_error depending on provider
        assert out.status in ["ok", "contract_error"]
        if out.status == "ok":
            response = out.payload["response"]
            assert set(response.keys()) == REQUIRED_FIELDS

    def test_unsupported_module_blocked(self) -> None:
        """Test unsupported modules are blocked with details."""
        out = Service().run({"module": "invalid_module", "context": {}})
        assert out.status == "blocked"
        assert out.payload["reason"] == "unsupported_module"
        assert "valid_modules" in out.payload


class TestFieldLevelValidation:
    """Field-level contract validation tests."""

    def test_validate_contract_missing_fields(self) -> None:
        """Test detection of missing required fields."""
        svc = Service()
        
        @dataclass
        class IncompleteResponse:
            decision: str = "approve"
            # Missing: confidence, reasons, risk_notes, action, model_version, prompt_version
        
        errors = svc._validate_contract(IncompleteResponse())
        missing = [e["field"] for e in errors]
        assert "confidence" in missing
        assert "reasons" in missing
        assert len(missing) == 6

    def test_validate_contract_confidence_out_of_range(self) -> None:
        """Test confidence value boundary validation."""
        svc = Service()
        
        response = AIResponse(
            decision="approve", confidence=1.5, reasons=["test"], risk_notes=[],
            action="proceed", model_version="v1", prompt_version="p1",
        )
        errors = svc._validate_contract(response)
        assert any(e["field"] == "confidence" and e["error"] == "out_of_range" for e in errors)

    def test_validate_contract_confidence_negative(self) -> None:
        """Test negative confidence is rejected."""
        svc = Service()
        response = AIResponse(
            decision="approve", confidence=-0.1, reasons=["test"], risk_notes=[],
            action="proceed", model_version="v1", prompt_version="p1",
        )
        errors = svc._validate_contract(response)
        assert any(e["field"] == "confidence" and e["error"] == "out_of_range" for e in errors)

    def test_validate_contract_reasons_not_list(self) -> None:
        """Test reasons must be array."""
        svc = Service()
        response = AIResponse(
            decision="approve", confidence=0.8, reasons="not a list", risk_notes=[],
            action="proceed", model_version="v1", prompt_version="p1",
        )
        errors = svc._validate_contract(response)
        assert any(e["field"] == "reasons" and e["error"] == "invalid_type" for e in errors)

    def test_validate_contract_risk_notes_not_list(self) -> None:
        """Test risk_notes must be array."""
        svc = Service()
        response = AIResponse(
            decision="approve", confidence=0.8, reasons=["test"], risk_notes="not a list",
            action="proceed", model_version="v1", prompt_version="p1",
        )
        errors = svc._validate_contract(response)
        assert any(e["field"] == "risk_notes" and e["error"] == "invalid_type" for e in errors)

    def test_validate_contract_invalid_decision(self) -> None:
        """Test invalid decision value is rejected."""
        svc = Service()
        response = AIResponse(
            decision="invalid_decision", confidence=0.8, reasons=["test"], risk_notes=[],
            action="proceed", model_version="v1", prompt_version="p1",
        )
        errors = svc._validate_contract(response)
        assert any(e["field"] == "decision" and e["error"] == "invalid_value" for e in errors)

    def test_validate_contract_valid_decisions(self) -> None:
        """Test all valid decision values."""
        svc = Service()
        for decision in ["approve", "adjust", "restrict", "reject"]:
            response = AIResponse(
                decision=decision, confidence=0.8, reasons=["test"], risk_notes=[],
                action="proceed", model_version="v1", prompt_version="p1",
            )
            errors = svc._validate_contract(response)
            decision_errors = [e for e in errors if e["field"] == "decision"]
            assert len(decision_errors) == 0, f"Valid decision '{decision}' rejected"

    def test_validate_contract_invalid_action(self) -> None:
        """Test invalid action value is rejected."""
        svc = Service()
        response = AIResponse(
            decision="approve", confidence=0.8, reasons=["test"], risk_notes=[],
            action="invalid_action", model_version="v1", prompt_version="p1",
        )
        errors = svc._validate_contract(response)
        assert any(e["field"] == "action" and e["error"] == "invalid_value" for e in errors)

    def test_validate_contract_valid_actions(self) -> None:
        """Test all valid action values."""
        svc = Service()
        for action in ["proceed", "modify", "block", "tighten_risk", "breakeven", "trailing", "hold", "block_entries"]:
            response = AIResponse(
                decision="approve", confidence=0.8, reasons=["test"], risk_notes=[],
                action=action, model_version="v1", prompt_version="p1",
            )
            errors = svc._validate_contract(response)
            action_errors = [e for e in errors if e["field"] == "action"]
            assert len(action_errors) == 0, f"Valid action '{action}' rejected"

    def test_contract_error_has_validation_errors(self) -> None:
        """Test contract errors include validation_errors array."""
        svc = Service()
        
        class BadProvider:
            def generate(self, module, context):
                return AIResponse(
                    decision="invalid", confidence=0.8, reasons=["test"], risk_notes=[],
                    action="proceed", model_version="v1", prompt_version="p1",
                )
        
        import services.ai_orchestrator.service as svc_module
        original = svc_module.get_provider
        svc_module.get_provider = lambda: BadProvider()
        
        try:
            out = svc.run({"module": "candidate_signal_reviewer", "context": {}})
            assert out.status == "contract_error"
            assert "validation_errors" in out.payload
            assert len(out.payload["validation_errors"]) > 0
            # Check structure of validation errors
            for err in out.payload["validation_errors"]:
                assert "field" in err
                assert "error" in err
                assert "message" in err
        finally:
            svc_module.get_provider = original


class TestExceptionHandling:
    """Exception path tests."""

    def test_provider_exception_returns_error_type(self) -> None:
        """Test provider exceptions include error_type."""
        svc = Service()
        
        class FailingProvider:
            def generate(self, module, context):
                raise RuntimeError("Simulated failure")
        
        import services.ai_orchestrator.service as svc_module
        original = svc_module.get_provider
        svc_module.get_provider = lambda: FailingProvider()
        
        try:
            out = svc.run({"module": "candidate_signal_reviewer", "context": {}})
            assert out.status == "error"
            assert "error_type" in out.payload
            assert out.payload["error_type"] == "RuntimeError"
        finally:
            svc_module.get_provider = original

    def test_latency_included_in_all_responses(self) -> None:
        """Test latency is included in all response types."""
        svc = Service()
        
        # Test ok response
        out = svc.run({"module": "candidate_signal_reviewer", "context": {}})
        assert "latency_ms" in out.payload
        
        # Test error response
        class FailingProvider:
            def generate(self, module, context):
                raise RuntimeError("Fail")
        
        import services.ai_orchestrator.service as svc_module
        original = svc_module.get_provider
        svc_module.get_provider = lambda: FailingProvider()
        
        try:
            out = svc.run({"module": "candidate_signal_reviewer", "context": {}})
            assert "latency_ms" in out.payload
            assert isinstance(out.payload["latency_ms"], float)
        finally:
            svc_module.get_provider = original


class TestEdgeCases:
    """Edge case tests."""

    def test_extra_keys_ignored(self) -> None:
        """Test that extra keys in response don't break validation."""
        svc = Service()
        
        response = AIResponse(
            decision="approve", confidence=0.8, reasons=["test"], risk_notes=[],
            action="proceed", model_version="v1", prompt_version="p1",
        )
        response.extra_field = "should be ignored"
        
        errors = svc._validate_contract(response)
        assert len(errors) == 0

    def test_none_values_detected_as_missing(self) -> None:
        """Test that None values are treated as missing."""
        svc = Service()
        
        @dataclass
        class ResponseWithNone:
            decision: str = "approve"
            confidence: float = None
            reasons: list = None
            risk_notes: list = None
            action: str = "proceed"
            model_version: str = "v1"
            prompt_version: str = "p1"
        
        errors = svc._validate_contract(ResponseWithNone())
        missing = [e["field"] for e in errors]
        assert "confidence" in missing
        assert "reasons" in missing
        assert "risk_notes" in missing

    def test_confidence_boundary_values(self) -> None:
        """Test confidence at exact boundaries."""
        svc = Service()
        
        # confidence = 0.0 (valid)
        response = AIResponse(
            decision="approve", confidence=0.0, reasons=["test"], risk_notes=[],
            action="proceed", model_version="v1", prompt_version="p1",
        )
        errors = svc._validate_contract(response)
        confidence_errors = [e for e in errors if e["field"] == "confidence"]
        assert len(confidence_errors) == 0
        
        # confidence = 1.0 (valid)
        response.confidence = 1.0
        errors = svc._validate_contract(response)
        confidence_errors = [e for e in errors if e["field"] == "confidence"]
        assert len(confidence_errors) == 0
