# ADR 0001: ORM and Migration Strategy

## Status

Accepted

## Context

EitohForge needs a production-safe, typed, migration-driven relational persistence baseline that can evolve into polyglot storage later.

## Decision

- Primary ORM stack: SQLAlchemy 2.x style.
- Migration tool: Alembic.
- Primary relational adapter for first release: Postgres.
- Migration operations are mandatory for schema changes.

## Consequences

- Strong ecosystem support for enterprise usage.
- Stable migration workflow with upgrade/downgrade controls.
- Clear expansion path to other providers through adapter interfaces.
