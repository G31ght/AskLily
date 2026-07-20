"""Dependency-free, versioned contracts for the P1 platform skeleton.

These models describe platform semantics only. They do not provide a Connector,
business rule, real data source, or external write operation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, FrozenSet, Mapping, Optional, Tuple

API_CONTRACT_VERSION = "1.0.0"
TOOL_CONTRACT_VERSION = "1.0.0"
VIEW_CONTRACT_VERSION = "1.0.0"
CAPABILITY_CONTRACT_VERSION = "1.0.0"


class ContractViolation(ValueError):
    """Raised when a caller violates a versioned platform contract."""


@dataclass(frozen=True)
class Scope:
    """Server-issued, allow-list data boundary. Owner: Identity / API."""

    project_id: str
    site_ids: FrozenSet[str] = field(default_factory=frozenset)
    cluster_ids: FrozenSet[str] = field(default_factory=frozenset)
    resource_types: FrozenSet[str] = field(default_factory=frozenset)
    actions: FrozenSet[str] = field(default_factory=lambda: frozenset({"read"}))

    def narrowed_to(self, requested: "Scope") -> "Scope":
        """Return a safe intersection; callers can never widen a Scope."""
        if requested.project_id != self.project_id:
            raise ContractViolation("scope_project_mismatch")
        if not requested.actions.issubset(self.actions):
            raise ContractViolation("scope_action_not_allowed")
        return Scope(
            project_id=self.project_id,
            site_ids=_narrow_dimension(self.site_ids, requested.site_ids, "site"),
            cluster_ids=_narrow_dimension(self.cluster_ids, requested.cluster_ids, "cluster"),
            resource_types=_narrow_dimension(
                self.resource_types, requested.resource_types, "resource_type"
            ),
            actions=requested.actions,
        )


def _narrow_dimension(
    granted: FrozenSet[str], requested: FrozenSet[str], dimension: str
) -> FrozenSet[str]:
    """An empty granted dimension means unrestricted only for that dimension."""
    if not requested:
        return granted
    if granted and not requested.issubset(granted):
        raise ContractViolation(f"scope_{dimension}_not_allowed")
    return requested


@dataclass(frozen=True)
class Resource:
    """Minimal resource identity. Owner: Domain."""

    resource_id: str
    project_id: str
    resource_type: str
    display_name: str
    site_id: Optional[str] = None
    cluster_id: Optional[str] = None
    source_ref: Optional[str] = None


@dataclass(frozen=True)
class Observation:
    """A source-attributed fact; it is not a health conclusion. Owner: Domain."""

    observation_id: str
    resource_id: str
    observed_at: datetime
    source: str
    values: Mapping[str, Any]
    quality: str


@dataclass(frozen=True)
class HealthAssessment:
    """A user-facing conclusion produced by a versioned domain rule. Owner: Domain."""

    resource_id: str
    health: str
    reason_codes: Tuple[str, ...]
    evaluated_at: datetime
    evidence_refs: Tuple[str, ...]
    rule_version: str


@dataclass(frozen=True)
class ApiError:
    """Typed failure, never a fabricated result. Owner: API / Domain."""

    code: str
    message: str
    request_id: str
    retryable: bool = False


@dataclass(frozen=True)
class PlatformResponse:
    """Envelope for versioned API responses. Owner: API / Domain."""

    contract_version: str
    request_id: str
    data: Optional[Mapping[str, Any]] = None
    error: Optional[ApiError] = None
    query_id: Optional[str] = None

    def __post_init__(self) -> None:
        if (self.data is None) == (self.error is None):
            raise ContractViolation("response_requires_exactly_one_of_data_or_error")


@dataclass(frozen=True)
class ToolContract:
    """Registered callable capability, not a direct data-source query. Owner: Agent / Domain."""

    tool_id: str
    version: str
    owner: str
    required_action: str
    input_schema_version: str
    output_schema_version: str
    read_only: bool = True


@dataclass(frozen=True)
class ViewContext:
    """Registered workspace state. Owner: Web / Domain."""

    view_id: str
    version: str
    scope: Scope
    filters: Mapping[str, Any]
    focus_resource_id: Optional[str] = None
    query_id: Optional[str] = None


@dataclass(frozen=True)
class CapabilityManifest:
    """Authoritative capability catalog entry. Owner: Capability Registry."""

    capability_id: str
    version: str
    owner: str
    status: str
    profile: str
    tool_ids: Tuple[str, ...]
    view_ids: Tuple[str, ...]
    limitations: Tuple[str, ...]


@dataclass(frozen=True)
class AuditEvent:
    """Trace of a platform request or denial. Owner: Audit."""

    event_id: str
    occurred_at: datetime
    actor_id: str
    action: str
    outcome: str
    request_id: str
    scope_project_id: str
    query_id: Optional[str] = None
    tool_id: Optional[str] = None
    reason_code: Optional[str] = None
