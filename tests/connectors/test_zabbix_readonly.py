from __future__ import annotations

from collections.abc import Mapping

import pytest
from asklily_zabbix import (
    ConnectorConfigurationError,
    ConnectorPolicyError,
    OpticFieldMapping,
    ZabbixOpticScopeBinding,
    ZabbixReadOnlyClient,
    ZabbixReadOnlyConfig,
    assess_optic_mapping,
    normalize_optic_readonly_results,
)


class RecordingTransport:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def post(
        self, endpoint: str, headers: Mapping[str, str], body: Mapping[str, object], timeout_seconds: float
    ) -> Mapping[str, object]:
        self.calls.append({"endpoint": endpoint, "headers": dict(headers), "body": dict(body), "timeout": timeout_seconds})
        method = body["method"]
        if method == "host.get":
            return {"result": [{"hostid": "101", "host": "redacted-host"}]}
        if method == "item.get":
            return {"result": [{"itemid": "201", "hostid": "101", "key_": "optic.rx.dbm"}]}
        if method == "history.get":
            return {"result": [{"itemid": body["params"]["itemids"][0], "clock": "1", "value": "-10"}]}
        return {"error": {"code": -32601}}


def _client(transport: RecordingTransport | None = None) -> tuple[ZabbixReadOnlyClient, RecordingTransport]:
    recorder = transport or RecordingTransport()
    config = ZabbixReadOnlyConfig("https://zabbix.example.invalid/api_jsonrpc.php", "local-token")
    return ZabbixReadOnlyClient(config, recorder), recorder


def test_missing_or_unsafe_local_configuration_fails_closed() -> None:
    with pytest.raises(ConnectorConfigurationError, match="configuration_required"):
        ZabbixReadOnlyConfig.from_environment({})
    with pytest.raises(ConnectorConfigurationError, match="https_endpoint_required"):
        ZabbixReadOnlyConfig.from_environment(
            {"ASKLILY_ZABBIX_URL": "http://zabbix.invalid/api_jsonrpc.php", "ASKLILY_ZABBIX_API_TOKEN": "x"}
        )


def test_only_allowlisted_read_methods_and_chunked_history_are_sent() -> None:
    client, recorder = _client()
    assert client.list_hosts(["10"])[0]["hostid"] == "101"
    assert client.list_items(["101"])[0]["itemid"] == "201"
    history = client.read_history(["201", "202"], time_from=1, time_till=2, page_size=1)
    assert [entry["itemid"] for entry in history] == ["201", "202"]
    assert [call["body"]["method"] for call in recorder.calls] == [
        "host.get",
        "item.get",
        "history.get",
        "history.get",
    ]
    assert all(call["headers"]["Authorization"] == "Bearer local-token" for call in recorder.calls)
    with pytest.raises(ConnectorPolicyError, match="method_not_read_only"):
        client._call("host.create", {})


def test_mapping_quality_reports_missing_duplicate_and_unusable_without_raw_values() -> None:
    mapping = OpticFieldMapping("optic.rx.dbm", "optic.tx.dbm", "optic.temperature.c")
    report = assess_optic_mapping(
        [{"hostid": "101", "name": "private-host-a"}, {"hostid": "102", "name": "private-host-b"}],
        [
            {"itemid": "1", "hostid": "101", "key_": "optic.rx.dbm"},
            {"itemid": "2", "hostid": "101", "key_": "optic.tx.dbm"},
            {"itemid": "3", "hostid": "101", "key_": "optic.temperature.c"},
            {"itemid": "4", "hostid": "102", "key_": "optic.rx.dbm"},
            {"itemid": "5", "hostid": "102", "key_": "optic.rx.dbm"},
            {"itemid": "6", "hostid": "999", "key_": "optic.tx.dbm"},
        ],
        mapping,
    )
    assert report.inspected_hosts == 2
    assert report.complete_hosts == 1
    assert report.missing_keys_by_host == {"102": ("optic.temperature.c", "optic.tx.dbm")}
    assert report.duplicate_keys_by_host == {"102": ("optic.rx.dbm",)}
    assert report.unusable_items == ("6",)
    assert report.quality == "needs_mapping_review"
    assert "private-host" not in repr(report)


def test_normalization_preserves_fact_quality_time_and_explicit_scope_binding() -> None:
    mapping = OpticFieldMapping("optic.rx.dbm", "optic.tx.dbm", "optic.temperature.c")
    result = normalize_optic_readonly_results(
        [{"hostid": "101", "name": "mock-leaf-a01"}],
        [
            {"itemid": "1", "hostid": "101", "key_": "optic.rx.dbm"},
            {"itemid": "2", "hostid": "101", "key_": "optic.tx.dbm"},
            {"itemid": "3", "hostid": "101", "key_": "optic.temperature.c"},
        ],
        [
            {"itemid": "1", "clock": "1720000000", "value": "-10.2"},
            {"itemid": "2", "clock": "1720000001", "value": "-2.1"},
            {"itemid": "3", "clock": "1720000002", "value": "45.0"},
        ],
        mapping,
        ZabbixOpticScopeBinding("demo-project", "site-a"),
    )
    assert result.resources[0].project_id == "demo-project"
    assert result.resources[0].site_id == "site-a"
    assert result.observations[0].source == "zabbix://live-readonly"
    assert result.observations[0].quality == "complete"
    assert result.observations[0].values == {"rx_dbm": -10.2, "tx_dbm": -2.1, "temperature_c": 45.0}


def test_normalization_does_not_fabricate_missing_or_invalid_values() -> None:
    mapping = OpticFieldMapping("optic.rx.dbm", "optic.tx.dbm", "optic.temperature.c")
    result = normalize_optic_readonly_results(
        [{"hostid": "101"}],
        [{"itemid": "1", "hostid": "101", "key_": "optic.rx.dbm"}],
        [{"itemid": "1", "clock": "1720000000", "value": "not-a-number"}],
        mapping,
        ZabbixOpticScopeBinding("demo-project", "site-a"),
    )
    assert result.observations[0].quality == "invalid"
    assert result.observations[0].values == {
        "rx_dbm": None,
        "tx_dbm": None,
        "temperature_c": None,
    }
