"""Unified runtime and explicit, read-only data-source registration."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class RuntimeConfigError(ValueError):
    """A safe failure for missing or invalid deployment configuration."""


@dataclass(frozen=True)
class DataSource:
    source_id: str
    kind: str
    enabled: bool
    read_only: bool
    data_level: str
    capability_ids: tuple[str, ...]
    visible_site_ids: frozenset[str]
    declared_environment: str
    config_revision: str

    def public_state(self, allowed_site_ids: frozenset[str] | None = None) -> dict[str, object]:
        if not self.enabled:
            state, reason = "disabled", "data_source_disabled"
        elif self.kind == "fixture":
            state, reason = "ready", None
        else:
            # P6 deliberately does not establish a real connector or L4 claim.
            state, reason = "unavailable", "connector_not_validated"
        visible_sites = self.visible_site_ids if allowed_site_ids is None else self.visible_site_ids & allowed_site_ids
        return {
            "source_id": self.source_id,
            "kind": self.kind,
            "enabled": self.enabled,
            "read_only": self.read_only,
            "data_level": self.data_level,
            "declared_environment": self.declared_environment,
            "visible_site_ids": sorted(visible_sites),
            "connection_state": state,
            "reason_code": reason,
            "last_checked_at": None,
            "config_revision": self.config_revision,
        }


@dataclass(frozen=True)
class RuntimeConfig:
    schema_version: str
    deployment_environment: str
    sources: tuple[DataSource, ...]

    def source_for_capability(self, capability_id: str) -> DataSource | None:
        return next((item for item in self.sources if capability_id in item.capability_ids), None)


def default_source_registry_path() -> Path:
    return Path(__file__).resolve().parents[4] / "deploy" / "runtime" / "sources.fixture.json"


def load_runtime_config(environment: dict[str, str] | None = None) -> RuntimeConfig:
    values = os.environ if environment is None else environment
    configured = values.get("ASKLILY_SOURCE_REGISTRY", "").strip()
    path = Path(configured) if configured else default_source_registry_path()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeConfigError("data_source_registry_unavailable") from exc
    if not isinstance(raw, dict) or raw.get("schema_version") != "1.0.0":
        raise RuntimeConfigError("data_source_registry_invalid")
    deployment = raw.get("deployment")
    sources = raw.get("sources")
    if not isinstance(deployment, dict) or not isinstance(sources, list):
        raise RuntimeConfigError("data_source_registry_invalid")
    environment_label = deployment.get("declared_environment")
    if environment_label not in {"fixture", "test", "production"}:
        raise RuntimeConfigError("data_source_environment_invalid")
    parsed = tuple(_parse_source(item, environment_label) for item in sources)
    if not parsed or len({item.source_id for item in parsed}) != len(parsed):
        raise RuntimeConfigError("data_source_registry_invalid")
    return RuntimeConfig("1.0.0", environment_label, parsed)


def _parse_source(value: Any, deployment_environment: str) -> DataSource:
    if not isinstance(value, dict):
        raise RuntimeConfigError("data_source_registry_invalid")
    source_id = value.get("source_id")
    kind = value.get("kind")
    enabled = value.get("enabled")
    read_only = value.get("read_only")
    data_level = value.get("data_level")
    capabilities = value.get("capability_ids")
    sites = value.get("visible_site_ids", [])
    revision = value.get("config_revision")
    if (
        not isinstance(source_id, str)
        or not source_id
        or kind not in {"fixture", "zabbix", "prometheus"}
        or not isinstance(enabled, bool)
        or read_only is not True
        or data_level not in {"L0_L1", "unverified"}
        or not isinstance(capabilities, list)
        or not all(isinstance(item, str) and item for item in capabilities)
        or not isinstance(sites, list)
        or not sites
        or not all(isinstance(item, str) and item for item in sites)
        or not isinstance(revision, str)
        or not revision
    ):
        raise RuntimeConfigError("data_source_registry_invalid")
    if kind == "fixture" and (deployment_environment != "fixture" or data_level != "L0_L1"):
        raise RuntimeConfigError("fixture_environment_or_level_invalid")
    if kind != "fixture" and data_level != "unverified":
        raise RuntimeConfigError("real_source_l4_not_authorized")
    return DataSource(source_id, kind, enabled, read_only, data_level, tuple(capabilities), frozenset(sites), deployment_environment, revision)
