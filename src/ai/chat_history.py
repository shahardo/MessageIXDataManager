"""
Chat history persistence for the AI assistant.

Stores conversation history per scenario file path so that sessions
survive app restarts.  History is saved as JSON in the user's app-data
directory (same folder used by SessionManager).
"""

import hashlib
import json
from pathlib import Path
from typing import List, Optional


# Directory where history files are written — inside the project root
# so they stay alongside the scenario files and are easy to find.
# src/ai/chat_history.py → parents[2] = project root
_HISTORY_DIR = Path(__file__).resolve().parents[2] / '.chat_history'


def _history_path(scenario_key: str) -> Path:
    """Return the JSON file path for the given scenario key."""
    # Hash the key so file names stay short and safe on all platforms
    safe = hashlib.sha1(scenario_key.encode('utf-8')).hexdigest()[:16]
    return _HISTORY_DIR / f'chat_{safe}.json'


def get_history_dir() -> Path:
    """Return (and create) the directory where history files are stored."""
    _HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    return _HISTORY_DIR


def save_history(
    scenario_key: str,
    history: List[dict],
    provider: str,
) -> None:
    """Persist conversation history and selected provider for a scenario.

    Args:
        scenario_key: Typically the absolute path of the input file,
                      or a fallback string when no file is loaded.
        history:      The LLMAgent._history list (plain dicts only —
                      Anthropic SDK objects are NOT JSON-serialisable and
                      are silently dropped).
        provider:     The Provider constant string ('anthropic' or 'groq').
    """
    get_history_dir()  # ensure directory exists
    path = _history_path(scenario_key)
    print(f"ChatHistory: saving to {path}")

    serialisable = _make_serialisable(history)
    payload = {
        'scenario_key': scenario_key,
        'provider': provider,
        'history': serialisable,
    }
    try:
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
    except OSError as exc:
        print(f"ChatHistory: could not save history: {exc}")


def load_history(scenario_key: str) -> Optional[dict]:
    """Load persisted history for a scenario.

    Returns a dict with keys 'history' (list) and 'provider' (str),
    or None if no saved history exists.
    """
    path = _history_path(scenario_key)
    if not path.exists():
        return None
    try:
        with open(path, 'r', encoding='utf-8') as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ChatHistory: could not load history: {exc}")
        return None


def delete_history(scenario_key: str) -> None:
    """Remove the saved history for a scenario (e.g. on Clear)."""
    path = _history_path(scenario_key)
    try:
        if path.exists():
            path.unlink()
    except OSError as exc:
        print(f"ChatHistory: could not delete history: {exc}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_serialisable(obj):
    """Recursively convert history to JSON-safe plain Python.

    Anthropic SDK content blocks (which are typed dataclass objects) are
    converted to plain dicts where possible; non-serialisable objects are
    dropped so the history stays valid.
    """
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, dict):
        return {k: _make_serialisable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_make_serialisable(v) for v in obj]
    # Anthropic content block objects (TextBlock, ToolUseBlock, etc.)
    # expose their fields via __dict__ or via a model_dump / to_dict method.
    if hasattr(obj, 'model_dump'):
        try:
            return _make_serialisable(obj.model_dump())
        except Exception:
            pass
    if hasattr(obj, '__dict__'):
        try:
            return _make_serialisable(vars(obj))
        except Exception:
            pass
    # Last resort: convert to string so nothing is lost entirely
    return str(obj)
