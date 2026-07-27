from pathlib import Path

from asklily_api import main
from asklily_api.local_identity import LocalIdentityStore
from fastapi.testclient import TestClient


def _client(tmp_path: Path) -> TestClient:
    main.LOCAL_IDENTITIES = LocalIdentityStore(tmp_path / "accounts.sqlite3")
    main.AUDIT_EVENTS.clear()
    return TestClient(main.app)


def _register(client: TestClient, username: str, password: str = "safe-password-123") -> None:
    response = client.post("/v1/auth/register", json={"username": username, "password": password})
    assert response.status_code == 201


def test_local_account_chat_history_is_account_scoped_and_deletable(tmp_path: Path) -> None:
    first = _client(tmp_path)
    _register(first, "operator-a")
    chat = first.post("/v1/chat", json={"question": "查看当前光模块健康异常"})
    assert chat.status_code == 200
    conversation_id = chat.json()["conversation_id"]
    history = first.get("/v1/conversations")
    assert history.json()["conversations"][0]["conversation_id"] == conversation_id
    reopened = first.get(f"/v1/conversations/{conversation_id}")
    assert [message["author"] for message in reopened.json()["conversation"]["messages"]] == ["user", "assistant"]

    second = TestClient(main.app)
    _register(second, "operator-b")
    assert second.get(f"/v1/conversations/{conversation_id}").status_code == 404
    assert second.delete(f"/v1/conversations/{conversation_id}").status_code == 404

    assert first.delete(f"/v1/conversations/{conversation_id}").status_code == 200
    assert first.get(f"/v1/conversations/{conversation_id}").status_code == 404


def test_invalid_password_session_and_account_deletion_fail_closed(tmp_path: Path) -> None:
    client = _client(tmp_path)
    _register(client, "operator-c", "safe-password-789")
    client.post("/v1/auth/logout")
    assert client.post("/v1/auth/login", json={"username": "operator-c", "password": "wrong-password-789"}).status_code == 401
    assert client.get("/v1/conversations").status_code == 401
    assert client.post("/v1/auth/login", json={"username": "operator-c", "password": "safe-password-789"}).status_code == 200
    assert client.request("DELETE", "/v1/auth/account", json={"password": "wrong-password-789"}).status_code == 401
    assert client.request("DELETE", "/v1/auth/account", json={"password": "safe-password-789"}).status_code == 200
    assert client.post("/v1/auth/login", json={"username": "operator-c", "password": "safe-password-789"}).status_code == 401
