"""P2 read-only API: deterministic Fixture optic-health vertical slice."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

from asklily_agent import (
    CapabilityCatalogOrchestrator,
    OpticHealthOrchestrator,
    ResourceExplorerOrchestrator,
    health_filter_for_question,
    is_capability_catalog_question,
    resource_explorer_intent,
)
from asklily_contracts import (
    AuditEvent,
    CapabilityManifest,
    ContractViolation,
    Scope,
    ToolContract,
    ViewContext,
    ViewContract,
)
from asklily_domain import (
    OPTIC_RULE_VERSION,
    RESOURCE_EXPLORER_SOURCE,
    OpticHealthQuery,
    PlatformRegistry,
    query_optic_health,
    related_resources,
    resource_detail,
    search_resources,
    validate_resource_query,
)
from asklily_monitoring import assess_monitoring_source_preflight
from fastapi import FastAPI, Header, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import JSONResponse

from .local_identity import IdentityError, LocalIdentity, LocalIdentityStore, default_database_path
from .runtime import DataSource, load_runtime_config

RUNTIME_CONFIG = load_runtime_config()
app = FastAPI(title="AskLily Unified Runtime API", version="0.6.0")

OPTIC_TOOL_ID = "optic_health.query"
OPTIC_VIEW_ID = "optic_health"
CAPABILITY_CATALOG_TOOL_ID = "capability_catalog.read"
CAPABILITY_CATALOG_VIEW_ID = "capability_catalog"
RESOURCE_EXPLORER_TOOL_ID = "resource_explorer.read"
RESOURCE_SEARCH_VIEW_ID = "resource_search"
RESOURCE_DETAIL_VIEW_ID = "resource_detail"
CATALOG_VERSION = "1.0.0"
ALLOWED_HEALTH = frozenset({"healthy", "critical", "warning", "recovered", "unknown"})

# A future model Skill may select only from this server-owned presentation
# registry.  It cannot supply arbitrary components, query parameters or data.
PRESENTATION_MODULES: dict[str, dict[str, str]] = {
    "optic-health-overview": {"module_id": "optic-health-overview", "view_id": OPTIC_VIEW_ID},
    "capability-catalog-overview": {"module_id": "capability-catalog-overview", "view_id": CAPABILITY_CATALOG_VIEW_ID},
    "resource-search-results": {"module_id": "resource-search-results", "view_id": RESOURCE_SEARCH_VIEW_ID},
    "resource-detail-overview": {"module_id": "resource-detail-overview", "view_id": RESOURCE_DETAIL_VIEW_ID},
}
MANAGEABLE_CAPABILITIES = frozenset({"optic-health", "resource-explorer"})


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


class LocalAccountInput(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=12, max_length=128)
    display_name: str | None = Field(default=None, max_length=100)


class LocalLoginInput(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class LocalAdminBootstrapInput(LocalAccountInput):
    """First-run local administrator creation; unavailable after bootstrap."""


class AccountDeletionInput(BaseModel):
    password: str = Field(min_length=1, max_length=128)


class AdminCapabilityStateInput(BaseModel):
    enabled: bool


class AdminAccountStateInput(BaseModel):
    status: str = Field(pattern="^(active|disabled)$")


class AdminAccountCreateInput(LocalAccountInput):
    site_ids: set[str] = Field(min_length=1, max_length=100)


FIXTURE_IDENTITIES: dict[str, tuple[str, Scope]] = {
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
REGISTRY.register_view(ViewContract("platform_status", "1.0.0"))
REGISTRY.register_capability(
    CapabilityManifest(
        "platform-foundation",
        "1.0.0",
        "platform",
        "verified_skeleton",
        (),
        ("platform.status",),
        ("platform_status",),
        ("no_business_capability", "no_real_data", "no_model_provider"),
        "平台基础能力", "受控只读平台骨架与契约状态。", "平台", "verified_skeleton", "现在可以做什么？",
    )
)
REGISTRY.register_tool(ToolContract("monitoring_source.readiness", "1.0.0", "platform", "read", "1.0.0", "1.0.0"))
REGISTRY.register_view(ViewContract("monitoring_source_readiness", "1.0.0"))
REGISTRY.register_capability(
    CapabilityManifest(
        "monitoring-source-readiness", "1.0.0", "platform", "mock_candidate",
        tuple(item.source_id for item in RUNTIME_CONFIG.sources if item.kind in {"zabbix", "prometheus"}),
        ("monitoring_source.readiness",), ("monitoring_source_readiness",),
        ("no_network_io", "no_secret_material", "no_real_connector", "no_write_operation"),
        "监控来源就绪度", "仅显示已声明监控来源的无网络预检状态。", "来源透明", "preflight_only", "为什么 Zabbix 不能查询？", True,
    )
)
REGISTRY.register_tool(ToolContract(OPTIC_TOOL_ID, "1.0.0", "optic-health", "read", "1.0.0", "1.0.0"))
REGISTRY.register_view(ViewContract(OPTIC_VIEW_ID, "1.0.0", frozenset({"health", "time_range"}), frozenset({"optic-health-overview"})))
REGISTRY.register_capability(
    CapabilityManifest(
        "optic-health",
        "1.0.0",
        "optic-health",
        "demo_candidate",
        tuple(item.source_id for item in RUNTIME_CONFIG.sources if "optic-health" in item.capability_ids),
        (OPTIC_TOOL_ID,),
        (OPTIC_VIEW_ID,),
        ("fixture_l0_l1_only", "no_real_connector", "no_write_operation"),
        "光模块健康", "基于受控 Fixture 的只读光模块健康查询。", "网络健康", "fixture_l0_l1", "查看当前光模块健康异常", True,
    )
)
REGISTRY.register_tool(ToolContract(CAPABILITY_CATALOG_TOOL_ID, "1.0.0", "platform", "read", "1.0.0", "1.0.0"))
REGISTRY.register_view(ViewContract(CAPABILITY_CATALOG_VIEW_ID, "1.0.0", frozenset(), frozenset({"capability-catalog-overview"})))
REGISTRY.register_capability(
    CapabilityManifest(
        "capability-center", "1.0.0", "platform", "verified",
        (), (CAPABILITY_CATALOG_TOOL_ID,), (CAPABILITY_CATALOG_VIEW_ID,),
        ("read_only", "no_real_connector", "no_write_operation"),
        "能力中心与来源透明", "展示已注册能力、来源状态与可见范围。", "平台", "registry_derived", "现在可以做什么？",
    )
)
REGISTRY.register_tool(ToolContract(RESOURCE_EXPLORER_TOOL_ID, "1.0.0", "resource-explorer", "read", "1.0.0", "1.0.0"))
REGISTRY.register_view(
    ViewContract(
        RESOURCE_SEARCH_VIEW_ID,
        "1.0.0",
        frozenset({"query", "site_id", "resource_type", "health", "page"}),
        frozenset({"resource-search-results"}),
    )
)
REGISTRY.register_view(
    ViewContract(RESOURCE_DETAIL_VIEW_ID, "1.0.0", frozenset(), frozenset({"resource-detail-overview"}))
)
REGISTRY.register_capability(
    CapabilityManifest(
        "resource-explorer",
        "1.0.0",
        "resource-explorer",
        "demo_candidate",
        tuple(item.source_id for item in RUNTIME_CONFIG.sources if "resource-explorer" in item.capability_ids),
        (RESOURCE_EXPLORER_TOOL_ID,),
        (RESOURCE_SEARCH_VIEW_ID, RESOURCE_DETAIL_VIEW_ID),
        ("fixture_l0_l1_only", "no_real_connector", "no_write_operation", "no_resource_mutation"),
        "资源检索与详情工作台",
        "基于受控 Fixture 的只读资源检索、详情与已有光模块健康摘要。",
        "资源目录",
        "fixture_l0_l1",
        "检索当前可见资源",
        True,
    )
)
AUDIT_EVENTS: list[AuditEvent] = []
ORCHESTRATOR = OpticHealthOrchestrator()
CATALOG_ORCHESTRATOR = CapabilityCatalogOrchestrator()
RESOURCE_EXPLORER_ORCHESTRATOR = ResourceExplorerOrchestrator()
LOCAL_IDENTITIES = LocalIdentityStore(default_database_path())
SESSION_COOKIE = "asklily_local_session"


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "missing-request-id")


@app.exception_handler(IdentityError)
async def identity_storage_failure(request: Request, exc: IdentityError) -> JSONResponse:
    """Do not continue with stale or partially written local control-plane state."""
    request_id = _request_id(request)
    code = str(exc)
    status = 503 if code.startswith("local_storage_") else 500
    return JSONResponse(status_code=status, content={"detail": {"code": code, "request_id": request_id}})


@app.middleware("http")
async def attach_request_id(request: Request, call_next: RequestResponseEndpoint) -> Response:
    request.state.request_id = request.headers.get("X-Request-ID", str(uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


def _identity(role: str, request_id: str) -> tuple[str, Scope]:
    try:
        return FIXTURE_IDENTITIES[role]
    except KeyError as exc:
        _audit(role, "session.resolve", "denied", request_id, Scope("unknown"), reason="unknown_fixture_role")
        raise HTTPException(401, detail={"code": "unknown_fixture_role", "request_id": request_id}) from exc


def _local_identity(request: Request, request_id: str) -> LocalIdentity | None:
    token = request.cookies.get(SESSION_COOKIE)
    if token is None:
        return None
    try:
        return LOCAL_IDENTITIES.resolve_session(token)
    except IdentityError as exc:
        status = 503 if str(exc).startswith("local_storage_") else 401
        raise HTTPException(status, detail={"code": str(exc), "request_id": request_id}) from exc


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


def _data_source_states(scope: Scope | None = None) -> list[dict[str, object]]:
    full_states = [item.public_state() for item in RUNTIME_CONFIG.sources]
    for state in full_states:
        LOCAL_IDENTITIES.record_data_source_state(state)
    allowed_sites = scope.site_ids if scope is not None and scope.site_ids else None
    return [item.public_state(allowed_sites) for item in RUNTIME_CONFIG.sources]


def _source_for_capability(capability_id: str, actor: str, scope: Scope, request_id: str) -> tuple[DataSource, Scope]:
    source = RUNTIME_CONFIG.source_for_capability(capability_id)
    if source is None:
        _audit(actor, f"{capability_id}.source", "denied", request_id, scope, reason="data_source_not_configured")
        raise HTTPException(503, detail={"code": "data_source_not_configured", "request_id": request_id})
    state = source.public_state()
    LOCAL_IDENTITIES.record_data_source_state(state)
    if not source.enabled:
        _audit(actor, f"{capability_id}.source", "denied", request_id, scope, reason="data_source_disabled")
        raise HTTPException(409, detail={"code": "data_source_disabled", "request_id": request_id})
    if source.kind != "fixture" or state["connection_state"] != "ready":
        _audit(actor, f"{capability_id}.source", "denied", request_id, scope, reason="data_source_unavailable")
        raise HTTPException(503, detail={"code": "data_source_unavailable", "request_id": request_id})
    source_sites = source.visible_site_ids if not scope.site_ids else source.visible_site_ids & scope.site_ids
    if not source_sites:
        _audit(actor, f"{capability_id}.source", "denied", request_id, scope, reason="data_source_scope_not_allowed")
        raise HTTPException(403, detail={"code": "data_source_scope_not_allowed", "request_id": request_id})
    return source, Scope(scope.project_id, source_sites, scope.cluster_ids, scope.resource_types, scope.actions)


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
    _, source_scope = _source_for_capability("optic-health", role, scope, request_id)
    try:
        REGISTRY.authorize_tool(OPTIC_TOOL_ID, scope)
    except ContractViolation as exc:
        _audit(role, "optic_health.query", "denied", request_id, scope, tool_id=OPTIC_TOOL_ID, reason=str(exc))
        raise HTTPException(403, detail={"code": str(exc), "request_id": request_id}) from exc
    result = query_optic_health(
        source_scope,
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


def _resource_source_scope(scope: Scope, actor: str, request_id: str) -> tuple[DataSource, Scope]:
    """Authorize the registered P5G Tool before accessing its Fixture directory."""
    _require_capability_enabled("resource-explorer", actor, scope, request_id)
    try:
        REGISTRY.authorize_tool(RESOURCE_EXPLORER_TOOL_ID, scope)
    except ContractViolation as exc:
        _audit(actor, "resource_explorer.read", "denied", request_id, scope, tool_id=RESOURCE_EXPLORER_TOOL_ID, reason=str(exc))
        raise HTTPException(403, detail={"code": str(exc), "request_id": request_id}) from exc
    source, source_scope = _source_for_capability("resource-explorer", actor, scope, request_id)
    _audit(
        actor,
        "resource_explorer.read",
        "allowed",
        request_id,
        scope,
        tool_id=RESOURCE_EXPLORER_TOOL_ID,
        query_id=f"fixture-resource:{request_id}",
    )
    return source, source_scope


def _resource_health_summaries(scope: Scope, health_filter: frozenset[str]) -> dict[str, dict[str, object]]:
    """Reference the established P2 conclusion without exposing facts or events."""
    query = query_optic_health(scope, health_filter=health_filter)
    return {
        record.resource.resource_id: {
            "health": record.assessment.health,
            "reason_codes": list(record.assessment.reason_codes),
            "rule_version": record.assessment.rule_version,
        }
        for record in query.records
    }


def _resource_summary(record: object, health_summaries: dict[str, dict[str, object]]) -> dict[str, object]:
    """Serialize the narrowly-defined public summary shared by search and details."""
    resource = cast(Any, record).resource
    return {
        "resource_id": resource.resource_id,
        "display_name": resource.display_name,
        "resource_type": resource.resource_type,
        "site_id": resource.site_id,
        "summary": cast(Any, record).summary,
        "health": health_summaries.get(resource.resource_id),
    }


def _parent_resource_id(record: object) -> str | None:
    resource = cast(Any, record).resource
    related = cast(tuple[str, ...], cast(Any, record).related_resource_ids)
    if resource.resource_type == "site":
        return None
    if resource.resource_type == "device":
        return next((item for item in related if item.startswith("site-")), None)
    if resource.resource_type == "interface":
        return next((item for item in related if item.startswith("leaf-")), None)
    if resource.resource_type == "optic_module":
        return next((item for item in related if item.startswith("interface-")), None)
    return None


def _resource_search_response(
    scope: Scope,
    actor: str,
    request_id: str,
    *,
    query: str | None,
    site_id: str | None,
    resource_type: str | None,
    health_filter: frozenset[str],
    page: int,
) -> dict[str, object]:
    source, source_scope = _resource_source_scope(scope, actor, request_id)
    health_summaries = _resource_health_summaries(source_scope, health_filter)
    try:
        result = search_resources(
            source_scope,
            query=query,
            site_id=site_id,
            resource_type=resource_type,
            resource_ids=frozenset(health_summaries) if health_filter else None,
            page=page,
        )
    except ValueError as exc:
        raise HTTPException(422, detail={"code": str(exc), "request_id": request_id}) from exc
    return {
        "request_id": request_id,
        "query": {
            "items": [_resource_summary(record, health_summaries) for record in result.items],
            "page": result.page,
            "page_size": result.page_size,
            "total": result.total,
            "has_more": result.has_more,
            "source": RESOURCE_EXPLORER_SOURCE,
            "limitations": ["fixture_l0_l1_only", "no_real_connector", "no_write_operation"],
        },
    }


def _resource_detail_response(scope: Scope, actor: str, request_id: str, resource_id: str) -> dict[str, object]:
    source, source_scope = _resource_source_scope(scope, actor, request_id)
    record = resource_detail(source_scope, resource_id)
    # Deliberately identical for a non-existent ID and an existing ID hidden by Scope.
    if record is None:
        raise HTTPException(404, detail={"code": "resource_not_available", "request_id": request_id})
    health_summaries = _resource_health_summaries(source_scope, frozenset())
    focus = _resource_summary(record, health_summaries)
    focus["parent_resource_id"] = _parent_resource_id(record)
    return {
        "request_id": request_id,
        "detail": {
            "resource": focus,
            "related": [_resource_summary(item, health_summaries) for item in related_resources(record, source_scope)],
            "source": RESOURCE_EXPLORER_SOURCE,
            "data_level": source.data_level,
            "limitations": ["fixture_l0_l1_only", "no_real_connector", "no_write_operation"],
        },
    }


def _validate_resource_view_filters(filters: dict[str, object], request_id: str) -> None:
    """Validate filter values as well as Registry keys before a Workspace fetch."""
    query = filters.get("query")
    site_id = filters.get("site_id")
    resource_type = filters.get("resource_type")
    health = filters.get("health", [])
    page = filters.get("page", 1)
    if query is not None and (not isinstance(query, str) or _invalid_resource_query(query)):
        raise HTTPException(422, detail={"code": "resource_search_query_invalid", "request_id": request_id})
    if site_id is not None and (not isinstance(site_id, str) or not site_id):
        raise HTTPException(422, detail={"code": "resource_site_filter_invalid", "request_id": request_id})
    if resource_type is not None and not isinstance(resource_type, str):
        raise HTTPException(422, detail={"code": "resource_type_invalid", "request_id": request_id})
    if not isinstance(health, list) or not all(isinstance(item, str) for item in health):
        raise HTTPException(422, detail={"code": "resource_health_filter_invalid", "request_id": request_id})
    _health_filter(cast(list[str], health), request_id)
    if isinstance(page, bool) or not isinstance(page, int) or page < 1:
        raise HTTPException(422, detail={"code": "resource_search_pagination_invalid", "request_id": request_id})
    try:
        # The directory owns the type allowlist and page-size rule; this call is
        # validation-only and has no side effect or source access.
        search_resources(Scope("demo-project"), resource_type=resource_type, page=page)
    except ValueError as exc:
        raise HTTPException(422, detail={"code": str(exc), "request_id": request_id}) from exc


def _invalid_resource_query(query: str) -> bool:
    try:
        validate_resource_query(query)
    except ValueError:
        return True
    return False


def _server_presentation(view_id: str, module_ids: tuple[str, ...]) -> dict[str, object]:
    """Create and validate a server-owned Workspace presentation directive."""
    try:
        REGISTRY.validate_presentation_modules(view_id, module_ids)
    except ContractViolation as exc:  # A programming/configuration defect must fail closed.
        raise RuntimeError(str(exc)) from exc
    return {
        "mode": "work",
        "modules": [PRESENTATION_MODULES[module_id] for module_id in module_ids],
    }


def _catalog_sources(manifest: CapabilityManifest) -> tuple[DataSource, ...]:
    """Resolve sources only through the registered capability and P6 runtime state."""
    if manifest.capability_id == "monitoring-source-readiness":
        return tuple(item for item in RUNTIME_CONFIG.sources if item.kind in {"zabbix", "prometheus"})
    return tuple(item for item in RUNTIME_CONFIG.sources if manifest.capability_id in item.capability_ids)


def _catalog_status(
    manifest: CapabilityManifest, sources: tuple[DataSource, ...]
) -> dict[str, str | None]:
    if not LOCAL_IDENTITIES.capability_enabled(manifest.capability_id):
        return {"code": "disabled", "reason_code": "capability_disabled"}
    if not sources:
        if manifest.requires_data_source:
            return {"code": "not_configured", "reason_code": "data_source_not_configured"}
        return {"code": "ready", "reason_code": None}
    states = [item.public_state() for item in sources]
    if all(state["connection_state"] == "disabled" for state in states):
        return {"code": "disabled", "reason_code": "data_source_disabled"}
    if any(state["connection_state"] == "ready" for state in states):
        return {"code": "ready", "reason_code": None}
    reason = next((state["reason_code"] for state in states if state["reason_code"]), "data_source_unavailable")
    return {"code": "unavailable", "reason_code": str(reason)}


def _catalog_entries(scope: Scope, is_project_admin: bool) -> list[dict[str, object]]:
    """Project Registry and P6 public state into a caller-safe catalog."""
    entries: list[dict[str, object]] = []
    allowed_sites = None if is_project_admin or not scope.site_ids else scope.site_ids
    for manifest in REGISTRY.capabilities.values():
        sources = _catalog_sources(manifest)
        # An operator must not learn that a source-backed capability exists
        # outside their site scope. Source-less registered platform capabilities
        # remain visible because they carry no site-scoped data.
        if sources and allowed_sites and not any(source.visible_site_ids & allowed_sites for source in sources):
            continue
        states = [
            source.public_state(allowed_sites)
            for source in sources
        ]
        entries.append(
            {
                "capability_id": manifest.capability_id,
                "display_name": manifest.display_name,
                "summary": manifest.summary,
                "category": manifest.category,
                "status": _catalog_status(manifest, sources),
                "data_sources": states,
                "read_only": True,
                "verification_level": manifest.verification_level,
                "limitations": list(manifest.limitations),
                "next_actions": [{"kind": "chat", "question": manifest.next_action}],
            }
        )
    return entries


def _capability_catalog_response(
    actor: str,
    scope: Scope,
    request_id: str,
    *,
    is_project_admin: bool,
) -> dict[str, object]:
    try:
        REGISTRY.authorize_tool(CAPABILITY_CATALOG_TOOL_ID, scope)
    except ContractViolation as exc:
        _audit(actor, "capability_catalog.read", "denied", request_id, scope, tool_id=CAPABILITY_CATALOG_TOOL_ID, reason=str(exc))
        raise HTTPException(403, detail={"code": str(exc), "request_id": request_id}) from exc
    context = REGISTRY.validate_view_context(
        ViewContext(CAPABILITY_CATALOG_VIEW_ID, CATALOG_VERSION, scope, {}), scope
    )
    _audit(actor, "capability_catalog.read", "allowed", request_id, scope, tool_id=CAPABILITY_CATALOG_TOOL_ID)
    return {
        "request_id": request_id,
        "catalog_version": CATALOG_VERSION,
        "view_context": _view_dict(context),
        "presentation": _server_presentation(CAPABILITY_CATALOG_VIEW_ID, ("capability-catalog-overview",)),
        "catalog": {
            "declared_environment": RUNTIME_CONFIG.deployment_environment,
            "capabilities": _catalog_entries(scope, is_project_admin),
        },
    }


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "runtime": _runtime_dict(),
        "rule_version": OPTIC_RULE_VERSION,
    }


@app.post("/v1/auth/login")
def login_local_account(payload: LocalLoginInput, request: Request, response: Response) -> dict[str, object]:
    request_id = _request_id(request)
    try:
        identity = LOCAL_IDENTITIES.authenticate(payload.username, payload.password)
        token = LOCAL_IDENTITIES.issue_session(identity.account_id)
    except IdentityError as exc:
        status = 503 if str(exc).startswith("local_storage_") else 401
        raise HTTPException(status, detail={"code": str(exc), "request_id": request_id}) from exc
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
        status = 503 if code.startswith("local_storage_") else 409 if code == "local_project_admin_already_exists" else 400
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
        status = 503 if str(exc).startswith("local_storage_") else 401
        raise HTTPException(status, detail={"code": str(exc), "request_id": request_id}) from exc
    response.delete_cookie(SESSION_COOKIE)
    _audit(identity.account_id, "local_account.delete", "allowed", request_id, identity.scope)
    return {"request_id": request_id, "status": "account_deleted"}


@app.get("/v1/session")
def session(request: Request, x_asklily_role: str = Header(default="operator")) -> dict[str, object]:
    request_id = _request_id(request)
    actor, scope, local = _request_identity(request, x_asklily_role, request_id)
    display_name = local.display_name if local is not None else FIXTURE_IDENTITIES[x_asklily_role][0]
    role = local.role if local is not None else x_asklily_role
    _audit(actor, "session.read", "allowed", request_id, scope)
    return {
        "request_id": request_id,
        "identity": {"role": role, "display_name": display_name, "authenticated": local is not None},
        "scope": _scope_dict(scope),
        "runtime": _runtime_dict(scope),
    }


@app.get("/v1/capabilities")
def capabilities(request: Request, x_asklily_role: str = Header(default="operator")) -> dict[str, object]:
    request_id = _request_id(request)
    actor, scope, local = _request_identity(request, x_asklily_role, request_id)
    return _capability_catalog_response(
        actor,
        scope,
        request_id,
        is_project_admin=(local.role if local is not None else x_asklily_role) == "project-admin",
    )


@app.get("/v1/capability-catalog")
def capability_catalog(request: Request, x_asklily_role: str = Header(default="operator")) -> dict[str, object]:
    request_id = _request_id(request)
    actor, scope, local = _request_identity(request, x_asklily_role, request_id)
    return _capability_catalog_response(
        actor,
        scope,
        request_id,
        is_project_admin=(local.role if local is not None else x_asklily_role) == "project-admin",
    )


@app.get("/v1/data-sources")
def data_sources(request: Request, x_asklily_role: str = Header(default="operator")) -> dict[str, object]:
    request_id = _request_id(request)
    actor, scope, _ = _request_identity(request, x_asklily_role, request_id)
    _audit(actor, "data_source_catalog.read", "allowed", request_id, scope)
    return {"request_id": request_id, "runtime": _runtime_dict(scope)}


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


@app.get("/v1/resources")
def resources(
    request: Request,
    query: str | None = Query(default=None, max_length=100),
    site_id: str | None = Query(default=None, max_length=100),
    resource_type: str | None = Query(default=None, max_length=100),
    health: list[str] = Query(default=[]),
    page: int = Query(default=1, ge=1),
    x_asklily_role: str = Header(default="operator"),
) -> dict[str, object]:
    """Server-side paginated, Scope-projected public resource directory."""
    request_id = _request_id(request)
    actor, scope, _ = _request_identity(request, x_asklily_role, request_id)
    return _resource_search_response(
        scope,
        actor,
        request_id,
        query=query,
        site_id=site_id,
        resource_type=resource_type,
        health_filter=_health_filter(health, request_id),
        page=page,
    )


@app.get("/v1/resources/suggestions")
def resource_suggestions(
    request: Request,
    query: str = Query(min_length=1, max_length=100),
    x_asklily_role: str = Header(default="operator"),
) -> dict[str, object]:
    """Return at most ten visible public summaries; there is no global lookup."""
    request_id = _request_id(request)
    actor, scope, _ = _request_identity(request, x_asklily_role, request_id)
    response = _resource_search_response(
        scope,
        actor,
        request_id,
        query=query,
        site_id=None,
        resource_type=None,
        health_filter=frozenset(),
        page=1,
    )
    items = cast(dict[str, Any], response["query"])["items"]
    return {"request_id": request_id, "suggestions": items[:10]}


@app.get("/v1/resources/{resource_id}")
def resource_by_id(
    resource_id: str,
    request: Request,
    x_asklily_role: str = Header(default="operator"),
) -> dict[str, object]:
    request_id = _request_id(request)
    actor, scope, _ = _request_identity(request, x_asklily_role, request_id)
    return _resource_detail_response(scope, actor, request_id, resource_id)


@app.post("/v1/views/context")
def validate_view_context(
    payload: ViewContextInput, request: Request, x_asklily_role: str = Header(default="operator")
) -> dict[str, object]:
    request_id = _request_id(request)
    actor, server_scope, _ = _request_identity(request, x_asklily_role, request_id)
    if payload.view_id == OPTIC_VIEW_ID:
        _require_capability_enabled("optic-health", actor, server_scope, request_id)
    if payload.view_id == RESOURCE_SEARCH_VIEW_ID:
        if payload.focus_resource_id is not None:
            raise HTTPException(403, detail={"code": "view_focus_not_allowed", "request_id": request_id})
        _validate_resource_view_filters(payload.filters, request_id)
    try:
        context = REGISTRY.validate_view_context(
            ViewContext(payload.view_id, payload.version, payload.scope.as_contract(), payload.filters, payload.focus_resource_id),
            server_scope,
        )
    except ContractViolation as exc:
        _audit(actor, "view.validate", "denied", request_id, server_scope, reason=str(exc))
        raise HTTPException(403, detail={"code": str(exc), "request_id": request_id}) from exc
    if payload.view_id == OPTIC_VIEW_ID:
        _, data_source_scope = _source_for_capability("optic-health", actor, context.scope, request_id)
        context = ViewContext(context.view_id, context.version, data_source_scope, context.filters, context.focus_resource_id, context.query_id)
    if payload.view_id in {RESOURCE_SEARCH_VIEW_ID, RESOURCE_DETAIL_VIEW_ID}:
        _, data_source_scope = _resource_source_scope(context.scope, actor, request_id)
        if payload.view_id == RESOURCE_DETAIL_VIEW_ID:
            if context.focus_resource_id is None or resource_detail(data_source_scope, context.focus_resource_id) is None:
                # Do not allow a context-validation probe to distinguish hidden IDs.
                raise HTTPException(404, detail={"code": "resource_not_available", "request_id": request_id})
        context = ViewContext(context.view_id, context.version, data_source_scope, context.filters, context.focus_resource_id, context.query_id)
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
    if is_capability_catalog_question(payload.question):
        catalog = _capability_catalog_response(
            actor,
            scope,
            request_id,
            is_project_admin=(local.role if local is not None else x_asklily_role) == "project-admin",
        )
        response = dict(
            CATALOG_ORCHESTRATOR.respond(
                payload.question,
                request_id,
                cast(dict[str, Any], catalog["catalog"]),
                cast(dict[str, Any], catalog["view_context"]),
                cast(dict[str, Any], catalog["presentation"]),
            )
        )
        conversation_source = "capability-catalog"
        conversation_limitations = "read_only,no_real_connector,no_write_operation"
    elif (resource_intent := resource_explorer_intent(payload.question)) is not None:
        _, resource_scope = _resource_source_scope(scope, actor, request_id)
        if resource_intent.response_kind == "resource_detail":
            if resource_intent.focus_resource_id is None or resource_detail(resource_scope, resource_intent.focus_resource_id) is None:
                # A Chat request must not turn into a resource-enumeration oracle.
                raise HTTPException(404, detail={"code": "resource_not_available", "request_id": request_id})
        else:
            try:
                if resource_intent.query is not None:
                    validate_resource_query(resource_intent.query)
            except ValueError as exc:
                raise HTTPException(422, detail={"code": str(exc), "request_id": request_id}) from exc
        response = dict(RESOURCE_EXPLORER_ORCHESTRATOR.respond(payload.question, resource_scope, request_id, resource_intent))
        raw_context = cast(dict[str, Any], response["view_context"])
        context = REGISTRY.validate_view_context(
            ViewContext(
                str(raw_context["view_id"]),
                str(raw_context["version"]),
                resource_scope,
                cast(dict[str, object], raw_context["filters"]),
                cast(str | None, raw_context["focus_resource_id"]),
                cast(str | None, raw_context["query_id"]),
            ),
            resource_scope,
        )
        response["view_context"] = _view_dict(context)
        module_id = "resource-detail-overview" if context.view_id == RESOURCE_DETAIL_VIEW_ID else "resource-search-results"
        response["presentation"] = _server_presentation(context.view_id, (module_id,))
        conversation_source = RESOURCE_EXPLORER_SOURCE
        conversation_limitations = "fixture_l0_l1_only,no_real_connector,no_write_operation"
    else:
        result = _run_optic_query(
            scope,
            actor,
            request_id,
            health_filter=health_filter_for_question(payload.question),
        )
        response = dict(ORCHESTRATOR.respond(payload.question, scope, request_id, result))
        raw_context = cast(dict[str, Any], response["view_context"])
        context = REGISTRY.validate_view_context(
            ViewContext(
                str(raw_context["view_id"]),
                str(raw_context["version"]),
                scope,
                cast(dict[str, object], raw_context["filters"]),
                cast(str | None, raw_context["focus_resource_id"]),
                cast(str | None, raw_context["query_id"]),
            ),
            scope,
        )
        _, source_scope = _source_for_capability("optic-health", actor, context.scope, request_id)
        response["view_context"] = _view_dict(
            ViewContext(
                context.view_id,
                context.version,
                source_scope,
                context.filters,
                context.focus_resource_id,
                context.query_id,
            )
        )
        response["presentation"] = _server_presentation(
            OPTIC_VIEW_ID, ("optic-health-overview",)
        )
        conversation_source = result.source
        conversation_limitations = "fixture_l0_l1_only,no_real_connector,no_write_operation"
    if local is not None:
        try:
            conversation_id = LOCAL_IDENTITIES.create_or_append_conversation(
                local,
                payload.conversation_id,
                payload.question,
                str(response["message"]),
                conversation_source,
                conversation_limitations,
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


@app.post("/v1/admin/accounts", status_code=201)
def create_admin_account(payload: AdminAccountCreateInput, request: Request) -> dict[str, object]:
    request_id = _request_id(request)
    identity = _require_admin(request, request_id)
    requested_sites = frozenset(payload.site_ids)
    if not requested_sites.issubset(identity.scope.site_ids):
        _audit(identity.account_id, "admin.account.create", "denied", request_id, identity.scope, reason="scope_site_not_allowed")
        raise HTTPException(403, detail={"code": "scope_site_not_allowed", "request_id": request_id})
    try:
        account = LOCAL_IDENTITIES.create_operator(
            payload.username,
            payload.password,
            payload.display_name,
            Scope(identity.scope.project_id, requested_sites, actions=frozenset({"read"})),
        )
    except IdentityError as exc:
        _audit(identity.account_id, "admin.account.create", "denied", request_id, identity.scope, reason=str(exc))
        raise HTTPException(400, detail={"code": str(exc), "request_id": request_id}) from exc
    _audit(identity.account_id, "admin.account.create", "allowed", request_id, account.scope)
    return {"request_id": request_id, "account": _local_identity_dict(account)}


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
        "runtime": _runtime_dict(identity.scope),
        "monitoring_source_readiness": _monitoring_source_readiness(),
        "persisted_data_source_status": LOCAL_IDENTITIES.list_data_source_status(),
        "read_only": True,
        "configuration_schema": "data-source-registry/1.0.0",
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


def _runtime_dict(scope: Scope | None = None) -> dict[str, object]:
    return {
        "schema_version": RUNTIME_CONFIG.schema_version,
        "declared_environment": RUNTIME_CONFIG.deployment_environment,
        "data_sources": _data_source_states(scope),
    }


def _monitoring_source_readiness() -> list[dict[str, object]]:
    """Return only no-I/O preflight summaries; source secrets are intentionally absent."""
    summaries: list[dict[str, object]] = []
    for source in RUNTIME_CONFIG.sources:
        if source.kind not in {"zabbix", "prometheus"}:
            continue
        result = assess_monitoring_source_preflight(
            source.kind,
            source_declared=source.enabled,
            configuration_declared=False,
            approved_scope_declared=bool(source.visible_site_ids),
            governance_accepted=source.kind == "zabbix",
            live_execution_authorized=False,
        )
        summaries.append({
            "source_id": source.source_id, "source_kind": result.source_kind, "status": result.status,
            "blockers": list(result.blockers), "allowed_operations": list(result.allowed_operations),
        })
    return summaries


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
        "data_source_ids": list(manifest.data_source_ids),
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
