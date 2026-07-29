import sqlite3
from pathlib import Path

from asklily_api import main
from asklily_api.local_identity import IdentityError, LocalIdentityStore
from asklily_api.runtime import DataSource, RuntimeConfig
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
    assert admin.post("/v1/admin/accounts", json={"username": "local-operator", "password": "safe-operator-password-123", "site_ids": ["site-a"]}).status_code == 201
    assert operator.post("/v1/auth/login", json={"username": "local-operator", "password": "safe-operator-password-123"}).status_code == 200

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
    registered = admin.post("/v1/admin/accounts", json={"username": "disabled-operator", "password": "safe-operator-password-123", "site_ids": ["site-a"]})
    assert registered.status_code == 201
    assert operator.post("/v1/auth/login", json={"username": "disabled-operator", "password": "safe-operator-password-123"}).status_code == 200

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


def test_only_admin_can_create_read_only_operator_accounts_within_own_scope(tmp_path: Path) -> None:
    store = _store(tmp_path)
    admin = _admin_client(store)
    public = TestClient(main.app)
    assert public.post("/v1/auth/register", json={"username": "self-service", "password": "safe-operator-password-123"}).status_code == 404

    created = admin.post("/v1/admin/accounts", json={"username": "site-b-operator", "password": "safe-operator-password-123", "site_ids": ["site-b"]})
    assert created.status_code == 201
    assert created.json()["account"]["role"] == "operator"
    assert created.json()["account"]["scope"]["site_ids"] == ["site-b"]
    assert created.json()["account"]["scope"]["actions"] == ["read"]

    denied = admin.post("/v1/admin/accounts", json={"username": "outside-scope", "password": "safe-operator-password-123", "site_ids": ["site-c"]})
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "scope_site_not_allowed"


def test_only_one_project_admin_can_be_bootstrapped(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.bootstrap_project_admin("first-admin", "safe-admin-password-123")
    try:
        store.bootstrap_project_admin("second-admin", "safe-admin-password-123")
    except IdentityError as exc:
        assert str(exc) == "local_project_admin_already_exists"
    else:
        raise AssertionError("second local project admin must be rejected")


def test_first_run_bootstrap_is_one_time_and_migrates_existing_local_database(tmp_path: Path) -> None:
    database = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TABLE accounts (account_id TEXT PRIMARY KEY, username TEXT NOT NULL UNIQUE, display_name TEXT NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL, project_id TEXT NOT NULL, site_ids TEXT NOT NULL, created_at TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO accounts VALUES ('legacy-operator', 'legacy-operator', 'Legacy', 'not-a-login-hash', 'operator', 'demo-project', 'site-a', '2026-07-28T00:00:00+00:00')"
        )
    main.LOCAL_IDENTITIES = LocalIdentityStore(database)
    main.AUDIT_EVENTS.clear()
    client = TestClient(main.app)
    assert client.get("/v1/admin/bootstrap-status").json()["bootstrap_required"] is True
    created = client.post("/v1/admin/bootstrap", json={"username": "first-admin", "password": "safe-admin-password-123", "display_name": "First Admin"})
    assert created.status_code == 201
    assert created.json()["identity"]["role"] == "project-admin"
    assert client.get("/v1/admin/bootstrap-status").json()["bootstrap_required"] is False
    assert client.post("/v1/admin/bootstrap", json={"username": "second-admin", "password": "safe-admin-password-123"}).status_code == 409
    with sqlite3.connect(database) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(accounts)")}
    assert "status" in columns
    assert database.stat().st_mode & 0o777 == 0o600
    assert database.parent.stat().st_mode & 0o777 == 0o700


def test_monitoring_readiness_admin_api_is_blocked_and_does_not_expose_sensitive_configuration(tmp_path: Path, monkeypatch) -> None:
    admin = _admin_client(_store(tmp_path))
    monkeypatch.setattr(
        main,
        "RUNTIME_CONFIG",
        RuntimeConfig(
            "1.0.0", "production",
            (
                DataSource("zabbix-source", "zabbix", True, True, "unverified", ("optic-health",), frozenset({"site-a"}), "production", "revision-a"),
                DataSource("prometheus-source", "prometheus", True, True, "unverified", ("optic-health",), frozenset({"site-a"}), "production", "revision-b"),
            ),
        ),
    )
    response = admin.get("/v1/admin/system")
    assert response.status_code == 200
    readiness = response.json()["monitoring_source_readiness"]
    assert readiness == [
        {"source_id": "zabbix-source", "source_kind": "zabbix", "status": "blocked", "blockers": ["monitoring_configuration_not_declared", "monitoring_live_execution_not_authorized"], "allowed_operations": ["history.get", "host.get", "item.get"]},
        {"source_id": "prometheus-source", "source_kind": "prometheus", "status": "blocked", "blockers": ["monitoring_configuration_not_declared", "monitoring_governance_not_accepted", "monitoring_live_execution_not_authorized"], "allowed_operations": ["query", "query_range"]},
    ]
    rendered = str(response.json())
    for sensitive_name in ("endpoint", "token", "credential", "promql", "label", "raw_observation"):
        assert sensitive_name not in rendered
