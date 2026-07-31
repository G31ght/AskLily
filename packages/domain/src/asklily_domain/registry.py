"""Pure registry guards used before any Agent, API, or UI invocation."""

from __future__ import annotations

from dataclasses import dataclass, field

from asklily_contracts import (
    CapabilityManifest,
    ContractViolation,
    Scope,
    ToolContract,
    ViewContext,
    ViewContract,
)


@dataclass
class PlatformRegistry:
    """In-memory registry for the P1 skeleton; it does not execute Tools."""

    tools: dict[str, ToolContract] = field(default_factory=dict)
    views: dict[str, ViewContract] = field(default_factory=dict)
    capabilities: dict[str, CapabilityManifest] = field(default_factory=dict)

    def register_tool(self, contract: ToolContract) -> None:
        if contract.tool_id in self.tools:
            raise ContractViolation("tool_already_registered")
        if not contract.read_only:
            raise ContractViolation("write_tools_not_allowed_in_p1")
        self.tools[contract.tool_id] = contract

    def register_view(self, contract: ViewContract) -> None:
        if not contract.view_id or not contract.version or contract.view_id in self.views:
            raise ContractViolation("view_already_registered_or_invalid")
        self.views[contract.view_id] = contract

    def register_capability(self, manifest: CapabilityManifest) -> None:
        if manifest.capability_id in self.capabilities:
            raise ContractViolation("capability_already_registered")
        unknown_tools = set(manifest.tool_ids) - set(self.tools)
        unknown_views = set(manifest.view_ids) - set(self.views)
        if unknown_tools or unknown_views:
            raise ContractViolation("capability_references_unregistered_contract")
        self.capabilities[manifest.capability_id] = manifest

    def authorize_tool(self, tool_id: str, scope: Scope) -> ToolContract:
        try:
            contract = self.tools[tool_id]
        except KeyError as exc:
            raise ContractViolation("tool_not_registered") from exc
        if contract.required_action not in scope.actions:
            raise ContractViolation("tool_action_not_allowed_by_scope")
        return contract

    def validate_view_context(
        self,
        context: ViewContext,
        server_scope: Scope,
        workspace_modules: tuple[str, ...] = (),
    ) -> ViewContext:
        contract = self.views.get(context.view_id)
        if contract is None:
            raise ContractViolation("view_not_registered")
        if context.version != contract.version:
            raise ContractViolation("view_version_not_registered")
        if not set(context.filters).issubset(contract.allowed_filter_keys):
            raise ContractViolation("view_filter_not_allowed")
        if not set(workspace_modules).issubset(contract.allowed_workspace_modules):
            raise ContractViolation("workspace_module_not_allowed")
        return ViewContext(
            view_id=context.view_id,
            version=context.version,
            scope=server_scope.narrowed_to(context.scope),
            filters=context.filters,
            focus_resource_id=context.focus_resource_id,
            query_id=context.query_id,
        )

    def validate_presentation_modules(self, view_id: str, module_ids: tuple[str, ...]) -> None:
        """Reject any workspace module not registered for the requested View."""
        contract = self.views.get(view_id)
        if contract is None:
            raise ContractViolation("view_not_registered")
        if not set(module_ids).issubset(contract.allowed_workspace_modules):
            raise ContractViolation("workspace_module_not_allowed")
