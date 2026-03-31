"""
Tests for ComparisonParameterTreeWidget and the MergedParameter logic.
"""

import sys
import os

import pandas as pd
import pytest

src_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from core.data_models import Parameter, ScenarioData
from ui.scenarios_comparison.comparison_parameter_tree import (
    MergedParameter,
    _build_merged_list,
    _categorize_parameter,
    _categorize_variable,
)
from ui.components.parameter_tree_widget import _SECTION_ICONS, _CATEGORY_ICONS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_param(name: str, rows: int = 3, result_type: str = '') -> Parameter:
    df = pd.DataFrame({'tec': [f't{i}' for i in range(rows)], 'value': range(rows)})
    metadata = {'dims': ['tec'], 'units': '-'}
    if result_type:
        metadata['result_type'] = result_type
    return Parameter(name=name, df=df, metadata=metadata)


def _make_scenario_data(param_names, var_names=None, set_names=None):
    data = ScenarioData()
    for n in param_names:
        data.add_parameter(_make_param(n), mark_modified=False)
    if var_names:
        for n in var_names:
            data.add_parameter(_make_param(n, result_type='variable'), mark_modified=False)
    if set_names:
        for n in set_names:
            data.sets[n] = pd.Series([f'v{i}' for i in range(2)])
    return data


# ---------------------------------------------------------------------------
# _build_merged_list
# ---------------------------------------------------------------------------

class TestBuildMergedList:

    def test_common_params_detected_as_both(self):
        data_a = _make_scenario_data(['inv_cost', 'fix_cost'])
        data_b = _make_scenario_data(['inv_cost', 'fix_cost'])
        params, _ = _build_merged_list(data_a, data_b)
        presences = {p.name: p.presence for p in params}
        assert presences['inv_cost'] == 'both'
        assert presences['fix_cost'] == 'both'

    def test_a_only_param_detected(self):
        data_a = _make_scenario_data(['inv_cost', 'extra_a'])
        data_b = _make_scenario_data(['inv_cost'])
        params, _ = _build_merged_list(data_a, data_b)
        presences = {p.name: p.presence for p in params}
        assert presences['extra_a'] == 'a_only'

    def test_b_only_param_detected(self):
        data_a = _make_scenario_data(['inv_cost'])
        data_b = _make_scenario_data(['inv_cost', 'extra_b'])
        params, _ = _build_merged_list(data_a, data_b)
        presences = {p.name: p.presence for p in params}
        assert presences['extra_b'] == 'b_only'

    def test_row_counts_populated_for_both(self):
        data_a = _make_scenario_data(['inv_cost'])
        # Override row count for scenario B
        p_b = _make_param('inv_cost', rows=7)
        data_b = ScenarioData()
        data_b.add_parameter(p_b, mark_modified=False)
        params, _ = _build_merged_list(data_a, data_b)
        mp = next(p for p in params if p.name == 'inv_cost')
        assert mp.row_count_a == 3  # default rows in _make_param
        assert mp.row_count_b == 7

    def test_row_count_none_for_missing_scenario(self):
        data_a = _make_scenario_data(['only_in_a'])
        data_b = _make_scenario_data([])
        params, _ = _build_merged_list(data_a, data_b)
        mp = next(p for p in params if p.name == 'only_in_a')
        assert mp.row_count_b is None

    def test_sets_merged_correctly(self):
        data_a = _make_scenario_data([], set_names=['technology', 'node'])
        data_b = _make_scenario_data([], set_names=['technology', 'mode'])
        _, sets = _build_merged_list(data_a, data_b)
        set_presences = {s.name: s.presence for s in sets}
        assert set_presences['technology'] == 'both'
        assert set_presences['node'] == 'a_only'
        assert set_presences['mode'] == 'b_only'

    def test_variables_assigned_to_variables_section(self):
        data_a = _make_scenario_data([], var_names=['var_ACT'])
        data_b = _make_scenario_data([], var_names=['var_ACT'])
        params, _ = _build_merged_list(data_a, data_b)
        mp = next(p for p in params if p.name == 'var_ACT')
        assert mp.section == 'variables'


# ---------------------------------------------------------------------------
# Categorization helpers
# ---------------------------------------------------------------------------

class TestCategorizationHelpers:

    def test_emission_param_categorized_environmental(self):
        assert _categorize_parameter('emission_factor') == 'Environmental'
        assert _categorize_parameter('bound_emission') == 'Environmental'

    def test_cost_param_categorized_economic(self):
        assert _categorize_parameter('inv_cost') == 'Economic'
        assert _categorize_parameter('fix_cost') == 'Economic'

    def test_capacity_param_categorized_capacity(self):
        assert _categorize_parameter('capacity_factor') == 'Capacity & Investment'

    def test_bounds_categorized_correctly(self):
        assert _categorize_parameter('bound_activity_up') == 'Bounds & Constraints'
        assert _categorize_parameter('capacity_lo') == 'Bounds & Constraints'

    def test_var_act_categorized_activity(self):
        assert _categorize_variable('var_ACT') == 'Activity'

    def test_var_cap_categorized_capacity(self):
        assert _categorize_variable('var_CAP') == 'Capacity'

    def test_emission_variable_categorized_emissions(self):
        assert _categorize_variable('var_EMISS') == 'Emissions'


# ---------------------------------------------------------------------------
# Section icons match ParameterTreeWidget
# ---------------------------------------------------------------------------

class TestSectionIcons:

    def test_section_icons_present_for_all_expected_sections(self):
        for sec in ['parameters', 'variables', 'postprocessing', 'results', 'sets']:
            assert sec in _SECTION_ICONS, f"Missing icon for section '{sec}'"

    def test_category_icons_populated(self):
        for cat in ['Environmental', 'Economic', 'Capacity & Investment',
                    'Bounds & Constraints', 'Activity', 'Capacity', 'Emissions']:
            assert cat in _CATEGORY_ICONS, f"Missing icon for category '{cat}'"


# ---------------------------------------------------------------------------
# Widget smoke test (requires QApplication)
# ---------------------------------------------------------------------------

class TestComparisonParameterTreeWidget:

    def test_populate_does_not_raise(self, qtbot):
        from ui.scenarios_comparison.comparison_parameter_tree import ComparisonParameterTreeWidget
        widget = ComparisonParameterTreeWidget()
        qtbot.addWidget(widget)
        data_a = _make_scenario_data(['inv_cost', 'fix_cost', 'extra_a'])
        data_b = _make_scenario_data(['inv_cost', 'fix_cost', 'extra_b'])
        widget.populate(data_a, data_b, "ScenA", "ScenB")
        # Should have top-level section item(s)
        assert widget.topLevelItemCount() > 0

    def test_both_items_selectable(self, qtbot):
        from PyQt5.QtCore import Qt
        from ui.scenarios_comparison.comparison_parameter_tree import ComparisonParameterTreeWidget
        widget = ComparisonParameterTreeWidget()
        qtbot.addWidget(widget)
        data_a = _make_scenario_data(['shared'])
        data_b = _make_scenario_data(['shared'])
        widget.populate(data_a, data_b, "A", "B")

        def _find_leaf(parent, target_name):
            for i in range(parent.childCount()):
                child = parent.child(i)
                raw = child.data(0, Qt.UserRole)
                if raw == target_name:
                    return child
                found = _find_leaf(child, target_name)
                if found:
                    return found
            return None

        # Walk tree to find the 'shared' leaf
        leaf = None
        for i in range(widget.topLevelItemCount()):
            leaf = _find_leaf(widget.topLevelItem(i), 'shared')
            if leaf:
                break

        assert leaf is not None, "Leaf item 'shared' not found in tree"
        assert bool(leaf.flags() & Qt.ItemIsEnabled), "'shared' item should be enabled"
        assert bool(leaf.flags() & Qt.ItemIsSelectable), "'shared' item should be selectable"

    def test_exclusive_items_disabled(self, qtbot):
        from PyQt5.QtCore import Qt
        from ui.scenarios_comparison.comparison_parameter_tree import ComparisonParameterTreeWidget
        widget = ComparisonParameterTreeWidget()
        qtbot.addWidget(widget)
        data_a = _make_scenario_data(['only_a'])
        data_b = _make_scenario_data([])
        widget.populate(data_a, data_b, "A", "B")

        def _find_by_text(parent, fragment):
            for i in range(parent.childCount()):
                child = parent.child(i)
                if fragment in child.text(0):
                    return child
                found = _find_by_text(child, fragment)
                if found:
                    return found
            return None

        leaf = None
        for i in range(widget.topLevelItemCount()):
            leaf = _find_by_text(widget.topLevelItem(i), 'only_a')
            if leaf:
                break

        assert leaf is not None, "Leaf item 'only_a' not found in tree"
        assert not bool(leaf.flags() & Qt.ItemIsEnabled), "'only_a' item should be disabled"
