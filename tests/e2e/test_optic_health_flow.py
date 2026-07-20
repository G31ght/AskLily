"""API-level end-to-end regression for the P2 Chat-to-Workspace control path."""

from asklily_api.main import AUDIT_EVENTS, app
from fastapi.testclient import TestClient

client = TestClient(app)


def setup_function() -> None:
    AUDIT_EVENTS.clear()


def test_chat_to_view_context_to_workspace_query_keeps_fixture_scope() -> None:
    chat = client.post(
        "/v1/chat",
        headers={"X-AskLily-Role": "operator", "X-Request-ID": "e2e-optic"},
        json={"question": "查看光模块健康异常"},
    )
    assert chat.status_code == 200
    result = chat.json()
    context = result["view_context"]
    assert context["view_id"] == "optic_health"
    assert context["scope"]["site_ids"] == ["site-a"]
    assert result["sources"] == ["fixture://optic-health/l0-l1-v1"]

    validated = client.post(
        "/v1/views/context",
        headers={"X-AskLily-Role": "operator"},
        json={
            "view_id": context["view_id"],
            "scope": context["scope"],
            "filters": context["filters"],
            "focus_resource_id": context["focus_resource_id"],
        },
    )
    assert validated.status_code == 200

    workspace = client.get("/v1/optic-health?health=critical", headers={"X-AskLily-Role": "operator"})
    records = workspace.json()["query"]["records"]
    assert {record["resource"]["site_id"] for record in records} == {"site-a"}
    assert {record["assessment"]["health"] for record in records} == {"critical"}
