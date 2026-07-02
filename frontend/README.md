# FabriQ Frontend

Interface React + Vite du MVP FabriQ v0.2.0-dev.0.

## Role

Le frontend expose l'experience principale:

- saisie d'une question metier en langage naturel;
- exemples de questions industrielles;
- reponse operationnelle;
- graphique Recharts;
- tableau de resultats;
- SQL transparent;
- statut de validation;
- panneau d'observabilite avec sante API, base active et traces recentes.
- statut LLM et strategie de routage de l'analyse.

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

## Notes v0.2.0-dev.0

- L'interface est orientee demonstration portfolio.
- Les graphiques couvrent les formats `bar` et `line`.
- L'historique affiche les traces recentes exposees par l'API.
- La barre de statut affiche le mode LLM retourne par l'API.
- La ligne de metriques affiche la strategie de routage (`deterministic_keywords` ou `ollama_intent_router`).
- L'authentification, le multi-tenant et les alertes planifiees sont hors scope MVP.
