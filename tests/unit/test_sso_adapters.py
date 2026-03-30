from __future__ import annotations

import base64
import json

from eitohforge_sdk.core.auth.sso_adapters import OidcSsoProvider, SamlSsoProvider


def test_oidc_provider_exchanges_code_and_builds_external_identity() -> None:
    payload = _jwt_payload(
        {
            "sub": "oidc-user-1",
            "email": "oidc@example.com",
            "name": "OIDC User",
            "tenant_id": "tenant-a",
        }
    )

    provider = OidcSsoProvider(
        name="oidc",
        token_endpoint="https://issuer.example.com/token",
        client_id="client-id",
        client_secret="client-secret",
        transport=lambda _: {"id_token": payload},
    )
    identity = provider.exchange_authorization_code(code="auth-code", redirect_uri="https://app/callback")

    assert identity.provider == "oidc"
    assert identity.subject == "oidc-user-1"
    assert identity.email == "oidc@example.com"
    assert identity.tenant_id == "tenant-a"


def test_saml_provider_parses_nameid_and_attributes() -> None:
    xml = """
<saml2:Response xmlns:saml2="urn:oasis:names:tc:SAML:2.0:assertion">
  <saml2:Assertion>
    <saml2:Subject>
      <saml2:NameID>saml-user-1</saml2:NameID>
    </saml2:Subject>
    <saml2:AttributeStatement>
      <saml2:Attribute Name="email"><saml2:AttributeValue>saml@example.com</saml2:AttributeValue></saml2:Attribute>
      <saml2:Attribute Name="tenant_id"><saml2:AttributeValue>tenant-b</saml2:AttributeValue></saml2:Attribute>
      <saml2:Attribute Name="name"><saml2:AttributeValue>SAML User</saml2:AttributeValue></saml2:Attribute>
    </saml2:AttributeStatement>
  </saml2:Assertion>
</saml2:Response>
"""
    encoded = base64.b64encode(xml.encode("utf-8")).decode("utf-8")

    provider = SamlSsoProvider(name="saml")
    identity = provider.exchange_authorization_code(code=encoded)

    assert identity.provider == "saml"
    assert identity.subject == "saml-user-1"
    assert identity.email == "saml@example.com"
    assert identity.tenant_id == "tenant-b"


def _jwt_payload(claims: dict[str, str]) -> str:
    header = _b64url(json.dumps({"alg": "none", "typ": "JWT"}).encode("utf-8"))
    payload = _b64url(json.dumps(claims).encode("utf-8"))
    signature = _b64url(b"sig")
    return f"{header}.{payload}.{signature}"


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")
