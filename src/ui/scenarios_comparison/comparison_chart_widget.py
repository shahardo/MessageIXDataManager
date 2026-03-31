"""
ComparisonChartWidget

Renders a Plotly chart comparing two Parameter objects side-by-side.

Four modes (selectable via toolbar buttons):
    Grouped Bar  — default; solid bars for A, hatched bars for B, grouped by year
    Stacked Bar  — two stacked bar columns per year (A and B), one segment per technology
    Overlaid Line — one solid line (A) and one dashed line (B) per series
    Delta Bar     — single bar chart of (B − A); green = increase, red = decrease

The widget wraps a QWebEngineView and writes temporary HTML files, identical
to ChartWidget's approach.
"""

import os
import tempfile
import threading
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from PyQt5.QtCore import QUrl, pyqtSignal
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import (
    QHBoxLayout, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from core.data_models import Parameter
from core.message_ix_schema import generate_legend_tooltip_script
from ui.scenarios_comparison.comparison_data_widget import merge_parameters

_PLOTLY_JS = "https://cdn.plot.ly/plotly-2.27.0.min.js"

# Palette — matches the default Plotly qualitative colours
_PALETTE = [
    '#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A',
    '#19D3F3', '#FF6692', '#B6E880', '#FF97FF', '#FECB52',
]

# When a parameter has more series than this, aggregate into totals per year
# instead of drawing one trace per series (which makes bars too thin to see).
_MAX_SERIES = 10


class ComparisonChartWidget(QWidget):
    """Grouped/Overlaid/Delta Plotly chart for scenario comparison."""

    chart_mode_changed = pyqtSignal(str)

    # Chart mode constants
    GROUPED_BAR   = 'grouped_bar'
    STACKED_BAR   = 'stacked_bar'
    OVERLAID_LINE = 'overlaid_line'
    DELTA_BAR     = 'delta_bar'

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mode = self.GROUPED_BAR
        self._label_a = "A"
        self._label_b = "B"
        self._setup_ui()
        self._show_placeholder("Select a parameter to view comparison chart")

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Toolbar
        toolbar = QHBoxLayout()

        _btn_style = """
            QPushButton {
                font-size: 16px;
                padding: 2px 6px;
                min-width: 32px;
                min-height: 28px;
                border: 1px solid #ccc;
                border-radius: 3px;
                background: #f8f8f8;
            }
            QPushButton:checked {
                background: #4a90d9;
                border-color: #2a6db5;
            }
            QPushButton:hover:!checked { background: #e8e8e8; }
        """

        # 📊 grouped bar  |  ≡ stacked bar  |  📈 overlaid line  |  Δ delta bar
        self._btn_grouped = QPushButton("📊")
        self._btn_stacked = QPushButton("≡")
        self._btn_line    = QPushButton("📈")
        self._btn_delta   = QPushButton("Δ")

        self._btn_grouped.setToolTip("Grouped Bar")
        self._btn_stacked.setToolTip("Stacked Bar (pivot by technology)")
        self._btn_line.setToolTip("Overlaid Line")
        self._btn_delta.setToolTip("Delta Bar")

        for btn in (self._btn_grouped, self._btn_stacked, self._btn_line, self._btn_delta):
            btn.setCheckable(True)
            btn.setStyleSheet(_btn_style)
            toolbar.addWidget(btn)
        toolbar.addStretch()

        self._btn_grouped.setChecked(True)
        self._btn_grouped.clicked.connect(lambda: self._set_mode(self.GROUPED_BAR))
        self._btn_stacked.clicked.connect(lambda: self._set_mode(self.STACKED_BAR))
        self._btn_line.clicked.connect(lambda: self._set_mode(self.OVERLAID_LINE))
        self._btn_delta.clicked.connect(lambda: self._set_mode(self.DELTA_BAR))

        layout.addLayout(toolbar)

        # Web view
        self._web = QWebEngineView()
        self._web.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self._web)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_chart(
        self,
        param_a: Parameter,
        param_b: Parameter,
        label_a: str,
        label_b: str,
    ) -> None:
        """Re-render the chart with the given two Parameter objects."""
        self._label_a = label_a
        self._label_b = label_b

        try:
            merged = merge_parameters(param_a, param_b, label_a, label_b)
        except Exception as e:
            print(f"[ComparisonChart] merge_parameters failed: {e}")
            self._show_placeholder(f"Cannot build chart: {e}")
            return

        if merged.empty:
            print("[ComparisonChart] merged DataFrame is empty — no chart")
            self._show_placeholder("No data to display")
            return

        col_a = f"Value ({label_a})"
        col_b = f"Value ({label_b})"

        if self._mode == self.GROUPED_BAR:
            self._render_grouped_bar(merged, col_a, col_b, param_a.name)
        elif self._mode == self.STACKED_BAR:
            self._render_stacked_bar(merged, col_a, col_b, param_a.name)
        elif self._mode == self.OVERLAID_LINE:
            self._render_overlaid_line(merged, col_a, col_b, param_a.name)
        elif self._mode == self.DELTA_BAR:
            self._render_delta_bar(merged, param_a.name)

    def show_placeholder(self, message: str = "Select a parameter to view comparison chart") -> None:
        self._show_placeholder(message)

    # ------------------------------------------------------------------
    # Mode handling
    # ------------------------------------------------------------------

    def _set_mode(self, mode: str) -> None:
        self._mode = mode
        for btn, m in (
            (self._btn_grouped, self.GROUPED_BAR),
            (self._btn_stacked, self.STACKED_BAR),
            (self._btn_line,    self.OVERLAID_LINE),
            (self._btn_delta,   self.DELTA_BAR),
        ):
            btn.setChecked(mode == m)
        self.chart_mode_changed.emit(mode)

    # ------------------------------------------------------------------
    # Chart renderers
    # ------------------------------------------------------------------

    def _detect_series_col(self, df: pd.DataFrame, val_cols: set) -> Optional[str]:
        """
        Return the column to use as the series dimension (e.g. 'tec', 'commodity').
        Falls back to None if no suitable column is found.
        """
        preferred = ['tec', 'technology', 'commodity', 'type_tec', 'relation']
        dim_cols = [c for c in df.columns if c not in val_cols]
        for p in preferred:
            if p in dim_cols:
                return p
        # Year-like columns are poor series candidates — skip them
        non_year = [c for c in dim_cols
                    if not any(y in c.lower() for y in ['year', 'time'])]
        return non_year[0] if non_year else None

    def _detect_year_col(self, df: pd.DataFrame, val_cols: set) -> Optional[str]:
        dim_cols = [c for c in df.columns if c not in val_cols]
        for c in dim_cols:
            if 'year' in c.lower() or 'time' in c.lower():
                return c
        return None

    def _render_grouped_bar(
        self,
        merged: pd.DataFrame,
        col_a: str,
        col_b: str,
        param_name: str,
    ) -> None:
        val_cols = {col_a, col_b, 'Δ', 'Δ%'}
        year_col  = self._detect_year_col(merged, val_cols)
        series_col = self._detect_series_col(merged, val_cols)

        fig = go.Figure()

        if year_col and series_col:
            years = sorted(merged[year_col].dropna().unique())
            series_vals = sorted(merged[series_col].dropna().unique())

            if len(series_vals) > _MAX_SERIES:
                # Too many series → aggregate totals per year (2 traces only)
                agg = merged.groupby(year_col, sort=True)[[col_a, col_b]].sum()
                agg_a = pd.to_numeric(agg[col_a], errors='coerce')
                agg_b = pd.to_numeric(agg[col_b], errors='coerce')
                fig.add_trace(go.Bar(
                    x=agg.index.tolist(), y=agg_a.tolist(),
                    name=self._label_a, marker_color=_PALETTE[0],
                ))
                fig.add_trace(go.Bar(
                    x=agg.index.tolist(), y=agg_b.tolist(),
                    name=self._label_b, marker_color=_PALETTE[1],
                    marker_pattern_shape='/',
                ))
            else:
                for i, s in enumerate(series_vals):
                    color = _PALETTE[i % len(_PALETTE)]
                    mask = merged[series_col] == s
                    sub = merged[mask].set_index(year_col)
                    if sub.index.duplicated().any():
                        sub = sub.groupby(level=0).sum()

                    y_a = [float(pd.to_numeric(sub.loc[yr, col_a], errors='coerce')) if yr in sub.index else None for yr in years]
                    y_b = [float(pd.to_numeric(sub.loc[yr, col_b], errors='coerce')) if yr in sub.index else None for yr in years]

                    fig.add_trace(go.Bar(
                        x=years, y=y_a,
                        name=f"{s} ({self._label_a})",
                        marker_color=color,
                        legendgroup=str(s),
                        offsetgroup=f"{s}_a",
                    ))
                    fig.add_trace(go.Bar(
                        x=years, y=y_b,
                        name=f"{s} ({self._label_b})",
                        marker_color=color,
                        marker_pattern_shape='/',
                        legendgroup=str(s),
                        offsetgroup=f"{s}_b",
                    ))
        else:
            # No year/series columns — one bar group per scenario
            x_vals = list(range(len(merged)))
            fig.add_trace(go.Bar(x=x_vals, y=pd.to_numeric(merged[col_a], errors='coerce').tolist(),
                                 name=self._label_a))
            fig.add_trace(go.Bar(x=x_vals, y=pd.to_numeric(merged[col_b], errors='coerce').tolist(),
                                 name=self._label_b, marker_pattern_shape='/'))

        fig.update_layout(
            barmode='group',
            title=f"{param_name} — Grouped Comparison",
            xaxis_title=year_col or "Index",
            yaxis_title="Value",
            template='plotly_white',
            legend=dict(orientation="h", yanchor="top", y=-0.3, xanchor="center", x=0.5),
            margin=dict(b=130),
        )
        if year_col:
            years_list = sorted(merged[year_col].dropna().unique().tolist())
            fig.update_xaxes(tickmode='array', tickvals=years_list,
                             ticktext=[str(y) for y in years_list])
        self._render(fig, f"{param_name} — Grouped Bar")

    # ------------------------------------------------------------------
    # Stacked-bar helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_tech_grouping(
        df: pd.DataFrame,
        series_col: str,
        col_a: str,
        col_b: str,
        year_col: str,
    ) -> pd.DataFrame:
        """
        Map individual technology names to group names (e.g. wind_res2 → 'Wind',
        solar_res_hist_2020 → 'Solar') using TECHNOLOGY_GROUPS patterns, then
        re-aggregate col_a and col_b by (year, group).

        This collapses:
          • resource-grade / potential techs (csp_sm1_res5, wind_res2)
          • historic variants (solar_res_hist_2020, coal_ppl__1990)
        into their parent groups, reducing legend clutter.
        """
        from utils.technology_classifier import _build_reverse_group_map, _find_group  # noqa: PLC0415

        reverse_map = _build_reverse_group_map()
        df = df.copy()

        # Replace individual tech names with group display names
        df[series_col] = df[series_col].apply(
            lambda t: _find_group(str(t), reverse_map) if pd.notna(t) else t
        )

        # Re-aggregate: sum col_a and col_b within each (year, group) bucket
        group_cols = [c for c in df.columns if c not in {col_a, col_b, 'Δ', 'Δ%'}]
        numeric_cols = {col_a, col_b} & set(df.columns)
        df = (
            df.groupby(group_cols, as_index=False, dropna=False)
            .agg({c: 'sum' for c in numeric_cols})
        )

        # Recalculate Δ / Δ% after aggregation
        a_vals = pd.to_numeric(df[col_a], errors='coerce')
        b_vals = pd.to_numeric(df[col_b], errors='coerce')
        df['Δ'] = b_vals - a_vals
        pct = (df['Δ'] / a_vals.replace(0, pd.NA)) * 100
        pct = pct.replace([float('inf'), float('-inf')], pd.NA)
        pct = pct.where(df['Δ'] != 0, 0.0)
        df['Δ%'] = pct
        return df

    def _render_stacked_bar(
        self,
        merged: pd.DataFrame,
        col_a: str,
        col_b: str,
        param_name: str,
    ) -> None:
        """
        Stacked bar chart: two side-by-side stacked columns per year (A and B).

        Strategy: barmode='overlay' with manually computed bar positions.
          - Bar width derived from the minimum gap between consecutive years, so
            the x-axis preserves real proportional year spacing (2060→2070 wider
            than 2025→2030).
          - Each technology adds two Bar traces: A bars shifted left of each year
            tick, B bars shifted right, with explicit `offset`/`width`/`base` so
            Plotly never needs to rearrange them.
          - Stacking is achieved by accumulating `base` per year before each trace.

        Pre-processing:
          1. Technology grouping — collapses potentials (wind_res2, csp_sm1_res5)
             and historic variants (solar_res_hist_2020) into their parent groups.
          2. Zero filtering — groups whose A and B values are all zero are skipped.
        """
        val_cols = {col_a, col_b, 'Δ', 'Δ%'}
        year_col   = self._detect_year_col(merged, val_cols)
        series_col = self._detect_series_col(merged, val_cols)

        fig = go.Figure()

        if year_col and series_col:
            # Apply technology grouping: collapse potentials / historic variants
            grouped = self._apply_tech_grouping(merged, series_col, col_a, col_b, year_col)

            years       = sorted(grouped[year_col].dropna().unique())
            series_vals = sorted(grouped[series_col].dropna().unique())

            # Bar geometry: each bar is 35 % of the minimum year gap; a 5 %
            # intra-pair gap separates A from B at the year-tick midpoint.
            if len(years) > 1:
                min_gap = min(years[i+1] - years[i] for i in range(len(years) - 1))
            else:
                min_gap = 5
            bar_w    = min_gap * 0.35     # width of one bar
            pair_gap = min_gap * 0.025    # gap between A and B bars
            # A bar: right edge at (year - pair_gap), so offset = -(bar_w + pair_gap)
            # B bar: left  edge at (year + pair_gap), so offset = +pair_gap
            off_a = -(bar_w + pair_gap)
            off_b = pair_gap

            # Per-year cumulative bases for manual stacking
            base_a = {yr: 0.0 for yr in years}
            base_b = {yr: 0.0 for yr in years}

            for i, s in enumerate(series_vals):
                color = _PALETTE[i % len(_PALETTE)]
                mask  = grouped[series_col] == s
                sub   = grouped[mask].set_index(year_col)
                if sub.index.duplicated().any():
                    sub = sub.groupby(level=0).sum()

                def _val(yr, col, _sub=sub):
                    if yr not in _sub.index:
                        return 0.0
                    v = pd.to_numeric(_sub.loc[yr, col], errors='coerce')
                    return 0.0 if pd.isna(v) else float(v)

                y_a = [_val(yr, col_a) for yr in years]
                y_b = [_val(yr, col_b) for yr in years]

                # Skip groups entirely zero in both scenarios
                if all(v == 0.0 for v in y_a) and all(v == 0.0 for v in y_b):
                    continue

                # A column: solid fill, to the LEFT of each year tick
                fig.add_trace(go.Bar(
                    x=years,
                    y=y_a,
                    base=[base_a[yr] for yr in years],
                    width=bar_w,
                    offset=off_a,
                    name=str(s),
                    legendgroup=str(s),
                    marker_color=color,
                    showlegend=True,
                ))
                # B column: hatched fill, to the RIGHT of each year tick
                fig.add_trace(go.Bar(
                    x=years,
                    y=y_b,
                    base=[base_b[yr] for yr in years],
                    width=bar_w,
                    offset=off_b,
                    name=str(s),
                    legendgroup=str(s),
                    marker_color=color,
                    marker_pattern_shape='/',
                    showlegend=False,
                ))

                # Advance stacking bases
                for yr, va, vb in zip(years, y_a, y_b):
                    base_a[yr] += va
                    base_b[yr] += vb

            # Dummy Scatter traces so scenario labels appear in the legend
            fig.add_trace(go.Scatter(
                x=[None], y=[None], mode='markers',
                marker=dict(symbol='square', size=10, color='#888888'),
                name=f"{self._label_a} (solid)",
                showlegend=True,
            ))
            fig.add_trace(go.Scatter(
                x=[None], y=[None], mode='markers',
                marker=dict(symbol='square-open', size=10, color='#888888'),
                name=f"{self._label_b} (hatched /)",
                showlegend=True,
            ))

        else:
            # No series/year — total per scenario
            total_a = pd.to_numeric(merged[col_a], errors='coerce').fillna(0).sum()
            total_b = pd.to_numeric(merged[col_b], errors='coerce').fillna(0).sum()
            fig.add_trace(go.Bar(x=[self._label_a], y=[total_a],
                                 name=self._label_a, marker_color=_PALETTE[0]))
            fig.add_trace(go.Bar(x=[self._label_b], y=[total_b],
                                 name=self._label_b, marker_color=_PALETTE[1],
                                 marker_pattern_shape='/'))

        fig.update_layout(
            barmode='overlay',   # bars are positioned manually; no Plotly rearrangement
            title=f"{param_name} — Stacked Comparison",
            xaxis_title=year_col or "Scenario",
            yaxis_title="Value",
            template='plotly_white',
            legend=dict(orientation="h", yanchor="top", y=-0.3, xanchor="center", x=0.5),
            margin=dict(b=130),
        )
        if year_col:
            years_list = sorted(merged[year_col].dropna().unique().tolist())
            fig.update_xaxes(tickmode='array', tickvals=years_list,
                             ticktext=[str(y) for y in years_list])
        self._render(fig, f"{param_name} — Stacked Bar")

    def _render_overlaid_line(
        self,
        merged: pd.DataFrame,
        col_a: str,
        col_b: str,
        param_name: str,
    ) -> None:
        val_cols = {col_a, col_b, 'Δ', 'Δ%'}
        year_col  = self._detect_year_col(merged, val_cols)
        series_col = self._detect_series_col(merged, val_cols)

        fig = go.Figure()

        if year_col and series_col:
            years = sorted(merged[year_col].dropna().unique())
            series_vals = sorted(merged[series_col].dropna().unique())

            if len(series_vals) > _MAX_SERIES:
                agg = merged.groupby(year_col, sort=True)[[col_a, col_b]].sum()
                fig.add_trace(go.Scatter(
                    x=agg.index.tolist(),
                    y=pd.to_numeric(agg[col_a], errors='coerce').tolist(),
                    mode='lines+markers', name=self._label_a,
                    line=dict(color=_PALETTE[0], dash='solid'),
                ))
                fig.add_trace(go.Scatter(
                    x=agg.index.tolist(),
                    y=pd.to_numeric(agg[col_b], errors='coerce').tolist(),
                    mode='lines+markers', name=self._label_b,
                    line=dict(color=_PALETTE[1], dash='dash'),
                ))
            else:
                for i, s in enumerate(series_vals):
                    color = _PALETTE[i % len(_PALETTE)]
                    mask = merged[series_col] == s
                    sub = merged[mask].set_index(year_col)
                    if sub.index.duplicated().any():
                        sub = sub.groupby(level=0).sum()

                    y_a = [float(pd.to_numeric(sub.loc[yr, col_a], errors='coerce')) if yr in sub.index else None for yr in years]
                    y_b = [float(pd.to_numeric(sub.loc[yr, col_b], errors='coerce')) if yr in sub.index else None for yr in years]

                    fig.add_trace(go.Scatter(
                        x=years, y=y_a, mode='lines+markers',
                        name=f"{s} ({self._label_a})",
                        line=dict(color=color, dash='solid'),
                        legendgroup=str(s),
                    ))
                    fig.add_trace(go.Scatter(
                        x=years, y=y_b, mode='lines+markers',
                        name=f"{s} ({self._label_b})",
                        line=dict(color=color, dash='dash'),
                        legendgroup=str(s),
                    ))
        else:
            x_vals = list(range(len(merged)))
            fig.add_trace(go.Scatter(x=x_vals,
                                     y=pd.to_numeric(merged[col_a], errors='coerce').tolist(),
                                     mode='lines+markers', name=self._label_a))
            fig.add_trace(go.Scatter(x=x_vals,
                                     y=pd.to_numeric(merged[col_b], errors='coerce').tolist(),
                                     mode='lines+markers', name=self._label_b,
                                     line=dict(dash='dash')))

        fig.update_layout(
            title=f"{param_name} — Overlaid Lines",
            xaxis_title=year_col or "Index",
            yaxis_title="Value",
            template='plotly_white',
            legend=dict(orientation="h", yanchor="top", y=-0.3, xanchor="center", x=0.5),
            margin=dict(b=130),
        )
        self._render(fig, f"{param_name} — Overlaid Line")

    def _render_delta_bar(self, merged: pd.DataFrame, param_name: str) -> None:
        val_cols = {'Δ', 'Δ%', f"Value ({self._label_a})", f"Value ({self._label_b})"}
        year_col  = self._detect_year_col(merged, val_cols)
        series_col = self._detect_series_col(merged, val_cols)

        fig = go.Figure()
        delta = pd.to_numeric(merged['Δ'], errors='coerce')
        colors = ['#27ae60' if (not pd.isna(v) and v >= 0) else '#e74c3c'
                  for v in delta]

        if year_col and series_col:
            years = sorted(merged[year_col].dropna().unique())
            series_vals = sorted(merged[series_col].dropna().unique())

            if len(series_vals) > _MAX_SERIES:
                agg = merged.groupby(year_col, sort=True)[['Δ']].sum()
                d_vals = pd.to_numeric(agg['Δ'], errors='coerce').tolist()
                bar_colors = ['#27ae60' if (v is not None and not pd.isna(v) and v >= 0) else '#e74c3c'
                              for v in d_vals]
                fig.add_trace(go.Bar(
                    x=agg.index.tolist(), y=d_vals,
                    marker_color=bar_colors, name='Δ (total)',
                ))
            else:
                for s in series_vals:
                    mask = merged[series_col] == s
                    sub = merged[mask].set_index(year_col)
                    if sub.index.duplicated().any():
                        sub = sub.groupby(level=0).sum()
                    d_vals = [float(pd.to_numeric(sub.loc[yr, 'Δ'], errors='coerce')) if yr in sub.index else None for yr in years]
                    bar_colors = ['#27ae60' if (v is not None and not pd.isna(v) and v >= 0) else '#e74c3c'
                                  for v in d_vals]
                    fig.add_trace(go.Bar(
                        x=years, y=d_vals,
                        name=str(s),
                        marker_color=bar_colors,
                    ))
        else:
            fig.add_trace(go.Bar(
                x=list(range(len(merged))),
                y=delta.tolist(),
                marker_color=colors,
                name='Δ',
            ))

        fig.update_layout(
            title=f"{param_name} — Delta ({self._label_b} − {self._label_a})",
            xaxis_title=year_col or "Index",
            yaxis_title="Δ Value",
            template='plotly_white',
            showlegend=bool(series_col),
            legend=dict(orientation="h", yanchor="top", y=-0.3, xanchor="center", x=0.5),
            margin=dict(b=130),
        )
        self._render(fig, f"{param_name} — Delta Bar")

    # ------------------------------------------------------------------
    # Rendering helpers (same pattern as ChartWidget)
    # ------------------------------------------------------------------

    def _render(self, fig: go.Figure, title: str) -> None:
        try:
            config = {
                'displayModeBar': True,
                'displaylogo': False,
                'responsive': True,
                'modeBarButtonsToRemove': ['pan2d', 'select2d', 'lasso2d', 'autoScale2d'],
            }
            html_body = pio.to_html(fig, full_html=False, include_plotlyjs=False,
                                    config=config, div_id='cmp-chart')
            complete = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <script src="{_PLOTLY_JS}"></script>
  <style>
    body {{ margin: 0; padding: 5px; font-family: Arial, sans-serif; overflow: hidden; }}
    #cmp-chart {{ width: 100%; height: 100%; }}
  </style>
</head>
<body style="height:100%; margin:0;">
  {html_body}
  {generate_legend_tooltip_script()}
</body>
</html>"""

            with tempfile.NamedTemporaryFile(mode='w', suffix='.html',
                                             delete=False, encoding='utf-8') as f:
                f.write(complete)
                path = f.name

            self._web.setUrl(QUrl.fromLocalFile(path))
            threading.Thread(target=self._cleanup, args=(path,), daemon=True).start()

        except Exception as e:
            print(f"[ComparisonChart _render] exception: {e}")
            self._show_placeholder(f"Error rendering chart: {e}")

    @staticmethod
    def _cleanup(path: str) -> None:
        import time
        time.sleep(2)
        try:
            os.unlink(path)
        except Exception:
            pass

    def _show_placeholder(self, message: str) -> None:
        html = f"""<html>
<body style="display:flex;justify-content:center;align-items:center;
             height:100vh;font-family:Arial,sans-serif;background:#f5f5f5;">
  <div style="text-align:center;color:#666;padding:20px;">
    <h4>{message}</h4>
  </div>
</body></html>"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html',
                                         delete=False, encoding='utf-8') as f:
            f.write(html)
            path = f.name
        self._web.setUrl(QUrl.fromLocalFile(path))
        threading.Thread(target=self._cleanup, args=(path,), daemon=True).start()
