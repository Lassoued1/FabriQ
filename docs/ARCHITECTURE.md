# FabriQ - Architecture

Document aligne sur la v0.10.0. Le coeur du systeme reste deterministe, auditable et protege par un garde-fou SQL: le LLM local est optionnel et cantonne au routage d'intention.

## Vue d'ensemble

```text
+-------------------+       +---------------------+       +--------------------+
| Utilisateur metier| ----> | Frontend React/Vite | ----> | FastAPI backend    |
| (login JWT)       |       | chat, graphiques,   |       | rate limiting,     |
+-------------------+       | admin, alertes,     |       | auth JWT, tenant   |
                            | audit, export       |       +----------+---------+
                            +---------------------+                  |
                                                                     v
                            +----------------------------------------+---------+
                            | Graphe LangGraph (StateGraph)                    |
                            |  route_intent -> build_sql -> validate_sql       |
                            |  -> execute (cache TTL, filtre tenant)           |
                            |  -> compose_answer (chart dynamique)             |
                            |  routeur hybride: mots-cles puis Ollama optionnel|
                            +----------------------------------------+---------+
                                                                     |
                                                                     v
                            +----------------------------------------+---------+
                            | SQL guard: SELECT seul, allowlist tables,        |
                            | mots-cles bloques, LIMIT force, mono-instruction |
                            +----------------------------------------+---------+
                                                                     |
                                                                     v
                            +----------------------------------------+---------+
                            | SQLite local ou PostgreSQL Docker                |
                            | role fabriq_readonly (aucun droit d'ecriture)    |
                            +----------------------------------------+---------+
                                                                     |
                +--------------------+---------------------+--------+
                v                    v                     v
      +---------+------+  +----------+---------+  +--------+---------+
      | Audit JSONL    |  | Alertes APScheduler|  | Prometheus       |
      | trace id,      |  | webhook, Slack,    |  | /metrics         |
      | export CSV/xlsx|  | e-mail SMTP        |  | + Grafana        |
      +----------------+  +--------------------+  +------------------+
```

## Composants

| Composant | Fichier principal | Role |
| --- | --- | --- |
| Frontend | `frontend/src/App.tsx` | Login, chat question/reponse, graphiques, tableau, SQL, pipeline, panneaux admin/alertes/audit/catalogue, exports PDF/CSV/xlsx. |
| API | `backend/app/main.py` | Endpoints health, auth, ask, catalog, audit, alerts, admin. Rate limiting slowapi. |
| Graphe | `backend/app/graph.py` | Orchestration LangGraph: routage, generation SQL, validation, execution, composition de la reponse. |
| Auth | `backend/app/auth.py` | JWT (login, refresh), utilisateurs env bcrypt, roles admin/user, tenant. |
| Couche semantique | `backend/app/semantic_layer.py` | Catalogue d'intentions, synonymes, templates SQL SQLite/PostgreSQL, formats de graphiques. |
| LLM | `backend/app/llm.py` | Client Ollama optionnel, routeur d'intention en repli, ping non bloquant. |
| SQL guard | `backend/app/sql_guard.py` | Validation stricte avant execution. |
| Database | `backend/app/database.py` | Abstraction SQLite/PostgreSQL, `ping()` healthcheck, lecture seule. |
| Cache | `backend/app/cache.py` | Cache TTL 5 min thread-safe des resultats SQL (cle: sql + tenant). |
| Audit | `backend/app/audit.py` | JSONL avec trace id, pagination, filtres, exports CSV et xlsx. |
| Alertes | `backend/app/alerts.py` | Regles CRUD, APScheduler, notifications webhook/Slack/e-mail. |
| Admin | `backend/app/disabled_users.py` | Desactivation/reactivation de comptes (fichier JSON). |
| Evaluation | `backend/scripts/evaluate.py` | Harnais golden + paraphrases, compare par resultat d'execution. |
| PostgreSQL | `backend/db/*.sql` | Schema industriel, seed 2 tenants, role `fabriq_readonly`. |
| Monitoring | `monitoring/` | Prometheus scrape config, datasource et dashboard Grafana provisionnes. |
| CI | `.github/workflows/ci.yml` | pytest + ruff, tsc + build, smoke test Docker, E2E Playwright. |

## Flux d'analyse

1. L'utilisateur se connecte (JWT) puis pose une question en francais.
2. Le routeur deterministe classe l'intention par mots-cles; si le score est insuffisant et qu'Ollama est configure, le LLM propose une intention du catalogue (jamais de SQL).
3. Si l'ambiguite persiste, l'API retourne des options de clarification cliquables.
4. La couche semantique genere le SQL par template selon le dialecte courant.
5. Le SQL guard valide la requete; le filtre tenant est injecte a l'execution.
6. La base execute en lecture seule (cache TTL en amont).
7. La reponse est composee: texte metier, tableau, graphique adapte a la forme des donnees, SQL visible, trace d'orchestration.
8. L'audit enregistre la trace; Prometheus compte et mesure; les alertes planifiees tournent en tache de fond.

## Securite

- **Base**: role PostgreSQL `fabriq_readonly` sans aucun droit d'ecriture.
- **Application**: SELECT obligatoire, allowlist de tables, mots-cles d'ecriture/administration bloques, LIMIT force (<= 100), mono-instruction.
- **API**: JWT obligatoire sur toutes les routes metier, roles admin, rate limiting login/ask.
- **Isolation**: filtrage SQL par `tenant_id` injecte cote serveur, jamais fourni par le client.
- **LLM**: aucun acces a la base, aucune generation de SQL, sortie contrainte au catalogue d'intentions.

Ameliorations prevues: parseur AST formel (sqlglot), validation EXPLAIN avant execution, timeout de requete cote base.

## Donnees

Schema industriel de demonstration: produits, commandes, clients, fournisseurs, retards fournisseurs, lots de production, mouvements de stock, expeditions, retours, couts. Deux tenants seedes (`tenant_demo`, `tenant_acme`) pour demontrer l'isolation.

## Decisions techniques

- FastAPI pour une API typee, testable et auto-documentee (OpenAPI).
- LangGraph pour une orchestration a etats explicite et extensible.
- React + Vite + Recharts pour une interface directe.
- PostgreSQL Docker reproductible; SQLite en fallback leger pour le dev et les tests.
- Templates SQL deterministes: la fiabilite prime sur la couverture.
- Ollama local optionnel: aucune dependance cloud, aucune cle API.
- Audit JSONL local: simple, lisible, suffisant pour la demo; Prometheus/Grafana pour les metriques.

## Tradeoffs

| Choix | Benefice | Limite |
| --- | --- | --- |
| Routage deterministe d'abord | Stable, explicable, evaluable | Moins flexible qu'un text-to-SQL libre |
| Templates SQL | Requetes controlees et testables | Couverture limitee aux 10 intentions |
| LLM = routeur seulement | Zero risque d'injection SQL par LLM | Le LLM n'apporte pas de nouvelles requetes |
| Utilisateurs en env | Zero dependance externe | Pas de SSO/OAuth2, rotation manuelle |
| Garde-fou regex + allowlist | Simple, rapide, lisible | Pas un parseur AST formel (prevu) |
| Base demo seedee | Demo reproductible | Pas de donnees client reelles |
