"""
Workflow graph builder for visualizing agent execution.
"""

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any


class NodeType(str, Enum):
    """Types of workflow nodes."""

    START = "start"
    THINKING = "thinking"
    ACTION = "action"
    RESULT = "result"
    ERROR = "error"
    END = "end"


class NodeStatus(str, Enum):
    """Status of a workflow node."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class WorkflowNode:
    """A single node in the workflow graph."""

    id: str
    type: NodeType
    position: dict[str, float]
    data: dict[str, Any]
    status: NodeStatus = NodeStatus.PENDING
    start_time: float | None = None
    end_time: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "id": self.id,
            "type": self.type.value,
            "position": self.position,
            "data": {**self.data, "status": self.status.value},
        }

        # Add timing information
        if self.start_time and self.end_time:
            result["data"]["duration"] = round(
                (self.end_time - self.start_time) * 1000, 2
            )  # milliseconds

        return result


@dataclass
class WorkflowEdge:
    """A connection between workflow nodes."""

    id: str
    source: str
    target: str
    animated: bool = False
    label: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "id": self.id,
            "source": self.source,
            "target": self.target,
        }

        if self.animated:
            result["animated"] = True
        if self.label:
            result["label"] = self.label

        return result


class WorkflowGraphBuilder:
    """Builds workflow graph data from agent execution."""

    def __init__(self):
        self.nodes: list[WorkflowNode] = []
        self.edges: list[WorkflowEdge] = []
        self.node_counter = 0
        self.current_depth = 0
        self.horizontal_offset = 250
        self.vertical_spacing = 120

    def add_start_node(self, task: str) -> str:
        """Add the starting node."""
        node_id = self._generate_node_id()

        node = WorkflowNode(
            id=node_id,
            type=NodeType.START,
            position={"x": self.horizontal_offset, "y": 0},
            data={"label": "Start", "task": task, "icon": "🚀"},
            status=NodeStatus.COMPLETED,
            start_time=time.time(),
            end_time=time.time(),
        )

        self.nodes.append(node)
        self.current_depth = 1
        return node_id

    def add_thinking_node(self, parent_id: str, content: str, model_name: str | None = None) -> str:
        """Add a thinking/reasoning node."""
        node_id = self._generate_node_id()

        # Calculate position based on parent
        parent_node = self._get_node_by_id(parent_id)
        y_pos = (
            parent_node.position["y"] + self.vertical_spacing
            if parent_node
            else self.vertical_spacing
        )

        node = WorkflowNode(
            id=node_id,
            type=NodeType.THINKING,
            position={"x": self.horizontal_offset, "y": y_pos},
            data={
                "label": "Thinking",
                "content": content[:200] + "..." if len(content) > 200 else content,
                "full_content": content,
                "model": model_name,
                "icon": "🤔",
            },
            status=NodeStatus.RUNNING,
            start_time=time.time(),
        )

        self.nodes.append(node)

        # Add edge from parent
        edge = WorkflowEdge(
            id=f"edge_{parent_id}_{node_id}", source=parent_id, target=node_id, animated=True
        )
        self.edges.append(edge)

        self.current_depth += 1
        return node_id

    def add_action_node(
        self,
        parent_id: str,
        action: str,
        params: dict[str, Any],
        status: NodeStatus = NodeStatus.PENDING,
    ) -> str:
        """Add an action node."""
        node_id = self._generate_node_id()

        parent_node = self._get_node_by_id(parent_id)
        y_pos = (
            parent_node.position["y"] + self.vertical_spacing
            if parent_node
            else self.vertical_spacing
        )

        # Format action label
        action_label = self._format_action_label(action)

        # Get appropriate icon
        icon = self._get_action_icon(action)

        node = WorkflowNode(
            id=node_id,
            type=NodeType.ACTION,
            position={"x": self.horizontal_offset, "y": y_pos},
            data={
                "label": action_label,
                "action": action,
                "params": self._sanitize_params(params),
                "icon": icon,
            },
            status=status,
            start_time=time.time() if status == NodeStatus.RUNNING else None,
        )

        self.nodes.append(node)

        # Add edge from parent
        edge = WorkflowEdge(id=f"edge_{parent_id}_{node_id}", source=parent_id, target=node_id)
        self.edges.append(edge)

        self.current_depth += 1
        return node_id

    def add_result_node(self, parent_id: str, result: Any, success: bool = True) -> str:
        """Add a result node."""
        node_id = self._generate_node_id()

        parent_node = self._get_node_by_id(parent_id)
        y_pos = (
            parent_node.position["y"] + self.vertical_spacing
            if parent_node
            else self.vertical_spacing
        )

        node = WorkflowNode(
            id=node_id,
            type=NodeType.RESULT,
            position={"x": self.horizontal_offset, "y": y_pos},
            data={
                "label": "Success" if success else "Failed",
                "result": str(result)[:200] if result else "No result",
                "full_result": str(result) if result else None,
                "icon": "✅" if success else "❌",
            },
            status=NodeStatus.COMPLETED if success else NodeStatus.ERROR,
            start_time=time.time(),
            end_time=time.time(),
        )

        self.nodes.append(node)

        # Add edge from parent
        edge = WorkflowEdge(
            id=f"edge_{parent_id}_{node_id}",
            source=parent_id,
            target=node_id,
            label="✓" if success else "✗",
        )
        self.edges.append(edge)

        return node_id

    def add_error_node(self, parent_id: str, error: Exception | str) -> str:
        """Add an error node."""
        node_id = self._generate_node_id()

        parent_node = self._get_node_by_id(parent_id)
        y_pos = (
            parent_node.position["y"] + self.vertical_spacing
            if parent_node
            else self.vertical_spacing
        )

        error_msg = (
            str(error) if isinstance(error, str) else f"{type(error).__name__}: {str(error)}"
        )

        node = WorkflowNode(
            id=node_id,
            type=NodeType.ERROR,
            position={"x": self.horizontal_offset, "y": y_pos},
            data={
                "label": "Error",
                "error": error_msg[:200],
                "full_error": error_msg,
                "icon": "🚫",
            },
            status=NodeStatus.ERROR,
            start_time=time.time(),
            end_time=time.time(),
        )

        self.nodes.append(node)

        # Add edge from parent
        edge = WorkflowEdge(
            id=f"edge_{parent_id}_{node_id}", source=parent_id, target=node_id, label="error"
        )
        self.edges.append(edge)

        return node_id

    def add_end_node(self, parent_id: str, final_result: str | None = None) -> str:
        """Add the ending node."""
        node_id = self._generate_node_id()

        parent_node = self._get_node_by_id(parent_id)
        y_pos = (
            parent_node.position["y"] + self.vertical_spacing
            if parent_node
            else self.vertical_spacing
        )

        node = WorkflowNode(
            id=node_id,
            type=NodeType.END,
            position={"x": self.horizontal_offset, "y": y_pos},
            data={"label": "Complete", "result": final_result or "Task completed", "icon": "🏁"},
            status=NodeStatus.COMPLETED,
            start_time=time.time(),
            end_time=time.time(),
        )

        self.nodes.append(node)

        # Add edge from parent
        edge = WorkflowEdge(id=f"edge_{parent_id}_{node_id}", source=parent_id, target=node_id)
        self.edges.append(edge)

        return node_id

    def update_node_status(
        self, node_id: str, status: NodeStatus, duration: float | None = None, result: Any = None
    ):
        """Update a node's status."""
        node = self._get_node_by_id(node_id)
        if node:
            node.status = status

            # Update timing
            if status == NodeStatus.RUNNING and not node.start_time:
                node.start_time = time.time()
            elif status in (NodeStatus.COMPLETED, NodeStatus.ERROR):
                node.end_time = time.time()

            # Update result/data
            if result is not None:
                node.data["result"] = str(result)[:200]
                node.data["full_result"] = str(result)

            if duration is not None:
                node.data["duration"] = duration

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for Gradio component."""
        return {
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "metadata": {
                "total_nodes": len(self.nodes),
                "total_edges": len(self.edges),
                "depth": self.current_depth,
            },
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        import json

        return json.dumps(self.to_dict(), indent=2)

    def _generate_node_id(self) -> str:
        """Generate a unique node ID."""
        node_id = f"node_{self.node_counter}"
        self.node_counter += 1
        return node_id

    def _get_node_by_id(self, node_id: str) -> WorkflowNode | None:
        """Get a node by its ID."""
        return next((n for n in self.nodes if n.id == node_id), None)

    def _format_action_label(self, action: str) -> str:
        """Format action name for display."""
        # Remove common prefixes
        action = action.replace("go_to_", "").replace("extract_", "")

        # Convert snake_case to Title Case
        words = action.split("_")
        return " ".join(word.capitalize() for word in words)

    def _get_action_icon(self, action: str) -> str:
        """Get appropriate icon for action type."""
        action_lower = action.lower()

        if "navigate" in action_lower or "go_to" in action_lower:
            return "🧭"
        elif "click" in action_lower:
            return "🖱️"
        elif "type" in action_lower or "input" in action_lower:
            return "⌨️"
        elif "extract" in action_lower or "get" in action_lower:
            return "📊"
        elif "search" in action_lower:
            return "🔍"
        elif "scroll" in action_lower:
            return "📜"
        elif "screenshot" in action_lower:
            return "📸"
        elif "wait" in action_lower:
            return "⏱️"
        else:
            return "⚡"

    def _sanitize_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """Sanitize parameters for display (remove sensitive data, truncate long values)."""
        sanitized = {}

        for key, value in params.items():
            # Skip sensitive keys
            if any(
                sensitive in key.lower() for sensitive in ["password", "token", "secret", "key"]
            ):
                sanitized[key] = "***REDACTED***"
            # Truncate long values
            elif isinstance(value, str) and len(value) > 100:
                sanitized[key] = value[:97] + "..."
            else:
                sanitized[key] = value

        return sanitized
