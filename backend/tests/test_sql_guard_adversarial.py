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


if __name__ == "__main__":
    unittest.main()
