"""Pydantic contracts shared by all owners (ported from legacy-ts/src/lib/contracts).

Change a contract only through a PR that tags the consumers. Never change silently.
"""

from .agent_key import (
    KeyFailureReason,
    KeyLimits,
    KeyRejected,
    KeyScope,
    KeyVerification,
    KeyVerified,
    VerifiedAgent,
)
from .audit import (
    SCORE_WEIGHTS,
    AuditResult,
    Dimension,
    FixType,
    Issue,
    IssueCode,
    ScoreCheck,
    Severity,
)
from .benchmark import (
    AgentMode,
    AgentRun,
    AgentRunOutcome,
    AgentStep,
    BenchmarkTask,
    ExpectedOutcome,
)
from .common import Contract
from .fix import FixEvidence, FixMethod, FixRecord, FixStatus, FixVersion
from .mcp import (
    STORE_TOOL_NAMES,
    CreateOrderInput,
    GetPolicyInput,
    GetProductInput,
    SearchProductsInput,
)
from .order import (
    GuardedOrderItem,
    GuardedOrderRequest,
    GuardedOrderResult,
    OrderStatus,
)
from .policy import (
    OrderDraft,
    OrderItemDraft,
    PolicyDecision,
    PolicyResult,
    PolicyRules,
    ReasonCode,
)
from .product import Image, Product, Returns, Shipping, Variant
from .quote import Quote, QuoteError, compute_quote_hash
from .run_event import GENESIS_HASH, RunEvent, hash_output

__all__ = [
    "GENESIS_HASH",
    "SCORE_WEIGHTS",
    "STORE_TOOL_NAMES",
    "AgentMode",
    "AgentRun",
    "AgentRunOutcome",
    "AgentStep",
    "AuditResult",
    "BenchmarkTask",
    "Contract",
    "CreateOrderInput",
    "Dimension",
    "ExpectedOutcome",
    "FixEvidence",
    "FixMethod",
    "FixRecord",
    "FixStatus",
    "FixType",
    "FixVersion",
    "GetPolicyInput",
    "GetProductInput",
    "GuardedOrderItem",
    "GuardedOrderRequest",
    "GuardedOrderResult",
    "Image",
    "Issue",
    "IssueCode",
    "KeyFailureReason",
    "KeyLimits",
    "KeyRejected",
    "KeyScope",
    "KeyVerification",
    "KeyVerified",
    "OrderDraft",
    "OrderItemDraft",
    "OrderStatus",
    "PolicyDecision",
    "PolicyResult",
    "PolicyRules",
    "Product",
    "Quote",
    "QuoteError",
    "ReasonCode",
    "Returns",
    "RunEvent",
    "ScoreCheck",
    "SearchProductsInput",
    "Severity",
    "Shipping",
    "Variant",
    "VerifiedAgent",
    "compute_quote_hash",
    "hash_output",
]
