# AI Integration Plan: LLM Assistant with MCP Tools

## Overview

Add an in-app AI assistant that can manipulate MESSAGEix scenario parameters via natural language.
Examples:
- "Set GHG targets to 500 Mt at year 2050"
- "Add option to import electricity"
- "Set demand in a linear increase from 100 at 2020 to 300 at 2050"

The LLM reads current parameter data, runs calculations (e.g. linear interpolation), and writes
back modified values using the existing internal ScenarioData API.

---

## Architecture

### Components

1. **MCP Tool Layer** (`src/ai/mcp_tools.py`)
   Python class that wraps `ScenarioData` read/write methods as callable tool functions
   with Anthropic-compatible `input_schema` definitions.

2. **LLM Agent** (`src/ai/llm_agent.py`)
   Uses the Anthropic Messages API with `tool_use`. Runs in a `QThread` (non-blocking).
   Maintains conversation history for multi-turn interactions.

3. **Chat Panel UI** (`src/ui/components/chat_panel_widget.py`)
   Right-side panel (300px) mirroring the left parameter panel in layout position.

---

## UI Layout

```
MainWindow splitter (horizontal, 3 children):
├── leftPanel     [300px]   File navigator + parameter tree (unchanged)
├── contentWidget [grows]   Table/chart/dashboards (unchanged)
└── rightPanel    [300px]   AI chat panel (new)
```

The right panel contains:
```
RightPanel (QWidget, 300px)
├── Header: "AI Assistant" label + clear button
├── conversation_view (QTextEdit, read-only, grows)
└── inputRow (QHBoxLayout)
    ├── input_field (QPlainTextEdit, ~60px)   Enter=send, Shift+Enter=newline
    └── send_button (QPushButton "Send")
```

Messages are color-coded HTML:
- User messages: right-aligned, blue background
- Assistant replies: left-aligned, gray background
- Tool calls: italic, indented (e.g. "📊 Reading fix_cost...")
- Errors: red text

---

## Files to Create

| File | Purpose |
|------|---------|
| `src/ai/__init__.py` | Package init |
| `src/ai/mcp_tools.py` | MCPTools class — tool definitions + execution |
| `src/ai/llm_agent.py` | LLMAgent + LLMWorker (QThread) |
| `src/ui/components/chat_panel_widget.py` | ChatPanelWidget — chat UI |
| `src/ui/components/chat_panel_widget.ui` | Qt Designer layout for chat panel |
| `tests/test_mcp_tools.py` | Unit tests for MCP tool functions |

## Files to Modify

| File | Change |
|------|--------|
| `src/ui/main_window.ui` | Add `rightPanel` as 3rd child of main `splitter` |
| `src/ui/main_window.py` | Instantiate components, wire signals, add accessor methods |
| `src/main.py` | Add `load_dotenv()` for `.env` file support |
| `requirements.txt` | Add `anthropic>=0.30`, `python-dotenv` |

---

## MCP Tools Specification

### Tool Definitions

```python
TOOL_DEFINITIONS = [
    {
        "name": "get_scenario_info",
        "description": "Get overview of the loaded scenario: name, year range, parameter count, set count",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "list_parameters",
        "description": "List all parameters in the scenario with dimensions, units, shape, description",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "get_parameter",
        "description": "Get data rows from a parameter, optionally filtered by dimension values",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Parameter name"},
                "filters": {
                    "type": "object",
                    "description": "Dict of column_name → value for filtering rows",
                    "additionalProperties": {"type": "string"}
                },
                "limit": {"type": "integer", "default": 200, "description": "Max rows to return"}
            },
            "required": ["name"]
        }
    },
    {
        "name": "set_parameter_values",
        "description": "Set values in a parameter. Each row is identified by its dimension values.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "rows": {
                    "type": "array",
                    "description": "List of dicts. Each dict has dimension keys + 'value' key.",
                    "items": {"type": "object"}
                }
            },
            "required": ["name", "rows"]
        }
    },
    {
        "name": "list_sets",
        "description": "List all sets in the scenario with their sizes",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "get_set",
        "description": "Get contents (members) of a specific set",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"]
        }
    },
    {
        "name": "execute_python",
        "description": "Execute Python code for calculations. numpy and pandas are available. Set a variable named 'result' to return a value.",
        "input_schema": {
            "type": "object",
            "properties": {"code": {"type": "string"}},
            "required": ["code"]
        }
    }
]
```

### MCPTools Class

```python
class MCPTools(QObject):
    parameter_changed = pyqtSignal(str)  # emitted after set_parameter_values

    def __init__(self, scenario_accessor: Callable[[], Optional[ScenarioData]],
                 undo_manager_accessor: Callable[[], Optional[UndoManager]]):
        ...

    def dispatch(self, tool_name: str, tool_input: dict) -> str:
        """Route tool call to the correct method. Returns JSON string."""
```

Key implementation notes for `set_parameter_values`:
1. Get parameter from scenario
2. For each row: find matching rows by dimension values (use pandas boolean mask)
3. Update `value` column (or create new row if not found)
4. Use `EditCellCommand` from `commands.py` for undo/redo support
5. Call `scenario.mark_modified(name)`
6. Emit `parameter_changed(name)` signal

For `execute_python`:
- Use `exec()` with restricted namespace: `{'np': numpy, 'pd': pandas, 'math': math}`
- Capture stdout via `io.StringIO`
- Return `{"stdout": ..., "result": ...}` as JSON

---

## LLM Agent

```python
class LLMWorker(QThread):
    token_received = pyqtSignal(str)        # text chunks (for streaming future)
    tool_call_started = pyqtSignal(str)     # tool name
    tool_call_result = pyqtSignal(str, str) # (tool_name, result_summary)
    finished = pyqtSignal(str)              # final assistant text
    error = pyqtSignal(str)

class LLMAgent(QObject):
    """Manages conversation history and spawns LLMWorker per turn."""

    SYSTEM_PROMPT = """You are an AI assistant for MESSAGEix energy modeling.
    You help users read and modify scenario parameters via tools.

    Guidelines:
    - Always read parameter data before modifying (use get_parameter or list_parameters first)
    - Use execute_python for calculations (linear interpolation, unit conversions, etc.)
    - Be explicit about what values you set and why
    - When setting many rows, show a summary of the range set
    - Ask for confirmation before making bulk changes (>20 rows)
    """

    MODEL = "claude-opus-4-6"

    def send_message(self, user_text: str) -> LLMWorker:
        """Append user message to history, return started worker."""
```

Worker loop:
```
1. POST to Anthropic API (messages.create with tools=TOOL_DEFINITIONS)
2. If stop_reason == "tool_use":
   a. For each tool_use block:
      - emit tool_call_started(name)
      - result = mcp_tools.dispatch(name, input)
      - emit tool_call_result(name, result[:200])
   b. Append assistant message + tool_result messages to history
   c. Loop
3. If stop_reason == "end_turn": emit finished(text)
```

---

## ChatPanelWidget (`src/ui/components/chat_panel_widget.py`)

### Class Structure

```python
class ChatPanelWidget(QWidget):
    """Right-side AI chat panel, mirroring the left parameter panel position."""

    task_submitted = pyqtSignal(str)   # emitted when user sends a message

    def __init__(self, parent=None): ...
```

### Layout (defined in `chat_panel_widget.ui`)

```
ChatPanelWidget (QWidget)
└── mainLayout (QVBoxLayout, margins=0)
    ├── headerWidget (QWidget, fixed height ~36px, styled dark bar)
    │   └── headerLayout (QHBoxLayout)
    │       ├── title_label (QLabel "🤖 AI Assistant", bold)
    │       └── clear_btn (QPushButton "✕", flat, right-aligned)
    │
    ├── conversation_view (QTextEdit, read-only, grows)
    │   └── Renders color-coded HTML bubbles (see below)
    │
    └── inputWidget (QWidget, fixed height ~80px)
        └── inputLayout (QVBoxLayout)
            ├── input_field (QPlainTextEdit, ~55px)
            └── btnRow (QHBoxLayout)
                ├── status_label (QLabel, grey, grows)  ← "Thinking..." indicator
                └── send_btn (QPushButton "Send ▶")
```

### Key Methods

```python
def append_user_message(self, text: str):
    """Append right-aligned blue bubble with user text."""

def append_assistant_message(self, text: str):
    """Append left-aligned gray bubble with assistant markdown-converted text."""

def append_tool_call(self, tool_name: str):
    """Append italic indented line: '⚙ Calling list_parameters…'"""

def append_tool_result(self, tool_name: str, summary: str):
    """Append italic indented line: '  ↳ 42 parameters found'"""

def set_thinking(self, thinking: bool):
    """Show/hide 'Thinking…' in status_label; disable/enable send_btn and input_field."""

def clear(self):
    """Clear conversation_view and reset history via llm_agent.clear_history()."""

def _on_send(self):
    """Called on send_btn click or Enter key. Reads input_field, emits task_submitted."""

def _on_input_key_press(self, event: QKeyEvent):
    """Enter = send; Shift+Enter = insert newline."""
```

### Message HTML Templates

```python
# User message — right-aligned bubble
USER_BUBBLE = """
<div style="text-align:right; margin:4px 2px;">
  <span style="background:#1565c0; color:white; border-radius:8px;
               padding:4px 10px; display:inline-block; max-width:90%;">
    {text}
  </span>
</div>"""

# Assistant message — left-aligned bubble
ASSISTANT_BUBBLE = """
<div style="text-align:left; margin:4px 2px;">
  <span style="background:#e0e0e0; color:#111; border-radius:8px;
               padding:4px 10px; display:inline-block; max-width:90%;">
    {text}
  </span>
</div>"""

# Tool call — indented italic
TOOL_LINE = """
<div style="margin:1px 10px; color:#666; font-style:italic; font-size:11px;">
  ⚙ {tool_name}…
</div>"""

# Tool result — indented, lighter
RESULT_LINE = """
<div style="margin:1px 20px; color:#888; font-size:11px;">
  ↳ {summary}
</div>"""

# Error
ERROR_LINE = """
<div style="margin:4px 2px; color:#c62828; font-size:11px;">
  ⚠ {message}
</div>"""
```

Text in bubbles is HTML-escaped. Assistant replies are converted from markdown to HTML using a
minimal inline converter (bold `**`, code `` ` ``, newlines → `<br>`).

---

## Integration in main_window.py

### 1. UI file change (`src/ui/main_window.ui`)

Add a `rightPanel` QWidget as the **3rd child** of the main `splitter` (after `contentWidget`).
It only needs a vertical layout and a placeholder child — Python will swap it out:

```xml
<widget class="QWidget" name="rightPanel">
  <layout class="QVBoxLayout" name="rightPanelLayout">
    <property name="leftMargin"><number>0</number></property>
    <property name="topMargin"><number>0</number></property>
    <property name="rightMargin"><number>0</number></property>
    <property name="bottomMargin"><number>0</number></property>
  </layout>
</widget>
```

### 2. Instantiation — end of `__init__` (after `self.undo_manager = UndoManager()`)

```python
# AI assistant components
from src.ai.mcp_tools import MCPTools
from src.ai.llm_agent import LLMAgent
from src.ui.components.chat_panel_widget import ChatPanelWidget

self.mcp_tools = MCPTools(
    scenario_accessor=self._get_current_scenario_data,
    undo_manager_accessor=lambda: self.undo_manager
)
self.llm_agent = LLMAgent(self.mcp_tools)
self.chat_panel = ChatPanelWidget()
```

(Placing after `self.undo_manager` ensures both accessors resolve correctly.)

### 3. `_setup_ui_components()` additions

After the existing `self.splitter.setSizes([300, 900])` block, update sizes and factors for the
3-panel layout and insert the chat panel into `rightPanel`:

```python
# Resize main splitter to 3 panels
self.splitter.setSizes([300, 900, 300])
self.splitter.setStretchFactor(0, 0)  # left panel fixed
self.splitter.setStretchFactor(1, 1)  # content area stretches
self.splitter.setStretchFactor(2, 0)  # right panel fixed
```

### 4. `_initialize_components_with_ui_widgets()` addition

After the existing navigator/param_tree replacement block, insert the chat panel into the right panel:

```python
# Insert chat panel into rightPanel layout
right_layout = self.rightPanel.layout()
right_layout.addWidget(self.chat_panel)
```

### 5. `_connect_component_signals()` additions

```python
# Chat panel signals
self.chat_panel.task_submitted.connect(self._on_chat_task_submitted)
self.mcp_tools.parameter_changed.connect(self._on_parameter_changed_by_ai)

# Worker signals are connected dynamically in _on_chat_task_submitted
```

### 6. New handler methods

```python
def _on_chat_task_submitted(self, text: str):
    """Handle user message submission: spawn LLM worker thread."""
    self.chat_panel.append_user_message(text)
    self.chat_panel.set_thinking(True)
    worker = self.llm_agent.send_message(text)
    worker.tool_call_started.connect(self.chat_panel.append_tool_call)
    worker.tool_call_result.connect(self.chat_panel.append_tool_result)
    worker.finished.connect(self._on_llm_finished)
    worker.error.connect(self._on_llm_error)
    worker.start()

def _on_llm_finished(self, reply: str):
    self.chat_panel.set_thinking(False)
    self.chat_panel.append_assistant_message(reply)

def _on_llm_error(self, error: str):
    self.chat_panel.set_thinking(False)
    self.chat_panel.append_error(error)

def _on_parameter_changed_by_ai(self, param_name: str):
    """Refresh the displayed table if the AI just changed the current parameter."""
    if self.current_displayed_parameter == param_name:
        scenario = self._get_current_scenario(is_results=False)
        if scenario:
            param = scenario.data.get_parameter(param_name)
            if param:
                self.data_display.display_parameter_data(param, is_results=False)

def _get_current_scenario_data(self) -> Optional[ScenarioData]:
    """Accessor passed to MCPTools — returns the active input ScenarioData."""
    scenario = self._get_current_scenario(is_results=False)
    return scenario.data if scenario else None
```

---

## API Key

- Primary: `ANTHROPIC_API_KEY` environment variable
- `.env` file support via `python-dotenv` (loaded in `src/main.py` at startup)
- If key is missing, chat panel shows a warning message instead of crashing

---

## Undo/Redo Integration

`set_parameter_values` in MCPTools uses `EditCellCommand` objects (from `src/managers/commands.py`)
executed through the `UndoManager`. This means AI changes appear in the undo stack and can be
reversed with Ctrl+Z.

---

## Tests Required (`tests/test_mcp_tools.py`)

Create `tests/test_mcp_tools.py` to unit-test the tool layer without needing a real LLM call.
Use a mock `ScenarioData` populated with sample parameters.

### Test Cases

```python
class TestMCPTools:

    @pytest.fixture
    def scenario(self):
        """ScenarioData with fix_cost and demand parameters + technology set."""
        ...

    @pytest.fixture
    def tools(self, scenario):
        return MCPTools(scenario_accessor=lambda: scenario, undo_manager_accessor=lambda: None)

    # --- list_parameters ---
    def test_list_parameters_returns_all(self, tools, scenario):
        result = json.loads(tools.list_parameters())
        names = [r["name"] for r in result]
        assert "fix_cost" in names and "demand" in names

    def test_list_parameters_includes_metadata(self, tools):
        result = json.loads(tools.list_parameters())
        entry = result[0]
        assert "dims" in entry and "units" in entry and "shape" in entry

    # --- get_parameter ---
    def test_get_parameter_returns_rows(self, tools):
        result = json.loads(tools.get_parameter("fix_cost"))
        assert len(result) > 0

    def test_get_parameter_with_filter(self, tools):
        result = json.loads(tools.get_parameter("fix_cost", filters={"technology": "coal_ppl"}))
        for row in result:
            assert row["technology"] == "coal_ppl"

    def test_get_parameter_unknown_raises_graceful(self, tools):
        result = json.loads(tools.get_parameter("nonexistent"))
        assert "error" in result

    def test_get_parameter_limit(self, tools):
        result = json.loads(tools.get_parameter("fix_cost", limit=2))
        assert len(result) <= 2

    # --- set_parameter_values ---
    def test_set_parameter_updates_value(self, tools, scenario):
        tools.set_parameter_values("fix_cost", [
            {"node": "World", "technology": "coal_ppl", "year_vtg": 2030, "year_act": 2030, "value": 999.0}
        ])
        param = scenario.get_parameter("fix_cost")
        mask = (param.df["technology"] == "coal_ppl") & (param.df["year_act"] == 2030)
        assert param.df.loc[mask, "value"].iloc[0] == 999.0

    def test_set_parameter_marks_modified(self, tools, scenario):
        tools.set_parameter_values("fix_cost", [
            {"node": "World", "technology": "coal_ppl", "year_vtg": 2030, "year_act": 2030, "value": 1.0}
        ])
        assert "fix_cost" in scenario.get_modified_parameters()

    def test_set_parameter_emits_signal(self, tools, qtbot):
        with qtbot.waitSignal(tools.parameter_changed, timeout=1000) as blocker:
            tools.set_parameter_values("fix_cost", [
                {"node": "World", "technology": "coal_ppl", "year_vtg": 2030, "year_act": 2030, "value": 1.0}
            ])
        assert blocker.args[0] == "fix_cost"

    def test_set_parameter_unknown_graceful(self, tools):
        result = json.loads(tools.set_parameter_values("nonexistent", [{"value": 1.0}]))
        assert "error" in result

    # --- list_sets / get_set ---
    def test_list_sets(self, tools):
        result = json.loads(tools.list_sets())
        assert isinstance(result, list)

    def test_get_set_returns_members(self, tools, scenario):
        result = json.loads(tools.get_set("technology"))
        assert "coal_ppl" in result

    def test_get_set_unknown_graceful(self, tools):
        result = json.loads(tools.get_set("nonexistent"))
        assert "error" in result

    # --- execute_python ---
    def test_execute_python_basic(self, tools):
        result = json.loads(tools.execute_python("result = 2 + 2"))
        assert result["result"] == 4

    def test_execute_python_numpy(self, tools):
        result = json.loads(tools.execute_python("result = list(np.linspace(0, 10, 3))"))
        assert result["result"] == [0.0, 5.0, 10.0]

    def test_execute_python_stdout(self, tools):
        result = json.loads(tools.execute_python("print('hello')"))
        assert "hello" in result["stdout"]

    def test_execute_python_error_graceful(self, tools):
        result = json.loads(tools.execute_python("raise ValueError('bad')"))
        assert "error" in result

    # --- dispatch ---
    def test_dispatch_routes_correctly(self, tools):
        result = tools.dispatch("list_parameters", {})
        assert isinstance(json.loads(result), list)

    def test_dispatch_unknown_tool(self, tools):
        result = json.loads(tools.dispatch("unknown_tool", {}))
        assert "error" in result

    # --- get_scenario_info ---
    def test_get_scenario_info(self, tools):
        result = json.loads(tools.get_scenario_info())
        assert "parameter_count" in result

    def test_get_scenario_info_no_scenario(self):
        tools = MCPTools(scenario_accessor=lambda: None, undo_manager_accessor=lambda: None)
        result = json.loads(tools.get_scenario_info())
        assert "error" in result or result.get("parameter_count") == 0
```

Run with: `pytest tests/test_mcp_tools.py -v`

---

## Documentation Updates

### 1. `CLAUDE.md` — Project Structure section

Add `src/ai/` to the project tree:
```
src/
├── ai/                     # AI assistant layer
│   ├── __init__.py               # Package init
│   ├── mcp_tools.py              # MCPTools: tool definitions + execution against ScenarioData
│   └── llm_agent.py              # LLMAgent + LLMWorker (QThread) using Anthropic API
```

Add to the **Key Classes** table:
| Class | Description |
|-------|-------------|
| `MCPTools` | Exposes ScenarioData read/write as Anthropic tool_use functions; emits `parameter_changed` signal after writes |
| `LLMAgent` | Manages conversation history; spawns `LLMWorker` per turn |
| `LLMWorker` | QThread that calls Anthropic API in a loop, dispatching tool calls via `MCPTools` |
| `ChatPanelWidget` | Right-side chat UI panel; HTML-rendered conversation bubbles; Enter-to-send input |

Add to **Important Files** table:
| File | Purpose |
|------|---------|
| `src/ai/mcp_tools.py` | Tool definitions + dispatch; wraps ScenarioData for LLM access |
| `src/ai/llm_agent.py` | LLM conversation loop with tool_use |
| `src/ui/components/chat_panel_widget.py` | Chat panel UI |

Add to **Dependencies**:
- **anthropic**: Anthropic Python SDK for Claude API
- **python-dotenv**: Load `.env` file for `ANTHROPIC_API_KEY`

### 2. `CLAUDE.md` — Architecture section

Add a new **AI / MCP Tool Layer** subsection:

```
AI / MCP Tool Layer:
- MCPTools wraps ScenarioData read/write behind tool functions with Anthropic input_schema
- LLMAgent maintains conversation history; model is claude-opus-4-6
- LLMWorker (QThread) runs the tool_use loop: POST → parse → dispatch → repeat until end_turn
- API key from ANTHROPIC_API_KEY env var or .env file (loaded at startup via python-dotenv)
- AI writes use EditCellCommand for undo/redo integration
- parameter_changed signal triggers UI table refresh after AI edits
```

### 3. New file: `docs/ai_integration_plan.md` (this file)

Already created — serves as the reference for the implementation.

---

## Verification Plan

1. Load an input `.xlsx` scenario in the app
2. Type in chat: "What parameters are available?" → LLM calls `list_parameters`, returns list
3. Type: "Show me the fix_cost parameter for coal_ppl" → LLM calls `get_parameter`, shows data
4. Type: "Set fix_cost for coal_ppl in World at 2030 to 500" → LLM calls `set_parameter_values`,
   table refreshes with new value visible
5. Press Ctrl+Z → change is undone
6. Type: "Set demand in a linear increase from 100 at 2020 to 300 at 2050" →
   LLM calls `execute_python` with `np.linspace(...)`, then `set_parameter_values` for all years
7. Run tests: `pytest tests/test_mcp_tools.py -v`
