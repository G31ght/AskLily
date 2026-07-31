"""Deterministic P2 optic-health response composer; no model provider is invoked."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict
from typing import Any

from asklily_contracts import Scope, ViewContext
from asklily_domain import OpticHealthQuery


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
