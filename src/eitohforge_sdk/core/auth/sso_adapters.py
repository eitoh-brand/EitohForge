"""Baseline OIDC and SAML SSO adapters."""

from __future__ import annotations

import base64
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any
import json
from xml.etree import ElementTree

from eitohforge_sdk.core.auth.sso import ExternalIdentity

OidcTokenExchange = Callable[[dict[str, str]], Mapping[str, Any]]


class SsoAdapterError(ValueError):
    """Base SSO adapter error."""


class OidcExchangeError(SsoAdapterError):
    """Raised when OIDC token exchange or ID token parsing fails."""


class SamlExchangeError(SsoAdapterError):
    """Raised when SAML response parsing fails."""


@dataclass
class OidcSsoProvider:
    """OIDC adapter implementing the SSO provider contract."""

    name: str
    token_endpoint: str
    client_id: str
    client_secret: str
    transport: OidcTokenExchange
    default_tenant_claim: str = "tenant_id"

    def exchange_authorization_code(
        self, *, code: str, redirect_uri: str | None = None, state: str | None = None
    ) -> ExternalIdentity:
        _ = state
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "token_endpoint": self.token_endpoint,
        }
        if redirect_uri is not None:
            payload["redirect_uri"] = redirect_uri

        token_response = dict(self.transport(payload))
        id_token = token_response.get("id_token")
        if not isinstance(id_token, str) or not id_token.strip():
            raise OidcExchangeError("OIDC response missing id_token.")
        claims = _decode_jwt_payload_without_verification(id_token)
        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject.strip():
            raise OidcExchangeError("OIDC id_token missing subject claim.")

        tenant_id = claims.get(self.default_tenant_claim) or claims.get("tid")
        return ExternalIdentity(
            provider=self.name,
            subject=subject,
            email=claims.get("email") if isinstance(claims.get("email"), str) else None,
            display_name=claims.get("name") if isinstance(claims.get("name"), str) else None,
            tenant_id=tenant_id if isinstance(tenant_id, str) else None,
            claims=claims,
        )


SamlAssertionParser = Callable[[str], Mapping[str, Any]]


@dataclass
class SamlSsoProvider:
    """SAML adapter implementing the SSO provider contract."""

    name: str
    parser: SamlAssertionParser = field(default_factory=lambda: _parse_saml_assertion)
    default_tenant_attribute: str = "tenant_id"

    def exchange_authorization_code(
        self, *, code: str, redirect_uri: str | None = None, state: str | None = None
    ) -> ExternalIdentity:
        _ = (redirect_uri, state)
        try:
            xml_payload = base64.b64decode(code.encode("utf-8"), validate=False).decode("utf-8")
        except Exception as exc:
            raise SamlExchangeError("Invalid SAML response encoding.") from exc

        claims = dict(self.parser(xml_payload))
        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject.strip():
            raise SamlExchangeError("SAML assertion missing subject.")
        tenant_id = claims.get(self.default_tenant_attribute)
        return ExternalIdentity(
            provider=self.name,
            subject=subject,
            email=claims.get("email") if isinstance(claims.get("email"), str) else None,
            display_name=claims.get("name") if isinstance(claims.get("name"), str) else None,
            tenant_id=tenant_id if isinstance(tenant_id, str) else None,
            claims=claims,
        )


def _decode_jwt_payload_without_verification(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise OidcExchangeError("Invalid JWT format for id_token.")
    payload_segment = parts[1]
    padding = "=" * (-len(payload_segment) % 4)
    try:
        payload_bytes = base64.urlsafe_b64decode(payload_segment + padding)
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as exc:
        raise OidcExchangeError("Unable to decode OIDC id_token payload.") from exc
    if not isinstance(payload, dict):
        raise OidcExchangeError("OIDC id_token payload is not a JSON object.")
    return payload


def _parse_saml_assertion(xml_payload: str) -> Mapping[str, Any]:
    namespaces = {
        "saml2": "urn:oasis:names:tc:SAML:2.0:assertion",
    }
    try:
        root = ElementTree.fromstring(xml_payload)
    except Exception as exc:
        raise SamlExchangeError("Invalid SAML XML payload.") from exc

    subject_node = root.find(".//saml2:Subject/saml2:NameID", namespaces)
    if subject_node is None or not subject_node.text:
        raise SamlExchangeError("SAML NameID is missing.")

    claims: dict[str, Any] = {"sub": subject_node.text.strip()}
    for attribute in root.findall(".//saml2:Attribute", namespaces):
        name = attribute.attrib.get("Name", "").strip()
        if not name:
            continue
        value_node = attribute.find("saml2:AttributeValue", namespaces)
        if value_node is None or value_node.text is None:
            continue
        claims[name] = value_node.text.strip()
    return claims
