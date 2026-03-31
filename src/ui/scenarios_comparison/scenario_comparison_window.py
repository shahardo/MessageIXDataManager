"""
ScenarioComparisonWindow

A standalone QMainWindow that compares two loaded scenarios side-by-side.

Layout
------
Horizontal splitter:
    Left  (300 px) — ComparisonParameterTreeWidget (same sidebar as main window)
    Right           — vertical splitter:
                          Top (60 %) — ComparisonDataWidget (merged table)
                          Bottom (40 %) — ComparisonChartWidget (Plotly chart)

Status bar shows row statistics whenever a parameter is selected.
"""

from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAction, QApplication, QLabel, QMainWindow, QMessageBox,
    QSplitter, QStatusBar, QWidget,
)

from core.data_models import Parameter, Scenario, ScenarioData
from ui.scenarios_comparison.comparison_chart_widget import ComparisonChartWidget
from ui.scenarios_comparison.comparison_data_widget import ComparisonDataWidget
from ui.scenarios_comparison.comparison_parameter_tree import ComparisonParameterTreeWidget


class ScenarioComparisonWindow(QMainWindow):
    """
    Window for comparing two scenarios parameter-by-parameter.

    Parameters
    ----------
    scenario_a, scenario_b : Scenario
        The two scenarios to compare (metadata only — names, file paths).
    data_a, data_b : ScenarioData
        Pre-assembled parameter data for each scenario.
    parent : QWidget, optional
        Parent widget (typically the main window).
    """

    def __init__(
        self,
        scenario_a: Scenario,
        scenario_b: Scenario,
        data_a: ScenarioData,
        data_b: ScenarioData,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.scenario_a = scenario_a
        self.scenario_b = scenario_b
        self._data_a = data_a
        self._data_b = data_b

        self._label_a = scenario_a.name
        self._label_b = scenario_b.name

        # Track last selected parameter for chart-mode re-renders
        self._current_param_name: Optional[str] = None

        self._setup_window()
        self._setup_menu()
        self._setup_ui()
        self._build_tree()
        self._connect_signals()

    # ------------------------------------------------------------------
    # Window setup
    # ------------------------------------------------------------------

    def _setup_window(self) -> None:
        a_star = '*' if self.scenario_a.is_modified() else ''
        b_star = '*' if self.scenario_b.is_modified() else ''
        self.setWindowTitle(
            f"Scenario Comparison: {self._label_a}{a_star}  vs  {self._label_b}{b_star}"
        )
        self.resize(1400, 800)

    def _setup_menu(self) -> None:
        """Add a minimal File menu with Export and Close."""
        file_menu = self.menuBar().addMenu("File")

        export_action = QAction("Export Comparison…", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self._export_comparison)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        close_action = QAction("Close", self)
        close_action.setShortcut("Ctrl+W")
        close_action.triggered.connect(self.close)
        file_menu.addAction(close_action)

    # ------------------------------------------------------------------
    # UI layout
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        # Main horizontal splitter: tree | data+chart
        self._h_splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(self._h_splitter)

        # Left: parameter tree
        self._tree = ComparisonParameterTreeWidget()
        self._h_splitter.addWidget(self._tree)

        # Right: vertical splitter (table on top, chart below)
        self._v_splitter = QSplitter(Qt.Vertical)
        self._h_splitter.addWidget(self._v_splitter)

        self._data_widget  = ComparisonDataWidget()
        self._chart_widget = ComparisonChartWidget()

        self._v_splitter.addWidget(self._data_widget)
        self._v_splitter.addWidget(self._chart_widget)

        self._h_splitter.setSizes([300, 1100])
        self._v_splitter.setSizes([480, 320])

        # Status bar — use a single permanent QLabel; no showMessage() to avoid overlap
        self._status_label = QLabel("Ready — select a parameter to compare")
        self._status_label.setStyleSheet("padding-left: 4px;")
        status_bar = QStatusBar()
        status_bar.addWidget(self._status_label, 1)
        self.setStatusBar(status_bar)

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def _build_tree(self) -> None:
        """Populate the comparison tree from both scenarios."""
        if not self._data_a or not self._data_b:
            return
        self._status_label.setText("Loading parameter list…")
        QApplication.processEvents()
        self._tree.populate(self._data_a, self._data_b, self._label_a, self._label_b)
        n_a = len(self._data_a.get_parameter_names())
        n_b = len(self._data_b.get_parameter_names())
        self._status_label.setText(
            f"{self._label_a}: {n_a} params  |  {self._label_b}: {n_b} params"
            "  —  select a parameter to compare"
        )

    def _connect_signals(self) -> None:
        self._tree.parameter_selected.connect(self._on_parameter_selected)
        self._chart_widget.chart_mode_changed.connect(self._on_chart_mode_changed)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_parameter_selected(self, param_name: str) -> None:
        """Load data for *param_name* from both scenarios and display it."""
        self._current_param_name = param_name
        self._status_label.setText(f"Loading {param_name}…")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()

        try:
            param_a: Optional[Parameter] = self._data_a.get_parameter(param_name)
            param_b: Optional[Parameter] = self._data_b.get_parameter(param_name)

            if param_a is None or param_b is None:
                self._status_label.setText(
                    f"{param_name} — missing in one scenario"
                )
                return

            self._data_widget.display(param_a, param_b, self._label_a, self._label_b)
            self._status_label.setText(f"Rendering chart for {param_name}…")
            QApplication.processEvents()
            self._chart_widget.update_chart(param_a, param_b, self._label_a, self._label_b)

            # Status summary
            merged = self._data_widget.get_merged_df()
            if merged is not None:
                col_a = f"Value ({self._label_a})"
                col_b = f"Value ({self._label_b})"
                n_a    = len(param_a.df) if param_a.df is not None else 0
                n_b    = len(param_b.df) if param_b.df is not None else 0
                n_both  = int(merged[col_a].notna().sum()) if col_a in merged.columns else 0
                n_only_a = int(merged[col_b].isna().sum()) if col_b in merged.columns else 0
                n_only_b = int(merged[col_a].isna().sum()) if col_a in merged.columns else 0
                self._status_label.setText(
                    f"{param_name}  —  "
                    f"A: {n_a} rows  |  B: {n_b} rows  |  "
                    f"Common: {n_both}  |  A-only: {n_only_a}  |  B-only: {n_only_b}"
                )
        finally:
            QApplication.restoreOverrideCursor()

    def _on_chart_mode_changed(self, mode: str) -> None:
        """Re-render chart when the user changes the chart mode."""
        if not self._current_param_name:
            return
        self._status_label.setText(f"Updating chart ({mode})…")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()
        try:
            self._on_parameter_selected(self._current_param_name)
        finally:
            QApplication.restoreOverrideCursor()

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def _export_comparison(self) -> None:
        """Export the current merged DataFrame to Excel."""
        merged = self._data_widget.get_merged_df()
        if merged is None:
            QMessageBox.information(
                self, "Export", "Select a parameter first to export its comparison."
            )
            return

        from PyQt5.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Comparison", "", "Excel Workbook (*.xlsx)"
        )
        if not path:
            return

        try:
            import pandas as pd
            col_a = f"Value ({self._label_a})"
            col_b = f"Value ({self._label_b})"

            with pd.ExcelWriter(path, engine='openpyxl') as writer:
                merged.to_excel(writer, sheet_name="Merged", index=False)
                dim_cols = [c for c in merged.columns if c not in {col_a, col_b, 'Δ', 'Δ%'}]
                merged[dim_cols + ['Δ', 'Δ%']].to_excel(writer, sheet_name="Delta", index=False)

            self._status_label.setText(f"Exported to {path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))
