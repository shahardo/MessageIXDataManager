"""Tests for the chat history persistence module."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def tmp_history_dir(tmp_path, monkeypatch):
    """Redirect the history directory to a temp folder for all tests."""
    import ai.chat_history as ch
    monkeypatch.setattr(ch, '_HISTORY_DIR', tmp_path / 'chat_history')
    return tmp_path / 'chat_history'


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_save_and_load_roundtrip():
    from ai.chat_history import save_history, load_history

    history = [
        {'role': 'user', 'content': 'Hello'},
        {'role': 'assistant', 'content': 'Hi there!'},
    ]
    save_history('/path/to/scenario.xlsx', history, 'anthropic')
    result = load_history('/path/to/scenario.xlsx')

    assert result is not None
    assert result['provider'] == 'anthropic'
    assert len(result['history']) == 2
    assert result['history'][0]['content'] == 'Hello'
    assert result['history'][1]['content'] == 'Hi there!'


def test_load_nonexistent_returns_none():
    from ai.chat_history import load_history

    result = load_history('/does/not/exist.xlsx')
    assert result is None


def test_different_keys_are_isolated():
    from ai.chat_history import save_history, load_history

    save_history('/scenario_a.xlsx', [{'role': 'user', 'content': 'A'}], 'anthropic')
    save_history('/scenario_b.xlsx', [{'role': 'user', 'content': 'B'}], 'groq')

    a = load_history('/scenario_a.xlsx')
    b = load_history('/scenario_b.xlsx')

    assert a['history'][0]['content'] == 'A'
    assert a['provider'] == 'anthropic'
    assert b['history'][0]['content'] == 'B'
    assert b['provider'] == 'groq'


def test_delete_history():
    from ai.chat_history import save_history, load_history, delete_history

    save_history('/scenario.xlsx', [{'role': 'user', 'content': 'Hi'}], 'anthropic')
    assert load_history('/scenario.xlsx') is not None

    delete_history('/scenario.xlsx')
    assert load_history('/scenario.xlsx') is None


def test_delete_nonexistent_is_safe():
    from ai.chat_history import delete_history
    # Should not raise
    delete_history('/nonexistent/path.xlsx')


def test_save_with_sdk_objects():
    """SDK content-block objects (with __dict__) should be serialised gracefully."""
    from ai.chat_history import save_history, load_history

    class FakeBlock:
        def __init__(self):
            self.type = 'text'
            self.text = 'Hello from SDK'

    history = [
        {'role': 'assistant', 'content': [FakeBlock()]},
    ]
    save_history('/scenario.xlsx', history, 'anthropic')
    result = load_history('/scenario.xlsx')
    assert result is not None
    # The content block should have been serialised as a dict
    block = result['history'][0]['content'][0]
    assert isinstance(block, dict)
    assert block.get('text') == 'Hello from SDK'


def test_provider_preserved():
    from ai.chat_history import save_history, load_history

    save_history('/s.xlsx', [], 'groq')
    result = load_history('/s.xlsx')
    assert result['provider'] == 'groq'
