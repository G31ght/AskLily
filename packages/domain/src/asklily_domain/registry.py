"""Pure registry guards used before any Agent, API, or UI invocation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Mapping

from asklily_contracts import CapabilityManifest, ContractViolation, Scope, ToolContract, ViewContext


@dataclass
class PlatformRegistry:
    """In-memory registry for the P1 skeleton; it does not execute Tools."""

    tools: Dict[str, ToolContract] = field(default_factory=dict)
    view_ids: set[str] = field(default_factory=set)
    capabilities: Dict[str, CapabilityManifest] = field(default_factory=dict)

    def register_tool(self, contract: ToolContract) -> None:
        if contract.tool_id in self.tools:
            raise ContractViolation("tool_already_registered")
        if not contract.read_only:
            raise ContractViolation("write_tools_not_allowed_in_p1")
        self.tools[contract.tool_id] = contract

    def register_view(self, view_id: str) -> None:
        if not view_id or view_id in self.view_ids:
            raise ContractViolation("view_already_registered_or_invalid")
        self.view_ids.add(view_id)

    def register_capability(self, manifest: CapabilityManifest) -> None:
        if manifest.capability_id in self.capabilities:
            raise ContractViolation("capability_already_registered")
        unknown_tools = set(manifest.tool_ids) - set(self.tools)
        unknown_views = set(manifest.view_ids) - self.view_ids
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

    def validate_view_context(self, context: ViewContext, server_scope: Scope) -> ViewContext:
        if context.view_id not in self.view_ids:
            raise ContractViolation("view_not_registered")
        return ViewContext(
            view_id=context.view_id,
            version=context.version,
            scope=server_scope.narrowed_to(context.scope),
            filters=context.filters,
            focus_resource_id=context.focus_resource_id,
            query_id=context.query_id,
        )
