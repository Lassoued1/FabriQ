from __future__ import annotations

import json
import operator
import os
import smtplib
import urllib.request
from datetime import UTC, datetime
from email.mime.text import MIMEText
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from .database import ReadonlyDatabase
from .semantic_layer import QueryParameters, intent_by_id, render_intent_sql

ALERTS_DIR = Path(__file__).resolve().parents[1] / "alerts"
RULES_FILE = ALERTS_DIR / "rules.json"
EVENTS_FILE = Path(__file__).resolve().parents[1] / "logs" / "alerts.jsonl"

_OPERATORS: dict[str, object] = {
    "gt": operator.gt,
    "lt": operator.lt,
    "gte": operator.ge,
    "lte": operator.le,
}


class AlertRule(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    name: str
    intent_id: str
    threshold_column: str
    threshold_value: float
    operator: Literal["gt", "lt", "gte", "lte"]
    tenant_id: str
    cron: str = "0 8 * * *"
    enabled: bool = True
    webhook_url: str | None = None
    email_to: list[str] | None = None
    slack_webhook_url: str | None = None


class AlertEvent(BaseModel):
    rule_id: str
    rule_name: str
    fired_at: str
    tenant_id: str
    triggered_value: float
    rows_snapshot: list[dict]


# ─── Persistence ──────────────────────────────────────────────────────────────

def load_rules() -> list[AlertRule]:
    if not RULES_FILE.exists():
        return []
    try:
        raw = json.loads(RULES_FILE.read_text(encoding="utf-8"))
        return [AlertRule(**r) for r in raw]
    except Exception:
        return []


def save_rules(rules: list[AlertRule]) -> None:
    ALERTS_DIR.mkdir(parents=True, exist_ok=True)
    RULES_FILE.write_text(
        json.dumps([r.model_dump() for r in rules], ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def append_event(event: AlertEvent) -> None:
    EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with EVENTS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event.model_dump(), ensure_ascii=True) + "\n")


def recent_alert_events(
    tenant_id: str,
    limit: int = 20,
    page: int = 1,
) -> tuple[list[dict], int]:
    """Return (events, total_count) for the given page, newest-first."""
    if not EVENTS_FILE.exists():
        return [], 0

    parsed: list[dict] = []
    for line in reversed(EVENTS_FILE.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        try:
            ev = json.loads(line)
            if ev.get("tenant_id") == tenant_id:
                parsed.append(ev)
        except Exception:
            continue

    total = len(parsed)
    offset = (page - 1) * limit
    return parsed[offset : offset + limit], total


def export_alert_events_csv(tenant_id: str, limit: int = 200) -> str:
    """Return alert events as a CSV string filtered by tenant_id."""
    import csv
    import io

    FIELDS = ["rule_id", "rule_name", "fired_at", "tenant_id", "triggered_value"]

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=FIELDS, extrasaction="ignore")
    writer.writeheader()

    events, _ = recent_alert_events(tenant_id=tenant_id, limit=limit)
    for ev in events:
        writer.writerow(ev)

    return buf.getvalue()


# ─── Rule management ──────────────────────────────────────────────────────────

def rules_for_tenant(tenant_id: str) -> list[AlertRule]:
    return [r for r in load_rules() if r.tenant_id == tenant_id]


def add_rule(rule: AlertRule) -> AlertRule:
    rules = load_rules()
    rules.append(rule)
    save_rules(rules)
    return rule


def delete_rule(rule_id: str, tenant_id: str) -> bool:
    rules = load_rules()
    new_rules = [r for r in rules if not (r.id == rule_id and r.tenant_id == tenant_id)]
    if len(new_rules) == len(rules):
        return False
    save_rules(new_rules)
    return True


# ─── Alert evaluation ─────────────────────────────────────────────────────────

def evaluate_rule(rule: AlertRule, database: ReadonlyDatabase) -> AlertEvent | None:
    intent = intent_by_id(rule.intent_id)
    if intent is None:
        return None

    try:
        sql, _ = render_intent_sql(intent, database.dialect, QueryParameters())
        rows = database.execute_readonly(sql)
    except Exception:
        return None

    if not rows:
        return None

    values = [
        float(row[rule.threshold_column])
        for row in rows
        if row.get(rule.threshold_column) is not None
    ]
    if not values:
        return None

    agg_value = max(values) if rule.operator in ("gt", "gte") else min(values)
    compare = _OPERATORS.get(rule.operator)
    if compare is None or not compare(agg_value, rule.threshold_value):
        return None

    return AlertEvent(
        rule_id=rule.id,
        rule_name=rule.name,
        fired_at=datetime.now(UTC).isoformat(),
        tenant_id=rule.tenant_id,
        triggered_value=agg_value,
        rows_snapshot=rows[:5],
    )


def fire_slack(slack_url: str, event: AlertEvent) -> None:
    """Post a Slack message via Incoming Webhook. Best-effort — errors are silenced."""
    if not slack_url:
        return
    text = (
        f":warning: *Alerte FabriQ* — {event.rule_name}\n"
        f"Valeur mesurée : *{event.triggered_value:.2f}*\n"
        f"Tenant : `{event.tenant_id}` | {event.fired_at}"
    )
    payload = json.dumps({"text": text}, ensure_ascii=True).encode()
    req = urllib.request.Request(
        slack_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=5)  # noqa: S310
    except Exception:
        pass


def fire_webhook(url: str, event: AlertEvent) -> None:
    """Best-effort POST of the alert event payload to a webhook URL."""
    payload = json.dumps(event.model_dump(), ensure_ascii=True).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=5)  # noqa: S310
    except Exception:
        pass


def send_alert_email(event: AlertEvent, recipients: list[str]) -> None:
    """Send a plain-text alert email via SMTP if configured in the environment."""
    host = os.environ.get("FABRIQ_SMTP_HOST", "")
    if not host or not recipients:
        return
    try:
        port = int(os.environ.get("FABRIQ_SMTP_PORT", "587"))
        user = os.environ.get("FABRIQ_SMTP_USER", "")
        password = os.environ.get("FABRIQ_SMTP_PASS", "")
        from_addr = os.environ.get("FABRIQ_ALERT_FROM_EMAIL", user or "fabriq-alerts@noreply.local")

        body = (
            f"Alerte FabriQ déclenchée : {event.rule_name}\n\n"
            f"Valeur mesurée : {event.triggered_value:.2f}\n"
            f"Heure         : {event.fired_at}\n"
            f"Tenant        : {event.tenant_id}\n"
        )
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = f"[FabriQ] Alerte : {event.rule_name}"
        msg["From"] = from_addr
        msg["To"] = ", ".join(recipients)

        with smtplib.SMTP(host, port, timeout=10) as server:
            server.ehlo()
            server.starttls()
            if user and password:
                server.login(user, password)
            server.sendmail(from_addr, recipients, msg.as_string())
    except Exception:
        pass  # best-effort — never crash the scheduler


def _fire_rule(rule: AlertRule, database: ReadonlyDatabase) -> None:
    """Evaluate a rule, persist the event, and notify via webhook, Slack and/or email."""
    event = evaluate_rule(rule, database)
    if event is None:
        return
    append_event(event)
    if rule.webhook_url:
        fire_webhook(rule.webhook_url, event)
    # Per-rule Slack webhook takes precedence; fall back to global env variable.
    slack_url = rule.slack_webhook_url or os.environ.get("FABRIQ_SLACK_WEBHOOK", "")
    if slack_url:
        fire_slack(slack_url, event)
    if rule.email_to:
        send_alert_email(event, rule.email_to)


def check_all_rules(database: ReadonlyDatabase) -> None:
    for rule in load_rules():
        if rule.enabled:
            _fire_rule(rule, database)


# ─── Scheduler setup ──────────────────────────────────────────────────────────

def start_scheduler(database: ReadonlyDatabase) -> None:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger

    scheduler = BackgroundScheduler(timezone="UTC")

    def _refresh_jobs() -> None:
        scheduler.remove_all_jobs()
        for rule in load_rules():
            if not rule.enabled:
                continue
            try:
                parts = rule.cron.split()
                trigger = CronTrigger(
                    minute=parts[0],
                    hour=parts[1],
                    day=parts[2],
                    month=parts[3],
                    day_of_week=parts[4],
                    timezone="UTC",
                )
                scheduler.add_job(
                    _fire_rule,
                    trigger=trigger,
                    args=[rule, database],
                    id=rule.id,
                    replace_existing=True,
                )
            except Exception:
                continue
        # Reload jobs every 5 minutes to pick up new/updated rules.
        scheduler.add_job(
            _refresh_jobs,
            "interval",
            minutes=5,
            id="__refresh__",
            replace_existing=True,
        )

    _refresh_jobs()
    scheduler.start()
