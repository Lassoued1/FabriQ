# FabriQ Frontend

Interface React + Vite de FabriQ v0.13.0 (voir [../CHANGELOG.md](../CHANGELOG.md)).

## Role

Le frontend expose l'experience principale:

- page de connexion et authentification JWT (refresh automatique);
- saisie d'une question metier en langage naturel (francais, allemand, anglais);
- exemples de questions industrielles;
- reponse operationnelle;
- graphique Recharts;
- tableau de resultats;
- SQL transparent;
- statut de validation;
- panneau d'observabilite avec sante API, base active et traces recentes;
- statut LLM et strategie de routage de l'analyse;
- panneau admin (liste, activation/desactivation des comptes);
- panneau alertes planifiees (regles CRUD, evenements, export CSV);
- panneau webhooks (creation, test, journal de livraison);
- export PDF du rapport d'analyse, export CSV/xlsx du journal d'audit.

## Lancement

```bash
cd frontend
npm install
npm run dev
```

L'application est disponible sur `http://localhost:5173`.

## Configuration

Par defaut, l'interface appelle `http://localhost:8000`.

Pour pointer vers une autre API:

```bash
$env:VITE_API_URL="http://127.0.0.1:8000"
npm run dev
```

## Verification

```bash
npm run build
npm run lint
```

## Notes

- L'interface est orientee demonstration portfolio.
- Les graphiques s'adaptent automatiquement a la forme des donnees (bar/line/area).
- L'historique affiche les traces recentes exposees par l'API.
- La barre de statut affiche le mode LLM retourne par l'API.
- La ligne de metriques affiche la strategie de routage (`deterministic_keywords` ou `ollama_intent_router`).
- L'authentification JWT, le multi-tenant et les alertes planifiees sont geres cote frontend depuis la v0.3.0.
