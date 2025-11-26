# Backend Improvements: LangGraph Memory & State Management

## Current Architecture Analysis

### Strengths

- ✅ **DeepResearchAgent** uses LangGraph with `StateGraph` for workflow orchestration
- ✅ Existing infrastructure: `EventBus`, `AgentTracer`, `CostCalculator`, `WorkflowGraphBuilder`
- ✅ MCP integration for external tool access
- ✅ Observability framework with spans and traces

### Gaps

- ❌ **BrowserUseAgent** doesn't use LangGraph (uses browser-use's internal Agent class)
- ❌ No persistent checkpointing/state management for BrowserUseAgent
- ❌ No conversation memory or summarization
- ❌ Limited streaming support for workflows
- ❌ No retry logic or error recovery patterns

---

## Recommended Improvements

### 1. LangGraph-Based State Management for BrowserUseAgent

**Current:** BrowserUseAgent uses a simple `for step in range(max_steps)` loop

**Proposed:** Refactor to use LangGraph StateGraph with nodes:

- `planning_node` - Analyze task and create plan
- `action_node` - Execute browser actions
- `observation_node` - Process results and extract information
- `decision_node` - Determine next action or completion
- `synthesis_node` - Aggregate results

**Benefits:**

- Better error recovery (can resume from any node)
- Checkpointing support (save/restore state)
- Parallel action execution
- Built-in observability

### 2. Persistent Memory Implementation

#### Short-Term Memory (Conversation Window Management)

```python
from langchain_core.chat_history import InMemoryChatMessageHistory
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode
from langchain_core.chat_history import BaseChatMessageHistory

class ShortTermMemory:
    """Manages conversation history within context window."""

    def __init__(self, max_history_length: int = 50):
        self.max_history_length = max_history_length
        self.memory = InMemoryChatMessageHistory()

    def add_message(self, message: BaseMessage):
        """Add message and trim if needed."""
        self.memory.add_message(message)
        if len(self.memory.messages) > self.max_history_length:
            self._trim_messages()

    def _trim_messages(self):
        """Remove oldest messages or summarize."""
        # Keep system message + last N messages
        # Or summarize older messages
        pass
```

#### Long-Term Memory (Persistent Storage)

```python
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma

class LongTermMemory:
    """Persistent memory across sessions."""

    def __init__(self, persist_directory: str = "./tmp/memory"):
        self.checkpointer = SqliteSaver.from_conn_string("memory.db")
        self.vectorstore = Chroma(
            persist_directory=persist_directory,
            embedding_function=self._get_embedding_fn()
        )

    async def save_episode(self, session_id: str, state: dict):
        """Save agent execution episode."""
        await self.checkpointer.aput((session_id,), state)

    async def retrieve_similar(self, query: str, k: int = 5):
        """Retrieve similar past experiences."""
        return self.vectorstore.similarity_search(query, k=k)
```

### 3. Enhanced Checkpointing

**Current:** BrowserUseAgent saves final history as JSON/GIF

**Proposed:** LangGraph checkpointing with SqliteSaver

```python
from langgraph.checkpoint.sqlite import SqliteSaver

def build_browser_agent_graph():
    workflow = StateGraph(BrowserAgentState)

    # Setup checkpointing
    checkpointer = SqliteSaver.from_conn_string("checkpoints.db")

    workflow.add_node("plan", planning_node)
    workflow.add_node("act", action_node)
    workflow.add_node("observe", observation_node)

    # Compile with checkpointing
    app = workflow.compile(checkpointer=checkpointer)
    return app

# Usage with checkpointing
thread_config = {"configurable": {"thread_id": task_id}}
final_state = await app.ainvoke(initial_state, config=thread_config)

# Resume from checkpoint
current_state = await app.aget_state(thread_config)
```

### 4. Streaming Support

**Proposed:** Add streaming for real-time updates

```python
from langgraph.graph.message import add_messages

async def stream_agent_execution(app, initial_state, thread_id):
    """Stream agent execution updates."""
    config = {"configurable": {"thread_id": thread_id}}

    async for event in app.astream(initial_state, config=config):
        # Yield events for UI updates
        if event:
            yield {
                "node": list(event.keys())[0],
                "state": event[list(event.keys())[0]],
                "timestamp": time.time()
            }
```

### 5. Error Recovery & Retry Logic

```python
from langgraph.graph import StateGraph
from typing import Literal

class BrowserAgentState(TypedDict):
    messages: list[BaseMessage]
    task: str
    actions_taken: list[dict]
    failures: int
    max_retries: int
    current_page: str
    browser_state: dict

def should_retry(state: BrowserAgentState) -> Literal["retry", "continue", "fail"]:
    """Determine if we should retry failed action."""
    if state["failures"] < state["max_retries"]:
        return "retry"
    elif state["failures"] >= state["max_retries"]:
        return "fail"
    return "continue"

# Add retry node
async def retry_node(state: BrowserAgentState) -> dict:
    """Retry last failed action with different strategy."""
    last_action = state["actions_taken"][-1]

    # Adjust strategy (e.g., wait longer, try different selector)
    return {
        "failures": state["failures"] + 1,
        "current_strategy": _get_next_strategy(state["failures"])
    }
```

### 6. Conversation Summarization

```python
from langchain.chains.summarize import load_summarize_chain
from langchain_core.prompts import PromptTemplate

class ConversationSummarizer:
    """Summarize long conversations to save tokens."""

    def __init__(self, llm):
        self.llm = llm
        self.summary_prompt = PromptTemplate(
            input_variables=["text"],
            template="Summarize the following conversation, focusing on: "
                     "1. Task objective 2. Key actions taken 3. Results found\n\n{text}"
        )

    async def summarize_history(self, messages: list[BaseMessage]) -> str:
        """Condense conversation history."""
        # Convert messages to text
        conversation_text = "\n".join([msg.content for msg in messages])

        # Create chain
        chain = load_summarize_chain(self.llm, chain_type="stuff")

        # Summarize
        summary = await chain.ainvoke({"input_documents": [Document(page_content=conversation_text)]})
        return summary["output_text"]
```

### 7. Integration with Existing Observability

**Proposed:** Enhance tracer to work with LangGraph

```python
from src.web_ui.observability.tracer import AgentTracer

class LangGraphTracer:
    """Tracer for LangGraph workflows."""

    def __init__(self, tracer: AgentTracer):
        self.tracer = tracer

    async def trace_node(self, node_name: str, inputs: dict):
        """Trace a LangGraph node execution."""
        async with self.tracer.span(
            name=f"node:{node_name}",
            span_type=SpanType.AGENT_NODE,
            inputs=inputs
        ) as span:
            # Node execution
            yield span
```

---

## Implementation Roadmap

### Phase 1: Foundation (Week 1-2)

1. ✅ Add LangGraph to BrowserUseAgent
2. ✅ Implement SqliteSaver checkpointing
3. ✅ Create BrowserAgentState TypedDict
4. ✅ Add basic workflow nodes (plan, act, observe)

### Phase 2: Memory (Week 3-4)

1. ✅ Implement ShortTermMemory for message trimming
2. ✅ Add LongTermMemory with vector store
3. ✅ Integrate conversation summarization
4. ✅ Add memory retrieval to planning node

### Phase 3: Reliability (Week 5-6)

1. ✅ Add retry logic and error recovery
2. ✅ Implement streaming support
3. ✅ Enhance observability integration
4. ✅ Add progress persistence

### Phase 4: Optimization (Week 7-8)

1. ✅ Optimize checkpoint frequency
2. ✅ Add parallel action execution
3. ✅ Implement result caching
4. ✅ Performance tuning

---

## Code Structure

```
src/web_ui/agent/browser_use/
├── browser_use_agent.py        # Current (to be refactored)
├── langgraph_agent.py          # NEW: LangGraph-based agent
├── state.py                    # NEW: State definitions
├── nodes.py                    # NEW: Workflow nodes
├── memory/
│   ├── __init__.py
│   ├── short_term.py          # NEW: Conversation memory
│   ├── long_term.py           # NEW: Persistent memory
│   └── summarizer.py          # NEW: Conversation summarization
└── checkpoints/
    ├── __init__.py
    └── sqlite_checkpointer.py  # NEW: Checkpoint management
```

---

## Example: New LangGraph-Based BrowserUseAgent

```python
from langgraph.graph import StateGraph
from langgraph.checkpoint.sqlite import SqliteSaver
from typing import TypedDict

class BrowserAgentState(TypedDict):
    task: str
    messages: list[BaseMessage]
    browser_context: BrowserContext
    actions_taken: list[dict]
    current_url: str
    page_html: str
    failures: int
    max_steps: int
    current_step: int

class LangGraphBrowserAgent:
    def __init__(self, llm, browser, controller):
        self.llm = llm
        self.browser = browser
        self.controller = controller
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(BrowserAgentState)

        # Add nodes
        workflow.add_node("plan", self.planning_node)
        workflow.add_node("act", self.action_node)
        workflow.add_node("observe", self.observation_node)
        workflow.add_node("decide", self.decision_node)

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
                "act": "act",
                "synthesize": "synthesize_node",
                "end": "end_node"
            }
        )

        # Compile with checkpointing
        checkpointer = SqliteSaver.from_conn_string("browser_agent.db")
        return workflow.compile(checkpointer=checkpointer)

    async def run(self, task: str, config: dict = None):
        """Run agent with checkpointing support."""
        initial_state = {
            "task": task,
            "messages": [HumanMessage(content=task)],
            "browser_context": self.browser,
            "actions_taken": [],
            "current_url": "",
            "page_html": "",
            "failures": 0,
            "max_steps": 100,
            "current_step": 0
        }

        # Use thread_id for checkpointing
        if config is None:
            config = {"configurable": {"thread_id": str(uuid.uuid4())}}

        # Stream execution for real-time updates
        async for event in self.graph.astream(initial_state, config=config):
            yield event

        # Get final state
        final_state = await self.graph.aget_state(config)
        return final_state
```

---

## Migration Strategy

### Option 1: Gradual Migration (Recommended)

1. Keep existing `BrowserUseAgent` as-is
2. Create new `LangGraphBrowserAgent` in parallel
3. Add feature flag to switch between implementations
4. Test thoroughly before full migration

### Option 2: Full Refactor

1. Refactor `BrowserUseAgent` to use LangGraph internally
2. Maintain same public API
3. Add checkpointing/memory as optional features

---

## Dependencies to Add

```toml
[dependencies]
langgraph = ">=0.3.34"              # Already added
langchain-community = ">=0.3.0"     # Already added
chromadb = ">=0.5.0"                # NEW: Vector store
tiktoken = ">=0.7.0"                # NEW: Token counting
sqlalchemy = ">=2.0.0"              # NEW: For SqliteSaver
```

---

## Benefits Summary

| Feature | Current | With Improvements |
|---------|---------|-------------------|
| State Persistence | ❌ None | ✅ Sqlite checkpointing |
| Resume Execution | ❌ Not possible | ✅ Resume from any checkpoint |
| Memory Management | ❌ None | ✅ Short + long-term memory |
| Error Recovery | ❌ Basic retry | ✅ Advanced retry logic |
| Streaming | ❌ Limited | ✅ Full streaming support |
| Observability | ⚠️ Partial | ✅ Full integration |
| Performance | ⚠️ Good | ✅ Optimized with caching |

---

## Next Steps

1. **Review** this document with the team
2. **Prioritize** features based on use cases
3. **Create** implementation tickets
4. **Start** with Phase 1 (foundation)
5. **Iterate** based on feedback

---

## Questions?

- Which features are highest priority?
- Should we implement gradual migration or full refactor?
- What's the target timeline?
- Any specific use cases we should prioritize?

---

### Review (GPT-5)

- Overall: Strong plan. Leverages existing `DeepResearchAgent` patterns and adds the missing foundations (checkpointing, memory, streaming) where `BrowserUseAgent` needs it most.
- Priority call: Start with a gradual migration via a new `LangGraphBrowserAgent` behind a feature flag, then cut over after parity tests pass.
- Short-term memory: Add trimming first; summarization can follow. Keep the heuristic simple initially (system + last N + rolling summary).
- Long-term memory: Defer vector DB until checkpoints and summaries are stable. Start with SQLite-only episode storage; add Chroma later if retrieval becomes a clear win.
- Checkpointing: Use `SqliteSaver` with per-thread `thread_id`. On Windows, set `PRAGMA journal_mode=WAL` and avoid sharing a single connection across threads to prevent locks.
- Streaming: Wire `app.astream()` into the existing `EventBus` so UI updates stay decoupled. Define a minimal event schema for node start/end and partial outputs.
- Reliability: Add explicit browser error classes (timeouts, stale element, navigation failures) and a bounded retry/backoff policy at the node level.
- Observability: Attach `AgentTracer` spans per LangGraph node and propagate token/cost from `llm_provider` so `CostCalculator` reflects real usage.
- Security/PII: Redact secrets in memory snapshots and streamed events. Reuse the `_sanitize_params()` approach from `workflow_graph`.
- Testing: Gate the migration with integration tests that assert deterministic node transitions, resumability from checkpoints, and Playwright/browser cleanup.

Do first (minimal, high impact):

1) Implement `LangGraphBrowserAgent` with `plan → act → observe → decide` and `SqliteSaver`.
2) Add feature flag and parity test path that runs both agents on the same seed task, comparing terminal outcomes.
3) Stream node lifecycle events through `EventBus` and render them in `workflow_visualizer`.
4) Add message trimming (no LLM summarization yet) and configurable history limits.
5) Introduce a small, typed retry policy with max attempts and exponential backoff.

Risks and mitigations:

- LangGraph refactor complexity → Mitigate with feature flag + parity tests + phased rollout.
- SQLite lock contention on Windows → Use WAL, one async connection per task/thread, and bounded checkpoint frequency.
- Playwright resource leaks → Add teardown guards, lint for awaited closures, and integration tests that assert clean shutdown.
- Token/cost drift → Centralize token accounting in one place (`llm_provider`), forward into spans, and surface totals in UI.

Decisions needed:

- Feature-flag name and default (recommend default ON for dev only).
- Summarization model/threshold (start off; enable after stability).
- Vector store choice and when to enable (defer until retrieval use-cases justify it).
- Event schema for streaming and retention policy for checkpoints.

---

### Technical Review (Claude Sonnet 4.5)

**Architecture Assessment:**

✅ **Strong Points:**

- LangGraph integration is the right choice - provides state machine formalism, checkpointing, and async-first design that aligns with browser automation's event-driven nature
- Gradual migration strategy minimizes risk while enabling feature-by-feature rollout - critical for production systems
- Leveraging existing `DeepResearchAgent` patterns ensures consistency and reduces learning curve
- EventBus + AgentTracer integration maintains separation of concerns and enables telemetry

⚠️ **Architecture Concerns:**

- BrowserUseAgent wraps browser-use's Agent base class - full LangGraph migration might break compatibility with upstream updates
- **Recommendation:** Use adapter pattern - keep browser-use Agent as-is, wrap it in LangGraph nodes rather than replacing internals
- State bloat risk: `BrowserAgentState` could grow large with full browser context + HTML + history - consider state partitioning
- Need clear boundaries between stateful (checkpointed) and ephemeral (runtime-only) data

**Memory Management Deep Dive:**

✅ **Short-Term Memory:**

- Trimming strategy is correct first step - summarization adds complexity, latency, and LLM costs
- **Critical:** Use token-aware trimming (tiktoken) rather than message count for consistency across model context windows
- Consider sliding window with overlap (e.g., keep last 30 messages + summary of prior 100) to preserve context continuity
- **Pro tip:** Store trimmed messages separately for debugging/audit trails - invaluable for diagnosing agent failures

⚠️ **Long-Term Memory Concerns:**

- Vector store (ChromaDB) adds 200MB+ dependency weight plus embedding model overhead
- **Key question:** Do browser automation tasks truly benefit from semantic memory retrieval? Most tasks are linear, not associative
- **Alternative:** Structured episode storage (SQLite) with metadata indexing (task type, success/fail, duration, actions) may be sufficient
- If vector search is needed, consider lighter options: SQLite-VSS (5MB), DuckDB with vec extension (15MB)

**Proposed Refinement - Multi-Tier Memory:**

```python
class MemoryTier:
    """Multi-tier memory strategy balancing performance and capability."""

    # Tier 1: Hot memory (last N messages, in-memory)
    hot_memory: list[BaseMessage]  # Last 20-50 messages, ~1-2MB
    hot_max_tokens: int = 8000     # Token limit, not message count

    # Tier 2: Warm memory (session summary, SQLite)
    session_summary: str           # Periodic condensation every 50 messages
    key_learnings: list[str]       # Extracted insights (optional)

    # Tier 3: Cold memory (historical episodes, indexed)
    episode_index: dict[str, EpisodeMetadata]  # Fast lookup by task_id, date, outcome

    # Tier 4: Vector search (only if retrieval use-case proven)
    semantic_store: Optional[VectorStore]  # Defer until Phase 3+
```

**Checkpointing Implementation:**

✅ **Good Approach:**

- SqliteSaver is production-ready, battle-tested in LangGraph
- Thread-based isolation prevents state collision across concurrent tasks

⚠️ **Windows-Specific Concerns (Critical for this project):**

- SQLite on Windows has known issues with concurrent writes despite WAL mode
- **Recommendation:** Use `timeout` parameter (30s+) and implement exponential backoff on SQLITE_BUSY errors
- Consider file locking implications in WSL vs native Windows - test both environments
- **Performance:** Test checkpoint frequency under load - every node vs every N nodes vs time-based (every 30s)

**Checkpoint Frequency Strategy:**

```python
class CheckpointStrategy:
    """Smart checkpointing to reduce I/O overhead."""

    def should_checkpoint(self, state: dict, node_name: str, last_checkpoint: float) -> bool:
        """Determine if we should checkpoint at this node."""
        # Checkpoint on:
        # 1. Critical state transitions (planning → execution)
        critical_nodes = ["planning_node", "synthesis_node"]
        if node_name in critical_nodes:
            return True

        # 2. Time threshold (every 30s to prevent data loss)
        if time.time() - last_checkpoint > 30:
            return True

        # 3. Action count (every 5 browser actions)
        if state.get("actions_taken", 0) % 5 == 0:
            return True

        # 4. Before expensive operations (page navigation, file download)
        if node_name in ["navigate_node", "download_node"]:
            return True

        return False
```

**Streaming Architecture:**

✅ **Event-Driven Design:**

- Integration with existing EventBus maintains architectural consistency
- Decoupled streaming enables multiple consumers (UI, logs, telemetry, debugging tools)

🔧 **Implementation Recommendations:**

**1. Event Schema Design:**

```python
from dataclasses import dataclass
from typing import Literal

@dataclass
class NodeEvent:
    """Standard event for LangGraph node lifecycle."""
    event_type: Literal["node_start", "node_end", "node_error"]
    node_name: str
    timestamp: float
    session_id: str
    thread_id: str

    # Optional fields (populated based on event type)
    inputs: Optional[dict] = None
    outputs: Optional[dict] = None
    duration_ms: Optional[float] = None
    error: Optional[str] = None
    metadata: Optional[dict] = None  # Cost, tokens, action count, etc.
```

**2. Backpressure Handling (Critical for UI responsiveness):**

```python
async def stream_with_backpressure(app, state, config, max_buffer=100):
    """Stream with bounded buffer to prevent memory exhaustion."""
    buffer = asyncio.Queue(maxsize=max_buffer)

    async def producer():
        try:
            async for event in app.astream(state, config):
                await buffer.put(event)
        except Exception as e:
            await buffer.put(("error", e))
        finally:
            await buffer.put(None)  # Sentinel

    producer_task = asyncio.create_task(producer())

    while True:
        event = await buffer.get()
        if event is None:
            break
        if isinstance(event, tuple) and event[0] == "error":
            raise event[1]
        yield event

    await producer_task
```

**Error Recovery & Retry:**

✅ **Bounded Retry is Essential:**

- Prevents infinite loops on persistent failures (e.g., element never appears)
- Exponential backoff reduces server load and respects rate limits

🔧 **Enhanced Retry Strategy:**

```python
from enum import Enum
from typing import List

class BrowserErrorType(Enum):
    NAVIGATION_TIMEOUT = "navigation_timeout"
    ELEMENT_NOT_FOUND = "element_not_found"
    STALE_ELEMENT = "stale_element"
    NETWORK_ERROR = "network_error"
    JAVASCRIPT_ERROR = "javascript_error"
    PERMISSION_DENIED = "permission_denied"

class RetryPolicy:
    """Multi-level retry with context-aware strategies."""

    def __init__(self):
        self.strategies = {
            BrowserErrorType.NAVIGATION_TIMEOUT: [
                "increase_timeout",      # 30s → 60s → 90s
                "refresh_page",          # Hard refresh
                "new_context"            # New browser context
            ],
            BrowserErrorType.ELEMENT_NOT_FOUND: [
                "wait_longer",           # 5s → 10s → 15s
                "search_by_text",        # Fall back to text search
                "relaxed_selector"       # Try parent or sibling elements
            ],
            BrowserErrorType.STALE_ELEMENT: [
                "refetch_element",       # Query DOM again
                "retry_action",          # Retry with fresh element
                "page_reload"            # Last resort
            ],
            BrowserErrorType.NETWORK_ERROR: [
                "exponential_backoff",   # 1s, 2s, 4s, 8s
                "dns_refresh",           # Clear DNS cache
                "proxy_switch"           # Try different network path
            ]
        }

        self.max_attempts = {
            BrowserErrorType.NAVIGATION_TIMEOUT: 3,
            BrowserErrorType.ELEMENT_NOT_FOUND: 5,
            BrowserErrorType.STALE_ELEMENT: 3,
            BrowserErrorType.NETWORK_ERROR: 4,
        }

    def get_retry_strategy(self, error_type: BrowserErrorType, attempt: int) -> Optional[str]:
        """Return strategy for given error and attempt number."""
        if attempt >= self.max_attempts.get(error_type, 3):
            return None  # Max retries exceeded

        strategies = self.strategies.get(error_type, ["exponential_backoff"])
        return strategies[min(attempt, len(strategies) - 1)]
```

**Code Organization Recommendations:**

```
src/web_ui/agent/browser_use/
├── browser_use_agent.py         # Legacy implementation (keep for now)
├── config.py                    # NEW: Feature flags and configuration
├── langgraph/                   # NEW: LangGraph implementation
│   ├── __init__.py
│   ├── agent.py                 # Main LangGraphBrowserAgent
│   ├── state.py                 # TypedDict definitions
│   ├── nodes/                   # Workflow nodes
│   │   ├── __init__.py
│   │   ├── planning.py         # Task analysis and plan generation
│   │   ├── action.py           # Browser action execution
│   │   ├── observation.py      # Result extraction and processing
│   │   └── decision.py         # Next action determination
│   ├── memory/                  # Memory management
│   │   ├── __init__.py
│   │   ├── manager.py          # Unified memory interface
│   │   ├── hot.py              # In-memory cache (last N messages)
│   │   ├── warm.py             # Session summaries (SQLite)
│   │   └── cold.py             # Historical storage (SQLite + optional vector)
│   ├── checkpointing/
│   │   ├── __init__.py
│   │   ├── sqlite_saver.py     # Checkpoint management
│   │   └── strategy.py         # Checkpoint policies (when to checkpoint)
│   ├── retry/
│   │   ├── __init__.py
│   │   ├── policies.py         # Retry strategies per error type
│   │   ├── backoff.py          # Backoff algorithms (exponential, linear, etc.)
│   │   └── classifiers.py      # Error classification logic
│   └── streaming/
│       ├── __init__.py
│       ├── events.py           # Event schemas
│       └── adapters.py         # EventBus integration
└── utils/
    ├── __init__.py
    ├── adapter.py              # Legacy → LangGraph adapter
    └── validators.py           # State validation utilities
```

**Testing Strategy:**

**Essential test coverage** (must have before GA):

1. **State Persistence Tests:**
   - Checkpoint at every node, kill process, resume from each checkpoint
   - Verify state integrity after resume (no data loss, correct continuation)
   - Test checkpoint corruption recovery

2. **Memory Tests:**
   - Validate trimming preserves system message and recent context
   - Test token counting accuracy across different models
   - Verify summarization doesn't lose critical task information
   - Test retrieval relevance (if vector store implemented)

3. **Retry Tests:**
   - Assert exponential backoff timing (measure actual delays)
   - Verify max attempts respected (doesn't retry forever)
   - Test strategy switching (tries different approaches)
   - Validate error classification accuracy

4. **Streaming Tests:**
   - Verify event ordering (start before end, no out-of-order)
   - Test backpressure (doesn't crash on burst of 1000 events)
   - Validate no data loss in events
   - Test stream cancellation (clean shutdown)

5. **Integration Tests (Most Important):**
   - Run legacy vs LangGraph on 50+ real-world tasks
   - Compare success rate, action count, execution time
   - Validate output equivalence (same result, different path OK)
   - Test edge cases: timeouts, errors, complex multi-step tasks

6. **Performance Tests:**
   - Measure checkpoint overhead per node (<100ms target)
   - Track memory growth over 100-step task (<200MB target)
   - Test streaming throughput (>100 events/sec)
   - Profile end-to-end latency (baseline + 20% acceptable)

7. **Failure Tests:**
   - Browser crash mid-execution → should resume cleanly
   - Network loss during action → should retry with backoff
   - Checkpoint DB corruption → should detect and recover
   - Out of memory → should trim aggressively and warn

**Performance Benchmarks to Track:**

| Metric | Baseline (Current) | Target (LangGraph) | Red Flag Threshold |
|--------|-------------------|--------------------|--------------------|
| Avg step latency | ~2-5s | ~2-6s | >7s |
| Memory per session | ~50-100MB | ~100-150MB | >200MB |
| Checkpoint write time | N/A | <100ms | >500ms |
| Resume time from checkpoint | N/A | <500ms | >2s |
| Event stream latency | ~100ms | ~50-100ms | >300ms |
| Token usage vs baseline | N/A | +0-10% | +30% |
| Success rate | ~85-90% | ~85-90% | <80% |

**Migration Risk Assessment:**

🔴 **High Risk:**

- **Upstream breaking changes:** browser-use library could change APIs, invalidating wrapper approach
  - *Mitigation:* Version pin browser-use, add integration tests for API surface, monitor upstream releases
- **SQLite corruption:** Crash during checkpoint write could corrupt database, lose session state
  - *Mitigation:* Add checksums, implement corruption recovery, periodic validation, backup last-known-good checkpoint
- **Memory leaks:** Long-running sessions (100+ steps) could leak browser contexts, DOM references
  - *Mitigation:* Add max session duration (30 min), periodic GC, browser context pooling, leak detection tests

🟡 **Medium Risk:**

- **Performance regression:** Checkpointing overhead could slow down fast tasks by 20-30%
  - *Mitigation:* Profile early, add opt-out flag for performance mode, optimize checkpoint frequency
- **Increased complexity:** More moving parts make debugging harder, especially async issues
  - *Mitigation:* Comprehensive docs, architecture diagrams, decision logs, enhanced logging
- **Dependency bloat:** ChromaDB (200MB), tiktoken (5MB), sqlalchemy (20MB) increase install size
  - *Mitigation:* Make vector store optional, lazy-load dependencies, document minimal install

🟢 **Low Risk:**

- **Feature flag enables safe rollback:** Can switch back to legacy with single config change
- **Gradual migration limits blast radius:** Only affects opt-in users initially
- **Existing DeepResearchAgent proves viability:** LangGraph already proven in production workload

**Mitigation Strategies:**

1. **Upstream Compatibility:**
   - Version pin: `browser-use==0.1.48` in `pyproject.toml`
   - Add integration tests for browser-use API surface (Agent.**init**, .run(), .step())
   - Set up GitHub webhook to monitor browser-use releases, review breaking changes

2. **Checkpoint Integrity:**
   - Add CRC32 checksums to checkpoint metadata
   - Implement auto-recovery: detect corruption, fall back to previous checkpoint
   - Periodic validation: background task checks checkpoint integrity every 5 minutes
   - Keep last 3 checkpoints (not just latest) for multi-level fallback

3. **Memory Management:**
   - Hard limit: max session duration 30 minutes, then force checkpoint and restart
   - Periodic GC: every 50 actions, explicitly close old browser tabs, clear caches
   - Browser context pooling: reuse contexts when possible, limit max open contexts to 3
   - Leak detection: track object counts (pages, contexts, DOM elements) in tests

4. **Performance:**
   - Profile early: add instrumentation from day 1, track all metrics in observability
   - Add opt-out: `DISABLE_CHECKPOINTING=true` environment variable for performance mode
   - Optimize checkpoint frequency: start conservative (every node), tune based on data

5. **Complexity:**
   - Architecture decision records (ADRs): document why each choice was made
   - Sequence diagrams: visual flow of state transitions, checkpointing, streaming
   - Enhanced logging: structured logs with correlation IDs, trace agent execution path
   - Decision logs: capture key decisions as they're made during implementation

**Immediate Action Items (Week-by-Week Breakdown):**

**Week 1 - Foundation (Must Have):**

- [ ] Create feature flag system: `config.py` with `USE_LANGGRAPH_AGENT=false` default
- [ ] Implement minimal `BrowserAgentState` TypedDict (task, messages, actions_taken, current_url)
- [ ] Build basic workflow: `START → planning_node → action_node → END`
- [ ] Add SqliteSaver with WAL mode, timeout handling (30s), and exponential backoff
- [ ] Create adapter that wraps browser-use Agent methods in LangGraph node functions
- [ ] Write unit tests for state transitions and adapter

**Week 2 - Parity (Must Have):**

- [ ] Implement all workflow nodes (planning, action, observation, decision)
- [ ] Add conditional edges and routing logic (`should_continue`, `should_retry`)
- [ ] Create integration test suite: run same 20 tasks on legacy vs LangGraph, compare outputs
- [ ] Implement checkpointing: checkpoint at every critical node (planning, synthesis)
- [ ] Add basic streaming via EventBus: node start/end events
- [ ] Performance baseline: measure latency, memory, success rate

**Week 3 - Memory (Should Have):**

- [ ] Implement hot memory: last N messages with token-aware trimming (tiktoken)
- [ ] Add configurable limits: max tokens (8000), max messages (50)
- [ ] Build session summary generation: template-based, no LLM (saves cost)
- [ ] Create memory manager interface: `MemoryManager.add_message()`, `.get_context()`
- [ ] Add memory tests: verify trimming, token counting, context preservation
- [ ] Integrate memory into planning node: prepend summary to planning prompt

**Week 4 - Reliability (Should Have):**

- [ ] Implement retry policies: exponential backoff, max attempts per error type
- [ ] Add error classification: navigation, element, network, JavaScript errors
- [ ] Build strategy-based retry: different approach per error type
- [ ] Add observability integration: AgentTracer spans per node, cost tracking
- [ ] Performance profiling: identify bottlenecks, optimize hot paths
- [ ] Load testing: 100 concurrent tasks, measure checkpoint contention

**Week 5-8 - Nice to Have (Defer if needed):**

- [ ] LLM-based summarization (optional, adds cost)
- [ ] Vector store integration (optional, evaluate need first)
- [ ] Parallel action execution (complex, high risk)
- [ ] Result caching (optimization, not critical)
- [ ] Advanced telemetry and dashboards

**Architectural Decisions Log:**

**Document these decisions with rationale:**

1. **Wrapper vs Full Refactor:**
   - **Decision:** Wrapper approach (keep browser-use Agent, wrap in LangGraph nodes)
   - **Rationale:** Maintains compatibility with upstream, reduces risk, enables gradual migration
   - **Trade-off:** Extra abstraction layer, but safer

2. **Memory Strategy:**
   - **Decision:** Defer vector store, focus on structured episode storage + hot memory
   - **Rationale:** Browser tasks are mostly linear, not associative; vector search has marginal benefit
   - **Trade-off:** Less sophisticated, but faster and cheaper

3. **Checkpoint Frequency:**
   - **Decision:** Start with checkpoint at every critical node, optimize based on profiling
   - **Rationale:** Prioritize data safety over performance initially
   - **Trade-off:** Higher I/O overhead, but prevents data loss

4. **Event Schema:**
   - **Decision:** Adopt lightweight schema (node_name, timestamp, inputs/outputs), add fields incrementally
   - **Rationale:** Simpler to implement, easier to evolve
   - **Trade-off:** May need to version schema later

5. **Feature Flag Default:**
   - **Decision:** `OFF` for production, `ON` for dev/staging
   - **Rationale:** Minimize risk in production, enable testing in non-prod
   - **Trade-off:** Requires manual enablement for testing

6. **Summarization:**
   - **Decision:** Defer LLM-based summarization until Phase 3+, use templates initially
   - **Rationale:** Reduces complexity, cost, and latency; template-based is sufficient for v1
   - **Trade-off:** Less sophisticated summaries, but faster

7. **Testing Threshold:**
   - **Decision:** Require 95%+ parity with legacy agent before GA (same success rate)
   - **Rationale:** High bar ensures quality, prevents regressions
   - **Trade-off:** Takes longer to ship, but safer

**Final Recommendation:**

**GO with gradual migration.** The plan is technically sound and addresses real limitations, but:

**✅ Do This:**

- Start with MVP: checkpointing + basic workflow (4 nodes: plan → act → observe → decide)
- Add memory tier-by-tier based on proven need (hot first, warm later, cold/vector defer)
- Measure everything from day 1: latency, memory, checkpoint size, success rate
- Keep escape hatch: per-user or per-task ability to fall back to legacy agent
- Document as you go: capture architecture decisions, learnings, trade-offs

**❌ Don't Do This:**

- Don't build all features upfront - ship incrementally, validate each layer
- Don't add vector store until you have concrete use-case demonstrating need
- Don't optimize prematurely - profile first, optimize hot paths only
- Don't skip testing - integration tests are more important than unit tests here
- Don't forget Windows-specific issues - SQLite, file locking, path handling all differ

**Timeline Assessment:**

The 8-week timeline is **reasonable but aggressive**. To hit it:

- Cut scope ruthlessly: focus on core features (checkpointing, workflow, streaming)
- Defer optimizations: memory tiers, retry strategies, vector store can wait
- Accept technical debt: ship MVP, refactor later with learnings
- Allocate 30% buffer for unexpected issues (SQLite quirks, browser-use API changes)

**Suggested Prioritization (MoSCoW):**

**Must Have (Week 1-2):**

- Feature flag + basic LangGraph workflow
- Checkpointing with SqliteSaver (resume support)
- Streaming integration with EventBus
- Integration tests (legacy vs LangGraph parity)

**Should Have (Week 3-4):**

- Hot memory management (token-aware trimming)
- Retry policies (exponential backoff, max attempts)
- Observability integration (AgentTracer spans, cost tracking)
- Performance profiling and optimization

**Could Have (Week 5-6):**

- Session summaries (template-based first, LLM later)
- Advanced error recovery (strategy-based retry)
- Load testing and concurrency optimization

**Won't Have (v1, revisit later):**

- Vector store / semantic memory retrieval
- Parallel action execution
- LLM-based conversation summarization
- Result caching / memoization

**Ship Fast, Iterate:**
Ship Phase 1 (checkpointing + workflow) as internal beta in Week 2, gather feedback, iterate. Don't wait for perfection - the infrastructure is solid, execution matters more than planning.

**Success Criteria:**

- ✅ Resume from checkpoint works 100% of the time (no data loss)
- ✅ Performance within 20% of baseline (acceptable overhead)
- ✅ Success rate matches or exceeds legacy (95%+ parity)
- ✅ No regressions in existing functionality
- ✅ Clear rollback path if issues arise
