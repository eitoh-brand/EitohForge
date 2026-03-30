# Load Balancing and Health-Check Routing Policy

Reference architecture for L7/L4 balancing, health probes, and traffic routing behavior.

## 1) Target Architecture

- Default entrypoint: L7 load balancer + ingress gateway.
- Optional L4 passthrough for specialized protocols.
- Application nodes should remain stateless.
- Session affinity is disabled by default; enable only when protocol requires it.

## 2) Health Probe Contract

- Liveness endpoint: `/health`
- Readiness endpoint: `/ready`
- Status endpoint: `/status`

Routing policy:

- LB forwards traffic only to targets passing readiness checks.
- Liveness is used for restart decisions, not traffic eligibility.
- Status endpoint is for operators/diagnostics and dashboards.

## 3) Recommended Probe Settings

- Interval: 10s
- Timeout: 2s
- Success threshold: 1
- Failure threshold: 3
- Deregistration delay/drain timeout: 30-60s

## 4) Connection and Retry Baseline

- Upstream connect timeout: 2s
- Request timeout: 30s (adjust by endpoint class)
- Retries on idempotent requests only
- Circuit-breaker style outlier ejection for unhealthy targets

## 5) Sticky Session Policy

- Disallowed by default.
- Allowed only for protocols that cannot externalize session state.
- If enabled:
  - explicit TTL
  - documented rationale
  - failover behavior validated

## 6) Validation and Test Evidence

The platform already validates health routing primitives through automated tests:

- endpoint availability for `/health`, `/ready`, `/status`
- generated project route contract assertions

Operational validation checklist:

- [ ] LB marks target unhealthy when `/ready` fails.
- [ ] Recovered target re-enters pool after readiness passes.
- [ ] Draining policy avoids request drops during rollout.
- [ ] Retry policy does not amplify non-idempotent write failures.

## 7) Multi-AZ Baseline

- Distribute targets across >= 2 availability zones.
- Use cross-zone balancing where provider supports it.
- Keep minimum healthy target count per zone to tolerate zonal loss.
