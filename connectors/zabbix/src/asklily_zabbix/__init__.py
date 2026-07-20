"""Fail-closed Zabbix read-only Connector preparation for P3."""

from .client import (
    ALLOWED_READ_METHODS,
    ConnectorConfigurationError,
    ConnectorPolicyError,
    JsonRpcTransport,
    ZabbixReadOnlyClient,
    ZabbixReadOnlyConfig,
)
from .normalizer import (
    ZABBIX_READONLY_SOURCE,
    ZabbixNormalizationResult,
    ZabbixOpticScopeBinding,
    normalize_optic_readonly_results,
)
from .quality import OpticFieldMapping, ZabbixMappingQualityReport, assess_optic_mapping

__all__ = [
    "ALLOWED_READ_METHODS",
    "ConnectorConfigurationError",
    "ConnectorPolicyError",
    "JsonRpcTransport",
    "OpticFieldMapping",
    "ZabbixMappingQualityReport",
    "ZabbixReadOnlyClient",
    "ZabbixReadOnlyConfig",
    "ZABBIX_READONLY_SOURCE",
    "ZabbixNormalizationResult",
    "ZabbixOpticScopeBinding",
    "assess_optic_mapping",
    "normalize_optic_readonly_results",
]
