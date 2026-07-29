"""Pure, fail-closed preflight for P5E; it never reads credentials or performs I/O."""

from __future__ import annotations

from dataclasses import dataclass

READ_ONLY_OPERATIONS: dict[str, tuple[str, ...]] = {
    "zabbix": ("history.get", "host.get", "item.get"),
    "prometheus": ("query", "query_range"),
}


class MonitoringSourcePolicyError(ValueError):
    """Raised for an unsupported source or a non-read-only requested operation."""


@dataclass(frozen=True)
class MonitoringSourcePreflight:
    source_kind: str
    status: str
    blockers: tuple[str, ...]
    allowed_operations: tuple[str, ...]

    @property
    def can_start_live_readonly_run(self) -> bool:
        return self.status == "ready"


def assess_monitoring_source_preflight(
    source_kind: str,
    *,
    source_declared: bool,
    configuration_declared: bool,
    approved_scope_declared: bool,
    governance_accepted: bool,
    live_execution_authorized: bool,
    requested_operation: str | None = None,
) -> MonitoringSourcePreflight:
    """Assess only caller-supplied booleans; no endpoint, secret or network is touched."""
    try:
        allowed = READ_ONLY_OPERATIONS[source_kind]
    except KeyError as exc:
        raise MonitoringSourcePolicyError("monitoring_source_kind_unsupported") from exc
    if requested_operation is not None and requested_operation not in allowed:
        raise MonitoringSourcePolicyError("monitoring_operation_not_read_only")
    blockers: list[str] = []
    for condition, code in (
        (source_declared, "monitoring_source_not_declared"),
        (configuration_declared, "monitoring_configuration_not_declared"),
        (approved_scope_declared, "monitoring_scope_not_declared"),
        (governance_accepted, "monitoring_governance_not_accepted"),
        (live_execution_authorized, "monitoring_live_execution_not_authorized"),
    ):
        if not condition:
            blockers.append(code)
    return MonitoringSourcePreflight(source_kind, "ready" if not blockers else "blocked", tuple(blockers), allowed)
