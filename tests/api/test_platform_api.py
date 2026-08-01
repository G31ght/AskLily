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


def test_registered_views_fail_closed_for_unregistered_versions_and_filters() -> None:
    wrong_version = client.post(
        "/v1/views/context",
        json={"view_id": "optic_health", "version": "2.0.0", "scope": {"project_id": "demo-project"}},
    )
    assert wrong_version.status_code == 403
    assert wrong_version.json()["detail"]["code"] == "view_version_not_registered"
    wrong_filter = client.post(
        "/v1/views/context",
        json={"view_id": "optic_health", "scope": {"project_id": "demo-project"}, "filters": {"source": "fixture"}},
    )
    assert wrong_filter.status_code == 403
    assert wrong_filter.json()["detail"]["code"] == "view_filter_not_allowed"


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


def test_resource_directory_is_server_paginated_scope_safe_and_references_health_only() -> None:
    response = client.get(
        "/v1/resources",
        params=[
            ("site_id", "site-a"),
            ("resource_type", "optic_module"),
            ("health", "critical"),
            ("health", "warning"),
            ("health", "unknown"),
        ],
        headers={"X-AskLily-Role": "operator"},
    )
    assert response.status_code == 200
    query = response.json()["query"]
    assert query["page"] == 1
    assert query["page_size"] == 20
    assert query["total"] == 5
    assert query["source"] == "fixture://resource-explorer/l0-l1-v1"
    assert {item["resource_id"] for item in query["items"]} == {
        "optic-a-02", "optic-a-03", "optic-a-04", "optic-a-06", "optic-a-07"
    }
    assert {item["health"]["health"] for item in query["items"]} == {"critical", "warning", "unknown"}
    rendered = str(query)
    for forbidden in ("observation", "event", "rx_dbm", "tx_dbm", "temperature_c", "evidence_refs"):
        assert forbidden not in rendered


def test_resource_detail_and_suggestions_have_no_scope_enumeration_side_channel() -> None:
    hidden = client.get("/v1/resources/optic-b-01", headers={"X-AskLily-Role": "operator"})
    unknown = client.get("/v1/resources/not-a-fixture-resource", headers={"X-AskLily-Role": "operator"})
    assert (hidden.status_code, hidden.json()["detail"]["code"]) == (404, "resource_not_available")
    assert (unknown.status_code, unknown.json()["detail"]["code"]) == (404, "resource_not_available")

    suggestions = client.get(
        "/v1/resources/suggestions", params={"query": "leaf-b01"}, headers={"X-AskLily-Role": "operator"}
    )
    assert suggestions.status_code == 200
    assert suggestions.json()["suggestions"] == []

    detail = client.get("/v1/resources/optic-a-02", headers={"X-AskLily-Role": "operator"})
    assert detail.status_code == 200
    value = detail.json()["detail"]
    assert value["resource"]["parent_resource_id"] == "interface-a01-e1-2"
    assert value["resource"]["health"] == {
        "health": "critical", "reason_codes": ["rx_power_low"], "rule_version": "demo-1.0.0"
    }
    assert {item["resource_id"] for item in value["related"]} == {"site-a", "leaf-a01", "interface-a01-e1-2"}


def test_resource_registry_routes_and_registered_views_fail_closed() -> None:
    catalog = client.get("/v1/capability-catalog", headers={"X-AskLily-Role": "operator"})
    entry = next(item for item in catalog.json()["catalog"]["capabilities"] if item["capability_id"] == "resource-explorer")
    assert entry["status"] == {"code": "ready", "reason_code": None}
    assert entry["next_actions"] == [{"kind": "chat", "question": "检索当前可见资源"}]

    wrong_filter = client.post(
        "/v1/views/context",
        json={"view_id": "resource_search", "scope": {"project_id": "demo-project"}, "filters": {"source": "fixture"}},
    )
    assert wrong_filter.status_code == 403
    assert wrong_filter.json()["detail"]["code"] == "view_filter_not_allowed"
    wrong_module = main.REGISTRY.validate_presentation_modules
    try:
        wrong_module("resource_search", ("resource-detail-overview",))
    except Exception as exc:
        assert str(exc) == "workspace_module_not_allowed"
    else:
        raise AssertionError("unregistered resource search module must fail closed")


def test_resource_source_never_falls_back_and_runtime_disable_is_enforced(tmp_path, monkeypatch) -> None:
    store = LocalIdentityStore(tmp_path / "runtime.sqlite3")
    store.set_capability_enabled("resource-explorer", False, "test-admin")
    monkeypatch.setattr(main, "LOCAL_IDENTITIES", store)
    disabled = TestClient(main.app).get("/v1/resources")
    assert disabled.status_code == 409
    assert disabled.json()["detail"]["code"] == "capability_disabled"

    monkeypatch.setattr(main, "LOCAL_IDENTITIES", LocalIdentityStore(tmp_path / "missing.sqlite3"))
    monkeypatch.setattr(main, "RUNTIME_CONFIG", RuntimeConfig("1.0.0", "production", ()))
    missing = TestClient(main.app).get("/v1/resources")
    assert missing.status_code == 503
    assert missing.json()["detail"]["code"] == "data_source_not_configured"


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


def test_capability_catalog_is_registry_derived_scope_projected_and_sensitive_field_free() -> None:
    response = client.get("/v1/capability-catalog", headers={"X-AskLily-Role": "operator", "X-Request-ID": "catalog-operator"})
    assert response.status_code == 200
    body = response.json()
    assert body["request_id"] == "catalog-operator"
    assert body["catalog_version"] == "1.0.0"
    assert body["view_context"]["view_id"] == "capability_catalog"
    assert body["view_context"]["version"] == "1.0.0"
    assert body["presentation"] == {"mode": "work", "modules": [{"module_id": "capability-catalog-overview", "view_id": "capability_catalog"}]}
    entries = body["catalog"]["capabilities"]
    assert body["catalog"]["declared_environment"] == "fixture"
    monitoring = next(item for item in entries if item["capability_id"] == "monitoring-source-readiness")
    assert monitoring["status"] == {"code": "not_configured", "reason_code": "data_source_not_configured"}
    assert monitoring["data_sources"] == []
    optic = next(item for item in entries if item["capability_id"] == "optic-health")
    assert optic["data_sources"][0]["visible_site_ids"] == ["site-a"]
    assert optic["next_actions"] == [{"kind": "chat", "question": "查看当前光模块健康异常"}]
    rendered = str(body)
    for sensitive_name in ("endpoint", "token", "credential", "promql", "label", "raw_observation"):
        assert sensitive_name not in rendered


def test_catalog_omits_scope_blocked_sources_for_operator_but_projects_for_admin(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(main, "LOCAL_IDENTITIES", LocalIdentityStore(tmp_path / "runtime.sqlite3"))
    source = DataSource(
        "fixture-site-b", "fixture", True, True, "L0_L1", ("optic-health",),
        frozenset({"site-b"}), "fixture", "fixture-site-b-v1",
    )
    monkeypatch.setattr(main, "RUNTIME_CONFIG", RuntimeConfig("1.0.0", "fixture", (source,)))
    operator = TestClient(main.app).get("/v1/capabilities", headers={"X-AskLily-Role": "operator"}).json()
    assert "optic-health" not in {item["capability_id"] for item in operator["catalog"]["capabilities"]}
    admin = TestClient(main.app).get("/v1/capabilities", headers={"X-AskLily-Role": "project-admin"}).json()
    optic = next(item for item in admin["catalog"]["capabilities"] if item["capability_id"] == "optic-health")
    assert optic["data_sources"][0]["visible_site_ids"] == ["site-b"]


def test_catalog_reports_unverified_monitoring_source_as_preflight_only(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(main, "LOCAL_IDENTITIES", LocalIdentityStore(tmp_path / "runtime.sqlite3"))
    source = DataSource(
        "zabbix-preflight", "zabbix", True, True, "unverified", ("optic-health",),
        frozenset({"site-a"}), "production", "customer-v1",
    )
    monkeypatch.setattr(main, "RUNTIME_CONFIG", RuntimeConfig("1.0.0", "production", (source,)))
    body = TestClient(main.app).get("/v1/capability-catalog").json()
    monitoring = next(item for item in body["catalog"]["capabilities"] if item["capability_id"] == "monitoring-source-readiness")
    assert monitoring["status"] == {"code": "unavailable", "reason_code": "connector_not_validated"}
    assert monitoring["verification_level"] == "preflight_only"
    assert monitoring["data_sources"][0]["kind"] == "zabbix"


def test_catalog_uses_existing_capability_override_for_disabled_status(tmp_path, monkeypatch) -> None:
    store = LocalIdentityStore(tmp_path / "runtime.sqlite3")
    store.set_capability_enabled("optic-health", False, "test-admin")
    monkeypatch.setattr(main, "LOCAL_IDENTITIES", store)
    body = TestClient(main.app).get("/v1/capability-catalog").json()
    optic = next(item for item in body["catalog"]["capabilities"] if item["capability_id"] == "optic-health")
    assert optic["status"] == {"code": "disabled", "reason_code": "capability_disabled"}


def test_catalog_chat_routes_before_optic_health_and_returns_legal_workspace_context() -> None:
    response = client.post("/v1/chat", json={"question": "光模块健康的数据来自哪里？"})
    assert response.status_code == 200
    body = response.json()
    assert body["response_kind"] == "capability_catalog"
    assert body["view_context"]["view_id"] == "capability_catalog"
    assert body["presentation"]["modules"] == [{"module_id": "capability-catalog-overview", "view_id": "capability_catalog"}]
    assert "optic_health" not in body


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
