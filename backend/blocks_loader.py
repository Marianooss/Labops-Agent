"""blocks_loader.py — Load Block Kit / Canvas JSON templates from blocks/.

Usage:
    from blocks_loader import load_template
    blocks = load_template("alert", reagent_name="TSH", current_stock=680, ...)
"""
import json
import os
from typing import Any, Dict, List

BLOCKS_DIR = os.path.join(os.path.dirname(__file__), "..", "blocks")


def load_template(name: str, **kwargs) -> Dict[str, Any]:
    """Load a JSON template and replace {{key}} placeholders."""
    path = os.path.join(BLOCKS_DIR, f"{name}.json")
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()

    for key, value in kwargs.items():
        raw = raw.replace(f"{{{{{key}}}}}", str(value))

    return json.loads(raw)
