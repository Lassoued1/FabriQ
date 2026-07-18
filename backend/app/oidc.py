"""OIDC / SSO optionnel (Keycloak ou tout fournisseur OpenID Connect).

Flux "backend-driven" : le backend redirige vers le fournisseur (authorization
code + PKCE), gere le callback, valide l'id_token via le JWKS du fournisseur,
mappe les claims vers (tenant, role), puis emet le JWT FabriQ habituel. Tout le
pipeline existant (refresh, multi-tenant, audit, desactivation) est reutilise.

Le SSO est desactive par defaut : il s'active quand FABRIQ_OIDC_ISSUER et
FABRIQ_OIDC_CLIENT_ID sont definis. Le login local FABRIQ_USERS reste toujours
disponible.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from jose import JWTError, jwt

# ─── Configuration ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class OidcSettings:
    issuer: str
    client_id: str
    client_secret: str
    redirect_url: str
    frontend_url: str
    # Base interne pour joindre le fournisseur (Docker : http://keycloak:8080/...)
    # quand l'issuer public n'est pas routable depuis le backend. L'issuer des
    # tokens reste valide contre `issuer`.
    internal_base: str

    @property
    def enabled(self) -> bool:
        return bool(self.issuer and self.client_id)


def oidc_settings_from_env() -> OidcSettings:
    issuer = os.environ.get("FABRIQ_OIDC_ISSUER", "").rstrip("/")
    return OidcSettings(
        issuer=issuer,
        client_id=os.environ.get("FABRIQ_OIDC_CLIENT_ID", ""),
        client_secret=os.environ.get("FABRIQ_OIDC_CLIENT_SECRET", ""),
        redirect_url=os.environ.get(
            "FABRIQ_OIDC_REDIRECT_URL", "http://localhost:8000/api/auth/oidc/callback"
        ),
        frontend_url=os.environ.get("FABRIQ_FRONTEND_URL", "http://localhost:5173").rstrip("/"),
        internal_base=os.environ.get("FABRIQ_OIDC_INTERNAL_BASE", "").rstrip("/"),
    )


# ─── Etat anti-CSRF + verifier PKCE (memoire, TTL) ───────────────────────────

_STATE_TTL_SECONDS = 600
_pending: dict[str, tuple[str, float]] = {}
_pending_lock = threading.Lock()


def _remember_state(state: str, verifier: str) -> None:
    now = time.time()
    with _pending_lock:
        expired = [s for s, (_, t) in _pending.items() if now - t > _STATE_TTL_SECONDS]
        for s in expired:
            del _pending[s]
        _pending[state] = (verifier, now)


def _consume_state(state: str) -> str | None:
    with _pending_lock:
        entry = _pending.pop(state, None)
    if entry is None:
        return None
    verifier, created = entry
    if time.time() - created > _STATE_TTL_SECONDS:
        return None
    return verifier


# ─── Decouverte + JWKS (caches) ──────────────────────────────────────────────

_HTTP_TIMEOUT = 10
_cache_lock = threading.Lock()
_discovery_cache: dict[str, dict] = {}
_jwks_cache: dict[str, dict] = {}


def _fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def _provider_base(settings: OidcSettings) -> str:
    return settings.internal_base or settings.issuer


def _discovery(settings: OidcSettings) -> dict:
    base = _provider_base(settings)
    with _cache_lock:
        cached = _discovery_cache.get(base)
    if cached is not None:
        return cached
    doc = _fetch_json(f"{base}/.well-known/openid-configuration")
    with _cache_lock:
        _discovery_cache[base] = doc
    return doc


def _jwks(settings: OidcSettings) -> dict:
    base = _provider_base(settings)
    with _cache_lock:
        cached = _jwks_cache.get(base)
    if cached is not None:
        return cached
    jwks_uri = _discovery(settings)["jwks_uri"]
    if settings.internal_base:
        # La decouverte renvoie des URLs publiques ; les reecrire vers la base interne.
        jwks_uri = jwks_uri.replace(settings.issuer, settings.internal_base, 1)
    keys = _fetch_json(jwks_uri)
    with _cache_lock:
        _jwks_cache[base] = keys
    return keys


def clear_caches() -> None:
    """Pour les tests."""
    with _cache_lock:
        _discovery_cache.clear()
        _jwks_cache.clear()
    with _pending_lock:
        _pending.clear()


# ─── Flux authorization code + PKCE ──────────────────────────────────────────

class OidcError(Exception):
    """Echec du flux OIDC (etat inconnu, echange refuse, id_token invalide)."""


def begin_login(settings: OidcSettings) -> str:
    """Construit l'URL d'autorisation du fournisseur et memorise state+verifier."""
    state = secrets.token_urlsafe(24)
    verifier = secrets.token_urlsafe(48)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
        .rstrip(b"=")
        .decode("ascii")
    )
    _remember_state(state, verifier)
    authorize = _discovery(settings)["authorization_endpoint"]
    if settings.internal_base:
        # L'URL d'autorisation est suivie par le NAVIGATEUR : toujours publique.
        authorize = authorize.replace(settings.internal_base, settings.issuer, 1)
    query = urllib.parse.urlencode(
        {
            "response_type": "code",
            "client_id": settings.client_id,
            "redirect_uri": settings.redirect_url,
            "scope": "openid email profile",
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
    )
    return f"{authorize}?{query}"


def _exchange_code(settings: OidcSettings, code: str, verifier: str) -> dict:
    token_endpoint = _discovery(settings)["token_endpoint"]
    if settings.internal_base:
        token_endpoint = token_endpoint.replace(settings.issuer, settings.internal_base, 1)
    form = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.redirect_url,
        "client_id": settings.client_id,
        "code_verifier": verifier,
    }
    if settings.client_secret:
        form["client_secret"] = settings.client_secret
    data = urllib.parse.urlencode(form).encode("ascii")
    req = urllib.request.Request(
        token_endpoint,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise OidcError(f"Echange du code refuse par le fournisseur ({exc.code}).") from exc
    except urllib.error.URLError as exc:
        raise OidcError("Fournisseur OIDC injoignable pour l'echange du code.") from exc


def _decode_id_token(settings: OidcSettings, id_token: str) -> dict:
    try:
        claims = jwt.decode(
            id_token,
            _jwks(settings),
            algorithms=["RS256"],
            audience=settings.client_id,
            issuer=settings.issuer,
            options={"verify_at_hash": False},
        )
    except JWTError as exc:
        raise OidcError(f"id_token invalide : {exc}") from exc
    return claims


@dataclass(frozen=True)
class SsoIdentity:
    email: str
    tenant_id: str
    role: str


_ALLOWED_ROLES = {"admin", "user", "viewer"}


def complete_login(settings: OidcSettings, state: str, code: str) -> SsoIdentity:
    """Valide state, echange le code, verifie l'id_token et mappe les claims."""
    verifier = _consume_state(state)
    if verifier is None:
        raise OidcError("Etat OIDC inconnu ou expire (rejouer le login).")
    tokens = _exchange_code(settings, code, verifier)
    id_token = tokens.get("id_token")
    if not id_token:
        raise OidcError("Reponse du fournisseur sans id_token.")
    claims = _decode_id_token(settings, id_token)
    email = claims.get("email") or claims.get("preferred_username")
    if not email:
        raise OidcError("id_token sans claim email.")
    tenant_id = claims.get("fabriq_tenant") or "tenant_demo"
    role = claims.get("fabriq_role") or "user"
    if role not in _ALLOWED_ROLES:
        role = "user"
    return SsoIdentity(email=email, tenant_id=tenant_id, role=role)
