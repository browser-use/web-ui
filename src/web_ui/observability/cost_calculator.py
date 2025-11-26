"""
LLM cost calculation based on token usage.
"""

import logging

logger = logging.getLogger(__name__)

# Pricing as of January 2025 (USD per 1M tokens)
# Sources: OpenAI, Anthropic, Google, DeepSeek pricing pages
LLM_PRICING = {
    # OpenAI Models
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    # Anthropic Models
    "claude-3.7-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-opus": {"input": 15.00, "output": 75.00},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
    "claude-3-sonnet": {"input": 3.00, "output": 15.00},
    # Google Models
    "gemini-pro": {"input": 0.50, "output": 1.50},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    # DeepSeek Models
    "deepseek-v3": {"input": 0.14, "output": 0.28},
    "deepseek-chat": {"input": 0.14, "output": 0.28},
    # Mistral Models
    "mistral-large": {"input": 2.00, "output": 6.00},
    "mistral-medium": {"input": 2.70, "output": 8.10},
    "mistral-small": {"input": 0.20, "output": 0.60},
    # Open Source / Self-hosted (free)
    "ollama": {"input": 0.00, "output": 0.00},
    "llama": {"input": 0.00, "output": 0.00},
}


def calculate_llm_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """
    Calculate cost in USD for an LLM call.

    Args:
        model: Model name/identifier
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        Cost in USD
    """
    if not model or input_tokens == 0 or output_tokens == 0:
        return 0.0

    # Normalize model name (lowercase, remove version suffixes)
    model_key = model.lower().strip()

    # Try exact match first
    if model_key in LLM_PRICING:
        pricing = LLM_PRICING[model_key]
    else:
        # Try fuzzy matching
        pricing = None
        for known_model in LLM_PRICING:
            if known_model in model_key or model_key in known_model:
                pricing = LLM_PRICING[known_model]
                logger.debug(f"Matched '{model}' to pricing model '{known_model}'")
                break

        if not pricing:
            logger.warning(f"Unknown model for cost calculation: {model}")
            return 0.0

    # Calculate costs
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]

    total_cost = input_cost + output_cost

    logger.debug(f"Cost for {model}: {input_tokens} in + {output_tokens} out = ${total_cost:.6f}")

    return total_cost


def estimate_task_cost(
    model: str, estimated_steps: int, avg_tokens_per_step: int = 2000
) -> dict[str, float]:
    """
    Estimate the cost of a task.

    Args:
        model: Model name
        estimated_steps: Estimated number of steps
        avg_tokens_per_step: Average tokens per step (input + output)

    Returns:
        Dictionary with cost estimates
    """
    # Assume 60% input, 40% output split
    input_tokens = int(avg_tokens_per_step * 0.6)
    output_tokens = int(avg_tokens_per_step * 0.4)

    cost_per_step = calculate_llm_cost(model, input_tokens, output_tokens)
    total_cost = cost_per_step * estimated_steps

    return {
        "cost_per_step": round(cost_per_step, 6),
        "total_cost": round(total_cost, 4),
        "total_tokens": avg_tokens_per_step * estimated_steps,
        "estimated_steps": estimated_steps,
    }


def get_pricing_info(model: str) -> dict[str, float] | None:
    """
    Get pricing information for a model.

    Args:
        model: Model name

    Returns:
        Dictionary with input and output pricing per 1M tokens, or None if unknown
    """
    model_key = model.lower().strip()

    # Try exact match
    if model_key in LLM_PRICING:
        return LLM_PRICING[model_key].copy()

    # Try fuzzy matching
    for known_model in LLM_PRICING:
        if known_model in model_key or model_key in known_model:
            return LLM_PRICING[known_model].copy()

    return None


def format_cost(cost_usd: float) -> str:
    """
    Format cost for display.

    Args:
        cost_usd: Cost in USD

    Returns:
        Formatted string
    """
    if cost_usd == 0:
        return "Free"
    elif cost_usd < 0.01:
        return f"${cost_usd:.6f}"
    elif cost_usd < 1:
        return f"${cost_usd:.4f}"
    else:
        return f"${cost_usd:.2f}"
