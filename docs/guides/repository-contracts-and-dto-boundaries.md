# Repository Contracts and DTO Boundaries

This guide defines the clean-architecture persistence boundary used by EitohForge.

## Why This Boundary Exists

- Keep application and domain logic independent from DB engines.
- Enforce typed repository inputs and outputs.
- Attach tenant/trace/security context to persistence calls.
- Standardize list/paginate behavior before concrete adapters are implemented.

## Core SDK Contracts

- Repository contract:
  - `eitohforge_sdk.domain.repositories.contracts.RepositoryContract`
- Query DTOs:
  - `eitohforge_sdk.application.dto.repository.QuerySpec`
  - `FilterCondition`, `SortSpec`, `PaginationSpec`
- Context DTO:
  - `RepositoryContext` for actor/tenant/request/trace propagation
- Page response:
  - `PageResult[T]` for paginated access

## Enterprise Design Notes

- Type variance is defined intentionally:
  - entity type is covariant (output-oriented)
  - create/update payload types are contravariant (input-oriented)
- DTOs are immutable (`frozen`) to reduce accidental mutation across layers.
- Pagination defaults are bounded to prevent unbounded reads.

## Usage Rule

Implement repositories against these contracts in infrastructure adapters; do not leak adapter-specific types into application or domain layers.
