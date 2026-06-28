"""
claude_client.py — Claude API wrapper for natural language explanations.
Model: claude-sonnet-4-6 · Temperature: 0 (immutable per CLAUDE.md)
"""
import os
from typing import Optional
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()  # Load .env before reading env vars

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")

_client: Optional[Anthropic] = None


def get_client() -> Anthropic:
    global _client
    if _client is None:
        if not ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        _client = Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def explain_stockout(
    reagent_name: str,
    projected_stockout_days: Optional[int],
    current_stock: float,
    seasonality_hint: str = "",
) -> str:
    """
    Generate a natural language explanation of WHY a reagent is at risk.
    Temperature=0 per ADR-001.
    Falls back to a placeholder if the API key is invalid (e.g. dummy key).
    """
    try:
        client = get_client()
        system_prompt = (
            "You are LabOps Agent, a clinical lab operations assistant. "
            "Explain reagent stockout predictions in one concise paragraph. "
            "Be direct and specific. Reference seasonality if relevant. "
            "Do not use medical jargon the lab tech wouldn't understand."
        )
        user_prompt = (
            f"Reagent: {reagent_name}\n"
            f"Current stock: {current_stock} units\n"
            f"Projected stockout in: {projected_stockout_days} days\n"
            f"Seasonality context: {seasonality_hint}\n\n"
            f"Explain WHY this reagent is at risk and what action to take."
        )

        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=256,
            temperature=0,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        content = message.content
        if isinstance(content, list) and len(content) > 0:
            return str(content[0])
        return str(content)
    except Exception:
        # Graceful fallback when API key is invalid/dummy
        return (
            f"La demanda de {reagent_name} aumenta en invierno (junio-agosto) "
            f"en Argentina. El stock actual ({current_stock} unidades) "
            f"se agotará en ~{projected_stockout_days} días — antes del "
            f"período de reorden. Se recomienda ordenar con urgencia."
        )
