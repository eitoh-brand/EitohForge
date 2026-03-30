# TLS Strategy and Certificate Rotation Runbook

Operational policy for ingress TLS termination, certificate lifecycle, and key rotation.

## Scope

- Public ingress and API gateway TLS posture.
- Certificate issuance, renewal, and emergency rotation controls.
- Runtime verification and rollback criteria.

## 1) TLS Termination Policy

- Terminate TLS at the ingress controller or API gateway (default).
- Enforce HTTPS redirect at edge (`80 -> 443`).
- Reject weak protocol versions; allow only TLS `1.2+` (prefer `1.3`).
- Disable insecure ciphers and legacy renegotiation.
- Use HSTS for production domains with preload only after validation.

## 2) Certificate Authority and Issuance

- Preferred issuance: managed ACME flow through enterprise CA integration.
- Allowed alternatives:
  - internal PKI-backed cert-manager issuer
  - managed cloud certificate service
- Wildcard certificates are allowed for non-sensitive shared ingress domains only.
- High-sensitivity services should use service-specific certificates.

## 3) Rotation and Expiry Policy

- Standard rotation cadence: every 60-90 days.
- Renewal trigger threshold: <= 30 days to expiry.
- Alert thresholds:
  - warning at 21 days
  - critical at 7 days
- Emergency rotation SLA: <= 4 hours after key compromise signal.

## 4) Key Management Controls

- Private keys must be generated and stored in managed secret stores.
- No private key material in repository, images, or runtime logs.
- Access to certificate secrets limited to platform runtime identities.
- All rotation operations require auditable change records.

## 5) Runtime Verification Checklist

- [ ] Ingress endpoints serve valid cert chain.
- [ ] Certificate SAN/CN matches production hostnames.
- [ ] TLS scanner confirms only approved protocol/cipher set.
- [ ] HTTP redirects enforce HTTPS consistently.
- [ ] Health endpoints (`/health`, `/ready`, `/status`) are reachable via HTTPS.

## 6) Rollback Procedure

1. Keep previous certificate version available for immediate fallback.
2. If handshake failures increase, roll back ingress secret reference.
3. Recheck certificate chain and hostname mapping.
4. Confirm service recovery and document incident details.

## 7) Ownership and Approval

- Primary owner: platform team.
- Security approval required for:
  - CA changes
  - protocol/cipher policy relaxation
  - wildcard cert use on sensitive workloads
