import json
from functools import lru_cache
from typing import Dict, Any, Optional
from pathlib import Path


CONFIG_PATH = Path(__file__).resolve().parents[1] / "figma_screens.json"


@lru_cache(maxsize=1)
def load_figma_screens() -> Dict[str, Any]:
    """Load and return the figma_screens.json content as a dict."""
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def get_screen_config(screen_id: str) -> Optional[Dict[str, Any]]:
    """Return config for a single screen_id (case-insensitive).

    Returns None if not found.
    """
    data = load_figma_screens()
    if not data:
        return None
    # case-insensitive lookup
    key = screen_id.strip().lower()
    for k, v in data.items():
        if k.lower() == key:
            return v
    return None


def list_screens() -> Dict[str, Any]:
    """Return the full mapping of screen_id -> config."""
    return load_figma_screens()
