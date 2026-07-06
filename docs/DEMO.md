# FabriQ - Scenario de demonstration v0.1.0

Ce scenario permet de montrer FabriQ sans preparation lourde.

## Prerequis

- Docker Desktop lance.
- PostgreSQL FabriQ en etat `healthy`.
- Backend FastAPI disponible sur `http://127.0.0.1:8000`.
- Frontend disponible sur `http://127.0.0.1:5173`.

## Demarrage

```bash
docker compose up -d postgres
```

```bash
cd backend
$env:FABRIQ_DATABASE_URL="postgresql://fabriq_readonly:fabriq_readonly@127.0.0.1:5432/fabriq"
python -m uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend
npm run dev
```

## Script de demo court

1. Ouvrir `http://127.0.0.1:5173`.
2. Montrer le bandeau: API ok, base `postgres`, read-only, `v0.1.0`.
3. Cliquer sur l'exemple `Quels fournisseurs ont ete le plus souvent en retard ?`.
4. Montrer la reponse metier, le graphique et le tableau.
5. Ouvrir visuellement le panneau SQL et expliquer que le SQL est transparent.
6. Montrer les checks de validation SQL.
7. Montrer le panneau Observabilite: derniere trace et historique recent.
8. Lancer une deuxieme question: `Montre le chiffre d'affaires mensuel par categorie.`
9. Montrer le changement automatique de graphique en courbe.
10. Conclure avec l'evaluation golden `10/10`.

## Questions recommandees

| Question | Ce que la demo prouve |
| --- | --- |
| `Quels fournisseurs ont ete le plus souvent en retard ?` | Analyse fournisseur, graphique barre, audit. |
| `Montre le chiffre d'affaires mensuel par categorie.` | Serie temporelle, graphique ligne. |
| `Quels SKU risquent une rupture dans les 30 prochains jours ?` | Stock, priorisation risque, parametre extrait de la question. |
| `Welche Lieferanten waren am häufigsten verspätet?` | Meme analyse en allemand, routage bilingue. |
| `Quels produits ont vu leur marge baisser le trimestre dernier ?` | Marge, periode, SQL agrégé. |
| `Quels clients concentrent le plus de chiffre d'affaires ?` | Concentration client et classement. |

## Verification avant demo

```bash
docker compose ps postgres
```

```bash
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

```bash
cd backend
python scripts/evaluate.py --database=env
```

Resultat attendu:

```text
10/10 passed
database: postgres
```

## Assets

Les captures de demo sont placees dans `docs/assets/` lorsqu'elles sont generees localement:

- `docs/assets/fabriq-v0.1.0-demo.png`
- `docs/assets/fabriq-v0.1.0-demo.gif`

Si ces fichiers ne sont pas presents, relancer la capture apres avoir demarre l'API et le frontend.
