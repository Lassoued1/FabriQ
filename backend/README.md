# FabriQ Backend

API FastAPI de FabriQ v0.2.0.

La version exposee par FastAPI est `0.2.0`.

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

- `GET /api/health`
- `GET /api/examples`
- `GET /api/catalog`
- `POST /api/ask`
- `GET /api/audit/recent`

Payload:

```json
{
  "question": "Quels fournisseurs ont ete le plus souvent en retard ?"
}
```

## Note technique

Le MVP demarre avec SQLite en memoire si `FABRIQ_DATABASE_URL` est absent. Si cette variable pointe vers PostgreSQL, les requetes utilisent le dialecte PostgreSQL et l'utilisateur read-only cree par Docker.

## LLM local optionnel

La V2 peut utiliser Ollama comme routeur d'intention lorsque le routeur deterministe ne reconnait pas la question.

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
