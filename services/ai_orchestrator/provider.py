"""AI Provider abstraction with DeepSeek integration."""
from __future__ import annotations

import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import httpx

from shared.config.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class AIResponse:
    """Standardized AI response with contract validation."""
    decision: str
    confidence: float
    reasons: list[str]
    risk_notes: list[str]
    action: str
    model_version: str
    prompt_version: str
    latency_ms: float = 0.0
    provider: str = "unknown"


class AIProvider(ABC):
    """Abstract base class for AI providers."""
    
    @abstractmethod
    def generate(self, module: str, context: dict[str, Any]) -> AIResponse:
        """Generate AI response for given module and context."""
        pass


class MockProvider(AIProvider):
    """Mock provider for development/testing."""
    
    def generate(self, module: str, context: dict[str, Any]) -> AIResponse:
        decision = "approve"
        action = "proceed"
        
        if module == "event_analyst" and context.get("event_block_active"):
            decision, action = "restrict", "block_entries"
        if module == "position_supervisor_ai" and context.get("state_change"):
            decision, action = "adjust", "tighten_risk"
        
        return AIResponse(
            decision=decision,
            confidence=0.74,
            reasons=[f"module={module}", "mock_provider"],
            risk_notes=["no_minutely_deep_scan", "xauusd_only"],
            action=action,
            model_version=context.get("model_version", "mock-v1"),
            prompt_version=context.get("prompt_version", "mock-p1"),
            latency_ms=0.1,
            provider="mock"
        )


class DeepSeekProvider(AIProvider):
    """DeepSeek AI provider with strict JSON contract."""
    
    REQUIRED_FIELDS = {"decision", "confidence", "reasons", "risk_notes", "action", "model_version", "prompt_version"}
    
    def __init__(self):
        self.settings = get_settings()
        self.api_base = self.settings.deepseek_api_base
        self.api_key = self.settings.deepseek_api_key
        self.timeout_ms = self.settings.ai_timeout_ms
        self.max_retries = self.settings.ai_max_retries
    
    def generate(self, module: str, context: dict[str, Any]) -> AIResponse:
        """Generate response from DeepSeek with retry logic."""
        prompt = self._build_prompt(module, context)
        
        for attempt in range(self.max_retries):
            try:
                start = time.perf_counter()
                response = self._call_api(prompt)
                latency_ms = round((time.perf_counter() - start) * 1000, 3)
                
                result = self._parse_response(response, module, context, latency_ms)
                logger.info(f"DeepSeek call success: module={module}, latency={latency_ms}ms, status=ok")
                return result
                
            except httpx.TimeoutException as e:
                logger.warning(f"DeepSeek timeout (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    raise
            except httpx.HTTPStatusError as e:
                logger.warning(f"DeepSeek HTTP error (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    raise
            except Exception as e:
                logger.warning(f"DeepSeek unexpected error (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    raise
            
            time.sleep(0.5 * (attempt + 1))  # Exponential backoff
        
        # Fallback to mock if all retries fail
        logger.error(f"DeepSeek all retries failed, falling back to mock for module={module}")
        return MockProvider().generate(module, context)
    
    def _build_prompt(self, module: str, context: dict[str, Any]) -> str:
        """Build structured prompt for AI module."""
        prompts = {
            "candidate_signal_reviewer": f"""You are a trading signal reviewer. Review this XAUUSD signal candidate and return strict JSON.

Signal Context:
{json.dumps(context, indent=2)}

Return JSON with exact fields: decision (approve|adjust|restrict|reject), confidence (0-1), reasons (array), risk_notes (array), action (proceed|modify|block), model_version, prompt_version.

Constraints: XAUUSD only, no minute-by-minute deep re-analysis, stage2 strategy.""",
            
            "event_analyst": f"""You are an economic event analyst. Assess event impact on XAUUSD trading.

Event Context:
{json.dumps(context, indent=2)}

Return JSON with: decision, confidence, reasons, risk_notes, action, model_version, prompt_version.

Focus on hard impact events, entry restrictions during windows.""",
            
            "position_supervisor_ai": f"""You are a position supervisor AI. Monitor open positions and recommend actions.

Position Context:
{json.dumps(context, indent=2)}

Return JSON with: decision, confidence, reasons, risk_notes, action, model_version, prompt_version.

Actions: breakeven, trailing, tighten_risk, hold.""",
            
            "weekly_review_ai": f"""You are a weekly review optimizer. Analyze past week performance and propose improvements.

Weekly Context:
{json.dumps(context, indent=2)}

Return JSON with: decision, confidence, reasons, risk_notes, action, model_version, prompt_version.

Proposals only, never auto-deploy to live.""",
        }
        return prompts.get(module, f"Module: {module}\nContext: {json.dumps(context)}")
    
    def _call_api(self, prompt: str) -> str:
        """Call DeepSeek API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 500
        }
        
        with httpx.Client(timeout=self.timeout_ms / 1000.0) as client:
            response = client.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
    
    def _parse_response(self, content: str, module: str, context: dict[str, Any], latency_ms: float) -> AIResponse:
        """Parse and validate AI response."""
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_str = content.strip()
            if json_str.startswith("```json"):
                json_str = json_str[7:]
            if json_str.endswith("```"):
                json_str = json_str[:-3]
            
            data = json.loads(json_str.strip())
            
            # Validate contract
            if set(data.keys()) != self.REQUIRED_FIELDS:
                raise ValueError(f"Invalid response fields: {set(data.keys())}")
            
            if not isinstance(data["reasons"], list) or not isinstance(data["risk_notes"], list):
                raise ValueError("reasons and risk_notes must be arrays")
            
            if not isinstance(data["confidence"], (float, int)) or not 0 <= data["confidence"] <= 1:
                raise ValueError(f"Invalid confidence: {data['confidence']}")
            
            return AIResponse(
                decision=data["decision"],
                confidence=float(data["confidence"]),
                reasons=data["reasons"],
                risk_notes=data["risk_notes"],
                action=data["action"],
                model_version=data["model_version"],
                prompt_version=data["prompt_version"],
                latency_ms=latency_ms,
                provider="deepseek"
            )
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse DeepSeek response: {e}")
            raise


def get_provider() -> AIProvider:
    """Factory function to get configured AI provider."""
    settings = get_settings()
    provider_type = settings.ai_provider.lower()
    
    if provider_type == "deepseek":
        if not settings.deepseek_api_key:
            logger.warning("DeepSeek provider selected but no API key configured, falling back to mock")
            return MockProvider()
        return DeepSeekProvider()
    
    return MockProvider()
