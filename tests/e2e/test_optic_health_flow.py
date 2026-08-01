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
    assert result["presentation"] == {
        "mode": "work",
        "modules": [{"module_id": "optic-health-overview", "view_id": "optic_health"}],
    }

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


def test_resource_chat_to_registered_workspace_context_to_detail_keeps_scope() -> None:
    chat = client.post(
        "/v1/chat",
        headers={"X-AskLily-Role": "operator", "X-Request-ID": "e2e-resource"},
        json={"question": "打开 optic-a-02"},
    )
    assert chat.status_code == 200
    result = chat.json()
    context = result["view_context"]
    assert result["response_kind"] == "resource_detail"
    assert context["view_id"] == "resource_detail"
    assert context["focus_resource_id"] == "optic-a-02"
    assert context["scope"]["site_ids"] == ["site-a"]
    assert result["presentation"] == {
        "mode": "work",
        "modules": [{"module_id": "resource-detail-overview", "view_id": "resource_detail"}],
    }

    validated = client.post(
        "/v1/views/context",
        headers={"X-AskLily-Role": "operator"},
        json={
            "view_id": context["view_id"],
            "version": context["version"],
            "scope": context["scope"],
            "filters": context["filters"],
            "focus_resource_id": context["focus_resource_id"],
        },
    )
    assert validated.status_code == 200

    workspace = client.get("/v1/resources/optic-a-02", headers={"X-AskLily-Role": "operator"})
    assert workspace.status_code == 200
    assert workspace.json()["detail"]["resource"]["health"]["health"] == "critical"
    assert "observation" not in str(workspace.json())
