from typing import Any, Literal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500)


class ChartSpec(BaseModel):
    type: Literal["bar", "line", "area", "table"]
    x: str
    y: str
    title: str


class ValidationReport(BaseModel):
    ok: bool
    checks: list[str]
    blocked: list[str] = Field(default_factory=list)


class OrchestrationStep(BaseModel):
    node: str
    status: Literal["done", "blocked", "skipped", "waiting"]
    detail: str


class ClarificationOption(BaseModel):
    intent_id: str
    label: str
    question: str
    reason: str


class AskResponse(BaseModel):
    trace_id: str | None = None
    question: str
    intent: str | None
    routing_strategy: str = "deterministic_keywords"
    llm_provider: str = "disabled"
    llm_reason: str | None = None
    orchestration: list[OrchestrationStep] = Field(default_factory=list)
    answer: str
    sql: str | None
    explanation: str
    columns: list[str]
    rows: list[dict[str, Any]]
    chart: ChartSpec | None
    validation: ValidationReport
    needs_clarification: bool = False
    clarification: str | None = None
    clarification_options: list[ClarificationOption] = Field(default_factory=list)
