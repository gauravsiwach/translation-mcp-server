"""Figma screen configuration utilities.

Provides functions for loading screen configurations from figma_screens.json.
"""
from typing import Optional, Dict, Any
import json
import os


def get_screen_config(screen_id: str) -> Optional[Dict[str, Any]]:
    """Get screen configuration from figma_screens.json.
    
    Args:
        screen_id: Screen identifier (e.g., "home", "basket")
        
    Returns:
        Dict with figma_file_key, figma_page_name, nodes or None
    """
    config_path = os.path.join(os.path.dirname(__file__), "..", "figma_screens.json")
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            return config.get(screen_id)
    except Exception as exc:
        return None
