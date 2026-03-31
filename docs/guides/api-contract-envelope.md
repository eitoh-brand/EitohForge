# API JSON envelope (contract middleware)

When enabled, JSON responses must match the standard envelope:

- Root object with boolean `success`.
- If `success` is `false`, include `error` with `code` and `message` (strings).

## Enable

Set `EITOHFORGE_API_CONTRACT_ENFORCE_JSON_ENVELOPE=true` (or `AppSettings.api_contract.enforce_json_envelope`).

The Forge registers `register_api_contract_middleware` when the `api_contract` platform toggle is on.

Paths under `/docs`, `/openapi.json`, `/health`, `/ready`, `/status`, `/metrics`, `/sdk/capabilities`, and static `/static` are excluded.

Invalid responses return **500** with body `{"success":false,"error":{"code":"INVALID_API_ENVELOPE","message":"..."}}`.
