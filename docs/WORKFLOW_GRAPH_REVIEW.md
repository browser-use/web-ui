# WorkflowGraphBuilder Review & Integration Plan

**Status:** CRITICAL - Missing from Migration Plan
**Impact:** HIGH - Affects UI visualization
**Date:** October 22, 2025

---

## Executive Summary

`workflow_graph.py` is **essential infrastructure** that was underspecified in the LangGraph migration plan. It provides UI visualization for agent execution and needs to be **extended, not replaced** to support LangGraph nodes while maintaining backward compatibility with the legacy agent.

---

## Current State

### What It Does

`WorkflowGraphBuilder` creates visual workflow graphs for Gradio UI with:

```python
NodeType:
- START: Beginning of execution
- THINKING: LLM reasoning
- ACTION: Browser actions
- RESULT: Action results
- ERROR: Failures
- END: Completion

NodeStatus:
- PENDING, RUNNING, COMPLETED, ERROR, SKIPPED
```

**Key Features:**

- ✅ Tracks node lifecycle (start_time, end_time, duration)
- ✅ Creates edges between nodes (animated for active)
- ✅ Sanitizes sensitive params (passwords, tokens)
- ✅ Icons for different action types
- ✅ JSON serialization for Gradio

**Integration Points:**

- Used by `workflow_visualizer.py` (Gradio component)
- Currently supports legacy `BrowserUseAgent`
- No integration with EventBus yet
- No LangGraph-specific node types

---

## Gap Analysis

### What's Missing for LangGraph

1. **New Node Types:**
   - No `PLANNING` node type (LangGraph planning_node)
   - No `OBSERVATION` node type (LangGraph observation_node)
   - No `DECISION` node type (LangGraph decision_node)
   - No `CHECKPOINT` node type (show checkpoint events)

2. **EventBus Integration:**
   - Not subscribed to `EventType.WORKFLOW_NODE_START/END`
   - Can't auto-update from streaming events
   - Requires manual node addition

3. **LangGraph-Specific Features:**
   - No support for conditional edges (different from error edges)
   - No checkpoint visualization
   - No state metadata display
   - No retry visualization (show retry attempts)

4. **Performance:**
   - No node deduplication (could create duplicate nodes in loops)
   - No depth limit (infinite loop protection)
   - Loads entire graph in memory

---

## Proposed Changes

### Phase 1: Extend Node Types (Week 2)

Add LangGraph-specific node types:

```python
# workflow_graph.py

class NodeType(str, Enum):
    """Types of workflow nodes."""

    # Existing
    START = "start"
    THINKING = "thinking"
    ACTION = "action"
    RESULT = "result"
    ERROR = "error"
    END = "end"

    # NEW: LangGraph nodes
    PLANNING = "planning"          # 🎯
    OBSERVATION = "observation"    # 👁️
    DECISION = "decision"          # 🤔
    CHECKPOINT = "checkpoint"      # 💾
    RETRY = "retry"                # 🔄
```

**Add Node Creation Methods:**

```python
def add_planning_node(self, parent_id: str, plan: str) -> str:
    """Add a planning node (LangGraph)."""
    node_id = self._generate_node_id()

    parent_node = self._get_node_by_id(parent_id)
    y_pos = parent_node.position["y"] + self.vertical_spacing if parent_node else 0

    node = WorkflowNode(
        id=node_id,
        type=NodeType.PLANNING,
        position={"x": self.horizontal_offset, "y": y_pos},
        data={
            "label": "Planning",
            "plan": plan[:200] + "..." if len(plan) > 200 else plan,
            "full_plan": plan,
            "icon": "🎯",
        },
        status=NodeStatus.RUNNING,
        start_time=time.time(),
    )

    self.nodes.append(node)
    self._add_edge(parent_id, node_id)
    return node_id

def add_observation_node(self, parent_id: str, observation: dict) -> str:
    """Add an observation node (LangGraph)."""
    node_id = self._generate_node_id()

    parent_node = self._get_node_by_id(parent_id)
    y_pos = parent_node.position["y"] + self.vertical_spacing if parent_node else 0

    node = WorkflowNode(
        id=node_id,
        type=NodeType.OBSERVATION,
        position={"x": self.horizontal_offset, "y": y_pos},
        data={
            "label": "Observation",
            "observation": str(observation)[:200],
            "full_observation": observation,
            "icon": "👁️",
        },
        status=NodeStatus.COMPLETED,
        start_time=time.time(),
        end_time=time.time(),
    )

    self.nodes.append(node)
    self._add_edge(parent_id, node_id)
    return node_id

def add_decision_node(self, parent_id: str, decision: str, reasoning: str = "") -> str:
    """Add a decision node (LangGraph)."""
    node_id = self._generate_node_id()

    parent_node = self._get_node_by_id(parent_id)
    y_pos = parent_node.position["y"] + self.vertical_spacing if parent_node else 0

    node = WorkflowNode(
        id=node_id,
        type=NodeType.DECISION,
        position={"x": self.horizontal_offset, "y": y_pos},
        data={
            "label": f"Decision: {decision}",
            "decision": decision,
            "reasoning": reasoning,
            "icon": "🤔",
        },
        status=NodeStatus.COMPLETED,
        start_time=time.time(),
        end_time=time.time(),
    )

    self.nodes.append(node)
    self._add_edge(parent_id, node_id, label=decision)
    return node_id

def add_checkpoint_node(self, parent_id: str, checkpoint_id: str) -> str:
    """Add a checkpoint node (shows state persistence)."""
    node_id = self._generate_node_id()

    parent_node = self._get_node_by_id(parent_id)
    y_pos = parent_node.position["y"] + self.vertical_spacing if parent_node else 0

    node = WorkflowNode(
        id=node_id,
        type=NodeType.CHECKPOINT,
        position={"x": self.horizontal_offset, "y": y_pos},
        data={
            "label": "Checkpoint",
            "checkpoint_id": checkpoint_id,
            "icon": "💾",
        },
        status=NodeStatus.COMPLETED,
        start_time=time.time(),
        end_time=time.time(),
    )

    self.nodes.append(node)
    self._add_edge(parent_id, node_id, animated=False)
    return node_id

def add_retry_node(self, parent_id: str, attempt: int, strategy: str) -> str:
    """Add a retry node (shows retry attempts)."""
    node_id = self._generate_node_id()

    parent_node = self._get_node_by_id(parent_id)
    y_pos = parent_node.position["y"] + self.vertical_spacing if parent_node else 0

    node = WorkflowNode(
        id=node_id,
        type=NodeType.RETRY,
        position={"x": self.horizontal_offset, "y": y_pos},
        data={
            "label": f"Retry #{attempt}",
            "attempt": attempt,
            "strategy": strategy,
            "icon": "🔄",
        },
        status=NodeStatus.RUNNING,
        start_time=time.time(),
    )

    self.nodes.append(node)
    self._add_edge(parent_id, node_id, label=f"Retry {strategy}")
    return node_id

def _add_edge(self, parent_id: str, child_id: str, label: str = None, animated: bool = True):
    """Helper to add edge between nodes."""
    edge = WorkflowEdge(
        id=f"edge_{parent_id}_{child_id}",
        source=parent_id,
        target=child_id,
        animated=animated,
        label=label
    )
    self.edges.append(edge)
```

---

### Phase 2: EventBus Integration (Week 2-3)

Create adapter to convert EventBus events to workflow graph nodes:

```python
# utils/workflow_event_adapter.py

from src.web_ui.events.event_bus import EventType, Event
from src.web_ui.utils.workflow_graph import WorkflowGraphBuilder

class WorkflowEventAdapter:
    """Adapter to convert EventBus events to workflow graph nodes."""

    def __init__(self, graph_builder: WorkflowGraphBuilder):
        self.graph = graph_builder
        self.node_map: dict[str, str] = {}  # Maps event IDs to node IDs
        self.current_parent: str = None

    async def handle_event(self, event: Event):
        """Handle incoming EventBus event."""

        if event.event_type == EventType.AGENT_START:
            # Create start node
            task = event.data.get("task", "Unknown task")
            node_id = self.graph.add_start_node(task)
            self.current_parent = node_id
            self.node_map[event.data.get("session_id")] = node_id

        elif event.event_type == EventType.WORKFLOW_NODE_START:
            # Map LangGraph node to workflow node
            node_name = event.data.get("node")

            if node_name == "planning_node":
                plan = event.data.get("state", {}).get("plan", "")
                node_id = self.graph.add_planning_node(self.current_parent, plan)

            elif node_name == "action_node":
                action = event.data.get("state", {}).get("action", {})
                node_id = self.graph.add_action_node(
                    self.current_parent,
                    action.get("name", "unknown"),
                    action.get("params", {}),
                    status=NodeStatus.RUNNING
                )

            elif node_name == "observation_node":
                observation = event.data.get("state", {}).get("observation", {})
                node_id = self.graph.add_observation_node(self.current_parent, observation)

            elif node_name == "decision_node":
                decision = event.data.get("state", {}).get("decision", "continue")
                reasoning = event.data.get("state", {}).get("reasoning", "")
                node_id = self.graph.add_decision_node(self.current_parent, decision, reasoning)

            else:
                # Generic node
                node_id = self.graph.add_thinking_node(
                    self.current_parent,
                    f"Node: {node_name}",
                    model_name=event.data.get("model")
                )

            self.current_parent = node_id
            self.node_map[event.data.get("node_id", node_name)] = node_id

        elif event.event_type == EventType.WORKFLOW_NODE_COMPLETE:
            # Update node status to completed
            node_name = event.data.get("node")
            node_id = self.node_map.get(event.data.get("node_id", node_name))

            if node_id:
                duration = event.data.get("duration_ms")
                result = event.data.get("state", {}).get("result")
                self.graph.update_node_status(
                    node_id,
                    NodeStatus.COMPLETED,
                    duration=duration,
                    result=result
                )

        elif event.event_type == EventType.AGENT_COMPLETE:
            # Add end node
            final_result = event.data.get("result", "Task completed")
            self.graph.add_end_node(self.current_parent, final_result)

        elif event.event_type == EventType.AGENT_ERROR:
            # Add error node
            error = event.data.get("error", "Unknown error")
            self.graph.add_error_node(self.current_parent, error)

        # Return updated graph
        return self.graph.to_dict()
```

**Usage in workflow_visualizer.py:**

```python
# webui/components/workflow_visualizer.py

from src.web_ui.utils.workflow_graph import WorkflowGraphBuilder
from src.web_ui.utils.workflow_event_adapter import WorkflowEventAdapter
from src.web_ui.events.event_bus import get_event_bus, EventType

class WorkflowVisualizer:
    """Real-time workflow visualization component."""

    def __init__(self):
        self.graph = WorkflowGraphBuilder()
        self.adapter = WorkflowEventAdapter(self.graph)
        self.event_bus = get_event_bus()

    async def start_listening(self, session_id: str):
        """Start listening to events for a session."""

        # Subscribe to relevant events
        event_types = [
            EventType.AGENT_START,
            EventType.WORKFLOW_NODE_START,
            EventType.WORKFLOW_NODE_COMPLETE,
            EventType.AGENT_COMPLETE,
            EventType.AGENT_ERROR,
        ]

        for event_type in event_types:
            await self.event_bus.subscribe(
                event_type,
                lambda e: self.adapter.handle_event(e) if e.session_id == session_id else None
            )

    def get_graph_data(self) -> dict:
        """Get current graph data for rendering."""
        return self.graph.to_dict()
```

---

### Phase 3: Enhanced Features (Week 3-4)

**1. Add Conditional Edges:**

```python
# In WorkflowEdge
@dataclass
class WorkflowEdge:
    """A connection between workflow nodes."""

    id: str
    source: str
    target: str
    animated: bool = False
    label: str | None = None
    edge_type: str = "normal"  # NEW: "normal", "conditional", "retry", "error"
    condition: str | None = None  # NEW: For conditional edges

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "type": self.edge_type,  # For UI styling
        }

        if self.animated:
            result["animated"] = True
        if self.label:
            result["label"] = self.label
        if self.condition:
            result["condition"] = self.condition

        return result
```

**2. Add State Metadata Display:**

```python
def add_state_snapshot(self, node_id: str, state: dict):
    """Attach state snapshot to node (for debugging)."""
    node = self._get_node_by_id(node_id)
    if node:
        # Sanitize state (remove large objects)
        sanitized_state = {
            k: v for k, v in state.items()
            if k not in ["browser_context", "page_html"]  # Skip large objects
        }
        node.data["state_snapshot"] = sanitized_state
```

**3. Add Depth Limit (Infinite Loop Protection):**

```python
class WorkflowGraphBuilder:
    """Builds workflow graph data from agent execution."""

    def __init__(self, max_depth: int = 100):
        self.nodes: list[WorkflowNode] = []
        self.edges: list[WorkflowEdge] = []
        self.node_counter = 0
        self.current_depth = 0
        self.horizontal_offset = 250
        self.vertical_spacing = 120
        self.max_depth = max_depth  # NEW: Prevent infinite loops

    def _check_depth_limit(self) -> bool:
        """Check if we've hit max depth."""
        if self.current_depth >= self.max_depth:
            logger.warning(f"Reached max graph depth: {self.max_depth}")
            return True
        return False

    def add_action_node(self, parent_id: str, action: str, params: dict, status: NodeStatus = NodeStatus.PENDING) -> str:
        """Add an action node."""
        if self._check_depth_limit():
            return self._add_truncation_node(parent_id)

        # ... rest of implementation

    def _add_truncation_node(self, parent_id: str) -> str:
        """Add node indicating graph was truncated."""
        node_id = self._generate_node_id()

        node = WorkflowNode(
            id=node_id,
            type=NodeType.END,
            position={"x": self.horizontal_offset, "y": self.current_depth * self.vertical_spacing},
            data={
                "label": "Graph Truncated",
                "message": f"Max depth ({self.max_depth}) reached. Graph truncated for performance.",
                "icon": "⚠️"
            },
            status=NodeStatus.SKIPPED,
        )

        self.nodes.append(node)
        self._add_edge(parent_id, node_id)
        return node_id
```

---

## Integration Checklist

### Week 2 (Phase 2 of Migration)

- [ ] Add new node types (PLANNING, OBSERVATION, DECISION, CHECKPOINT, RETRY)
- [ ] Add node creation methods for each new type
- [ ] Create `WorkflowEventAdapter` class
- [ ] Update `workflow_visualizer.py` to use adapter
- [ ] Test with both legacy and LangGraph agents

### Week 3 (Phase 3 of Migration)

- [ ] Add conditional edge support
- [ ] Add state snapshot capability
- [ ] Add depth limit protection
- [ ] Enhanced styling for different edge types
- [ ] Add checkpoint visualization

### Week 4 (Testing)

- [ ] Integration tests (legacy vs LangGraph visualization)
- [ ] Performance tests (large graphs with 100+ nodes)
- [ ] UI tests (verify Gradio rendering)

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking changes in existing UI | 🔴 High | Maintain backward compatibility, feature flag |
| Large graphs slow down UI | 🟡 Medium | Add depth limit, lazy loading, virtualization |
| EventBus subscription leaks | 🟡 Medium | Proper cleanup on session end |
| Graph state diverges from actual | 🟢 Low | Single source of truth (EventBus) |

---

## Recommendations

### MUST DO

1. ✅ **Extend `WorkflowGraphBuilder`** with LangGraph node types (Week 2)
2. ✅ **Create `WorkflowEventAdapter`** for EventBus integration (Week 2)
3. ✅ **Add depth limit** to prevent UI crashes (Week 3)
4. ✅ **Test with both agent types** to ensure compatibility (Week 4)

### SHOULD DO

- Add conditional edge visualization (better UX)
- Add checkpoint nodes (helps debugging)
- Add retry visualization (shows recovery)
- State snapshot display (debugging aid)

### NICE TO HAVE

- Graph export to PNG/SVG
- Timeline view (alternative visualization)
- Graph diff (compare two executions)
- Interactive node details panel

---

## Conclusion

**`WorkflowGraphBuilder` is CRITICAL infrastructure** that must be updated for LangGraph migration. The good news:

✅ **Architecture is sound** - just needs extension, not replacement
✅ **Backward compatible** - can support both legacy and LangGraph
✅ **EventBus integration** - natural fit for streaming updates
⚠️ **Missing from plan** - needs to be added to Phase 2 deliverables

**Action:** Update migration plan to include `WorkflowGraphBuilder` extension in Phase 2 (Week 2).

---

**End of Review**
