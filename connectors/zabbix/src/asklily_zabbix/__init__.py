"""Fail-closed Zabbix read-only Connector preparation for P3."""

from .client import (
    ALLOWED_READ_METHODS,
    ConnectorConfigurationError,
    ConnectorPolicyError,
    JsonRpcTransport,
    ZabbixReadOnlyClient,
    ZabbixReadOnlyConfig,
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
    "assess_optic_mapping",
]
