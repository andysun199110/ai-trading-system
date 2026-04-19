"""AI Orchestrator Contract Tests - Type/Boundary/Exception coverage."""
from dataclasses import dataclass

import pytest

from services.ai_orchestrator.service import (
    REQUIRED_FIELDS,
    ContractValidationError,
    Service,
)
from services.ai_orchestrator.provider import AIResponse, MockProvider


class TestAIOutputContract:
    """Test AI output contract validation."""

    def test_ai_output_contract_basic(self) -> None:
        """Test basic contract with valid module."""
        out = Service().run({"module": "candidate_signal_reviewer", "context": {}})
        assert out.status == "ok"
        response = out.payload["response"]
        assert set(response.keys()) == REQUIRED_FIELDS

    def test_ai_output_contract_all_modules(self) -> None:
        """Test contract for all supported modules."""
        modules = [
            "candidate_signal_reviewer",
            "event_analyst",
            "position_supervisor_ai",
            "weekly_review_ai",
        ]
        for module in modules:
            out = Service().run({"module": module, "context": {}})
            assert out.status == "ok", f"Module {module} failed"
            assert set(out.payload["response"].keys()) == REQUIRED_FIELDS

    def test_unsupported_module_blocked(self) -> None:
        """Test that unsupported modules are blocked with details."""
        out = Service().run({"module": "invalid_module", "context": {}})
        assert out.status == "blocked"
        assert out.payload["reason"] == "unsupported_module"
        assert out.payload["module"] == "invalid_module"
        assert "valid_modules" in out.payload


class TestContractValidationErrors:
    """Test field-level contract validation errors."""

    def test_missing_required_fields(self) -> None:
        """Test detection of missing required fields."""
        svc = Service()
        
        # Create a response with missing fields
        @dataclass
        class IncompleteResponse:
            decision: str = "approve"
            # Missing: confidence, reasons, risk_notes, action, model_version, prompt_version
        
        errors = svc._validate_contract(IncompleteResponse())
        assert len(errors) == 6
        missing_fields = [e["field"] for e in errors]
        assert "confidence" in missing_fields
        assert "reasons" in missing_fields

    def test_confidence_out_of_range(self) -> None:
        """Test confidence value boundary validation."""
        svc = Service()
        
        # Confidence > 1
        response = AIResponse(
            decision="approve",
            confidence=1.5,  # Invalid
            reasons=["test"],
            risk_notes=[],
            action="proceed",
            model_version="test-v1",
            prompt_version="test-p1",
        )
        errors = svc._validate_contract(response)
        assert any(e["field"] == "confidence" and e["error"] == "out_of_range" for e in errors)
        
        # Confidence < 0
        response.confidence = -0.1
        errors = svc._validate_contract(response)
        assert any(e["field"] == "confidence" and e["error"] == "out_of_range" for e in errors)

    def test_confidence_invalid_type(self) -> None:
        """Test confidence type validation."""
        svc = Service()
        
        response = AIResponse(
            decision="approve",
            confidence="high",  # Invalid type
            reasons=["test"],
            risk_notes=[],
            action="proceed",
            model_version="test-v1",
            prompt_version="test-p1",
        )
        errors = svc._validate_contract(response)
        assert any(e["field"] == "confidence" and e["error"] == "invalid_type" for e in errors)

    def test_reasons_invalid_type(self) -> None:
        """Test reasons field type validation."""
        svc = Service()
        
        response = AIResponse(
            decision="approve",
            confidence=0.8,
            reasons="not a list",  # Invalid type
            risk_notes=[],
            action="proceed",
            model_version="test-v1",
            prompt_version="test-p1",
        )
        errors = svc._validate_contract(response)
        assert any(e["field"] == "reasons" and e["error"] == "invalid_type" for e in errors)

    def test_risk_notes_invalid_type(self) -> None:
        """Test risk_notes field type validation."""
        svc = Service()
        
        response = AIResponse(
            decision="approve",
            confidence=0.8,
            reasons=["test"],
            risk_notes="not a list",  # Invalid type
            action="proceed",
            model_version="test-v1",
            prompt_version="test-p1",
        )
        errors = svc._validate_contract(response)
        assert any(e["field"] == "risk_notes" and e["error"] == "invalid_type" for e in errors)

    def test_invalid_decision_value(self) -> None:
        """Test decision field value validation."""
        svc = Service()
        
        response = AIResponse(
            decision="invalid_decision",  # Not in valid set
            confidence=0.8,
            reasons=["test"],
            risk_notes=[],
            action="proceed",
            model_version="test-v1",
            prompt_version="test-p1",
        )
        errors = svc._validate_contract(response)
        assert any(e["field"] == "decision" and e["error"] == "invalid_value" for e in errors)

    def test_valid_decisions(self) -> None:
        """Test all valid decision values."""
        svc = Service()
        valid_decisions = ["approve", "adjust", "restrict", "reject"]
        
        for decision in valid_decisions:
            response = AIResponse(
                decision=decision,
                confidence=0.8,
                reasons=["test"],
                risk_notes=[],
                action="proceed",
                model_version="test-v1",
                prompt_version="test-p1",
            )
            errors = svc._validate_contract(response)
            decision_errors = [e for e in errors if e["field"] == "decision"]
            assert len(decision_errors) == 0, f"Valid decision '{decision}' was rejected"

    def test_invalid_action_value(self) -> None:
        """Test action field value validation."""
        svc = Service()
        
        response = AIResponse(
            decision="approve",
            confidence=0.8,
            reasons=["test"],
            risk_notes=[],
            action="invalid_action",  # Not in valid set
            model_version="test-v1",
            prompt_version="test-p1",
        )
        errors = svc._validate_contract(response)
        assert any(e["field"] == "action" and e["error"] == "invalid_value" for e in errors)

    def test_valid_actions(self) -> None:
        """Test all valid action values."""
        svc = Service()
        valid_actions = ["proceed", "modify", "block", "tighten_risk", "breakeven", "trailing", "hold", "block_entries"]
        
        for action in valid_actions:
            response = AIResponse(
                decision="approve",
                confidence=0.8,
                reasons=["test"],
                risk_notes=[],
                action=action,
                model_version="test-v1",
                prompt_version="test-p1",
            )
            errors = svc._validate_contract(response)
            action_errors = [e for e in errors if e["field"] == "action"]
            assert len(action_errors) == 0, f"Valid action '{action}' was rejected"

    def test_contract_error_response_format(self) -> None:
        """Test that contract errors return proper format."""
        # This tests the full service.run() path with validation errors
        svc = Service()
        
        # Mock a provider that returns invalid response
        class BadProvider:
            def generate(self, module, context):
                return AIResponse(
                    decision="invalid",  # Will fail validation
                    confidence=0.8,
                    reasons=["test"],
                    risk_notes=[],
                    action="proceed",
                    model_version="test-v1",
                    prompt_version="test-p1",
                )
        
        # Temporarily replace provider
        import services.ai_orchestrator.service as svc_module
        original_get_provider = svc_module.get_provider
        svc_module.get_provider = lambda: BadProvider()
        
        try:
            out = svc.run({"module": "candidate_signal_reviewer", "context": {}})
            assert out.status == "contract_error"
            assert "validation_errors" in out.payload
        finally:
            svc_module.get_provider = original_get_provider


class TestExceptionPaths:
    """Test exception handling paths."""

    def test_provider_exception_handled(self) -> None:
        """Test that provider exceptions are caught and returned."""
        svc = Service()
        
        class FailingProvider:
            def generate(self, module, context):
                raise RuntimeError("Simulated provider failure")
        
        import services.ai_orchestrator.service as svc_module
        original_get_provider = svc_module.get_provider
        svc_module.get_provider = lambda: FailingProvider()
        
        try:
            out = svc.run({"module": "candidate_signal_reviewer", "context": {}})
            assert out.status == "error"
            assert "error" in out.payload
            assert "error_type" in out.payload
            assert out.payload["error_type"] == "RuntimeError"
        finally:
            svc_module.get_provider = original_get_provider

    def test_latency_included_in_error(self) -> None:
        """Test that latency is included even in error responses."""
        svc = Service()
        
        class FailingProvider:
            def generate(self, module, context):
                raise RuntimeError("Fail")
        
        import services.ai_orchestrator.service as svc_module
        original_get_provider = svc_module.get_provider
        svc_module.get_provider = lambda: FailingProvider()
        
        try:
            out = svc.run({"module": "candidate_signal_reviewer", "context": {}})
            assert "latency_ms" in out.payload
            assert isinstance(out.payload["latency_ms"], float)
        finally:
            svc_module.get_provider = original_get_provider


class TestMockProviderBehavior:
    """Test MockProvider behavior for different modules."""

    def test_mock_event_analyst_blocking(self) -> None:
        """Test MockProvider blocks when event_block_active is True."""
        provider = MockProvider()
        response = provider.generate("event_analyst", {"event_block_active": True})
        assert response.decision == "restrict"
        assert response.action == "block_entries"

    def test_mock_position_supervisor_adjust(self) -> None:
        """Test MockProvider adjusts when state_change is True."""
        provider = MockProvider()
        response = provider.generate("position_supervisor_ai", {"state_change": True})
        assert response.decision == "adjust"
        assert response.action == "tighten_risk"

    def test_mock_default_approve(self) -> None:
        """Test MockProvider defaults to approve."""
        provider = MockProvider()
        response = provider.generate("candidate_signal_reviewer", {})
        assert response.decision == "approve"
        assert response.action == "proceed"
