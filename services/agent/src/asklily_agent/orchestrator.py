"""A deterministic P1 response composer; no model or data source is invoked."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict
from typing import Any

from asklily_contracts import Scope, ViewContext


class P1Orchestrator:
    """Produces only the explicit P1 skeleton limitation response."""

    def respond(self, question: str, scope: Scope, request_id: str) -> Mapping[str, Any]:
        context = ViewContext(
            view_id="platform_status",
            version="1.0.0",
            scope=scope,
            filters={},
            query_id=None,
        )
        return {
            "request_id": request_id,
            "message": (
                "P1 平台骨架已就绪，但尚未注册业务能力、真实数据源或模型 Provider；"
                "无法对问题给出业务事实或健康结论。"
            ),
            "question_acknowledged": question,
            "sources": [],
            "view_context": asdict(context),
            "limitations": ["no_business_capability", "no_real_data", "no_model_provider"],
        }
