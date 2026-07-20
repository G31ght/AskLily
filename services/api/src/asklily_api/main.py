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

app = FastAPI(title="AskLily P2 Optic Health API", version="0.2.0")

OPTIC_TOOL_ID = "optic_health.query"
OPTIC_VIEW_ID = "optic_health"
ALLOWED_HEALTH = frozenset({"healthy", "critical", "warning", "recovered", "unknown"})


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
        "developer",
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
        "developer",
        (OPTIC_TOOL_ID,),
        (OPTIC_VIEW_ID,),
        ("fixture_l0_l1_only", "no_real_connector", "no_write_operation"),
    )
)
AUDIT_EVENTS: list[AuditEvent] = []
ORCHESTRATOR = OpticHealthOrchestrator()


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
    AUDIT_EVENTS.append(
        AuditEvent(
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
    )


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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "profile": "developer", "data": "fixture_l0_l1", "rule_version": OPTIC_RULE_VERSION}


@app.get("/v1/session")
def session(request: Request, x_asklily_role: str = Header(default="operator")) -> dict[str, object]:
    request_id = _request_id(request)
    display_name, scope = _identity(x_asklily_role, request_id)
    _audit(x_asklily_role, "session.read", "allowed", request_id, scope)
    return {
        "request_id": request_id,
        "identity": {"role": x_asklily_role, "display_name": display_name},
        "scope": _scope_dict(scope),
        "profile": "developer",
    }


@app.get("/v1/capabilities")
def capabilities(request: Request, x_asklily_role: str = Header(default="operator")) -> dict[str, object]:
    request_id = _request_id(request)
    _, scope = _identity(x_asklily_role, request_id)
    _audit(x_asklily_role, "capability_catalog.read", "allowed", request_id, scope)
    return {"request_id": request_id, "capabilities": [_manifest_dict(item) for item in REGISTRY.capabilities.values()]}


@app.post("/v1/tools/{tool_id}/authorize")
def authorize_tool(tool_id: str, request: Request, x_asklily_role: str = Header(default="operator")) -> dict[str, object]:
    request_id = _request_id(request)
    _, scope = _identity(x_asklily_role, request_id)
    try:
        contract = REGISTRY.authorize_tool(tool_id, scope)
    except ContractViolation as exc:
        _audit(x_asklily_role, "tool.authorize", "denied", request_id, scope, tool_id=tool_id, reason=str(exc))
        raise HTTPException(404, detail={"code": str(exc), "request_id": request_id}) from exc
    _audit(x_asklily_role, "tool.authorize", "allowed", request_id, scope, tool_id=tool_id)
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
    _, scope = _identity(x_asklily_role, request_id)
    result = _run_optic_query(
        scope,
        x_asklily_role,
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
    _, scope = _identity(x_asklily_role, request_id)
    result = _run_optic_query(scope, x_asklily_role, request_id, search=query)
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
    _, server_scope = _identity(x_asklily_role, request_id)
    try:
        context = REGISTRY.validate_view_context(
            ViewContext(payload.view_id, payload.version, payload.scope.as_contract(), payload.filters, payload.focus_resource_id),
            server_scope,
        )
    except ContractViolation as exc:
        _audit(x_asklily_role, "view.validate", "denied", request_id, server_scope, reason=str(exc))
        raise HTTPException(403, detail={"code": str(exc), "request_id": request_id}) from exc
    _audit(x_asklily_role, "view.validate", "allowed", request_id, context.scope)
    return {"request_id": request_id, "view_context": _view_dict(context)}


@app.post("/v1/chat")
def chat(payload: ChatInput, request: Request, x_asklily_role: str = Header(default="operator")) -> dict[str, object]:
    request_id = _request_id(request)
    _, server_scope = _identity(x_asklily_role, request_id)
    scope = _narrow(
        server_scope,
        payload.requested_scope.as_contract() if payload.requested_scope else None,
        x_asklily_role,
        request_id,
        "chat.read",
    )
    _audit(x_asklily_role, "chat.read", "allowed", request_id, scope)
    result = _run_optic_query(
        scope,
        x_asklily_role,
        request_id,
        health_filter=health_filter_for_question(payload.question),
    )
    return dict(ORCHESTRATOR.respond(payload.question, scope, request_id, result))


@app.get("/v1/audit")
def audit(request: Request, x_asklily_role: str = Header(default="auditor")) -> dict[str, object]:
    request_id = _request_id(request)
    _, scope = _identity(x_asklily_role, request_id)
    if x_asklily_role not in {"auditor", "project-admin"}:
        _audit(x_asklily_role, "audit.read", "denied", request_id, scope, reason="audit_role_required")
        raise HTTPException(403, detail={"code": "audit_role_required", "request_id": request_id})
    _audit(x_asklily_role, "audit.read", "allowed", request_id, scope)
    return {"request_id": request_id, "events": [_audit_dict(event) for event in AUDIT_EVENTS]}


def _scope_dict(scope: Scope) -> dict[str, object]:
    return {
        "project_id": scope.project_id,
        "site_ids": sorted(scope.site_ids),
        "cluster_ids": sorted(scope.cluster_ids),
        "resource_types": sorted(scope.resource_types),
        "actions": sorted(scope.actions),
    }


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
