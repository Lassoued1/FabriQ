# FabriQ

[![CI](https://github.com/Lassoued1/FabriQ/actions/workflows/ci.yml/badge.svg)](https://github.com/Lassoued1/FabriQ/actions/workflows/ci.yml)

> **Portfolio Notice**
> This repository is a demonstrative, standalone build shared for portfolio purposes. It showcases architecture, technical decisions, and code quality. The database is an industrial demo dataset, not a client database.

FabriQ is an analytics assistant for industrial SMEs: ask a question in natural language, get a safe SQL query, executed read-only, then a readable answer with table, chart, visible SQL, and an operational explanation.

**Current version: v0.11.0** (v0.12.0 and v0.13.0 in progress, not yet tagged: English questions, generic outbound webhooks) — questions in French, German and English driving parameterized queries, AST-parser SQL guardrail, multi-user, multi-tenant, LangGraph orchestration, scheduled alerts, outbound webhooks, Prometheus/Grafana observability, CI and E2E tests.

![FabriQ demo](docs/assets/fabriq-v0.11.0-demo.gif)

## Problem

In an industrial SME, production, stock, sales, supplier, returns, and logistics data often stays locked inside relational databases. Business users need fast answers without writing SQL and without risking any modification to the database.

FabriQ turns a business question into a validated SQL query, executes that query read-only, then returns a result that is understandable and auditable.

## Design principles

- **The LLM proposes, the code decides.** The optional local LLM (Ollama) only acts as an intent router, as a fallback to the deterministic router. It never generates SQL.
- **No writes to the database, ever.** Dedicated PostgreSQL role `fabriq_readonly` + an application-level guardrail (SELECT only, table allowlist, blocked keywords, forced LIMIT, single statement only).
- **Everything is transparent.** The SQL, the orchestration trace, and the business explanation are visible in every response.
- **Accuracy is measured by execution result**, not by SQL text similarity. 83 cases across four suites, all passing: golden 43/43, paraphrases 10/10, German 15/15, English 15/15.

## Features

### Analytics core

- React interface to ask a business question in French, German or English.
- Hybrid router: deterministic keywords first, optional Ollama as fallback.
- Semantic layer: 10 families of industrial questions (margin, stockouts, supplier delays, production, revenue, inventory, logistics, returns, customers, anomalies).
- SQL generation via controlled templates, strict validation before execution.
- Business-readable answer, table, chart adapted to the data shape, visible SQL.
- Guided clarifications with clickable options when a question is ambiguous.
- Exposed semantic catalog (`GET /api/catalog`), also visible in the UI.

### Multi-user & security

- JWT authentication (login, automatic refresh, login page).
- Multi-tenant: `tenant_id` propagated from the JWT down to SQL filtering and audit logging.
- User roles (admin/user), admin panel (list, enable/disable accounts).
- Rate limiting on login and analysis endpoints.

### Alerts & observability

- Scheduled alerts (APScheduler): CRUD rules, webhook, Slack, and SMTP email notifications.
- Generic outbound webhooks: per-tenant subscriptions by event type (`question.answered`, `question.blocked`, `alert.fired`, `auth.login_failed`), HMAC-SHA256 signed delivery with retry backoff, SSRF guard, delivery log.
- JSONL audit log with trace ID, paginated and filterable, CSV and Excel export.
- PDF export of the analysis report on the frontend.
- Prometheus `/metrics` endpoint, provisioned Grafana dashboard.
- Frontend observability panel: API health, active database, LLM status, recent traces.

### Quality

- 107 backend tests (pytest), 9 frontend unit tests (Vitest), and 10 Playwright E2E tests.
- GitHub Actions CI: backend (pytest + ruff), frontend (tsc + build), Docker smoke test, E2E.
- Load testing with Locust.
- Golden and paraphrase evaluation harness, compared by execution result.

## Architecture

Full schema and technical decisions are detailed in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

```text
User
  -> React/Vite frontend (JWT auth, chat, charts, admin/alerts/audit panels)
  -> FastAPI (rate limiting, multi-tenant)
  -> LangGraph graph (routing -> SQL template -> validation -> execution -> response)
  -> SQL guard + read-only PostgreSQL role
  -> Response + chart + orchestration trace + JSONL audit
  -> Prometheus / Grafana
```

## Quick start (Docker Compose)

```bash
cp .env.example .env
python scripts/init_env.py   # generates JWT secret and bcrypt users
docker compose up -d
```

Services: frontend `http://localhost:80`, API `http://localhost:8000`, Prometheus `http://localhost:9090`, Grafana `http://localhost:3000`.

## Local development

### 1. PostgreSQL

```bash
docker compose up -d postgres
```

The database exposes `localhost:5432` and automatically creates the read-only application role `fabriq_readonly`.

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

Open `http://localhost:5173`.

## Optional local LLM

Default behavior stays fully deterministic and works without any LLM.

```bash
$env:FABRIQ_LLM_PROVIDER="ollama"
$env:FABRIQ_OLLAMA_URL="http://127.0.0.1:11434"
$env:FABRIQ_OLLAMA_MODEL="llama3.1"
```

LLM status is exposed in `/api/health` (non-blocking) and visible in the UI.

## API

| Group | Endpoints |
| --- | --- |
| Health | `GET /api/health`, `GET /metrics` |
| Auth | `POST /api/auth/login`, `POST /api/auth/refresh`, `GET /api/auth/me` |
| Analysis | `POST /api/ask` |
| Catalog | `GET /api/catalog`, `GET /api/examples` |
| Audit | `GET /api/audit/recent`, `GET /api/audit/export`, `GET /api/audit/export.xlsx` |
| Alerts | `GET/POST /api/alerts`, `DELETE /api/alerts/{id}`, `GET /api/alerts/events`, `GET /api/alerts/events/export` |
| Webhooks | `GET /api/webhooks/event-types`, `GET/POST /api/webhooks`, `DELETE /api/webhooks/{id}`, `POST /api/webhooks/{id}/test`, `GET /api/webhooks/{id}/deliveries` |
| Admin | `GET /api/admin/users`, `POST /api/admin/users/{email}/disable`, `POST /api/admin/users/{email}/enable` |

Interactive documentation: `http://localhost:8000/docs` (OpenAPI).

## Evaluation

```bash
cd backend
python scripts/evaluate.py --database=env
python scripts/evaluate.py --database=env --suite=paraphrases
python scripts/evaluate.py --database=env --suite=german
python scripts/evaluate.py --database=env --suite=english
```

Reports are written to `backend/reports/`. Documentation: [docs/EVALUATION.md](docs/EVALUATION.md).

## Tests

```bash
cd backend
python -m pytest tests -q          # 107 backend tests

cd frontend
npm run build && npm run lint
npx playwright test                # E2E
```

## Demo

Demo scenario: [docs/DEMO.md](docs/DEMO.md).

Recommended questions:

- `Which suppliers were most frequently late?`
- `Show monthly revenue by category.`
- `Which SKUs are at risk of stockout in the next 30 days?`
- `Welche Lieferanten waren am häufigsten verspätet?`
- `Which products saw their margin drop last quarter?`

## Explicit limitations

- Users are declared via environment variables (no external SSO/OAuth2 yet).
- Questions supported in French, German and English; the interface remains in French.
- No PDF ingestion or document RAG, no fine-tuning.
- Ollama remains optional and local.
- The database is an industrial demo dataset, not a client database.
- The SQL guardrail is application-level (AST parser via sqlglot, table allowlist, forced LIMIT, single statement, pre-flight EXPLAIN and query timeout) backed by the read-only role — a defense-in-depth layer on top of, not a replacement for, database-level access control.

## History & roadmap

- Project notes (handoff, run, gotchas): [docs/PROJECT_NOTES.md](docs/PROJECT_NOTES.md)
- Version history: [CHANGELOG.md](CHANGELOG.md)
- Detailed roadmap: [docs/ROADMAP.md](docs/ROADMAP.md)
- Original requirements document: [Cahier de charges.pdf](Cahier%20de%20charges.pdf)
