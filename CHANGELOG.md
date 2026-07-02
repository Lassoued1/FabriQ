# Changelog

Historique des versions de FabriQ. Le detail complet de chaque jalon est dans [docs/ROADMAP.md](docs/ROADMAP.md).

## v0.10.0 — 2 juillet 2026

- Export Excel (xlsx) du journal d'audit: `GET /api/audit/export.xlsx` + bouton frontend.
- Remise a niveau portfolio: depot Git initialise, README et architecture actualises, changelog consolide.
- 60 tests backend.

## v0.9.0 — Qualite et experience

- Tests E2E Playwright: 3 suites (auth, ask, observability), job CI dedie avec artefacts en cas d'echec.
- Export PDF du panneau de resultats (CSS `@media print`).
- Toast notifications (success/error/info) sur les actions utilisateur.

## v0.8.0 — DevOps et observabilite

- CI GitHub Actions: backend (pytest + ruff), frontend (tsc + build), smoke test Docker.
- Prometheus + Grafana provisionnes dans docker-compose.
- Notifications Slack sur les alertes (webhook global ou par regle).
- JWT refresh: `POST /api/auth/refresh` + auto-refresh frontend.
- OpenAPI enrichie (tags, resumes, descriptions).

## v0.7.0 — Performance et controle

- Cache TTL 5 min sur l'execution SQL (cle: sql + tenant).
- Filtres du journal d'audit (intention, statut de validation).
- Pagination des evenements d'alerte.
- Desactivation/reactivation d'utilisateurs par l'admin.
- Tests de charge Locust.

## v0.6.0 — Observabilite et administration

- Healthcheck DB (`db_ok`, `db_latency_ms`) dans `/api/health`.
- Journal d'audit pagine, export CSV des evenements d'alerte.
- Panneau admin frontend (role admin requis).
- Endpoint Prometheus `/metrics`.

## v0.5.0 — Robustesse et UX

- Selection de graphique dynamique selon la forme des donnees.
- Endpoint admin users avec controle de role (403 sinon).
- Notifications e-mail SMTP optionnelles sur les alertes.
- Rate limiting: login 10/min, analyse 30/min.

## v0.4.0 — Qualite et isolation

- Filtrage SQL par tenant injecte a l'execution (PostgreSQL + JWT).
- Colonne `tenant_id` sur `orders` et `customers`, seed 2 tenants.
- Webhook optionnel par regle d'alerte.
- Export CSV du journal d'audit filtre par tenant.
- Docker: nginx non-root, `.dockerignore`.

## v0.3.0 — Multi-utilisateurs

- Orchestration LangGraph (`StateGraph`, reducers, edges conditionnels) remplace le pipeline lineaire.
- Authentification JWT: login, protection des routes, page de connexion.
- Multi-tenant: `tenant_id` propage JWT -> etat LangGraph -> audit.
- Alertes planifiees APScheduler avec regles CRUD et panneau UI.
- Docker Compose complet (postgres, backend, frontend).

## v0.2.0 — V2 locale

- Routeur d'intention hybride: deterministe d'abord, Ollama optionnel en repli.
- Le LLM ne genere jamais de SQL et ne propose qu'une intention du catalogue.
- Clarifications guidees avec options cliquables.
- Catalogue semantique expose (`GET /api/catalog`) et visible dans l'UI.
- Trace d'orchestration dans chaque reponse.
- Suite d'evaluation paraphrases: 10/10.
- Health-check Ollama non bloquant.

## v0.1.0 — MVP

- Boucle NL -> SQL -> validation -> execution -> reponse, sans LLM obligatoire.
- 10 familles de questions industrielles par templates SQL deterministes.
- Garde-fou SQL: SELECT seul, allowlist de tables, mots-cles bloques, LIMIT force.
- Execution en lecture seule (SQLite local ou PostgreSQL Docker, role `fabriq_readonly`).
- UI React: question, reponse metier, tableau, graphique, SQL visible.
- Audit JSONL avec trace id, harnais d'evaluation golden 10/10.
