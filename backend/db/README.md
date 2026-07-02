# FabriQ PostgreSQL

Les scripts dans `init/` sont montes dans `/docker-entrypoint-initdb.d`.

- `01_schema.sql` cree le schema industriel.
- `02_seed.sql` charge des donnees de demonstration et cree le role `fabriq_readonly`.

Si le volume Docker existe deja, les scripts d'initialisation PostgreSQL ne sont pas rejoues. Pour repartir proprement:

```bash
docker compose down -v
docker compose up -d postgres
```
