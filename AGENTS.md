# FlowerAI — AGENTS.md

## Project Overview

FlowerAI is an AI-powered platform for florists focused on bouquet building and recommendation.

The backend must remain multi-florist and extensible for future AI features such as conversational recommendations, semantic search, catalog enrichment, customer-profile recommendations, and image search.

Current stack:
- Python 3.12
- FastAPI
- Pydantic
- SQLAlchemy
- PostgreSQL
- pytest
- Ruff
- GitHub Actions

Repository structure:

```text
flower-ai/
├── backend/
│   ├── app/
│   │   ├── models/
│   │   ├── routers/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── database.py
│   │   ├── dependencies.py
│   │   └── main.py
│   └── tests/
└── frontend/
```

## Architecture

Follow Clean Architecture principles pragmatically.

```text
HTTP request
    ↓
Router
    ↓
Service / business logic
    ↓
Models / persistence
    ↓
Database
```

Responsibilities:

- `routers/`: HTTP concerns, dependencies, status codes and response models.
- `services/`: business/application logic.
- `schemas/`: Pydantic request and response contracts.
- `models/`: SQLAlchemy persistence models.
- `dependencies.py`: reusable FastAPI dependencies.
- `database.py`: database configuration and session management.

Keep business logic and large SQL queries out of routers.

Do not add abstractions unless they solve a concrete problem.

## Code Quality

Follow Clean Code and Python best practices.

- Keep functions focused and reasonably small.
- Use descriptive domain-specific names.
- Add type hints to service/public functions.
- Add concise module, class and function docstrings.
- Prefer explicit, readable code over clever code.
- Use early returns when they simplify control flow.
- Avoid duplicated business rules.
- Comments should explain **why**, not restate the code.
- Preserve existing conventions unless there is a concrete reason to change them.
- Do not rewrite working code only for stylistic preference.

Ruff is the source of truth for linting and import organization.

Before considering backend work complete, run from `backend/`:

```bash
ruff check .
pytest
```

Inspect automatic fixes before committing them.

## Testing

Tests are part of the implementation.

Every behavior change should add or update tests when appropriate.

### Unit tests

Use unit tests for isolated business rules such as:
- recommendation logic;
- pricing;
- stock calculations;
- candidate selection;
- preferences and exclusions;
- validation;
- fallback behavior;
- boundary and edge cases.

### Integration tests

Use integration tests for boundaries such as:
- API → dependency → service;
- service → database;
- multi-table persistence;
- HTTP status codes and response schemas.

Tests must:
- be deterministic;
- be independent of execution order;
- never use the application/production database accidentally.

Preserve the existing test-database safety checks.

Do not weaken tests merely to make them pass.

## API and Error Handling

Use resource-oriented endpoints and explicit response schemas where practical.

Florist-scoped endpoints must validate the florist through the shared dependency.

Expected failures should return meaningful HTTP responses. Do not intentionally expose raw Python exceptions as `500` errors.

Examples:
- nonexistent florist → `404`;
- invalid request payload → `422`;
- invalid business operation → appropriate `4xx`.

Do not expose stack traces, SQL details, credentials, or internal infrastructure information.

## Database and Transactions

Keep transaction boundaries explicit.

For multi-table writes:
1. validate first when practical;
2. create the parent;
3. `flush()` when its generated ID is required;
4. create dependent records;
5. commit once.

Avoid multiple commits inside one logical operation.

Rollback appropriately when transactional operations fail.

Use database constraints as a second line of defense in addition to application validation.

Be aware of N+1 queries. Do not optimize prematurely, but fix them when they affect meaningful request paths.

## Logging and Observability

Use Python `logging`, not `print()`, for application diagnostics.

Logs should capture useful operational context such as:
- operation;
- success/failure;
- relevant resource IDs (`florist_id`, `bouquet_id`);
- errors;
- important latency when useful.

Use appropriate levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`.

Never log passwords, API keys, access tokens, secrets, or unnecessary personal/sensitive data.

Prefer structured logging and request correlation as the system grows.

## Security and Validation

Never trust client-provided IDs, quantities, prices, or ownership relationships.

The backend must validate relevant:
- resource existence;
- florist association;
- active status;
- quantity;
- stock;
- business constraints.

Prices are server-authoritative.

Keep secrets and credentials in environment variables and out of source control.

When authentication is introduced, authorization must be enforced server-side for florist-scoped operations.

## Recommendation Engine

The recommendation engine contains deterministic business logic.

Current high-level flow:

```text
BouquetRequest
      ↓
candidate selection
      ↓
preference prioritization
      ↓
composition building
      ↓
foliage + wrapping
      ↓
stock + budget validation
      ↓
cheapest valid fallback when necessary
      ↓
Recommendation
```

Important rules:
- preferences must never override stock or budget constraints;
- recommendations must use the florist's active catalog and inventory;
- preserve deterministic fallback behavior;
- do not return a fake successful recommendation when no valid composition exists.

## AI / LLM Rules

Use LLMs for probabilistic interpretation, not deterministic business rules.

Good LLM responsibilities:
- interpret natural-language requests;
- extract structured bouquet preferences;
- conversational clarification;
- user-friendly explanations;
- future catalog enrichment.

Deterministic code remains responsible for:
- prices;
- stock;
- availability;
- florist ownership;
- totals;
- database integrity;
- hard business rules.

Preferred future flow:

```text
Natural language
      ↓
LLM / structured extraction
      ↓
BouquetRequest
      ↓
deterministic recommendation engine
      ↓
Recommendation
```

Do not couple core business logic directly to a specific LLM provider.

Future LLM integrations should support structured outputs, failure handling, timeouts, evaluation and observability.

## Bouquet Persistence

A recommendation is not automatically persisted.

Expected flow:

```text
Recommendation
      ↓
user accepts/saves
      ↓
BouquetCreate
      ↓
validation
      ↓
Bouquet + composition records
```

Before saving, validate:
- positive quantities;
- active florist catalog membership;
- sufficient stock.

Persist the bouquet and its composition atomically.

## Current Backend Capabilities

Currently implemented or in progress:
- florist-specific catalog and inventory;
- deterministic recommendation engine;
- stock and budget validation;
- preference handling and cheapest fallback;
- recommendation API;
- flower, foliage and wrapping catalog APIs;
- aggregated catalog API;
- reusable florist/database dependencies;
- detailed recommendation responses;
- bouquet persistence;
- bouquet item/quantity/stock validation;
- pytest suite;
- Ruff;
- GitHub Actions CI.

Immediate work is focused on robust bouquet persistence validation/error handling and API coverage before adding the LLM layer.

## Instructions for Coding Agents

When modifying FlowerAI:

1. Read the relevant existing code and tests before editing.
2. Do not invent models, columns, helpers, endpoints, or requirements without checking the repository.
3. Make the smallest coherent change that solves the task.
4. Preserve the current architecture and multi-florist behavior.
5. Keep business logic out of routers.
6. Treat price, stock, ownership and business constraints as server-authoritative.
7. Add or update tests with behavior changes.
8. Run `ruff check .` and `pytest`.
9. Investigate failures instead of weakening tests.
10. Do not unintentionally change existing API contracts.
11. Flag database/schema changes before destructive operations.
12. Avoid new dependencies unless they provide clear value.
13. Never commit secrets, local databases, virtual environments, caches or coverage artifacts.
