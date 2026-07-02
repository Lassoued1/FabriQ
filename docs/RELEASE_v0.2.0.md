# FabriQ v0.2.0

Date: 27 June 2026

Statut: release candidate stable du Jalon 5 - V2 locale.

## Resume

FabriQ v0.2.0 consolide le MVP en ajoutant une intelligence locale optionnelle, sans abandonner les garanties de securite:

```text
Question metier -> routage hybride -> SQL template -> validation -> execution read-only -> reponse + UI transparente
```

Le LLM local via Ollama ne genere jamais de SQL. Il sert uniquement de routeur d'intention lorsque le routeur deterministe ne reconnait pas assez clairement la question.

## Inclus

- Backend FastAPI version `0.2.0`.
- Frontend React/Vite version `0.2.0`.
- Routeur hybride:
  - deterministe par mots-cles en priorite;
  - Ollama optionnel uniquement en fallback;
  - clarification guidee si aucune intention autorisee n'est fiable.
- SQL toujours genere par templates controles.
- Garde-fou SQL read-only conserve.
- PostgreSQL Docker avec role applicatif `fabriq_readonly`.
- Trace d'orchestration exposee dans chaque reponse.
- Pipeline visible dans l'UI.
- Options de clarification cliquables.
- Catalogue semantique enrichi:
  - 10 intentions;
  - descriptions metier;
  - synonymes;
  - 9 tables;
  - colonnes documentees.
- Endpoint `GET /api/catalog`.
- Catalogue visible dans l'UI avec onglets `Intentions` et `Tables`.
- Ping Ollama non bloquant dans `GET /api/health`.
- Statuts LLM visibles dans l'UI: `LLM ready`, `LLM off`, `Model missing`, `LLM unreachable`.
- Suite d'evaluation paraphrases avec 10 reformulations.

## Validation

Dernier etat verifie pour la release candidate:

| Controle | Resultat |
| --- | --- |
| Backend tests | `14 tests OK` |
| Evaluation golden SQLite | `10/10` |
| Evaluation paraphrases SQLite | `10/10` |
| Frontend build | `npm run build` OK, avec avertissement de taille de bundle Vite |
| Frontend lint | `npm run lint` OK |
| API catalog | `10` intentions, `9` tables |
| Health Ollama local | `ready`, modele disponible |

Validation PostgreSQL:

- validation PostgreSQL + Ollama deja reussie le 26 June 2026: golden `10/10`, role `fabriq_readonly` read-only OK;
- revalidation du 27 June 2026 bloquee dans ce shell: `docker` introuvable dans le PATH et port `127.0.0.1:5432` ferme.

Avant tag final, relancer PostgreSQL Docker puis executer les deux suites `--database=env`.

## Commandes de verification

```bash
docker compose up -d postgres
docker compose ps postgres
```

```bash
cd backend
$env:FABRIQ_DATABASE_URL="postgresql://fabriq_readonly:fabriq_readonly@127.0.0.1:5432/fabriq"
python -m unittest discover -s tests
python scripts/evaluate.py --database=env
python scripts/evaluate.py --database=env --suite=paraphrases
```

```bash
cd frontend
npm run build
npm run lint
```

## Smoke test local

Backend:

```bash
cd backend
$env:FABRIQ_DATABASE_URL="postgresql://fabriq_readonly:fabriq_readonly@127.0.0.1:5432/fabriq"
$env:FABRIQ_LLM_PROVIDER="ollama"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd frontend
$env:VITE_API_URL="http://127.0.0.1:8000"
npm run dev
```

Points a verifier:

- `GET /api/health` retourne `version=0.2.0`.
- `GET /api/catalog` retourne 10 intentions et 9 tables.
- L'UI affiche le catalogue.
- Une question connue retourne tableau, graphique, SQL et pipeline.
- Une question ambigue retourne des options de clarification.

## Limites connues

- Pas d'authentification.
- Pas de multi-tenant.
- Pas d'ingestion documentaire.
- Pas de RAG.
- Pas de fine-tuning.
- Ollama reste optionnel et local.
- Pas encore d'orchestration LangGraph complete.
- La base reste une base industrielle de demonstration.
- Les graphiques restent choisis par template d'intention.

## Tag Git

Ce dossier n'est pas detecte comme depot Git dans l'environnement actuel. Des qu'un depot existe:

```bash
git add .
git commit -m "Release FabriQ v0.2.0"
git tag v0.2.0
```

## Prochaine version

`v0.3.0` peut cibler:

- orchestration LangGraph formelle;
- authentification;
- multi-tenant;
- insights planifies et alertes;
- packaging de demo;
- selection de graphiques plus avancee.
