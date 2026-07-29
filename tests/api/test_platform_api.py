from asklily_api import main
from asklily_api.local_identity import LocalIdentityStore
from asklily_api.main import AUDIT_EVENTS, app
from asklily_api.runtime import DataSource, RuntimeConfig, RuntimeConfigError, load_runtime_config
from fastapi.testclient import TestClient

client = TestClient(app)


def setup_function() -> None:
    AUDIT_EVENTS.clear()


def test_chat_cannot_expand_server_scope_and_audits_denial() -> None:
    response = client.post(
        "/v1/chat",
        headers={"X-AskLily-Role": "operator", "X-Request-ID": "req-expand"},
        json={"question": "status", "requested_scope": {"project_id": "demo-project", "site_ids": ["site-b"]}},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "scope_site_not_allowed"
    audit = client.get("/v1/audit", headers={"X-AskLily-Role": "auditor"}).json()["events"]
    assert any(event["request_id"] == "req-expand" and event["outcome"] == "denied" for event in audit)


def test_unknown_tool_and_view_are_rejected() -> None:
    assert client.post("/v1/tools/unknown/authorize").status_code == 404
    response = client.post(
        "/v1/views/context",
        json={"view_id": "unknown", "scope": {"project_id": "demo-project"}},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "view_not_registered"


def test_chat_uses_authorized_fixture_tool_and_returns_legal_view_context() -> None:
    response = client.post(
        "/v1/chat",
        headers={"X-Request-ID": "req-optic-chat"},
        json={"question": "查看光模块健康异常"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["sources"] == ["fixture://optic-health/l0-l1-v1"]
    assert body["view_context"]["view_id"] == "optic_health"
    assert body["view_context"]["scope"]["site_ids"] == ["site-a"]
    assert body["optic_health"]["summary"] == {"critical": 3, "unknown": 1, "warning": 1}
    assert body["limitations"] == ["fixture_l0_l1_only", "no_real_connector", "no_write_operation"]
    audit = client.get("/v1/audit", headers={"X-AskLily-Role": "auditor"}).json()["events"]
    assert any(event["tool_id"] == "optic_health.query" and event["outcome"] == "allowed" for event in audit)


def test_optic_query_and_suggestions_never_leak_site_b_to_operator() -> None:
    operator = client.get("/v1/optic-health", headers={"X-AskLily-Role": "operator"})
    assert operator.status_code == 200
    records = operator.json()["query"]["records"]
    assert len(records) == 7
    assert "optic-b-01" not in {record["resource"]["resource_id"] for record in records}

    operator_suggestions = client.get(
        "/v1/optic-health/suggestions", params={"query": "leaf-b01"}, headers={"X-AskLily-Role": "operator"}
    )
    assert operator_suggestions.json()["suggestions"] == []

    admin_suggestions = client.get(
        "/v1/optic-health/suggestions", params={"query": "leaf-b01"}, headers={"X-AskLily-Role": "project-admin"}
    )
    assert admin_suggestions.json()["suggestions"] == [
        {"resource_id": "optic-b-01", "display_name": "leaf-b01 / Ethernet1/1"}
    ]


def test_optic_view_context_rejects_scope_expansion() -> None:
    response = client.post(
        "/v1/views/context",
        headers={"X-AskLily-Role": "operator"},
        json={
            "view_id": "optic_health",
            "scope": {"project_id": "demo-project", "site_ids": ["site-b"]},
            "filters": {"health": ["critical"], "time_range": {"from": "fixture"}},
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "scope_site_not_allowed"


def test_data_source_registry_requires_explicit_valid_fixture_configuration(tmp_path) -> None:
    registry = tmp_path / "sources.json"
    registry.write_text(
        """{
          "schema_version": "1.0.0",
          "deployment": {"declared_environment": "fixture"},
          "sources": [{
            "source_id": "fixture-test", "kind": "fixture", "enabled": true,
            "read_only": true, "data_level": "L0_L1", "capability_ids": ["optic-health"],
            "visible_site_ids": ["site-a"], "config_revision": "test-v1"
          }]
        }"""
    )
    config = load_runtime_config({"ASKLILY_SOURCE_REGISTRY": str(registry)})
    assert config.deployment_environment == "fixture"
    assert config.source_for_capability("optic-health").public_state()["connection_state"] == "ready"  # type: ignore[union-attr]

    registry.write_text('{"schema_version": "1.0.0", "deployment": {"declared_environment": "production"}, "sources": []}')
    try:
        load_runtime_config({"ASKLILY_SOURCE_REGISTRY": str(registry)})
    except RuntimeConfigError as exc:
        assert str(exc) == "data_source_registry_invalid"
    else:
        raise AssertionError("empty production source registry must fail closed")


def test_session_reports_declared_data_source_context_without_a_frontend_switch() -> None:
    response = client.get("/v1/session", headers={"X-AskLily-Role": "operator"})
    assert response.status_code == 200
    runtime = response.json()["runtime"]
    assert runtime["declared_environment"] == "fixture"
    assert runtime["data_sources"] == [{
        "source_id": "fixture-optic-health-l0-l1", "kind": "fixture", "enabled": True,
        "read_only": True, "data_level": "L0_L1", "declared_environment": "fixture",
        "visible_site_ids": ["site-a"], "connection_state": "ready",
        "reason_code": None, "last_checked_at": None, "config_revision": "fixture-v1",
    }]


def test_missing_or_unverified_real_source_never_falls_back_to_fixture(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(main, "LOCAL_IDENTITIES", LocalIdentityStore(tmp_path / "runtime.sqlite3"))
    monkeypatch.setattr(main, "RUNTIME_CONFIG", RuntimeConfig("1.0.0", "production", ()))
    missing = TestClient(main.app).get("/v1/optic-health")
    assert missing.status_code == 503
    assert missing.json()["detail"]["code"] == "data_source_not_configured"

    source = DataSource(
        "zabbix-production", "zabbix", True, True, "unverified", ("optic-health",),
        frozenset({"site-a"}), "production", "customer-v1",
    )
    monkeypatch.setattr(main, "RUNTIME_CONFIG", RuntimeConfig("1.0.0", "production", (source,)))
    unavailable = TestClient(main.app).get("/v1/optic-health")
    assert unavailable.status_code == 503
    assert unavailable.json()["detail"]["code"] == "data_source_unavailable"


def test_source_visible_sites_constrain_queries_view_context_and_session_state(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(main, "LOCAL_IDENTITIES", LocalIdentityStore(tmp_path / "runtime.sqlite3"))
    source = DataSource(
        "fixture-site-a", "fixture", True, True, "L0_L1", ("optic-health",),
        frozenset({"site-a"}), "fixture", "fixture-site-a-v1",
    )
    monkeypatch.setattr(main, "RUNTIME_CONFIG", RuntimeConfig("1.0.0", "fixture", (source,)))
    client = TestClient(main.app)

    session = client.get("/v1/session", headers={"X-AskLily-Role": "operator"})
    assert session.status_code == 200
    assert session.json()["runtime"]["data_sources"][0]["visible_site_ids"] == ["site-a"]

    admin_records = client.get("/v1/optic-health", headers={"X-AskLily-Role": "project-admin"})
    assert admin_records.status_code == 200
    assert {item["resource"]["site_id"] for item in admin_records.json()["query"]["records"]} == {"site-a"}

    unavailable_context = client.post(
        "/v1/views/context",
        headers={"X-AskLily-Role": "project-admin"},
        json={"view_id": "optic_health", "scope": {"project_id": "demo-project", "site_ids": ["site-b"]}},
    )
    assert unavailable_context.status_code == 403
    assert unavailable_context.json()["detail"]["code"] == "data_source_scope_not_allowed"


def test_local_storage_failure_is_not_reported_as_invalid_credentials(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(main, "LOCAL_IDENTITIES", LocalIdentityStore(tmp_path))
    client = TestClient(main.app)
    response = client.post("/v1/auth/login", json={"username": "any-user", "password": "safe-password-123"})
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "local_storage_unavailable"


def test_corrupt_sqlite_fails_closed_and_source_status_persists_only_control_plane_fields(tmp_path, monkeypatch) -> None:
    database = tmp_path / "corrupt.sqlite3"
    database.write_text("not a sqlite database")
    monkeypatch.setattr(main, "LOCAL_IDENTITIES", LocalIdentityStore(database))
    failed = TestClient(main.app).get("/v1/session")
    assert failed.status_code == 503
    assert failed.json()["detail"]["code"] == "local_storage_unavailable"

    store = LocalIdentityStore(tmp_path / "state.sqlite3")
    store.record_data_source_state({
        "source_id": "fixture-test", "kind": "fixture", "declared_environment": "fixture",
        "data_level": "L0_L1", "connection_state": "ready", "config_revision": "test-v1",
        "reason_code": None, "visible_site_ids": ["site-a"], "raw_observation": "must-not-persist",
    })
    persisted = store.list_data_source_status()
    assert persisted == [{
        "source_id": "fixture-test", "kind": "fixture", "declared_environment": "fixture",
        "data_level": "L0_L1", "connection_state": "ready", "reason_code": None,
        "config_revision": "test-v1", "observed_at": persisted[0]["observed_at"],
    }]
