# FabriQ - Roadmap de developpement

FabriQ est un assistant d'analyse pour PME industrielles: une question en langage naturel, une requete SQL sure, une execution en lecture seule, puis une reponse lisible avec tableau, graphique, SQL visible et explication operationnelle.

## Etat actuel

Version stabilisee: `FabriQ v0.11.0`.

Version courante de developpement: `v0.12.0` (support anglais) et `v0.13.0` (webhooks sortants generiques) en cours, non taguees.

| Jalon | Etat | Commentaire |
| --- | --- | --- |
| Jalon 0 - Fondations techniques | Termine | Monorepo, FastAPI, React, Docker PostgreSQL, donnees demo. |
| Jalon 1 - Boucle coeur NL -> SQL -> reponse | Termine | 10 familles metier couvertes par templates deterministes. |
| Jalon 2 - Transparence, graphiques et experience utilisateur | Termine | UI question/reponse, graphique, tableau, SQL visible, observabilite. |
| Jalon 3 - Harnais d'evaluation | Termine | Golden set 10/10 contre PostgreSQL. |
| Jalon 4 - Portfolio et livraison | Termine | README, architecture, demo, release notes et verification v0.1.0. |
| Jalon 5 - V2 locale v0.2.0 | Termine | Routeur hybride, Ollama optionnel, clarifications guidees, catalogue semantique visible, evaluation paraphrases et health-check LLM. |
| Jalon 6 - V3 multi-utilisateurs v0.3.0 | Termine | LangGraph, Auth JWT, Multi-tenant, Alertes planifiees, Docker Compose complet. |
| Jalon 7 - V4 qualite et isolation v0.4.0 | Termine | Tenant SQL filtering, webhook alertes, export CSV, 23 tests, corrections qualite. |
| Jalon 8 - V5 robustesse et UX v0.5.0 | Termine | Chart dynamique, admin users, email SMTP, rate limiting, 30 tests. |
| Jalon 9 - V6 observabilite et administration v0.6.0 | Termine | Healthcheck DB, audit pagine, admin panel, Prometheus /metrics. |
| Jalon 10 - V7 performance et controle v0.7.0 | Termine | Cache TTL, filtres audit, desactivation users, Locust. |
| Jalon 11 - V8 DevOps et observabilite v0.8.0 | Termine | CI GitHub Actions, Grafana, Slack, JWT refresh. |
| Jalon 12 - V9 qualite et experience v0.9.0 | Termine | E2E Playwright, export PDF, toasts. |
| Jalon 13 - V10 portfolio et export v0.10.0 | Termine | Export xlsx audit, depot Git initialise, README/architecture/changelog actualises, 60 tests. |
| Jalon 14 - V11 gouvernance et bilingue v0.11.0 | Termine | Garde-fou AST + EXPLAIN + timeout, suite adversariale, parametres extraits des questions, allemand, refactor frontend, 78 tests. |
| Jalon 15 - V12 trilingue v0.12.0 | En cours | Support des questions en anglais, CI elargie a toute la suite tests, 85 tests. |
| Jalon 16 - V13 webhooks sortants v0.13.0 | En cours | Webhooks generiques par evenement, signature HMAC, reessais, garde SSRF, panneau UI, 107 tests. |

## Objectif MVP

Livrer une boucle fiable de bout en bout:

1. Question metier en francais.
2. Detection de l'intention et des donnees necessaires.
3. Generation d'une requete SQL bornee.
4. Validation stricte avant execution.
5. Execution en lecture seule sur une base industrielle de demonstration.
6. Reponse synthetique, tableau, graphique adapte et SQL transparent.
7. Journalisation pour mesurer les echecs et ameliorer le systeme.

## Principes directeurs

- Le LLM propose, le code decide.
- Aucune ecriture en base, jamais.
- Tout SQL est visible et explique.
- La precision est mesuree par le resultat d'execution, pas par similarite de texte.
- Le MVP reste serre: pas de SaaS, pas d'auth avancee, pas de RAG, pas d'ingestion PDF, pas de fine-tuning.

## Jalon 0 - Fondations techniques

Objectif: obtenir un projet reproductible et demonstrable.

- Monorepo `frontend` + `backend`.
- API FastAPI avec endpoint de sante et endpoint d'analyse.
- Frontend React avec interface applicative directe.
- Donnees industrielles de demonstration.
- Configuration locale documentee.
- Docker Compose pour PostgreSQL avec schema, seed et utilisateur read-only.

Succes:

- Le projet s'installe et demarre localement.
- Une question de test retourne une reponse structuree.
- Le code est suffisamment clair pour etre defendu en entretien.

## Jalon 1 - Boucle coeur NL -> SQL -> reponse

Objectif: implementer le flux MVP sans dependance LLM obligatoire.

- Catalogue semantique: tables, colonnes, metriques, synonymes.
- Classification d'intention sur les 10 familles du cahier des charges.
- Generation SQL structuree par templates verifies.
- Validation SQL: SELECT seul, allowlist tables/colonnes, LIMIT force, mots-cles interdits.
- Execution en lecture seule.
- Gestion des questions ambigues avec demande de precision.
- Reponse courte orientee metier.

Familles couvertes:

- Tendance de marge.
- Risque de rupture.
- Retard fournisseur.
- Efficacite production.
- Tendance de chiffre d'affaires.
- Vieillissement de stock.
- Cout logistique.
- Retours.
- Concentration clients.
- Detection d'anomalie.

Succes:

- Les 10 familles ont au moins un exemple fonctionnel.
- Les erreurs SQL sont bloquees avant execution.
- Chaque resultat expose le SQL, les donnees et une explication.

## Jalon 2 - Transparence, graphiques et experience utilisateur

Objectif: rendre l'outil utile et comprehensible.

- Interface chat question/reponse.
- Panneau SQL avec statut de validation.
- Tableau de resultats.
- Graphiques automatiques selon les donnees.
- Explication operationnelle lisible.
- Exemples de questions metier.
- Historique de session.
- Etats de chargement, erreur, clarification.

Succes:

- Un utilisateur comprend pourquoi la reponse est produite.
- Le graphique choisi correspond a la forme du resultat.
- Les resultats restent lisibles sur desktop et mobile.

## Jalon 3 - Harnais d'evaluation

Objectif: mesurer la fiabilite.

- Jeu golden pour les 10 familles.
- Resultats attendus stockes.
- Comparaison par execution et non par texte SQL.
- Mesures: validite SQL, exactitude resultat, pertinence graphique, taux d'echec.
- Journal des echecs avec type, question, SQL, raison.
- Script de rapport local.

Succes:

- Un rapport d'evaluation donne une precision mesurable.
- Les regressions sont visibles.
- Les cas ambigus sont classes proprement.

## Jalon 4 - Portfolio et livraison

Objectif: presenter un projet propre, fini et defendable.

- README clair: probleme, architecture, lancement, limites.
- Schema d'architecture.
- GIF de demonstration court.
- Donnees de demo realistes.
- Rapport d'evaluation.
- Docker Compose stable.
- Liste des tradeoffs et risques.

Succes:

- Le projet peut etre montre sans preparation lourde.
- Les choix techniques sont justifiables.
- Les limites sont explicites.

## Jalon 5 - V2 locale v0.2.0

Version livree: `v0.2.0`.

- Couche semantique enrichie avec synonymes plus fins.
- Detection d'ambiguite avancee.
- Selection de graphique plus deterministe.
- Branchement LLM local via Ollama.

Lot stable `v0.2.0`:

- Routeur d'intention hybride.
- Ollama optionnel via variables d'environnement.
- Fallback deterministe et clarification si Ollama est indisponible.
- SQL toujours genere par templates controles.
- Statut LLM expose dans `/api/health`.
- Strategie de routage visible dans l'UI.
- Trace d'orchestration exposee par l'API et visible dans l'UI.
- Clarifications guidees exposees par l'API et cliquables dans l'UI.
- Catalogue semantique enrichi avec descriptions d'intentions, synonymes metier, tables et colonnes.
- Endpoint `GET /api/catalog` pour exposer ce catalogue.
- Suite d'evaluation paraphrases: 10/10 en local.
- Ping Ollama non bloquant expose dans `/api/health`.
- Statut LLM visible dans l'UI: pret, desactive, modele manquant ou indisponible.
- Catalogue semantique visible dans l'UI avec intentions, questions exemples, tables et colonnes.

## Jalon 6 - V3 multi-utilisateurs v0.3.0

Version livree: `v0.3.0`.

- Graphe LangGraph remplace le pipeline lineaire (`StateGraph` avec `TypedDict`, reducers, edges conditionnels).
- Auth JWT: login, protection des routes, token localStorage, page de connexion.
- Multi-tenant: `tenant_id` propage JWT -> LangGraph state -> audit JSONL.
- Alertes planifiees: `APScheduler` + regles CRUD + panneau UI alertes/evenements.
- Docker Compose complet: 3 services (postgres, backend, frontend nginx non-root).
- Script `scripts/init_env.py` pour generer `.env` avec hash bcrypt.

## Jalon 7 - V4 qualite et isolation v0.4.0

Version livree: `v0.4.0`.

- Tenant SQL filtering: `inject_tenant_filter()` dans `execute_node` (Postgres, JWT uniquement).
- Schema DB: colonne `tenant_id` sur `orders` et `customers`; seed 2 tenants (`tenant_demo`, `tenant_acme`).
- Webhook alertes: `webhook_url` optionnel sur `AlertRule`, POST JSON best-effort a l'evenement.
- Correction bug scheduler: jobs appelaient `evaluate_rule` sans persister -> remplace par `_fire_rule`.
- Export CSV audit: `GET /api/audit/export` filtre par tenant + bouton frontend.
- 21 tests au total (14 legacy + 7 nouveaux v0.4.0): `inject_tenant_filter`, `export_csv`, endpoint CSV.
- FastAPI `lifespan` remplace `@app.on_event("startup")` deprecie.
- Docker: `nginx-unprivileged` (non-root), `.dockerignore`, `VITE_API_URL=''` au build.

## Jalon 8 - V5 robustesse et UX v0.5.0

Version livree: `v0.5.0`.

- Chart dynamique: `_adjust_chart()` dans `compose_answer_node` (line/area ≤2 pts → bar, bar + temps + ≥4 pts → area).
- Admin users: `GET /api/admin/users` (role admin requis, 403 sinon), `require_admin` dependency.
- Email SMTP optionnel: `email_to: list[str]` sur `AlertRule`, `send_alert_email()` via smtplib stdlib.
- Rate limiting: `slowapi` sur `/api/auth/login` (10/min) et `/api/ask` (30/min).
- 31 tests au total: 14 legacy + 9 V4 + 8 V5.

## Jalon 9 - V6 observabilite et administration v0.6.0

Version livree: `v0.6.0`.

- Healthcheck DB: methode `ping()` sur `SQLiteDatabase` et `PostgresDatabase`, champ `db_ok` + `db_latency_ms` dans `/api/health`.
- Audit pagine: `GET /api/audit/recent?page=1&limit=10` retourne `{events, total, page, limit}`, panneau frontend avec boutons precedent/suivant.
- Export alertes CSV: `export_alert_events_csv()`, endpoint `GET /api/alerts/events/export`, bouton dans AlertsPanel.
- Admin panel frontend: `AdminPanel` visible pour role=admin, tableau email/tenant/role via `GET /api/admin/users`.
- Prometheus: `prometheus-fastapi-instrumentator`, endpoint `/metrics` exposant `http_requests_total` et latences.
- 38 tests au total: 14 legacy + 9 V4 + 9 V5 + 6 V6.

## Jalon 10 - V7 performance et controle v0.7.0

Version livree: `v0.7.0`.

- Filtres audit: `GET /api/audit/recent?intent=X&validation_ok=true`, UI select dans ObservabilityPanel.
- Cache TTL 5min: `TTLCache` thread-safe dans `cache.py`, integre dans `execute_node` (cle: sql + tenant_id).
- Pagination alertes: `recent_alert_events(page, limit)` → `(events, total)`, boutons precedent/suivant dans AlertsPanel.
- Desactivation utilisateur: `disabled_users.py` (JSON file), `POST /api/admin/users/{email}/disable|enable`, boutons dans AdminPanel.
- Locust: `tests/locustfile.py` avec `FabriqUser` (ask x5, audit x2, alerts x1) et `AnonUser` (health, metrics).
- 49 tests au total: 14 legacy + 9 V4 + 9 V5 + 7 V6 + 10 V7.

## Jalon 11 - V8 DevOps et observabilite v0.8.0

Version livree: `v0.8.0`.

- CI GitHub Actions: `.github/workflows/ci.yml` — 3 jobs (backend pytest+ruff, frontend tsc+build, docker smoke test).
- OpenAPI enrichie: `tags`, `summary`, `response_description` sur tous les endpoints + `openapi_tags` + description globale.
- Slack notifications: `fire_slack()` dans alerts.py, `slack_webhook_url` sur AlertRule, `FABRIQ_SLACK_WEBHOOK` env global.
- JWT refresh: `POST /api/auth/refresh` + auto-refresh frontend toutes les 55 min via `setInterval`.
- Prometheus + Grafana: services dans docker-compose, `monitoring/prometheus.yml`, datasource et dashboard provisiones.
- 55 tests au total: 49 V1-V7 + 6 V8.

## Jalon 12 - V9 Qualite et experience v0.9.0

Version livree: `v0.9.0`.

- Tests E2E Playwright: `frontend/e2e/` — 3 suites (auth, ask, observability), config `playwright.config.ts`, job CI dedie avec upload d'artefacts en cas d'echec.
- Export PDF: bouton "Exporter PDF" sur le panneau de resultats, CSS `@media print` masquant topbar/pipeline/filtres, mise en page propre pour impression.
- Toast notifications: hook `useToast` + composant `ToastContainer` (success/error/info), feedback visuel sur create/delete alerte, toggle user, export CSV.
- 55 tests backend au total (inchange).

## Jalon 13 - V10 portfolio et export v0.10.0

Version livree: `v0.10.0`.

- Export Excel (xlsx) du journal d'audit: `export_xlsx()` dans `audit.py`, endpoint `GET /api/audit/export.xlsx`, bouton frontend.
- Depot Git initialise avec tag `v0.10.0` (le projet n'etait pas versionne jusque-la).
- README reecrit pour refleter l'etat reel (auth, multi-tenant, LangGraph, alertes, monitoring, CI, E2E).
- `docs/ARCHITECTURE.md` actualise (graphe LangGraph, securite, tradeoffs v0.10).
- `CHANGELOG.md` consolide v0.1.0 -> v0.10.0.
- 60 tests backend au total (55 en v0.9.0, +5 depuis).

## Jalon 14 - V11 gouvernance et bilingue v0.11.0

Version livree: `v0.11.0`.

- Garde-fou SQL v2 : parseur AST sqlglot (SELECT pur, allowlist sur l'arbre, LIMIT litteral borne), EXPLAIN prealable, timeout via `FABRIQ_QUERY_TIMEOUT_SECONDS`.
- Suite adversariale : 24 tentatives d'injection bloquees (`tests/test_sql_guard_adversarial.py`).
- Extraction de parametres deterministe : top N, horizon jours, fenetre mois (FR et DE), bindes dans les templates et visibles dans la trace d'orchestration.
- Routeur durci : deduplication des mots-cles imbriques, refus des demandes d'ecriture sans consulter le LLM.
- Support des questions en allemand : mots-cles, verbes d'ecriture, parametres, suite `evaluation/german.json` 15/15.
- Frontend refactore : App.tsx 1567 -> 667 lignes, 13 modules, tests Vitest, etape Unit tests en CI.
- Golden 43/43, paraphrases 10/10, german 15/15, 78 tests + 135 sous-tests.

## Jalon 15 - V12 trilingue v0.12.0

Version en cours (non taguee).

- Support des questions en anglais : mots-cles EN sur les 10 intentions, verbes d'ecriture refuses (remove, update, delete, add...), parametres extraits (next N days, last N months, quarter, semester, N largest).
- Suite d'evaluation `evaluation/english.json`, lancee par `scripts/evaluate.py --suite=english` : 15/15.
- Detection d'ecriture affinee : "drop" retire de la detection en langage naturel ("margin drop" est une tournure de lecture) ; un vrai `DROP TABLE` reste bloque par le garde-fou SQL (parseur AST).
- CI elargie : le job backend execute toute la suite `tests` (avant : seul `test_agent.py`), couvrant en CI l'allemand, l'anglais et les parametres.
- Golden 43/43, paraphrases 10/10, german 15/15, english 15/15, 85 tests + 159 sous-tests.

## Jalon 16 - V13 webhooks sortants v0.13.0

Version en cours (non taguee).

- Emetteur d'evenements central (`app/webhooks.py`) decouple des alertes : souscription = URL + types abonnes + secret HMAC, persistance JSON par tenant.
- Types d'evenements : `question.answered`, `question.blocked` (depuis `/api/ask`), `auth.login_failed` (login), `alert.fired` (pont depuis `alerts._fire_rule`).
- Livraison signee HMAC-SHA256 (`X-FabriQ-Signature`), reessais a backoff (0/5/30 s), journal de livraison JSONL par tentative, emission non bloquante.
- Garde anti-SSRF : refus des URLs internes (loopback / prive / link-local / reserve) et des schemas non HTTP(S).
- 6 endpoints `/api/webhooks*` (CRUD, event-types, test, deliveries) scopes par tenant ; panneau `WebhooksPanel` cote frontend.
- Le champ `webhook_url` par-regle des alertes reste pour retrocompatibilite (deprecie).

## Horizon suivant

Prochaine version possible: `v0.14.0`.

- Authentification OAuth2 / SSO (Keycloak ou Auth0) en remplacement des users env.
- Demo en ligne optionnelle.
