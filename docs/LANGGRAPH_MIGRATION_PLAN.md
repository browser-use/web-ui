# LangGraph Migration Plan: BrowserUseAgent Enhancement

**Status:** Planning Phase
**Target Timeline:** 8 weeks (with 30% buffer)
**Priority:** High - Foundation for improved reliability and state management
**Last Updated:** October 22, 2025

---

## Executive Summary

This plan outlines the migration of `BrowserUseAgent` to a LangGraph-based architecture, enabling:

- **State persistence** via checkpointing (resume interrupted sessions)
- **Memory management** (conversation trimming, session summaries)
- **Streaming updates** (real-time UI feedback)
- **Error recovery** (smart retry with context-aware strategies)
- **Observability** (detailed tracing and cost tracking)

**Approach:** Gradual migration with feature flag, preserving legacy agent as fallback.

**Key Success Metrics:**

- 95%+ parity with legacy agent (success rate, output quality)
- <500ms checkpoint write time
- <2s resume time from checkpoint
- +20% performance overhead acceptable
- 100% resumability (no data loss on crash)

---

## Current State Analysis

### Architecture Overview

```
Current: BrowserUseAgent (browser-use lib)
├── Simple for loop: range(max_steps)
├── No state persistence
├── No memory management
└── Limited error recovery

Existing Infrastructure:
├── DeepResearchAgent (already uses LangGraph) ✅
├── EventBus (pub/sub pattern) ✅
├── AgentTracer (observability) ✅
├── CostCalculator (token/cost tracking) ✅
└── WorkflowGraphBuilder (visualization) ✅
```

### Gaps Identified

| Gap | Impact | Priority |
|-----|--------|----------|
| No checkpointing | Can't resume after crash/interruption | 🔴 High |
| No memory management | Context window overflow on long tasks | 🔴 High |
| Limited streaming | Poor UI responsiveness | 🟡 Medium |
| Basic retry logic | Fails unnecessarily on transient errors | 🟡 Medium |
| Incomplete observability | Hard to debug failures | 🟢 Low |

---

## Proposed Architecture

### High-Level Design

```
LangGraphBrowserAgent
├── StateGraph (LangGraph)
│   ├── planning_node: Analyze task, create sub-plan
│   ├── action_node: Execute browser actions (wrapped browser-use)
│   ├── observation_node: Extract results, update state
│   ├── decision_node: Determine next action or completion
│   └── synthesis_node: Aggregate final results
├── SqliteSaver (checkpointing)
│   ├── Auto-checkpoint at critical nodes
│   ├── WAL mode for Windows compatibility
│   └── Multi-checkpoint fallback (last 3)
├── MemoryManager
│   ├── Hot: In-memory (last N messages, token-aware)
│   ├── Warm: SQLite summaries (periodic condensation)
│   └── Cold: Historical episodes (defer vector store)
├── RetryPolicy
│   ├── Error classification (navigation, element, network)
│   ├── Strategy-based retry (different approach per error)
│   └── Exponential backoff with max attempts
└── StreamingAdapter
    ├── EventBus integration
    ├── Backpressure handling (bounded buffer)
    └── Node lifecycle events
```

### State Definition

```python
from typing import TypedDict, Optional
from langchain_core.messages import BaseMessage

class BrowserAgentState(TypedDict):
    """Complete agent state (checkpointed)."""
    # Core task info
    task: str
    task_id: str
    session_id: str

    # Conversation history (managed by MemoryManager)
    messages: list[BaseMessage]
    message_summary: Optional[str]  # Condensed history

    # Execution state
    current_step: int
    max_steps: int
    actions_taken: list[dict]  # History of actions

    # Browser state (minimal, avoid bloat)
    current_url: str
    current_page_title: str
    browser_context_id: str  # Reference, not full context

    # Error tracking
    failures: int
    consecutive_failures: int
    last_error: Optional[str]

    # Control flags
    paused: bool
    stopped: bool
    completed: bool

    # Observability
    trace_id: str
    start_time: float
    checkpoint_count: int
```

---

## Implementation Plan

### Phase 1: Foundation (Week 1-2) - MUST HAVE

**Goal:** MVP with checkpointing and basic workflow

**Deliverables:**

- [ ] Feature flag system (`USE_LANGGRAPH_AGENT=false` default)
- [ ] `BrowserAgentState` TypedDict
- [ ] Basic workflow: `START → plan → act → observe → decide → END`
- [ ] SqliteSaver with Windows optimizations (WAL, timeout, backoff)
- [ ] Adapter wrapping browser-use Agent in LangGraph nodes
- [ ] Unit tests for state transitions

**Technical Details:**

```python
# config.py
from pydantic import BaseModel

class BrowserAgentConfig(BaseModel):
    use_langgraph: bool = False  # Feature flag
    checkpoint_enabled: bool = True
    checkpoint_db_path: str = "./tmp/checkpoints/browser_agent.db"
    checkpoint_timeout: int = 30  # seconds
    max_checkpoints_to_keep: int = 3

# adapter.py
class BrowserUseAdapter:
    """Wraps browser-use Agent methods for LangGraph nodes."""

    def __init__(self, browser_use_agent):
        self.agent = browser_use_agent

    async def plan(self, state: BrowserAgentState) -> dict:
        """Planning node: analyze task, create action plan."""
        # Use browser-use agent's planning logic
        pass

    async def act(self, state: BrowserAgentState) -> dict:
        """Action node: execute browser actions."""
        # Delegate to browser-use agent's step() method
        pass

    async def observe(self, state: BrowserAgentState) -> dict:
        """Observation node: extract results."""
        pass

    async def decide(self, state: BrowserAgentState) -> str:
        """Decision node: determine next action."""
        # Return: "act" | "end" | "error"
        pass
```

**Windows SQLite Setup:**

```python
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3

def create_checkpointer(db_path: str) -> SqliteSaver:
    """Create SQLite checkpointer with Windows optimizations."""
    conn = sqlite3.connect(
        db_path,
        timeout=30.0,  # 30s timeout for locks
        check_same_thread=False
    )

    # Enable WAL mode for better concurrency
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")  # Balance safety/speed
    conn.execute("PRAGMA cache_size=-64000")  # 64MB cache

    return SqliteSaver(conn)
```

**Exit Criteria:**

- ✅ Basic workflow runs end-to-end
- ✅ Checkpoint created after each node
- ✅ Resume from checkpoint works (manual test)
- ✅ Feature flag switches between implementations
- ✅ No regressions in legacy agent

---

### Phase 2: Parity & Testing (Week 2-3) - MUST HAVE

**Goal:** Achieve feature parity with legacy agent

**Deliverables:**

- [ ] All workflow nodes implemented (plan, act, observe, decide)
- [ ] Conditional edges (`should_continue`, `should_retry`)
- [ ] Integration test suite (20+ tasks, legacy vs LangGraph)
- [ ] Checkpoint at critical nodes (planning, synthesis)
- [ ] Basic streaming via EventBus
- [ ] Performance baseline measurements

**Integration Test Strategy:**

```python
# tests/test_langgraph_parity.py
import pytest

TEST_TASKS = [
    "Navigate to google.com and search for 'LangGraph'",
    "Find the price of iPhone 15 on apple.com",
    "Fill out contact form on example.com",
    # ... 17 more real-world tasks
]

@pytest.mark.asyncio
async def test_parity_success_rate():
    """Verify LangGraph agent matches legacy success rate."""
    legacy_results = await run_legacy_agent(TEST_TASKS)
    langgraph_results = await run_langgraph_agent(TEST_TASKS)

    assert langgraph_results.success_rate >= legacy_results.success_rate * 0.95

@pytest.mark.asyncio
async def test_parity_output_quality():
    """Verify outputs are equivalent (semantic comparison)."""
    # Compare final results, allowing for different action paths
    pass

@pytest.mark.asyncio
async def test_checkpoint_resumability():
    """Test resume from every possible checkpoint."""
    for checkpoint_node in ["plan", "act", "observe", "decide"]:
        # Kill process at checkpoint_node, resume, verify completion
        pass
```

**Streaming Integration:**

```python
# streaming/adapters.py
from src.web_ui.events.event_bus import get_event_bus, EventType, create_event

async def stream_node_events(app, state, config):
    """Stream LangGraph events through EventBus."""
    event_bus = get_event_bus()

    async for event in app.astream(state, config):
        node_name = list(event.keys())[0]
        node_data = event[node_name]

        # Publish to EventBus
        await event_bus.publish(create_event(
            event_type=EventType.WORKFLOW_NODE_START,
            session_id=state["session_id"],
            data={
                "node": node_name,
                "state": node_data,
                "timestamp": time.time()
            }
        ))

        yield event
```

**Exit Criteria:**

- ✅ 95%+ success rate parity with legacy
- ✅ Output quality equivalent (manual review)
- ✅ Resume works from any checkpoint (100% success)
- ✅ Performance within +20% of baseline
- ✅ Streaming events render in UI

---

### Phase 3: Memory Management (Week 3-4) - SHOULD HAVE

**Goal:** Add smart memory management to prevent context overflow

**Deliverables:**

- [ ] Hot memory with token-aware trimming (tiktoken)
- [ ] Configurable limits (max tokens: 8000, max messages: 50)
- [ ] Template-based session summaries (no LLM, cost-free)
- [ ] MemoryManager interface
- [ ] Memory tests (trimming, token counting, context preservation)
- [ ] Integration with planning node

**Memory Implementation:**

```python
# memory/manager.py
import tiktoken
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage

class MemoryManager:
    """Unified memory management interface."""

    def __init__(
        self,
        max_tokens: int = 8000,
        max_messages: int = 50,
        model_name: str = "gpt-4"
    ):
        self.max_tokens = max_tokens
        self.max_messages = max_messages
        self.tokenizer = tiktoken.encoding_for_model(model_name)
        self.hot_memory: list[BaseMessage] = []
        self.summary: str = ""

    def add_message(self, message: BaseMessage):
        """Add message, trim if needed."""
        self.hot_memory.append(message)

        if self._should_trim():
            self._trim_memory()

    def _should_trim(self) -> bool:
        """Check if trimming is needed."""
        if len(self.hot_memory) > self.max_messages:
            return True

        total_tokens = sum(
            len(self.tokenizer.encode(msg.content))
            for msg in self.hot_memory
        )
        return total_tokens > self.max_tokens

    def _trim_memory(self):
        """Trim oldest messages, preserve system + recent."""
        # Keep system message (first)
        system_msgs = [m for m in self.hot_memory if isinstance(m, SystemMessage)]

        # Keep last N messages
        recent_msgs = self.hot_memory[-30:]

        # Create summary of trimmed messages
        trimmed = self.hot_memory[len(system_msgs):-30]
        if trimmed:
            self.summary = self._create_summary(trimmed)

        # Update hot memory
        self.hot_memory = system_msgs + recent_msgs

    def _create_summary(self, messages: list[BaseMessage]) -> str:
        """Create template-based summary (no LLM)."""
        action_count = sum(1 for m in messages if "action" in m.content.lower())
        error_count = sum(1 for m in messages if "error" in m.content.lower())

        return f"Previous context: {len(messages)} messages, {action_count} actions taken, {error_count} errors encountered."

    def get_context(self) -> list[BaseMessage]:
        """Get current context for LLM."""
        if self.summary:
            # Prepend summary as system message
            summary_msg = SystemMessage(content=f"Summary: {self.summary}")
            return [summary_msg] + self.hot_memory
        return self.hot_memory
```

**Exit Criteria:**

- ✅ Trimming works correctly (preserves important messages)
- ✅ Token counting accurate across models
- ✅ Summary generation fast (<10ms)
- ✅ No loss of critical context
- ✅ Memory tests pass (100% coverage)

---

### Phase 4: Reliability & Error Recovery (Week 4-5) - SHOULD HAVE

**Goal:** Add intelligent retry and error recovery

**Deliverables:**

- [ ] Retry policies (exponential backoff, max attempts)
- [ ] Error classification (navigation, element, network, JS)
- [ ] Strategy-based retry (different approach per error type)
- [ ] Observability integration (AgentTracer spans per node)
- [ ] Performance profiling and optimization
- [ ] Load testing (100 concurrent tasks)

**Retry Implementation:**

```python
# retry/policies.py
from enum import Enum
import asyncio

class BrowserErrorType(Enum):
    NAVIGATION_TIMEOUT = "navigation_timeout"
    ELEMENT_NOT_FOUND = "element_not_found"
    STALE_ELEMENT = "stale_element"
    NETWORK_ERROR = "network_error"
    JAVASCRIPT_ERROR = "javascript_error"

class RetryPolicy:
    """Context-aware retry strategies."""

    STRATEGIES = {
        BrowserErrorType.NAVIGATION_TIMEOUT: [
            {"action": "increase_timeout", "timeout": 60},
            {"action": "refresh_page"},
            {"action": "new_context"}
        ],
        BrowserErrorType.ELEMENT_NOT_FOUND: [
            {"action": "wait_longer", "wait": 10},
            {"action": "search_by_text"},
            {"action": "relaxed_selector"}
        ],
        # ... more strategies
    }

    MAX_ATTEMPTS = {
        BrowserErrorType.NAVIGATION_TIMEOUT: 3,
        BrowserErrorType.ELEMENT_NOT_FOUND: 5,
        BrowserErrorType.STALE_ELEMENT: 3,
        BrowserErrorType.NETWORK_ERROR: 4,
    }

    async def retry_with_backoff(
        self,
        func,
        error_type: BrowserErrorType,
        max_attempts: int = None
    ):
        """Execute function with retry and exponential backoff."""
        max_attempts = max_attempts or self.MAX_ATTEMPTS.get(error_type, 3)

        for attempt in range(max_attempts):
            try:
                return await func()
            except Exception as e:
                if attempt >= max_attempts - 1:
                    raise

                # Get retry strategy
                strategy = self._get_strategy(error_type, attempt)

                # Apply strategy
                await self._apply_strategy(strategy)

                # Exponential backoff
                wait_time = min(2 ** attempt, 30)  # Cap at 30s
                await asyncio.sleep(wait_time)

    def _get_strategy(self, error_type: BrowserErrorType, attempt: int) -> dict:
        """Get retry strategy for error type and attempt."""
        strategies = self.STRATEGIES.get(error_type, [])
        if not strategies:
            return {"action": "exponential_backoff"}

        idx = min(attempt, len(strategies) - 1)
        return strategies[idx]

    async def _apply_strategy(self, strategy: dict):
        """Apply retry strategy."""
        action = strategy.get("action")

        if action == "increase_timeout":
            self.current_timeout = strategy.get("timeout", 60)
        elif action == "wait_longer":
            wait = strategy.get("wait", 10)
            await asyncio.sleep(wait)
        # ... more strategy implementations
```

**Observability Integration:**

```python
# Integration with AgentTracer
from src.web_ui.observability.tracer import AgentTracer
from src.web_ui.observability.trace_models import SpanType

class LangGraphTracerIntegration:
    """Attach tracing to LangGraph nodes."""

    def __init__(self, session_id: str):
        self.tracer = AgentTracer(session_id)

    async def trace_node(self, node_name: str, node_func, state: dict):
        """Wrap node execution with tracing."""
        async with self.tracer.span(
            name=f"node:{node_name}",
            span_type=SpanType.AGENT_NODE,
            inputs={"state_keys": list(state.keys())}
        ) as span:
            result = await node_func(state)

            # Add cost if available
            if "cost" in result:
                span.metadata["cost_usd"] = result["cost"]
            if "tokens" in result:
                span.metadata["tokens"] = result["tokens"]

            return result
```

**Exit Criteria:**

- ✅ Retry reduces failure rate by >30%
- ✅ Error classification >90% accurate
- ✅ Strategy switching works correctly
- ✅ Tracing captures all node executions
- ✅ Cost tracking accurate within 5%
- ✅ Load test: 100 concurrent tasks complete

---

### Phase 5: Optimization & Polish (Week 5-6) - COULD HAVE

**Goal:** Optimize performance and add nice-to-have features

**Deliverables:**

- [ ] Optimize checkpoint frequency (smart strategy)
- [ ] LLM-based summarization (optional, configurable)
- [ ] Advanced error recovery
- [ ] Result caching (for idempotent actions)
- [ ] Enhanced telemetry dashboards

**Checkpoint Optimization:**

```python
# checkpointing/strategy.py
class CheckpointStrategy:
    """Smart checkpointing to minimize I/O."""

    def __init__(self):
        self.last_checkpoint_time = 0
        self.last_checkpoint_action_count = 0

    def should_checkpoint(
        self,
        node_name: str,
        state: dict,
        current_time: float
    ) -> bool:
        """Determine if checkpoint is needed."""

        # 1. Critical nodes (always checkpoint)
        if node_name in ["planning_node", "synthesis_node"]:
            return True

        # 2. Time-based (every 30s)
        if current_time - self.last_checkpoint_time > 30:
            return True

        # 3. Action-based (every 5 actions)
        actions = state.get("actions_taken", [])
        if len(actions) - self.last_checkpoint_action_count >= 5:
            return True

        # 4. Before expensive operations
        if node_name in ["navigate_node", "download_node"]:
            return True

        # 5. After errors (for recovery)
        if state.get("last_error"):
            return True

        return False

    def on_checkpoint(self, state: dict, current_time: float):
        """Update tracking after checkpoint."""
        self.last_checkpoint_time = current_time
        self.last_checkpoint_action_count = len(state.get("actions_taken", []))
```

**Exit Criteria:**

- ✅ Checkpoint frequency reduced by 50% (smart strategy)
- ✅ Performance within +10% of baseline (improved from +20%)
- ✅ Optional features configurable via flags
- ✅ Telemetry dashboards functional

---

### Phase 6: Production Readiness (Week 6-8) - NICE TO HAVE

**Goal:** Prepare for production rollout

**Deliverables:**

- [ ] Comprehensive documentation (architecture, API, troubleshooting)
- [ ] Migration guide for users
- [ ] Monitoring alerts and dashboards
- [ ] Performance benchmarks published
- [ ] Gradual rollout plan (10% → 50% → 100%)
- [ ] Rollback procedures documented

**Exit Criteria:**

- ✅ Documentation complete and reviewed
- ✅ All tests passing (unit, integration, performance)
- ✅ Production monitoring configured
- ✅ Rollback tested successfully
- ✅ Team trained on new architecture

---

## Technical Specifications

### File Structure

```
src/web_ui/agent/browser_use/
├── browser_use_agent.py         # Legacy (keep as fallback)
├── config.py                    # NEW: Feature flags
├── langgraph/                   # NEW: LangGraph implementation
│   ├── __init__.py
│   ├── agent.py                 # Main LangGraphBrowserAgent
│   ├── state.py                 # State TypedDicts
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── planning.py         # Task analysis
│   │   ├── action.py           # Browser actions
│   │   ├── observation.py      # Result extraction
│   │   └── decision.py         # Next action logic
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── manager.py          # MemoryManager
│   │   ├── hot.py              # Hot memory (in-memory)
│   │   └── warm.py             # Warm memory (SQLite)
│   ├── checkpointing/
│   │   ├── __init__.py
│   │   ├── saver.py            # SqliteSaver wrapper
│   │   └── strategy.py         # Checkpoint policies
│   ├── retry/
│   │   ├── __init__.py
│   │   ├── policies.py         # Retry strategies
│   │   ├── backoff.py          # Backoff algorithms
│   │   └── classifiers.py      # Error classification
│   └── streaming/
│       ├── __init__.py
│       ├── events.py           # Event schemas
│       └── adapters.py         # EventBus integration
└── utils/
    ├── __init__.py
    ├── adapter.py              # browser-use wrapper
    └── validators.py           # State validation

tests/
├── test_langgraph_agent.py     # Unit tests
├── test_parity.py              # Integration tests
├── test_checkpointing.py       # Checkpoint tests
├── test_memory.py              # Memory tests
└── test_performance.py         # Performance benchmarks
```

### Dependencies

```toml
[dependencies]
# Already installed
langgraph = ">=0.3.34"
langchain-community = ">=0.3.0"
browser-use = "==0.1.48"  # Version pin

# New dependencies
tiktoken = ">=0.7.0"      # Token counting
sqlalchemy = ">=2.0.0"    # For SqliteSaver

# Optional (defer)
chromadb = ">=0.5.0"      # Vector store (Phase 6+)
```

### Configuration

```python
# .env additions
USE_LANGGRAPH_AGENT=false  # Feature flag (default OFF)
CHECKPOINT_ENABLED=true
CHECKPOINT_DB_PATH=./tmp/checkpoints/browser_agent.db
CHECKPOINT_TIMEOUT=30
MAX_MEMORY_TOKENS=8000
MAX_MEMORY_MESSAGES=50
RETRY_MAX_ATTEMPTS=3
```

---

## Risk Management

### High-Risk Items

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| browser-use API changes | 🔴 High | 🟡 Medium | Version pin, integration tests, monitor releases |
| SQLite corruption | 🔴 High | 🟢 Low | Checksums, multi-checkpoint backup, recovery logic |
| Memory leaks | 🔴 High | 🟡 Medium | Max session duration, periodic GC, leak tests |
| Performance regression | 🟡 Medium | 🟡 Medium | Early profiling, opt-out flag, smart checkpointing |

### Mitigation Strategies

1. **Version Pinning:**
   - Pin `browser-use==0.1.48` in `pyproject.toml`
   - Add tests for browser-use API surface
   - Monitor upstream releases, review changes before upgrading

2. **Checkpoint Integrity:**
   - CRC32 checksums on all checkpoints
   - Keep last 3 checkpoints (multi-level fallback)
   - Background validation every 5 minutes
   - Auto-recovery on corruption detection

3. **Memory Management:**
   - Hard limit: 30-minute max session duration
   - Periodic GC every 50 actions
   - Browser context pooling (max 3 contexts)
   - Leak detection in integration tests

4. **Performance:**
   - Profile from day 1
   - Add `DISABLE_CHECKPOINTING` flag for perf mode
   - Optimize checkpoint frequency based on data
   - Target: +10% overhead (stretch: +20% acceptable)

---

## Success Criteria

### Must-Have (Week 1-4)

- ✅ Feature flag working (easy toggle)
- ✅ Checkpointing working (100% resumability)
- ✅ 95%+ parity with legacy (success rate)
- ✅ Performance: +20% overhead or less
- ✅ Streaming: Events render in UI
- ✅ Memory: Token-aware trimming works
- ✅ Tests: Integration tests pass

### Should-Have (Week 4-6)

- ✅ Retry: 30% failure reduction
- ✅ Observability: Full tracing
- ✅ Performance: +10% overhead (optimized)
- ✅ Load test: 100 concurrent tasks pass

### Nice-to-Have (Week 6-8)

- ✅ Documentation complete
- ✅ Production monitoring configured
- ✅ Gradual rollout plan ready
- ✅ Optional features (LLM summarization, caching)

---

## Performance Benchmarks

| Metric | Baseline (Legacy) | Target (LangGraph) | Red Flag |
|--------|-------------------|-------------------|----------|
| Avg step latency | 2-5s | 2-6s | >7s |
| Memory per session | 50-100MB | 100-150MB | >200MB |
| Checkpoint write | N/A | <100ms | >500ms |
| Resume time | N/A | <500ms | >2s |
| Stream latency | 100ms | 50-100ms | >300ms |
| Token usage | Baseline | +0-10% | >+30% |
| Success rate | 85-90% | 85-90% | <80% |

---

## Testing Strategy

### Test Pyramid

```
    /\
   /  \  E2E Tests (10 tests)
  /    \ Integration Tests (50 tests)
 /______\ Unit Tests (200+ tests)
```

### Test Categories

1. **Unit Tests (200+):**
   - State transitions
   - Memory trimming
   - Retry logic
   - Error classification
   - Checkpoint serialization

2. **Integration Tests (50):**
   - Legacy vs LangGraph parity (20 tasks)
   - Checkpoint resumability (10 scenarios)
   - Memory management (10 scenarios)
   - Error recovery (10 scenarios)

3. **Performance Tests:**
   - Latency benchmarks
   - Memory leak detection
   - Checkpoint overhead
   - Streaming throughput

4. **Load Tests:**
   - 100 concurrent tasks
   - SQLite lock contention
   - Memory pressure scenarios

---

## Migration Path

### Gradual Rollout Strategy

**Week 1-2: Internal Alpha**

- Feature flag: ON for dev team only
- Manual testing with real tasks
- Fix critical bugs

**Week 3-4: Internal Beta**

- Feature flag: ON for staging environment
- Automated integration tests running
- Performance profiling

**Week 5-6: Limited Production (10%)**

- Feature flag: 10% of production tasks
- Monitor metrics closely
- Ready to rollback

**Week 7: Expanded Production (50%)**

- Feature flag: 50% of production tasks
- Gather user feedback
- Fine-tune performance

**Week 8: Full Production (100%)**

- Feature flag: 100% of production tasks
- Legacy agent as fallback (keep for 1 month)
- Monitor for regressions

### Rollback Procedures

If issues arise:

1. **Immediate Rollback:**

   ```bash
   # Set feature flag to OFF
   export USE_LANGGRAPH_AGENT=false
   # Restart application
   ```

2. **Per-User Rollback:**

   ```python
   # Allow users to opt-out
   if user.preferences.get("use_legacy_agent"):
       agent = BrowserUseAgent(...)
   else:
       agent = LangGraphBrowserAgent(...)
   ```

3. **Automatic Fallback:**

   ```python
   try:
       result = await langgraph_agent.run(task)
   except LangGraphError:
       logger.warning("LangGraph failed, falling back to legacy")
       result = await legacy_agent.run(task)
   ```

---

## Decision Log

| Decision | Rationale | Trade-off | Date |
|----------|-----------|-----------|------|
| Gradual migration | Minimize risk | Longer timeline | Oct 22 |
| Wrapper pattern | Maintain compatibility | Extra layer | Oct 22 |
| Defer vector store | Unclear benefit | Less sophisticated | Oct 22 |
| Template summaries | Cost/latency | Less accurate | Oct 22 |
| SQLite checkpoints | Simple, proven | Not distributed | Oct 22 |
| Feature flag OFF default | Safety first | Manual enablement | Oct 22 |

---

## Next Steps

### Immediate Actions (This Week)

1. **Review & Approve Plan**
   - [ ] Team review meeting
   - [ ] Get stakeholder approval
   - [ ] Finalize timeline

2. **Setup Development Environment**
   - [ ] Create feature branch: `feature/langgraph-migration`
   - [ ] Setup checkpoint database directory
   - [ ] Configure feature flags

3. **Start Phase 1 Implementation**
   - [ ] Create `config.py` with feature flags
   - [ ] Define `BrowserAgentState` TypedDict
   - [ ] Implement basic adapter wrapper
   - [ ] Setup SqliteSaver with Windows optimizations

### Week 1 Goals

- Complete Phase 1 deliverables
- First checkpoint working
- Basic workflow (plan → act → end) functional
- Feature flag tested

---

## Resources & References

### Documentation

- [LangGraph Docs](https://langchain-ai.github.io/langgraph/)
- [SqliteSaver API](https://langchain-ai.github.io/langgraph/reference/checkpoints/)
- [browser-use Docs](https://github.com/browser-use/browser-use)

### Internal References

- `CLAUDE.md` - Project overview and standards
- `src/web_ui/agent/deep_research/deep_research_agent.py` - LangGraph example
- `src/web_ui/events/event_bus.py` - Event system
- `src/web_ui/observability/tracer.py` - Tracing infrastructure

### Team Contacts

- **Project Lead:** Shaun (@savagelysubtle)
- **Architecture Review:** Team
- **Testing:** QA Team
- **DevOps:** Deployment Team

---

## Appendix: Code Examples

### Complete LangGraphBrowserAgent Example

```python
from langgraph.graph import StateGraph
from langgraph.checkpoint.sqlite import SqliteSaver
from typing import TypedDict, Optional
import uuid

class BrowserAgentState(TypedDict):
    task: str
    session_id: str
    messages: list
    current_step: int
    max_steps: int
    completed: bool

class LangGraphBrowserAgent:
    """LangGraph-based browser agent."""

    def __init__(self, llm, browser, controller, config):
        self.llm = llm
        self.browser = browser
        self.controller = controller
        self.config = config
        self.graph = self._build_graph()

    def _build_graph(self):
        """Build LangGraph workflow."""
        workflow = StateGraph(BrowserAgentState)

        # Add nodes
        workflow.add_node("plan", self.plan_node)
        workflow.add_node("act", self.act_node)
        workflow.add_node("observe", self.observe_node)
        workflow.add_node("decide", self.decide_node)

        # Setup edges
        workflow.set_entry_point("plan")
        workflow.add_edge("plan", "act")
        workflow.add_edge("act", "observe")
        workflow.add_edge("observe", "decide")

        # Conditional edge
        workflow.add_conditional_edges(
            "decide",
            self.should_continue,
            {
                "continue": "act",
                "end": END
            }
        )

        # Compile with checkpointing
        checkpointer = create_checkpointer(self.config.checkpoint_db_path)
        return workflow.compile(checkpointer=checkpointer)

    async def plan_node(self, state: BrowserAgentState) -> dict:
        """Planning node."""
        # Implementation
        return {"current_step": state["current_step"] + 1}

    async def act_node(self, state: BrowserAgentState) -> dict:
        """Action node."""
        # Implementation
        return {}

    async def observe_node(self, state: BrowserAgentState) -> dict:
        """Observation node."""
        # Implementation
        return {}

    async def decide_node(self, state: BrowserAgentState) -> dict:
        """Decision node."""
        # Implementation
        return {}

    def should_continue(self, state: BrowserAgentState) -> str:
        """Conditional edge logic."""
        if state["completed"] or state["current_step"] >= state["max_steps"]:
            return "end"
        return "continue"

    async def run(self, task: str, max_steps: int = 100):
        """Run agent with checkpointing."""
        initial_state = {
            "task": task,
            "session_id": str(uuid.uuid4()),
            "messages": [],
            "current_step": 0,
            "max_steps": max_steps,
            "completed": False
        }

        config = {
            "configurable": {
                "thread_id": initial_state["session_id"]
            }
        }

        # Stream execution
        async for event in self.graph.astream(initial_state, config):
            yield event

        # Get final state
        final = await self.graph.aget_state(config)
        return final
```

---

**End of Plan**

*This is a living document. Update as implementation progresses.*
