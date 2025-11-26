"""
Agent tracer for execution observability.
"""

import logging
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from src.web_ui.observability.trace_models import ExecutionTrace, SpanType, TraceSpan

logger = logging.getLogger(__name__)


class AgentTracer:
    """Tracer for agent execution with span management."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.current_trace: ExecutionTrace | None = None
        self.span_stack: list[TraceSpan] = []  # Stack for nested spans

    def start_trace(self, task: str) -> ExecutionTrace:
        """Start a new trace."""
        import time

        trace_id = str(uuid.uuid4())
        self.current_trace = ExecutionTrace(
            trace_id=trace_id, session_id=self.session_id, task=task, start_time=time.time()
        )
        logger.info(f"Started trace {trace_id} for task: {task[:50]}")
        return self.current_trace

    def end_trace(self, success: bool, final_output: Any = None, error: str | None = None):
        """End the current trace."""
        import time

        if self.current_trace:
            self.current_trace.end_time = time.time()
            self.current_trace.success = success
            self.current_trace.final_output = final_output
            self.current_trace.error = error

            duration = self.current_trace.get_duration_seconds()
            logger.info(
                f"Ended trace {self.current_trace.trace_id} | "
                f"Success: {success} | "
                f"Duration: {duration:.2f}s | "
                f"Cost: ${self.current_trace.total_cost_usd:.4f}"
            )

    @asynccontextmanager
    async def span(
        self, name: str, span_type: SpanType, inputs: dict[str, Any] | None = None, **metadata
    ) -> AsyncGenerator[TraceSpan]:
        """Context manager for creating spans."""
        import time

        # Create span
        span_id = str(uuid.uuid4())
        parent_id = self.span_stack[-1].span_id if self.span_stack else None

        span = TraceSpan(
            span_id=span_id,
            parent_id=parent_id,
            span_type=span_type,
            name=name,
            start_time=time.time(),
            inputs=inputs or {},
            metadata=metadata,
        )

        # Push to stack
        self.span_stack.append(span)

        # Add to trace
        if self.current_trace:
            self.current_trace.add_span(span)

        logger.debug(f"Started span: {name} ({span_type.value})")

        try:
            yield span
            span.complete()
            logger.debug(f"Completed span: {name} in {span.duration_ms:.0f}ms")
        except Exception as e:
            span.error_out(e)
            logger.error(f"Span {name} failed with error: {e}")
            raise
        finally:
            # Pop from stack
            if self.span_stack and self.span_stack[-1].span_id == span_id:
                self.span_stack.pop()

    def get_current_trace(self) -> ExecutionTrace | None:
        """Get the current trace."""
        return self.current_trace

    def get_current_span(self) -> TraceSpan | None:
        """Get the current (top-level) span."""
        return self.span_stack[-1] if self.span_stack else None
