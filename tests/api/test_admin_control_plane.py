from pathlib import Path

from asklily_api import main
from asklily_api.local_identity import IdentityError, LocalIdentityStore
from fastapi.testclient import TestClient


def _store(tmp_path: Path) -> LocalIdentityStore:
    store = LocalIdentityStore(tmp_path / "admin.sqlite3")
    main.LOCAL_IDENTITIES = store
    main.AUDIT_EVENTS.clear()
    return store


def _admin_client(store: LocalIdentityStore) -> TestClient:
    store.bootstrap_project_admin("local-admin", "safe-admin-password-123", "Local Admin")
    client = TestClient(main.app)
    response = client.post("/v1/auth/login", json={"username": "local-admin", "password": "safe-admin-password-123"})
    assert response.status_code == 200
    return client


def test_admin_can_stop_and_restore_only_business_capability(tmp_path: Path) -> None:
    store = _store(tmp_path)
    admin = _admin_client(store)
    operator = TestClient(main.app)
    assert operator.post("/v1/auth/register", json={"username": "local-operator", "password": "safe-operator-password-123"}).status_code == 201

    listed = admin.get("/v1/admin/capabilities")
    optic = next(item for item in listed.json()["capabilities"] if item["capability_id"] == "optic-health")
    assert optic["enabled"] is True and optic["manageable"] is True
    assert admin.patch("/v1/admin/capabilities/platform-foundation/state", json={"enabled": False}).status_code == 403

    assert admin.patch("/v1/admin/capabilities/optic-health/state", json={"enabled": False}).status_code == 200
    denied = operator.post("/v1/chat", json={"question": "查看当前光模块健康异常"})
    assert denied.status_code == 409
    assert denied.json()["detail"]["code"] == "capability_disabled"
    assert admin.patch("/v1/admin/capabilities/optic-health/state", json={"enabled": True}).status_code == 200
    assert operator.post("/v1/chat", json={"question": "查看当前光模块健康异常"}).status_code == 200


def test_admin_account_controls_and_audit_are_persistent_and_minimal(tmp_path: Path) -> None:
    store = _store(tmp_path)
    admin = _admin_client(store)
    operator = TestClient(main.app)
    registered = operator.post("/v1/auth/register", json={"username": "disabled-operator", "password": "safe-operator-password-123"})
    assert registered.status_code == 201

    assert operator.get("/v1/admin/overview").status_code == 403
    accounts = admin.get("/v1/admin/accounts").json()["accounts"]
    target = next(item for item in accounts if item["username"] == "disabled-operator")
    assert admin.patch(f"/v1/admin/accounts/{target['account_id']}/state", json={"status": "disabled"}).status_code == 200
    assert operator.get("/v1/conversations").status_code == 401

    # A replacement store models an API restart against the same local database.
    main.LOCAL_IDENTITIES = LocalIdentityStore(tmp_path / "admin.sqlite3")
    events = admin.get("/v1/admin/audit").json()["events"]
    assert events
    assert {"actor_id", "action", "outcome", "request_id", "scope_project_id"}.issubset(events[0])
    assert "body" not in events[0] and "password" not in events[0]


def test_only_one_project_admin_can_be_bootstrapped(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.bootstrap_project_admin("first-admin", "safe-admin-password-123")
    try:
        store.bootstrap_project_admin("second-admin", "safe-admin-password-123")
    except IdentityError as exc:
        assert str(exc) == "local_project_admin_already_exists"
    else:
        raise AssertionError("second local project admin must be rejected")
