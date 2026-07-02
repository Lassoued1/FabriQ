# FabriQ MVP v0.1.0

Date: 25 June 2026

Statut: release portfolio prete a taguer pour le Jalon 4.

## Resume

FabriQ v0.1.0 livre une boucle complete de demonstration:

```text
Question metier -> intention -> SQL controle -> validation -> execution read-only -> reponse + tableau + graphique + audit
```

La version cible une demonstration fiable, explicable et defendable, sans dependance obligatoire a un LLM.

## Inclus

- Frontend React/Vite avec interface applicative directe.
- Backend FastAPI version `0.1.0`.
- PostgreSQL Docker avec schema, seed et role `fabriq_readonly`.
- Fallback SQLite local si `FABRIQ_DATABASE_URL` est absent.
- Couche semantique deterministe couvrant 10 familles metier.
- Templates SQL SQLite et PostgreSQL.
- SQL guard avec contraintes read-only.
- Graphiques `bar` et `line` via Recharts.
- Audit JSONL et endpoint `/api/audit/recent`.
- Evaluation golden locale.
- Documentation portfolio: README, architecture, evaluation, demo, roadmap.
- Presentation Word trilingue dans `output/documents/`.

## Validation

Dernier etat verifie pour la release:

| Controle | Resultat attendu |
| --- | --- |
| Docker PostgreSQL | `healthy` |
| API health | `{"status":"ok","service":"fabriq-api","database":"postgres"}` |
| Backend tests | `5 tests OK` |
| Evaluation golden | `10/10` |
| Frontend build | `npm run build` OK, avec avertissement de taille de bundle Vite |
| Frontend lint | `npm run lint` sans erreur bloquante |

## Limites connues

- Pas d'authentification.
- Pas de multi-tenant.
- Pas d'ingestion documentaire.
- Pas de RAG.
- Pas de fine-tuning.
- Pas encore d'orchestration LangGraph.
- LLM/Ollama prevu mais pas branche en production.
- La base est une base demo, pas une integration client.
- Les intentions hors catalogue peuvent demander une clarification ou rester non supportees.

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
```

```bash
cd frontend
npm run build
npm run lint
```

## Tag Git

Ce dossier n'est pas encore initialise en depot Git. Des qu'un depot existe:

```bash
git add .
git commit -m "Release FabriQ MVP v0.1.0"
git tag v0.1.0
```

## Prochaine version

`v0.2.0` doit ouvrir la V2:

- LLM local via Ollama;
- orchestration LangGraph;
- clarification plus riche;
- couche semantique enrichie;
- meilleur choix de graphique;
- schema d'architecture final exportable;
- eventuel packaging de demo.
