from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .agent import answer_question
from .cache import sql_result_cache
from .alerts import (
    AlertRule,
    add_rule,
    delete_rule,
    export_alert_events_csv,
    recent_alert_events,
    rules_for_tenant,
    start_scheduler,
)
from .audit import export_csv, export_xlsx, log_analysis, recent_events
from .auth import UserContext, authenticate_user, create_access_token, get_current_user, list_users, require_admin
from .disabled_users import disable_user, enable_user, list_disabled
from .database import create_database_from_env
from .llm import check_ollama_health, llm_settings_from_env
from .models import AskRequest, AskResponse, LoginRequest, TokenResponse
from .semantic_layer import EXAMPLE_QUESTIONS, semantic_catalog
from .webhooks import (
    EVENT_TYPES,
    WebhookCreate,
    WebhookSubscription,
    add_subscription,
    delete_subscription,
    emit,
    is_safe_webhook_url,
    recent_deliveries,
    send_test,
    subscription_by_id,
    subscriptions_for_tenant,
)

limiter = Limiter(key_func=get_remote_address)

database = create_database_from_env()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    start_scheduler(database)
    yield


_TAGS_METADATA = [
    {"name": "health", "description": "Statut de l'API, de la base de données et du LLM."},
    {"name": "auth", "description": "Authentification JWT — login, token, identité courante."},
    {"name": "analysis", "description": "Analyse NL→SQL : poser une question métier et recevoir une réponse structurée."},
    {"name": "audit", "description": "Journal d'audit des analyses : historique paginé et export CSV."},
    {"name": "catalog", "description": "Catalogue sémantique : intentions, exemples et tables disponibles."},
    {"name": "alerts", "description": "Règles d'alerte planifiées, événements déclenchés et export CSV."},
    {"name": "webhooks", "description": "Webhooks sortants génériques : souscriptions par événement, livraison signée et journal."},
    {"name": "admin", "description": "Administration des utilisateurs (rôle admin requis)."},
]

app = FastAPI(
    title="FabriQ API",
    version="0.11.0",
    description=(
        "FabriQ est un assistant d'analyse industrielle NL→SQL. "
        "Une question en français, une requête SQL sécurisée, "
        "une réponse structurée avec tableau, graphique et explication."
    ),
    openapi_tags=_TAGS_METADATA,
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

# CORSMiddleware added last so it is outermost (LIFO processing order).
# Demo locale : tout port localhost est accepte (dev Vite, e2e Playwright).
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CurrentUser = Annotated[UserContext, Depends(get_current_user)]
AdminUser = Annotated[UserContext, Depends(require_admin)]


# ─── Public endpoints ─────────────────────────────────────────────────────────

@app.get("/api/health", tags=["health"], summary="Statut global de l'API")
def health() -> dict[str, object]:
    llm_settings = llm_settings_from_env()
    llm_health = check_ollama_health(llm_settings)

    db_ok = False
    db_latency_ms: float | None = None
    try:
        db_latency_ms = round(database.ping(), 2)
        db_ok = True
    except Exception:
        pass

    return {
        "status": "ok" if db_ok else "degraded",
        "service": "fabriq-api",
        "database": database.dialect,
        "db_ok": db_ok,
        "db_latency_ms": db_latency_ms,
        "cache_entries": sql_result_cache.size(),
        "version": app.version,
        "llm_provider": llm_settings.provider,
        "llm_model": llm_settings.model if llm_settings.enabled else "none",
        "llm_mode": "optional-router" if llm_settings.enabled else "disabled",
        "llm_status": llm_health.status,
        "llm_reachable": llm_health.reachable,
        "llm_model_available": llm_health.model_available,
        "llm_latency_ms": llm_health.latency_ms,
        "llm_error": llm_health.error,
    }


@app.post("/api/auth/login", tags=["auth"], summary="Authentification — retourne un token JWT Bearer")
@limiter.limit("10/minute")
def login(request: Request, payload: LoginRequest) -> TokenResponse:
    user = authenticate_user(payload.email, payload.password)
    if user is None:
        # Signal de sécurité : une tentative ratée sur un compte connu notifie
        # le tenant de ce compte (email inconnu -> aucun tenant, on ignore).
        known = next((u for u in list_users() if u.email == payload.email), None)
        if known is not None:
            emit(
                "auth.login_failed",
                known.tenant_id,
                {"email": payload.email, "ip": get_remote_address(request)},
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(
        data={"sub": user.email, "tenant_id": user.tenant_id, "role": user.role},
        expires_delta=timedelta(minutes=60),
    )
    return TokenResponse(access_token=token)


# ─── Protected endpoints ──────────────────────────────────────────────────────

@app.post("/api/auth/refresh", tags=["auth"], summary="Renouveler le token JWT sans re-saisir le mot de passe")
def refresh_token(current_user: CurrentUser) -> TokenResponse:
    token = create_access_token(
        data={"sub": current_user.email, "tenant_id": current_user.tenant_id, "role": current_user.role},
        expires_delta=timedelta(minutes=60),
    )
    return TokenResponse(access_token=token)


@app.get("/api/auth/me", tags=["auth"], summary="Identité de l'utilisateur connecté")
def me(current_user: CurrentUser) -> dict[str, str]:
    return {
        "email": current_user.email,
        "tenant_id": current_user.tenant_id,
        "role": current_user.role,
    }


@app.get("/api/examples", tags=["catalog"], summary="Questions d'exemple par intention")
def examples(current_user: CurrentUser) -> dict[str, list[str]]:
    return {"questions": EXAMPLE_QUESTIONS}


@app.get("/api/catalog", tags=["catalog"], summary="Catalogue sémantique complet (intentions, tables, colonnes)")
def catalog(current_user: CurrentUser) -> dict[str, object]:
    return semantic_catalog()


@app.post(
    "/api/ask",
    tags=["analysis"],
    summary="Analyser une question métier en langage naturel",
    response_description="Réponse structurée avec SQL, tableau, graphique et orchestration.",
)
@limiter.limit("30/minute")
def ask(request: Request, payload: AskRequest, current_user: CurrentUser) -> AskResponse:
    response = answer_question(database, payload.question, user_ctx=current_user)
    response.trace_id = log_analysis(response, user_ctx=current_user)

    if response.needs_clarification or not response.validation.ok:
        emit(
            "question.blocked",
            current_user.tenant_id,
            {
                "question": response.question,
                "needs_clarification": response.needs_clarification,
                "blocked": response.validation.blocked,
                "trace_id": response.trace_id,
            },
        )
    else:
        emit(
            "question.answered",
            current_user.tenant_id,
            {
                "intent": response.intent,
                "sql": response.sql,
                "row_count": len(response.rows),
                "chart_type": response.chart.type if response.chart else None,
                "trace_id": response.trace_id,
            },
        )
    return response


@app.get("/api/audit/recent", tags=["audit"], summary="Journal d'audit paginé et filtrable")
def audit_recent(
    current_user: CurrentUser,
    page: int = 1,
    limit: int = 20,
    intent: str | None = None,
    validation_ok: bool | None = None,
) -> dict[str, object]:
    events, total = recent_events(
        page=page,
        limit=limit,
        tenant_id=current_user.tenant_id,
        intent=intent or None,
        validation_ok=validation_ok,
    )
    return {"events": events, "total": total, "page": page, "limit": limit}


@app.get("/api/audit/export", tags=["audit"], summary="Export CSV du journal d'audit (filtré par tenant)")
def audit_export(current_user: CurrentUser) -> Response:
    csv_data = export_csv(tenant_id=current_user.tenant_id)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit.csv"},
    )


@app.get("/api/audit/export.xlsx", tags=["audit"], summary="Export Excel (xlsx) du journal d'audit")
def audit_export_xlsx(current_user: CurrentUser) -> Response:
    xlsx_data = export_xlsx(tenant_id=current_user.tenant_id)
    return Response(
        content=xlsx_data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=audit.xlsx"},
    )


# ─── Admin endpoints ──────────────────────────────────────────────────────────

@app.get("/api/admin/users", tags=["admin"], summary="Lister tous les utilisateurs avec leur statut (admin)")
def admin_list_users(current_user: AdminUser) -> dict[str, list]:
    disabled = set(list_disabled())
    return {
        "users": [
            {"email": u.email, "tenant_id": u.tenant_id, "role": u.role, "disabled": u.email in disabled}
            for u in list_users()
        ]
    }


@app.post("/api/admin/users/{email}/disable", tags=["admin"], summary="Désactiver un compte utilisateur", responses={404: {"description": "Utilisateur introuvable."}, 400: {"description": "Auto-désactivation interdite."}})
def admin_disable_user(email: str, current_user: AdminUser) -> dict[str, object]:
    all_emails = {u.email for u in list_users()}
    if email not in all_emails:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")
    if email == current_user.email:
        raise HTTPException(status_code=400, detail="Impossible de se désactiver soi-même.")
    disable_user(email)
    return {"email": email, "disabled": True}


@app.post("/api/admin/users/{email}/enable", tags=["admin"], summary="Réactiver un compte utilisateur", responses={404: {"description": "Utilisateur introuvable."}})
def admin_enable_user(email: str, current_user: AdminUser) -> dict[str, object]:
    all_emails = {u.email for u in list_users()}
    if email not in all_emails:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")
    enable_user(email)
    return {"email": email, "disabled": False}


# ─── Alerts endpoints ─────────────────────────────────────────────────────────

@app.get("/api/alerts", tags=["alerts"], summary="Lister les règles d'alerte du tenant")
def list_alerts(current_user: CurrentUser) -> dict[str, list]:
    return {"rules": [r.model_dump() for r in rules_for_tenant(current_user.tenant_id)]}


@app.post("/api/alerts", tags=["alerts"], summary="Créer une règle d'alerte planifiée")
def create_alert(payload: AlertRule, current_user: CurrentUser) -> dict[str, object]:
    payload.tenant_id = current_user.tenant_id
    rule = add_rule(payload)
    return {"rule": rule.model_dump()}


@app.delete("/api/alerts/{rule_id}", tags=["alerts"], summary="Supprimer une règle d'alerte", responses={404: {"description": "Règle introuvable."}})
def remove_alert(rule_id: str, current_user: CurrentUser) -> dict[str, bool]:
    deleted = delete_rule(rule_id, current_user.tenant_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Règle introuvable.")
    return {"deleted": True}


@app.get("/api/alerts/events", tags=["alerts"], summary="Événements d'alerte déclenchés (paginé)")
def alert_events(
    current_user: CurrentUser,
    page: int = 1,
    limit: int = 20,
) -> dict[str, object]:
    events, total = recent_alert_events(current_user.tenant_id, limit=limit, page=page)
    return {"events": events, "total": total, "page": page, "limit": limit}


@app.get("/api/alerts/events/export", tags=["alerts"], summary="Export CSV des événements d'alerte")
def alert_events_export(current_user: CurrentUser) -> Response:
    csv_data = export_alert_events_csv(tenant_id=current_user.tenant_id)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=alert_events.csv"},
    )


# ─── Webhooks endpoints ───────────────────────────────────────────────────────

@app.get("/api/webhooks/event-types", tags=["webhooks"], summary="Types d'événements auxquels s'abonner")
def webhook_event_types(current_user: CurrentUser) -> dict[str, list[str]]:
    return {"event_types": list(EVENT_TYPES)}


@app.get("/api/webhooks", tags=["webhooks"], summary="Lister les webhooks du tenant")
def list_webhooks(current_user: CurrentUser) -> dict[str, list]:
    return {"webhooks": [s.model_dump() for s in subscriptions_for_tenant(current_user.tenant_id)]}


@app.post("/api/webhooks", tags=["webhooks"], summary="Créer un webhook", responses={400: {"description": "URL non autorisée (SSRF)."}, 422: {"description": "Type d'événement inconnu."}})
def create_webhook(payload: WebhookCreate, current_user: CurrentUser) -> dict[str, object]:
    unknown = [e for e in payload.events if e not in EVENT_TYPES]
    if unknown:
        raise HTTPException(status_code=422, detail=f"Types d'événement inconnus : {unknown}")
    if not is_safe_webhook_url(payload.url):
        raise HTTPException(status_code=400, detail="URL non autorisée (schéma non HTTP(S) ou adresse interne).")
    subscription = add_subscription(
        WebhookSubscription(
            tenant_id=current_user.tenant_id,
            name=payload.name,
            url=payload.url,
            events=payload.events,
        )
    )
    return {"webhook": subscription.model_dump()}


@app.delete("/api/webhooks/{webhook_id}", tags=["webhooks"], summary="Supprimer un webhook", responses={404: {"description": "Webhook introuvable."}})
def remove_webhook(webhook_id: str, current_user: CurrentUser) -> dict[str, bool]:
    if not delete_subscription(webhook_id, current_user.tenant_id):
        raise HTTPException(status_code=404, detail="Webhook introuvable.")
    return {"deleted": True}


@app.post("/api/webhooks/{webhook_id}/test", tags=["webhooks"], summary="Envoyer un événement ping de test", responses={404: {"description": "Webhook introuvable."}})
def test_webhook(webhook_id: str, current_user: CurrentUser) -> dict[str, object]:
    subscription = subscription_by_id(webhook_id, current_user.tenant_id)
    if subscription is None:
        raise HTTPException(status_code=404, detail="Webhook introuvable.")
    attempts = send_test(subscription)
    delivered = any(a["ok"] for a in attempts)
    return {"delivered": delivered, "attempts": attempts}


@app.get("/api/webhooks/{webhook_id}/deliveries", tags=["webhooks"], summary="Journal de livraison d'un webhook (paginé)", responses={404: {"description": "Webhook introuvable."}})
def webhook_deliveries(
    webhook_id: str,
    current_user: CurrentUser,
    page: int = 1,
    limit: int = 20,
) -> dict[str, object]:
    if subscription_by_id(webhook_id, current_user.tenant_id) is None:
        raise HTTPException(status_code=404, detail="Webhook introuvable.")
    deliveries, total = recent_deliveries(webhook_id, current_user.tenant_id, limit=limit, page=page)
    return {"deliveries": deliveries, "total": total, "page": page, "limit": limit}
