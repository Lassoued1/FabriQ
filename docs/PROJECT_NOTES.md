# FabriQ — Notes de projet

Document de reprise (handoff). Résume l'état courant, comment lancer, et les pièges connus. Pour l'historique détaillé voir [CHANGELOG.md](../CHANGELOG.md) et [ROADMAP.md](ROADMAP.md).

## État courant

- **Version** : v0.13.0 taguée/publiée le 18 juillet 2026 (v0.12.0 taguée le même jour, sur le même état du dépôt : les deux périmètres ont atterri dans le même commit) — dépôt public https://github.com/Lassoued1/FabriQ
- **CI** : GitHub Actions verte (backend, frontend, E2E Playwright, Docker). Le job backend exécute toute la suite `tests`. La CI a été rouge du 15 au 18 juillet : `WebhooksPanel` réutilisait la classe CSS `alerts-panel`, ce qui faisait échouer le sélecteur strict Playwright (voir piège 9).
- **Tests** : 107 backend (pytest) + 166 sous-tests, 13 unitaires frontend (Vitest), 10 E2E (Playwright), 4 suites d'évaluation (golden 43, paraphrases 10, allemand 15, anglais 15).

## Stack

| Couche | Techno |
| --- | --- |
| Backend | Python — FastAPI + orchestration LangGraph |
| Frontend | React 19 + Vite + TypeScript |
| Base de données | PostgreSQL (Docker, rôle read-only) ; SQLite en fallback dev/tests |
| LLM | Ollama local, optionnel (routage d'intention uniquement, jamais de SQL) |
| Observabilité | Prometheus + Grafana |
| Langues des questions | Français, allemand et anglais |

Pas d'OCR, pas de RAG, pas de fine-tuning (hors périmètre assumé).

## Lancer le projet

### Docker (stack complet : 5 services)

```bash
cp .env.example .env          # ou : python scripts/init_env.py (interactif)
docker-compose up -d --build
```

Accès : frontend http://localhost:80 · API http://localhost:8000 · Prometheus http://localhost:9090 · Grafana http://localhost:3000

**Utilisateur de démo** : `admin@fabriq.io` / `fabriq2024` (tenant_demo, rôle admin). Les comptes sont définis par `FABRIQ_USERS` dans `.env` ; aucun n'est codé en dur.

### Local (dev)

```bash
# Backend
cd backend && python -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# Frontend
cd frontend && npm install && npm run dev
```

## Tests

```bash
cd backend && python -m pytest tests -q
cd backend && python scripts/evaluate.py            # golden
cd backend && python scripts/evaluate.py --suite=paraphrases
cd backend && python scripts/evaluate.py --suite=german
cd backend && python scripts/evaluate.py --suite=english
cd frontend && npm test                             # Vitest
cd frontend && npx playwright test                  # E2E
```

## Pièges connus (importants)

1. **Hash bcrypt dans `.env` + docker-compose standalone** : le binaire autonome `docker-compose` (v5.x) interprète les `$` du `.env` comme des variables → il corrompt le hash bcrypt (`$2b$12$…` → `$2b$12.…`) et casse le login. Solution : doubler les `$` en `$$` dans la ligne `FABRIQ_USERS` du `.env`. Non nécessaire avec le plugin `docker compose` v2.
2. **502 après recréation du backend** : si on recrée le conteneur backend seul (`--force-recreate backend`), il change d'IP interne et nginx garde l'ancienne en cache → 502 sur `/api/`. Solution : `docker-compose restart frontend` ensuite (ou `docker-compose up -d` global).
3. **Lock npm / Windows** : les dépendances `@emnapi` (binding wasm de rolldown) disparaissent du `package-lock.json` à certaines installs → `npm ci` échoue en CI. Elles sont épinglées en devDependencies ; en cas de récidive : supprimer `node_modules` + `package-lock.json`, `npm install`, puis valider par un vrai `npm ci`.
4. **Mots-clés allemands** : dans `semantic_layer.py`, les mots-clés sont stockés SANS umlauts (la normalisation replie ä/ö/ü et ß→ss) ; les questions de test, elles, s'écrivent AVEC umlauts. La translittération ae/oe/ue ne matche pas.
5. **Port 5432** : partagé avec le projet WerkPilotVLBG (`D:\Reactprojects\WerkPilotVLBG-agent-kit`). Un seul stack peut le tenir à la fois.
6. **"drop" ≠ écriture** : le mot anglais "drop" ("margin drop", "sales drop") est une tournure de LECTURE, pas une demande d'écriture. Il est volontairement absent de `_WRITE_REQUEST_PATTERN` ; un vrai `DROP TABLE` est bloqué par le garde-fou SQL (parseur AST dans `sql_guard.py`), pas par la détection en langage naturel. Ne pas le rajouter au pattern NL sous peine de refuser les questions de marge en anglais.
7. **Webhooks — garde SSRF** : `webhooks.is_safe_webhook_url` refuse loopback / réseaux privés / link-local / réservé et les schémas non HTTP(S). Vérifiée à la création (400). Elle fait une résolution DNS (`getaddrinfo`) : les tests l'exercent avec des IP littérales pour rester hors-ligne. En démo locale, un webhook vers `localhost`/`127.0.0.1` est donc **refusé par conception** (utiliser une IP publique ou un tunnel).
8. **Webhooks — données runtime** : `backend/webhooks/subscriptions.json` contient les secrets HMAC → dossier gitignoré (`backend/webhooks/`), jamais commité. Le journal de livraison est sous `backend/logs/` (déjà gitignoré).
9. **Classes CSS et sélecteurs E2E** : les specs Playwright ciblent des classes de panneau (`.alerts-panel`, `.observability-panel`…) en mode strict. Réutiliser la classe d'un panneau existant pour un nouveau panneau casse les E2E (vécu avec `WebhooksPanel` qui portait `alerts-panel` → CI rouge 3 jours). Donner à chaque panneau sa propre classe et mutualiser le style via un sélecteur groupé dans App.css.

## Prochaines pistes (au-delà)

- **Fait (v0.12.0)** : questions en anglais — mots-clés, verbes d'écriture, paramètres, suite `evaluation/english.json` 15/15.
- **Fait (v0.13.0)** : webhooks sortants génériques — émetteur d'événements, signature HMAC, reessais, garde SSRF, panneau UI — et sélecteur de langue FR/EN (i18n.tsx). Voir [ROADMAP.md](ROADMAP.md) jalon 16.
- Authentification OAuth2 / SSO (Keycloak ou Auth0) en remplacement des utilisateurs env.
- Démo en ligne.
