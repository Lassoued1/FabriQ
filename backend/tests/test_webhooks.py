# -*- coding: utf-8 -*-
"""Tests unitaires du module de webhooks sortants generiques (lot A)."""

from __future__ import annotations

import tempfile
import unittest
import urllib.error
from pathlib import Path

from app import webhooks
from app.webhooks import (
    WebhookSubscription,
    add_subscription,
    delete_subscription,
    deliver,
    emit,
    is_safe_webhook_url,
    recent_deliveries,
    send_test,
    sign_payload,
    subscription_by_id,
    subscriptions_for_tenant,
)


def _sub(tenant="tenant_demo", events=("question.answered",), enabled=True, url="https://hooks.example/x"):
    return WebhookSubscription(
        tenant_id=tenant,
        name="test",
        url=url,
        events=list(events),
        secret="s3cr3t",
        enabled=enabled,
    )


class WebhookTestBase(unittest.TestCase):
    """Isole les fichiers de persistance dans un dossier temporaire."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        self._orig_subs = webhooks.SUBSCRIPTIONS_FILE
        self._orig_deliv = webhooks.DELIVERIES_FILE
        self._orig_post = webhooks._http_post
        webhooks.SUBSCRIPTIONS_FILE = tmp / "subscriptions.json"
        webhooks.DELIVERIES_FILE = tmp / "webhook_deliveries.jsonl"

    def tearDown(self) -> None:
        webhooks.SUBSCRIPTIONS_FILE = self._orig_subs
        webhooks.DELIVERIES_FILE = self._orig_deliv
        webhooks._http_post = self._orig_post
        self._tmp.cleanup()


class PersistenceTests(WebhookTestBase):
    def test_add_and_load_roundtrip(self) -> None:
        created = add_subscription(_sub())
        loaded = subscriptions_for_tenant("tenant_demo")
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].id, created.id)

    def test_tenant_isolation(self) -> None:
        add_subscription(_sub(tenant="tenant_demo"))
        add_subscription(_sub(tenant="tenant_acme"))
        self.assertEqual(len(subscriptions_for_tenant("tenant_demo")), 1)
        self.assertIsNone(subscription_by_id(subscriptions_for_tenant("tenant_acme")[0].id, "tenant_demo"))

    def test_delete_scoped_by_tenant(self) -> None:
        created = add_subscription(_sub(tenant="tenant_acme"))
        self.assertFalse(delete_subscription(created.id, "tenant_demo"))
        self.assertTrue(delete_subscription(created.id, "tenant_acme"))
        self.assertEqual(subscriptions_for_tenant("tenant_acme"), [])


class SignatureTests(WebhookTestBase):
    def test_signature_is_deterministic_and_prefixed(self) -> None:
        body = b'{"hello":"world"}'
        first = sign_payload("s3cr3t", body)
        second = sign_payload("s3cr3t", body)
        self.assertEqual(first, second)
        self.assertTrue(first.startswith("sha256="))

    def test_signature_changes_with_secret(self) -> None:
        body = b'{"hello":"world"}'
        self.assertNotEqual(sign_payload("a", body), sign_payload("b", body))


class SsrfGuardTests(WebhookTestBase):
    def test_rejects_internal_and_bad_schemes(self) -> None:
        for url in (
            "http://localhost/hook",
            "http://127.0.0.1/hook",
            "http://10.0.0.5/hook",
            "http://192.168.1.10/hook",
            "http://169.254.1.1/hook",
            "ftp://example.com/hook",
            "not-a-url",
        ):
            with self.subTest(url=url):
                self.assertFalse(is_safe_webhook_url(url))

    def test_accepts_public_ip_literal(self) -> None:
        # IP litterale publique -> pas de resolution DNS, test hors-ligne.
        self.assertTrue(is_safe_webhook_url("https://93.184.216.34/hook"))


class DeliveryTests(WebhookTestBase):
    def test_success_logs_single_attempt(self) -> None:
        webhooks._http_post = lambda *a, **k: 200
        sub = _sub()
        attempts = deliver(sub, webhooks.WebhookEvent(type="ping", tenant_id=sub.tenant_id, data={}))
        self.assertEqual(len(attempts), 1)
        self.assertTrue(attempts[0]["ok"])
        logged, total = recent_deliveries(sub.id, sub.tenant_id)
        self.assertEqual(total, 1)

    def test_retries_then_succeeds(self) -> None:
        calls = {"n": 0}

        def flaky(*a, **k):
            calls["n"] += 1
            return 500 if calls["n"] == 1 else 200

        webhooks._http_post = flaky
        sub = _sub()
        attempts = deliver(
            sub,
            webhooks.WebhookEvent(type="ping", tenant_id=sub.tenant_id, data={}),
            delays=(0, 0, 0),
        )
        self.assertEqual(len(attempts), 2)
        self.assertFalse(attempts[0]["ok"])
        self.assertTrue(attempts[1]["ok"])

    def test_network_error_exhausts_retries(self) -> None:
        def boom(*a, **k):
            raise urllib.error.URLError("connection refused")

        webhooks._http_post = boom
        sub = _sub()
        attempts = deliver(
            sub,
            webhooks.WebhookEvent(type="ping", tenant_id=sub.tenant_id, data={}),
            delays=(0, 0, 0),
        )
        self.assertEqual(len(attempts), 3)
        self.assertTrue(all(not a["ok"] for a in attempts))
        self.assertIn("connection refused", attempts[0]["error"])

    def test_signature_header_is_sent(self) -> None:
        captured: dict = {}

        def spy(url, data, headers, timeout):
            captured["data"] = data
            captured["headers"] = headers
            return 200

        webhooks._http_post = spy
        sub = _sub()
        event = webhooks.WebhookEvent(type="ping", tenant_id=sub.tenant_id, data={"a": 1})
        deliver(sub, event)
        expected = sign_payload(sub.secret, captured["data"])
        self.assertEqual(captured["headers"]["X-FabriQ-Signature"], expected)
        self.assertEqual(captured["headers"]["X-FabriQ-Event"], "ping")


class EmitTests(WebhookTestBase):
    def test_emit_delivers_only_to_enabled_subscribed(self) -> None:
        posted: list[str] = []
        webhooks._http_post = lambda url, *a, **k: posted.append(url) or 200

        add_subscription(_sub(events=("question.answered",), url="https://hooks.example/yes"))
        add_subscription(_sub(events=("alert.fired",), url="https://hooks.example/othertype"))
        add_subscription(_sub(events=("question.answered",), enabled=False, url="https://hooks.example/disabled"))

        emit("question.answered", "tenant_demo", {"intent": "revenue_trend"}, sync=True)

        self.assertEqual(posted, ["https://hooks.example/yes"])

    def test_emit_is_tenant_scoped(self) -> None:
        posted: list[str] = []
        webhooks._http_post = lambda url, *a, **k: posted.append(url) or 200
        add_subscription(_sub(tenant="tenant_acme", url="https://hooks.example/acme"))

        emit("question.answered", "tenant_demo", {}, sync=True)

        self.assertEqual(posted, [])


class SendTestTests(WebhookTestBase):
    def test_send_test_emits_ping_delivery(self) -> None:
        webhooks._http_post = lambda *a, **k: 200
        sub = add_subscription(_sub())
        attempts = send_test(sub)
        self.assertEqual(len(attempts), 1)
        self.assertEqual(attempts[0]["event_type"], "ping")
        logged, total = recent_deliveries(sub.id, sub.tenant_id)
        self.assertEqual(total, 1)


class EndpointTests(WebhookTestBase):
    """Tests des endpoints /api/webhooks via TestClient (auth surchargée)."""

    SAFE_URL = "https://93.184.216.34/hook"  # IP litterale publique : pas de DNS

    def setUp(self) -> None:
        super().setUp()
        from fastapi.testclient import TestClient
        from app.auth import UserContext, get_current_user
        from app.main import app

        self.app = app
        self._get_current_user = get_current_user
        self.user = UserContext(user_id="u", email="admin@fabriq.io", tenant_id="tenant_demo", role="admin")
        app.dependency_overrides[get_current_user] = lambda: self.user
        webhooks._http_post = lambda *a, **k: 200
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.pop(self._get_current_user, None)
        super().tearDown()

    def _create(self, **overrides) -> dict:
        body = {"name": "hook", "url": self.SAFE_URL, "events": ["question.answered"]}
        body.update(overrides)
        return self.client.post("/api/webhooks", json=body)

    def test_event_types_endpoint(self) -> None:
        resp = self.client.get("/api/webhooks/event-types")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("question.answered", resp.json()["event_types"])

    def test_create_forces_tenant_and_generates_secret(self) -> None:
        resp = self._create()
        self.assertEqual(resp.status_code, 200)
        hook = resp.json()["webhook"]
        self.assertEqual(hook["tenant_id"], "tenant_demo")
        self.assertTrue(hook["secret"])
        self.assertTrue(hook["id"])

    def test_create_rejects_unknown_event(self) -> None:
        resp = self._create(events=["not.a.real.event"])
        self.assertEqual(resp.status_code, 422)

    def test_create_rejects_internal_url(self) -> None:
        resp = self._create(url="http://localhost/hook")
        self.assertEqual(resp.status_code, 400)

    def test_list_and_delete_roundtrip(self) -> None:
        hook_id = self._create().json()["webhook"]["id"]
        listed = self.client.get("/api/webhooks").json()["webhooks"]
        self.assertEqual([h["id"] for h in listed], [hook_id])

        self.assertEqual(self.client.delete(f"/api/webhooks/{hook_id}").status_code, 200)
        self.assertEqual(self.client.delete(f"/api/webhooks/{hook_id}").status_code, 404)

    def test_test_endpoint_and_deliveries(self) -> None:
        hook_id = self._create().json()["webhook"]["id"]
        test_resp = self.client.post(f"/api/webhooks/{hook_id}/test")
        self.assertEqual(test_resp.status_code, 200)
        self.assertTrue(test_resp.json()["delivered"])

        deliveries = self.client.get(f"/api/webhooks/{hook_id}/deliveries").json()
        self.assertEqual(deliveries["total"], 1)
        self.assertEqual(deliveries["deliveries"][0]["event_type"], "ping")

    def test_deliveries_unknown_webhook_is_404(self) -> None:
        self.assertEqual(self.client.get("/api/webhooks/deadbeef/deliveries").status_code, 404)

    def test_cross_tenant_isolation(self) -> None:
        hook_id = self._create().json()["webhook"]["id"]
        # Bascule vers un autre tenant : il ne voit ni ne supprime le webhook.
        self.user.tenant_id = "tenant_acme"
        self.assertEqual(self.client.get("/api/webhooks").json()["webhooks"], [])
        self.assertEqual(self.client.delete(f"/api/webhooks/{hook_id}").status_code, 404)


if __name__ == "__main__":
    unittest.main()
