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

# Allowlist de colonnes, par table (couche L4 du cahier des charges).
# `tenant_id` n'existe que sur le schema PostgreSQL : il est injecte cote
# serveur par inject_tenant_filter(), jamais fourni par le client.
ALLOWED_COLUMNS: dict[str, frozenset[str]] = {
    "products": frozenset({
        "id", "reference", "category", "price", "cost",
        "safety_stock", "current_stock", "created_at",
    }),
    "customers": frozenset({"id", "name", "region", "segment", "tenant_id"}),
    "orders": frozenset({
        "id", "customer_id", "product_id", "order_date",
        "quantity", "revenue", "cost", "tenant_id",
    }),
    "production_batches": frozenset({
        "id", "product_id", "line", "produced_at", "volume", "defects",
    }),
    "inventory_movements": frozenset({
        "id", "product_id", "movement_type", "quantity", "happened_at",
    }),
    "suppliers": frozenset({"id", "name", "punctuality_rate", "lead_time_days"}),
    "supplier_delays": frozenset({
        "id", "supplier_id", "product_id", "delivery_date", "delay_days",
    }),
    "shipments": frozenset({
        "id", "route", "carrier", "shipped_at", "cost", "delay_days",
    }),
    "returns": frozenset({
        "id", "product_id", "customer_id", "returned_at", "quantity", "reason",
    }),
    "costs": frozenset({"id", "product_id", "period", "cost_type", "amount"}),
}

# Union de toutes les colonnes connues : sert aux references non qualifiees,
# dont la table d'origine n'est pas determinable sans resolution de portee.
_ANY_ALLOWED_COLUMN: frozenset[str] = frozenset().union(*ALLOWED_COLUMNS.values())

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

# Seules fonctions "anonymes" (non mappees par sqlglot) tolerees : fonctions de
# date utilisees par les templates. Toute autre fonction inconnue (pg_sleep,
# pg_read_file, load_extension, dblink...) est refusee.
ALLOWED_ANON_FUNCTIONS = {"STRFTIME", "JULIANDAY"}


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
    # Operations ensemblistes, y compris imbriquees dans une sous-requete.
    if next(tree.find_all(exp.Union, exp.Intersect, exp.Except), None) is not None:
        blocked.append("Les operations ensemblistes (UNION/INTERSECT/EXCEPT) sont bloquees.")
    # SELECT * / t.* interdits : les colonnes doivent etre projetees explicitement
    # (COUNT(*) reste autorise, l'etoile y est un argument de fonction, pas une projection).
    if _has_star_projection(tree):
        blocked.append("SELECT * n'est pas autorise : projeter les colonnes explicitement.")
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
    # Un qualificatif de schema/base (evil.orders, pg_catalog.pg_tables) est
    # refuse : l'allowlist porte sur le nom nu, il ne doit pas etre contournable
    # en pointant une table d'un autre schema qui partagerait le meme nom.
    schema_qualified = sorted(
        f"{table.db or table.catalog}.{table.name}"
        for table in tree.find_all(exp.Table)
        if table.args.get("db") or table.args.get("catalog")
    )
    if schema_qualified:
        blocked.append(f"Tables qualifiees par un schema non autorisees: {', '.join(schema_qualified)}.")
    referenced_tables = {table.name.lower() for table in tree.find_all(exp.Table)}
    forbidden_tables = sorted(referenced_tables - ALLOWED_TABLES)
    if forbidden_tables:
        blocked.append(f"Tables non autorisees: {', '.join(forbidden_tables)}.")
    elif referenced_tables:
        checks.append("Tables limitees au catalogue autorise.")
    else:
        blocked.append("Aucune table referencee.")

    # 5b. Fonctions inconnues (non mappees) refusees hors allowlist de dates.
    bad_functions = sorted({
        str(func.this).lower()
        for func in tree.find_all(exp.Anonymous)
        if str(func.this).upper() not in ALLOWED_ANON_FUNCTIONS
    })
    if bad_functions:
        blocked.append(f"Fonctions non autorisees: {', '.join(bad_functions)}.")
    else:
        checks.append("Fonctions limitees aux fonctions analytiques connues.")

    # 6. Colonnes limitees a l'allowlist (par table quand la reference est qualifiee).
    forbidden_columns = _forbidden_columns(tree)
    if forbidden_columns:
        blocked.append(f"Colonnes non autorisees: {', '.join(forbidden_columns)}.")
    else:
        checks.append("Colonnes limitees au catalogue autorise.")

    # 7. LIMIT obligatoire sur le SELECT racine, entier litteral et borne.
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


def _has_star_projection(tree: exp.Expression) -> bool:
    """True si un SELECT (racine ou sous-requete) projette '*' ou 'table.*'.

    L'etoile d'un COUNT(*) n'est pas une projection (c'est un argument de
    fonction) et reste donc autorisee.
    """
    for select in tree.find_all(exp.Select):
        for projection in select.expressions:
            target = projection.this if isinstance(projection, exp.Alias) else projection
            if isinstance(target, exp.Star):
                return True
            if isinstance(target, exp.Column) and isinstance(target.this, exp.Star):
                return True
    return False


def _forbidden_columns(tree: exp.Expression) -> list[str]:
    """Colonnes referencees qui ne figurent pas dans l'allowlist.

    Une reference qualifiee (`o.revenue`) est verifiee contre les colonnes de
    sa table d'origine, l'alias etant resolu depuis le FROM/JOIN. Une reference
    non qualifiee est acceptee si elle appartient a une table du catalogue ou
    s'il s'agit d'un alias defini par la requete elle-meme (`AS taux_marge`,
    reutilise en GROUP BY / ORDER BY / HAVING).
    """
    # alias (ou nom de table) -> nom de table reel
    sources: dict[str, str] = {}
    for table in tree.find_all(exp.Table):
        name = table.name.lower()
        sources[name] = name
        if table.alias:
            sources[table.alias.lower()] = name

    # Alias de projection definis par la requete : SELECT ... AS x
    query_aliases = {
        alias.alias.lower() for alias in tree.find_all(exp.Alias) if alias.alias
    }

    forbidden: set[str] = set()
    for column in tree.find_all(exp.Column):
        name = column.name.lower()
        if not name or name == "*":
            continue

        qualifier = (column.table or "").lower()
        if qualifier:
            source = sources.get(qualifier)
            # Alias inconnu : on retombe sur l'union, la table etant de toute
            # facon deja filtree par l'allowlist des tables.
            allowed = ALLOWED_COLUMNS.get(source, _ANY_ALLOWED_COLUMN) if source else _ANY_ALLOWED_COLUMN
            if name not in allowed:
                forbidden.add(f"{qualifier}.{name}")
        elif name not in _ANY_ALLOWED_COLUMN and name not in query_aliases:
            forbidden.add(name)

    return sorted(forbidden)


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
