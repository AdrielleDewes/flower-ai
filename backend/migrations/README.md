Alembic uses the application's `DATABASE_URL` and `Base.metadata`. Importing
`app.models` registers the tables for autogenerate.

The first revision, `a17d0c1b6e90`, is a baseline for the PostgreSQL database
that already contains the FlowerAI schema. Its upgrade and downgrade contain
no DDL, so it does not create, drop, or modify application tables.

When the existing schema has been checked against this baseline, record it
from `backend/` with:

```bash
alembic stamp a17d0c1b6e90
```

Stamping only records the revision in `alembic_version`. It must not be used
to initialize an empty database. The next revision, `801ced7ebaab`, updates
the three bouquet composition foreign keys to `ON DELETE CASCADE`. Review its
DDL before applying it to an existing database.
