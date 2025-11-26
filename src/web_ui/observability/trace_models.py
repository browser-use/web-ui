"""
Observability and tracing data structures for agent execution.
"""

import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class SpanType(str, Enum):
    """Types of execution spans."""

    AGENT_RUN = "agent_run"
    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"
    BROWSER_ACTION = "browser_action"
    RETRIEVAL = "retrieval"


@dataclass
class TraceSpan:
    """A single span in the execution trace."""

    span_id: str
    parent_id: str | None
    span_type: SpanType
    name: str
    start_time: float
    end_time: float | None = None
    duration_ms: float | None = None

    # Inputs & Outputs
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)

    # LLM-specific
    model_name: str | None = None
    tokens_input: int | None = None
    tokens_output: int | None = None
    cost_usd: float | None = None

    # Status
    status: str = "running"  # running, completed, error
    error: str | None = None

    def complete(self, outputs: dict[str, Any] | None = None):
        """Mark span as completed."""
        self.end_time = time.time()
        if self.start_time:
            self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = "completed"
        if outputs:
            self.outputs = outputs

    def error_out(self, error: Exception):
        """Mark span as error."""
        self.end_time = time.time()
        if self.start_time:
            self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = "error"
        self.error = str(error)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)


@dataclass
class ExecutionTrace:
    """Complete execution trace with all spans."""

    trace_id: str
    session_id: str
    task: str
    start_time: float
    end_time: float | None = None

    spans: list[TraceSpan] = field(default_factory=list)

    # Aggregated metrics
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    llm_calls: int = 0
    actions_executed: int = 0

    # Outcome
    success: bool = False
    final_output: Any = None
    error: str | None = None

    def add_span(self, span: TraceSpan):
        """Add a span to the trace."""
        self.spans.append(span)

        # Update aggregated metrics
        if span.tokens_input:
            self.total_tokens += span.tokens_input
        if span.tokens_output:
            self.total_tokens += span.tokens_output
        if span.cost_usd:
            self.total_cost_usd += span.cost_usd
        if span.span_type == SpanType.LLM_CALL:
            self.llm_calls += 1
        if span.span_type == SpanType.BROWSER_ACTION:
            self.actions_executed += 1

    def get_duration_ms(self) -> float:
        """Get total trace duration."""
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return (time.time() - self.start_time) * 1000

    def get_duration_seconds(self) -> float:
        """Get total trace duration in seconds."""
        return self.get_duration_ms() / 1000

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "task": self.task,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.get_duration_ms(),
            "spans": [span.to_dict() for span in self.spans],
            "total_tokens": self.total_tokens,
            "total_cost_usd": self.total_cost_usd,
            "llm_calls": self.llm_calls,
            "actions_executed": self.actions_executed,
            "success": self.success,
            "final_output": str(self.final_output) if self.final_output else None,
            "error": self.error,
        }

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of the trace."""
        return {
            "trace_id": self.trace_id,
            "task": self.task,
            "duration_seconds": round(self.get_duration_seconds(), 2),
            "total_spans": len(self.spans),
            "llm_calls": self.llm_calls,
            "actions_executed": self.actions_executed,
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost_usd, 4),
            "success": self.success,
            "timestamp": datetime.fromtimestamp(self.start_time).isoformat(),
        }

    def get_llm_spans(self) -> list[TraceSpan]:
        """Get all LLM call spans."""
        return [span for span in self.spans if span.span_type == SpanType.LLM_CALL]

    def get_action_spans(self) -> list[TraceSpan]:
        """Get all browser action spans."""
        return [span for span in self.spans if span.span_type == SpanType.BROWSER_ACTION]

    def get_failed_spans(self) -> list[TraceSpan]:
        """Get all failed spans."""
        return [span for span in self.spans if span.status == "error"]
