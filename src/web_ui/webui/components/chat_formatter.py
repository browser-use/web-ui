"""
Chat message formatting utilities for enhanced display.
"""

import re
from typing import Any


def format_agent_message(content: str, metadata: dict[str, Any] | None = None) -> str:
    """
    Format agent messages with rich styling, action badges, and interactive elements.

    Args:
        content: The message content
        metadata: Optional metadata including action type, status, etc.

    Returns:
        HTML-formatted message string
    """
    if not content:
        return ""

    formatted = content

    # Add action badge if action metadata is present
    if metadata and "action" in metadata:
        action = metadata["action"].lower()
        status = metadata.get("status", "default")
        badge_html = create_action_badge(action, status)
        formatted = badge_html + " " + formatted

    # Make URLs clickable
    formatted = make_urls_clickable(formatted)

    # Format code blocks
    formatted = format_code_blocks(formatted)

    # Format inline code
    formatted = format_inline_code(formatted)

    # Add collapsible sections for long content
    if len(formatted) > 500 and metadata and metadata.get("collapsible"):
        formatted = create_collapsible_section("Details", formatted)

    return formatted


def create_action_badge(action: str, status: str = "default") -> str:
    """
    Create an action badge with appropriate styling.

    Args:
        action: The action type (navigate, click, type, extract, etc.)
        status: The status (running, completed, error)

    Returns:
        HTML badge element
    """
    # Map actions to display text and styles
    action_map = {
        "navigate": {"text": "🧭 Navigate", "class": "navigate"},
        "click": {"text": "🖱️ Click", "class": "click"},
        "type": {"text": "⌨️ Type", "class": "type"},
        "input": {"text": "⌨️ Input", "class": "type"},
        "extract": {"text": "📊 Extract", "class": "extract"},
        "search": {"text": "🔍 Search", "class": "search"},
        "scroll": {"text": "📜 Scroll", "class": "scroll"},
        "wait": {"text": "⏱️ Wait", "class": "wait"},
        "screenshot": {"text": "📸 Screenshot", "class": "screenshot"},
        "done": {"text": "✅ Done", "class": "done"},
        "thinking": {"text": "🤔 Thinking", "class": "thinking"},
    }

    action_info = action_map.get(action, {"text": f"⚡ {action.title()}", "class": "default"})
    status_class = f"status-{status}" if status != "default" else ""

    return f'<span class="action-badge {action_info["class"]} {status_class}">{action_info["text"]}</span>'


def make_urls_clickable(text: str) -> str:
    """
    Convert URLs in text to clickable links.

    Args:
        text: Text containing URLs

    Returns:
        Text with URLs converted to HTML links
    """
    url_pattern = r'(https?://[^\s<>"]+|www\.[^\s<>"]+)'

    def replace_url(match):
        url = match.group(0)
        # Add https:// if only www. is present
        full_url = url if url.startswith("http") else f"https://{url}"
        # Truncate long URLs for display
        display_url = url if len(url) <= 50 else url[:47] + "..."
        return f'<a href="{full_url}" target="_blank" rel="noopener noreferrer" class="url-link">{display_url}</a>'

    return re.sub(url_pattern, replace_url, text)


def format_code_blocks(text: str) -> str:
    """
    Format code blocks with proper HTML.

    Args:
        text: Text containing code blocks marked with ```

    Returns:
        Text with formatted code blocks
    """
    # Match code blocks with optional language
    pattern = r"```(\w+)?\n(.*?)```"

    def replace_code_block(match):
        language = match.group(1) or ""
        code = match.group(2)
        lang_class = f' class="language-{language}"' if language else ""
        return f"<pre><code{lang_class}>{code}</code></pre>"

    return re.sub(pattern, replace_code_block, text, flags=re.DOTALL)


def format_inline_code(text: str) -> str:
    """
    Format inline code with backticks.

    Args:
        text: Text containing inline code marked with `

    Returns:
        Text with formatted inline code
    """
    # Match inline code (single backticks not in code blocks)
    pattern = r"`([^`\n]+)`"
    return re.sub(pattern, r'<code class="inline-code">\1</code>', text)


def create_collapsible_section(title: str, content: str, collapsed: bool = True) -> str:
    """
    Create a collapsible section for long content.

    Args:
        title: Section title
        content: Section content
        collapsed: Whether to start collapsed

    Returns:
        HTML collapsible section
    """
    collapsed_class = "collapsed" if collapsed else ""

    return f"""
    <div class="collapsible-section {collapsed_class}">
        <div class="collapsible-header" onclick="this.parentElement.classList.toggle('collapsed')">
            <span class="collapse-icon">▶</span>
            <span class="collapsible-title">{title}</span>
        </div>
        <div class="collapsible-content">
            {content}
        </div>
    </div>
    """


def add_copy_button(content: str, label: str = "Copy") -> str:
    """
    Add a copy button to content.

    Args:
        content: Content to make copyable
        label: Button label

    Returns:
        HTML with copy button
    """
    import uuid

    content_id = f"copy-content-{uuid.uuid4().hex[:8]}"

    return f"""
    <div class="copy-container">
        <div class="copy-content" id="{content_id}">{content}</div>
        <button class="copy-button" onclick="copyToClipboard('{content_id}')">
            {label}
        </button>
    </div>
    """


def format_error_message(
    error: Exception | str, context: str | None = None, include_traceback: bool = False
) -> str:
    """
    Format error messages in a user-friendly way.

    Args:
        error: The error (Exception object or string)
        context: Optional context about where/when the error occurred
        include_traceback: Whether to include full traceback (for debugging)

    Returns:
        Formatted HTML error message
    """
    import traceback

    # Extract error details
    if isinstance(error, Exception):
        error_type = type(error).__name__
        error_message = str(error)
        trace = traceback.format_exc() if include_traceback else None
    else:
        error_type = "Error"
        error_message = str(error)
        trace = None

    # Create user-friendly error message
    error_icon = "🚫"
    error_html = f"""
    <div class="error-container">
        <div class="error-header">
            <span class="error-icon">{error_icon}</span>
            <span class="error-title">{error_type}</span>
        </div>
        """

    if context:
        error_html += f"""
        <div class="error-context">
            <strong>Context:</strong> {context}
        </div>
        """

    error_html += f"""
        <div class="error-message">
            {error_message}
        </div>
    """

    # Add helpful suggestions based on error type
    suggestions = _get_error_suggestions(error_type, error_message)
    if suggestions:
        error_html += """
        <div class="error-suggestions">
            <strong>💡 Suggestions:</strong>
            <ul>
        """
        for suggestion in suggestions:
            error_html += f"<li>{suggestion}</li>"
        error_html += """
            </ul>
        </div>
        """

    # Add collapsible traceback if available
    if trace:
        trace_html = create_collapsible_section(
            "Technical Details (Traceback)", f"<pre>{trace}</pre>", collapsed=True
        )
        error_html += trace_html

    error_html += """
    </div>
    """

    return error_html


def _get_error_suggestions(error_type: str, error_message: str) -> list[str]:
    """
    Get helpful suggestions based on error type and message.

    Args:
        error_type: Type of error
        error_message: Error message text

    Returns:
        List of suggestions
    """
    suggestions = []
    error_msg_lower = error_message.lower()

    # API Key errors
    if (
        "api key" in error_msg_lower
        or "authentication" in error_msg_lower
        or "unauthorized" in error_msg_lower
    ):
        suggestions.extend(
            [
                "Check that your API key is correctly set in the .env file",
                "Verify that the API key has not expired",
                "Ensure the API key has the necessary permissions",
            ]
        )

    # Connection errors
    elif (
        "connection" in error_msg_lower
        or "timeout" in error_msg_lower
        or "network" in error_msg_lower
    ):
        suggestions.extend(
            [
                "Check your internet connection",
                "Verify that the API endpoint is accessible",
                "Try increasing the timeout value in settings",
            ]
        )

    # Rate limit errors
    elif "rate limit" in error_msg_lower or "quota" in error_msg_lower:
        suggestions.extend(
            [
                "Wait a few moments before trying again",
                "Check your API usage quota",
                "Consider upgrading your API plan if you're hitting limits frequently",
            ]
        )

    # Browser/Playwright errors
    elif "browser" in error_msg_lower or "playwright" in error_msg_lower:
        suggestions.extend(
            [
                "Ensure Playwright browsers are installed: `playwright install chromium --with-deps`",
                "Try restarting the browser session using the Clear button",
                "Check if the browser path is correct in settings",
            ]
        )

    # Model/LLM errors
    elif "model" in error_msg_lower and (
        "not found" in error_msg_lower or "does not exist" in error_msg_lower
    ):
        suggestions.extend(
            [
                "Verify that the model name is correct in Agent Settings",
                "Check if the model is available for your API plan",
                "Try using a different model from the same provider",
            ]
        )

    # File/Path errors
    elif "filenotfound" in error_type.lower() or "no such file" in error_msg_lower:
        suggestions.extend(
            [
                "Check that the file path exists and is accessible",
                "Verify that you have read/write permissions for the directory",
                "Use absolute paths if relative paths are causing issues",
            ]
        )

    # Generic fallback
    if not suggestions:
        suggestions.extend(
            [
                "Check the Agent Settings tab for configuration issues",
                "Review the technical details below for more information",
                "Try restarting the agent with the Clear button",
            ]
        )

    return suggestions


# CSS for chat formatting
CHAT_FORMATTING_CSS = """
/* Action Badges */
.action-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 0.75em;
    font-weight: 600;
    margin-right: 8px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.action-badge.navigate { background: #FF5722; color: white; }
.action-badge.click { background: #4CAF50; color: white; }
.action-badge.type { background: #2196F3; color: white; }
.action-badge.extract { background: #9C27B0; color: white; }
.action-badge.search { background: #FF9800; color: white; }
.action-badge.scroll { background: #607D8B; color: white; }
.action-badge.wait { background: #9E9E9E; color: white; }
.action-badge.screenshot { background: #00BCD4; color: white; }
.action-badge.done { background: #4CAF50; color: white; }
.action-badge.thinking { background: #673AB7; color: white; }
.action-badge.default { background: #757575; color: white; }

.action-badge.status-running { animation: pulse 1.5s ease-in-out infinite; }
.action-badge.status-error { background: #F44336 !important; }

@keyframes pulse {
    0%, 100% { opacity: 0.8; }
    50% { opacity: 1; }
}

/* URL Links */
.url-link {
    color: #1976D2;
    text-decoration: none;
    border-bottom: 1px solid #1976D2;
    transition: color 0.2s, border-color 0.2s;
}

.url-link:hover {
    color: #0D47A1;
    border-bottom-color: #0D47A1;
}

/* Code Blocks */
pre {
    background: #f5f5f5;
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    padding: 12px 16px;
    overflow-x: auto;
    margin: 8px 0;
}

pre code {
    font-family: 'Courier New', 'Monaco', monospace;
    font-size: 0.9em;
    line-height: 1.5;
    color: #212121;
}

.inline-code {
    font-family: 'Courier New', 'Monaco', monospace;
    font-size: 0.9em;
    background: #f5f5f5;
    padding: 2px 6px;
    border-radius: 3px;
    color: #d32f2f;
}

/* Collapsible Sections */
.collapsible-section {
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    margin: 8px 0;
    overflow: hidden;
}

.collapsible-header {
    background: #f5f5f5;
    padding: 10px 14px;
    cursor: pointer;
    user-select: none;
    display: flex;
    align-items: center;
    gap: 8px;
    transition: background 0.2s;
}

.collapsible-header:hover {
    background: #eeeeee;
}

.collapse-icon {
    transition: transform 0.2s ease;
    font-size: 0.8em;
}

.collapsible-section:not(.collapsed) .collapse-icon {
    transform: rotate(90deg);
}

.collapsible-title {
    font-weight: 500;
}

.collapsible-content {
    max-height: 0;
    overflow: hidden;
    transition: max-height 0.3s ease;
    padding: 0 14px;
}

.collapsible-section:not(.collapsed) .collapsible-content {
    max-height: 1000px;
    padding: 14px;
    overflow-y: auto;
}

/* Copy Container */
.copy-container {
    position: relative;
    background: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 6px;
    padding: 12px;
    margin: 8px 0;
}

.copy-button {
    position: absolute;
    top: 8px;
    right: 8px;
    padding: 6px 12px;
    background: #007bff;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.85em;
    transition: background 0.2s;
}

.copy-button:hover {
    background: #0056b3;
}

.copy-button.copied {
    background: #28a745;
}

.copy-content {
    font-family: 'Courier New', 'Monaco', monospace;
    white-space: pre-wrap;
    word-break: break-word;
    padding-right: 80px;
}

/* Error Container */
.error-container {
    background: #fff3f3;
    border: 2px solid #f44336;
    border-radius: 8px;
    padding: 16px;
    margin: 12px 0;
}

.error-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 12px;
    font-size: 1.1em;
}

.error-icon {
    font-size: 1.5em;
}

.error-title {
    font-weight: 700;
    color: #d32f2f;
}

.error-context {
    background: #ffebee;
    border-left: 3px solid #f44336;
    padding: 8px 12px;
    margin-bottom: 10px;
    border-radius: 4px;
}

.error-message {
    font-size: 1em;
    line-height: 1.5;
    margin: 10px 0;
    color: #333;
}

.error-suggestions {
    background: #e8f5e9;
    border-left: 3px solid #4caf50;
    padding: 12px 16px;
    margin-top: 12px;
    border-radius: 4px;
}

.error-suggestions ul {
    margin: 8px 0 0 0;
    padding-left: 20px;
}

.error-suggestions li {
    margin: 6px 0;
    color: #2e7d32;
}
"""

# JavaScript for copy functionality
CHAT_FORMATTING_JS = """
<script>
function copyToClipboard(elementId) {
    const element = document.getElementById(elementId);
    const text = element.innerText;

    navigator.clipboard.writeText(text).then(() => {
        // Visual feedback
        const btn = event.target;
        const originalText = btn.innerText;
        btn.innerText = 'Copied!';
        btn.classList.add('copied');

        setTimeout(() => {
            btn.innerText = originalText;
            btn.classList.remove('copied');
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy:', err);
    });
}
</script>
"""
