import pytest
from asklily_monitoring import (
    MonitoringSourcePolicyError,
    assess_monitoring_source_preflight,
)


def test_preflight_is_deterministic_and_has_no_real_source_dependency() -> None:
    result = assess_monitoring_source_preflight(
        "prometheus", source_declared=True, configuration_declared=False,
        approved_scope_declared=True, governance_accepted=False, live_execution_authorized=False,
    )
    assert result.status == "blocked"
    assert result.blockers == (
        "monitoring_configuration_not_declared", "monitoring_governance_not_accepted",
        "monitoring_live_execution_not_authorized",
    )
    assert result.allowed_operations == ("query", "query_range")


def test_preflight_rejects_non_read_only_operations_and_unknown_sources() -> None:
    with pytest.raises(MonitoringSourcePolicyError, match="not_read_only"):
        assess_monitoring_source_preflight(
            "prometheus", source_declared=True, configuration_declared=True,
            approved_scope_declared=True, governance_accepted=True, live_execution_authorized=True,
            requested_operation="delete_series",
        )
    with pytest.raises(MonitoringSourcePolicyError, match="kind_unsupported"):
        assess_monitoring_source_preflight(
            "unknown", source_declared=True, configuration_declared=True,
            approved_scope_declared=True, governance_accepted=True, live_execution_authorized=True,
        )
