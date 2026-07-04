import io
import unittest
from pathlib import Path
import json
from unittest.mock import patch

from app.agent import answer_question
from app.audit import export_csv
from app.auth import UserContext, get_current_user
from app.database import SQLiteDatabase
from app.graph import inject_tenant_filter
from app.llm import LlmSettings, check_ollama_health, llm_settings_from_env
from app.semantic_layer import INTENTS, semantic_catalog
from app.sql_guard import validate_sql


def _test_user() -> UserContext:
    return UserContext(user_id="test", email="test@test.com", tenant_id="tenant_test", role="admin")


class AgentTest(unittest.TestCase):
    def setUp(self) -> None:
        self.env_patcher = patch.dict("os.environ", {}, clear=True)
        self.env_patcher.start()
        self.database = SQLiteDatabase()

    def tearDown(self) -> None:
        self.env_patcher.stop()

    def test_known_question_returns_rows_and_sql(self) -> None:
        response = answer_question(self.database, "Quels fournisseurs ont ete le plus souvent en retard ?")

        self.assertEqual(response.intent, "supplier_delays")
        self.assertEqual(response.routing_strategy, "deterministic_keywords")
        self.assertEqual(response.llm_provider, "disabled")
        self.assertTrue(response.validation.ok)
        self.assertIsNotNone(response.sql)
        self.assertGreater(len(response.rows), 0)
        self.assertEqual(response.clarification_options, [])
        self.assertEqual(response.orchestration[-1].node, "compose_answer")
        self.assertEqual(response.orchestration[-1].status, "done")

    def test_unknown_question_asks_for_clarification(self) -> None:
        response = answer_question(self.database, "Peux-tu importer ce PDF et facturer le client ?")

        self.assertTrue(response.needs_clarification)
        self.assertFalse(response.validation.ok)
        self.assertIn("clarify", [step.node for step in response.orchestration])
        self.assertIn("generate_sql", [step.node for step in response.orchestration])
        self.assertEqual(response.orchestration[-1].status, "skipped")
        self.assertGreaterEqual(len(response.clarification_options), 1)
        self.assertTrue(response.clarification_options[0].question)
        self.assertTrue(response.clarification_options[0].intent_id)

    def test_llm_is_disabled_by_default(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            settings = llm_settings_from_env()

        self.assertEqual(settings.provider, "disabled")
        self.assertFalse(settings.enabled)

    def test_ollama_health_is_disabled_without_provider(self) -> None:
        health = check_ollama_health(
            LlmSettings(
                provider="disabled",
                ollama_url="http://127.0.0.1:11434",
                model="llama3.1",
                timeout_seconds=60,
            )
        )

        self.assertEqual(health.status, "disabled")
        self.assertFalse(health.reachable)
        self.assertIsNone(health.model_available)

    def test_ollama_health_detects_ready_model(self) -> None:
        class FakeResponse:
            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, *_args: object) -> None:
                return None

            def read(self) -> bytes:
                return b'{"models":[{"name":"llama3.1:latest"}]}'

        with patch("app.llm.urlopen", return_value=FakeResponse()):
            health = check_ollama_health(
                LlmSettings(
                    provider="ollama",
                    ollama_url="http://127.0.0.1:11434",
                    model="llama3.1",
                    timeout_seconds=60,
                )
            )

        self.assertEqual(health.status, "ready")
        self.assertTrue(health.reachable)
        self.assertTrue(health.model_available)
        self.assertIsInstance(health.latency_ms, int)

    def test_ollama_health_handles_unreachable_server(self) -> None:
        with patch("app.llm.urlopen", side_effect=OSError("down")):
            health = check_ollama_health(
                LlmSettings(
                    provider="ollama",
                    ollama_url="http://127.0.0.1:11434",
                    model="llama3.1",
                    timeout_seconds=60,
                )
            )

        self.assertEqual(health.status, "unreachable")
        self.assertFalse(health.reachable)
        self.assertIsNone(health.model_available)
        self.assertIn("down", health.error or "")

    def test_ollama_router_can_select_allowed_intent(self) -> None:
        with patch.dict("os.environ", {"FABRIQ_LLM_PROVIDER": "ollama"}):
            with patch("app.agent.classify_intent_with_ollama") as classify:
                classify.return_value.intent_id = "supplier_delays"
                classify.return_value.reason = "Supplier delay wording."
                classify.return_value.confidence = 0.91

                response = answer_question(self.database, "Qui pose probleme ce mois-ci ?")

        self.assertEqual(response.intent, "supplier_delays")
        self.assertEqual(response.routing_strategy, "ollama_intent_router")
        self.assertEqual(response.llm_provider, "ollama")
        self.assertTrue(response.validation.ok)
        self.assertTrue(
            any("Ollama selected supplier_delays" in step.detail for step in response.orchestration)
        )

    def test_guard_blocks_write_queries(self) -> None:
        result = validate_sql("DELETE FROM orders LIMIT 1")

        self.assertFalse(result.ok)
        self.assertGreater(len(result.blocked), 0)

    def test_golden_questions_are_covered(self) -> None:
        golden_path = Path(__file__).resolve().parents[1] / "evaluation" / "golden.json"
        cases = json.loads(golden_path.read_text(encoding="utf-8"))

        for case in cases:
            with self.subTest(case=case["id"]):
                response = answer_question(self.database, case["question"])

                if case.get("expects_clarification"):
                    self.assertTrue(response.needs_clarification)
                    self.assertIsNone(response.intent)
                    self.assertEqual(response.rows, [])
                    continue

                self.assertEqual(response.intent, case["expected_intent"])
                self.assertTrue(response.validation.ok)
                self.assertGreaterEqual(len(response.rows), case["min_rows"])
                self.assertTrue(set(case["required_columns"]).issubset(response.columns))
                self.assertIsNotNone(response.chart)
                self.assertEqual(response.chart.type, case["expected_chart_type"])

    def test_paraphrase_questions_are_covered(self) -> None:
        paraphrase_path = Path(__file__).resolve().parents[1] / "evaluation" / "paraphrases.json"
        cases = json.loads(paraphrase_path.read_text(encoding="utf-8"))

        for case in cases:
            with self.subTest(case=case["id"]):
                response = answer_question(self.database, case["question"])

                self.assertEqual(response.intent, case["expected_intent"])
                self.assertTrue(response.validation.ok)
                self.assertGreaterEqual(len(response.rows), case["min_rows"])
                self.assertTrue(set(case["required_columns"]).issubset(response.columns))
                self.assertIsNotNone(response.chart)
                self.assertEqual(response.chart.type, case["expected_chart_type"])

    def test_semantic_catalog_exposes_intents_and_columns(self) -> None:
        catalog = semantic_catalog()
        intents = catalog["intents"]
        tables = catalog["tables"]

        self.assertEqual(len(intents), len(INTENTS))
        self.assertGreaterEqual(len(tables), 1)
        self.assertTrue(all(intent["description"] for intent in intents))
        self.assertIn("orders", {table["name"] for table in tables})
        self.assertTrue(
            any(
                column["name"] == "revenue"
                for table in tables
                if table["name"] == "orders"
                for column in table["columns"]
            )
        )

    def test_catalog_endpoint_returns_semantic_catalog(self) -> None:
        from fastapi.testclient import TestClient

        from app.main import app

        app.dependency_overrides[get_current_user] = _test_user
        try:
            response = TestClient(app).get("/api/catalog")
            payload = response.json()
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        self.assertEqual(response.status_code, 200)
        self.assertIn("intents", payload)
        self.assertIn("tables", payload)
        self.assertEqual(len(payload["intents"]), len(INTENTS))

    def test_health_endpoint_exposes_llm_ping_fields(self) -> None:
        from fastapi.testclient import TestClient

        from app.main import app

        response = TestClient(app).get("/api/health")
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["version"], "0.10.0")
        self.assertIn("llm_status", payload)
        self.assertIn("llm_reachable", payload)
        self.assertIn("llm_model_available", payload)
        self.assertIn("llm_latency_ms", payload)

    def test_postgres_templates_pass_sql_guard(self) -> None:
        for intent in INTENTS:
            with self.subTest(intent=intent.id):
                result = validate_sql(intent.sql_for("postgres"))

                self.assertTrue(result.ok, result.blocked)


class V4Test(unittest.TestCase):
    """Tests for v0.4.0 features: tenant SQL filtering, audit CSV export, webhook."""

    # ─── inject_tenant_filter ─────────────────────────────────────────────────

    def test_inject_adds_where_when_no_existing_where(self) -> None:
        sql = (
            "SELECT o.id FROM orders o "
            "GROUP BY o.id ORDER BY o.id LIMIT 10"
        )
        result = inject_tenant_filter(sql, "tenant_demo")
        self.assertIn("tenant_demo", result)
        self.assertIn("WHERE", result.upper())
        # WHERE must appear before GROUP BY
        self.assertLess(result.upper().index("WHERE"), result.upper().index("GROUP BY"))

    def test_inject_adds_and_when_where_already_present(self) -> None:
        sql = (
            "SELECT o.id FROM orders o "
            "WHERE o.order_date >= '2026-01-01' "
            "GROUP BY o.id LIMIT 10"
        )
        result = inject_tenant_filter(sql, "tenant_acme")
        self.assertIn("tenant_acme", result)
        # Should keep the existing WHERE keyword (only one WHERE)
        self.assertEqual(result.upper().count("WHERE"), 1)
        self.assertIn("AND", result.upper())

    def test_inject_skips_non_tenant_tables(self) -> None:
        sql = (
            "SELECT s.name, AVG(sd.delay_days) FROM supplier_delays sd "
            "JOIN suppliers s ON s.id = sd.supplier_id "
            "GROUP BY s.name LIMIT 10"
        )
        result = inject_tenant_filter(sql, "tenant_demo")
        # No tenant-scoped table → SQL should be unchanged
        self.assertEqual(result, sql)

    def test_inject_uses_alias_qualifier(self) -> None:
        sql = "SELECT o.id FROM orders o GROUP BY o.id LIMIT 5"
        result = inject_tenant_filter(sql, "x")
        self.assertIn("o.tenant_id", result)

    def test_postgres_templates_with_tenant_pass_guard(self) -> None:
        """Injected tenant SQL must still pass the SQL guard."""
        for intent in INTENTS:
            with self.subTest(intent=intent.id):
                original = intent.sql_for("postgres")
                tenanted = inject_tenant_filter(original, "tenant_demo")
                result = validate_sql(tenanted)
                self.assertTrue(result.ok, f"Guard blocked tenanted SQL: {result.blocked}")

    # ─── export_csv ───────────────────────────────────────────────────────────

    def test_export_csv_returns_header_when_no_log(self) -> None:
        with patch("app.audit.LOG_FILE") as mock_path:
            mock_path.exists.return_value = False
            csv_text = export_csv()
        # Must have at least the header row
        self.assertIn("trace_id", csv_text)
        self.assertIn("question", csv_text)

    def test_export_csv_filters_by_tenant(self) -> None:
        fake_event_demo = json.dumps({
            "trace_id": "abc", "created_at": "2026-01-01", "user_id": "u1",
            "tenant_id": "tenant_demo", "question": "Q1", "intent": "margin_trend",
            "routing_strategy": "det", "llm_provider": "disabled",
            "validation_ok": True, "needs_clarification": False, "row_count": 5,
            "chart_type": "bar",
        })
        fake_event_acme = json.dumps({
            "trace_id": "xyz", "created_at": "2026-01-01", "user_id": "u2",
            "tenant_id": "tenant_acme", "question": "Q2", "intent": "stockout_risk",
            "routing_strategy": "det", "llm_provider": "disabled",
            "validation_ok": True, "needs_clarification": False, "row_count": 2,
            "chart_type": "bar",
        })

        with patch("app.audit.LOG_FILE") as mock_path:
            mock_path.exists.return_value = True
            mock_path.read_text.return_value = "\n".join([fake_event_demo, fake_event_acme])
            csv_demo = export_csv(tenant_id="tenant_demo")
            csv_acme = export_csv(tenant_id="tenant_acme")

        self.assertIn("margin_trend", csv_demo)
        self.assertNotIn("stockout_risk", csv_demo)
        self.assertIn("stockout_risk", csv_acme)
        self.assertNotIn("margin_trend", csv_acme)

    # ─── /api/audit/export endpoint ───────────────────────────────────────────

    def test_audit_export_endpoint_returns_csv(self) -> None:
        from fastapi.testclient import TestClient
        from app.main import app

        app.dependency_overrides[get_current_user] = _test_user
        try:
            response = TestClient(app).get("/api/audit/export")
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response.headers["content-type"])
        self.assertIn("attachment", response.headers["content-disposition"])
        self.assertIn("trace_id", response.text)  # CSV header row present

    def test_audit_export_endpoint_requires_auth(self) -> None:
        from fastapi.testclient import TestClient
        from app.main import app

        response = TestClient(app).get("/api/audit/export")
        self.assertEqual(response.status_code, 401)


class V5Test(unittest.TestCase):
    """Tests for v0.5.0 features: dynamic chart, admin endpoint, rate limiting."""

    def setUp(self) -> None:
        self.env_patcher = patch.dict("os.environ", {}, clear=True)
        self.env_patcher.start()
        self.database = SQLiteDatabase()

    def tearDown(self) -> None:
        self.env_patcher.stop()

    # ─── Dynamic chart selection ───────────────────────────────────────────────

    def test_chart_is_none_when_no_rows(self) -> None:
        from app.graph import _adjust_chart
        from app.models import ChartSpec
        chart = ChartSpec(type="line", x="mois", y="marge", title="Test")
        self.assertIsNone(_adjust_chart(chart, []))

    def test_line_is_bar_for_single_row(self) -> None:
        from app.graph import _adjust_chart
        from app.models import ChartSpec
        chart = ChartSpec(type="line", x="mois", y="val", title="Test")
        result = _adjust_chart(chart, [{"mois": "2026-01", "val": 1}])
        self.assertIsNotNone(result)
        self.assertEqual(result.type, "bar")

    def test_bar_kept_for_single_row(self) -> None:
        from app.graph import _adjust_chart
        from app.models import ChartSpec
        chart = ChartSpec(type="bar", x="ref", y="val", title="Test")
        result = _adjust_chart(chart, [{"ref": "A", "val": 1}])
        self.assertIsNotNone(result)
        self.assertEqual(result.type, "bar")

    def test_line_becomes_bar_for_two_rows(self) -> None:
        from app.graph import _adjust_chart
        from app.models import ChartSpec
        chart = ChartSpec(type="line", x="mois", y="taux", title="Test")
        rows = [{"mois": "2026-01", "taux": 12}, {"mois": "2026-02", "taux": 14}]
        result = _adjust_chart(chart, rows)
        self.assertIsNotNone(result)
        self.assertEqual(result.type, "bar")

    def test_bar_becomes_area_for_time_column_many_rows(self) -> None:
        from app.graph import _adjust_chart
        from app.models import ChartSpec
        chart = ChartSpec(type="bar", x="mois", y="ca", title="Test")
        rows = [{"mois": f"2026-{i:02d}", "ca": i * 100} for i in range(1, 7)]
        result = _adjust_chart(chart, rows)
        self.assertIsNotNone(result)
        self.assertEqual(result.type, "area")

    def test_chart_unchanged_for_non_time_bar(self) -> None:
        from app.graph import _adjust_chart
        from app.models import ChartSpec
        chart = ChartSpec(type="bar", x="fournisseur", y="retard", title="Test")
        rows = [{"fournisseur": f"F{i}", "retard": i} for i in range(5)]
        result = _adjust_chart(chart, rows)
        self.assertIsNotNone(result)
        self.assertEqual(result.type, "bar")

    # ─── Admin endpoint ────────────────────────────────────────────────────────

    def test_admin_users_requires_admin_role(self) -> None:
        from fastapi.testclient import TestClient
        from app.main import app

        viewer = UserContext(user_id="v", email="v@v.com", tenant_id="t", role="viewer")
        app.dependency_overrides[get_current_user] = lambda: viewer
        try:
            response = TestClient(app).get("/api/admin/users")
        finally:
            app.dependency_overrides.pop(get_current_user, None)
        self.assertEqual(response.status_code, 403)

    def test_admin_users_returns_list_for_admin(self) -> None:
        from fastapi.testclient import TestClient
        from app.main import app

        app.dependency_overrides[get_current_user] = _test_user
        try:
            with patch.dict("os.environ", {
                "FABRIQ_USERS": "admin@x.io:hash:tenant_demo:admin",
                "FABRIQ_JWT_SECRET": "test-secret",
            }):
                response = TestClient(app).get("/api/admin/users")
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("users", payload)
        self.assertIsInstance(payload["users"], list)
        # Passwords must not be present
        for user in payload["users"]:
            self.assertNotIn("hashed_password", user)
            self.assertNotIn("password", user)


class V6Test(unittest.TestCase):
    """Tests for v0.6.0 features: DB ping, audit pagination, alert CSV, Prometheus."""

    def setUp(self) -> None:
        self.env_patcher = patch.dict("os.environ", {}, clear=True)
        self.env_patcher.start()
        self.database = SQLiteDatabase()

    def tearDown(self) -> None:
        self.env_patcher.stop()

    # ─── DB ping ──────────────────────────────────────────────────────────────

    def test_sqlite_ping_returns_float(self) -> None:
        latency = self.database.ping()
        self.assertIsInstance(latency, float)
        self.assertGreaterEqual(latency, 0)

    def test_health_includes_db_ok(self) -> None:
        from fastapi.testclient import TestClient
        from app.main import app

        response = TestClient(app).get("/api/health")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("db_ok", payload)
        self.assertTrue(payload["db_ok"])
        self.assertIn("db_latency_ms", payload)

    # ─── Audit pagination ─────────────────────────────────────────────────────

    def test_recent_events_returns_tuple(self) -> None:
        from app.audit import recent_events
        events, total = recent_events(page=1, limit=5)
        self.assertIsInstance(events, list)
        self.assertIsInstance(total, int)
        self.assertGreaterEqual(total, 0)

    def test_audit_endpoint_returns_pagination_fields(self) -> None:
        from fastapi.testclient import TestClient
        from app.main import app

        app.dependency_overrides[get_current_user] = _test_user
        try:
            response = TestClient(app).get("/api/audit/recent?page=1&limit=5")
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("events", payload)
        self.assertIn("total", payload)
        self.assertIn("page", payload)
        self.assertIn("limit", payload)

    # ─── Alert events CSV ─────────────────────────────────────────────────────

    def test_alert_events_csv_returns_header(self) -> None:
        from app.alerts import export_alert_events_csv
        csv_data = export_alert_events_csv(tenant_id="tenant_test")
        self.assertIn("rule_id", csv_data)
        self.assertIn("fired_at", csv_data)

    def test_alert_events_export_endpoint(self) -> None:
        from fastapi.testclient import TestClient
        from app.main import app

        app.dependency_overrides[get_current_user] = _test_user
        try:
            response = TestClient(app).get("/api/alerts/events/export")
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response.headers.get("content-type", ""))

    # ─── Prometheus ───────────────────────────────────────────────────────────

    def test_metrics_endpoint_returns_prometheus_text(self) -> None:
        from fastapi.testclient import TestClient
        from app.main import app

        response = TestClient(app).get("/metrics")
        self.assertEqual(response.status_code, 200)
        self.assertIn("http_requests_total", response.text)


class V7Test(unittest.TestCase):
    """Tests for v0.7.0 features: audit filters, TTL cache, alert pagination, user disable."""

    def setUp(self) -> None:
        self.env_patcher = patch.dict("os.environ", {}, clear=True)
        self.env_patcher.start()
        self.database = SQLiteDatabase()

    def tearDown(self) -> None:
        self.env_patcher.stop()

    # ─── Audit filters ────────────────────────────────────────────────────────

    def test_recent_events_intent_filter(self) -> None:
        from app.audit import recent_events
        events, total = recent_events(intent="margin_trend")
        for ev in events:
            self.assertEqual(ev.get("intent"), "margin_trend")

    def test_recent_events_validation_ok_filter(self) -> None:
        from app.audit import recent_events
        events, _ = recent_events(validation_ok=True)
        for ev in events:
            self.assertTrue(ev.get("validation_ok"))

    def test_audit_endpoint_accepts_intent_filter(self) -> None:
        from fastapi.testclient import TestClient
        from app.main import app

        app.dependency_overrides[get_current_user] = _test_user
        try:
            response = TestClient(app).get("/api/audit/recent?intent=margin_trend")
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        self.assertEqual(response.status_code, 200)

    # ─── TTL cache ────────────────────────────────────────────────────────────

    def test_cache_set_get(self) -> None:
        from app.cache import TTLCache
        cache = TTLCache(ttl_seconds=60)
        cache.set("key1", [1, 2, 3])
        self.assertEqual(cache.get("key1"), [1, 2, 3])

    def test_cache_miss_returns_none(self) -> None:
        from app.cache import TTLCache
        cache = TTLCache(ttl_seconds=60)
        self.assertIsNone(cache.get("nonexistent"))

    def test_cache_expiry(self) -> None:
        import time
        from app.cache import TTLCache
        cache = TTLCache(ttl_seconds=0)
        cache.set("k", "v")
        time.sleep(0.01)
        self.assertIsNone(cache.get("k"))

    def test_cache_size(self) -> None:
        from app.cache import TTLCache
        cache = TTLCache(ttl_seconds=60)
        self.assertEqual(cache.size(), 0)
        cache.set("a", 1)
        cache.set("b", 2)
        self.assertEqual(cache.size(), 2)

    # ─── Alert events pagination ──────────────────────────────────────────────

    def test_recent_alert_events_returns_tuple(self) -> None:
        from app.alerts import recent_alert_events
        events, total = recent_alert_events(tenant_id="tenant_test", page=1, limit=5)
        self.assertIsInstance(events, list)
        self.assertIsInstance(total, int)

    def test_alert_events_endpoint_has_pagination(self) -> None:
        from fastapi.testclient import TestClient
        from app.main import app

        app.dependency_overrides[get_current_user] = _test_user
        try:
            response = TestClient(app).get("/api/alerts/events?page=1&limit=5")
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("total", payload)
        self.assertIn("page", payload)

    # ─── User disable/enable ──────────────────────────────────────────────────

    def test_disable_enable_roundtrip(self) -> None:
        from app.disabled_users import disable_user, enable_user, is_disabled
        test_email = "roundtrip_test@fabriq.io"
        self.assertFalse(is_disabled(test_email))
        disable_user(test_email)
        self.assertTrue(is_disabled(test_email))
        enable_user(test_email)
        self.assertFalse(is_disabled(test_email))

    def test_disable_endpoint_requires_admin(self) -> None:
        from fastapi.testclient import TestClient
        from app.main import app

        viewer = UserContext(user_id="v", email="v@v.com", tenant_id="t", role="viewer")
        app.dependency_overrides[get_current_user] = lambda: viewer
        try:
            response = TestClient(app).post("/api/admin/users/someone@test.io/disable")
        finally:
            app.dependency_overrides.pop(get_current_user, None)
        self.assertEqual(response.status_code, 403)


class V8Test(unittest.TestCase):
    """Tests for v0.8.0: Slack alerts, JWT refresh endpoint, OpenAPI tags."""

    def setUp(self) -> None:
        self.env_patcher = patch.dict("os.environ", {}, clear=True)
        self.env_patcher.start()

    def tearDown(self) -> None:
        self.env_patcher.stop()

    # ─── Slack notification ───────────────────────────────────────────────────

    def test_fire_slack_skips_when_no_url(self) -> None:
        from app.alerts import AlertEvent, fire_slack
        event = AlertEvent(
            rule_id="r1", rule_name="Test", fired_at="2026-01-01T08:00:00Z",
            tenant_id="tenant_demo", triggered_value=5.0, rows_snapshot=[],
        )
        fire_slack("", event)  # must not raise

    def test_alert_rule_has_slack_field(self) -> None:
        from app.alerts import AlertRule
        rule = AlertRule(
            name="test", intent_id="margin_trend", threshold_column="margin",
            threshold_value=10.0, operator="lt", tenant_id="t",
            slack_webhook_url="https://hooks.slack.com/services/test",
        )
        self.assertEqual(rule.slack_webhook_url, "https://hooks.slack.com/services/test")

    # ─── JWT refresh endpoint ────────────────────────────────────────────────

    def test_refresh_endpoint_returns_new_token(self) -> None:
        from fastapi.testclient import TestClient
        from app.main import app

        app.dependency_overrides[get_current_user] = _test_user
        try:
            with patch.dict("os.environ", {"FABRIQ_JWT_SECRET": "test-secret"}):
                response = TestClient(app).post("/api/auth/refresh")
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("access_token", payload)
        self.assertEqual(payload["token_type"], "bearer")

    def test_refresh_endpoint_without_auth_returns_401(self) -> None:
        from fastapi.testclient import TestClient
        from app.main import app

        response = TestClient(app).post("/api/auth/refresh")
        self.assertEqual(response.status_code, 401)

    # ─── OpenAPI tags ─────────────────────────────────────────────────────────

    def test_openapi_has_tags(self) -> None:
        from fastapi.testclient import TestClient
        from app.main import app

        response = TestClient(app).get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        schema = response.json()
        tag_names = {t["name"] for t in schema.get("tags", [])}
        self.assertIn("auth", tag_names)
        self.assertIn("analysis", tag_names)
        self.assertIn("audit", tag_names)
        self.assertIn("alerts", tag_names)
        self.assertIn("admin", tag_names)

    def test_ask_endpoint_has_summary(self) -> None:
        from fastapi.testclient import TestClient
        from app.main import app

        response = TestClient(app).get("/openapi.json")
        schema = response.json()
        ask_path = schema.get("paths", {}).get("/api/ask", {})
        self.assertIn("post", ask_path)
        self.assertIn("summary", ask_path["post"])


class V10Test(unittest.TestCase):
    """Tests for v0.10.0: Excel export, audit/export.xlsx endpoint."""

    def test_export_xlsx_returns_bytes(self) -> None:
        from app.audit import export_xlsx
        data = export_xlsx(tenant_id="tenant_demo")
        self.assertEqual(data[:2], b"PK")

    def test_export_xlsx_empty_tenant(self) -> None:
        from app.audit import export_xlsx
        data = export_xlsx(tenant_id="nonexistent-tenant-xyz")
        self.assertEqual(data[:2], b"PK")

    def test_xlsx_endpoint_exists_in_openapi(self) -> None:
        from fastapi.testclient import TestClient
        from app.main import app

        response = TestClient(app).get("/openapi.json")
        schema = response.json()
        paths = schema.get("paths", {})
        self.assertIn("/api/audit/export.xlsx", paths)

    def test_xlsx_endpoint_requires_auth(self) -> None:
        from fastapi.testclient import TestClient
        from app.main import app

        response = TestClient(app).get("/api/audit/export.xlsx")
        self.assertEqual(response.status_code, 401)

    def test_xlsx_endpoint_returns_xlsx_content_type(self) -> None:
        from fastapi.testclient import TestClient
        from app.main import app

        app.dependency_overrides[get_current_user] = _test_user
        try:
            response = TestClient(app).get("/api/audit/export.xlsx")
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "spreadsheetml",
            response.headers.get("content-type", ""),
        )


if __name__ == "__main__":
    unittest.main()
