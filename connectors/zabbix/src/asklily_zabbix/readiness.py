"""Fail-closed L4 readiness and sanitized evidence summaries.

This module is deliberately transport-free: assessing readiness must never
touch a live endpoint or load a secret.
"""

from __future__ import annotations

from dataclasses import dataclass

from .client import ALLOWED_READ_METHODS
from .quality import ZabbixMappingQualityReport


@dataclass(frozen=True)
class L4PreflightResult:
    """The complete, non-sensitive gate decision before any live connection."""

    status: str
    blockers: tuple[str, ...]
    allowed_methods: tuple[str, ...]

    @property
    def can_start_live_readonly_run(self) -> bool:
        return self.status == "ready"


@dataclass(frozen=True)
class L4QualitySummary:
    """Audit-safe mapping evidence; it contains no identifiers or observations."""

    request_id: str
    mapping_quality: str
    inspected_resource_count: int
    complete_resource_count: int
    missing_mapping_resource_count: int
    duplicate_mapping_resource_count: int
    unusable_item_count: int
    allowed_methods: tuple[str, ...]


def assess_l4_preflight(
    *,
    adr_accepted: bool,
    local_configuration_present: bool,
    approved_scope_declared: bool,
    live_execution_authorized: bool,
) -> L4PreflightResult:
    """Return a deterministic gate decision without loading configuration or I/O."""

    blockers: list[str] = []
    if not adr_accepted:
        blockers.append("adr_not_accepted")
    if not local_configuration_present:
        blockers.append("local_readonly_configuration_missing")
    if not approved_scope_declared:
        blockers.append("approved_scope_missing")
    if not live_execution_authorized:
        blockers.append("live_execution_not_authorized")
    return L4PreflightResult(
        status="ready" if not blockers else "blocked",
        blockers=tuple(blockers),
        allowed_methods=tuple(sorted(ALLOWED_READ_METHODS)),
    )


def summarize_mapping_quality(request_id: str, report: ZabbixMappingQualityReport) -> L4QualitySummary:
    """Convert detailed local mapping diagnostics to a report-safe aggregate."""

    if not request_id.strip():
        raise ValueError("l4_request_id_required")
    return L4QualitySummary(
        request_id=request_id,
        mapping_quality=report.quality,
        inspected_resource_count=report.inspected_hosts,
        complete_resource_count=report.complete_hosts,
        missing_mapping_resource_count=len(report.missing_keys_by_host),
        duplicate_mapping_resource_count=len(report.duplicate_keys_by_host),
        unusable_item_count=len(report.unusable_items),
        allowed_methods=tuple(sorted(ALLOWED_READ_METHODS)),
    )
