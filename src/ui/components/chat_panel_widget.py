"""
Chat panel widget for the AI assistant.

Displayed as the right-side panel in the main window.  Shows a conversation
view with HTML-rendered messages and a plain-text input field.
"""

import html
import os
import re
from typing import Optional

from PyQt5 import uic
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtWidgets import QWidget


# ---------------------------------------------------------------------------
# Greeting shown when the conversation is empty
# ---------------------------------------------------------------------------

_GREETING = (
    "Hi! I'm an AI agent specialised in MESSAGEix energy-system modelling. "
    "I can read and modify scenario parameters, run calculations, and answer "
    "questions about your model. Load a scenario and ask me anything."
)

# Font stack with emoji support (used in styles throughout).
# Emoji fonts are listed FIRST so Qt selects one as the primary font;
# 'Segoe UI Emoji' on Windows contains full Latin glyphs + color emoji.
_EMOJI_FONT = ("'Segoe UI Emoji', 'Apple Color Emoji', 'Noto Color Emoji', "
               "'Segoe UI', sans-serif")


# ---------------------------------------------------------------------------
# HTML message templates
# ---------------------------------------------------------------------------

# User message: table-based pill so padding is guaranteed in Qt's HTML renderer.
# Qt supports cellpadding/cellspacing attributes on <table> elements reliably.
# Note: border-radius is NOT supported by Qt's HTML renderer.
_USER_BUBBLE = (
    '<table cellpadding="10" cellspacing="0" '
    'style="background:#dedede; border:1px solid #c0c0c0; '
    'margin:6px 4px 4px 40px; width:auto;">'
    '<tr>'
    f'<td style="color:#212121; font-size:12px; font-weight:500; '
    f'font-family:{_EMOJI_FONT}; white-space:normal;">'
    '{text}'
    '</td>'
    '</tr>'
    '</table>'
)

_ASSISTANT_BUBBLE = (
    '<div style="margin:2px 4px 8px 4px; '
    f'color:#212121; font-size:12px; line-height:1.5; font-family:{_EMOJI_FONT};">'
    '{text}'
    '</div>'
)

_TOOL_LINE = (
    '<div style="margin:1px 8px; color:#546e7a; font-style:italic; font-size:11px;">'
    '⚙ {tool_name}…'
    '</div>'
)

_RESULT_LINE = (
    '<div style="margin:1px 18px 3px; color:#78909c; font-size:11px;">'
    '↳ {summary}'
    '</div>'
)

_ERROR_LINE = (
    '<div style="margin:4px 4px; color:#c62828; font-size:11px; '
    'background:#ffebee; border-radius:4px; padding:4px 8px;">'
    '⚠ {message}'
    '</div>'
)


# ---------------------------------------------------------------------------
# Markdown → HTML conversion
# ---------------------------------------------------------------------------

def _md_to_html(text: str) -> str:
    """Full GFM Markdown → HTML conversion for assistant replies."""
    parts = _split_code_blocks(text)
    result = []
    for ptype, pdata in parts:
        if ptype == 'code':
            lang, code = pdata
            result.append(_code_block_html(lang, code))
        else:
            for ttype, ttext in _split_tables(pdata):
                if ttype == 'table':
                    result.append(_table_to_html(ttext))
                else:
                    result.append(_process_blocks(ttext))
    return ''.join(result)


# ------------------------------------------------------------------
# Code-block helpers
# ------------------------------------------------------------------

def _split_code_blocks(text: str):
    """Split on fenced code blocks (``` ... ```)."""
    pattern = re.compile(r'```(\w*)\n?([\s\S]*?)```', re.MULTILINE)
    parts: list = []
    last = 0
    for m in pattern.finditer(text):
        if m.start() > last:
            parts.append(('text', text[last:m.start()]))
        parts.append(('code', (m.group(1), m.group(2))))
        last = m.end()
    if last < len(text):
        parts.append(('text', text[last:]))
    return parts


# Emoji fonts are placed right after Consolas so Qt falls back to them for
# emoji glyphs that Consolas doesn't have, while keeping monospace rendering
# for regular code characters.
_CODE_FONT = ("'Consolas', 'Segoe UI Emoji', 'Apple Color Emoji', 'Noto Color Emoji', "
              "'Courier New', monospace")


def _code_block_html(lang: str, code: str) -> str:
    """Render a fenced code block with an optional language pill.

    Uses white-space:pre (no wrapping) so long lines extend beyond the block.
    The QTextEdit's horizontal scroll bar (enabled in _setup_conversation_view)
    lets the user scroll right to see the full line.
    """
    safe = html.escape(code)
    pre_style = (
        'background:#e0e0e0; border:1px solid #bbb; '
        'padding:10px 14px; margin:0 0 6px; font-size:11px; '
        f'font-family:{_CODE_FONT}; '
        'white-space:pre; overflow-x:auto; width: 100%;'
    )
    if lang:
        pill = (
            f'<p style="margin:4px 0 0; padding:3px 10px; '
            f'background:#c8c8c8; border-radius:4px 4px 0 0; '
            f'font-size:10px; font-family:monospace; color:#444;">'
            f'{html.escape(lang)}</p>'
        )
        pre_style += ' border-radius:0 0 4px 4px;'
    else:
        pill = ''
        pre_style += ' border-radius:4px; margin-top:4px;'
    return f'{pill}<pre style="{pre_style}"><code>{safe}</code></pre>'


# ------------------------------------------------------------------
# Table helpers
# ------------------------------------------------------------------

# A separator row contains only pipes, hyphens, colons, and spaces
# and must include at least three consecutive hyphens.
_TABLE_SEP_RE = re.compile(r'^[\s|:]*---[-|:\s]*$')


def _split_tables(text: str):
    """Split text into ('table', ...) and ('text', ...) pairs."""
    lines = text.split('\n')
    result: list = []
    i = 0
    while i < len(lines):
        # Detect table: current line has pipes AND next line is a separator
        if ('|' in lines[i]
                and i + 1 < len(lines)
                and _TABLE_SEP_RE.match(lines[i + 1].strip())):
            j = i
            while j < len(lines) and ('|' in lines[j] or lines[j].strip() == ''):
                # Stop at truly blank lines (not just pipe-free separator rows)
                if lines[j].strip() == '' and j > i + 1:
                    break
                j += 1
            result.append(('table', '\n'.join(lines[i:j])))
            i = j
        else:
            start = i
            while i < len(lines):
                if ('|' in lines[i]
                        and i + 1 < len(lines)
                        and _TABLE_SEP_RE.match(lines[i + 1].strip())):
                    break
                i += 1
            result.append(('text', '\n'.join(lines[start:i])))
    return result


def _table_to_html(table_text: str) -> str:
    """Convert a GFM pipe table to a styled HTML table.

    Applies inline markdown to cell content, and treats `<br>` in cells
    as a line break (common when AI uses HTML for cell newlines).
    """
    rows = [r for r in table_text.strip().splitlines() if r.strip()]
    if len(rows) < 2:
        return html.escape(table_text)

    def parse_row(row: str) -> list:
        return [c.strip() for c in row.strip().strip('|').split('|')]

    def render_cell(text: str) -> str:
        """HTML-escape then apply inline markdown; restore <br> breaks."""
        escaped = html.escape(text)
        # Restore <br> that the AI may have placed in cell text
        escaped = re.sub(r'&lt;br\s*/?&gt;', '<br>', escaped, flags=re.IGNORECASE)
        return _apply_inline(escaped)

    header = parse_row(rows[0])
    data_rows = [parse_row(r) for r in rows[2:]]

    th_s = (f'background:#f0f0f0; padding:4px 10px; border:1px solid #ccc; '
            f'font-size:11px; font-family:{_EMOJI_FONT};')
    td_s = (f'padding:4px 10px; border:1px solid #ccc; '
            f'font-size:11px; font-family:{_EMOJI_FONT};')

    buf = ['<table style="border-collapse:collapse; margin:4px 0;"><thead><tr>']
    for cell in header:
        buf.append(f'<th style="{th_s}">{render_cell(cell)}</th>')
    buf.append('</tr></thead><tbody>')
    for row in data_rows:
        buf.append('<tr>')
        for cell in row:
            buf.append(f'<td style="{td_s}">{render_cell(cell)}</td>')
        buf.append('</tr>')
    buf.append('</tbody></table>')
    return ''.join(buf)


# ------------------------------------------------------------------
# Block and inline markdown
# ------------------------------------------------------------------

def _apply_inline(escaped: str) -> str:
    """Apply inline markdown to already HTML-escaped text."""
    # Bold
    escaped = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', escaped)
    escaped = re.sub(r'__(.+?)__', r'<b>\1</b>', escaped)
    # Italic (avoid matching ** or __)
    escaped = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', escaped)
    escaped = re.sub(r'(?<!_)_(?!_)([^_\n]+?)(?<!_)_(?!_)', r'<em>\1</em>', escaped)
    # Inline code
    escaped = re.sub(
        r'`([^`]+)`',
        r'<code style="background:#f0f0f0; padding:1px 4px; border-radius:3px; font-size:11px;">\1</code>',
        escaped,
    )
    return escaped


def _process_blocks(text: str) -> str:
    """Convert Markdown block elements to HTML.

    Suppresses blank lines that are adjacent to block-level elements
    (headings, HR, lists, blockquotes, code blocks) so they don't
    compound with those elements' own margins.
    """
    lines = text.split('\n')
    out: list[str] = []
    i = 0
    prev_is_block = False

    def next_non_blank_stripped(idx: int) -> str:
        j = idx + 1
        while j < len(lines):
            s = lines[j].strip()
            if s:
                return s
            j += 1
        return ''

    def is_block_start(s: str) -> bool:
        return bool(
            re.match(r'^[-*_]{3,}$', s)       # HR
            or re.match(r'^#{1,6}\s', s)       # heading
            or re.match(r'^[*\-+]\s', s)       # UL
            or re.match(r'^\d+\.\s', s)        # OL
            or re.match(r'^>\s?', s)           # blockquote
            or re.match(r'^```', s)            # fenced code (shouldn't happen but guard)
        )

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Horizontal rule: ---, ***, or ___ (3+ repeated chars, nothing else)
        if re.match(r'^[-*_]{3,}$', stripped):
            out.append('<hr style="border:none; border-top:1px solid #ccc; margin:3px 0;">')
            prev_is_block = True
            i += 1
            continue

        # ATX heading: # through ######
        m = re.match(r'^(#{1,6})\s+(.+)$', stripped)
        if m:
            level = min(len(m.group(1)), 6)
            heading_html = _apply_inline(html.escape(m.group(2)))
            sizes = ['15px', '14px', '13px', '12px', '12px', '12px']
            sz = sizes[level - 1]
            out.append(
                f'<p style="font-size:{sz}; font-weight:bold; margin:0 0 1px; '
                f'font-family:{_EMOJI_FONT};">'
                f'{heading_html}</p>'
            )
            prev_is_block = True
            i += 1
            continue

        # Blockquote: lines starting with >
        if re.match(r'^>\s?', stripped):
            quote_lines = []
            while i < len(lines) and re.match(r'^>\s?', lines[i].strip()):
                content = re.sub(r'^>\s?', '', lines[i].strip())
                quote_lines.append(_apply_inline(html.escape(content)))
                i += 1
            inner = '<br>'.join(quote_lines)
            out.append(
                f'<p style="margin:2px 4px; padding:4px 10px; '
                f'border-left:3px solid #ccc; color:#666; font-style:italic;">'
                f'{inner}</p>'
            )
            prev_is_block = True
            continue

        # Unordered list
        if re.match(r'^[*\-+]\s+', stripped):
            items = []
            while i < len(lines) and re.match(r'^[*\-+]\s+', lines[i].strip()):
                item_text = re.sub(r'^[*\-+]\s+', '', lines[i].strip())
                items.append(
                    f'<li style="margin:1px 0;">{_apply_inline(html.escape(item_text))}</li>'
                )
                i += 1
            out.append('<ul style="margin:2px 0; padding-left:20px;">' + ''.join(items) + '</ul>')
            prev_is_block = True
            continue

        # Ordered list
        if re.match(r'^\d+\.\s+', stripped):
            items = []
            while i < len(lines) and re.match(r'^\d+\.\s+', lines[i].strip()):
                item_text = re.sub(r'^\d+\.\s+', '', lines[i].strip())
                items.append(
                    f'<li style="margin:1px 0;">{_apply_inline(html.escape(item_text))}</li>'
                )
                i += 1
            out.append('<ol style="margin:2px 0; padding-left:20px;">' + ''.join(items) + '</ol>')
            prev_is_block = True
            continue

        # Blank line — suppress when adjacent to block elements
        if stripped == '':
            next_s = next_non_blank_stripped(i)
            if not prev_is_block and not is_block_start(next_s):
                out.append('<br>')
                prev_is_block = True  # prevent multiple consecutive blanks
            i += 1
            continue

        # Regular paragraph line
        out.append(_apply_inline(html.escape(line)) + '<br>')
        prev_is_block = False
        i += 1

    return ''.join(out)


# ---------------------------------------------------------------------------
# Widget
# ---------------------------------------------------------------------------

from ai.llm_agent import Provider  # noqa: E402

_PROVIDER_VALUES = [Provider.ANTHROPIC, Provider.GROQ]
_PROVIDER_ENV_VARS = ['ANTHROPIC_API_KEY', 'GROQ_API_KEY']
_PROVIDER_LABELS = ['Claude', 'Groq']


class ChatPanelWidget(QWidget):
    """Right-side AI chat panel.

    Signals:
        task_submitted(str):    Emitted when the user submits a message.
        clear_requested():      Emitted when the Clear button is clicked.
        provider_changed(str):  Emitted when the provider combo changes.
    """

    task_submitted = pyqtSignal(str)
    clear_requested = pyqtSignal()
    provider_changed = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        try:
            uic.loadUi('src/ui/components/chat_panel_widget.ui', self)
        except Exception as exc:
            print(f"ChatPanelWidget: could not load .ui file: {exc}")
            self._build_fallback_ui()
            return
        self._connect_internal_signals()
        self._setup_conversation_view()
        self._setup_provider_combo()
        self.show_greeting()

    # ------------------------------------------------------------------
    # Internal setup
    # ------------------------------------------------------------------

    def _connect_internal_signals(self):
        self.send_btn.clicked.connect(self._on_send)
        self.clear_btn.clicked.connect(self._on_clear)
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        self.input_field.keyPressEvent = self._input_key_press

    def _setup_conversation_view(self):
        """Configure the conversation view for proper emoji and font rendering."""
        from PyQt5.QtGui import QFont
        from PyQt5.QtWidgets import QTextEdit

        # Register emoji fonts as fallbacks for both UI and monospace fonts so
        # that emoji in headings AND in <pre> code blocks render correctly.
        _emoji_fallbacks = ['Segoe UI Emoji', 'Apple Color Emoji', 'Noto Color Emoji']
        QFont.insertSubstitutions('Segoe UI', _emoji_fallbacks)
        QFont.insertSubstitutions('Consolas', _emoji_fallbacks)
        QFont.insertSubstitutions('Courier New', _emoji_fallbacks)
        QFont.insertSubstitutions('monospace', _emoji_fallbacks)

        font = QFont('Segoe UI', 10)
        self.conversation_view.setFont(font)

        # Default stylesheet for all HTML rendered inside the widget
        self.conversation_view.document().setDefaultStyleSheet(
            f"body {{ font-family: {_EMOJI_FONT}; font-size: 12px; }}"
        )

        # Prose wraps at widget width; code blocks use white-space:pre and extend
        # the document horizontally — the scroll bar lets the user scroll right.
        from PyQt5.QtCore import Qt
        self.conversation_view.setLineWrapMode(QTextEdit.WidgetWidth)
        self.conversation_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    def _setup_provider_combo(self):
        """Populate combo showing all providers.

        Providers with API keys are fully interactive (userData = provider string).
        Providers without keys are shown grayed with "(no key)" suffix; their
        model item flags are cleared so they cannot be selected, and their
        userData is None so _on_provider_changed can detect and reject them.
        """
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QBrush, QColor

        self.provider_combo.blockSignals(True)
        self.provider_combo.clear()

        first_available = -1
        for value, env_var, label in zip(_PROVIDER_VALUES, _PROVIDER_ENV_VARS, _PROVIDER_LABELS):
            has_key = bool(os.environ.get(env_var, '').strip())
            if has_key:
                self.provider_combo.addItem(label, userData=value)
                if first_available == -1:
                    first_available = self.provider_combo.count() - 1
            else:
                self.provider_combo.addItem(f'{label} (no key)', userData=None)
                # Strip ALL item flags so the item is visible but non-interactive
                model = self.provider_combo.model()
                item = model.item(self.provider_combo.count() - 1)
                if item is not None:
                    item.setFlags(Qt.ItemFlag(0))
                    item.setForeground(QBrush(QColor('#888888')))

        if first_available >= 0:
            self.provider_combo.setCurrentIndex(first_available)
            self.provider_combo.setEnabled(True)
        else:
            self.provider_combo.setEnabled(False)

        self.provider_combo.blockSignals(False)

    def _build_fallback_ui(self):
        """Minimal programmatic fallback if the .ui file cannot be loaded."""
        from PyQt5.QtWidgets import (
            QComboBox, QHBoxLayout, QLabel, QPlainTextEdit,
            QPushButton, QTextEdit, QVBoxLayout,
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.title_label = QLabel("AI Assistant")
        self.conversation_view = QTextEdit()
        self.conversation_view.setReadOnly(True)
        self.input_field = QPlainTextEdit()
        self.send_btn = QPushButton("Send")
        self.clear_btn = QPushButton("Clear")
        self.status_label = QLabel()
        self.provider_combo = QComboBox()
        for label in _PROVIDER_LABELS:
            self.provider_combo.addItem(label)
        layout.addWidget(self.title_label)
        layout.addWidget(self.provider_combo)
        layout.addWidget(self.conversation_view)
        layout.addWidget(self.input_field)
        row = QHBoxLayout()
        row.addWidget(self.status_label)
        row.addWidget(self.clear_btn)
        row.addWidget(self.send_btn)
        layout.addLayout(row)
        self._connect_internal_signals()
        self._setup_conversation_view()
        self._setup_provider_combo()
        self.show_greeting()

    # ------------------------------------------------------------------
    # Key handling
    # ------------------------------------------------------------------

    def _input_key_press(self, event: QKeyEvent):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if event.modifiers() & Qt.ShiftModifier:
                from PyQt5.QtWidgets import QPlainTextEdit
                QPlainTextEdit.keyPressEvent(self.input_field, event)
            else:
                self._on_send()
        else:
            from PyQt5.QtWidgets import QPlainTextEdit
            QPlainTextEdit.keyPressEvent(self.input_field, event)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_send(self):
        text = self.input_field.toPlainText().strip()
        if not text:
            return
        self.input_field.clear()
        self.task_submitted.emit(text)

    def _on_clear(self):
        self.conversation_view.clear()
        self.clear_requested.emit()
        self.show_greeting()

    def _on_provider_changed(self, index: int):
        from PyQt5.QtCore import Qt
        # If the selected item has no userData (no API key), revert to first available
        data = self.provider_combo.itemData(index)
        if not data:
            model = self.provider_combo.model()
            for j in range(self.provider_combo.count()):
                if model and model.item(j) and (model.item(j).flags() & Qt.ItemIsEnabled):
                    self.provider_combo.blockSignals(True)
                    self.provider_combo.setCurrentIndex(j)
                    self.provider_combo.blockSignals(False)
                    return
            return
        self.provider_changed.emit(data)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show_greeting(self):
        """Display the standard greeting when the conversation is empty."""
        self.conversation_view.clear()
        self.append_assistant_message(_GREETING)

    def append_user_message(self, text: str):
        escaped = html.escape(text).replace('\n', '<br>')
        self.conversation_view.append(_USER_BUBBLE.format(text=escaped))
        self._scroll_to_bottom()

    def append_assistant_message(self, text: str):
        converted = _md_to_html(text)
        self.conversation_view.append(_ASSISTANT_BUBBLE.format(text=converted))
        self._scroll_to_bottom()

    def append_tool_call(self, tool_name: str):
        safe = html.escape(tool_name)
        self.conversation_view.append(_TOOL_LINE.format(tool_name=safe))
        self._scroll_to_bottom()

    def append_tool_result(self, tool_name: str, summary: str):
        safe = html.escape(summary[:200])
        self.conversation_view.append(_RESULT_LINE.format(summary=safe))
        self._scroll_to_bottom()

    def append_error(self, message: str):
        safe = html.escape(message)
        self.conversation_view.append(_ERROR_LINE.format(message=safe))
        self._scroll_to_bottom()

    def set_thinking(self, thinking: bool):
        self.status_label.setText("Thinking…" if thinking else "")
        self.send_btn.setEnabled(not thinking)
        self.input_field.setEnabled(not thinking)

    def get_current_provider(self) -> str:
        """Return the provider value for the currently selected combo item."""
        data = self.provider_combo.itemData(self.provider_combo.currentIndex())
        if isinstance(data, str) and data:
            return data
        # Fallback: return first provider that has a key
        for value, env_var in zip(_PROVIDER_VALUES, _PROVIDER_ENV_VARS):
            if os.environ.get(env_var, '').strip():
                return value
        return Provider.ANTHROPIC

    def set_provider(self, provider: str):
        """Set provider in the combo without emitting provider_changed."""
        for i in range(self.provider_combo.count()):
            if self.provider_combo.itemData(i) == provider:
                self.provider_combo.blockSignals(True)
                try:
                    self.provider_combo.setCurrentIndex(i)
                finally:
                    self.provider_combo.blockSignals(False)
                return

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _scroll_to_bottom(self):
        sb = self.conversation_view.verticalScrollBar()
        sb.setValue(sb.maximum())
