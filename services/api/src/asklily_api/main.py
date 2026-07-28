"""P2 read-only API: deterministic Fixture optic-health vertical slice."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from uuid import uuid4

from asklily_agent import OpticHealthOrchestrator, health_filter_for_question
from asklily_contracts import (
    AuditEvent,
    CapabilityManifest,
    ContractViolation,
    Scope,
    ToolContract,
    ViewContext,
)
from asklily_domain import (
    OPTIC_RULE_VERSION,
    OpticHealthQuery,
    PlatformRegistry,
    query_optic_health,
)
from fastapi import FastAPI, Header, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field
from starlette.middleware.base import RequestResponseEndpoint

from .local_identity import IdentityError, LocalIdentity, LocalIdentityStore, default_database_path
from .runtime import runtime_profile

RUNTIME_PROFILE = runtime_profile()
app = FastAPI(title="AskLily P2 Optic Health API", version="0.2.0")

OPTIC_TOOL_ID = "optic_health.query"
OPTIC_VIEW_ID = "optic_health"
ALLOWED_HEALTH = frozenset({"healthy", "critical", "warning", "recovered", "unknown"})

# A future model Skill may select only from this server-owned presentation
# registry.  It cannot supply arbitrary components, query parameters or data.
PRESENTATION_MODULES: dict[str, dict[str, str]] = {
    "optic-health-overview": {"module_id": "optic-health-overview", "view_id": OPTIC_VIEW_ID},
}
MANAGEABLE_CAPABILITIES = frozenset({"optic-health"})


class ScopeInput(BaseModel):
    project_id: str
    site_ids: set[str] = Field(default_factory=set)
    cluster_ids: set[str] = Field(default_factory=set)
    resource_types: set[str] = Field(default_factory=set)
    actions: set[str] = Field(default_factory=lambda: {"read"})

    def as_contract(self) -> Scope:
        return Scope(
            project_id=self.project_id,
            site_ids=frozenset(self.site_ids),
            cluster_ids=frozenset(self.cluster_ids),
            resource_types=frozenset(self.resource_types),
            actions=frozenset(self.actions),
        )


class ViewContextInput(BaseModel):
    view_id: str
    version: str = "1.0.0"
    scope: ScopeInput
    filters: dict[str, object] = Field(default_factory=dict)
    focus_resource_id: str | None = None


class ChatInput(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    requested_scope: ScopeInput | None = None
    conversation_id: str | None = Field(default=None, max_length=100)


class LocalRegistrationInput(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=12, max_length=128)
    display_name: str | None = Field(default=None, max_length=100)


class LocalLoginInput(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class LocalAdminBootstrapInput(LocalRegistrationInput):
    """First-run local administrator creation; unavailable after bootstrap."""


class AccountDeletionInput(BaseModel):
    password: str = Field(min_length=1, max_length=128)


class AdminCapabilityStateInput(BaseModel):
    enabled: bool


class AdminAccountStateInput(BaseModel):
    status: str = Field(pattern="^(active|disabled)$")


DEVELOPMENT_IDENTITIES: dict[str, tuple[str, Scope]] = {
    "project-admin": (
        "Project Admin",
        Scope("demo-project", frozenset({"site-a", "site-b"}), actions=frozenset({"read"})),
    ),
    "operator": (
        "Operator",
        Scope("demo-project", frozenset({"site-a"}), actions=frozenset({"read"})),
    ),
    "auditor": (
        "Auditor",
        Scope("demo-project", frozenset({"site-a"}), actions=frozenset({"read"})),
    ),
}

REGISTRY = PlatformRegistry()
REGISTRY.register_tool(ToolContract("platform.status", "1.0.0", "platform", "read", "1.0.0", "1.0.0"))
REGISTRY.register_view("platform_status")
REGISTRY.register_capability(
    CapabilityManifest(
        "platform-foundation",
        "1.0.0",
        "platform",
        "verified_skeleton",
        RUNTIME_PROFILE,
        ("platform.status",),
        ("platform_status",),
        ("no_business_capability", "no_real_data", "no_model_provider"),
    )
)
REGISTRY.register_tool(ToolContract(OPTIC_TOOL_ID, "1.0.0", "optic-health", "read", "1.0.0", "1.0.0"))
REGISTRY.register_view(OPTIC_VIEW_ID)
REGISTRY.register_capability(
    CapabilityManifest(
        "optic-health",
        "1.0.0",
        "optic-health",
        "demo_candidate",
        RUNTIME_PROFILE,
        (OPTIC_TOOL_ID,),
        (OPTIC_VIEW_ID,),
        ("fixture_l0_l1_only", "no_real_connector", "no_write_operation"),
    )
)
AUDIT_EVENTS: list[AuditEvent] = []
ORCHESTRATOR = OpticHealthOrchestrator()
LOCAL_IDENTITIES = LocalIdentityStore(default_database_path())
SESSION_COOKIE = "asklily_local_session"


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "missing-request-id")


@app.middleware("http")
async def attach_request_id(request: Request, call_next: RequestResponseEndpoint) -> Response:
    request.state.request_id = request.headers.get("X-Request-ID", str(uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


def _identity(role: str, request_id: str) -> tuple[str, Scope]:
    try:
        return DEVELOPMENT_IDENTITIES[role]
    except KeyError as exc:
        _audit(role, "session.resolve", "denied", request_id, Scope("unknown"), reason="unknown_development_role")
        raise HTTPException(401, detail={"code": "unknown_development_role", "request_id": request_id}) from exc


def _local_identity(request: Request, request_id: str) -> LocalIdentity | None:
    token = request.cookies.get(SESSION_COOKIE)
    if token is None:
        return None
    try:
        return LOCAL_IDENTITIES.resolve_session(token)
    except IdentityError as exc:
        raise HTTPException(401, detail={"code": str(exc), "request_id": request_id}) from exc


def _request_identity(request: Request, role: str, request_id: str) -> tuple[str, Scope, LocalIdentity | None]:
    local = _local_identity(request, request_id)
    if local is not None:
        return local.account_id, local.scope, local
    actor, scope = _identity(role, request_id)
    return actor, scope, None


def _require_local_identity(request: Request, request_id: str) -> LocalIdentity:
    identity = _local_identity(request, request_id)
    if identity is None:
        raise HTTPException(401, detail={"code": "local_session_required", "request_id": request_id})
    return identity


def _require_admin(request: Request, request_id: str) -> LocalIdentity:
    identity = _require_local_identity(request, request_id)
    if identity.role != "project-admin":
        _audit(identity.account_id, "admin.access", "denied", request_id, identity.scope, reason="project_admin_required")
        raise HTTPException(403, detail={"code": "project_admin_required", "request_id": request_id})
    return identity


def _audit(
    actor: str,
    action: str,
    outcome: str,
    request_id: str,
    scope: Scope,
    *,
    tool_id: str | None = None,
    query_id: str | None = None,
    reason: str | None = None,
) -> None:
    event = AuditEvent(
        event_id=str(uuid4()),
        occurred_at=datetime.now(UTC),
        actor_id=actor,
        action=action,
        outcome=outcome,
        request_id=request_id,
        query_id=query_id,
        scope_project_id=scope.project_id,
        tool_id=tool_id,
        reason_code=reason,
    )
    AUDIT_EVENTS.append(event)
    LOCAL_IDENTITIES.append_audit_event(_audit_dict(event))


def _require_capability_enabled(capability_id: str, actor: str, scope: Scope, request_id: str) -> None:
    if not LOCAL_IDENTITIES.capability_enabled(capability_id):
        _audit(actor, "capability.execute", "denied", request_id, scope, reason="capability_disabled")
        raise HTTPException(409, detail={"code": "capability_disabled", "request_id": request_id})


def _narrow(server_scope: Scope, requested: Scope | None, role: str, request_id: str, action: str) -> Scope:
    try:
        return server_scope if requested is None else server_scope.narrowed_to(requested)
    except ContractViolation as exc:
        _audit(role, action, "denied", request_id, server_scope, reason=str(exc))
        raise HTTPException(403, detail={"code": str(exc), "request_id": request_id}) from exc


def _health_filter(values: list[str], request_id: str) -> frozenset[str]:
    invalid = set(values) - ALLOWED_HEALTH
    if invalid:
        raise HTTPException(422, detail={"code": "optic_health_filter_invalid", "request_id": request_id})
    return frozenset(values)


def _run_optic_query(
    scope: Scope,
    role: str,
    request_id: str,
    *,
    health_filter: frozenset[str] = frozenset(),
    search: str | None = None,
    focus_resource_id: str | None = None,
) -> OpticHealthQuery:
    _require_capability_enabled("optic-health", role, scope, request_id)
    try:
        REGISTRY.authorize_tool(OPTIC_TOOL_ID, scope)
    except ContractViolation as exc:
        _audit(role, "optic_health.query", "denied", request_id, scope, tool_id=OPTIC_TOOL_ID, reason=str(exc))
        raise HTTPException(403, detail={"code": str(exc), "request_id": request_id}) from exc
    result = query_optic_health(
        scope,
        health_filter=health_filter,
        search=search.casefold() if search else None,
        focus_resource_id=focus_resource_id,
    )
    _audit(
        role,
        "optic_health.query",
        "allowed",
        request_id,
        scope,
        tool_id=OPTIC_TOOL_ID,
        query_id=f"fixture-query:{request_id}",
    )
    return result


def _default_presentation() -> dict[str, object]:
    """Return the safe no-model default for the natural-language response.

    P5A intentionally leaves this in Chat Mode.  A later trusted Skill adapter
    may return ``mode=work`` and an ordered subset of PRESENTATION_MODULES only
    after its tool calls have completed and the server has validated its result.
    """
    return {"mode": "chat", "modules": []}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "profile": RUNTIME_PROFILE, "data": "fixture_l0_l1", "rule_version": OPTIC_RULE_VERSION}


@app.post("/v1/auth/register", status_code=201)
def register_local_account(payload: LocalRegistrationInput, request: Request, response: Response) -> dict[str, object]:
    request_id = _request_id(request)
    try:
        identity = LOCAL_IDENTITIES.register(payload.username, payload.password, payload.display_name)
        token = LOCAL_IDENTITIES.issue_session(identity.account_id)
    except IdentityError as exc:
        raise HTTPException(400, detail={"code": str(exc), "request_id": request_id}) from exc
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax", secure=request.url.scheme == "https", max_age=int(12 * 60 * 60))
    _audit(identity.account_id, "local_account.register", "allowed", request_id, identity.scope)
    return {"request_id": request_id, "identity": _local_identity_dict(identity)}


@app.post("/v1/auth/login")
def login_local_account(payload: LocalLoginInput, request: Request, response: Response) -> dict[str, object]:
    request_id = _request_id(request)
    try:
        identity = LOCAL_IDENTITIES.authenticate(payload.username, payload.password)
        token = LOCAL_IDENTITIES.issue_session(identity.account_id)
    except IdentityError as exc:
        raise HTTPException(401, detail={"code": str(exc), "request_id": request_id}) from exc
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax", secure=request.url.scheme == "https", max_age=int(12 * 60 * 60))
    _audit(identity.account_id, "local_account.login", "allowed", request_id, identity.scope)
    return {"request_id": request_id, "identity": _local_identity_dict(identity)}


@app.get("/v1/admin/bootstrap-status")
def admin_bootstrap_status(request: Request) -> dict[str, object]:
    """Expose only whether first-run local setup is still required."""
    return {"request_id": _request_id(request), "bootstrap_required": not LOCAL_IDENTITIES.project_admin_exists()}


@app.post("/v1/admin/bootstrap", status_code=201)
def bootstrap_local_project_admin(payload: LocalAdminBootstrapInput, request: Request, response: Response) -> dict[str, object]:
    request_id = _request_id(request)
    if LOCAL_IDENTITIES.project_admin_exists():
        raise HTTPException(409, detail={"code": "local_project_admin_already_exists", "request_id": request_id})
    try:
        identity = LOCAL_IDENTITIES.bootstrap_project_admin(payload.username, payload.password, payload.display_name)
        token = LOCAL_IDENTITIES.issue_session(identity.account_id)
    except IdentityError as exc:
        code = str(exc)
        status = 409 if code == "local_project_admin_already_exists" else 400
        raise HTTPException(status, detail={"code": code, "request_id": request_id}) from exc
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax", secure=request.url.scheme == "https", max_age=int(12 * 60 * 60))
    _audit(identity.account_id, "local_project_admin.bootstrap", "allowed", request_id, identity.scope)
    return {"request_id": request_id, "identity": _local_identity_dict(identity)}


@app.post("/v1/auth/logout")
def logout_local_account(request: Request, response: Response) -> dict[str, object]:
    request_id = _request_id(request)
    identity = _require_local_identity(request, request_id)
    token = request.cookies[SESSION_COOKIE]
    LOCAL_IDENTITIES.revoke_session(token)
    response.delete_cookie(SESSION_COOKIE)
    _audit(identity.account_id, "local_account.logout", "allowed", request_id, identity.scope)
    return {"request_id": request_id, "status": "logged_out"}


@app.delete("/v1/auth/account")
def delete_local_account(payload: AccountDeletionInput, request: Request, response: Response) -> dict[str, object]:
    request_id = _request_id(request)
    identity = _require_local_identity(request, request_id)
    try:
        LOCAL_IDENTITIES.delete_account(identity, payload.password)
    except IdentityError as exc:
        raise HTTPException(401, detail={"code": str(exc), "request_id": request_id}) from exc
    response.delete_cookie(SESSION_COOKIE)
    _audit(identity.account_id, "local_account.delete", "allowed", request_id, identity.scope)
    return {"request_id": request_id, "status": "account_deleted"}


@app.get("/v1/session")
def session(request: Request, x_asklily_role: str = Header(default="operator")) -> dict[str, object]:
    request_id = _request_id(request)
    actor, scope, local = _request_identity(request, x_asklily_role, request_id)
    display_name = local.display_name if local is not None else DEVELOPMENT_IDENTITIES[x_asklily_role][0]
    role = local.role if local is not None else x_asklily_role
    _audit(actor, "session.read", "allowed", request_id, scope)
    return {
        "request_id": request_id,
        "identity": {"role": role, "display_name": display_name, "authenticated": local is not None},
        "scope": _scope_dict(scope),
        "profile": RUNTIME_PROFILE,
    }


@app.get("/v1/capabilities")
def capabilities(request: Request, x_asklily_role: str = Header(default="operator")) -> dict[str, object]:
    request_id = _request_id(request)
    actor, scope, _ = _request_identity(request, x_asklily_role, request_id)
    _audit(actor, "capability_catalog.read", "allowed", request_id, scope)
    return {"request_id": request_id, "capabilities": [_manifest_dict(item) for item in REGISTRY.capabilities.values()]}


@app.post("/v1/tools/{tool_id}/authorize")
def authorize_tool(tool_id: str, request: Request, x_asklily_role: str = Header(default="operator")) -> dict[str, object]:
    request_id = _request_id(request)
    actor, scope, _ = _request_identity(request, x_asklily_role, request_id)
    if tool_id == OPTIC_TOOL_ID:
        _require_capability_enabled("optic-health", actor, scope, request_id)
    try:
        contract = REGISTRY.authorize_tool(tool_id, scope)
    except ContractViolation as exc:
        _audit(actor, "tool.authorize", "denied", request_id, scope, tool_id=tool_id, reason=str(exc))
        raise HTTPException(404, detail={"code": str(exc), "request_id": request_id}) from exc
    _audit(actor, "tool.authorize", "allowed", request_id, scope, tool_id=tool_id)
    return {"request_id": request_id, "tool_id": contract.tool_id, "read_only": True, "executed": False}


@app.get("/v1/optic-health")
def optic_health(
    request: Request,
    health: list[str] = Query(default=[]),
    search: str | None = Query(default=None, max_length=200),
    focus_resource_id: str | None = Query(default=None, max_length=100),
    x_asklily_role: str = Header(default="operator"),
) -> dict[str, object]:
    request_id = _request_id(request)
    actor, scope, _ = _request_identity(request, x_asklily_role, request_id)
    result = _run_optic_query(
        scope,
        actor,
        request_id,
        health_filter=_health_filter(health, request_id),
        search=search,
        focus_resource_id=focus_resource_id,
    )
    return {"request_id": request_id, "query": _optic_query_dict(result)}


@app.get("/v1/optic-health/suggestions")
def optic_health_suggestions(
    request: Request,
    query: str = Query(min_length=1, max_length=100),
    x_asklily_role: str = Header(default="operator"),
) -> dict[str, object]:
    request_id = _request_id(request)
    actor, scope, _ = _request_identity(request, x_asklily_role, request_id)
    result = _run_optic_query(scope, actor, request_id, search=query)
    return {
        "request_id": request_id,
        "suggestions": [
            {"resource_id": item.resource.resource_id, "display_name": item.resource.display_name}
            for item in result.records[:10]
        ],
    }


@app.post("/v1/views/context")
def validate_view_context(
    payload: ViewContextInput, request: Request, x_asklily_role: str = Header(default="operator")
) -> dict[str, object]:
    request_id = _request_id(request)
    actor, server_scope, _ = _request_identity(request, x_asklily_role, request_id)
    if payload.view_id == OPTIC_VIEW_ID:
        _require_capability_enabled("optic-health", actor, server_scope, request_id)
    try:
        context = REGISTRY.validate_view_context(
            ViewContext(payload.view_id, payload.version, payload.scope.as_contract(), payload.filters, payload.focus_resource_id),
            server_scope,
        )
    except ContractViolation as exc:
        _audit(actor, "view.validate", "denied", request_id, server_scope, reason=str(exc))
        raise HTTPException(403, detail={"code": str(exc), "request_id": request_id}) from exc
    _audit(actor, "view.validate", "allowed", request_id, context.scope)
    return {"request_id": request_id, "view_context": _view_dict(context)}


@app.post("/v1/chat")
def chat(payload: ChatInput, request: Request, x_asklily_role: str = Header(default="operator")) -> dict[str, object]:
    request_id = _request_id(request)
    actor, server_scope, local = _request_identity(request, x_asklily_role, request_id)
    scope = _narrow(
        server_scope,
        payload.requested_scope.as_contract() if payload.requested_scope else None,
        actor,
        request_id,
        "chat.read",
    )
    _audit(actor, "chat.read", "allowed", request_id, scope)
    result = _run_optic_query(
        scope,
        actor,
        request_id,
        health_filter=health_filter_for_question(payload.question),
    )
    response = dict(ORCHESTRATOR.respond(payload.question, scope, request_id, result))
    response["presentation"] = _default_presentation()
    if local is not None:
        try:
            conversation_id = LOCAL_IDENTITIES.create_or_append_conversation(
                local,
                payload.conversation_id,
                payload.question,
                str(response["message"]),
                result.source,
                "fixture_l0_l1_only,no_real_connector,no_write_operation",
            )
        except IdentityError as exc:
            raise HTTPException(404, detail={"code": str(exc), "request_id": request_id}) from exc
        response["conversation_id"] = conversation_id
    return response


@app.get("/v1/conversations")
def conversations(request: Request) -> dict[str, object]:
    request_id = _request_id(request)
    identity = _require_local_identity(request, request_id)
    return {"request_id": request_id, "conversations": LOCAL_IDENTITIES.list_conversations(identity)}


@app.get("/v1/conversations/{conversation_id}")
def conversation(conversation_id: str, request: Request) -> dict[str, object]:
    request_id = _request_id(request)
    identity = _require_local_identity(request, request_id)
    try:
        value = LOCAL_IDENTITIES.read_conversation(identity, conversation_id)
    except IdentityError as exc:
        raise HTTPException(404, detail={"code": str(exc), "request_id": request_id}) from exc
    return {"request_id": request_id, "conversation": value}


@app.delete("/v1/conversations/{conversation_id}")
def delete_conversation(conversation_id: str, request: Request) -> dict[str, object]:
    request_id = _request_id(request)
    identity = _require_local_identity(request, request_id)
    try:
        LOCAL_IDENTITIES.delete_conversation(identity, conversation_id)
    except IdentityError as exc:
        raise HTTPException(404, detail={"code": str(exc), "request_id": request_id}) from exc
    _audit(identity.account_id, "conversation.delete", "allowed", request_id, identity.scope)
    return {"request_id": request_id, "status": "conversation_deleted"}


@app.get("/v1/audit")
def audit(request: Request, x_asklily_role: str = Header(default="auditor")) -> dict[str, object]:
    request_id = _request_id(request)
    _, scope = _identity(x_asklily_role, request_id)
    if x_asklily_role not in {"auditor", "project-admin"}:
        _audit(x_asklily_role, "audit.read", "denied", request_id, scope, reason="audit_role_required")
        raise HTTPException(403, detail={"code": "audit_role_required", "request_id": request_id})
    _audit(x_asklily_role, "audit.read", "allowed", request_id, scope)
    return {"request_id": request_id, "events": [_audit_dict(event) for event in AUDIT_EVENTS]}


@app.get("/v1/admin/overview")
def admin_overview(request: Request) -> dict[str, object]:
    request_id = _request_id(request)
    identity = _require_admin(request, request_id)
    capabilities = [_manifest_dict(item) for item in REGISTRY.capabilities.values()]
    accounts = LOCAL_IDENTITIES.list_accounts()
    _audit(identity.account_id, "admin.overview.read", "allowed", request_id, identity.scope)
    return {
        "request_id": request_id,
        "metrics": {
            "capability_total": len(capabilities),
            "capability_enabled": sum(1 for item in capabilities if item["enabled"]),
            "capability_disabled": sum(1 for item in capabilities if not item["enabled"]),
            "account_total": len(accounts),
            "account_active": sum(1 for item in accounts if item["status"] == "active"),
            "audit_event_total": LOCAL_IDENTITIES.audit_event_count(),
        },
    }


@app.get("/v1/admin/capabilities")
def admin_capabilities(request: Request) -> dict[str, object]:
    request_id = _request_id(request)
    identity = _require_admin(request, request_id)
    _audit(identity.account_id, "admin.capability.read", "allowed", request_id, identity.scope)
    return {"request_id": request_id, "capabilities": [_manifest_dict(item) for item in REGISTRY.capabilities.values()]}


@app.patch("/v1/admin/capabilities/{capability_id}/state")
def set_admin_capability_state(capability_id: str, payload: AdminCapabilityStateInput, request: Request) -> dict[str, object]:
    request_id = _request_id(request)
    identity = _require_admin(request, request_id)
    manifest = REGISTRY.capabilities.get(capability_id)
    if manifest is None:
        raise HTTPException(404, detail={"code": "capability_not_found", "request_id": request_id})
    if capability_id not in MANAGEABLE_CAPABILITIES:
        _audit(identity.account_id, "admin.capability.state", "denied", request_id, identity.scope, reason="capability_state_protected")
        raise HTTPException(403, detail={"code": "capability_state_protected", "request_id": request_id})
    LOCAL_IDENTITIES.set_capability_enabled(capability_id, payload.enabled, identity.account_id)
    _audit(identity.account_id, "admin.capability.state", "allowed", request_id, identity.scope, reason="enabled" if payload.enabled else "disabled")
    return {"request_id": request_id, "capability": _manifest_dict(manifest)}


@app.get("/v1/admin/accounts")
def admin_accounts(request: Request) -> dict[str, object]:
    request_id = _request_id(request)
    identity = _require_admin(request, request_id)
    _audit(identity.account_id, "admin.account.read", "allowed", request_id, identity.scope)
    return {"request_id": request_id, "accounts": LOCAL_IDENTITIES.list_accounts()}


@app.patch("/v1/admin/accounts/{account_id}/state")
def set_admin_account_state(account_id: str, payload: AdminAccountStateInput, request: Request) -> dict[str, object]:
    request_id = _request_id(request)
    identity = _require_admin(request, request_id)
    try:
        account = LOCAL_IDENTITIES.set_account_status(account_id, payload.status)
    except IdentityError as exc:
        code = str(exc)
        status = 403 if code == "local_project_admin_state_protected" else 404
        _audit(identity.account_id, "admin.account.state", "denied", request_id, identity.scope, reason=code)
        raise HTTPException(status, detail={"code": code, "request_id": request_id}) from exc
    _audit(identity.account_id, "admin.account.state", "allowed", request_id, identity.scope, reason=payload.status)
    return {"request_id": request_id, "account": account}


@app.delete("/v1/admin/accounts/{account_id}/sessions")
def revoke_admin_account_sessions(account_id: str, request: Request) -> dict[str, object]:
    request_id = _request_id(request)
    identity = _require_admin(request, request_id)
    try:
        LOCAL_IDENTITIES.revoke_account_sessions(account_id)
    except IdentityError as exc:
        raise HTTPException(404, detail={"code": str(exc), "request_id": request_id}) from exc
    _audit(identity.account_id, "admin.account.sessions.revoke", "allowed", request_id, identity.scope)
    return {"request_id": request_id, "status": "sessions_revoked"}


@app.get("/v1/admin/audit")
def admin_audit(request: Request, limit: int = Query(default=50, ge=1, le=200), action: str | None = Query(default=None, max_length=100)) -> dict[str, object]:
    request_id = _request_id(request)
    identity = _require_admin(request, request_id)
    _audit(identity.account_id, "admin.audit.read", "allowed", request_id, identity.scope)
    return {"request_id": request_id, "events": LOCAL_IDENTITIES.list_audit_events(limit, action)}


@app.get("/v1/admin/system")
def admin_system(request: Request) -> dict[str, object]:
    request_id = _request_id(request)
    identity = _require_admin(request, request_id)
    _audit(identity.account_id, "admin.system.read", "allowed", request_id, identity.scope)
    return {
        "request_id": request_id,
        "profile": RUNTIME_PROFILE,
        "data_level": "fixture_l0_l1",
        "read_only": True,
        "configuration_schema": "none_registered",
        "limitations": ["no_real_connector", "no_model_provider", "no_write_operation"],
    }


def _scope_dict(scope: Scope) -> dict[str, object]:
    return {
        "project_id": scope.project_id,
        "site_ids": sorted(scope.site_ids),
        "cluster_ids": sorted(scope.cluster_ids),
        "resource_types": sorted(scope.resource_types),
        "actions": sorted(scope.actions),
    }


def _local_identity_dict(identity: LocalIdentity) -> dict[str, object]:
    return {"account_id": identity.account_id, "username": identity.username, "display_name": identity.display_name, "role": identity.role, "scope": _scope_dict(identity.scope)}


def _view_dict(context: ViewContext) -> dict[str, object]:
    return {
        "view_id": context.view_id,
        "version": context.version,
        "scope": _scope_dict(context.scope),
        "filters": dict(context.filters),
        "focus_resource_id": context.focus_resource_id,
        "query_id": context.query_id,
    }


def _manifest_dict(manifest: CapabilityManifest) -> dict[str, object]:
    return {
        "capability_id": manifest.capability_id,
        "version": manifest.version,
        "owner": manifest.owner,
        "status": manifest.status,
        "profile": manifest.profile,
        "tool_ids": list(manifest.tool_ids),
        "view_ids": list(manifest.view_ids),
        "limitations": list(manifest.limitations),
        "enabled": True if manifest.capability_id not in MANAGEABLE_CAPABILITIES else LOCAL_IDENTITIES.capability_enabled(manifest.capability_id),
        "manageable": manifest.capability_id in MANAGEABLE_CAPABILITIES,
    }


def _audit_dict(event: AuditEvent) -> dict[str, object]:
    return {
        "event_id": event.event_id,
        "occurred_at": event.occurred_at.isoformat(),
        "actor_id": event.actor_id,
        "action": event.action,
        "outcome": event.outcome,
        "request_id": event.request_id,
        "query_id": event.query_id,
        "scope_project_id": event.scope_project_id,
        "tool_id": event.tool_id,
        "reason_code": event.reason_code,
    }


def _optic_query_dict(result: OpticHealthQuery) -> dict[str, object]:
    return {
        "summary": result.summary,
        "source": result.source,
        "observed_from": result.observed_from.isoformat(),
        "observed_to": result.observed_to.isoformat(),
        "rule_version": result.rule_version,
        "records": [
            {
                "resource": asdict(item.resource),
                "latest_observation": {
                    **asdict(item.latest_observation),
                    "observed_at": item.latest_observation.observed_at.isoformat(),
                },
                "assessment": {
                    **asdict(item.assessment),
                    "evaluated_at": item.assessment.evaluated_at.isoformat(),
                },
                "event": None
                if item.event is None
                else {
                    **asdict(item.event),
                    "first_seen_at": item.event.first_seen_at.isoformat(),
                    "last_seen_at": item.event.last_seen_at.isoformat(),
                },
            }
            for item in result.records
        ],
    }
