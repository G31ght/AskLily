"""P1 platform guards and deterministic Fixture domain capabilities."""

from .optic_health import OPTIC_RULE_VERSION, OpticHealthQuery, query_optic_health
from .registry import PlatformRegistry
from .resource_explorer import (
    ALLOWED_RESOURCE_TYPES,
    OPTIC_MODULE_TYPE,
    RESOURCE_EXPLORER_SOURCE,
    ResourceDirectoryRecord,
    ResourceSearchPage,
    related_resources,
    resource_detail,
    search_resources,
    validate_resource_query,
)

__all__ = [
    "ALLOWED_RESOURCE_TYPES",
    "OPTIC_MODULE_TYPE",
    "OPTIC_RULE_VERSION",
    "RESOURCE_EXPLORER_SOURCE",
    "OpticHealthQuery",
    "PlatformRegistry",
    "ResourceDirectoryRecord",
    "ResourceSearchPage",
    "query_optic_health",
    "related_resources",
    "resource_detail",
    "search_resources",
    "validate_resource_query",
]
