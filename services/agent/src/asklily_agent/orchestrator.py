"""Deterministic P2 optic-health response composer; no model provider is invoked."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

from asklily_contracts import Scope, ViewContext
from asklily_domain import OpticHealthQuery


@dataclass(frozen=True)
class ResourceExplorerIntent:
    """Small server-owned intent surface for the Fixture directory."""

    response_kind: str
    query: str | None = None
    site_id: str | None = None
    resource_type: str | None = None
    health: frozenset[str] = frozenset()
    focus_resource_id: str | None = None


class OpticHealthOrchestrator:
    """Turns authorized Fixture query evidence into a constrained Chat response."""

    def respond(self, question: str, scope: Scope, request_id: str, result: OpticHealthQuery) -> Mapping[str, Any]:
        health_filter = _health_filter(question)
        focus_resource_id = result.records[0].resource.resource_id if len(result.records) == 1 else None
        context = ViewContext(
            view_id="optic_health",
            version="1.0.0",
            scope=scope,
            filters={
                "health": sorted(health_filter),
                "time_range": {
                    "from": result.observed_from.isoformat(),
                    "to": result.observed_to.isoformat(),
                },
            },
            focus_resource_id=focus_resource_id,
            query_id=f"fixture-query:{request_id}",
        )
        summary = "、".join(f"{health} {count}" for health, count in sorted(result.summary.items())) or "无匹配资源"
        return {
            "request_id": request_id,
            "response_kind": "optic_health",
            "message": (
                f"已调用受授权的 optic_health.query：在站点 {', '.join(sorted(scope.site_ids)) or '全部授权站点'} "
                f"内得到 {summary}。来源为固定 Fixture，观测范围为 "
                f"{result.observed_from.isoformat()} 至 {result.observed_to.isoformat()}；"
                f"规则版本 {result.rule_version}。"
            ),
            "question_acknowledged": question,
            "sources": [result.source],
            "view_context": asdict(context),
            "limitations": ["fixture_l0_l1_only", "no_real_connector", "no_write_operation"],
            "optic_health": _query_dict(result),
        }


class CapabilityCatalogOrchestrator:
    """Compose the catalog-only Chat response after server authorization."""

    def respond(
        self,
        question: str,
        request_id: str,
        catalog: Mapping[str, Any],
        view_context: Mapping[str, Any],
        presentation: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        entries = catalog["capabilities"]
        ready = sum(1 for item in entries if item["status"]["code"] == "ready")
        return {
            "request_id": request_id,
            "response_kind": "capability_catalog",
            "message": f"当前可见能力 {len(entries)} 项，其中可用 {ready} 项。目录仅展示已注册、只读且在你的 Scope 内的信息。",
            "question_acknowledged": question,
            "sources": ["capability-catalog"],
            "catalog": catalog,
            "view_context": view_context,
            "presentation": presentation,
            "limitations": ["read_only", "no_real_connector", "no_write_operation"],
        }


class ResourceExplorerOrchestrator:
    """Compose legal P5G workspace contexts without accepting client components."""

    def respond(self, question: str, scope: Scope, request_id: str, intent: ResourceExplorerIntent) -> Mapping[str, Any]:
        if intent.response_kind == "resource_detail":
            context = ViewContext(
                view_id="resource_detail",
                version="1.0.0",
                scope=scope,
                filters={},
                focus_resource_id=intent.focus_resource_id,
                query_id=f"fixture-resource:{request_id}",
            )
            message = "已打开受授权的 Fixture 资源详情。详细信息仅限当前 Scope，且不包含原始监控事实。"
        else:
            filters: dict[str, Any] = {"page": 1}
            if intent.query is not None:
                filters["query"] = intent.query
            if intent.site_id is not None:
                filters["site_id"] = intent.site_id
            if intent.resource_type is not None:
                filters["resource_type"] = intent.resource_type
            if intent.health:
                filters["health"] = [
                    value for value in ("critical", "warning", "unknown", "recovered", "healthy") if value in intent.health
                ]
            context = ViewContext(
                view_id="resource_search",
                version="1.0.0",
                scope=scope,
                filters=filters,
                query_id=f"fixture-resource:{request_id}",
            )
            message = "已准备受授权的 Fixture 资源检索。工作台会仅在当前 Scope 内请求分页后的结构化摘要。"
        return {
            "request_id": request_id,
            "response_kind": intent.response_kind,
            "message": message,
            "question_acknowledged": question,
            "sources": ["fixture://resource-explorer/l0-l1-v1"],
            "view_context": asdict(context),
            "limitations": ["fixture_l0_l1_only", "no_real_connector", "no_write_operation"],
        }


def health_filter_for_question(question: str) -> frozenset[str]:
    """Map only explicit P2 demo terms to registered health states."""

    return _health_filter(question)


def is_capability_catalog_question(question: str) -> bool:
    """Recognize only the approved deterministic catalog intents before optic routing."""
    normalized = question.casefold()
    asks_what_is_available = any(token in normalized for token in ("能做什么", "可以做什么", "有哪些能力", "能力中心"))
    asks_optic_source = "光模块" in normalized and any(token in normalized for token in ("来源", "数据来自", "数据从哪", "哪里来"))
    asks_monitoring_explanation = any(token in normalized for token in ("zabbix", "prometheus")) and any(
        token in normalized for token in ("为什么", "为何", "不能", "不可", "查询不了")
    )
    return asks_what_is_available or asks_optic_source or asks_monitoring_explanation


def resource_explorer_intent(question: str) -> ResourceExplorerIntent | None:
    """Recognize only the three approved directory phrases before optic routing.

    The parser intentionally maps no general language, regex, URL, path, or
    cross-project syntax into a directory query.
    """
    normalized = " ".join(question.casefold().split())
    if not normalized:
        return None
    focus = re.search(r"(?:打开|open)\s+([a-z0-9-]+)", normalized)
    if focus is not None:
        return ResourceExplorerIntent("resource_detail", focus_resource_id=focus.group(1))
    if "site-a" in normalized and "光模块" in question and any(token in normalized for token in ("异常", "告警")):
        return ResourceExplorerIntent(
            "resource_search",
            site_id="site-a",
            resource_type="optic_module",
            health=frozenset({"critical", "warning", "unknown"}),
        )
    if normalized in {"检索当前可见资源", "查询当前可见资源", "搜索当前可见资源"}:
        return ResourceExplorerIntent("resource_search")
    marker = next((item for item in ("查询", "搜索", "检索", "查 ", "搜 ") if item in normalized), None)
    if marker is None:
        return None
    candidate = normalized.split(marker, 1)[1].strip(" ：:")
    if not candidate or len(candidate) > 100 or not re.fullmatch(r"[\w\s\-/.]+", candidate, re.UNICODE):
        return None
    return ResourceExplorerIntent("resource_search", query=candidate)


def _health_filter(question: str) -> frozenset[str]:
    if "恢复" in question:
        return frozenset({"recovered"})
    if "缺失" in question or "未知" in question:
        return frozenset({"unknown"})
    if "温度" in question:
        return frozenset({"warning"})
    if "RX" in question.upper() or "接收" in question:
        return frozenset({"critical"})
    if "TX" in question.upper() or "发送" in question:
        return frozenset({"critical"})
    if "异常" in question or "告警" in question or "健康" in question:
        return frozenset({"critical", "warning", "unknown"})
    return frozenset()


def _query_dict(result: OpticHealthQuery) -> dict[str, Any]:
    return {
        "summary": result.summary,
        "source": result.source,
        "observed_from": result.observed_from.isoformat(),
        "observed_to": result.observed_to.isoformat(),
        "rule_version": result.rule_version,
        "records": [
            {
                "resource": asdict(record.resource),
                "latest_observation": {
                    **asdict(record.latest_observation),
                    "observed_at": record.latest_observation.observed_at.isoformat(),
                },
                "assessment": {
                    **asdict(record.assessment),
                    "evaluated_at": record.assessment.evaluated_at.isoformat(),
                },
                "event": None
                if record.event is None
                else {
                    **asdict(record.event),
                    "first_seen_at": record.event.first_seen_at.isoformat(),
                    "last_seen_at": record.event.last_seen_at.isoformat(),
                },
            }
            for record in result.records
        ],
    }
