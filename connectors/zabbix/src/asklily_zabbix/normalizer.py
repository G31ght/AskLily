"""Normalize mock or future Zabbix read results into P2 Resource/Observation facts."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from asklily_contracts import Observation, Resource

from .quality import OpticFieldMapping

ZABBIX_READONLY_SOURCE = "zabbix://live-readonly"


@dataclass(frozen=True)
class ZabbixOpticScopeBinding:
    project_id: str
    site_id: str
    cluster_id: str | None = None


@dataclass(frozen=True)
class ZabbixNormalizationResult:
    resources: tuple[Resource, ...]
    observations: tuple[Observation, ...]
    quality_by_resource_id: Mapping[str, str]


def normalize_optic_readonly_results(
    hosts: Sequence[Mapping[str, object]],
    items: Sequence[Mapping[str, object]],
    history: Sequence[Mapping[str, object]],
    mapping: OpticFieldMapping,
    binding: ZabbixOpticScopeBinding,
) -> ZabbixNormalizationResult:
    """Preserve source/time/quality and never infer values absent from Zabbix output."""

    history_by_item: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    for entry in history:
        item_id = entry.get("itemid")
        if item_id is not None:
            history_by_item[str(item_id)].append(entry)
    items_by_host: dict[str, dict[str, list[Mapping[str, object]]]] = defaultdict(lambda: defaultdict(list))
    for item in items:
        host_id = item.get("hostid")
        key = item.get("key_")
        if host_id is not None and isinstance(key, str):
            items_by_host[str(host_id)][key].append(item)

    resources: list[Resource] = []
    observations: list[Observation] = []
    quality: dict[str, str] = {}
    for host in hosts:
        host_id = host.get("hostid")
        if host_id is None:
            continue
        host_key = str(host_id)
        resource_id = f"zabbix-optic:{host_key}"
        display_name = str(host.get("name") or host.get("host") or resource_id)
        resource = Resource(
            resource_id=resource_id,
            project_id=binding.project_id,
            resource_type="optic_module",
            display_name=display_name,
            site_id=binding.site_id,
            cluster_id=binding.cluster_id,
            source_ref=f"zabbix-host:{host_key}",
        )
        resources.append(resource)
        values, observed_at, record_quality = _latest_values(
            items_by_host[host_key], history_by_item, mapping
        )
        quality[resource_id] = record_quality
        observations.append(
            Observation(
                observation_id=f"zabbix-observation:{host_key}:{int(observed_at.timestamp())}",
                resource_id=resource_id,
                observed_at=observed_at,
                source=ZABBIX_READONLY_SOURCE,
                values=values,
                quality=record_quality,
            )
        )
    return ZabbixNormalizationResult(tuple(resources), tuple(observations), quality)


def _latest_values(
    items_by_key: Mapping[str, Sequence[Mapping[str, object]]],
    history_by_item: Mapping[str, Sequence[Mapping[str, object]]],
    mapping: OpticFieldMapping,
) -> tuple[dict[str, float | None], datetime, str]:
    mapped_keys = {
        "rx_dbm": mapping.rx_power_key,
        "tx_dbm": mapping.tx_power_key,
        "temperature_c": mapping.temperature_key,
    }
    values: dict[str, float | None] = {field: None for field in mapped_keys}
    timestamps: list[datetime] = []
    qualities: set[str] = set()
    for field, item_key in mapped_keys.items():
        candidates = items_by_key.get(item_key, ())
        if len(candidates) != 1:
            qualities.add("duplicate_mapping" if len(candidates) > 1 else "missing")
            continue
        samples = history_by_item.get(str(candidates[0].get("itemid")), ())
        if not samples:
            qualities.add("missing")
            continue
        latest = max(samples, key=lambda item: _clock(item))
        try:
            raw_value = latest["value"]
            if not isinstance(raw_value, (str, int, float)):
                raise ValueError("Zabbix history value is not numeric")
            values[field] = float(raw_value)
            timestamps.append(_clock(latest))
        except (KeyError, TypeError, ValueError):
            qualities.add("invalid")
    observed_at = max(timestamps) if timestamps else datetime.fromtimestamp(0, UTC)
    return values, observed_at, _quality(qualities)


def _clock(value: Mapping[str, object]) -> datetime:
    return datetime.fromtimestamp(int(str(value["clock"])), UTC)


def _quality(qualities: set[str]) -> str:
    if "invalid" in qualities:
        return "invalid"
    if "duplicate_mapping" in qualities:
        return "duplicate_mapping"
    if "missing" in qualities:
        return "missing"
    return "complete"
