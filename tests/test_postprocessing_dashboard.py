"""
Tests for PostprocessingDashboard and DashboardChartMixin
"""

import os
import sys
import pytest
import pandas as pd
from unittest.mock import Mock, patch

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.data_models import ScenarioData, Parameter
from core.user_preferences import UserPreferences
from ui.dashboard_chart_mixin import DashboardChartMixin, PLOTLY_CDN_URL
from ui.postprocessing_dashboard import PostprocessingDashboard


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_results_analyzer():
    """Create a mock ResultsAnalyzer."""
    analyzer = Mock()
    analyzer.calculate_dashboard_metrics.return_value = {
        'primary_energy_2050': 160.0,
        'electricity_2050': 100.0,
        'clean_electricity_pct': 50.0,
        'emissions_2050': 90.0
    }
    return analyzer


@pytest.fixture
def postprocessing_scenario():
    """Create a ScenarioData with postprocessed parameters (long format)."""
    scenario = ScenarioData()

    # Primary energy supply – long format
    pe_df = pd.DataFrame({
        'year': [2020, 2020, 2020, 2050, 2050, 2050],
        'category': ['coal', 'gas', 'solar', 'coal', 'gas', 'solar'],
        'value': [40.0, 30.0, 10.0, 55.0, 45.0, 25.0]
    })
    scenario.add_parameter(
        Parameter("Primary energy supply (PJ)", pe_df, {
            'result_type': 'postprocessed', 'dims': ['year', 'category'],
            'value_column': 'value', 'source': 'postprocessor'
        })
    )

    # Electricity generation by source – long format
    elec_df = pd.DataFrame({
        'year': [2020, 2020, 2020, 2050, 2050, 2050],
        'category': ['coal', 'solar', 'wind', 'coal', 'solar', 'wind'],
        'value': [15.0, 5.0, 3.0, 20.0, 15.0, 10.0]
    })
    scenario.add_parameter(
        Parameter("Electricity generation by source (TWh)", elec_df, {
            'result_type': 'postprocessed', 'dims': ['year', 'category'],
            'value_column': 'value', 'source': 'postprocessor'
        })
    )

    # Aggregate electricity generation
    elec_agg_df = pd.DataFrame({
        'year': [2020, 2020, 2050, 2050],
        'category': ['coal', 'solar', 'coal', 'solar'],
        'value': [15.0, 8.0, 20.0, 25.0]
    })
    scenario.add_parameter(
        Parameter("Electricity generation (TWh)", elec_agg_df, {
            'result_type': 'postprocessed', 'dims': ['year', 'category'],
            'value_column': 'value', 'source': 'postprocessor'
        })
    )

    # Emissions
    em_df = pd.DataFrame({
        'year': [2020, 2050],
        'category': ['CO2', 'CO2'],
        'value': [120.0, 90.0]
    })
    scenario.add_parameter(
        Parameter("Total GHG emissions (MtCeq)", em_df, {
            'result_type': 'postprocessed', 'dims': ['year', 'category'],
            'value_column': 'value', 'source': 'postprocessor'
        })
    )

    # Electricity cost by source
    cost_df = pd.DataFrame({
        'year': [2020, 2020, 2050, 2050],
        'category': ['coal', 'solar', 'coal', 'solar'],
        'value': [65.0, 120.0, 70.0, 40.0]
    })
    scenario.add_parameter(
        Parameter("Electricity cost by source ($/MWh)", cost_df, {
            'result_type': 'postprocessed', 'dims': ['year', 'category'],
            'value_column': 'value', 'source': 'postprocessor'
        })
    )

    return scenario


def _make_dashboard(mock_results_analyzer, chart_views=None, elec_views=None,
                    labels=None, user_prefs=None):
    """Helper to create a PostprocessingDashboard without Qt event loop.

    Patches QWidget.__init__ and uic.loadUi so no real Qt objects are created,
    then manually attaches mock chart views and metric labels.
    """
    if user_prefs is None:
        user_prefs = UserPreferences()

    with patch('ui.postprocessing_dashboard.uic') as mock_uic, \
         patch('PyQt5.QtWidgets.QWidget.__init__', return_value=None):
        mock_uic.loadUi.side_effect = Exception("No UI file in test")
        dashboard = PostprocessingDashboard(mock_results_analyzer, user_prefs=user_prefs)

    if chart_views is not None:
        dashboard.chart_views = chart_views
    if elec_views is not None:
        dashboard.electricity_chart_views = elec_views
    if labels is not None:
        dashboard.metric_labels = labels

    return dashboard


# ---------------------------------------------------------------------------
# DashboardChartMixin tests
# ---------------------------------------------------------------------------

class TestDashboardChartMixin:
    """Tests for the shared chart rendering mixin."""

    def _make_mixin(self):
        """Create an instance that has the mixin methods."""
        class Concrete(DashboardChartMixin):
            pass
        return Concrete()

    def test_show_chart_placeholder(self):
        """show_chart_placeholder sets HTML with the message."""
        mixin = self._make_mixin()
        view = Mock()
        mixin.show_chart_placeholder(view, "No data loaded")
        view.setHtml.assert_called_once()
        html = view.setHtml.call_args[0][0]
        assert "No data loaded" in html

    def test_wrap_plotly_html_contains_cdn(self):
        """_wrap_plotly_html includes the Plotly CDN URL."""
        mixin = self._make_mixin()
        html = mixin._wrap_plotly_html("<div>chart</div>", "Test Title")
        assert PLOTLY_CDN_URL in html
        assert "Test Title" in html
        assert "<div>chart</div>" in html

    def test_render_stacked_bar_chart(self):
        """render_stacked_bar_chart calls setHtml on the chart view."""
        mixin = self._make_mixin()
        view = Mock()
        mixin.render_stacked_bar_chart(
            view, [2020, 2050], {'coal': [40, 55], 'gas': [30, 45]},
            'Title', 'HTML Title'
        )
        view.setHtml.assert_called_once()
        html = view.setHtml.call_args[0][0]
        assert PLOTLY_CDN_URL in html

    def test_render_pie_chart(self):
        """render_pie_chart calls setHtml on the chart view."""
        mixin = self._make_mixin()
        view = Mock()
        mixin.render_pie_chart(
            view, {'coal': 55, 'gas': 45}, 'Title', 'HTML Title'
        )
        view.setHtml.assert_called_once()

    def test_render_energy_chart_long_format(self):
        """render_energy_chart handles long-format DataFrames."""
        mixin = self._make_mixin()
        view = Mock()
        df = pd.DataFrame({
            'year': [2020, 2020, 2050, 2050],
            'category': ['coal', 'gas', 'coal', 'gas'],
            'value': [40, 30, 55, 45]
        })
        param = Parameter("Test (PJ)", df, {})
        mixin.render_energy_chart(param, view, 'Title', 'HTML Title')
        view.setHtml.assert_called_once()

    def test_render_energy_chart_wide_format(self):
        """render_energy_chart handles wide-format DataFrames."""
        mixin = self._make_mixin()
        view = Mock()
        df = pd.DataFrame({
            'year': [2020, 2050],
            'coal': [40, 55],
            'gas': [30, 45]
        })
        param = Parameter("Test (PJ)", df, {})
        mixin.render_energy_chart(param, view, 'Title', 'HTML Title')
        view.setHtml.assert_called_once()

    def test_render_energy_pie_chart_long_format(self):
        """render_energy_pie_chart filters to 2050 and renders pie."""
        mixin = self._make_mixin()
        view = Mock()
        df = pd.DataFrame({
            'year': [2020, 2020, 2050, 2050],
            'category': ['coal', 'gas', 'coal', 'gas'],
            'value': [40, 30, 55, 45]
        })
        param = Parameter("Test (PJ)", df, {})
        mixin.render_energy_pie_chart(param, view, 'Title', 'HTML Title')
        view.setHtml.assert_called_once()

    def test_render_energy_pie_chart_no_2050(self):
        """render_energy_pie_chart shows placeholder when no 2050 data."""
        mixin = self._make_mixin()
        view = Mock()
        df = pd.DataFrame({
            'year': [2020, 2030],
            'category': ['coal', 'coal'],
            'value': [40, 50]
        })
        param = Parameter("Test (PJ)", df, {})
        mixin.render_energy_pie_chart(param, view, 'Title', 'HTML Title')
        view.setHtml.assert_called_once()
        html = view.setHtml.call_args[0][0]
        assert "No data available for year 2050" in html

    def test_render_energy_pie_chart_no_positive(self):
        """render_energy_pie_chart shows placeholder when all values <= 0."""
        mixin = self._make_mixin()
        view = Mock()
        df = pd.DataFrame({
            'year': [2050, 2050],
            'category': ['coal', 'gas'],
            'value': [0.0, -5.0]
        })
        param = Parameter("Test (PJ)", df, {})
        mixin.render_energy_pie_chart(param, view, 'Title', 'HTML Title')
        view.setHtml.assert_called_once()
        html = view.setHtml.call_args[0][0]
        assert "No positive values" in html


# ---------------------------------------------------------------------------
# PostprocessingDashboard tests
# ---------------------------------------------------------------------------

class TestPostprocessingDashboard:
    """Tests for the PostprocessingDashboard widget."""

    def test_dashboard_creation_without_ui(self, mock_results_analyzer):
        """Dashboard initialises with empty dicts when UI file is absent."""
        dashboard = _make_dashboard(mock_results_analyzer)

        assert dashboard.results_analyzer is mock_results_analyzer
        assert dashboard.current_scenario is None
        assert dashboard.chart_views == {}
        assert dashboard.electricity_chart_views == {}
        assert dashboard.metric_labels == {}

    def test_update_dashboard_stores_scenario(self, mock_results_analyzer, postprocessing_scenario):
        """update_dashboard stores the scenario on the instance."""
        dashboard = _make_dashboard(mock_results_analyzer)
        dashboard.update_dashboard(postprocessing_scenario)
        assert dashboard.current_scenario is postprocessing_scenario

    def test_render_metrics_with_scenario(self, mock_results_analyzer, postprocessing_scenario):
        """_render_metrics delegates to results_analyzer and sets labels."""
        labels = {k: Mock() for k in ['primary_energy_2050', 'electricity_2050',
                                       'clean_electricity_pct', 'emissions_2050']}
        dashboard = _make_dashboard(mock_results_analyzer, labels=labels)
        dashboard.current_scenario = postprocessing_scenario

        dashboard._render_metrics()

        mock_results_analyzer.calculate_dashboard_metrics.assert_called_once_with(postprocessing_scenario)
        labels['primary_energy_2050'].setText.assert_called_with("160.0 PJ")
        labels['electricity_2050'].setText.assert_called_with("100.0 TWh")
        labels['clean_electricity_pct'].setText.assert_called_with("50.0%")
        labels['emissions_2050'].setText.assert_called_with("90.0 Mt")

    def test_render_metrics_none_scenario(self, mock_results_analyzer):
        """_render_metrics sets '--' when scenario is None."""
        labels = {k: Mock() for k in ['primary_energy_2050', 'electricity_2050',
                                       'clean_electricity_pct', 'emissions_2050']}
        dashboard = _make_dashboard(mock_results_analyzer, labels=labels)
        dashboard.current_scenario = None

        dashboard._render_metrics()

        for label in labels.values():
            label.setText.assert_called_with("--")

    def test_render_metrics_error_handling(self, mock_results_analyzer, postprocessing_scenario):
        """_render_metrics sets 'Error' when calculate_dashboard_metrics raises."""
        mock_results_analyzer.calculate_dashboard_metrics.side_effect = Exception("boom")

        labels = {k: Mock() for k in ['primary_energy_2050', 'electricity_2050',
                                       'clean_electricity_pct', 'emissions_2050']}
        dashboard = _make_dashboard(mock_results_analyzer, labels=labels)
        dashboard.current_scenario = postprocessing_scenario

        dashboard._render_metrics()

        for label in labels.values():
            label.setText.assert_called_with("Error")

    def test_render_charts_no_scenario(self, mock_results_analyzer):
        """_render_charts shows placeholders when scenario is None."""
        views = {k: Mock() for k in ['primary_energy_demand', 'electricity_generation',
                                      'primary_energy_pie', 'electricity_pie']}
        dashboard = _make_dashboard(mock_results_analyzer, chart_views=views, elec_views={})
        dashboard.current_scenario = None

        dashboard._render_charts()

        for view in views.values():
            view.setHtml.assert_called_once()
            html = view.setHtml.call_args[0][0]
            assert "No postprocessing data loaded" in html

    def test_render_charts_with_data(self, mock_results_analyzer, postprocessing_scenario):
        """_render_charts renders charts when scenario has postprocessed data."""
        views = {k: Mock() for k in ['primary_energy_demand', 'electricity_generation',
                                      'primary_energy_pie', 'electricity_pie']}
        elec_views = {k: Mock() for k in ['electricity_generation_by_fuel',
                                           'electricity_costs_by_fuel']}
        dashboard = _make_dashboard(mock_results_analyzer, chart_views=views, elec_views=elec_views)
        dashboard.current_scenario = postprocessing_scenario

        dashboard._render_charts()

        # All 4 overview chart views should have received HTML
        for view in views.values():
            view.setHtml.assert_called_once()
            html = view.setHtml.call_args[0][0]
            assert PLOTLY_CDN_URL in html

        # Electricity tab charts should also have received HTML
        for view in elec_views.values():
            view.setHtml.assert_called_once()

    def test_render_charts_missing_primary_energy(self, mock_results_analyzer):
        """Charts show placeholder when primary energy param is missing."""
        scenario = ScenarioData()
        # Only add electricity, no primary energy
        elec_df = pd.DataFrame({
            'year': [2050], 'category': ['solar'], 'value': [25.0]
        })
        scenario.add_parameter(
            Parameter("Electricity generation by source (TWh)", elec_df, {
                'result_type': 'postprocessed'
            })
        )

        views = {k: Mock() for k in ['primary_energy_demand', 'electricity_generation',
                                      'primary_energy_pie', 'electricity_pie']}
        dashboard = _make_dashboard(mock_results_analyzer, chart_views=views, elec_views={})
        dashboard.current_scenario = scenario

        dashboard._render_charts()

        # Primary energy views should show placeholder
        pe_html = views['primary_energy_demand'].setHtml.call_args[0][0]
        assert "No primary energy supply data" in pe_html
        pie_html = views['primary_energy_pie'].setHtml.call_args[0][0]
        assert "No primary energy supply data" in pie_html

        # Electricity views should have chart data
        elec_html = views['electricity_generation'].setHtml.call_args[0][0]
        assert PLOTLY_CDN_URL in elec_html

    def test_electricity_tab_uses_by_source(self, mock_results_analyzer, postprocessing_scenario):
        """Electricity tab prefers 'by source' parameter over aggregate."""
        elec_views = {
            'electricity_generation_by_fuel': Mock(),
            'electricity_costs_by_fuel': Mock()
        }
        dashboard = _make_dashboard(mock_results_analyzer, chart_views={}, elec_views=elec_views)
        dashboard.current_scenario = postprocessing_scenario

        dashboard._render_electricity_charts()

        # Generation chart should have been rendered (not placeholder)
        gen_html = elec_views['electricity_generation_by_fuel'].setHtml.call_args[0][0]
        assert PLOTLY_CDN_URL in gen_html

    def test_electricity_cost_from_postprocessed_param(self, mock_results_analyzer, postprocessing_scenario):
        """Electricity cost chart reads from postprocessed LCOE parameter."""
        elec_views = {
            'electricity_generation_by_fuel': Mock(),
            'electricity_costs_by_fuel': Mock()
        }
        dashboard = _make_dashboard(mock_results_analyzer, chart_views={}, elec_views=elec_views)
        dashboard.current_scenario = postprocessing_scenario

        dashboard._render_electricity_charts()

        cost_html = elec_views['electricity_costs_by_fuel'].setHtml.call_args[0][0]
        assert PLOTLY_CDN_URL in cost_html

    def test_electricity_cost_fallback(self, mock_results_analyzer):
        """When no cost parameter exists, falls back to results_analyzer."""
        scenario = ScenarioData()
        elec_df = pd.DataFrame({
            'year': [2020, 2050], 'category': ['coal', 'coal'], 'value': [15, 20]
        })
        scenario.add_parameter(
            Parameter("Electricity generation by source (TWh)", elec_df, {
                'result_type': 'postprocessed'
            })
        )

        # Make the fallback return empty to trigger placeholder
        mock_results_analyzer.calculate_electricity_cost_breakdown.return_value = pd.DataFrame()

        elec_views = {
            'electricity_generation_by_fuel': Mock(),
            'electricity_costs_by_fuel': Mock()
        }
        dashboard = _make_dashboard(mock_results_analyzer, chart_views={}, elec_views=elec_views)
        dashboard.current_scenario = scenario

        dashboard._render_electricity_charts()

        # Fallback was called
        mock_results_analyzer.calculate_electricity_cost_breakdown.assert_called_once_with(scenario)
        # Placeholder shown because fallback returned empty
        cost_html = elec_views['electricity_costs_by_fuel'].setHtml.call_args[0][0]
        assert "No electricity cost data" in cost_html


# ---------------------------------------------------------------------------
# Controls tests (Limit years checkbox + Pie year combo)
# ---------------------------------------------------------------------------

class TestDashboardControls:
    """Tests for the dashboard controls: limit-years checkbox and pie-year combo."""

    def test_get_pie_year_default_without_combo(self, mock_results_analyzer):
        """_get_pie_year returns 2050 when no combo exists."""
        dashboard = _make_dashboard(mock_results_analyzer)
        assert dashboard._get_pie_year() == 2050

    def test_get_pie_year_with_combo(self, mock_results_analyzer):
        """_get_pie_year returns the value selected in the combo."""
        dashboard = _make_dashboard(mock_results_analyzer)
        combo = Mock()
        combo.count.return_value = 3
        combo.currentText.return_value = '2030'
        dashboard.pieYearCombo = combo
        assert dashboard._get_pie_year() == 2030

    def test_get_pie_year_invalid_text(self, mock_results_analyzer):
        """_get_pie_year falls back to 2050 for non-numeric text."""
        dashboard = _make_dashboard(mock_results_analyzer)
        combo = Mock()
        combo.count.return_value = 1
        combo.currentText.return_value = 'abc'
        dashboard.pieYearCombo = combo
        assert dashboard._get_pie_year() == 2050

    def test_is_limit_years_default(self, mock_results_analyzer):
        """_is_limit_years returns True (UserPreferences default)."""
        dashboard = _make_dashboard(mock_results_analyzer)
        assert dashboard._is_limit_years() is True

    def test_is_limit_years_enabled(self, mock_results_analyzer):
        """_is_limit_years returns True when user_prefs.limit_enabled is True."""
        prefs = UserPreferences(limit_enabled=True)
        dashboard = _make_dashboard(mock_results_analyzer, user_prefs=prefs)
        assert dashboard._is_limit_years() is True

    def test_is_limit_years_disabled(self, mock_results_analyzer):
        """_is_limit_years returns False when user_prefs.limit_enabled is False."""
        prefs = UserPreferences(limit_enabled=False)
        dashboard = _make_dashboard(mock_results_analyzer, user_prefs=prefs)
        assert dashboard._is_limit_years() is False

    def test_filter_param_years_limits_to_range(self, mock_results_analyzer):
        """_filter_param_years keeps only years within [min_year, max_year]."""
        prefs = UserPreferences(min_year=2020, max_year=2050, limit_enabled=True)
        dashboard = _make_dashboard(mock_results_analyzer, user_prefs=prefs)

        # Data includes years outside the default range
        df = pd.DataFrame({
            'year': [2010, 2015, 2020, 2025, 2030, 2035, 2040, 2045, 2050, 2055, 2060],
            'category': ['a'] * 11,
            'value': [1.0] * 11
        })
        param = Parameter("Test", df, {})
        filtered = dashboard._filter_param_years(param)

        assert list(filtered.df['year']) == [2020, 2025, 2030, 2035, 2040, 2045, 2050]

    def test_filter_param_years_custom_range(self, mock_results_analyzer):
        """_filter_param_years respects custom min/max year from user_prefs."""
        prefs = UserPreferences(min_year=2028, max_year=2042, limit_enabled=True)
        dashboard = _make_dashboard(mock_results_analyzer, user_prefs=prefs)

        # All years within range are kept, regardless of step
        df = pd.DataFrame({
            'year': [2020, 2025, 2028, 2030, 2035, 2040, 2042, 2045, 2050],
            'category': ['a'] * 9,
            'value': [1.0] * 9
        })
        param = Parameter("Test", df, {})
        filtered = dashboard._filter_param_years(param)

        assert list(filtered.df['year']) == [2028, 2030, 2035, 2040, 2042]

    def test_filter_param_years_no_limit(self, mock_results_analyzer):
        """_filter_param_years returns param unchanged when limit is off."""
        prefs = UserPreferences(limit_enabled=False)
        dashboard = _make_dashboard(mock_results_analyzer, user_prefs=prefs)

        df = pd.DataFrame({
            'year': [2020, 2022, 2025, 2028, 2030],
            'category': ['a'] * 5,
            'value': [1.0] * 5
        })
        param = Parameter("Test", df, {})
        result = dashboard._filter_param_years(param)

        # Should be the exact same object (not a copy)
        assert result is param

    def test_filter_param_years_none_param(self, mock_results_analyzer):
        """_filter_param_years returns None when param is None."""
        dashboard = _make_dashboard(mock_results_analyzer)
        assert dashboard._filter_param_years(None) is None

    def test_filter_param_years_all_filtered_returns_original(self, mock_results_analyzer):
        """If filtering removes everything, return original param."""
        prefs = UserPreferences(min_year=2020, max_year=2050, limit_enabled=True)
        dashboard = _make_dashboard(mock_results_analyzer, user_prefs=prefs)

        # Years completely outside the range
        df = pd.DataFrame({
            'year': [1990, 1995, 2070],
            'category': ['a'] * 3,
            'value': [1.0] * 3
        })
        param = Parameter("Test", df, {})
        result = dashboard._filter_param_years(param)
        assert result is param

    def test_populate_year_combo(self, mock_results_analyzer, postprocessing_scenario):
        """_populate_year_combo populates combo from data years."""
        dashboard = _make_dashboard(mock_results_analyzer)

        # Create a mock combo
        combo = Mock()
        combo.currentText.return_value = ''
        combo.findText.return_value = -1
        combo.count.return_value = 0
        dashboard.pieYearCombo = combo
        dashboard.current_scenario = postprocessing_scenario

        dashboard._populate_year_combo()

        # Should have called addItem for each unique year
        add_calls = [call[0][0] for call in combo.addItem.call_args_list]
        assert '2020' in add_calls
        assert '2050' in add_calls

    def test_populate_year_combo_defaults_to_2050(self, mock_results_analyzer, postprocessing_scenario):
        """_populate_year_combo selects 2050 by default."""
        dashboard = _make_dashboard(mock_results_analyzer)

        combo = Mock()
        combo.currentText.return_value = ''
        combo.findText.side_effect = lambda t: 1 if t == '2050' else -1
        combo.count.return_value = 2
        dashboard.pieYearCombo = combo
        dashboard.current_scenario = postprocessing_scenario

        dashboard._populate_year_combo()

        combo.setCurrentIndex.assert_called_with(1)

    def test_shared_user_prefs_syncs_dashboard(self, mock_results_analyzer, postprocessing_scenario):
        """Changing shared UserPreferences updates the dashboard's filtering."""
        prefs = UserPreferences(min_year=2020, max_year=2050, limit_enabled=True)
        dashboard = _make_dashboard(mock_results_analyzer, user_prefs=prefs)

        # Verify initial range
        assert dashboard.user_prefs.min_year == 2020
        assert dashboard.user_prefs.max_year == 2050

        # Change via shared prefs (as MainWindow/DataDisplay would)
        prefs.min_year = 2030
        prefs.max_year = 2040

        # Dashboard should now read the updated range
        assert dashboard.user_prefs.min_year == 2030
        assert dashboard.user_prefs.max_year == 2040

        # Filtering should use the new range
        df = pd.DataFrame({
            'year': [2020, 2025, 2030, 2035, 2040, 2045, 2050],
            'category': ['a'] * 7,
            'value': [1.0] * 7
        })
        param = Parameter("Test", df, {})
        filtered = dashboard._filter_param_years(param)
        assert list(filtered.df['year']) == [2030, 2035, 2040]

    def test_on_controls_changed_rerenders(self, mock_results_analyzer, postprocessing_scenario):
        """_on_controls_changed re-renders charts when scenario exists."""
        views = {k: Mock() for k in ['primary_energy_demand', 'electricity_generation',
                                      'primary_energy_pie', 'electricity_pie']}
        elec_views = {k: Mock() for k in ['electricity_generation_by_fuel',
                                           'electricity_costs_by_fuel']}
        dashboard = _make_dashboard(mock_results_analyzer, chart_views=views, elec_views=elec_views)
        dashboard.current_scenario = postprocessing_scenario

        dashboard._on_controls_changed()

        # All chart views should have been rendered
        for view in views.values():
            view.setHtml.assert_called_once()

    def test_on_controls_changed_no_scenario(self, mock_results_analyzer):
        """_on_controls_changed does nothing when no scenario."""
        views = {k: Mock() for k in ['primary_energy_demand']}
        dashboard = _make_dashboard(mock_results_analyzer, chart_views=views)
        dashboard.current_scenario = None

        dashboard._on_controls_changed()

        # No setHtml call because there's no scenario
        views['primary_energy_demand'].setHtml.assert_not_called()

    def test_pie_chart_uses_selected_year(self, mock_results_analyzer):
        """Pie charts use the year from the combo, not hardcoded 2050."""
        scenario = ScenarioData()
        pe_df = pd.DataFrame({
            'year': [2020, 2020, 2030, 2030, 2050, 2050],
            'category': ['coal', 'solar', 'coal', 'solar', 'coal', 'solar'],
            'value': [40.0, 10.0, 35.0, 20.0, 30.0, 30.0]
        })
        scenario.add_parameter(
            Parameter("Primary energy supply (PJ)", pe_df, {
                'result_type': 'postprocessed'
            })
        )

        views = {k: Mock() for k in ['primary_energy_demand', 'electricity_generation',
                                      'primary_energy_pie', 'electricity_pie']}
        dashboard = _make_dashboard(mock_results_analyzer, chart_views=views, elec_views={})
        dashboard.current_scenario = scenario

        # Set combo to 2030
        combo = Mock()
        combo.count.return_value = 3
        combo.currentText.return_value = '2030'
        dashboard.pieYearCombo = combo

        dashboard._render_charts()

        # Primary energy pie should contain '2030' in its HTML title
        pie_html = views['primary_energy_pie'].setHtml.call_args[0][0]
        assert '2030' in pie_html

    def test_bar_chart_respects_narrow_year_range(self, mock_results_analyzer):
        """Bar charts must only show years within the user_prefs range."""
        # Realistic postprocessed data: 7 years in 5-year steps
        years_all = [2020, 2025, 2030, 2035, 2040, 2045, 2050]
        pe_df = pd.DataFrame({
            'year': years_all * 2,
            'category': ['coal'] * 7 + ['solar'] * 7,
            'value': [40, 38, 35, 32, 28, 25, 22,
                      10, 12, 15, 20, 25, 30, 35]
        })
        scenario = ScenarioData()
        scenario.add_parameter(
            Parameter("Primary energy supply (PJ)", pe_df,
                      {'result_type': 'postprocessed'})
        )

        # Narrow the range to 2030-2040
        prefs = UserPreferences(min_year=2030, max_year=2040, limit_enabled=True)
        views = {k: Mock() for k in ['primary_energy_demand',
                                      'electricity_generation',
                                      'primary_energy_pie',
                                      'electricity_pie']}
        dashboard = _make_dashboard(mock_results_analyzer, chart_views=views,
                                    elec_views={}, user_prefs=prefs)
        dashboard.current_scenario = scenario

        dashboard._render_charts()

        bar_html = views['primary_energy_demand'].setHtml.call_args[0][0]
        # Years inside the range must appear in the chart
        assert '2030' in bar_html
        assert '2035' in bar_html
        assert '2040' in bar_html
        # Years outside the range must NOT appear in trace data.
        # Plotly encodes x-values as JSON arrays, e.g. [2030,2035,2040].
        # If 2020 appears, it would be as "2020" in the trace data.
        assert '2020' not in bar_html, "Year 2020 should be filtered out"
        assert '2025' not in bar_html, "Year 2025 should be filtered out"
        assert '2045' not in bar_html, "Year 2045 should be filtered out"
        assert '2050' not in bar_html, "Year 2050 should be filtered out"

    def test_on_controls_changed_syncs_limit_to_prefs(self, mock_results_analyzer):
        """_on_controls_changed writes checkbox state to user_prefs."""
        prefs = UserPreferences(limit_enabled=True)
        dashboard = _make_dashboard(mock_results_analyzer, user_prefs=prefs)
        # Simulate checkbox being unchecked
        checkbox = Mock()
        checkbox.isChecked.return_value = False
        dashboard.limitYearsCheckbox = checkbox

        dashboard._on_controls_changed()

        assert prefs.limit_enabled is False


# ---------------------------------------------------------------------------
# Mixin target_year tests
# ---------------------------------------------------------------------------

class TestMixinTargetYear:
    """Tests for render_energy_pie_chart target_year parameter."""

    def _make_mixin(self):
        class Concrete(DashboardChartMixin):
            pass
        return Concrete()

    def test_render_energy_pie_chart_custom_year(self):
        """render_energy_pie_chart filters to custom target_year."""
        mixin = self._make_mixin()
        view = Mock()
        df = pd.DataFrame({
            'year': [2020, 2020, 2030, 2030, 2050, 2050],
            'category': ['coal', 'gas', 'coal', 'gas', 'coal', 'gas'],
            'value': [40, 30, 50, 35, 55, 45]
        })
        param = Parameter("Test (PJ)", df, {})

        # Render for 2030
        mixin.render_energy_pie_chart(param, view, 'Title 2030', 'HTML', target_year=2030)
        view.setHtml.assert_called_once()
        html = view.setHtml.call_args[0][0]
        assert PLOTLY_CDN_URL in html

    def test_render_energy_pie_chart_missing_year(self):
        """render_energy_pie_chart shows placeholder for missing year."""
        mixin = self._make_mixin()
        view = Mock()
        df = pd.DataFrame({
            'year': [2020, 2050],
            'category': ['coal', 'coal'],
            'value': [40, 55]
        })
        param = Parameter("Test (PJ)", df, {})

        mixin.render_energy_pie_chart(param, view, 'Title', 'HTML', target_year=2040)
        html = view.setHtml.call_args[0][0]
        assert "No data available for year 2040" in html


# ---------------------------------------------------------------------------
# UserPreferences unit tests
# ---------------------------------------------------------------------------

class TestUserPreferences:
    """Tests for the shared UserPreferences object."""

    def test_defaults(self):
        prefs = UserPreferences()
        assert prefs.min_year == 2020
        assert prefs.max_year == 2050
        assert prefs.limit_enabled is True

    def test_custom_values(self):
        prefs = UserPreferences(min_year=2025, max_year=2045, limit_enabled=False)
        assert prefs.min_year == 2025
        assert prefs.max_year == 2045
        assert prefs.limit_enabled is False

    def test_to_dict(self):
        prefs = UserPreferences(min_year=2030, max_year=2040, limit_enabled=False)
        d = prefs.to_dict()
        assert d == {'YearsLimitEnabled': False, 'MinYear': 2030, 'MaxYear': 2040}

    def test_update_from_dict(self):
        prefs = UserPreferences()
        prefs.update_from_dict({'MinYear': 2025, 'MaxYear': 2045, 'YearsLimitEnabled': False})
        assert prefs.min_year == 2025
        assert prefs.max_year == 2045
        assert prefs.limit_enabled is False

    def test_changed_signal_on_min_year(self):
        prefs = UserPreferences()
        handler = Mock()
        prefs.changed.connect(handler)
        prefs.min_year = 2030
        handler.assert_called_once()

    def test_changed_signal_on_max_year(self):
        prefs = UserPreferences()
        handler = Mock()
        prefs.changed.connect(handler)
        prefs.max_year = 2040
        handler.assert_called_once()

    def test_changed_signal_on_limit_enabled(self):
        prefs = UserPreferences()
        handler = Mock()
        prefs.changed.connect(handler)
        prefs.limit_enabled = False
        handler.assert_called_once()

    def test_no_signal_when_value_unchanged(self):
        prefs = UserPreferences(min_year=2020)
        handler = Mock()
        prefs.changed.connect(handler)
        prefs.min_year = 2020  # same value
        handler.assert_not_called()

    def test_update_from_dict_emits_once(self):
        prefs = UserPreferences()
        handler = Mock()
        prefs.changed.connect(handler)
        prefs.update_from_dict({'MinYear': 2025, 'MaxYear': 2045})
        # Bulk update should emit only one changed signal
        handler.assert_called_once()
