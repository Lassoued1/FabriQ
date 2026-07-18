# -*- coding: utf-8 -*-
"""Tests unitaires du SSO OIDC optionnel (v0.14) — entierement hors ligne.

La decouverte, le JWKS et l'echange de code sont mockes ; l'id_token est signe
RS256 avec une cle generee dans le test, ce qui exerce la vraie validation de
signature de python-jose.
"""

from __future__ import annotations

import os
import time
import unittest
import urllib.parse
from unittest import mock

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwk, jwt

from app import oidc
from app.oidc import (
    OidcError,
    OidcSettings,
    begin_login,
    complete_login,
    oidc_settings_from_env,
)

ISSUER = "https://sso.example/realms/fabriq"
CLIENT_ID = "fabriq-backend"

_SETTINGS = OidcSettings(
    issuer=ISSUER,
    client_id=CLIENT_ID,
    client_secret="secret",
    redirect_url="http://localhost:8000/api/auth/oidc/callback",
    frontend_url="http://localhost:5173",
    internal_base="",
)

_DISCOVERY = {
    "authorization_endpoint": f"{ISSUER}/protocol/openid-connect/auth",
    "token_endpoint": f"{ISSUER}/protocol/openid-connect/token",
    "jwks_uri": f"{ISSUER}/protocol/openid-connect/certs",
}


def _generate_keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")
    public_jwk = jwk.construct(public_pem, algorithm="RS256").to_dict()
    public_jwk["kid"] = "test-key"
    return private_pem, {"keys": [public_jwk]}


_PRIVATE_PEM, _JWKS = _generate_keypair()


def _make_id_token(claims_override: dict | None = None, **jwt_kwargs) -> str:
    now = int(time.time())
    claims = {
        "iss": ISSUER,
        "aud": CLIENT_ID,
        "sub": "user-123",
        "email": "sso.user@example.com",
        "exp": now + 300,
        "iat": now,
    }
    claims.update(claims_override or {})
    return jwt.encode(claims, _PRIVATE_PEM, algorithm="RS256", headers={"kid": "test-key"}, **jwt_kwargs)


class OidcTestBase(unittest.TestCase):
    def setUp(self) -> None:
        oidc.clear_caches()
        self._patches = [
            mock.patch.object(oidc, "_discovery", return_value=_DISCOVERY),
            mock.patch.object(oidc, "_jwks", return_value=_JWKS),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self) -> None:
        for p in self._patches:
            p.stop()
        oidc.clear_caches()


class SettingsTests(unittest.TestCase):
    def test_disabled_by_default(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("FABRIQ_OIDC_ISSUER", None)
            os.environ.pop("FABRIQ_OIDC_CLIENT_ID", None)
            self.assertFalse(oidc_settings_from_env().enabled)

    def test_enabled_with_issuer_and_client(self) -> None:
        env = {"FABRIQ_OIDC_ISSUER": ISSUER + "/", "FABRIQ_OIDC_CLIENT_ID": CLIENT_ID}
        with mock.patch.dict(os.environ, env):
            settings = oidc_settings_from_env()
            self.assertTrue(settings.enabled)
            self.assertEqual(settings.issuer, ISSUER)  # slash final retire


class BeginLoginTests(OidcTestBase):
    def test_authorize_url_contains_pkce_and_state(self) -> None:
        url = begin_login(_SETTINGS)
        parsed = urllib.parse.urlparse(url)
        query = dict(urllib.parse.parse_qsl(parsed.query))
        self.assertTrue(url.startswith(_DISCOVERY["authorization_endpoint"]))
        self.assertEqual(query["response_type"], "code")
        self.assertEqual(query["client_id"], CLIENT_ID)
        self.assertEqual(query["code_challenge_method"], "S256")
        self.assertIn("state", query)
        self.assertIn("code_challenge", query)
        self.assertIn("openid", query["scope"])

    def test_each_login_gets_a_fresh_state(self) -> None:
        q1 = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(begin_login(_SETTINGS)).query))
        q2 = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(begin_login(_SETTINGS)).query))
        self.assertNotEqual(q1["state"], q2["state"])


class CompleteLoginTests(OidcTestBase):
    def _state_from_login(self) -> str:
        url = begin_login(_SETTINGS)
        return dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))["state"]

    def test_happy_path_maps_claims(self) -> None:
        state = self._state_from_login()
        token = _make_id_token({"fabriq_tenant": "tenant_acme", "fabriq_role": "admin"})
        with mock.patch.object(oidc, "_exchange_code", return_value={"id_token": token}):
            identity = complete_login(_SETTINGS, state=state, code="abc")
        self.assertEqual(identity.email, "sso.user@example.com")
        self.assertEqual(identity.tenant_id, "tenant_acme")
        self.assertEqual(identity.role, "admin")

    def test_defaults_without_custom_claims(self) -> None:
        state = self._state_from_login()
        with mock.patch.object(oidc, "_exchange_code", return_value={"id_token": _make_id_token()}):
            identity = complete_login(_SETTINGS, state=state, code="abc")
        self.assertEqual(identity.tenant_id, "tenant_demo")
        self.assertEqual(identity.role, "user")

    def test_unknown_role_falls_back_to_user(self) -> None:
        state = self._state_from_login()
        token = _make_id_token({"fabriq_role": "superuser"})
        with mock.patch.object(oidc, "_exchange_code", return_value={"id_token": token}):
            identity = complete_login(_SETTINGS, state=state, code="abc")
        self.assertEqual(identity.role, "user")

    def test_unknown_state_rejected(self) -> None:
        with self.assertRaises(OidcError):
            complete_login(_SETTINGS, state="never-issued", code="abc")

    def test_state_cannot_be_replayed(self) -> None:
        state = self._state_from_login()
        with mock.patch.object(oidc, "_exchange_code", return_value={"id_token": _make_id_token()}):
            complete_login(_SETTINGS, state=state, code="abc")
            with self.assertRaises(OidcError):
                complete_login(_SETTINGS, state=state, code="abc")

    def test_wrong_issuer_rejected(self) -> None:
        state = self._state_from_login()
        token = _make_id_token({"iss": "https://evil.example"})
        with mock.patch.object(oidc, "_exchange_code", return_value={"id_token": token}):
            with self.assertRaises(OidcError):
                complete_login(_SETTINGS, state=state, code="abc")

    def test_wrong_audience_rejected(self) -> None:
        state = self._state_from_login()
        token = _make_id_token({"aud": "some-other-client"})
        with mock.patch.object(oidc, "_exchange_code", return_value={"id_token": token}):
            with self.assertRaises(OidcError):
                complete_login(_SETTINGS, state=state, code="abc")

    def test_expired_token_rejected(self) -> None:
        state = self._state_from_login()
        token = _make_id_token({"exp": int(time.time()) - 60})
        with mock.patch.object(oidc, "_exchange_code", return_value={"id_token": token}):
            with self.assertRaises(OidcError):
                complete_login(_SETTINGS, state=state, code="abc")

    def test_missing_email_rejected(self) -> None:
        state = self._state_from_login()
        token = _make_id_token({"email": None})
        with mock.patch.object(oidc, "_exchange_code", return_value={"id_token": token}):
            with self.assertRaises(OidcError):
                complete_login(_SETTINGS, state=state, code="abc")

    def test_response_without_id_token_rejected(self) -> None:
        state = self._state_from_login()
        with mock.patch.object(oidc, "_exchange_code", return_value={"access_token": "x"}):
            with self.assertRaises(OidcError):
                complete_login(_SETTINGS, state=state, code="abc")


class SsoJwtPipelineTests(unittest.TestCase):
    """Le JWT FabriQ emis au callback traverse get_current_user et refresh."""

    def setUp(self) -> None:
        os.environ.setdefault("FABRIQ_JWT_SECRET", "test-secret")

    def _client(self):
        from fastapi.testclient import TestClient
        from app.main import app
        return TestClient(app)

    def _sso_token(self) -> str:
        from datetime import timedelta
        from app.auth import create_access_token
        return create_access_token(
            data={
                "sub": "sso.user@example.com",
                "tenant_id": "tenant_acme",
                "role": "user",
                "auth": "oidc",
            },
            expires_delta=timedelta(minutes=5),
        )

    def test_sso_user_not_in_env_is_accepted(self) -> None:
        client = self._client()
        res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {self._sso_token()}"})
        self.assertEqual(res.status_code, 200)
        payload = res.json()
        self.assertEqual(payload["email"], "sso.user@example.com")
        self.assertEqual(payload["tenant_id"], "tenant_acme")

    def test_refresh_preserves_oidc_marker(self) -> None:
        from app.auth import decode_access_token
        client = self._client()
        res = client.post("/api/auth/refresh", headers={"Authorization": f"Bearer {self._sso_token()}"})
        self.assertEqual(res.status_code, 200)
        refreshed = res.json()["access_token"]
        payload = decode_access_token(refreshed)
        self.assertEqual(payload["auth"], "oidc")
        self.assertEqual(payload["tenant_id"], "tenant_acme")

    def test_oidc_login_endpoint_404_when_disabled(self) -> None:
        for var in ("FABRIQ_OIDC_ISSUER", "FABRIQ_OIDC_CLIENT_ID"):
            os.environ.pop(var, None)
        client = self._client()
        res = client.get("/api/auth/oidc/login", follow_redirects=False)
        self.assertEqual(res.status_code, 404)

    def test_health_exposes_oidc_flag(self) -> None:
        for var in ("FABRIQ_OIDC_ISSUER", "FABRIQ_OIDC_CLIENT_ID"):
            os.environ.pop(var, None)
        client = self._client()
        payload = client.get("/api/health").json()
        self.assertIn("oidc_enabled", payload)
        self.assertFalse(payload["oidc_enabled"])


if __name__ == "__main__":
    unittest.main()
