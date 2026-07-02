# FabriQ

FabriQ est un assistant d'analyse pour PME industrielles: une question en langage naturel, une requete SQL sure, une execution en lecture seule, puis une reponse lisible avec tableau, graphique, SQL visible et explication operationnelle.

**Version courante: v0.10.0** — multi-utilisateurs, multi-tenant, orchestration LangGraph, alertes planifiees, observabilite Prometheus/Grafana, CI et tests E2E.

## Probleme

Dans une PME industrielle, les donnees de production, stock, ventes, fournisseurs, retours et logistique restent souvent enfermees dans des bases relationnelles. Les utilisateurs metier ont besoin de reponses rapides sans ecrire de SQL et sans risquer de modifier la base.

FabriQ transforme une question metier en requete SQL validee, execute cette requete en lecture seule, puis restitue un resultat comprehensible et auditable.

## Principes de conception

- **Le LLM propose, le code decide.** Le LLM local (Ollama, optionnel) ne sert que de routeur d'intention en repli du routeur deterministe. Il ne genere jamais de SQL.
- **Aucune ecriture en base, jamais.** Role PostgreSQL `fabriq_readonly` + garde-fou applicatif (SELECT seul, allowlist de tables, mots-cles bloques, LIMIT force, mono-instruction).
- **Tout est transparent.** Le SQL, la trace d'orchestration et l'explication metier sont visibles dans chaque reponse.
- **La precision se mesure par le resultat d'execution**, pas par similarite de texte SQL. Harnais golden 10/10 + suite paraphrases 10/10.

## Fonctionnalites

### Coeur d'analyse

- Interface React pour poser une question metier en francais.
- Routeur hybride: mots-cles deterministes d'abord, Ollama optionnel en repli.
- Couche semantique: 10 familles de questions industrielles (marge, rupture, retards fournisseurs, production, CA, stock, logistique, retours, clients, anomalies).
- Generation SQL par templates controles, validation stricte avant execution.
- Reponse metier, tableau, graphique adapte a la forme des donnees, SQL visible.
- Clarifications guidees avec options cliquables quand la question est ambigue.
- Catalogue semantique expose (`GET /api/catalog`) et visible dans l'UI.

### Multi-utilisateurs et securite

- Authentification JWT (login, refresh automatique, page de connexion).
- Multi-tenant: `tenant_id` propage du JWT jusqu'au filtrage SQL et a l'audit.
- Roles utilisateur (admin/user), panneau admin (liste, activation/desactivation de comptes).
- Rate limiting sur le login et l'analyse.

### Alertes et observabilite

- Alertes planifiees (APScheduler): regles CRUD, notifications webhook, Slack et e-mail SMTP.
- Journal d'audit JSONL avec trace id, pagine et filtrable, export CSV et Excel.
- Export PDF du rapport d'analyse cote frontend.
- Endpoint Prometheus `/metrics`, dashboard Grafana provisionne.
- Panneau d'observabilite frontend: sante API, base active, statut LLM, traces recentes.

### Qualite

- 60 tests backend (pytest), suites E2E Playwright (auth, analyse, observabilite).
- CI GitHub Actions: backend (pytest + ruff), frontend (tsc + build), smoke test Docker, E2E.
- Tests de charge Locust.
- Harnais d'evaluation golden et paraphrases, compares par resultat d'execution.

## Architecture

Le schema et les decisions techniques sont detailles dans [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

```text
Utilisateur
  -> Frontend React/Vite (auth JWT, chat, graphiques, panneaux admin/alertes/audit)
  -> API FastAPI (rate limiting, multi-tenant)
  -> Graphe LangGraph (routage -> SQL template -> validation -> execution -> reponse)
  -> SQL guard + role PostgreSQL read-only
  -> Reponse + graphique + trace d'orchestration + audit JSONL
  -> Prometheus / Grafana
```

## Demarrage rapide (Docker Compose)

```bash
cp .env.example .env
python scripts/init_env.py   # genere JWT secret et utilisateurs bcrypt
docker compose up -d
```

Services: frontend `http://localhost:80`, API `http://localhost:8000`, Prometheus `http://localhost:9090`, Grafana `http://localhost:3000`.

## Demarrage local (developpement)

### 1. PostgreSQL

```bash
docker compose up -d postgres
```

La base expose `localhost:5432` et cree automatiquement le role applicatif read-only `fabriq_readonly`.

### 2. Backend

```bash
cd backend
python -m pip install -r requirements.txt
$env:FABRIQ_DATABASE_URL="postgresql://fabriq_readonly:fabriq_readonly@127.0.0.1:5432/fabriq"
python -m uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Ouvrir `http://localhost:5173`.

## LLM local optionnel

Le comportement par defaut reste deterministe et fonctionne sans LLM.

```bash
$env:FABRIQ_LLM_PROVIDER="ollama"
$env:FABRIQ_OLLAMA_URL="http://127.0.0.1:11434"
$env:FABRIQ_OLLAMA_MODEL="llama3.1"
```

Le statut LLM est expose dans `/api/health` (non bloquant) et visible dans l'UI.

## API

| Groupe | Endpoints |
| --- | --- |
| Sante | `GET /api/health`, `GET /metrics` |
| Auth | `POST /api/auth/login`, `POST /api/auth/refresh`, `GET /api/auth/me` |
| Analyse | `POST /api/ask` |
| Catalogue | `GET /api/catalog`, `GET /api/examples` |
| Audit | `GET /api/audit/recent`, `GET /api/audit/export`, `GET /api/audit/export.xlsx` |
| Alertes | `GET/POST /api/alerts`, `DELETE /api/alerts/{id}`, `GET /api/alerts/events`, `GET /api/alerts/events/export` |
| Admin | `GET /api/admin/users`, `POST /api/admin/users/{email}/disable`, `POST /api/admin/users/{email}/enable` |

Documentation interactive: `http://localhost:8000/docs` (OpenAPI).

## Evaluation

```bash
cd backend
python scripts/evaluate.py --database=env
python scripts/evaluate.py --database=env --suite=paraphrases
```

Les rapports sont ecrits dans `backend/reports/`. Documentation: [docs/EVALUATION.md](docs/EVALUATION.md).

## Tests

```bash
cd backend
python -m pytest tests -q          # 60 tests

cd frontend
npm run build && npm run lint
npx playwright test                # E2E
```

## Demo

Scenario de demonstration: [docs/DEMO.md](docs/DEMO.md).

Questions recommandees:

- `Quels fournisseurs ont ete le plus souvent en retard ?`
- `Montre le chiffre d'affaires mensuel par categorie.`
- `Quels SKU risquent une rupture dans les 14 prochains jours ?`
- `Quels produits ont vu leur marge baisser le trimestre dernier ?`

## Limites explicites

- Utilisateurs declares en variables d'environnement (pas encore de SSO/OAuth2 externe).
- Questions en francais uniquement.
- Pas d'ingestion PDF ni de RAG documentaire, pas de fine-tuning.
- Ollama reste optionnel et local.
- La base de donnees est une base industrielle de demonstration, pas une base client.
- Le garde-fou SQL est applicatif (regex + allowlist) adosse au role read-only; un parseur AST formel et une validation EXPLAIN restent des ameliorations prevues.

## Historique et roadmap

- Historique des versions: [CHANGELOG.md](CHANGELOG.md)
- Roadmap detaillee: [docs/ROADMAP.md](docs/ROADMAP.md)
- Cahier des charges d'origine: [Cahier de charges.pdf](Cahier%20de%20charges.pdf)
