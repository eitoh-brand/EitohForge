"""Core-layer scaffold template fragments."""

from eitohforge_cli.template_parts.core_templates_auth import CORE_AUTH_FILE_TEMPLATES
from eitohforge_cli.template_parts.core_templates_platform import CORE_PLATFORM_FILE_TEMPLATES
from eitohforge_cli.template_parts.core_templates_runtime import CORE_RUNTIME_FILE_TEMPLATES
from eitohforge_cli.template_parts.core_templates_security import CORE_SECURITY_FILE_TEMPLATES
from eitohforge_cli.template_parts.core_templates_validation import CORE_VALIDATION_FILE_TEMPLATES

CORE_FILE_TEMPLATES: dict[str, str] = {
    **CORE_PLATFORM_FILE_TEMPLATES,
    **CORE_AUTH_FILE_TEMPLATES,
    **CORE_VALIDATION_FILE_TEMPLATES,
    **CORE_SECURITY_FILE_TEMPLATES,
    **CORE_RUNTIME_FILE_TEMPLATES,
}
