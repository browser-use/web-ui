"""
Workflow visualization component for Gradio UI.
"""

from typing import Any

import gradio as gr


def create_workflow_visualizer() -> tuple[gr.JSON, gr.Markdown]:
    """
    Create a simple workflow visualizer using Gradio's built-in components.

    Returns a tuple of (JSON component for graph data, Markdown component for current status).

    Note: This is a simplified version using JSON display. For production,
    consider creating a custom Gradio component with React Flow.
    """

    # Workflow graph data display
    workflow_json = gr.JSON(
        label="Workflow Graph",
        elem_id="workflow_graph",
    )

    # Current step status
    workflow_status = gr.Markdown(value="**Status:** Ready to start", elem_id="workflow_status")

    return workflow_json, workflow_status


def format_workflow_for_display(workflow_data: dict[str, Any]) -> dict[str, Any]:
    """
    Format workflow data for better readability in JSON display.

    Args:
        workflow_data: Raw workflow data from WorkflowGraphBuilder

    Returns:
        Formatted workflow data optimized for display
    """
    if not workflow_data:
        return {"message": "No workflow data available"}

    # Create a more readable structure
    formatted: dict[str, Any] = {
        "summary": {
            "total_nodes": workflow_data.get("metadata", {}).get("total_nodes", 0),
            "total_edges": workflow_data.get("metadata", {}).get("total_edges", 0),
            "depth": workflow_data.get("metadata", {}).get("depth", 0),
        },
        "steps": [],
    }

    # Convert nodes to a timeline-style format
    nodes = workflow_data.get("nodes", [])
    for node in nodes:
        node_data = node.get("data", {})
        step = {
            "id": node.get("id"),
            "type": node.get("type"),
            "label": node_data.get("label"),
            "status": node_data.get("status"),
            "icon": node_data.get("icon", "⚡"),
        }

        # Add duration if available
        if "duration" in node_data:
            step["duration_ms"] = node_data["duration"]

        # Add type-specific details
        if node.get("type") == "action":
            step["action"] = node_data.get("action")
            step["params"] = node_data.get("params", {})
        elif node.get("type") == "thinking":
            step["content"] = node_data.get("content")
        elif node.get("type") in ("result", "error"):
            step["result"] = node_data.get("result") or node_data.get("error")

        steps = formatted.get("steps")
        if isinstance(steps, list):
            steps.append(step)

    return formatted


def generate_workflow_status_markdown(workflow_data: dict[str, Any]) -> str:
    """
    Generate a Markdown status summary from workflow data.

    Args:
        workflow_data: Raw workflow data from WorkflowGraphBuilder

    Returns:
        Markdown-formatted status string
    """
    if not workflow_data or not workflow_data.get("nodes"):
        return "**Status:** No workflow data available"

    nodes = workflow_data.get("nodes", [])
    metadata = workflow_data.get("metadata", {})

    # Find current (last) node
    current_node = nodes[-1] if nodes else None

    if not current_node:
        return "**Status:** Ready to start"

    node_data = current_node.get("data", {})
    status = node_data.get("status", "unknown")
    label = node_data.get("label", "Step")
    # icon is not currently used but kept for future extensibility
    _ = node_data.get("icon", "⚡")

    # Build status message
    status_emoji = {
        "pending": "⏳",
        "running": "▶️",
        "completed": "✅",
        "error": "❌",
        "skipped": "⏭️",
    }

    status_icon = status_emoji.get(status, "•")

    message = f"{status_icon} **{label}**"

    # Add details based on node type
    if current_node.get("type") == "action":
        action = node_data.get("action", "")
        message += f" - {action}"
    elif current_node.get("type") == "thinking":
        content = node_data.get("content", "")[:50]
        message += f" - {content}..."

    # Add progress
    total_nodes = metadata.get("total_nodes", 0)
    current_index = len(nodes)
    message += f"\n\n**Progress:** {current_index}/{total_nodes} steps"

    # Add duration if completed
    if status == "completed" and "duration" in node_data:
        duration = node_data["duration"]
        message += f" | Duration: {duration:.0f}ms"

    return message


# CSS for workflow visualization
WORKFLOW_CSS = """
/* Workflow visualization styling */
#workflow_graph {
    max-height: 600px;
    overflow-y: auto;
}

#workflow_status {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 16px 20px;
    border-radius: 8px;
    margin: 12px 0;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}

#workflow_status strong {
    font-size: 1.1em;
}

/* Make JSON display more readable */
#workflow_graph .json-node {
    margin: 4px 0;
}

#workflow_graph .json-key {
    color: #667eea;
    font-weight: 600;
}

#workflow_graph .json-string {
    color: #22863a;
}

#workflow_graph .json-number {
    color: #005cc5;
}
"""
