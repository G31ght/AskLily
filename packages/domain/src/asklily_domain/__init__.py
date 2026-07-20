"""P1 platform guards and P2 deterministic domain capabilities."""

from .optic_health import OPTIC_RULE_VERSION, OpticHealthQuery, query_optic_health
from .registry import PlatformRegistry

__all__ = ["OPTIC_RULE_VERSION", "OpticHealthQuery", "PlatformRegistry", "query_optic_health"]
