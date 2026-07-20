"""Deterministic L0/L1 optical-health domain slice with no external connector."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime

from asklily_contracts import Event, HealthAssessment, Observation, Resource, Scope

OPTIC_RULE_VERSION = "demo-1.0.0"
FIXTURE_SOURCE = "fixture://optic-health/l0-l1-v1"
OPTIC_RESOURCE_TYPE = "optic_module"


@dataclass(frozen=True)
class OpticHealthRecord:
    resource: Resource
    latest_observation: Observation
    assessment: HealthAssessment
    event: Event | None


@dataclass(frozen=True)
class OpticHealthQuery:
    records: tuple[OpticHealthRecord, ...]
    summary: dict[str, int]
    source: str
    observed_from: datetime
    observed_to: datetime
    rule_version: str


def _at(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


FIXTURE_RESOURCES = (
    Resource("optic-a-01", "demo-project", OPTIC_RESOURCE_TYPE, "leaf-a01 / Ethernet1/1", "site-a", source_ref=FIXTURE_SOURCE),
    Resource("optic-a-02", "demo-project", OPTIC_RESOURCE_TYPE, "leaf-a01 / Ethernet1/2", "site-a", source_ref=FIXTURE_SOURCE),
    Resource("optic-a-03", "demo-project", OPTIC_RESOURCE_TYPE, "leaf-a01 / Ethernet1/3", "site-a", source_ref=FIXTURE_SOURCE),
    Resource("optic-a-04", "demo-project", OPTIC_RESOURCE_TYPE, "leaf-a02 / Ethernet1/1", "site-a", source_ref=FIXTURE_SOURCE),
    Resource("optic-a-05", "demo-project", OPTIC_RESOURCE_TYPE, "leaf-a02 / Ethernet1/2", "site-a", source_ref=FIXTURE_SOURCE),
    Resource("optic-a-06", "demo-project", OPTIC_RESOURCE_TYPE, "leaf-a02 / Ethernet1/3", "site-a", source_ref=FIXTURE_SOURCE),
    Resource("optic-a-07", "demo-project", OPTIC_RESOURCE_TYPE, "leaf-a03 / Ethernet1/1", "site-a", source_ref=FIXTURE_SOURCE),
    Resource("optic-b-01", "demo-project", OPTIC_RESOURCE_TYPE, "leaf-b01 / Ethernet1/1", "site-b", source_ref=FIXTURE_SOURCE),
)


def _observation(
    observation_id: str,
    resource_id: str,
    observed_at: str,
    rx_dbm: float | None,
    tx_dbm: float | None,
    temperature_c: float | None,
    quality: str = "complete",
) -> Observation:
    return Observation(
        observation_id=observation_id,
        resource_id=resource_id,
        observed_at=_at(observed_at),
        source=FIXTURE_SOURCE,
        values={"rx_dbm": rx_dbm, "tx_dbm": tx_dbm, "temperature_c": temperature_c},
        quality=quality,
    )


FIXTURE_OBSERVATIONS = (
    _observation("obs-a01", "optic-a-01", "2026-07-20T10:00:00Z", -10.2, -2.1, 44.0),
    _observation("obs-a02", "optic-a-02", "2026-07-20T10:00:00Z", -19.1, -2.0, 46.0),
    _observation("obs-a03", "optic-a-03", "2026-07-20T10:00:00Z", -10.5, -9.3, 47.0),
    _observation("obs-a04", "optic-a-04", "2026-07-20T10:00:00Z", -10.1, -2.3, 78.2),
    _observation("obs-a05-before", "optic-a-05", "2026-07-20T09:45:00Z", -19.0, -2.2, 45.0),
    _observation("obs-a05-after", "optic-a-05", "2026-07-20T10:00:00Z", -10.0, -2.2, 45.0),
    _observation("obs-a06", "optic-a-06", "2026-07-20T10:00:00Z", None, None, None, "missing"),
    _observation("obs-a07-first", "optic-a-07", "2026-07-20T09:50:00Z", -19.2, -2.1, 45.0),
    _observation("obs-a07-repeat", "optic-a-07", "2026-07-20T10:00:00Z", -19.3, -2.0, 45.0),
    _observation("obs-b01", "optic-b-01", "2026-07-20T10:00:00Z", -19.5, -2.1, 45.0),
)


def query_optic_health(
    scope: Scope,
    *,
    health_filter: frozenset[str] = frozenset(),
    search: str | None = None,
    focus_resource_id: str | None = None,
) -> OpticHealthQuery:
    """Evaluate only Fixture resources visible in the server-issued Scope."""

    records = tuple(
        _record_for(resource)
        for resource in FIXTURE_RESOURCES
        if _visible(resource, scope)
        and (focus_resource_id is None or resource.resource_id == focus_resource_id)
        and (search is None or search.casefold() in _searchable(resource))
    )
    if health_filter:
        records = tuple(record for record in records if record.assessment.health in health_filter)
    return OpticHealthQuery(
        records=records,
        summary=dict(Counter(record.assessment.health for record in records)),
        source=FIXTURE_SOURCE,
        observed_from=min(item.latest_observation.observed_at for item in records) if records else _at("2026-07-20T10:00:00Z"),
        observed_to=max(item.latest_observation.observed_at for item in records) if records else _at("2026-07-20T10:00:00Z"),
        rule_version=OPTIC_RULE_VERSION,
    )


def _visible(resource: Resource, scope: Scope) -> bool:
    return (
        resource.project_id == scope.project_id
        and (not scope.site_ids or resource.site_id in scope.site_ids)
        and (not scope.resource_types or resource.resource_type in scope.resource_types)
    )


def _searchable(resource: Resource) -> str:
    return f"{resource.resource_id} {resource.display_name}".casefold()


def _record_for(resource: Resource) -> OpticHealthRecord:
    observations = tuple(item for item in FIXTURE_OBSERVATIONS if item.resource_id == resource.resource_id)
    latest = max(observations, key=lambda item: item.observed_at)
    health, reasons = _evaluate(latest)
    if health == "healthy" and any(_evaluate(item)[0] in {"critical", "warning"} for item in observations[:-1]):
        health, reasons = "recovered", ("recovered",)
    assessment = HealthAssessment(
        resource_id=resource.resource_id,
        health=health,
        reason_codes=reasons,
        evaluated_at=latest.observed_at,
        evidence_refs=tuple(item.observation_id for item in observations),
        rule_version=OPTIC_RULE_VERSION,
    )
    return OpticHealthRecord(resource, latest, assessment, _event_for(resource, observations, assessment))


def _evaluate(observation: Observation) -> tuple[str, tuple[str, ...]]:
    if observation.quality != "complete":
        return "unknown", ("data_missing",)
    values = observation.values
    reasons: list[str] = []
    if float(values["rx_dbm"]) < -18:
        reasons.append("rx_power_low")
    if float(values["tx_dbm"]) < -9:
        reasons.append("tx_power_low")
    if float(values["temperature_c"]) > 75:
        reasons.append("temperature_high")
    if not reasons:
        return "healthy", ()
    return ("warning" if reasons == ["temperature_high"] else "critical"), tuple(reasons)


def _event_for(
    resource: Resource, observations: tuple[Observation, ...], assessment: HealthAssessment
) -> Event | None:
    if assessment.health == "healthy":
        return None
    fingerprint = f"optic-health:{resource.resource_id}:{','.join(assessment.reason_codes)}"
    return Event(
        event_id=f"event-{resource.resource_id}",
        fingerprint=fingerprint,
        resource_ids=(resource.resource_id,),
        severity="critical" if assessment.health == "critical" else "warning",
        status="resolved" if assessment.health == "recovered" else "open",
        first_seen_at=observations[0].observed_at,
        last_seen_at=observations[-1].observed_at,
    )
