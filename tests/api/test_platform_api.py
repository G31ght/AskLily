from asklily_api.main import AUDIT_EVENTS, app
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
