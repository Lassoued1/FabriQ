# -*- coding: utf-8 -*-
"""Tests unitaires du support des questions en anglais."""

from __future__ import annotations

import unittest

from app.semantic_layer import (
    extract_query_parameters,
    is_write_request,
    select_intent_match,
)

ENGLISH_ROUTING_CASES: tuple[tuple[str, str], ...] = (
    ("margin_trend", "Which products saw their margin drop last quarter?"),
    ("stockout_risk", "Which items are at risk of a stockout in the next 30 days?"),
    ("supplier_delays", "Which suppliers were most often late?"),
    ("production_efficiency", "Which production lines had the most defects?"),
    ("revenue_trend", "Show the monthly revenue by category."),
    ("stock_ageing", "Which products have been sitting in stock too long?"),
    ("logistics_cost", "Which routes have become more expensive?"),
    ("returns_rate", "Which products have the highest return rate?"),
    ("customer_concentration", "Which customers account for the largest share of revenue?"),
    ("anomaly_detection", "What changed unusually last month?"),
)


class EnglishRoutingTests(unittest.TestCase):
    def test_english_questions_route_to_expected_intent(self) -> None:
        for expected, question in ENGLISH_ROUTING_CASES:
            with self.subTest(intent=expected):
                match = select_intent_match(question)
                self.assertIsNotNone(match.intent, f"pas d'intention pour: {question}")
                self.assertEqual(match.intent.id, expected)

    def test_english_write_requests_are_refused(self) -> None:
        cases = (
            "Delete all orders.",
            "Remove the supplier from the database.",
            "Update all product prices.",
            "Add a new customer.",
        )
        for question in cases:
            with self.subTest(question=question):
                self.assertTrue(is_write_request(question))
                self.assertIsNone(select_intent_match(question).intent)

    def test_english_read_questions_are_not_write_requests(self) -> None:
        for _, question in ENGLISH_ROUTING_CASES:
            with self.subTest(question=question):
                self.assertFalse(is_write_request(question))


class EnglishParameterTests(unittest.TestCase):
    def test_horizon_in_days(self) -> None:
        params = extract_query_parameters("a stockout in the next 14 days?")
        self.assertEqual(params.horizon_days, 14)

    def test_window_in_months(self) -> None:
        params = extract_query_parameters("revenue over the last 6 months")
        self.assertEqual(params.window_months, 6)

    def test_quarter_and_semester(self) -> None:
        self.assertEqual(extract_query_parameters("margin over the last quarter").window_months, 3)
        self.assertEqual(extract_query_parameters("revenue over the last semester").window_months, 6)

    def test_top_n_largest(self) -> None:
        params = extract_query_parameters("the 5 largest customers")
        self.assertEqual(params.top_n, 5)


if __name__ == "__main__":
    unittest.main()
