"""Suite adversariale du garde-fou SQL.

Chaque cas simule une tentative d'injection ou de contournement et doit
etre bloque par validate_sql. Les cas de controle verifient que le SQL
legitime des templates continue de passer.
"""

from __future__ import annotations

import unittest

from app.sql_guard import validate_sql

ADVERSARIAL_CASES: tuple[tuple[str, str], ...] = (
    ("multi_statement_drop", "SELECT * FROM orders LIMIT 5; DROP TABLE orders"),
    ("multi_statement_insert", "SELECT 1 FROM orders LIMIT 1; INSERT INTO orders VALUES (1)"),
    ("update_direct", "UPDATE orders SET revenue = 0 WHERE id = 1"),
    ("delete_direct", "DELETE FROM orders"),
    ("insert_direct", "INSERT INTO orders (id) VALUES (99)"),
    ("drop_direct", "DROP TABLE products"),
    ("create_table", "CREATE TABLE pwned (id INT)"),
    ("alter_table", "ALTER TABLE orders ADD COLUMN pwned INT"),
    ("truncate_table", "TRUNCATE TABLE orders"),
    ("pragma_sqlite", "PRAGMA writable_schema = ON"),
    ("attach_database", "ATTACH DATABASE '/tmp/evil.db' AS evil"),
    ("union_system_table", "SELECT reference FROM products UNION SELECT usename FROM pg_user LIMIT 10"),
    ("subquery_system_table", "SELECT * FROM orders WHERE id IN (SELECT 1 FROM pg_shadow) LIMIT 5"),
    ("sqlite_master_probe", "SELECT name FROM sqlite_master LIMIT 10"),
    ("information_schema_probe", "SELECT table_name FROM information_schema.tables LIMIT 10"),
    ("cte_wrapper", "WITH x AS (SELECT * FROM orders) SELECT * FROM x LIMIT 5"),
    ("select_into", "SELECT * INTO dump FROM orders LIMIT 5"),
    ("for_update_lock", "SELECT * FROM orders LIMIT 5 FOR UPDATE"),
    ("no_limit", "SELECT * FROM orders"),
    ("limit_overflow", "SELECT * FROM orders LIMIT 100000"),
    ("limit_subquery", "SELECT * FROM orders LIMIT (SELECT 999999)"),
    ("comment_smuggle_drop", "SELECT * FROM orders /* ; DROP TABLE orders */ LIMIT 5; DROP TABLE orders"),
    ("unparsable_garbage", "SELECT * FROM WHERE LIMIT ,,"),
    ("empty_string", ""),
    # Allowlist de colonnes (L4) : la table est autorisee, la colonne non.
    ("column_unknown", "SELECT secret FROM orders LIMIT 10"),
    ("column_unknown_qualified", "SELECT o.password FROM orders o LIMIT 10"),
    ("column_from_other_table", "SELECT o.reference FROM orders o LIMIT 10"),
    ("column_in_where", "SELECT id FROM orders WHERE credit_card = 1 LIMIT 10"),
    ("column_in_order_by", "SELECT id FROM orders ORDER BY internal_score LIMIT 10"),
    ("column_in_subquery", (
        "SELECT id FROM orders WHERE id IN (SELECT hidden_flag FROM products) LIMIT 10"
    )),
    ("column_in_function", "SELECT SUM(salary) FROM customers LIMIT 10"),
    # Contournements du garde-fou corriges (point 9 de l'audit) :
    ("nested_union_in_subquery", (
        "SELECT x FROM (SELECT id AS x FROM orders UNION SELECT id FROM customers) t LIMIT 10"
    )),
    ("star_projection", "SELECT * FROM orders LIMIT 10"),
    ("qualified_star_projection", "SELECT o.* FROM orders o LIMIT 10"),
    ("schema_qualified_table", "SELECT id FROM evil.orders LIMIT 10"),
    ("pg_catalog_qualified_table", "SELECT tablename FROM pg_catalog.pg_tables LIMIT 10"),
    ("time_based_pg_sleep", "SELECT id FROM orders WHERE pg_sleep(5) IS NULL LIMIT 10"),
    ("sqlite_load_extension", "SELECT load_extension('evil.so') AS a FROM orders LIMIT 10"),
)

CONTROL_CASES: tuple[tuple[str, str], ...] = (
    ("template_join", (
        "SELECT p.reference AS produit, SUM(o.revenue) AS ca "
        "FROM orders o JOIN products p ON p.id = o.product_id "
        "GROUP BY p.reference ORDER BY ca DESC LIMIT 50"
    )),
    ("template_tenant_filter", (
        "SELECT p.reference AS produit, SUM(o.revenue) AS ca "
        "FROM orders o JOIN products p ON p.id = o.product_id "
        "WHERE o.tenant_id = 'tenant_demo' "
        "GROUP BY p.reference ORDER BY ca DESC LIMIT 50"
    )),
    ("template_subquery_allowed", (
        "SELECT reference FROM products "
        "WHERE id IN (SELECT product_id FROM orders) LIMIT 20"
    )),
    # Un alias de projection reutilise en GROUP BY / ORDER BY / HAVING n'est pas
    # une colonne physique : il ne doit pas etre rejete par l'allowlist L4.
    ("template_projection_alias_reused", (
        "SELECT strftime('%Y-%m', o.order_date) AS mois, SUM(o.revenue) AS ca "
        "FROM orders o GROUP BY mois ORDER BY ca DESC LIMIT 10"
    )),
    ("template_count_star", "SELECT COUNT(*) AS n FROM orders LIMIT 10"),
)


class AdversarialGuardTests(unittest.TestCase):
    def test_adversarial_cases_are_blocked(self) -> None:
        for case_id, sql in ADVERSARIAL_CASES:
            with self.subTest(case=case_id):
                result = validate_sql(sql)
                self.assertFalse(result.ok, f"{case_id} aurait du etre bloque: {sql}")
                self.assertGreater(len(result.blocked), 0, case_id)

    def test_control_cases_still_pass(self) -> None:
        for case_id, sql in CONTROL_CASES:
            with self.subTest(case=case_id):
                result = validate_sql(sql)
                self.assertTrue(result.ok, f"{case_id} bloque a tort: {result.blocked}")

    def test_blocking_rate_is_total(self) -> None:
        blocked = sum(1 for _, sql in ADVERSARIAL_CASES if not validate_sql(sql).ok)
        total = len(ADVERSARIAL_CASES)
        self.assertEqual(blocked, total, f"taux de blocage {blocked}/{total}")


class ColumnAllowlistTests(unittest.TestCase):
    """L'allowlist L4 ne doit jamais bloquer un template livre.

    Ce test rend les templates des deux dialectes et les passe au garde-fou :
    une future intention utilisant une colonne absente de ALLOWED_COLUMNS
    echoue ici, en CI, plutot qu'a la premiere question posee en production.
    """

    def test_every_template_passes_the_guard(self) -> None:
        from app.semantic_layer import INTENTS, QueryParameters, render_intent_sql

        for intent in INTENTS:
            for dialect in ("sqlite", "postgres"):
                with self.subTest(intent=intent.id, dialect=dialect):
                    sql, _ = render_intent_sql(intent, dialect, QueryParameters())
                    result = validate_sql(sql)
                    self.assertTrue(result.ok, f"{intent.id}/{dialect}: {result.blocked}")
                    self.assertIn("Colonnes limitees au catalogue autorise.", result.checks)

    def test_tenant_filtered_templates_pass_the_guard(self) -> None:
        """Le filtre multi-tenant injecte cote serveur reste valide."""
        from app.graph import inject_tenant_filter
        from app.semantic_layer import INTENTS, QueryParameters, render_intent_sql

        for intent in INTENTS:
            with self.subTest(intent=intent.id):
                sql, _ = render_intent_sql(intent, "postgres", QueryParameters())
                result = validate_sql(inject_tenant_filter(sql, "tenant_demo"))
                self.assertTrue(result.ok, f"{intent.id}: {result.blocked}")

    def test_allowlist_matches_the_table_allowlist(self) -> None:
        """Toute table autorisee doit declarer ses colonnes, et inversement."""
        from app.sql_guard import ALLOWED_COLUMNS, ALLOWED_TABLES

        self.assertEqual(set(ALLOWED_COLUMNS), ALLOWED_TABLES)
        for table, columns in ALLOWED_COLUMNS.items():
            self.assertTrue(columns, f"{table} n'a aucune colonne declaree")

    def test_public_catalog_documents_real_columns(self) -> None:
        """Le catalogue montre aux utilisateurs des colonnes qui existent.

        Regression : `inventory_movements` annoncait `quantity_delta`, colonne
        inexistante en base (le vrai nom est `quantity`).
        """
        from app.semantic_layer import TABLE_CATALOG
        from app.sql_guard import ALLOWED_COLUMNS

        for table in TABLE_CATALOG:
            real_columns = ALLOWED_COLUMNS.get(table.name, frozenset())
            for column in table.columns:
                with self.subTest(table=table.name, column=column.name):
                    self.assertIn(
                        column.name,
                        real_columns,
                        f"{table.name}.{column.name} est documentee mais n'existe pas",
                    )


if __name__ == "__main__":
    unittest.main()
