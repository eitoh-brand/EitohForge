# Deployment Strategies and Rollback Controls

Production deployment playbook for rolling, blue/green, and canary strategies.

## 1) Strategy Selection Matrix

- **Rolling**: default for low-risk stateless updates.
- **Blue/Green**: preferred for high-risk releases needing near-instant rollback.
- **Canary**: preferred for behavior-sensitive changes with progressive risk control.

## 2) Global Guardrails

- All releases must use immutable build artifacts from CI.
- Database migrations must be backward-compatible for at least one release window.
- Pre-deploy checks required:
  - quality gates green
  - readiness route health green
  - rollback candidate confirmed

## 3) Rolling Deployment Playbook

1. Set max unavailable/min available thresholds.
2. Drain target before replacement.
3. Verify `/ready` before routing traffic to new pod/node.
4. Continue in batches until completion.
5. Monitor error budget burn and abort if threshold exceeded.

Rollback:

- revert deployment to previous image tag
- confirm readiness and key business smoke checks

## 4) Blue/Green Deployment Playbook

1. Keep `blue` (active) and `green` (candidate) environments.
2. Deploy candidate to inactive environment.
3. Run smoke + integration tests against candidate.
4. Shift traffic via LB switch or weighted rule update.
5. Keep prior environment warm for rollback window.

Rollback:

- switch traffic back to previous environment
- investigate failed candidate before retry

## 5) Canary Deployment Playbook

Suggested phases:

- 5% -> 20% -> 50% -> 100%

Gate checks at each phase:

- 5xx error rate within threshold
- latency SLO not violated
- no elevated business KPI regressions

Rollback:

- immediately route 100% to previous stable version
- freeze rollout until root cause is identified

## 6) Release Abort Criteria

- sustained 5xx breach > 0.5% over 5 minutes
- p95 latency regression > 30% vs baseline
- readiness failures across more than one zone
- severe incident escalation (SEV-1/SEV-2)

## 7) Post-Deploy Verification

- [ ] `/health`, `/ready`, `/status` healthy
- [ ] no abnormal error budget burn
- [ ] critical business flow smoke tests pass
- [ ] audit trail includes deploy actor, artifact, and timestamp
