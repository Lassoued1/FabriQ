# FabriQ Backend

API FastAPI de FabriQ v0.13.0 (voir [../CHANGELOG.md](../CHANGELOG.md)).

La version exposee par FastAPI (`/api/health`) est `0.13.0`.

## Lancement

```bash
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

Avec PostgreSQL Docker:

```bash
docker compose up -d postgres
$env:FABRIQ_DATABASE_URL="postgresql://fabriq_readonly:fabriq_readonly@127.0.0.1:5432/fabriq"
python -m uvicorn app.main:app --reload --port 8000
```

## Endpoints

- Sante: `GET /api/health`, `GET /metrics`
- Auth: `POST /api/auth/login`, `POST /api/auth/refresh`, `GET /api/auth/me`
- Analyse: `POST /api/ask`
- Catalogue: `GET /api/catalog`, `GET /api/examples`
- Audit: `GET /api/audit/recent`, `GET /api/audit/export`, `GET /api/audit/export.xlsx`
- Alertes: `GET/POST /api/alerts`, `DELETE /api/alerts/{id}`, `GET /api/alerts/events`, `GET /api/alerts/events/export`
- Webhooks: `GET /api/webhooks/event-types`, `GET/POST /api/webhooks`, `DELETE /api/webhooks/{id}`, `POST /api/webhooks/{id}/test`, `GET /api/webhooks/{id}/deliveries`
- Admin: `GET /api/admin/users`, `POST /api/admin/users/{email}/disable`, `POST /api/admin/users/{email}/enable`

Toutes les routes metier (hors `/api/health` et `/api/auth/login`) requierent un JWT Bearer et sont filtrees par `tenant_id`.

Documentation interactive: `http://localhost:8000/docs`.

Payload `/api/ask`:

```json
{
  "question": "Quels fournisseurs ont ete le plus souvent en retard ?"
}
```

## Note technique

Le backend demarre avec SQLite en memoire si `FABRIQ_DATABASE_URL` est absent. Si cette variable pointe vers PostgreSQL, les requetes utilisent le dialecte PostgreSQL et l'utilisateur read-only cree par Docker.

Questions supportees en francais, allemand et anglais. Le garde-fou SQL valide chaque requete via un parseur AST (sqlglot) avant execution.

## LLM local optionnel

Ollama peut etre utilise comme routeur d'intention lorsque le routeur deterministe ne reconnait pas la question.

```bash
$env:FABRIQ_LLM_PROVIDER="ollama"
$env:FABRIQ_OLLAMA_URL="http://127.0.0.1:11434"
$env:FABRIQ_OLLAMA_MODEL="llama3.1"
```

Le LLM ne genere pas de SQL. Il ne peut proposer qu'une intention autorisee, puis les templates et le garde-fou SQL existants continuent de s'appliquer.

`GET /api/health` expose aussi un ping Ollama non bloquant:

- `llm_status`;
- `llm_reachable`;
- `llm_model_available`;
- `llm_latency_ms`;
- `llm_error`.

## Evaluation

Tests unitaires:

```bash
python -m unittest discover -s tests
```

Evaluation golden:

```bash
python scripts/evaluate.py
```

Evaluation paraphrases:

```bash
python scripts/evaluate.py --suite=paraphrases
```

Les rapports detailles sont ecrits dans `reports/evaluation-latest.json` et `reports/evaluation-paraphrases-latest.json`. Les appels API sont journalises dans `logs/analysis.jsonl`.

Pour evaluer la base PostgreSQL:

```bash
python scripts/evaluate.py --database=env
python scripts/evaluate.py --database=env --suite=paraphrases
```
