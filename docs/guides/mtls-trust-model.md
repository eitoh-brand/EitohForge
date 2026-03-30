# Optional mTLS Trust Model

Design baseline for optional service-to-service mTLS in internal traffic paths.

## Scope and Intent

- Provide a hardened internal communication profile where required by compliance or threat model.
- Keep mTLS optional by environment/security tier.
- Preserve a documented fallback for non-mTLS environments.

## 1) Trust Domains

- Define separate trust domains by environment:
  - `dev`
  - `staging`
  - `prod`
- Never share root/intermediate CAs across environments.
- Workload identity must be bound to a unique service account or SPIFFE-style identity.

## 2) Certificate Model

- Short-lived workload certificates (target: <= 24h validity).
- Automated issuance and rotation via service mesh or sidecar control plane.
- Leaf cert subject must map to service identity and namespace/project boundary.
- Mutual validation required:
  - client validates server identity
  - server validates client identity

## 3) Authorization Model

- mTLS authentication is necessary but not sufficient.
- Enforce service authorization by allowlist policy:
  - source identity
  - destination service
  - allowed method/port
- Deny-by-default for unlisted internal service paths.

## 4) Rotation and Revocation

- Automatic rotation before expiration (>= 30% lifetime remaining).
- Fast revocation process for compromised identity:
  - revoke identity binding
  - rotate trust bundle where applicable
  - block affected source at policy layer

## 5) Operational Modes

- `strict`: all internal service traffic requires mTLS.
- `permissive`: mTLS preferred, plaintext temporarily allowed during migration.
- Production target should be `strict` after rollout completion.

## 6) Rollout Plan

1. Enable permissive mode in staging and validate telemetry.
2. Turn on identity-based policy checks in audit mode.
3. Enforce strict mode per service group.
4. Promote to production in phased rollout by criticality tier.

## 7) Validation Checklist

- [ ] Identity issuance/rotation is fully automated.
- [ ] Expired or unknown certs are rejected.
- [ ] Unauthorized source identity is denied.
- [ ] Strict mode tested in staging before production enablement.
- [ ] Incident rollback documented and exercised.

## 8) Fallback Strategy

- If control-plane failure impacts availability:
  - temporarily degrade to permissive mode in non-prod only.
  - production exceptions require security approval and incident record.
