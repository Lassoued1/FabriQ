"""Webhooks sortants generiques.

Emetteur d'evenements decouple des alertes : une souscription enregistre une
URL, une liste de types d'evenements auxquels elle s'abonne et un secret HMAC.
Quand un evenement est emis (`emit`), il est livre a chaque souscription du
meme tenant abonnee a ce type, avec signature HMAC-SHA256, reessais a backoff
et journalisation de chaque tentative.

La couche HTTP passe par `_http_post`, volontairement isolee pour etre
monkeypatchee dans les tests (aucun reseau requis).
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field

WEBHOOKS_DIR = Path(__file__).resolve().parents[1] / "webhooks"
SUBSCRIPTIONS_FILE = WEBHOOKS_DIR / "subscriptions.json"
DELIVERIES_FILE = Path(__file__).resolve().parents[1] / "logs" / "webhook_deliveries.jsonl"

# Types d'evenements metier auxquels une souscription peut s'abonner.
EVENT_TYPES: tuple[str, ...] = (
    "question.answered",
    "question.blocked",
    "alert.fired",
    "auth.login_failed",
)

# Reessais : delais (en secondes) avant chaque tentative. La 1re est immediate.
RETRY_DELAYS: tuple[int, ...] = (0, 5, 30)
HTTP_TIMEOUT_SECONDS = 5

_delivery_lock = threading.Lock()


# ─── Modeles ──────────────────────────────────────────────────────────────────

class WebhookSubscription(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    tenant_id: str
    name: str
    url: str
    events: list[str]
    secret: str = Field(default_factory=lambda: uuid4().hex)
    enabled: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class WebhookCreate(BaseModel):
    """Charge utile de creation exposee a l'API.

    Le client ne fixe que le nom, l'URL et les types d'evenements ; l'id, le
    secret HMAC, le tenant et la date sont generes ou imposes cote serveur.
    """

    name: str = Field(..., min_length=1, max_length=120)
    url: str = Field(..., min_length=1, max_length=500)
    events: list[str] = Field(..., min_length=1)


class WebhookEvent(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    type: str
    tenant_id: str
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    data: dict


# ─── Persistence des souscriptions ────────────────────────────────────────────

def load_subscriptions() -> list[WebhookSubscription]:
    if not SUBSCRIPTIONS_FILE.exists():
        return []
    try:
        raw = json.loads(SUBSCRIPTIONS_FILE.read_text(encoding="utf-8"))
        return [WebhookSubscription(**s) for s in raw]
    except Exception:
        return []


def save_subscriptions(subscriptions: list[WebhookSubscription]) -> None:
    SUBSCRIPTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SUBSCRIPTIONS_FILE.write_text(
        json.dumps([s.model_dump() for s in subscriptions], ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def subscriptions_for_tenant(tenant_id: str) -> list[WebhookSubscription]:
    return [s for s in load_subscriptions() if s.tenant_id == tenant_id]


def add_subscription(subscription: WebhookSubscription) -> WebhookSubscription:
    subscriptions = load_subscriptions()
    subscriptions.append(subscription)
    save_subscriptions(subscriptions)
    return subscription


def delete_subscription(subscription_id: str, tenant_id: str) -> bool:
    subscriptions = load_subscriptions()
    kept = [s for s in subscriptions if not (s.id == subscription_id and s.tenant_id == tenant_id)]
    if len(kept) == len(subscriptions):
        return False
    save_subscriptions(kept)
    return True


def subscription_by_id(subscription_id: str, tenant_id: str) -> WebhookSubscription | None:
    return next(
        (s for s in load_subscriptions() if s.id == subscription_id and s.tenant_id == tenant_id),
        None,
    )


# ─── Journal de livraison ─────────────────────────────────────────────────────

def _append_delivery(entry: dict) -> None:
    with _delivery_lock:
        DELIVERIES_FILE.parent.mkdir(parents=True, exist_ok=True)
        with DELIVERIES_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=True) + "\n")


def recent_deliveries(
    webhook_id: str,
    tenant_id: str,
    limit: int = 20,
    page: int = 1,
) -> tuple[list[dict], int]:
    """Return (deliveries, total) for one webhook, newest-first, paginated."""
    if not DELIVERIES_FILE.exists():
        return [], 0

    parsed: list[dict] = []
    for line in reversed(DELIVERIES_FILE.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except Exception:
            continue
        if entry.get("webhook_id") == webhook_id and entry.get("tenant_id") == tenant_id:
            parsed.append(entry)

    total = len(parsed)
    offset = (page - 1) * limit
    return parsed[offset : offset + limit], total


# ─── Signature ────────────────────────────────────────────────────────────────

def sign_payload(secret: str, body: bytes) -> str:
    """HMAC-SHA256 du corps brut, prefixe 'sha256=' (convention Stripe/GitHub)."""
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


# ─── Garde SSRF ───────────────────────────────────────────────────────────────

def is_safe_webhook_url(url: str) -> bool:
    """Rejette les URLs non HTTP(S) et celles resolvant vers une IP interne.

    Defense anti-SSRF : une souscription ne doit pas pouvoir faire poster le
    serveur vers loopback, reseaux prives, link-local ou adresses reservees.
    """
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        return False
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False
    try:
        infos = socket.getaddrinfo(parsed.hostname, None)
    except Exception:
        return False
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            return False
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return False
    return True


# ─── Livraison ────────────────────────────────────────────────────────────────

def _http_post(url: str, data: bytes, headers: dict[str, str], timeout: int) -> int:
    """POST le corps et retourne le code de statut HTTP.

    Isole pour etre monkeypatchee dans les tests. Les statuts d'erreur (4xx/5xx)
    sont retournes tels quels ; seules les erreurs reseau (URLError, timeout)
    remontent en exception.
    """
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            return int(resp.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)


def _attempt_delivery(sub: WebhookSubscription, event: WebhookEvent, attempt: int) -> dict:
    body = event.model_dump_json().encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "X-FabriQ-Event": event.type,
        "X-FabriQ-Delivery": uuid4().hex,
        "X-FabriQ-Signature": sign_payload(sub.secret, body),
    }
    entry: dict = {
        "webhook_id": sub.id,
        "event_id": event.id,
        "event_type": event.type,
        "tenant_id": sub.tenant_id,
        "attempt": attempt,
        "delivered_at": datetime.now(UTC).isoformat(),
    }
    try:
        status = _http_post(sub.url, body, headers, HTTP_TIMEOUT_SECONDS)
        entry.update(status_code=status, ok=200 <= status < 300, error=None)
    except Exception as exc:  # noqa: BLE001 — best-effort, jamais de crash
        entry.update(status_code=None, ok=False, error=str(exc))
    return entry


def deliver(
    sub: WebhookSubscription,
    event: WebhookEvent,
    delays: tuple[int, ...] = RETRY_DELAYS,
) -> list[dict]:
    """Livre l'evenement avec reessais a backoff, journalise chaque tentative.

    S'arrete a la premiere reponse 2xx. Retourne la liste des tentatives.
    """
    attempts: list[dict] = []
    for index, delay in enumerate(delays, start=1):
        if delay:
            time.sleep(delay)
        entry = _attempt_delivery(sub, event, index)
        _append_delivery(entry)
        attempts.append(entry)
        if entry["ok"]:
            break
    return attempts


def _matching_subscriptions(tenant_id: str, event_type: str) -> list[WebhookSubscription]:
    return [
        s
        for s in subscriptions_for_tenant(tenant_id)
        if s.enabled and event_type in s.events
    ]


def emit(event_type: str, tenant_id: str, data: dict, *, sync: bool = False) -> WebhookEvent:
    """Emet un evenement vers les souscriptions abonnees du tenant.

    Par defaut, chaque livraison part dans un thread daemon pour ne jamais
    bloquer l'appelant (ex. `/api/ask`). `sync=True` livre en ligne — utilise
    par les tests et le endpoint de test.
    """
    event = WebhookEvent(type=event_type, tenant_id=tenant_id, data=data)
    for sub in _matching_subscriptions(tenant_id, event_type):
        if sync:
            deliver(sub, event)
        else:
            threading.Thread(target=deliver, args=(sub, event), daemon=True).start()
    return event


def send_test(sub: WebhookSubscription) -> list[dict]:
    """Livre un evenement `ping` synthetique a une souscription (bouton Tester)."""
    event = WebhookEvent(
        type="ping",
        tenant_id=sub.tenant_id,
        data={"message": "FabriQ webhook test", "webhook_id": sub.id},
    )
    return deliver(sub, event)
