from __future__ import annotations

import json
import os
import re
from time import perf_counter
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .semantic_layer import IntentDefinition


@dataclass(frozen=True)
class LlmSettings:
    provider: str
    ollama_url: str
    model: str
    timeout_seconds: float

    @property
    def enabled(self) -> bool:
        return self.provider == "ollama"


@dataclass(frozen=True)
class LlmIntentChoice:
    intent_id: str | None
    confidence: float
    reason: str
    raw_response: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class LlmHealth:
    status: str
    reachable: bool
    model_available: bool | None
    latency_ms: int | None = None
    error: str | None = None


def llm_settings_from_env() -> LlmSettings:
    provider = os.getenv("FABRIQ_LLM_PROVIDER", "disabled").strip().lower()
    if provider not in {"disabled", "ollama"}:
        provider = "disabled"

    timeout_raw = os.getenv("FABRIQ_LLM_TIMEOUT_SECONDS", "60")
    try:
        timeout_seconds = max(0.5, min(float(timeout_raw), 60.0))
    except ValueError:
        timeout_seconds = 60.0

    return LlmSettings(
        provider=provider,
        ollama_url=os.getenv("FABRIQ_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/"),
        model=os.getenv("FABRIQ_OLLAMA_MODEL", "llama3.1"),
        timeout_seconds=timeout_seconds,
    )


def check_ollama_health(settings: LlmSettings, timeout_seconds: float = 0.35) -> LlmHealth:
    if not settings.enabled:
        return LlmHealth(status="disabled", reachable=False, model_available=None)

    timeout = max(0.05, min(timeout_seconds, settings.timeout_seconds))
    started_at = perf_counter()

    try:
        request = Request(f"{settings.ollama_url}/api/tags", method="GET")
        with urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return LlmHealth(
            status="unreachable",
            reachable=False,
            model_available=None,
            latency_ms=_elapsed_ms(started_at),
            error=str(exc),
        )

    model_available = _model_is_available(body, settings.model)
    return LlmHealth(
        status="ready" if model_available else "model_missing",
        reachable=True,
        model_available=model_available,
        latency_ms=_elapsed_ms(started_at),
    )


def classify_intent_with_ollama(
    question: str,
    intents: tuple[IntentDefinition, ...],
    settings: LlmSettings,
) -> LlmIntentChoice:
    if not settings.enabled:
        return LlmIntentChoice(intent_id=None, confidence=0.0, reason="LLM disabled.")

    allowed_ids = {intent.id for intent in intents}
    prompt = _build_intent_prompt(question, intents)
    payload = {
        "model": settings.model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0},
    }

    try:
        request = Request(
            f"{settings.ollama_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=settings.timeout_seconds) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return LlmIntentChoice(
            intent_id=None,
            confidence=0.0,
            reason="Ollama unavailable; deterministic fallback kept control.",
            error=str(exc),
        )

    raw_response = str(body.get("response", ""))
    parsed = _extract_json_object(raw_response)
    intent_id = str(parsed.get("intent_id", "")).strip() if parsed else ""
    confidence = _coerce_confidence(parsed.get("confidence") if parsed else None)
    reason = str(parsed.get("reason", "")).strip() if parsed else ""

    if intent_id not in allowed_ids:
        return LlmIntentChoice(
            intent_id=None,
            confidence=confidence,
            reason=reason or "Ollama returned an unknown intent.",
            raw_response=raw_response,
        )

    if confidence < 0.55:
        return LlmIntentChoice(
            intent_id=None,
            confidence=confidence,
            reason=reason or "Ollama confidence is too low.",
            raw_response=raw_response,
        )

    return LlmIntentChoice(
        intent_id=intent_id,
        confidence=confidence,
        reason=reason or "Ollama selected an allowed intent.",
        raw_response=raw_response,
    )


def _build_intent_prompt(question: str, intents: tuple[IntentDefinition, ...]) -> str:
    intent_catalog = "\n".join(
        f"- {intent.id}: {intent.label}. {intent.description} "
        f"Keywords: {', '.join(intent.keywords)}"
        for intent in intents
    )
    return f"""
You are an intent router for FabriQ, an industrial analytics assistant.
Select exactly one intent id from the allowed catalog, or null if no intent matches.
You must not write SQL. You only classify the user's question.

Allowed intents:
{intent_catalog}

User question:
{question}

Return strict JSON only with this shape:
{{"intent_id":"supplier_delays","confidence":0.92,"reason":"short reason"}}

Use null for intent_id when the question is not covered.
""".strip()


def _extract_json_object(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", value, flags=re.DOTALL)
    if not match:
        return {}

    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}

    return parsed if isinstance(parsed, dict) else {}


def _coerce_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0

    return max(0.0, min(confidence, 1.0))


def _elapsed_ms(started_at: float) -> int:
    return max(0, round((perf_counter() - started_at) * 1000))


def _model_is_available(payload: dict[str, Any], model: str) -> bool:
    models = payload.get("models", [])
    if not isinstance(models, list):
        return False

    expected = model if ":" in model else f"{model}:latest"
    aliases = {model, expected}
    for item in models:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", ""))
        if name in aliases:
            return True

    return False
