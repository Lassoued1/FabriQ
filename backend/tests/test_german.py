# -*- coding: utf-8 -*-
"""Tests unitaires du support des questions en allemand."""

from __future__ import annotations

import unittest

from app.semantic_layer import (
    extract_query_parameters,
    is_write_request,
    select_intent_match,
)

GERMAN_ROUTING_CASES: tuple[tuple[str, str], ...] = (
    ("margin_trend", "Bei welchen Produkten ist die Marge gesunken?"),
    ("stockout_risk", "Welche Artikel haben in den nächsten 30 Tagen einen Engpass?"),
    ("supplier_delays", "Welche Lieferanten waren am häufigsten verspätet?"),
    ("production_efficiency", "Welche Produktionslinien hatten die meisten Fehler?"),
    ("revenue_trend", "Zeige den monatlichen Umsatz pro Kategorie."),
    ("stock_ageing", "Welche Produkte liegen zu lange im Lager?"),
    ("logistics_cost", "Welche Routen sind teurer geworden?"),
    ("returns_rate", "Welche Produkte haben die höchste Retourenquote?"),
    ("customer_concentration", "Welche Kunden machen den größten Teil des Umsatzes aus?"),
    ("anomaly_detection", "Was hat sich im letzten Monat ungewöhnlich verändert?"),
    ("regional_performance", "Welche Regionen erzielen den meisten Umsatz?"),
    ("return_reasons", "Was sind die häufigsten Gründe für Retouren?"),
    ("avg_order_value", "Wie hoch ist der durchschnittliche Bestellwert pro Kunde?"),
)


class GermanRoutingTests(unittest.TestCase):
    def test_german_questions_route_to_expected_intent(self) -> None:
        for expected, question in GERMAN_ROUTING_CASES:
            with self.subTest(intent=expected):
                match = select_intent_match(question)
                self.assertIsNotNone(match.intent, f"pas d'intention pour: {question}")
                self.assertEqual(match.intent.id, expected)

    def test_german_write_requests_are_refused(self) -> None:
        cases = (
            "Lösche alle Bestellungen.",
            "Entferne den Lieferanten aus der Datenbank.",
            "Aktualisiere die Preise aller Produkte.",
            "Füge einen neuen Kunden hinzu.",
        )
        for question in cases:
            with self.subTest(question=question):
                self.assertTrue(is_write_request(question))
                self.assertIsNone(select_intent_match(question).intent)

    def test_german_read_questions_are_not_write_requests(self) -> None:
        for _, question in GERMAN_ROUTING_CASES:
            with self.subTest(question=question):
                self.assertFalse(is_write_request(question))


class GermanParameterTests(unittest.TestCase):
    def test_horizon_in_tagen(self) -> None:
        params = extract_query_parameters("Engpass in den nächsten 14 Tagen?")
        self.assertEqual(params.horizon_days, 14)

    def test_window_in_monaten(self) -> None:
        params = extract_query_parameters("Umsatz der letzten 6 Monate")
        self.assertEqual(params.window_months, 6)

    def test_quartal_and_halbjahr(self) -> None:
        self.assertEqual(extract_query_parameters("Marge im letzten Quartal").window_months, 3)
        self.assertEqual(extract_query_parameters("Umsatz im letzten Halbjahr").window_months, 6)

    def test_top_n_grossten(self) -> None:
        params = extract_query_parameters("die 5 größten Kunden")
        self.assertEqual(params.top_n, 5)


if __name__ == "__main__":
    unittest.main()
