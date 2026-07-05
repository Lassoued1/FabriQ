from __future__ import annotations

import operator
import re
from types import SimpleNamespace
from typing import Annotated, Any

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from .cache import sql_result_cache
from .llm import llm_settings_from_env
from .models import AskResponse, ClarificationOption, OrchestrationStep, ValidationReport
from .semantic_layer import (
    EXAMPLE_BY_INTENT_ID,
    EXAMPLE_QUESTIONS,
    INTENTS,
    extract_query_parameters,
    intent_by_id,
    is_write_request,
    rank_intent_candidates,
    render_intent_sql,
    select_intent_match,
)
from .sql_guard import validate_sql


class FabriqState(TypedDict, total=False):
    question: str
    intent: Any
    intent_match: Any
    routing_strategy: str
    llm_reason: Any
    orchestration: Annotated[list, operator.add]
    sql: Any
    guard: Any
    rows: list
    columns: list
    response: Any
    needs_clarification: bool
    clarification_options: list
    database: Any
    llm_settings: Any
    user_ctx: Any


def make_initial_state(database: Any, question: str, user_ctx: Any = None) -> FabriqState:
    return FabriqState(
        question=question,
        intent=None,
        intent_match=None,
        routing_strategy="deterministic_keywords",
        llm_reason=None,
        orchestration=[],
        sql=None,
        guard=None,
        rows=[],
        columns=[],
        response=None,
        needs_clarification=False,
        clarification_options=[],
        database=database,
        llm_settings=llm_settings_from_env(),
        user_ctx=user_ctx,
    )


# ─── Nodes ────────────────────────────────────────────────────────────────────

def receive_question_node(state: FabriqState) -> dict:
    steps = [_step("receive_question", "done", "Question received by the API.")]
    user_ctx = state.get("user_ctx")
    if user_ctx is not None:
        tenant_id = getattr(user_ctx, "tenant_id", None)
        user_id = getattr(user_ctx, "user_id", None)
        if tenant_id:
            steps.append(
                _step(
                    "tenant_context",
                    "done",
                    f"Tenant: {tenant_id} | User: {user_id}.",
                )
            )
    return {"orchestration": steps}


def route_intent_node(state: FabriqState) -> dict:
    intent_match = select_intent_match(state["question"])
    updates: dict = {"intent_match": intent_match}

    if intent_match.intent is not None:
        updates["intent"] = intent_match.intent
        updates["orchestration"] = [
            _step(
                "route_intent",
                "done",
                f"Deterministic route selected {intent_match.intent.id} with score {intent_match.score}.",
            )
        ]

    return updates


def _after_route_intent(state: FabriqState) -> str:
    if state.get("intent") is not None:
        return "generate_sql"
    # Une demande d'ecriture ne doit jamais atteindre le routeur LLM :
    # clarification directe, sans analyse.
    if is_write_request(state["question"]):
        return "clarify"
    llm_settings = state.get("llm_settings")
    if llm_settings and getattr(llm_settings, "enabled", False):
        return "llm_route"
    return "clarify"


def make_llm_route_node(llm_classifier: Any) -> Any:
    """Return a LangGraph node that calls the injected LLM classifier."""

    def llm_route_node(state: FabriqState) -> dict:
        steps: list[OrchestrationStep] = [
            _step(
                "route_intent",
                "waiting",
                "Deterministic route was uncertain; asking Ollama for an allowed intent.",
            )
        ]
        llm_choice = llm_classifier(state["question"], INTENTS, state["llm_settings"])
        updates: dict = {}

        if llm_choice.intent_id:
            intent = intent_by_id(llm_choice.intent_id)
            updates["intent"] = intent
            updates["routing_strategy"] = "ollama_intent_router"
            updates["llm_reason"] = f"{llm_choice.reason} Confidence: {llm_choice.confidence:.2f}."
            steps.append(
                _step(
                    "route_intent",
                    "done",
                    f"Ollama selected {llm_choice.intent_id} with confidence {llm_choice.confidence:.2f}.",
                )
            )
        else:
            updates["routing_strategy"] = "clarification"
            updates["llm_reason"] = llm_choice.reason
            steps.append(
                _step("route_intent", "skipped", llm_choice.reason or "No allowed intent selected.")
            )

        updates["orchestration"] = steps
        return updates

    return llm_route_node


def _after_llm_route(state: FabriqState) -> str:
    return "generate_sql" if state.get("intent") is not None else "clarify"


def clarify_node(state: FabriqState) -> dict:
    steps: list[OrchestrationStep] = []

    if not any(s.node == "route_intent" for s in state.get("orchestration", [])):
        intent_match = state.get("intent_match")
        matched = (
            ", ".join(intent_match.matched_keywords)
            if intent_match and intent_match.matched_keywords
            else "none"
        )
        score = intent_match.score if intent_match else 0
        steps.append(
            _step(
                "route_intent",
                "skipped",
                f"No supported intent reached threshold. Best score: {score}; matches: {matched}.",
            )
        )

    options = _build_clarification_options(state["question"])
    steps.append(
        _step(
            "clarify",
            "waiting",
            f"A clarification is required; {len(options)} guided options were prepared.",
        )
    )
    steps.append(_step("generate_sql", "skipped", "No SQL is generated without intent."))

    full_orchestration = state.get("orchestration", []) + steps
    llm_settings = state.get("llm_settings")

    response = AskResponse(
        question=state["question"],
        intent=None,
        routing_strategy=state.get("routing_strategy", "deterministic_keywords"),
        llm_provider=llm_settings.provider if llm_settings else "disabled",
        llm_reason=state.get("llm_reason"),
        orchestration=full_orchestration,
        answer="J'ai besoin d'une precision pour relier la question a une metrique industrielle connue.",
        sql=None,
        explanation=(
            "Le MVP couvre pour l'instant les familles marge, rupture, retards,"
            " production, CA, stock, logistique, retours, clients et anomalies."
        ),
        columns=[],
        rows=[],
        chart=None,
        validation=ValidationReport(ok=False, checks=[], blocked=["Intention non reconnue."]),
        needs_clarification=True,
        clarification="Choisissez une piste d'analyse ou reformulez avec une metrique industrielle plus precise.",
        clarification_options=options,
    )

    return {
        "orchestration": steps,
        "clarification_options": options,
        "needs_clarification": True,
        "response": response,
    }


def generate_sql_node(state: FabriqState) -> dict:
    intent = state["intent"]
    database = state["database"]
    params = extract_query_parameters(state["question"])
    rendered, applied = render_intent_sql(intent, database.dialect, params)
    sql = _compact_sql(rendered)

    if applied:
        detail = (
            f"Template SQL selected for {database.dialect}. "
            f"Parametres extraits de la question: {', '.join(applied)}."
        )
    else:
        detail = f"Template SQL selected for {database.dialect}. Parametres par defaut."

    return {
        "sql": sql,
        "orchestration": [_step("generate_sql", "done", detail)],
    }


def validate_sql_node(state: FabriqState) -> dict:
    guard = validate_sql(state["sql"])

    if not guard.ok:
        return {
            "guard": guard,
            "orchestration": [
                _step("validate_sql", "blocked", "SQL guard blocked the query before execution."),
                _step("execute_readonly", "skipped", "Execution skipped."),
            ],
        }

    return {
        "guard": guard,
        "orchestration": [_step("validate_sql", "done", "SQL guard accepted the query.")],
    }


def _after_validate_sql(state: FabriqState) -> str:
    guard = state.get("guard")
    return "execute" if guard and guard.ok else "compose_answer"


def execute_node(state: FabriqState) -> dict:
    database = state["database"]
    sql = state["sql"]

    # Inject tenant filter for authenticated Postgres sessions only.
    user_ctx = state.get("user_ctx")
    tenant_id: str | None = None
    if user_ctx and database.dialect == "postgres":
        tenant_id = getattr(user_ctx, "tenant_id", None)
        if tenant_id:
            sql = inject_tenant_filter(sql, tenant_id)

    # Check cache before hitting the database.
    cache_key = f"{sql}|{tenant_id or ''}"
    cached = sql_result_cache.get(cache_key)
    if cached is not None:
        return {
            "rows": cached["rows"],
            "columns": cached["columns"],
            "orchestration": [
                _step("execute_readonly", "done", f"Cache hit — {len(cached['rows'])} rows.")
            ],
        }

    rows = database.execute_readonly(sql)
    columns = list(rows[0].keys()) if rows else []
    sql_result_cache.set(cache_key, {"rows": rows, "columns": columns})

    return {
        "rows": rows,
        "columns": columns,
        "orchestration": [
            _step(
                "execute_readonly",
                "done",
                f"Read-only execution returned {len(rows)} rows.",
            )
        ],
    }


def compose_answer_node(state: FabriqState) -> dict:
    guard = state.get("guard")
    intent = state.get("intent")
    llm_settings = state.get("llm_settings")
    rows = state.get("rows", [])
    columns = state.get("columns", [])

    compose_step = _step("compose_answer", "done", "Answer, table and chart metadata composed.")
    full_orchestration = state.get("orchestration", []) + [compose_step]

    if guard is None or not guard.ok:
        response = AskResponse(
            question=state["question"],
            intent=intent.id if intent else None,
            routing_strategy=state.get("routing_strategy", "deterministic_keywords"),
            llm_provider=llm_settings.provider if llm_settings else "disabled",
            llm_reason=state.get("llm_reason"),
            orchestration=full_orchestration,
            answer="La requete a ete bloquee avant execution.",
            sql=state.get("sql"),
            explanation="Le garde-fou SQL a detecte une requete non conforme.",
            columns=[],
            rows=[],
            chart=None,
            validation=ValidationReport(
                ok=False,
                checks=guard.checks if guard else [],
                blocked=guard.blocked if guard else ["Garde-fou SQL: erreur inconnue."],
            ),
        )
    else:
        chart = _adjust_chart(intent.chart, rows)
        response = AskResponse(
            question=state["question"],
            intent=intent.id if intent else None,
            routing_strategy=state.get("routing_strategy", "deterministic_keywords"),
            llm_provider=llm_settings.provider if llm_settings else "disabled",
            llm_reason=state.get("llm_reason"),
            orchestration=full_orchestration,
            answer=_summarize(intent.label, rows),
            sql=state.get("sql"),
            explanation=intent.explanation,
            columns=columns,
            rows=rows,
            chart=chart,
            validation=ValidationReport(ok=True, checks=guard.checks, blocked=[]),
        )

    return {
        "orchestration": [compose_step],
        "response": response,
    }


# ─── Graph construction ────────────────────────────────────────────────────────

def build_graph(llm_classifier: Any = None) -> Any:
    """Build and compile the FabriQ LangGraph analysis pipeline."""
    llm_route_node = make_llm_route_node(llm_classifier or _noop_classifier)

    g = StateGraph(FabriqState)

    g.add_node("receive_question", receive_question_node)
    g.add_node("route_intent", route_intent_node)
    g.add_node("llm_route", llm_route_node)
    g.add_node("clarify", clarify_node)
    g.add_node("generate_sql", generate_sql_node)
    g.add_node("validate_sql", validate_sql_node)
    g.add_node("execute", execute_node)
    g.add_node("compose_answer", compose_answer_node)

    g.add_edge(START, "receive_question")
    g.add_edge("receive_question", "route_intent")
    g.add_conditional_edges(
        "route_intent",
        _after_route_intent,
        {"generate_sql": "generate_sql", "llm_route": "llm_route", "clarify": "clarify"},
    )
    g.add_conditional_edges(
        "llm_route",
        _after_llm_route,
        {"generate_sql": "generate_sql", "clarify": "clarify"},
    )
    g.add_edge("clarify", END)
    g.add_edge("generate_sql", "validate_sql")
    g.add_conditional_edges(
        "validate_sql",
        _after_validate_sql,
        {"execute": "execute", "compose_answer": "compose_answer"},
    )
    g.add_edge("execute", "compose_answer")
    g.add_edge("compose_answer", END)

    return g.compile()


# ─── Helpers ──────────────────────────────────────────────────────────────────

_TENANT_TABLES = frozenset({"orders", "customers"})


def inject_tenant_filter(sql: str, tenant_id: str) -> str:
    """Inject a tenant_id WHERE/AND clause for queries referencing tenant-scoped tables.

    Only called for authenticated Postgres sessions — SQLite tests are unaffected.
    The tenant_id value comes from a signed JWT, never from user input.
    """
    lower = sql.lower()
    if not any(re.search(rf"\b{t}\b", lower) for t in _TENANT_TABLES):
        return sql

    # Detect alias for 'orders' (e.g. "FROM orders o" → "o")
    alias_match = re.search(r"\borders\s+(?:as\s+)?([a-z_]\w*)", lower)
    if alias_match and alias_match.group(1) not in ("join", "inner", "left", "right", "on"):
        qualifier = f"{alias_match.group(1)}.tenant_id"
    else:
        qualifier = "orders.tenant_id"

    tenant_clause = f"{qualifier} = '{tenant_id}'"

    where_match = re.search(r"\bWHERE\b", sql, re.IGNORECASE)
    split_match = re.search(r"\b(GROUP BY|ORDER BY|LIMIT)\b", sql, re.IGNORECASE)

    if where_match:
        pos = split_match.start() if split_match else len(sql)
        return sql[:pos] + f"AND {tenant_clause}\n" + sql[pos:]
    else:
        pos = split_match.start() if split_match else len(sql)
        return sql[:pos] + f"WHERE {tenant_clause}\n" + sql[pos:]


_TIME_COLUMN_HINTS = frozenset({
    "mois", "date", "period", "semaine", "annee", "jour",
    "month", "week", "year", "day",
})


def _adjust_chart(chart: Any, rows: list) -> Any:
    """Dynamically adjust chart type based on actual result shape.

    Rules (in priority order):
    - 0 or 1 rows → no chart (not enough data to visualise a trend).
    - x column is time-based and ≥ 4 rows → prefer line/area.
    - 2-3 rows → prefer bar (a 2-point line looks wrong).
    - Fallback to intent's own chart spec.
    """
    if chart is None or not rows:
        return None

    from .models import ChartSpec

    x_col: str = chart.x or ""
    is_time_x = (
        x_col.lower() in _TIME_COLUMN_HINTS
        or any(hint in x_col.lower() for hint in _TIME_COLUMN_HINTS)
    )

    # A line/area with ≤2 points conveys nothing — downgrade to bar.
    if chart.type in ("line", "area") and len(rows) <= 2:
        if len(rows) == 0:
            return None
        return ChartSpec(type="bar", x=chart.x, y=chart.y, title=chart.title)

    # Time column + many rows + still on bar → upgrade to area for trend readability.
    if is_time_x and chart.type == "bar" and len(rows) >= 4:
        return ChartSpec(type="area", x=chart.x, y=chart.y, title=chart.title)

    return chart


def _step(node: str, status: str, detail: str) -> OrchestrationStep:
    return OrchestrationStep(node=node, status=status, detail=detail)


def _compact_sql(sql: str) -> str:
    return "\n".join(line.strip() for line in sql.strip().splitlines() if line.strip())


def _summarize(label: str, rows: list) -> str:
    if not rows:
        return f"{label}: aucune ligne ne correspond aux criteres de l'analyse."
    first = rows[0]
    visible_values = [str(v) for v in first.values() if v is not None][:3]
    return f"{label}: {len(rows)} lignes trouvees. Signal principal: {', '.join(visible_values)}."


def _build_clarification_options(question: str) -> list[ClarificationOption]:
    candidates = rank_intent_candidates(question)
    selected = candidates[:3]

    if not selected:
        selected = [
            candidate
            for example in EXAMPLE_QUESTIONS[:4]
            for candidate in rank_intent_candidates(example)[:1]
        ]

    options: list[ClarificationOption] = []
    seen: set[str] = set()
    for candidate in selected:
        intent = candidate.intent
        if intent.id in seen:
            continue
        seen.add(intent.id)
        matched = ", ".join(candidate.matched_keywords) or "aucun mot-cle direct"
        options.append(
            ClarificationOption(
                intent_id=intent.id,
                label=intent.label,
                question=EXAMPLE_BY_INTENT_ID[intent.id],
                reason=f"Score {candidate.score}; indices detectes: {matched}.",
            )
        )

    return options


def _noop_classifier(*args: Any, **kwargs: Any) -> Any:
    """Returned when no LLM classifier is provided (LLM disabled path)."""
    return SimpleNamespace(
        intent_id=None,
        confidence=0.0,
        reason="No LLM classifier provided.",
        raw_response=None,
        error=None,
    )
