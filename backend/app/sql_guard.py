from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass


ALLOWED_TABLES = {
    "products",
    "customers",
    "orders",
    "production_batches",
    "inventory_movements",
    "suppliers",
    "supplier_delays",
    "shipments",
    "returns",
    "costs",
}

BLOCKED_KEYWORDS = {
    "alter",
    "attach",
    "create",
    "delete",
    "detach",
    "drop",
    "insert",
    "pragma",
    "replace",
    "truncate",
    "update",
    "vacuum",
}


@dataclass(frozen=True)
class GuardResult:
    ok: bool
    checks: list[str]
    blocked: list[str]


def validate_sql(sql: str) -> GuardResult:
    normalized = _compact(sql)
    lowered = normalized.lower()
    checks: list[str] = []
    blocked: list[str] = []

    if not lowered.startswith("select "):
        blocked.append("La requete doit commencer par SELECT.")
    else:
        checks.append("SELECT uniquement.")

    if ";" in lowered:
        blocked.append("Les requetes multi-instructions sont bloquees.")
    else:
        checks.append("Une seule instruction SQL.")

    found_keywords = sorted(keyword for keyword in BLOCKED_KEYWORDS if re.search(rf"\b{keyword}\b", lowered))
    if found_keywords:
        blocked.append(f"Mots-cles interdits detectes: {', '.join(found_keywords)}.")
    else:
        checks.append("Aucun mot-cle d'ecriture ou d'administration.")

    referenced_tables = set(re.findall(r"\b(?:from|join)\s+([a-z_][a-z0-9_]*)", lowered))
    forbidden_tables = sorted(referenced_tables - ALLOWED_TABLES)
    if forbidden_tables:
        blocked.append(f"Tables non autorisees: {', '.join(forbidden_tables)}.")
    elif referenced_tables:
        checks.append("Tables limitees au catalogue autorise.")
    else:
        blocked.append("Aucune table referencee.")

    limit_match = re.search(r"\blimit\s+(\d+)\b", lowered)
    if not limit_match:
        blocked.append("LIMIT obligatoire pour borner le resultat.")
    elif int(limit_match.group(1)) > 100:
        blocked.append("LIMIT ne peut pas depasser 100 lignes.")
    else:
        checks.append("LIMIT present et borne.")

    return GuardResult(ok=not blocked, checks=checks, blocked=blocked)


def execute_readonly(connection: sqlite3.Connection, sql: str) -> list[dict[str, object]]:
    result = validate_sql(sql)
    if not result.ok:
        raise ValueError("SQL bloque par le garde-fou.")

    cursor = connection.execute(sql)
    return [dict(row) for row in cursor.fetchall()]


def _compact(sql: str) -> str:
    return re.sub(r"\s+", " ", sql.strip())
