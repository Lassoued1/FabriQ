# Changelog

Historique des versions de FabriQ. Le detail complet de chaque jalon est dans [docs/ROADMAP.md](docs/ROADMAP.md).

## v0.14.0 — en cours (non taguee)

- **SSO OIDC optionnel (Keycloak ou tout fournisseur OpenID Connect)** : flux
  authorization code + PKCE pilote par le backend (`app/oidc.py`). Le backend
  redirige vers le fournisseur, valide l'id_token (signature RS256 via JWKS,
  issuer, audience, expiration), mappe les claims `fabriq_tenant`/`fabriq_role`
  puis emet le JWT FabriQ habituel (`auth=oidc`) — refresh, multi-tenant, audit
  et desactivation de compte reutilises tels quels. Desactive par defaut :
  s'active par `FABRIQ_OIDC_ISSUER` + `FABRIQ_OIDC_CLIENT_ID`; le login local
  `FABRIQ_USERS` reste toujours disponible.
- **Endpoints** : `GET /api/auth/oidc/login` (302 vers le fournisseur, state
  anti-CSRF + PKCE S256) et `GET /api/auth/oidc/callback` (echange du code,
  emission du JWT, retour au frontend via fragment `#sso_token=`). Flag
  `oidc_enabled` dans `/api/health`.
- **Keycloak pret a l'emploi** : service docker-compose derriere le profil
  `sso` (`docker-compose --profile sso up`), realm `fabriq` importe
  automatiquement (`keycloak/fabriq-realm.json`) avec client confidentiel,
  mappers de claims et utilisateur de demo `sso.demo` / `fabriq2024`.
- **Frontend** : bouton « Se connecter avec SSO » affiche uniquement quand le
  backend expose `oidc_enabled=true`; recuperation du token dans le fragment
  d'URL (jamais dans les logs serveur) puis nettoyage de l'URL.
- 125 tests backend (+18 pour l'OIDC : PKCE, anti-rejeu du state, issuer/
  audience/expiration invalides, mapping des claims, pipeline JWT SSO).
- **UI en allemand** : troisieme langue du selecteur d'interface (FR/EN/DE).
  Dictionnaire `de` complet dans `i18n.tsx` (meme forme que `fr`/`en`, verrouille
  par test), 10 exemples de questions allemandes issus de la suite d'evaluation
  `german.json` (un par intention, garantis de router). Correction au passage :
  les exemples affiches suivent desormais la langue via `examplesByLang[lang]`
  (avant, seul l'anglais etait gere). 15 tests unitaires frontend.

## v0.13.0 — 18 juillet 2026

- **Webhooks sortants generiques** : systeme d'evenements decouple des alertes.
  Souscriptions par tenant (`app/webhooks.py`) enregistrant une URL, une liste
  de types d'evenements et un secret HMAC ; persistance JSON.
- **Types d'evenements** : `question.answered`, `question.blocked`, `alert.fired`,
  `auth.login_failed`, emis depuis `/api/ask`, le login et `alerts._fire_rule`.
- **Livraison robuste** : signature HMAC-SHA256 (`X-FabriQ-Signature`), reessais
  a backoff (0/5/30 s), journal de livraison (JSONL) par tentative, emission
  non bloquante (threads daemon).
- **Garde anti-SSRF** : les URLs vers loopback / reseaux prives / link-local /
  reserve, et les schemas non HTTP(S), sont refuses a la creation.
- **API** : 6 endpoints `/api/webhooks*` (CRUD, `event-types`, `test`,
  `deliveries`), tous scopes par tenant.
- **Frontend** : `WebhooksPanel` (creation avec cases d'evenements, liste, bouton
  Tester, journal de livraison repliable), monte dans la sidebar.
- **i18n frontend** : selecteur de langue FR/EN dans l'en-tete, contexte
  `i18n.tsx` couvrant les 13 composants (libelles, exemples de questions,
  panneaux). La reponse suit la langue de la question posee.
- **Correctif E2E** : `WebhooksPanel` reutilisait la classe CSS `alerts-panel`,
  ce qui cassait le selecteur strict Playwright du panneau alertes ; il a
  desormais sa propre classe `webhooks-panel`.
- 107 tests backend + 166 sous-tests (+22 pour les webhooks), 13 tests unitaires
  frontend (Vitest), E2E 10/10.

Note : v0.12.0 et v0.13.0 ont ete developpees en parallele sur `main` (les deux
perimetres ont atterri dans le meme commit) ; les deux tags pointent sur le meme
etat du depot.

## v0.12.0 — 18 juillet 2026

- **Questions en anglais** : mots-cles EN sur les 10 intentions, verbes d'ecriture
  refuses (remove, update, delete, add...), parametres extraits (next N days,
  last N months, quarter, semester, N largest). Suite d'evaluation
  `--suite=english` 15/15.
- **Detection d'ecriture affinee** : "drop" retire de la detection en langage
  naturel ("margin drop", "sales drop" sont des tournures de lecture) ; un vrai
  `DROP TABLE` reste bloque par le garde-fou SQL (parseur AST).
- **CI elargie** : le job backend execute desormais toute la suite `tests`
  (auparavant seul `test_agent.py`), ce qui couvre en CI les tests allemand,
  anglais et parametres. 85 tests backend + 159 sous-tests.

## v0.11.0 — 6 juillet 2026

- **Garde-fou SQL v2** : validation par parseur AST (sqlglot) — instruction unique,
  SELECT pur (UNION/CTE/verrous bloques), allowlist appliquee aux sous-requetes,
  LIMIT litteral borne. EXPLAIN prealable et timeout de requete
  (`FABRIQ_QUERY_TIMEOUT_SECONDS`) sur PostgreSQL et SQLite.
- **Suite adversariale** : 24 tentatives d'injection bloquees 24/24.
- **Extraction de parametres** : top N, horizon en jours et fenetre en mois extraits
  de la question et bindes dans les templates ("rupture dans les 7 prochains jours"
  vs "30 jours" produisent des requetes differentes). Parametres visibles dans la
  trace d'orchestration.
- **Questions en allemand** : ~100 mots-cles DE sur les 10 intentions, verbes
  d'ecriture refuses, parametres extraits (Tagen, Monaten, Quartal, Halbjahr),
  suite d'evaluation `--suite=german` 15/15.
- **Routeur durci** : deduplication des mots-cles singulier/pluriel, refus des
  demandes d'ecriture (FR et DE) sans jamais consulter le routeur LLM.
- **Frontend refactore** : App.tsx 1567 -> 667 lignes, 13 modules extraits,
  9 tests unitaires Vitest, etape "Unit tests" en CI.
- **Evaluation** : golden 43 cas (negatifs et pieges inclus), checks `max_rows` et
  `expected_sql_contains`. 78 tests backend + 135 sous-tests.

## v0.10.0 — 2 juillet 2026

- Export Excel (xlsx) du journal d'audit: `GET /api/audit/export.xlsx` + bouton frontend.
- Remise a niveau portfolio: depot Git initialise, README et architecture actualises, changelog consolide.
- 60 tests backend.

## v0.9.0 — Qualite et experience

- Tests E2E Playwright: 3 suites (auth, ask, observability), job CI dedie avec artefacts en cas d'echec.
- Export PDF du panneau de resultats (CSS `@media print`).
- Toast notifications (success/error/info) sur les actions utilisateur.

## v0.8.0 — DevOps et observabilite

- CI GitHub Actions: backend (pytest + ruff), frontend (tsc + build), smoke test Docker.
- Prometheus + Grafana provisionnes dans docker-compose.
- Notifications Slack sur les alertes (webhook global ou par regle).
- JWT refresh: `POST /api/auth/refresh` + auto-refresh frontend.
- OpenAPI enrichie (tags, resumes, descriptions).

## v0.7.0 — Performance et controle

- Cache TTL 5 min sur l'execution SQL (cle: sql + tenant).
- Filtres du journal d'audit (intention, statut de validation).
- Pagination des evenements d'alerte.
- Desactivation/reactivation d'utilisateurs par l'admin.
- Tests de charge Locust.

## v0.6.0 — Observabilite et administration

- Healthcheck DB (`db_ok`, `db_latency_ms`) dans `/api/health`.
- Journal d'audit pagine, export CSV des evenements d'alerte.
- Panneau admin frontend (role admin requis).
- Endpoint Prometheus `/metrics`.

## v0.5.0 — Robustesse et UX

- Selection de graphique dynamique selon la forme des donnees.
- Endpoint admin users avec controle de role (403 sinon).
- Notifications e-mail SMTP optionnelles sur les alertes.
- Rate limiting: login 10/min, analyse 30/min.

## v0.4.0 — Qualite et isolation

- Filtrage SQL par tenant injecte a l'execution (PostgreSQL + JWT).
- Colonne `tenant_id` sur `orders` et `customers`, seed 2 tenants.
- Webhook optionnel par regle d'alerte.
- Export CSV du journal d'audit filtre par tenant.
- Docker: nginx non-root, `.dockerignore`.

## v0.3.0 — Multi-utilisateurs

- Orchestration LangGraph (`StateGraph`, reducers, edges conditionnels) remplace le pipeline lineaire.
- Authentification JWT: login, protection des routes, page de connexion.
- Multi-tenant: `tenant_id` propage JWT -> etat LangGraph -> audit.
- Alertes planifiees APScheduler avec regles CRUD et panneau UI.
- Docker Compose complet (postgres, backend, frontend).

## v0.2.0 — V2 locale

- Routeur d'intention hybride: deterministe d'abord, Ollama optionnel en repli.
- Le LLM ne genere jamais de SQL et ne propose qu'une intention du catalogue.
- Clarifications guidees avec options cliquables.
- Catalogue semantique expose (`GET /api/catalog`) et visible dans l'UI.
- Trace d'orchestration dans chaque reponse.
- Suite d'evaluation paraphrases: 10/10.
- Health-check Ollama non bloquant.

## v0.1.0 — MVP

- Boucle NL -> SQL -> validation -> execution -> reponse, sans LLM obligatoire.
- 10 familles de questions industrielles par templates SQL deterministes.
- Garde-fou SQL: SELECT seul, allowlist de tables, mots-cles bloques, LIMIT force.
- Execution en lecture seule (SQLite local ou PostgreSQL Docker, role `fabriq_readonly`).
- UI React: question, reponse metier, tableau, graphique, SQL visible.
- Audit JSONL avec trace id, harnais d'evaluation golden 10/10.
