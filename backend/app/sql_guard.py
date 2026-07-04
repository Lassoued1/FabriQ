from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError


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

# Defense en profondeur : scan textuel conserve en plus de l'analyse AST.
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

# Types de noeuds sqlglot interdits quelle que soit leur position dans l'arbre.
_FORBIDDEN_NODE_NAMES = (
    "Insert",
    "Update",
    "Delete",
    "Create",
    "Drop",
    "Alter",
    "AlterTable",
    "TruncateTable",
    "Command",
    "Set",
    "Attach",
    "Detach",
    "Pragma",
)
FORBIDDEN_NODES = tuple(
    node for name in _FORBIDDEN_NODE_NAMES if (node := getattr(exp, name, None)) is not None
)

MAX_LIMIT_ROWS = 100


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

    # 1. Analyse syntaxique : le SQL doit etre parsable avant toute execution.
    try:
        statements = [s for s in sqlglot.parse(normalized) if s is not None]
    except ParseError:
        return GuardResult(
            ok=False,
            checks=checks,
            blocked=["SQL rejete: analyse syntaxique impossible (parseur AST)."],
        )
    checks.append("Syntaxe analysee par parseur AST.")

    # 2. Une seule instruction.
    if ";" in lowered or len(statements) != 1:
        blocked.append("Les requetes multi-instructions sont bloquees.")
        return GuardResult(ok=False, checks=checks, blocked=blocked)
    checks.append("Une seule instruction SQL.")

    tree = statements[0]

    # 3. L'instruction racine doit etre un SELECT pur (pas d'UNION, pas de CTE).
    if not isinstance(tree, exp.Select):
        blocked.append("Seules les requetes SELECT simples sont autorisees.")
        return GuardResult(ok=False, checks=checks, blocked=blocked)
    if next(tree.find_all(exp.With, exp.CTE), None) is not None:
        blocked.append("Les CTE (WITH) ne sont pas autorisees.")
    if tree.args.get("into"):
        blocked.append("SELECT INTO est bloque.")
    if tree.args.get("locks"):
        blocked.append("Les verrous (FOR UPDATE/SHARE) sont bloques.")
    if not blocked:
        checks.append("SELECT uniquement.")

    # 4. Aucun noeud d'ecriture ou d'administration dans tout l'arbre.
    forbidden_found = sorted({node.__class__.__name__ for node in tree.find_all(*FORBIDDEN_NODES)})
    found_keywords = sorted(
        keyword for keyword in BLOCKED_KEYWORDS if re.search(rf"\b{keyword}\b", lowered)
    )
    if forbidden_found or found_keywords:
        details = ", ".join(forbidden_found + found_keywords)
        blocked.append(f"Operations interdites detectees: {details}.")
    else:
        checks.append("Aucun mot-cle d'ecriture ou d'administration.")

    # 5. Tables limitees a l'allowlist, y compris sous-requetes et jointures.
    referenced_tables = {table.name.lower() for table in tree.find_all(exp.Table)}
    forbidden_tables = sorted(referenced_tables - ALLOWED_TABLES)
    if forbidden_tables:
        blocked.append(f"Tables non autorisees: {', '.join(forbidden_tables)}.")
    elif referenced_tables:
        checks.append("Tables limitees au catalogue autorise.")
    else:
        blocked.append("Aucune table referencee.")

    # 6. LIMIT obligatoire sur le SELECT racine, entier litteral et borne.
    limit_value = _literal_limit(tree.args.get("limit"))
    if limit_value is None:
        blocked.append("LIMIT obligatoire (entier litteral) pour borner le resultat.")
    elif limit_value > MAX_LIMIT_ROWS:
        blocked.append(f"LIMIT ne peut pas depasser {MAX_LIMIT_ROWS} lignes.")
    else:
        checks.append("LIMIT present et borne.")

    return GuardResult(ok=not blocked, checks=checks, blocked=blocked)


def execute_readonly(connection: sqlite3.Connection, sql: str) -> list[dict[str, object]]:
    result = validate_sql(sql)
    if not result.ok:
        raise ValueError("SQL bloque par le garde-fou.")

    cursor = connection.execute(sql)
    return [dict(row) for row in cursor.fetchall()]


def _literal_limit(limit_node: exp.Expression | None) -> int | None:
    if not isinstance(limit_node, exp.Limit):
        return None

    expression = limit_node.expression
    if not isinstance(expression, exp.Literal) or expression.is_string:
        return None

    try:
        return int(expression.this)
    except (TypeError, ValueError):
        return None


def _compact(sql: str) -> str:
    return re.sub(r"\s+", " ", sql.strip())
