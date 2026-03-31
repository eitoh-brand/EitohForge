"""Named policy registry for composing ABAC-style rules without a full DSL yet."""

from __future__ import annotations

from eitohforge_sdk.core.abac import AccessPolicy


class PolicyRegistry:
    """Register reusable policies by name (for documentation, composition, and future DSL hooks)."""

    def __init__(self) -> None:
        self._policies: dict[str, AccessPolicy] = {}

    def register(self, name: str, policy: AccessPolicy) -> None:
        if not name.strip():
            raise ValueError("Policy name is required.")
        self._policies[name.strip()] = policy

    def get(self, name: str) -> AccessPolicy | None:
        return self._policies.get(name.strip())

    def require(self, name: str) -> AccessPolicy:
        policy = self.get(name)
        if policy is None:
            raise KeyError(f"Unknown policy: {name}")
        return policy

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._policies.keys()))
