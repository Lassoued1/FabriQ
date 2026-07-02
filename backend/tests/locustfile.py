"""
FabriQ load test — run with:
    locust -f tests/locustfile.py --host http://localhost:8000

Environment variables:
    LOCUST_EMAIL    (default: admin@fabriq.io)
    LOCUST_PASSWORD (default: demo)

Scenarios:
    FabriqUser  — authenticate once, then mix of /ask and /audit/recent
    AnonUser    — unauthenticated health checks (lightweight baseline)
"""
from __future__ import annotations

import os
import random

from locust import HttpUser, between, task


_EMAIL = os.getenv("LOCUST_EMAIL", "admin@fabriq.io")
_PASSWORD = os.getenv("LOCUST_PASSWORD", "demo")

_QUESTIONS = [
    "Quelle est la tendance de marge ce trimestre ?",
    "Quels produits sont en risque de rupture ?",
    "Montre-moi les retards fournisseurs des 30 derniers jours.",
    "Quel est le taux de retours par famille de produits ?",
    "Quelle est l'evolution du chiffre d'affaires mensuel ?",
    "Y a-t-il des anomalies dans les niveaux de stock ?",
    "Quelle est la concentration de mes 5 meilleurs clients ?",
    "Donne-moi le cout logistique par famille d'expedition.",
    "Quel est le vieillissement moyen du stock par categorie ?",
    "Quels sont les indicateurs d'efficacite de production ?",
]


class FabriqUser(HttpUser):
    """Authenticated user — realistic usage mix."""

    wait_time = between(1, 3)
    _token: str | None = None

    def on_start(self) -> None:
        res = self.client.post("/api/auth/login", json={"email": _EMAIL, "password": _PASSWORD})
        if res.status_code == 200:
            self._token = res.json().get("access_token")

    def _auth(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"} if self._token else {}

    @task(5)
    def ask_question(self) -> None:
        question = random.choice(_QUESTIONS)
        self.client.post("/api/ask", json={"question": question}, headers=self._auth(), name="/api/ask")

    @task(2)
    def get_audit(self) -> None:
        self.client.get("/api/audit/recent?page=1&limit=10", headers=self._auth(), name="/api/audit/recent")

    @task(1)
    def get_alerts(self) -> None:
        self.client.get("/api/alerts", headers=self._auth(), name="/api/alerts")

    @task(1)
    def get_catalog(self) -> None:
        self.client.get("/api/catalog", headers=self._auth(), name="/api/catalog")


class AnonUser(HttpUser):
    """Unauthenticated probe — health and metrics only."""

    wait_time = between(5, 15)
    weight = 1

    @task
    def health_check(self) -> None:
        self.client.get("/api/health", name="/api/health")

    @task
    def metrics_check(self) -> None:
        self.client.get("/metrics", name="/metrics")
