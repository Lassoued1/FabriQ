"""Tests unitaires de l'extraction de parametres des questions."""

from __future__ import annotations

import unittest

from app.semantic_layer import (
    QueryParameters,
    extract_query_parameters,
    intent_by_id,
    render_intent_sql,
)


class ExtractionTests(unittest.TestCase):
    def test_no_parameters_in_question(self) -> None:
        params = extract_query_parameters("Quels fournisseurs sont en retard ?")
        self.assertEqual(params, QueryParameters())

    def test_horizon_days(self) -> None:
        cases = {
            "rupture dans les 14 prochains jours": 14,
            "rupture d'ici 7 jours": 7,
            "risque de penurie sous 21 jours": 21,
        }
        for question, expected in cases.items():
            with self.subTest(question=question):
                self.assertEqual(extract_query_parameters(question).horizon_days, expected)

    def test_top_n(self) -> None:
        cases = {
            "top 5 des clients": 5,
            "les 3 principaux fournisseurs": 3,
            "les 10 plus gros clients": 10,
        }
        for question, expected in cases.items():
            with self.subTest(question=question):
                self.assertEqual(extract_query_parameters(question).top_n, expected)

    def test_window_months(self) -> None:
        cases = {
            "chiffre d'affaires sur 6 mois": 6,
            "les 3 derniers mois": 3,
            "depuis 12 mois": 12,
            "la marge du trimestre dernier": 3,
            "le CA du dernier semestre": 6,
        }
        for question, expected in cases.items():
            with self.subTest(question=question):
                self.assertEqual(extract_query_parameters(question).window_months, expected)

    def test_values_are_clamped(self) -> None:
        params = extract_query_parameters("top 999 produits sur une rupture dans 999 jours")
        self.assertEqual(params.top_n, 100)
        self.assertEqual(params.horizon_days, 365)


class RenderTests(unittest.TestCase):
    def test_defaults_reproduce_historical_sql(self) -> None:
        intent = intent_by_id("stockout_risk")
        sql, applied = render_intent_sql(intent, "sqlite", QueryParameters())
        self.assertIn("LIMIT 50", sql)
        self.assertIn("< 30", sql)
        self.assertIn("'2026-04-01'", sql)
        self.assertEqual(applied, [])

    def test_explicit_parameters_are_bound(self) -> None:
        intent = intent_by_id("stockout_risk")
        params = QueryParameters(top_n=5, horizon_days=7, window_months=2)
        sql, applied = render_intent_sql(intent, "sqlite", params)
        self.assertIn("LIMIT 5", sql)
        self.assertIn("< 7", sql)
        self.assertIn("'2026-04-30'", sql)
        self.assertEqual(len(applied), 3)

    def test_unsupported_parameters_are_ignored(self) -> None:
        intent = intent_by_id("customer_concentration")
        params = QueryParameters(horizon_days=7, window_months=3)
        sql, applied = render_intent_sql(intent, "sqlite", params)
        self.assertIn("LIMIT 50", sql)
        self.assertEqual(applied, [])


if __name__ == "__main__":
    unittest.main()
