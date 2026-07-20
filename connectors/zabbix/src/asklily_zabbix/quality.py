"""Explicit item-key mapping and quality assessment for a future L4 optic run."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class OpticFieldMapping:
    rx_power_key: str
    tx_power_key: str
    temperature_key: str

    @property
    def required_keys(self) -> frozenset[str]:
        return frozenset({self.rx_power_key, self.tx_power_key, self.temperature_key})


@dataclass(frozen=True)
class ZabbixMappingQualityReport:
    inspected_hosts: int
    complete_hosts: int
    missing_keys_by_host: Mapping[str, tuple[str, ...]]
    duplicate_keys_by_host: Mapping[str, tuple[str, ...]]
    unusable_items: tuple[str, ...]
    quality: str


def assess_optic_mapping(
    hosts: Sequence[Mapping[str, object]], items: Sequence[Mapping[str, object]], mapping: OpticFieldMapping
) -> ZabbixMappingQualityReport:
    """Report mapping readiness without retaining raw metric values or host names."""

    host_ids = {str(host["hostid"]) for host in hosts if host.get("hostid") is not None}
    keys_by_host: dict[str, list[str]] = defaultdict(list)
    unusable_items: list[str] = []
    for item in items:
        host_id = str(item.get("hostid", ""))
        key = item.get("key_")
        if host_id not in host_ids or not isinstance(key, str):
            unusable_items.append(str(item.get("itemid", "unknown")))
            continue
        keys_by_host[host_id].append(key)

    missing: dict[str, tuple[str, ...]] = {}
    duplicate: dict[str, tuple[str, ...]] = {}
    complete = 0
    for host_id in sorted(host_ids):
        seen = keys_by_host[host_id]
        missing_keys = tuple(sorted(mapping.required_keys - set(seen)))
        duplicate_keys = tuple(sorted(key for key in mapping.required_keys if seen.count(key) > 1))
        if missing_keys:
            missing[host_id] = missing_keys
        if duplicate_keys:
            duplicate[host_id] = duplicate_keys
        if not missing_keys and not duplicate_keys:
            complete += 1
    quality = "ready" if complete == len(host_ids) and not unusable_items else "needs_mapping_review"
    return ZabbixMappingQualityReport(
        inspected_hosts=len(host_ids),
        complete_hosts=complete,
        missing_keys_by_host=missing,
        duplicate_keys_by_host=duplicate,
        unusable_items=tuple(sorted(unusable_items)),
        quality=quality,
    )
