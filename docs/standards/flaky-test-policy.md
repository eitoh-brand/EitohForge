# Flaky Test Policy

This policy defines how intermittent test failures are handled without eroding CI trust.

## Principles

- A flaky test is worse than a failing test: it trains teams to ignore CI.
- Quarantine is temporary; removal or fix is mandatory.

## Detection

- Any test that fails on main without a code defect in the same commit is investigated as flaky.
- CI reruns may be used once for signal, not as a permanent workaround.

## Quarantine Process

1. Open a tracked remediation item with owner and SLA (default: 5 business days).
2. Mark the test with `@pytest.mark.flaky` and add a module docstring or comment referencing the ticket ID.
3. Prefer moving the test behind an explicit job or skipping with a **single** guarded skip (not broad `skip`).

## Remediation SLA

- `P0` flake blocking release: fix or disable within 24 hours.
- `P1` flake: fix within 5 business days.
- `P2` flake: fix within 10 business days.

## Removal

- Remove `flaky` marker only after the test is stabilized (root cause fixed or test rewritten).
- Do not increase `cov-fail-under` or weaken other gates to hide flakes.

## Ownership

- Test author owns first response.
- Platform team arbitrates if ownership is unclear.
