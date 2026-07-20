from asklily_contracts import Scope
from asklily_domain import query_optic_health

SITE_A_SCOPE = Scope("demo-project", frozenset({"site-a"}), actions=frozenset({"read"}))


def _record(scope: Scope, resource_id: str):
    result = query_optic_health(scope, focus_resource_id=resource_id)
    assert len(result.records) == 1
    return result.records[0]


def test_fixture_rules_cover_normal_fault_recovery_and_missing_data() -> None:
    cases = {
        "optic-a-01": ("healthy", ()),
        "optic-a-02": ("critical", ("rx_power_low",)),
        "optic-a-03": ("critical", ("tx_power_low",)),
        "optic-a-04": ("warning", ("temperature_high",)),
        "optic-a-05": ("recovered", ("recovered",)),
        "optic-a-06": ("unknown", ("data_missing",)),
    }
    for resource_id, (health, reasons) in cases.items():
        record = _record(SITE_A_SCOPE, resource_id)
        assert record.assessment.health == health
        assert record.assessment.reason_codes == reasons
        assert record.assessment.rule_version == "demo-1.0.0"
        assert record.latest_observation.source.startswith("fixture://")


def test_duplicate_alerts_produce_one_stable_event() -> None:
    record = _record(SITE_A_SCOPE, "optic-a-07")
    assert record.assessment.reason_codes == ("rx_power_low",)
    assert record.event is not None
    assert record.event.fingerprint == "optic-health:optic-a-07:rx_power_low"
    assert record.event.first_seen_at.isoformat() == "2026-07-20T09:50:00+00:00"
    assert record.event.last_seen_at.isoformat() == "2026-07-20T10:00:00+00:00"


def test_query_filters_site_resource_type_health_and_search_without_scope_leakage() -> None:
    all_site_a = query_optic_health(SITE_A_SCOPE)
    assert len(all_site_a.records) == 7
    assert "optic-b-01" not in {item.resource.resource_id for item in all_site_a.records}

    critical = query_optic_health(SITE_A_SCOPE, health_filter=frozenset({"critical"}))
    assert {item.resource.resource_id for item in critical.records} == {
        "optic-a-02",
        "optic-a-03",
        "optic-a-07",
    }

    assert not query_optic_health(SITE_A_SCOPE, focus_resource_id="optic-b-01").records
    assert not query_optic_health(SITE_A_SCOPE, search="leaf-b01").records

    wrong_type_scope = Scope(
        "demo-project",
        frozenset({"site-a"}),
        resource_types=frozenset({"switch"}),
        actions=frozenset({"read"}),
    )
    assert not query_optic_health(wrong_type_scope).records
