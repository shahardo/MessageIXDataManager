"""
LLM agent layer for the AI assistant.

Supports two providers:
  - Anthropic  (claude-opus-4-6, tool_use loop via anthropic SDK)
  - Groq       (openai/gpt-oss-120b, function-calling loop via groq SDK)

Classes:
    Provider   — String constants for provider names.
    LLMWorker  — QThread that runs one conversation turn for either provider.
    LLMAgent   — Manages conversation history and spawns LLMWorker per turn.
"""

import json
from typing import List, Optional

from PyQt5.QtCore import QObject, QThread, pyqtSignal

from ai.mcp_tools import MCPTools, TOOL_DEFINITIONS, TOOL_DEFINITIONS_OPENAI


# ---------------------------------------------------------------------------
# Provider constants
# ---------------------------------------------------------------------------

class Provider:
    ANTHROPIC = "anthropic"
    GROQ = "groq"


# ---------------------------------------------------------------------------
# Model / config
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are an AI assistant embedded in the MessageIX Data Manager desktop application.
You help users read and modify MESSAGEix energy-system scenario parameters.

Available tools let you:
  - Inspect the scenario (get_scenario_info, list_parameters, list_sets, get_set)
  - Read parameter data (get_parameter)
  - Write parameter data (set_parameter_values)
  - Run Python calculations (execute_python) — numpy (np) and pandas (pd) are available

Guidelines:
  - Always read parameter data before modifying it (call get_parameter or list_parameters first).
  - Use execute_python for any calculations: linear interpolation, unit conversion, np.linspace, etc.
  - Be explicit about every value you set and why.
  - When setting many rows summarise the range (e.g. "set demand from 100 in 2020 to 300 in 2050").
  - If a task would change more than 20 rows ask the user to confirm before proceeding.
  - Dimension names must match exactly — use list_parameters to check column names first.
"""

ANTHROPIC_MODEL = "claude-opus-4-6"
GROQ_MODEL = "openai/gpt-oss-120b"
MAX_TOKENS = 4096


# ---------------------------------------------------------------------------
# Worker thread
# ---------------------------------------------------------------------------

class LLMWorker(QThread):
    """Runs one LLM conversation turn in a background thread.

    Routes to the correct provider loop (_run_anthropic or _run_groq).

    Signals:
        tool_call_started(str):        Tool name being invoked.
        tool_call_result(str, str):    (tool_name, first 300 chars of result).
        finished(str):                 Final assistant text reply.
        error(str):                    Error message if something goes wrong.
    """

    tool_call_started = pyqtSignal(str)
    tool_call_result = pyqtSignal(str, str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, history: list, mcp_tools: MCPTools,
                 provider: str = Provider.ANTHROPIC, parent=None):
        super().__init__(parent)
        self._history = list(history)   # copy — agent syncs after success
        self._mcp_tools = mcp_tools
        self._provider = provider

    def run(self):
        if self._provider == Provider.ANTHROPIC:
            self._run_anthropic()
        elif self._provider == Provider.GROQ:
            self._run_groq()
        else:
            self.error.emit(f"Unknown provider: {self._provider!r}")

    # ------------------------------------------------------------------
    # Anthropic loop
    # ------------------------------------------------------------------

    def _run_anthropic(self):
        try:
            import anthropic
        except ImportError:
            self.error.emit("The 'anthropic' package is not installed. Run: pip install anthropic")
            return

        try:
            client = anthropic.Anthropic()   # reads ANTHROPIC_API_KEY from env
        except Exception as exc:
            self.error.emit(f"Failed to create Anthropic client: {exc}")
            return

        try:
            while True:
                response = client.messages.create(
                    model=ANTHROPIC_MODEL,
                    system=SYSTEM_PROMPT,
                    messages=self._history,
                    tools=TOOL_DEFINITIONS,
                    max_tokens=MAX_TOKENS,
                )

                if response.stop_reason == "end_turn":
                    text = "\n".join(
                        block.text for block in response.content if hasattr(block, "text")
                    )
                    self._history.append({"role": "assistant", "content": response.content})
                    self.finished.emit(text)
                    break

                elif response.stop_reason == "tool_use":
                    tool_results = []
                    for block in response.content:
                        if block.type != "tool_use":
                            continue
                        self.tool_call_started.emit(block.name)
                        result_str = self._mcp_tools.dispatch(block.name, block.input)
                        self.tool_call_result.emit(block.name, result_str[:300])
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_str,
                        })
                    self._history.append({"role": "assistant", "content": response.content})
                    self._history.append({"role": "user", "content": tool_results})

                else:
                    text = "\n".join(
                        block.text for block in response.content if hasattr(block, "text")
                    )
                    self._history.append({"role": "assistant", "content": response.content})
                    self.finished.emit(text)
                    break

        except Exception as exc:
            self.error.emit(f"Anthropic error: {type(exc).__name__}: {exc}")

    # ------------------------------------------------------------------
    # Groq loop (OpenAI-compatible function calling)
    # ------------------------------------------------------------------

    def _run_groq(self):
        try:
            from groq import Groq
        except ImportError:
            self.error.emit("The 'groq' package is not installed. Run: pip install groq")
            return

        try:
            client = Groq()   # reads GROQ_API_KEY from env
        except Exception as exc:
            self.error.emit(f"Failed to create Groq client: {exc}")
            return

        # For Groq/OpenAI the system message lives inside the messages array.
        messages_for_api = [{"role": "system", "content": SYSTEM_PROMPT}] + self._history

        try:
            while True:
                response = client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=messages_for_api,
                    tools=TOOL_DEFINITIONS_OPENAI,
                    tool_choice="auto",
                    max_tokens=MAX_TOKENS,
                )
                msg = response.choices[0].message

                if msg.tool_calls:
                    # Build assistant history entry with tool_calls
                    assistant_entry = {
                        "role": "assistant",
                        "content": msg.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                },
                            }
                            for tc in msg.tool_calls
                        ],
                    }
                    messages_for_api.append(assistant_entry)
                    self._history.append(assistant_entry)

                    for tc in msg.tool_calls:
                        self.tool_call_started.emit(tc.function.name)
                        try:
                            tool_input = json.loads(tc.function.arguments)
                        except json.JSONDecodeError:
                            tool_input = {}
                        result_str = self._mcp_tools.dispatch(tc.function.name, tool_input)
                        self.tool_call_result.emit(tc.function.name, result_str[:300])
                        tool_entry = {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": result_str,
                        }
                        messages_for_api.append(tool_entry)
                        self._history.append(tool_entry)

                else:
                    # No tool calls — final reply
                    text = msg.content or ""
                    assistant_entry = {"role": "assistant", "content": text}
                    self._history.append(assistant_entry)
                    self.finished.emit(text)
                    break

        except Exception as exc:
            self.error.emit(f"Groq error: {type(exc).__name__}: {exc}")

    def get_updated_history(self) -> list:
        """Return the history updated during this run (call after finished)."""
        return self._history


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class LLMAgent(QObject):
    """Manages conversation history and spawns an LLMWorker per user turn.

    Usage::

        agent = LLMAgent(mcp_tools)
        agent.provider = Provider.GROQ          # switch provider (clears history)
        worker = agent.send_message("Set GHG target to 500 Mt in 2050")
        worker.finished.connect(on_done)
        worker.start()
    """

    def __init__(self, mcp_tools: MCPTools,
                 provider: str = Provider.ANTHROPIC,
                 parent: Optional[QObject] = None):
        super().__init__(parent)
        self._mcp_tools = mcp_tools
        self._history: List[dict] = []
        self._provider = provider

    # ------------------------------------------------------------------
    # Provider property — clears history when switching
    # ------------------------------------------------------------------

    @property
    def provider(self) -> str:
        return self._provider

    @provider.setter
    def provider(self, value: str):
        if value != self._provider:
            self._provider = value
            self._history = []   # incompatible formats between providers

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def send_message(self, user_text: str) -> LLMWorker:
        """Append a user message and return a worker ready to be started."""
        self._history.append({"role": "user", "content": user_text})
        worker = LLMWorker(self._history, self._mcp_tools, self._provider, parent=self)
        worker.finished.connect(lambda _: self._sync_history(worker))
        return worker

    def _sync_history(self, worker: LLMWorker):
        """Replace internal history with the worker's completed history."""
        self._history = worker.get_updated_history()

    def clear_history(self):
        """Reset the conversation to a clean state."""
        self._history = []

    def get_history(self) -> list:
        """Return a copy of the current conversation history."""
        return list(self._history)

    def set_history(self, history: list) -> None:
        """Replace conversation history (e.g. when restoring a saved session)."""
        self._history = list(history)
