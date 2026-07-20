"""Stub de fournisseur OIDC — fixture E2E pour le flux SSO, sans Keycloak.

Sert aux tests Playwright (e2e/sso.spec.ts) : la CI le demarre a cote d'un
backend configure avec FABRIQ_OIDC_* pointant dessus, puis deroule le parcours
SSO complet dans un vrai navigateur.

Implemente le strict necessaire du protocole :
- document de decouverte OpenID Connect ;
- endpoint d'autorisation avec page de login factice (un bouton « Continuer ») ;
- endpoint token qui VERIFIE reellement le PKCE (S256 du code_verifier compare
  au code_challenge memorise) et le client_secret ;
- JWKS avec une cle RSA generee au demarrage — l'id_token emis est reellement
  signe RS256, donc la validation de signature de `app/oidc.py` est exercee.

Dependances : cryptography et python-jose, deja presentes dans requirements.txt.

Usage : python scripts/oidc_stub.py   (port via FABRIQ_OIDC_STUB_PORT, defaut 8180)
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwk, jwt

PORT = int(os.environ.get("FABRIQ_OIDC_STUB_PORT", "8180"))
ISSUER = f"http://localhost:{PORT}/realms/fabriq"
CLIENT_ID = os.environ.get("FABRIQ_OIDC_STUB_CLIENT_ID", "fabriq-backend")
CLIENT_SECRET = os.environ.get("FABRIQ_OIDC_STUB_CLIENT_SECRET", "fabriq-oidc-demo-secret")

# Identite emise pour tout login reussi (page factice auto-validee).
USER_EMAIL = "sso.demo@fabriq.io"
USER_TENANT = "tenant_demo"
USER_ROLE = "admin"

_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PRIVATE_PEM = _key.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption(),
).decode()
PUBLIC_PEM = _key.public_key().public_bytes(
    serialization.Encoding.PEM,
    serialization.PublicFormat.SubjectPublicKeyInfo,
).decode()
PUBLIC_JWK = jwk.construct(PUBLIC_PEM, algorithm="RS256").to_dict()
PUBLIC_JWK["kid"] = "stub-key"

# code d'autorisation -> code_challenge attendu au token endpoint
_codes: dict[str, str] = {}


class Handler(BaseHTTPRequestHandler):
    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 (API http.server)
        url = urlparse(self.path)
        if url.path == "/realms/fabriq/.well-known/openid-configuration":
            self._json({
                "issuer": ISSUER,
                "authorization_endpoint": f"{ISSUER}/protocol/openid-connect/auth",
                "token_endpoint": f"{ISSUER}/protocol/openid-connect/token",
                "jwks_uri": f"{ISSUER}/protocol/openid-connect/certs",
            })
        elif url.path == "/realms/fabriq/protocol/openid-connect/certs":
            self._json({"keys": [PUBLIC_JWK]})
        elif url.path == "/realms/fabriq/protocol/openid-connect/auth":
            q = {k: v[0] for k, v in parse_qs(url.query).items()}
            if q.get("client_id") != CLIENT_ID or q.get("code_challenge_method") != "S256":
                self._json({"error": "invalid_request"}, 400)
                return
            code = secrets.token_urlsafe(16)
            _codes[code] = q["code_challenge"]
            target = f"{q['redirect_uri']}?code={code}&state={q['state']}"
            html = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<title>Stub SSO — FabriQ</title></head>
<body style="font-family:sans-serif;display:grid;place-items:center;height:100vh">
<div style="text-align:center">
<h1>Fournisseur SSO (stub)</h1>
<p>Connexion en tant que <strong>{USER_EMAIL}</strong></p>
<a id="login" href="{target}" style="display:inline-block;padding:12px 24px;background:#1f6feb;color:#fff;border-radius:8px;text-decoration:none">Continuer</a>
</div></body></html>"""
            body = html.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self._json({"error": "not_found"}, 404)

    def do_POST(self) -> None:  # noqa: N802 (API http.server)
        url = urlparse(self.path)
        if url.path != "/realms/fabriq/protocol/openid-connect/token":
            self._json({"error": "not_found"}, 404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        form = {k: v[0] for k, v in parse_qs(self.rfile.read(length).decode()).items()}
        expected_challenge = _codes.pop(form.get("code", ""), None)
        if expected_challenge is None:
            self._json({"error": "invalid_grant"}, 400)
            return
        # Verification PKCE reelle : S256(code_verifier) doit matcher le challenge.
        actual = base64.urlsafe_b64encode(
            hashlib.sha256(form.get("code_verifier", "").encode()).digest()
        ).rstrip(b"=").decode()
        if actual != expected_challenge:
            self._json({"error": "invalid_pkce"}, 400)
            return
        if form.get("client_secret") != CLIENT_SECRET:
            self._json({"error": "invalid_client"}, 401)
            return
        now = int(time.time())
        id_token = jwt.encode(
            {
                "iss": ISSUER,
                "aud": CLIENT_ID,
                "sub": "stub-user-1",
                "email": USER_EMAIL,
                "fabriq_tenant": USER_TENANT,
                "fabriq_role": USER_ROLE,
                "iat": now,
                "exp": now + 300,
            },
            PRIVATE_PEM,
            algorithm="RS256",
            headers={"kid": "stub-key"},
        )
        self._json({"access_token": "stub-access", "id_token": id_token, "token_type": "Bearer"})

    def log_message(self, fmt: str, *args: object) -> None:
        print("[oidc-stub]", fmt % args, flush=True)


if __name__ == "__main__":
    print(f"Stub OIDC pret sur {ISSUER}", flush=True)
    # ThreadingHTTPServer obligatoire : Chromium ouvre des connexions
    # speculatives (preconnect) qui bloqueraient un serveur mono-thread
    # pendant que le backend appelle le token endpoint.
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
