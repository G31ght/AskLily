"""P1 contract tests use only the Python standard library."""

from __future__ import annotations

import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [
    str(ROOT / "packages" / "contracts" / "src"),
    str(ROOT / "packages" / "domain" / "src"),
]

from asklily_contracts import (  # noqa: E402
    AuditEvent,
    ContractViolation,
    Scope,
    ToolContract,
    ViewContext,
)
from asklily_domain import PlatformRegistry  # noqa: E402


class PlatformContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scope = Scope(
            project_id="demo-project",
            site_ids=frozenset({"site-a"}),
            actions=frozenset({"read"}),
        )
        self.registry = PlatformRegistry()
        self.registry.register_tool(
            ToolContract("platform.status", "1.0.0", "platform", "read", "1.0.0", "1.0.0")
        )
        self.registry.register_view("platform_status")

    def test_scope_cannot_expand_sites_or_actions(self) -> None:
        with self.assertRaisesRegex(ContractViolation, "scope_site_not_allowed"):
            self.scope.narrowed_to(
                Scope("demo-project", frozenset({"site-a", "site-b"}), actions=frozenset({"read"}))
            )
        with self.assertRaisesRegex(ContractViolation, "scope_action_not_allowed"):
            self.scope.narrowed_to(Scope("demo-project", actions=frozenset({"read", "write"})))

    def test_unregistered_tool_and_view_are_rejected(self) -> None:
        with self.assertRaisesRegex(ContractViolation, "tool_not_registered"):
            self.registry.authorize_tool("unknown", self.scope)
        with self.assertRaisesRegex(ContractViolation, "view_not_registered"):
            self.registry.validate_view_context(
                ViewContext("unknown", "1.0.0", self.scope, {}), self.scope
            )

    def test_audit_event_links_request_and_query(self) -> None:
        event = AuditEvent(
            event_id="audit-1",
            occurred_at=datetime.now(UTC),
            actor_id="developer",
            action="tool.authorize",
            outcome="allowed",
            request_id="req-1",
            query_id="query-1",
            scope_project_id="demo-project",
            tool_id="platform.status",
        )
        self.assertEqual(event.request_id, "req-1")
        self.assertEqual(event.query_id, "query-1")


if __name__ == "__main__":
    unittest.main()
