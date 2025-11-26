"""
Event-driven architecture for scalable agent execution.
"""

import asyncio
import logging
import os
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """All event types in the system."""

    # Agent lifecycle
    AGENT_START = "agent.start"
    AGENT_STEP = "agent.step"
    AGENT_COMPLETE = "agent.complete"
    AGENT_ERROR = "agent.error"
    AGENT_PAUSED = "agent.paused"
    AGENT_RESUMED = "agent.resumed"

    # LLM events
    LLM_REQUEST = "llm.request"
    LLM_TOKEN = "llm.token"
    LLM_RESPONSE = "llm.response"
    LLM_ERROR = "llm.error"

    # Browser events
    ACTION_START = "action.start"
    ACTION_COMPLETE = "action.complete"
    ACTION_ERROR = "action.error"
    BROWSER_NAVIGATE = "browser.navigate"
    BROWSER_SCREENSHOT = "browser.screenshot"

    # Trace events
    TRACE_SPAN_START = "trace.span.start"
    TRACE_SPAN_END = "trace.span.end"
    TRACE_COMPLETE = "trace.complete"

    # UI events
    UI_CONNECTED = "ui.connected"
    UI_DISCONNECTED = "ui.disconnected"
    UI_COMMAND = "ui.command"

    # Workflow events
    WORKFLOW_NODE_START = "workflow.node.start"
    WORKFLOW_NODE_COMPLETE = "workflow.node.complete"
    WORKFLOW_EDGE_TRAVERSED = "workflow.edge.traversed"


@dataclass
class Event:
    """Base event class."""

    event_type: EventType
    session_id: str
    timestamp: float
    data: dict[str, Any]
    correlation_id: str | None = None  # For tracing related events

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_type": self.event_type.value,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "data": self.data,
            "correlation_id": self.correlation_id,
        }


EventHandler = Callable[[Event], Awaitable[None]]


class EventBus:
    """
    Event bus for publish-subscribe pattern.
    Supports both in-memory and Redis backends.
    """

    def __init__(self, backend: str = "memory"):
        self.backend = backend
        self._subscribers: dict[EventType, set[EventHandler]] = {}
        self._lock = asyncio.Lock()
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._processing_task: asyncio.Task | None = None

        if backend == "redis":
            self._init_redis()

    def _init_redis(self):
        """Initialize Redis pub/sub."""
        try:
            import redis.asyncio as redis  # type: ignore[import-untyped]

            self.redis = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", 6379)),
                decode_responses=True,
            )
            logger.info("Redis event bus initialized")
        except ImportError:
            logger.warning("redis package not installed, falling back to memory")
            self.backend = "memory"
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {e}")
            self.backend = "memory"

    async def subscribe(self, event_type: EventType, handler: EventHandler):
        """Subscribe to an event type."""
        async with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = set()
            self._subscribers[event_type].add(handler)
            logger.debug(f"Subscribed to {event_type.value}")

    async def unsubscribe(self, event_type: EventType, handler: EventHandler):
        """Unsubscribe from an event type."""
        async with self._lock:
            if event_type in self._subscribers:
                self._subscribers[event_type].discard(handler)
                logger.debug(f"Unsubscribed from {event_type.value}")

    async def publish(self, event: Event):
        """Publish an event to all subscribers."""
        logger.debug(f"Publishing {event.event_type.value} for session {event.session_id}")

        if self.backend == "redis":
            await self._publish_redis(event)
        else:
            await self._publish_memory(event)

    async def _publish_memory(self, event: Event):
        """Publish to in-memory subscribers."""
        if event.event_type in self._subscribers:
            handlers = list(self._subscribers[event.event_type])

            # Call handlers concurrently
            await asyncio.gather(
                *[self._safe_handle(handler, event) for handler in handlers],
                return_exceptions=True,
            )

    async def _publish_redis(self, event: Event):
        """Publish to Redis pub/sub."""
        import json

        channel = f"events:{event.event_type.value}"
        message = json.dumps(event.to_dict())

        try:
            await self.redis.publish(channel, message)
        except Exception as e:
            logger.error(f"Failed to publish to Redis: {e}")

    async def _safe_handle(self, handler: EventHandler, event: Event):
        """Call handler with error handling."""
        try:
            await handler(event)
        except Exception as e:
            logger.error(f"Error in event handler for {event.event_type.value}: {e}", exc_info=True)

    async def start_processing(self):
        """Start background event processing."""
        if self._processing_task is None:
            self._processing_task = asyncio.create_task(self._process_events())
            logger.info("Event bus processing started")

    async def stop_processing(self):
        """Stop background event processing."""
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
            self._processing_task = None
            logger.info("Event bus processing stopped")

    async def _process_events(self):
        """Process events from queue."""
        while True:
            try:
                event = await self._event_queue.get()
                await self.publish(event)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing event: {e}")

    async def close(self):
        """Clean up resources."""
        await self.stop_processing()

        if self.backend == "redis" and hasattr(self, "redis"):
            await self.redis.close()
            logger.info("Redis connection closed")


# Global event bus instance
_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        backend = os.getenv("EVENT_BUS_BACKEND", "memory")
        _event_bus = EventBus(backend=backend)
    return _event_bus


def create_event(
    event_type: EventType,
    session_id: str,
    data: dict[str, Any],
    correlation_id: str | None = None,
) -> Event:
    """Helper to create an event with current timestamp."""
    return Event(
        event_type=event_type,
        session_id=session_id,
        timestamp=time.time(),
        data=data,
        correlation_id=correlation_id,
    )
