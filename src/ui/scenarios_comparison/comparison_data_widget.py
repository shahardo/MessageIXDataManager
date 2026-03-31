"""
ComparisonDataWidget

Displays a side-by-side comparison of two Parameter objects with the same
name but from different scenarios.

Table columns:
    [dim1 … dimN | Value A | Value B | Δ | Δ%]

Color coding on Δ column cells:
    Δ > 0  → light green  (#d4edda)
    Δ < 0  → light red    (#f8d7da)
    Δ = 0  → default

Rows where a value exists only in one scenario show "—" for the missing side.
A "Show Δ only" checkbox hides the raw value columns.
"""

from typing import Dict, Optional, Tuple

import pandas as pd
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush, QColor, QFont
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QHBoxLayout, QLabel, QSizePolicy,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from core.data_models import Parameter

_GREEN = QColor('#d4edda')
_RED   = QColor('#f8d7da')
_GRAY  = QColor('#999999')

# Columns whose numeric values should be formatted with 3 significant figures
_FLOAT_COLS = {'Δ', 'Δ%'}


def _fmt(value) -> str:
    """Format a number for display."""
    if pd.isna(value):
        return "—"
    if isinstance(value, float):
        return f"{value:,.4g}"
    return str(value)


def merge_parameters(
    param_a: Parameter,
    param_b: Parameter,
    label_a: str,
    label_b: str,
) -> pd.DataFrame:
    """
    Outer-join two long-format DataFrames on their shared dimension columns.

    Returns a DataFrame with columns:
        [dim1, …, dimN, value_{label_a}, value_{label_b}, Δ, Δ%]
    """
    # Determine value column (results use 'lvl'; inputs use 'value')
    _VALUE_COLS = frozenset(['value', 'val', 'lvl'])

    def _val_col(df: pd.DataFrame) -> str:
        for c in df.columns:
            if c in _VALUE_COLS:
                return c
        return df.columns[-1]  # fallback

    val_col_a = _val_col(param_a.df)
    val_col_b = _val_col(param_b.df)

    dim_cols_a = [c for c in param_a.df.columns if c != val_col_a]
    dim_cols_b = [c for c in param_b.df.columns if c != val_col_b]

    # Use intersection of dimension columns as merge keys (handles minor schema diffs)
    dim_cols = [c for c in dim_cols_a if c in dim_cols_b] or dim_cols_a

    col_a = f"Value ({label_a})"
    col_b = f"Value ({label_b})"

    df_a = param_a.df[dim_cols + [val_col_a]].rename(columns={val_col_a: col_a})
    df_b = param_b.df[dim_cols + [val_col_b]].rename(columns={val_col_b: col_b})

    merged = pd.merge(df_a, df_b, on=dim_cols, how='outer')

    # Delta calculations — coerce to float; missing values stay NaN
    a_vals = pd.to_numeric(merged[col_a], errors='coerce')
    b_vals = pd.to_numeric(merged[col_b], errors='coerce')
    merged['Δ'] = b_vals - a_vals
    pct = (merged['Δ'] / a_vals.replace(0, pd.NA)) * 100
    pct = pct.replace([float('inf'), float('-inf')], pd.NA)
    # When Δ == 0 (both values equal, including both-zero), Δ% is 0
    pct = pct.where(merged['Δ'] != 0, 0.0)
    merged['Δ%'] = pct

    return merged


class ComparisonDataWidget(QWidget):
    """
    Widget that shows a merged comparison table for two Parameter objects.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._merged_df: Optional[pd.DataFrame] = None
        self._label_a = "A"
        self._label_b = "B"
        self._dim_filters: Dict[str, QComboBox] = {}   # col → combo
        self._setup_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Controls bar
        ctrl = QHBoxLayout()
        self._lbl_a = QLabel()
        self._lbl_b = QLabel()
        self._lbl_a.setStyleSheet("font-weight: bold; color: #1a6e3c;")
        self._lbl_b.setStyleSheet("font-weight: bold; color: #1a3a6e;")
        self._delta_only_cb = QCheckBox("Show Δ only")
        self._delta_only_cb.toggled.connect(self._toggle_delta_only)
        ctrl.addWidget(self._lbl_a)
        ctrl.addWidget(QLabel(" vs "))
        ctrl.addWidget(self._lbl_b)
        ctrl.addStretch()
        ctrl.addWidget(self._delta_only_cb)
        layout.addLayout(ctrl)

        # Filter bar — rebuilt dynamically when data is loaded
        self._filter_container = QWidget()
        self._filter_layout = QHBoxLayout(self._filter_container)
        self._filter_layout.setContentsMargins(0, 0, 0, 0)
        self._filter_layout.setSpacing(6)
        self._filter_container.setVisible(False)
        layout.addWidget(self._filter_container)

        # Placeholder label
        self._placeholder = QLabel("Select a parameter to compare")
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._placeholder.setStyleSheet("color: #888; font-size: 13px;")
        layout.addWidget(self._placeholder)

        # Table
        self._table = QTableWidget()
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.horizontalHeader().setStretchLastSection(False)
        self._table.setVisible(False)
        layout.addWidget(self._table)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def display(
        self,
        param_a: Parameter,
        param_b: Parameter,
        label_a: str,
        label_b: str,
    ) -> None:
        """Merge two parameters and populate the table."""
        self._label_a = label_a
        self._label_b = label_b
        self._lbl_a.setText(label_a)
        self._lbl_b.setText(label_b)

        try:
            self._merged_df = merge_parameters(param_a, param_b, label_a, label_b)
        except Exception as e:
            self._show_placeholder(f"Could not merge parameters: {e}")
            return

        self._rebuild_filters(self._merged_df)
        self._apply_filters()

    def clear(self) -> None:
        """Clear the table and show placeholder."""
        self._merged_df = None
        self._filter_container.setVisible(False)
        self._table.setVisible(False)
        self._placeholder.setVisible(True)

    def get_merged_df(self) -> Optional[pd.DataFrame]:
        """Return the current merged DataFrame (for export)."""
        return self._merged_df

    # ------------------------------------------------------------------
    # Filter bar
    # ------------------------------------------------------------------

    def _rebuild_filters(self, df: pd.DataFrame) -> None:
        """Recreate one QComboBox per dimension column from *df*."""
        val_cols = {
            f"Value ({self._label_a})", f"Value ({self._label_b})", 'Δ', 'Δ%',
        }
        dim_cols = [c for c in df.columns if c not in val_cols]

        # Remove old widgets
        while self._filter_layout.count():
            item = self._filter_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._dim_filters.clear()

        if not dim_cols:
            self._filter_container.setVisible(False)
            return

        self._filter_layout.addWidget(QLabel("Filter:"))

        for col in dim_cols:
            lbl = QLabel(col + ":")
            lbl.setStyleSheet("color: #555; font-size: 11px;")
            cb = QComboBox()
            cb.setMaximumWidth(160)
            cb.addItem("All")
            unique_vals = sorted(df[col].dropna().astype(str).unique())
            cb.addItems(unique_vals)
            cb.currentTextChanged.connect(self._apply_filters)
            self._filter_layout.addWidget(lbl)
            self._filter_layout.addWidget(cb)
            self._dim_filters[col] = cb

        self._filter_layout.addStretch()
        self._filter_container.setVisible(True)

    def _apply_filters(self, *_) -> None:
        """Apply current combo-box selections to the merged DataFrame and repopulate the table."""
        if self._merged_df is None:
            return
        self._populate_table(self._filtered_df())

    def _filtered_df(self) -> pd.DataFrame:
        """Return the merged DataFrame with all active filters applied."""
        df = self._merged_df.copy()
        for col, cb in self._dim_filters.items():
            # index 0 is always "All" — skip filtering when it is selected
            if cb.currentIndex() > 0:
                val = cb.currentText()
                df = df[df[col].astype(str) == val]
        return df

    def _current_filtered_df(self) -> Optional[pd.DataFrame]:
        """Public accessor for the currently filtered DataFrame (used by export)."""
        if self._merged_df is None:
            return None
        return self._filtered_df()

    # ------------------------------------------------------------------
    # Table population
    # ------------------------------------------------------------------

    def _populate_table(self, df: pd.DataFrame) -> None:
        self._table.clear()
        self._table.setVisible(True)
        self._placeholder.setVisible(False)

        show_delta_only = self._delta_only_cb.isChecked()
        col_a = f"Value ({self._label_a})"
        col_b = f"Value ({self._label_b})"

        # Decide which columns to show
        dim_cols = [c for c in df.columns if c not in {col_a, col_b, 'Δ', 'Δ%'}]
        if show_delta_only:
            display_cols = dim_cols + ['Δ', 'Δ%']
        else:
            display_cols = dim_cols + [col_a, col_b, 'Δ', 'Δ%']

        self._table.setColumnCount(len(display_cols))
        self._table.setRowCount(len(df))
        self._table.setHorizontalHeaderLabels(display_cols)

        delta_col_idx = display_cols.index('Δ') if 'Δ' in display_cols else None
        pct_col_idx   = display_cols.index('Δ%') if 'Δ%' in display_cols else None

        for row_idx, (_, row) in enumerate(df.iterrows()):
            delta_val = row.get('Δ', None)

            for col_idx, col_name in enumerate(display_cols):
                raw = row.get(col_name, None)
                text = _fmt(raw)

                cell = QTableWidgetItem(text)
                cell.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

                # Color-code the Δ and Δ% cells
                if col_idx in (delta_col_idx, pct_col_idx):
                    if not pd.isna(delta_val):
                        if delta_val > 0:
                            cell.setBackground(QBrush(_GREEN))
                        elif delta_val < 0:
                            cell.setBackground(QBrush(_RED))

                # Gray out cells where value is missing (NaN → "—")
                if text == "—":
                    cell.setForeground(QBrush(_GRAY))
                    font = cell.font()
                    font.setItalic(True)
                    cell.setFont(font)

                self._table.setItem(row_idx, col_idx, cell)

        self._table.resizeColumnsToContents()

    # ------------------------------------------------------------------
    # Controls handlers
    # ------------------------------------------------------------------

    def _toggle_delta_only(self, _checked: bool) -> None:
        if self._merged_df is not None:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            QApplication.processEvents()
            try:
                self._apply_filters()
            finally:
                QApplication.restoreOverrideCursor()

    def _show_placeholder(self, msg: str) -> None:
        self._placeholder.setText(msg)
        self._placeholder.setVisible(True)
        self._table.setVisible(False)
