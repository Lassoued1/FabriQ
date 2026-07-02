# Evaluation FabriQ

Le MVP est evalue par execution, pas par similarite de texte SQL.

## Etat v0.1.0

Dernier rapport release attendu:

- base: PostgreSQL;
- total: 10 cas;
- reussis: 10 cas;
- precision: 100%;
- rapport: `backend/reports/evaluation-latest.json`.

## Etat v0.2.0

Derniere validation locale:

- suite golden: 10 cas, 10 reussis, rapport `backend/reports/evaluation-latest.json`;
- suite paraphrases: 10 cas, 10 reussis, rapport `backend/reports/evaluation-paraphrases-latest.json`;
- couverture: les 10 familles metier restent executees par templates SQL controles.

Note du 27 June 2026:

- validation SQLite: OK;
- ping Ollama: OK;
- revalidation PostgreSQL locale bloquee car `docker` est introuvable dans le PATH de ce shell et le port `127.0.0.1:5432` est ferme.

## Jeu golden

Le fichier `backend/evaluation/golden.json` couvre les 10 familles du cahier des charges:

- tendance de marge;
- risque de rupture;
- retards fournisseurs;
- efficacite production;
- tendance de chiffre d'affaires;
- vieillissement de stock;
- cout logistique;
- retours;
- concentration clients;
- detection d'anomalie.

Chaque cas verifie:

- l'intention reconnue;
- la validation SQL;
- le nombre minimal de lignes;
- les colonnes attendues;
- le type de graphique attendu.

## Jeu paraphrases

Le fichier `backend/evaluation/paraphrases.json` reprend les memes familles avec des formulations differentes:

- rentabilite au lieu de marge;
- produits qui manquent au lieu de rupture;
- delais de livraison peu fiables au lieu de retards;
- rebuts et ateliers au lieu de defauts et lignes;
- ventes mensuelles par famille au lieu de chiffre d'affaires par categorie.

Ce jeu sert a verifier que l'enrichissement des synonymes ne casse pas le routage d'intention.

## Lancer l'evaluation

```bash
cd backend
python scripts/evaluate.py
```

Le rapport detaille est ecrit dans `backend/reports/evaluation-latest.json`.

Pour executer le jeu de paraphrases:

```bash
cd backend
python scripts/evaluate.py --suite=paraphrases
```

Le rapport detaille est ecrit dans `backend/reports/evaluation-paraphrases-latest.json`.

Pour executer le meme jeu golden contre PostgreSQL:

```bash
$env:FABRIQ_DATABASE_URL="postgresql://fabriq_readonly:fabriq_readonly@127.0.0.1:5432/fabriq"
python scripts/evaluate.py --database=env
```

Pour executer les paraphrases contre PostgreSQL:

```bash
$env:FABRIQ_DATABASE_URL="postgresql://fabriq_readonly:fabriq_readonly@127.0.0.1:5432/fabriq"
python scripts/evaluate.py --database=env --suite=paraphrases
```

## Journalisation

Chaque appel `POST /api/ask` ajoute un evenement JSONL dans `backend/logs/analysis.jsonl` avec:

- trace id;
- horodatage;
- question;
- intention;
- statut de validation;
- nombre de lignes;
- type de graphique;
- raison de blocage si besoin.

Le frontend affiche aussi ces signaux dans son panneau d'observabilite: sante API, base active, derniere trace et dernieres questions traitees.
