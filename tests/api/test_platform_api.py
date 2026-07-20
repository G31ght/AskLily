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


def test_chat_discloses_no_business_data_or_fact() -> None:
    response = client.post("/v1/chat", json={"question": "what is the optic health?"})
    assert response.status_code == 200
    body = response.json()
    assert body["sources"] == []
    assert "尚未注册业务能力" in body["message"]
    assert body["view_context"]["view_id"] == "platform_status"
