"""
Defines the valid MessageIX parameters, their dimensions, and descriptions.
Based on the canonical MESSAGEix scheme.
"""

import json


def get_code_display_names() -> dict:
    """Return a combined mapping of technology/commodity codes to human-readable names.

    Used to generate legend tooltips in charts.  The returned dict maps
    short identifiers (e.g. ``"sp_el_I"``) to their full display names
    (e.g. ``"Electricity specific industry"``).
    """
    names: dict[str, str] = {}
    for code, info in MESSAGE_IX_COMMODITIES.items():
        label = info.get("name") or info.get("description", code)
        if label != code:
            names[code] = label
    for code, info in MESSAGE_IX_TECHNOLOGIES.items():
        label = info.get("name") or info.get("description", code)
        if label != code:
            names[code] = label
    return names


def generate_legend_tooltip_script() -> str:
    """Return a ``<script>`` block that adds hover tooltips to Plotly legend items.

    The script embeds the full code-to-display-name mapping and creates a
    custom HTML tooltip ``<div>`` that appears when hovering over legend entries.
    A ``MutationObserver`` re-attaches listeners whenever Plotly re-draws.
    """
    mapping = get_code_display_names()
    return f"""
    <style>
    #legend-tooltip {{
        position: fixed;
        padding: 6px 10px;
        background: rgba(30, 30, 30, 0.92);
        color: #fff;
        font-size: 12px;
        font-family: Arial, sans-serif;
        border-radius: 4px;
        pointer-events: none;
        z-index: 99999;
        display: none;
        white-space: nowrap;
        box-shadow: 0 2px 6px rgba(0,0,0,0.3);
        max-width: 400px;
    }}
    </style>
    <div id="legend-tooltip"></div>
    <script>
    // --- Legend tooltip support ---
    var LEGEND_TOOLTIPS = {json.dumps(mapping, ensure_ascii=False)};
    var _ltTip = document.getElementById('legend-tooltip');
    var _ltBound = new WeakSet();  // track elements already wired up

    function _wireUpLegendTooltips() {{
        // Each legend entry is a <g class="traces"> containing a .legendtext
        var groups = document.querySelectorAll('.legend .traces');
        groups.forEach(function(g) {{
            if (_ltBound.has(g)) return;
            _ltBound.add(g);

            g.addEventListener('mouseenter', function(e) {{
                var textEl = g.querySelector('.legendtext');
                if (!textEl) return;
                var code = textEl.getAttribute('data-unformatted')
                           || textEl.textContent.trim();
                var tip = LEGEND_TOOLTIPS[code];
                if (tip && tip !== code) {{
                    _ltTip.textContent = tip;
                    _ltTip.style.display = 'block';
                    // Position near cursor
                    _ltTip.style.left = (e.clientX + 12) + 'px';
                    _ltTip.style.top  = (e.clientY - 28) + 'px';
                }}
            }});

            g.addEventListener('mousemove', function(e) {{
                if (_ltTip.style.display === 'block') {{
                    _ltTip.style.left = (e.clientX + 12) + 'px';
                    _ltTip.style.top  = (e.clientY - 28) + 'px';
                }}
            }});

            g.addEventListener('mouseleave', function() {{
                _ltTip.style.display = 'none';
            }});
        }});
    }}

    // Run after initial render, then watch for Plotly re-draws
    window.addEventListener('load', function() {{
        setTimeout(_wireUpLegendTooltips, 800);
        var target = document.querySelector('.js-plotly-plot');
        if (target) {{
            var _debounce = null;
            new MutationObserver(function() {{
                clearTimeout(_debounce);
                _debounce = setTimeout(_wireUpLegendTooltips, 200);
            }}).observe(target, {{ childList: true, subtree: true }});
        }}
    }});
    </script>
    """

# ---------------------------------------------------------------------------
# Canonical item-type registry extracted from message_ix.MESSAGE.items
# (ixmp.ItemType.SET / .PAR).  Used by the Excel parser to correctly route
# sheets to SetParsingStrategy vs ParameterParsingStrategy without importing
# message_ix at parse time (which can crash due to JVM / JPype init).
# ---------------------------------------------------------------------------

MESSAGE_IX_SET_NAMES: frozenset = frozenset({
    'addon', 'balance_equality', 'cat_addon', 'cat_emission', 'cat_node',
    'cat_relation', 'cat_tec', 'cat_year', 'commodity', 'emission', 'grade',
    'is_capacity_factor', 'land_scenario', 'land_type', 'level',
    'level_renewable', 'level_resource', 'level_stocks', 'level_storage',
    'lvl_spatial', 'lvl_temporal', 'map_node', 'map_shares_commodity_share',
    'map_shares_commodity_total', 'map_spatial_hierarchy', 'map_tec_addon',
    'map_tec_storage', 'map_temporal_hierarchy', 'map_time', 'mode', 'node',
    'rating', 'relation', 'shares', 'storage_tec', 'technology', 'time',
    'time_relative', 'type_addon', 'type_emission', 'type_node',
    'type_relation', 'type_tec', 'type_tec_land', 'type_year', 'year',
})

MESSAGE_IX_PAR_NAMES: frozenset = frozenset({
    'abs_cost_activity_soft_lo', 'abs_cost_activity_soft_up',
    'abs_cost_new_capacity_soft_lo', 'abs_cost_new_capacity_soft_up',
    'addon_conversion', 'addon_lo', 'addon_up', 'bound_activity_lo',
    'bound_activity_up', 'bound_emission', 'bound_extraction_up',
    'bound_new_capacity_lo', 'bound_new_capacity_up', 'bound_total_capacity_lo',
    'bound_total_capacity_up', 'capacity_factor', 'commodity_stock',
    'construction_time', 'demand', 'duration_period', 'duration_time',
    'dynamic_land_lo', 'dynamic_land_up', 'emission_factor', 'emission_scaling',
    'fix_cost', 'fixed_activity', 'fixed_capacity', 'fixed_extraction',
    'fixed_land', 'fixed_new_capacity', 'fixed_stock', 'flexibility_factor',
    'growth_activity_lo', 'growth_activity_up', 'growth_land_lo',
    'growth_land_scen_lo', 'growth_land_scen_up', 'growth_land_up',
    'growth_new_capacity_lo', 'growth_new_capacity_up', 'historical_activity',
    'historical_emission', 'historical_extraction', 'historical_gdp',
    'historical_land', 'historical_new_capacity', 'initial_activity_lo',
    'initial_activity_up', 'initial_land_lo', 'initial_land_scen_lo',
    'initial_land_scen_up', 'initial_land_up', 'initial_new_capacity_lo',
    'initial_new_capacity_up', 'input', 'interestrate', 'inv_cost',
    'land_cost', 'land_emission', 'land_input', 'land_output', 'land_use',
    'level_cost_activity_soft_lo', 'level_cost_activity_soft_up',
    'level_cost_new_capacity_soft_lo', 'level_cost_new_capacity_soft_up',
    'min_utilization_factor', 'operation_factor', 'output', 'peak_load_factor',
    'rating_bin', 'ref_activity', 'ref_extraction', 'ref_new_capacity',
    'ref_relation', 'relation_activity', 'relation_cost', 'relation_lower',
    'relation_new_capacity', 'relation_total_capacity', 'relation_upper',
    'reliability_factor', 'renewable_capacity_factor', 'renewable_potential',
    'resource_cost', 'resource_remaining', 'resource_volume', 'share_commodity_lo',
    'share_commodity_up', 'share_mode_lo', 'share_mode_up', 'soft_activity_lo',
    'soft_activity_up', 'soft_new_capacity_lo', 'soft_new_capacity_up',
    'storage_initial', 'storage_self_discharge', 'subsidy', 'tax',
    'tax_emission', 'technical_lifetime', 'time_order', 'var_cost',
})


MESSAGE_IX_PARAMETERS = {
    # 1. Core Technology Input–Output Parameters
    "input": {
        "dims": ["node_loc", "tec", "year_vtg", "year_act", "mode", "node_origin", "commodity", "level", "time", "time_origin"],
        "description": "Quantity of input commodity required per unit of technology activity",
        "type": "float"
    },
    "output": {
        "dims": ["node_loc", "tec", "year_vtg", "year_act", "mode", "node_dest", "commodity", "level", "time", "time_dest"],
        "description": "Quantity of output commodity produced per unit of activity",
        "type": "float"
    },
    "input_cap": {
        "dims": ["node_loc", "tec", "year_vtg", "year_act", "node_origin", "commodity", "level", "time_origin"],
        "description": "Input flow per unit of installed capacity",
        "type": "float"
    },
    "output_cap": {
        "dims": ["node_loc", "tec", "year_vtg", "year_act", "node_dest", "commodity", "level", "time_dest"],
        "description": "Output flow per unit of installed capacity",
        "type": "float"
    },
    "input_cap_new": {
        "dims": ["node_loc", "tec", "year_vtg", "node_origin", "commodity", "level", "time_origin"],
        "description": "Input per unit of newly built capacity",
        "type": "float"
    },
    "output_cap_new": {
        "dims": ["node_loc", "tec", "year_vtg", "node_dest", "commodity", "level", "time_dest"],
        "description": "Output per unit of newly built capacity",
        "type": "float"
    },
    "input_cap_ret": {
        "dims": ["node_loc", "tec", "year_vtg", "node_origin", "commodity", "level", "time_origin"],
        "description": "Input associated with retired capacity",
        "type": "float"
    },
    "output_cap_ret": {
        "dims": ["node_loc", "tec", "year_vtg", "node_dest", "commodity", "level", "time_dest"],
        "description": "Output associated with retired capacity",
        "type": "float"
    },

    # 2. Technical Performance Parameters
    "capacity_factor": {
        "dims": ["node_loc", "tec", "year_vtg", "year_act", "time"],
        "description": "Maximum utilization rate of capacity in a given time slice",
        "type": "float"
    },
    "renewable_capacity_factor": {
        "dims": ["node_loc", "commodity", "grade", "level", "year"],
        "description": "Quality of renewable potential by grade",
        "type": "float"
    },
    "renewable_potential": {
        "dims": ["node", "commodity", "grade", "level", "year"],
        "description": "Size of renewable potential per grade",
        "type": "float"
    },
    "operation_factor": {
        "dims": ["node_loc", "tec", "year_vtg", "year_act"],
        "description": "Fraction of the year the technology can operate",
        "type": "float"
    },
    "min_utilization_factor": {
        "dims": ["node_loc", "tec", "year_vtg", "year_act"],
        "description": "Minimum utilization requirement for installed capacity",
        "type": "float"
    },
    "technical_lifetime": {
        "dims": ["node_loc", "tec", "year_vtg"],
        "description": "Lifetime of a technology before retirement",
        "type": "float"
    },
    "construction_time": {
        "dims": ["node_loc", "tec", "year_vtg"],
        "description": "Time delay between investment and availability",
        "type": "float"
    },
    "rating_bin": {
        "dims": ["node", "tec", "year_act", "commodity", "level", "time", "rating"],
        "description": "Share of output assigned to a reliability rating bin",
        "type": "float"
    },
    "reliability_factor": {
        "dims": ["node", "tec", "year_act", "commodity", "level", "time", "rating"],
        "description": "Contribution of a rating bin to firm capacity",
        "type": "float"
    },
    "flexibility_factor": {
        "dims": ["node_loc", "tec", "year_vtg", "year_act", "mode", "commodity", "level", "time", "rating"],
        "description": "Contribution of a technology to system flexibility",
        "type": "float"
    },
    "addon_conversion": {
        "dims": ["node", "tec", "year_vtg", "year_act", "mode", "time", "type_addon"],
        "description": "Conversion factor for add-on technologies",
        "type": "float"
    },
    "addon_up": {
        "dims": ["node", "tec", "year_act", "mode", "time", "type_addon"],
        "description": "Upper bound on add-on technology relative to parent",
        "type": "float"
    },
    "addon_lo": {
        "dims": ["node", "tec", "year_act", "mode", "time", "type_addon"],
        "description": "Lower bound on add-on technology relative to parent",
        "type": "float"
    },
    "storage_initial": {
        "dims": ["node", "tec", "level", "commodity", "year_act", "time"],
        "description": "Initial storage level",
        "type": "float"
    },
    "storage_self_discharge": {
        "dims": ["node", "tec", "level", "commodity", "year_act", "time"],
        "description": "Fraction of stored energy lost per time slice",
        "type": "float"
    },
    "time_order": {
        "dims": ["lvl_temporal", "time"],
        "description": "Ordering of subannual time slices",
        "type": "float"
    },

    # 3. Cost and Economic Parameters
    "inv_cost": {
        "dims": ["node_loc", "tec", "year_vtg"],
        "description": "Investment cost per unit of new capacity",
        "type": "float"
    },
    "fix_cost": {
        "dims": ["node_loc", "tec", "year_vtg", "year_act"],
        "description": "Fixed O&M cost per unit of capacity",
        "type": "float"
    },
    "var_cost": {
        "dims": ["node_loc", "tec", "year_vtg", "year_act", "mode", "time"],
        "description": "Variable cost per unit of activity",
        "type": "float"
    },
    "levelized_cost": {
        "dims": ["node_loc", "tec", "year_vtg", "time"],
        "description": "Exogenously specified levelized cost",
        "type": "float"
    },
    "construction_time_factor": {
        "dims": ["node", "tec", "year"],
        "description": "Capital cost weighting during construction",
        "type": "float"
    },
    "remaining_capacity": {
        "dims": ["node", "tec", "year"],
        "description": "Fraction of capacity remaining from earlier vintages",
        "type": "float"
    },
    "remaining_capacity_extended": {
        "dims": ["node", "tec", "year"],
        "description": "Extended formulation of remaining capacity",
        "type": "float"
    },
    "end_of_horizon_factor": {
        "dims": ["node", "tec", "year"],
        "description": "Salvage value factor at model horizon",
        "type": "float"
    },
    "beyond_horizon_lifetime": {
        "dims": ["node", "tec", "year"],
        "description": "Remaining lifetime beyond model horizon",
        "type": "float"
    },
    "beyond_horizon_factor": {
        "dims": ["node", "tec", "year"],
        "description": "Discount factor for post-horizon capacity",
        "type": "float"
    },

    # 4. Capacity and Activity Bounds (Hard)
    "bound_new_capacity_up": {"dims": ["node_loc", "tec", "year_vtg"], "description": "Upper bound on new capacity additions", "type": "float"},
    "bound_new_capacity_lo": {"dims": ["node_loc", "tec", "year_vtg"], "description": "Lower bound on new capacity additions", "type": "float"},
    "bound_total_capacity_up": {"dims": ["node_loc", "tec", "year_act"], "description": "Upper bound on total installed capacity", "type": "float"},
    "bound_total_capacity_lo": {"dims": ["node_loc", "tec", "year_act"], "description": "Lower bound on total installed capacity", "type": "float"},
    "bound_activity_up": {"dims": ["node_loc", "tec", "year_act", "mode", "time"], "description": "Upper bound on activity", "type": "float"},
    "bound_activity_lo": {"dims": ["node_loc", "tec", "year_act", "mode", "time"], "description": "Lower bound on activity", "type": "float"},

    # 5. Dynamic Growth Constraints
    "initial_new_capacity_up": {"dims": ["node_loc", "tec", "year_vtg"], "description": "Initial upper bound on new capacity", "type": "float"},
    "growth_new_capacity_up": {"dims": ["node_loc", "tec", "year_vtg"], "description": "Growth rate limit for new capacity (up)", "type": "float"},
    "initial_new_capacity_lo": {"dims": ["node_loc", "tec", "year_vtg"], "description": "Initial lower bound on new capacity", "type": "float"},
    "growth_new_capacity_lo": {"dims": ["node_loc", "tec", "year_vtg"], "description": "Growth rate limit for new capacity (down)", "type": "float"},
    "initial_activity_up": {"dims": ["node_loc", "tec", "year_act", "time"], "description": "Initial activity upper bound", "type": "float"},
    "growth_activity_up": {"dims": ["node_loc", "tec", "year_act", "time"], "description": "Activity growth limit (up)", "type": "float"},
    "initial_activity_lo": {"dims": ["node_loc", "tec", "year_act", "time"], "description": "Initial activity lower bound", "type": "float"},
    "growth_activity_lo": {"dims": ["node_loc", "tec", "year_act", "time"], "description": "Activity growth limit (down)", "type": "float"},

    # 5b. Historical Data
    "historical_new_capacity": {"dims": ["node_loc", "tec", "year_vtg"], "description": "Historical new capacity additions", "type": "float"},
    "historical_activity": {"dims": ["node_loc", "tec", "year_act", "mode", "time"], "description": "Historical activity levels", "type": "float"},

    # 6. Soft Constraints (Penalty-Based)
    "soft_new_capacity_up": {"dims": ["node_loc", "tec", "year_vtg"], "description": "Soft upper bound on new capacity", "type": "float"},
    "soft_new_capacity_lo": {"dims": ["node_loc", "tec", "year_vtg"], "description": "Soft lower bound on new capacity", "type": "float"},
    "soft_activity_up": {"dims": ["node_loc", "tec", "year_act", "time"], "description": "Soft upper bound on activity", "type": "float"},
    "soft_activity_lo": {"dims": ["node_loc", "tec", "year_act", "time"], "description": "Soft lower bound on activity", "type": "float"},
    "abs_cost_new_capacity_soft_up": {"dims": ["node_loc", "tec", "year_vtg"], "description": "Absolute penalty for violating new-capacity upper bound", "type": "float"},
    "level_cost_new_capacity_soft_up": {"dims": ["node_loc", "tec", "year_vtg"], "description": "Marginal penalty for new-capacity upper bound", "type": "float"},
    "abs_cost_activity_soft_up": {"dims": ["node_loc", "tec", "year_act", "time"], "description": "Absolute penalty for activity upper bound", "type": "float"},
    "level_cost_activity_soft_up": {"dims": ["node_loc", "tec", "year_act", "time"], "description": "Marginal penalty for activity upper bound", "type": "float"},
    "abs_cost_new_capacity_soft_lo": {"dims": ["node_loc", "tec", "year_vtg"], "description": "Absolute cost for relaxing lower bound on new capacity", "type": "float"},
    "level_cost_new_capacity_soft_lo": {"dims": ["node_loc", "tec", "year_vtg"], "description": "Levelized cost for relaxing lower bound on new capacity", "type": "float"},
    "abs_cost_activity_soft_lo": {"dims": ["node_loc", "tec", "year_act", "time"], "description": "Absolute cost for relaxing lower bound on activity", "type": "float"},
    "level_cost_activity_soft_lo": {"dims": ["node_loc", "tec", "year_act", "time"], "description": "Levelized cost for relaxing lower bound on activity", "type": "float"},

    # 7. Emissions (Technology Level)
    "emission_factor": {"dims": ["node_loc", "tec", "year_vtg", "year_act", "mode", "emission"], "description": "Emissions per unit of activity", "type": "float"},

    # 8. Emissions Accounting & Policy
    "historical_emission": {"dims": ["node", "emission", "type_tec", "year"], "description": "Exogenous historical emissions", "type": "float"},
    "emission_scaling": {"dims": ["type_emission", "emission"], "description": "Scaling factor for emissions aggregation", "type": "float"},
    "bound_emission": {"dims": ["node", "type_emission", "type_tec", "type_year"], "description": "Emissions cap", "type": "float"},
    "tax_emission": {"dims": ["node", "type_emission", "type_tec", "type_year"], "description": "Emissions tax", "type": "float"},

    # 9. Resources & Extraction
    "resource_volume": {"dims": ["node", "commodity", "grade"], "description": "Total available resource", "type": "float"},
    "resource_cost": {"dims": ["node", "commodity", "grade", "year"], "description": "Extraction cost", "type": "float"},
    "resource_remaining": {"dims": ["node", "commodity", "grade", "year"], "description": "Remaining resource stock", "type": "float"},
    "bound_extraction_up": {"dims": ["node", "commodity", "level", "year"], "description": "Upper bound on extraction", "type": "float"},
    "commodity_stock": {"dims": ["node", "commodity", "level", "year"], "description": "Stock of commodity", "type": "float"},
    "historical_extraction": {"dims": ["node", "commodity", "grade", "year"], "description": "Historical extraction levels", "type": "float"},

    # 10. Demand & Load Representation
    "demand": {"dims": ["node", "commodity", "level", "year", "time"], "description": "Exogenous final demand", "type": "float"},
    "peak_load_factor": {"dims": ["node", "commodity", "year"], "description": "Ratio of peak to average load", "type": "float"},

    # 11. Land-Use & Bioenergy Emulator
    "historical_land": {"dims": ["node", "land_scenario", "year"], "description": "Historical land allocation", "type": "float"},
    "land_cost": {"dims": ["node", "land_scenario", "year"], "description": "Cost of land use", "type": "float"},
    "land_input": {"dims": ["node", "land_scenario", "year", "commodity", "level", "time"], "description": "Inputs to land system", "type": "float"},
    "land_output": {"dims": ["node", "land_scenario", "year", "commodity", "level", "time"], "description": "Outputs from land system", "type": "float"},
    "land_use": {"dims": ["node", "land_scenario", "year", "land_type"], "description": "Land allocation by type", "type": "float"},
    "land_emission": {"dims": ["node", "land_scenario", "year", "emission"], "description": "Emissions from land use", "type": "float"},
    "initial_land_up": {"dims": ["node", "year", "land_type"], "description": "Initial land upper bound", "type": "float"},
    "initial_land_lo": {"dims": ["node", "year", "land_type"], "description": "Initial land lower bound", "type": "float"},
    "growth_land_up": {"dims": ["node", "year", "land_type"], "description": "Land growth limit (up)", "type": "float"},
    "growth_land_lo": {"dims": ["node", "year", "land_type"], "description": "Land growth limit (down)", "type": "float"},

    # 12. Share Constraints
    "share_commodity_up": {"dims": ["shares", "node_share", "year_act", "time"], "description": "Upper bound on commodity share", "type": "float"},
    "share_commodity_lo": {"dims": ["shares", "node", "year_act", "time"], "description": "Lower bound on commodity share", "type": "float"},
    "share_mode_up": {"dims": ["shares", "node_loc", "tec", "mode", "year_act", "time"], "description": "Upper bound on mode share", "type": "float"},
    "share_mode_lo": {"dims": ["shares", "node_loc", "tec", "mode", "year_act", "time"], "description": "Lower bound on mode share", "type": "float"},

    # 13. Generic Relations
    "relation_upper": {"dims": ["relation", "node_rel", "year_rel"], "description": "Upper bound on relation", "type": "float"},
    "relation_lower": {"dims": ["relation", "node_rel", "year_rel"], "description": "Lower bound on relation", "type": "float"},
    "relation_cost": {"dims": ["relation", "node_rel", "year_rel"], "description": "Cost of relation slack", "type": "float"},
    "relation_new_capacity": {"dims": ["relation", "node_rel", "year_rel", "tec"], "description": "Capacity term in relation", "type": "float"},
    "relation_total_capacity": {"dims": ["relation", "node_rel", "year_rel", "tec"], "description": "Total capacity term", "type": "float"},
    "relation_activity": {"dims": ["relation", "node_rel", "year_rel", "node_loc", "tec", "year_act", "mode"], "description": "Activity term", "type": "float"},

    # 14. Fixed Variables (Exogenous Decisions)
    "fixed_extraction": {"dims": ["node", "commodity", "grade", "year"], "description": "Fixed extraction level", "type": "float"},
    "fixed_stock": {"dims": ["node", "commodity", "level", "year"], "description": "Fixed stock level", "type": "float"},
    "fixed_new_capacity": {"dims": ["node", "tec", "year_vtg"], "description": "Fixed new capacity", "type": "float"},
    "fixed_capacity": {"dims": ["node", "tec", "year_vtg", "year_act"], "description": "Fixed installed capacity", "type": "float"},
    "fixed_activity": {"dims": ["node", "tec", "year_vtg", "year_act", "mode", "time"], "description": "Fixed activity", "type": "float"},
    "fixed_land": {"dims": ["node", "land_scenario", "year"], "description": "Fixed land allocation", "type": "float"},

    # 15. Reporting Parameters
    "total_cost": {"dims": ["node", "year"], "description": "Total system cost including trade and emission taxes", "type": "float"},
    "trade_cost": {"dims": ["node", "year"], "description": "Net cost from trade (exports minus imports)", "type": "float"},
    "import_cost": {"dims": ["node", "commodity", "year"], "description": "Cost from importing commodities", "type": "float"},
    "export_cost": {"dims": ["node", "commodity", "year"], "description": "Revenue from exporting commodities", "type": "float"},
}

PARAMETER_CATEGORIES = {
    "Core Technology Input–Output": ["input", "output", "input_cap", "output_cap", "input_cap_new", "output_cap_new", "input_cap_ret", "output_cap_ret"],
    "Technical Performance": ["capacity_factor", "operation_factor", "min_utilization_factor", "technical_lifetime", "construction_time", "rating_bin", "reliability_factor", "flexibility_factor", "addon_conversion", "addon_up", "addon_lo", "storage_initial", "storage_self_discharge", "time_order", "renewable_capacity_factor", "renewable_potential"],
    "Cost and Economic": ["inv_cost", "fix_cost", "var_cost", "levelized_cost", "construction_time_factor", "remaining_capacity", "remaining_capacity_extended", "end_of_horizon_factor", "beyond_horizon_lifetime", "beyond_horizon_factor"],
    "Capacity and Activity Bounds": ["bound_new_capacity_up", "bound_new_capacity_lo", "bound_total_capacity_up", "bound_total_capacity_lo", "bound_activity_up", "bound_activity_lo"],
    "Dynamic Growth Constraints": ["initial_new_capacity_up", "growth_new_capacity_up", "initial_new_capacity_lo", "growth_new_capacity_lo", "initial_activity_up", "growth_activity_up", "initial_activity_lo", "growth_activity_lo"],
    "Soft Constraints": ["soft_new_capacity_up", "soft_new_capacity_lo", "soft_activity_up", "soft_activity_lo", "abs_cost_new_capacity_soft_up", "level_cost_new_capacity_soft_up", "abs_cost_activity_soft_up", "level_cost_activity_soft_up", "abs_cost_new_capacity_soft_lo", "level_cost_new_capacity_soft_lo", "abs_cost_activity_soft_lo", "level_cost_activity_soft_lo"],
    "Emissions": ["emission_factor"],
    "Emissions Policy": ["historical_emission", "emission_scaling", "bound_emission", "tax_emission"],
    "Resources & Extraction": ["resource_volume", "resource_cost", "resource_remaining", "bound_extraction_up", "commodity_stock", "historical_extraction"],
    "Demand & Load": ["demand", "peak_load_factor"],
    "Land-Use": ["historical_land", "land_cost", "land_input", "land_output", "land_use", "land_emission", "initial_land_up", "initial_land_lo", "growth_land_up", "growth_land_lo"],
    "Share Constraints": ["share_commodity_up", "share_commodity_lo", "share_mode_up", "share_mode_lo"],
    "Generic Relations": ["relation_upper", "relation_lower", "relation_cost", "relation_new_capacity", "relation_total_capacity", "relation_activity"],
    "Fixed Variables": ["fixed_extraction", "fixed_stock", "fixed_new_capacity", "fixed_capacity", "fixed_activity", "fixed_land"],
    "Historical Data": ["historical_new_capacity", "historical_activity"],
    "Reporting": ["total_cost", "trade_cost", "import_cost", "export_cost"]
}

# ---------------------------------------------------------------------------
# Commodity codelist
# Based on: https://docs.messageix.org/projects/models/en/stable/pkg-data/codelists.html
# Keys = commodity IDs used in MESSAGEix scenarios.
# "report-only" entries are aggregation nodes for reporting and are excluded.
# ---------------------------------------------------------------------------

MESSAGE_IX_COMMODITIES = {
    # --- Energy carriers ---
    "biomass": {
        "name": "Biomass",
        "description": "Solid biomass energy carrier",
        "units": "GWa",
    },
    "coal": {
        "name": "Coal",
        "description": "Hard coal (Other Bituminous Coal)",
        "units": "GWa",
    },
    "lignite": {
        "name": "Lignite",
        "description": "Lignite coal",
        "units": "GWa",
    },
    "crudeoil": {
        "name": "Crude oil",
        "description": "Crude oil at primary level",
        "level": "primary",
        "units": "GWa",
    },
    "fueloil": {
        "name": "Fuel oil",
        "description": "Heavy fuel oil (Residual Fuel Oil)",
        "level": "secondary",
        "units": "GWa",
    },
    "lightoil": {
        "name": "Light oil",
        "description": "Includes gasoline, diesel oil",
        "units": "GWa",
    },
    "gas": {
        "name": "Natural Gas",
        "description": "Natural gas (dry)",
        "units": "GWa",
    },
    "electr": {
        "name": "Electricity",
        "description": "Electricity",
        "units": "GWa",
    },
    "hydrogen": {
        "name": "Gaseous hydrogen",
        "description": "Gaseous hydrogen",
        "units": "GWa",
    },
    "lh2": {
        "name": "Liquid hydrogen",
        "description": "Liquid hydrogen",
        "units": "GWa",
    },
    "ethanol": {
        "name": "Ethanol",
        "description": "Ethanol fuel",
        "units": "GWa",
    },
    "methanol": {
        "name": "Methanol",
        "description": "Methanol",
        "units": "GWa",
    },
    "d_heat": {
        "name": "District heat",
        "description": "District heat commodity",
        "units": "GWa",
    },
    "non-comm": {
        "name": "Non-commercial biomass",
        "description": "Non-commercial (traditional) biomass",
        "units": "GWa",
    },

    # --- Resource grades (oil) ---
    "crude_1": {"description": "Crude oil resource grade 1"},
    "crude_2": {"description": "Crude oil resource grade 2"},
    "crude_3": {"description": "Crude oil resource grade 3"},
    "crude_4": {"description": "Crude oil resource grade 4"},
    "crude_5": {"description": "Crude oil resource grade 5"},
    "crude_6": {"description": "Crude oil resource grade 6"},
    "crude_7": {"description": "Crude oil resource grade 7"},
    "crude_8": {"description": "Crude oil resource grade 8"},

    # --- Resource grades (gas) ---
    "gas_1": {"description": "Natural gas resource grade 1"},
    "gas_2": {"description": "Natural gas resource grade 2"},
    "gas_3": {"description": "Natural gas resource grade 3"},
    "gas_4": {"description": "Natural gas resource grade 4"},
    "gas_5": {"description": "Natural gas resource grade 5"},
    "gas_6": {"description": "Natural gas resource grade 6"},
    "gas_7": {"description": "Natural gas resource grade 7"},
    "gas_8": {"description": "Natural gas resource grade 8"},

    # --- Resource (uranium) ---
    "uranium": {"description": "Uranium resource"},

    # --- End-use / service demands ---
    "i_therm": {
        "name": "Industrial thermal",
        "description": "Industrial thermal energy demand",
        "level": "useful",
        "units": "GWa",
    },
    "i_spec": {
        "name": "Industrial specific",
        "description": "Industrial specific (electric) energy demand",
        "level": "useful",
        "units": "GWa",
    },
    "i_feed": {
        "name": "Industrial feedstock",
        "description": "Industrial feedstock (non-energy) demand",
        "level": "useful",
        "units": "GWa",
    },
    "rc_spec": {
        "name": "Residential/commercial specific",
        "description": "Residential and commercial non-substitutable fuels",
        "level": "useful",
    },
    "rc_therm": {
        "name": "Residential/commercial thermal",
        "description": "Residential and commercial thermal demand",
        "level": "useful",
    },
    "transport": {
        "name": "Transportation",
        "description": "Transportation service demand",
        "level": "useful",
        "units": "GWa",
    },
    "freshwater_supply": {
        "name": "Fresh water",
        "description": "Fresh water supply",
    },
}

COMMODITY_CATEGORIES = {
    "Primary Energy": ["biomass", "coal", "lignite", "crudeoil", "gas", "uranium"],
    "Secondary Energy": ["electr", "fueloil", "lightoil", "hydrogen", "lh2", "ethanol", "methanol", "d_heat"],
    "Non-commercial": ["non-comm"],
    "Oil Resources": ["crude_1", "crude_2", "crude_3", "crude_4", "crude_5", "crude_6", "crude_7", "crude_8"],
    "Gas Resources": ["gas_1", "gas_2", "gas_3", "gas_4", "gas_5", "gas_6", "gas_7", "gas_8"],
    "End-use Demands": ["i_therm", "i_spec", "i_feed", "rc_spec", "rc_therm", "transport", "freshwater_supply"],
}

# ---------------------------------------------------------------------------
# Technology codelist
# Based on: https://docs.messageix.org/projects/models/en/stable/pkg-data/codelists.html
# ---------------------------------------------------------------------------

MESSAGE_IX_TECHNOLOGIES = {
    # ===== Electricity generation =====
    "bio_istig": {"name": "Biomass ISTIG", "description": "Advanced biomass power plant – gasified biomass burned in gas turbine", "sector": "electricity"},
    "bio_istig_ccs": {"name": "Biomass ISTIG CCS", "description": "Advanced biomass power plant with carbon capture and storage", "sector": "electricity"},
    "bio_ppl": {"name": "Biomass power plant", "description": "Bio powerplant", "sector": "electricity"},
    "coal_adv": {"name": "Advanced coal", "description": "Advanced coal power plant", "sector": "electricity"},
    "coal_adv_ccs": {"name": "Advanced coal CCS", "description": "Advanced coal power plant with carbon capture and storage", "sector": "electricity"},
    "coal_ppl": {"name": "Coal power plant", "description": "Coal power-plant", "sector": "electricity"},
    "coal_ppl_u": {"name": "Coal power plant (unabated)", "description": "Coal power plant without abatement measures", "sector": "electricity"},
    "elec_exp": {"name": "Electricity export", "description": "Net export of electricity", "sector": "electricity"},
    "elec_imp": {"name": "Electricity import", "description": "Net import of electricity", "sector": "electricity"},
    "elec_t/d": {"name": "Electricity T&D", "description": "Electricity transmission and distribution grid", "sector": "electricity"},
    "foil_ppl": {"name": "Fuel oil power plant", "description": "New standard oil power plant, Rankine cycle", "sector": "electricity"},
    "gas_cc": {"name": "Gas combined cycle", "description": "Gas combined cycle power-plant", "sector": "electricity"},
    "gas_cc_ccs": {"name": "Gas CC CCS", "description": "Gas combined cycle power-plant with carbon capture and storage", "sector": "electricity"},
    "gas_ct": {"name": "Gas combustion turbine", "description": "Gas combustion-turbine power plant", "sector": "electricity"},
    "gas_htfc": {"name": "Gas fuel cell", "description": "High temperature fuel cell powered with natural gas", "sector": "electricity"},
    "gas_ppl": {"name": "Gas power plant", "description": "Gas power plant, Rankine cycle", "sector": "electricity"},
    "geo_ppl": {"name": "Geothermal power plant", "description": "Geothermal power plant", "sector": "electricity"},
    "glb_elec_exp": {"name": "Global electricity export", "description": "Global net export of electricity", "sector": "electricity"},
    "glb_elec_imp": {"name": "Global electricity import", "description": "Global net import of electricity", "sector": "electricity"},
    "hydro_hc": {"name": "Hydro (high cost)", "description": "High cost hydro power plant", "sector": "electricity"},
    "hydro_lc": {"name": "Hydro (low cost)", "description": "Low cost hydro power plant", "sector": "electricity"},
    "igcc": {"name": "IGCC", "description": "Integrated gasification combined cycle power plant", "sector": "electricity"},
    "igcc_ccs": {"name": "IGCC CCS", "description": "Integrated gasification combined cycle plant with CCS", "sector": "electricity"},
    "igcc_co2scr": {"name": "IGCC CO2 scrubber", "description": "New coal scrubber for IGCC plants", "sector": "electricity"},
    "loil_cc": {"name": "Light oil combined cycle", "description": "Light oil combined cycle", "sector": "electricity"},
    "loil_ppl": {"name": "Light oil power plant", "description": "Existing light oil power-plant", "sector": "electricity"},
    "nuc_hc": {"name": "Nuclear (high cost)", "description": "Nuclear power plant (~GEN III+), high cost", "sector": "electricity"},
    "nuc_lc": {"name": "Nuclear (low cost)", "description": "Nuclear power plant (~GEN II), low cost", "sector": "electricity"},
    "stor_ppl": {"name": "Electric storage", "description": "Generic electric storage", "sector": "electricity"},

    # --- Solar ---
    "solar_pv_ppl": {"name": "Solar PV", "description": "Solar photovoltaic power plant (no storage)", "sector": "electricity"},
    "solar_th_ppl": {"name": "Solar thermal", "description": "Solar thermal power plant with storage", "sector": "electricity"},
    "solar_curtailment1": {"name": "Solar curtailment 1", "description": "Solar PV curtailment step 1", "sector": "electricity"},
    "solar_curtailment2": {"name": "Solar curtailment 2", "description": "Solar PV curtailment step 2", "sector": "electricity"},
    "solar_curtailment3": {"name": "Solar curtailment 3", "description": "Solar PV curtailment step 3", "sector": "electricity"},
    "solar_cv1": {"name": "Solar integration cost 1", "description": "Quadratic systems integration costs for solar PV step 1", "sector": "electricity"},
    "solar_cv2": {"name": "Solar integration cost 2", "description": "Quadratic systems integration costs for solar PV step 2", "sector": "electricity"},
    "solar_cv3": {"name": "Solar integration cost 3", "description": "Quadratic systems integration costs for solar PV step 3", "sector": "electricity"},
    "solar_cv4": {"name": "Solar integration cost 4", "description": "Quadratic systems integration costs for solar PV step 4", "sector": "electricity"},
    "solar_res1": {"name": "Solar potential 1", "description": "Maximum solar electricity potential 1", "sector": "electricity"},
    "solar_res2": {"name": "Solar potential 2", "description": "Maximum solar electricity potential 2", "sector": "electricity"},
    "solar_res3": {"name": "Solar potential 3", "description": "Maximum solar electricity potential 3", "sector": "electricity"},
    "solar_res4": {"name": "Solar potential 4", "description": "Maximum solar electricity potential 4", "sector": "electricity"},
    "solar_res5": {"name": "Solar potential 5", "description": "Maximum solar electricity potential 5", "sector": "electricity"},
    "solar_res6": {"name": "Solar potential 6", "description": "Maximum solar electricity potential 6", "sector": "electricity"},
    "solar_res7": {"name": "Solar potential 7", "description": "Maximum solar electricity potential 7", "sector": "electricity"},
    "solar_res8": {"name": "Solar potential 8", "description": "Maximum solar electricity potential 8", "sector": "electricity"},
    "solar_res_hist_2000": {"name": "Solar installed 2000", "description": "Currently installed solar capacity with 2000 vintage", "sector": "electricity"},
    "solar_res_hist_2005": {"name": "Solar installed 2005", "description": "Currently installed solar capacity with 2005 vintage", "sector": "electricity"},
    "solar_res_hist_2010": {"name": "Solar installed 2010", "description": "Currently installed solar capacity with 2010 vintage", "sector": "electricity"},
    "solar_res_hist_2015": {"name": "Solar installed 2015", "description": "Currently installed solar capacity with 2015 vintage", "sector": "electricity"},
    "solar_res_hist_2020": {"name": "Solar installed 2020", "description": "Currently installed solar capacity with 2020 vintage", "sector": "electricity"},
    "solar_res_hist_2025": {"name": "Solar installed 2025", "description": "Currently installed solar capacity with 2025 vintage", "sector": "electricity"},
    "solar_res_rt_hist_2000": {"name": "Solar rooftop installed 2000", "description": "Installed rooftop solar capacity with 2000 vintage", "sector": "electricity"},
    "solar_res_rt_hist_2005": {"name": "Solar rooftop installed 2005", "description": "Installed rooftop solar capacity with 2005 vintage", "sector": "electricity"},
    "solar_res_rt_hist_2010": {"name": "Solar rooftop installed 2010", "description": "Installed rooftop solar capacity with 2010 vintage", "sector": "electricity"},
    "solar_res_rt_hist_2015": {"name": "Solar rooftop installed 2015", "description": "Installed rooftop solar capacity with 2015 vintage", "sector": "electricity"},
    "solar_res_rt_hist_2020": {"name": "Solar rooftop installed 2020", "description": "Installed rooftop solar capacity with 2020 vintage", "sector": "electricity"},
    "solar_res_rt_hist_2025": {"name": "Solar rooftop installed 2025", "description": "Installed rooftop solar capacity with 2025 vintage", "sector": "electricity"},
    "solar_res_RT1": {"name": "Rooftop solar potential 1", "description": "Rooftop solar potential step 1", "sector": "electricity"},
    "solar_res_RT2": {"name": "Rooftop solar potential 2", "description": "Rooftop solar potential step 2", "sector": "electricity"},
    "solar_res_RT3": {"name": "Rooftop solar potential 3", "description": "Rooftop solar potential step 3", "sector": "electricity"},
    "solar_res_RT4": {"name": "Rooftop solar potential 4", "description": "Rooftop solar potential step 4", "sector": "electricity"},
    "solar_res_RT5": {"name": "Rooftop solar potential 5", "description": "Rooftop solar potential step 5", "sector": "electricity"},
    "solar_res_RT6": {"name": "Rooftop solar potential 6", "description": "Rooftop solar potential step 6", "sector": "electricity"},
    "solar_res_RT7": {"name": "Rooftop solar potential 7", "description": "Rooftop solar potential step 7", "sector": "electricity"},
    "solar_res_RT8": {"name": "Rooftop solar potential 8", "description": "Rooftop solar potential step 8", "sector": "electricity"},

    # --- Wind ---
    "wind_ppl": {"name": "Wind onshore", "description": "Wind power plant onshore", "sector": "electricity"},
    "wind_ppf": {"name": "Wind offshore", "description": "Wind power plant offshore", "sector": "electricity"},
    "wind_curtailment1": {"name": "Wind curtailment 1", "description": "Wind curtailment step 1", "sector": "electricity"},
    "wind_curtailment2": {"name": "Wind curtailment 2", "description": "Wind curtailment step 2", "sector": "electricity"},
    "wind_curtailment3": {"name": "Wind curtailment 3", "description": "Wind curtailment step 3", "sector": "electricity"},
    "wind_cv1": {"name": "Wind flexibility 1", "description": "Wind flexibility requirement and firm capacity contribution step 1", "sector": "electricity"},
    "wind_cv2": {"name": "Wind flexibility 2", "description": "Wind flexibility requirement and firm capacity contribution step 2", "sector": "electricity"},
    "wind_cv3": {"name": "Wind flexibility 3", "description": "Wind flexibility requirement and firm capacity contribution step 3", "sector": "electricity"},
    "wind_cv4": {"name": "Wind flexibility 4", "description": "Wind flexibility requirement and firm capacity contribution step 4", "sector": "electricity"},
    "wind_res1": {"name": "Wind onshore potential 1", "description": "Wind onshore potential and generation step 1", "sector": "electricity"},
    "wind_res2": {"name": "Wind onshore potential 2", "description": "Wind onshore potential and generation step 2", "sector": "electricity"},
    "wind_res3": {"name": "Wind onshore potential 3", "description": "Wind onshore potential and generation step 3", "sector": "electricity"},
    "wind_res4": {"name": "Wind onshore potential 4", "description": "Wind onshore potential and generation step 4", "sector": "electricity"},
    "wind_res_hist_2000": {"name": "Wind onshore installed 2000", "description": "Installed wind onshore capacity with 2000 vintage", "sector": "electricity"},
    "wind_res_hist_2005": {"name": "Wind onshore installed 2005", "description": "Installed wind onshore capacity with 2005 vintage", "sector": "electricity"},
    "wind_res_hist_2010": {"name": "Wind onshore installed 2010", "description": "Installed wind onshore capacity with 2010 vintage", "sector": "electricity"},
    "wind_res_hist_2015": {"name": "Wind onshore installed 2015", "description": "Installed wind onshore capacity with 2015 vintage", "sector": "electricity"},
    "wind_res_hist_2020": {"name": "Wind onshore installed 2020", "description": "Installed wind onshore capacity with 2020 vintage", "sector": "electricity"},
    "wind_res_hist_2025": {"name": "Wind onshore installed 2025", "description": "Installed wind onshore capacity with 2025 vintage", "sector": "electricity"},
    "wind_ref1": {"name": "Wind offshore potential 1", "description": "Wind offshore potential and generation step 1", "sector": "electricity"},
    "wind_ref2": {"name": "Wind offshore potential 2", "description": "Wind offshore potential and generation step 2", "sector": "electricity"},
    "wind_ref3": {"name": "Wind offshore potential 3", "description": "Wind offshore potential and generation step 3", "sector": "electricity"},
    "wind_ref4": {"name": "Wind offshore potential 4", "description": "Wind offshore potential and generation step 4", "sector": "electricity"},
    "wind_ref5": {"name": "Wind offshore potential 5", "description": "Wind offshore potential and generation step 5", "sector": "electricity"},
    "wind_ref_hist_2000": {"name": "Wind offshore installed 2000", "description": "Installed wind offshore capacity with 2000 vintage", "sector": "electricity"},
    "wind_ref_hist_2005": {"name": "Wind offshore installed 2005", "description": "Installed wind offshore capacity with 2005 vintage", "sector": "electricity"},
    "wind_ref_hist_2010": {"name": "Wind offshore installed 2010", "description": "Installed wind offshore capacity with 2010 vintage", "sector": "electricity"},
    "wind_ref_hist_2015": {"name": "Wind offshore installed 2015", "description": "Installed wind offshore capacity with 2015 vintage", "sector": "electricity"},
    "wind_ref_hist_2020": {"name": "Wind offshore installed 2020", "description": "Installed wind offshore capacity with 2020 vintage", "sector": "electricity"},
    "wind_ref_hist_2025": {"name": "Wind offshore installed 2025", "description": "Installed wind offshore capacity with 2025 vintage", "sector": "electricity"},

    # --- Concentrating Solar Power (CSP) ---
    "csp_sm3_ppl": {"name": "CSP SM3", "description": "Concentrating solar power with solar multiple of 3", "sector": "electricity"},
    "csp_sm3_res": {"name": "CSP SM3 potential 0", "description": "CSP SM3 potential step 0", "sector": "electricity"},
    "csp_sm3_res1": {"name": "CSP SM3 potential 1", "description": "CSP SM3 potential step 1", "sector": "electricity"},
    "csp_sm3_res2": {"name": "CSP SM3 potential 2", "description": "CSP SM3 potential step 2", "sector": "electricity"},
    "csp_sm3_res3": {"name": "CSP SM3 potential 3", "description": "CSP SM3 potential step 3", "sector": "electricity"},
    "csp_sm3_res4": {"name": "CSP SM3 potential 4", "description": "CSP SM3 potential step 4", "sector": "electricity"},
    "csp_sm3_res5": {"name": "CSP SM3 potential 5", "description": "CSP SM3 potential step 5", "sector": "electricity"},
    "csp_sm3_res6": {"name": "CSP SM3 potential 6", "description": "CSP SM3 potential step 6", "sector": "electricity"},
    "csp_sm3_res7": {"name": "CSP SM3 potential 7", "description": "CSP SM3 potential step 7", "sector": "electricity"},
    "csp_sm1_ppl": {"name": "CSP SM1", "description": "Concentrating solar power with solar multiple of 1", "sector": "electricity"},
    "csp_sm1_res": {"name": "CSP SM1 potential 0", "description": "CSP SM1 potential step 0", "sector": "electricity"},
    "csp_sm1_res1": {"name": "CSP SM1 potential 1", "description": "CSP SM1 potential step 1", "sector": "electricity"},
    "csp_sm1_res2": {"name": "CSP SM1 potential 2", "description": "CSP SM1 potential step 2", "sector": "electricity"},
    "csp_sm1_res3": {"name": "CSP SM1 potential 3", "description": "CSP SM1 potential step 3", "sector": "electricity"},
    "csp_sm1_res4": {"name": "CSP SM1 potential 4", "description": "CSP SM1 potential step 4", "sector": "electricity"},
    "csp_sm1_res5": {"name": "CSP SM1 potential 5", "description": "CSP SM1 potential step 5", "sector": "electricity"},
    "csp_sm1_res6": {"name": "CSP SM1 potential 6", "description": "CSP SM1 potential step 6", "sector": "electricity"},
    "csp_sm1_res7": {"name": "CSP SM1 potential 7", "description": "CSP SM1 potential step 7", "sector": "electricity"},

    # ===== Extraction =====
    "bio_extr_1": {"name": "Biomass extraction 1", "description": "Biomass extraction grade 1", "sector": "extraction"},
    "bio_extr_2": {"name": "Biomass extraction 2", "description": "Biomass extraction grade 2", "sector": "extraction"},
    "bio_extr_3": {"name": "Biomass extraction 3", "description": "Biomass extraction grade 3", "sector": "extraction"},
    "bio_extr_4": {"name": "Biomass extraction 4", "description": "Biomass extraction grade 4", "sector": "extraction"},
    "bio_extr_5": {"name": "Biomass extraction 5", "description": "Biomass extraction grade 5", "sector": "extraction"},
    "bio_extr_6": {"name": "Biomass extraction 6", "description": "Biomass extraction grade 6", "sector": "extraction"},
    "bio_extr_mpen": {"name": "Biomass extraction penetration", "description": "Market penetration slack for biomass extraction", "sector": "extraction"},
    "coal_extr": {"name": "Coal extraction", "description": "Hard coal extraction, world average grade A", "sector": "extraction"},
    "coal_extr_ch4": {"name": "Coal extraction CH4", "description": "CH4-reduction efforts from coal mining", "sector": "extraction"},
    "lignite_extr": {"name": "Lignite extraction", "description": "Lignite extraction, world average grade A", "sector": "extraction"},
    "gas_extr_1": {"name": "Gas extraction Cat I", "description": "Natural gas extraction, Cat I – Identified Reserves", "sector": "extraction"},
    "gas_extr_2": {"name": "Gas extraction Cat II", "description": "Natural gas extraction, Cat II – Mode undiscovered", "sector": "extraction"},
    "gas_extr_3": {"name": "Gas extraction Cat III", "description": "Natural gas extraction, Cat III – Difference Mode/5%", "sector": "extraction"},
    "gas_extr_4": {"name": "Gas extraction Cat IV", "description": "Natural gas extraction, Cat IV – Estimated enhanced recovery", "sector": "extraction"},
    "gas_extr_5": {"name": "Gas extraction Cat V", "description": "Natural gas extraction, Cat V – Non-conventional reserves", "sector": "extraction"},
    "gas_extr_6": {"name": "Gas extraction Cat VI-VII", "description": "Natural gas extraction, Cat VI-VII – Non-conventional resources", "sector": "extraction"},
    "gas_extr_mpen": {"name": "Gas extraction penetration", "description": "Market penetration slack for gas extraction", "sector": "extraction"},
    "oil_extr_1": {"name": "Oil extraction Cat I", "description": "Crude oil extraction, Cat I – Conventional reserves", "sector": "extraction"},
    "oil_extr_1_ch4": {"name": "Oil extraction Cat I CH4", "description": "CH4-reduction from oil extraction Cat I", "sector": "extraction"},
    "oil_extr_2": {"name": "Oil extraction Cat II", "description": "Crude oil extraction, Cat II – Mode undiscovered conventional", "sector": "extraction"},
    "oil_extr_2_ch4": {"name": "Oil extraction Cat II CH4", "description": "CH4-reduction from oil extraction Cat II", "sector": "extraction"},
    "oil_extr_3": {"name": "Oil extraction Cat III", "description": "Crude oil extraction, Cat III – Masters 5%-50%", "sector": "extraction"},
    "oil_extr_3_ch4": {"name": "Oil extraction Cat III CH4", "description": "CH4-reduction from oil extraction Cat III", "sector": "extraction"},
    "oil_extr_4": {"name": "Oil extraction Cat IV", "description": "Crude oil extraction, Cat IV – Non-conventional reserves", "sector": "extraction"},
    "oil_extr_4_ch4": {"name": "Oil extraction Cat IV CH4", "description": "CH4-reduction from oil extraction Cat IV", "sector": "extraction"},
    "oil_extr_5": {"name": "Oil extraction Cat V", "description": "Crude oil extraction, Cat V – Non-conventional reserves", "sector": "extraction"},
    "oil_extr_6": {"name": "Oil extraction Cat VI", "description": "Crude oil extraction, Cat VI – 20% estimated occurrences", "sector": "extraction"},
    "oil_extr_mpen": {"name": "Oil extraction penetration", "description": "Market penetration slack for oil extraction", "sector": "extraction"},
    "Uran_extr": {"name": "Uranium extraction (FBR)", "description": "Uranium extraction, milling for FBR blanket", "sector": "extraction"},
    "uran2u5": {"name": "Uranium enrichment", "description": "Uranium extraction, milling, fluorination and enrichment per t U5", "sector": "extraction"},
    "flaring_CO2": {"name": "Gas flaring CO2", "description": "CO2 emissions from gas flaring", "sector": "extraction"},

    # ===== Feedstock =====
    "coal_fs": {"name": "Coal feedstock", "description": "Coal as industry feedstock", "sector": "feedstock"},
    "ethanol_fs": {"name": "Ethanol feedstock", "description": "Ethanol as industry feedstock", "sector": "feedstock"},
    "foil_fs": {"name": "Fuel oil feedstock", "description": "Fuel oil as industry feedstock", "sector": "feedstock"},
    "gas_fs": {"name": "Gas feedstock", "description": "Gas as industry feedstock", "sector": "feedstock"},
    "loil_fs": {"name": "Light oil feedstock", "description": "Light oil as industry feedstock", "sector": "feedstock"},
    "methanol_fs": {"name": "Methanol feedstock", "description": "Methanol as industry feedstock", "sector": "feedstock"},
    "Feeds_1": {"name": "Feedstock conservation 1", "description": "Conservation cost curve step 1 for industry feedstock", "sector": "feedstock"},
    "Feeds_2": {"name": "Feedstock conservation 2", "description": "Conservation cost curve step 2 for industry feedstock", "sector": "feedstock"},
    "Feeds_3": {"name": "Feedstock conservation 3", "description": "Conservation cost curve step 3 for industry feedstock", "sector": "feedstock"},
    "Feeds_4": {"name": "Feedstock conservation 4", "description": "Conservation cost curve step 4 for industry feedstock", "sector": "feedstock"},
    "Feeds_5": {"name": "Feedstock conservation 5", "description": "Conservation cost curve step 5 for industry feedstock", "sector": "feedstock"},
    "Feeds_con": {"name": "Feedstock conservation constraint", "description": "Joint diffusion constraint for feedstock conservation steps", "sector": "feedstock"},

    # ===== Gas processing =====
    "coal_gas": {"name": "Coal gasification", "description": "Hard coal gasification", "sector": "gas"},
    "g_ppl_co2scr": {"name": "Gas CO2 scrubber", "description": "CO2 scrubber for natural gas power plant", "sector": "gas"},
    "gas_bal": {"name": "Gas balance", "description": "Link technology to stabilize gas production", "sector": "gas"},
    "gas_bio": {"name": "Gas from biomass", "description": "Synthesis gas production from biomass", "sector": "gas"},
    "gas_imp": {"name": "Gas import (piped)", "description": "Piped gas imports", "sector": "gas"},
    "gas_rc": {"name": "Gas heating (R/C)", "description": "Gas heating in residential/commercial sector", "sector": "gas"},
    "gas_t_d": {"name": "Gas T&D", "description": "Transmission/Distribution of gas", "sector": "gas"},
    "gas_t_d_ch4": {"name": "Gas T&D (CH4 mitigation)", "description": "Transmission/Distribution of gas with CH4 mitigation", "sector": "gas"},
    "gfc_co2scr": {"name": "Gas FC CO2 scrubber", "description": "CO2 scrubber for gas fuel cells (CCS)", "sector": "gas"},
    "glb_gas_exp": {"name": "Global gas export", "description": "Global net export of gas", "sector": "gas"},
    "glb_LNG_exp": {"name": "Global LNG export", "description": "Global net export of liquified natural gas", "sector": "gas"},
    "h2_mix": {"name": "H2 gas blending", "description": "Hydrogen injection into the natural gas system", "sector": "gas"},
    "LNG_bal": {"name": "LNG balance", "description": "Link technology to stabilize LNG production", "sector": "gas"},
    "LNG_imp": {"name": "LNG import", "description": "LNG imports", "sector": "gas"},
    "LNG_regas": {"name": "LNG regasification", "description": "LNG regasification (link; losses in trade)", "sector": "gas"},

    # ===== Heat =====
    "bio_hpl": {"name": "Biomass heating plant", "description": "Biomass heating plant", "sector": "heat"},
    "coal_hpl": {"name": "Coal heating plant", "description": "Coal heating plant", "sector": "heat"},
    "foil_hpl": {"name": "Fuel oil heating plant", "description": "Fuel oil heating plant", "sector": "heat"},
    "gas_hpl": {"name": "Gas heating plant", "description": "Natural gas heating plant", "sector": "heat"},
    "geo_hpl": {"name": "Geothermal heat plant", "description": "Geothermal heat plant", "sector": "heat"},
    "heat_t/d": {"name": "Heat T&D", "description": "Transmission/Distribution of district heat", "sector": "heat"},
    "po_turbine": {"name": "Pass-out turbine", "description": "Pass out turbine", "sector": "heat"},

    # ===== Hydrogen =====
    "glb_lh2_imp": {"name": "Global LH2 import", "description": "Global net import of liquid hydrogen", "sector": "hydrogen"},
    "h2_bio": {"name": "H2 from biomass", "description": "Hydrogen production from biomass via gasification", "sector": "hydrogen"},
    "h2_bio_ccs": {"name": "H2 from biomass CCS", "description": "Hydrogen from biomass with carbon capture and storage", "sector": "hydrogen"},
    "h2_co2_scrub": {"name": "H2 CO2 scrubber", "description": "CO2 scrubber for H2 production from coal and gas", "sector": "hydrogen"},
    "h2_coal": {"name": "H2 from coal", "description": "Hydrogen production via coal gasification", "sector": "hydrogen"},
    "h2_coal_ccs": {"name": "H2 from coal CCS", "description": "Hydrogen via coal gasification with CCS", "sector": "hydrogen"},
    "h2_elec": {"name": "H2 electrolysis", "description": "Hydrogen production via electrolysis", "sector": "hydrogen"},
    "h2_liq": {"name": "H2 liquefaction", "description": "Hydrogen liquefaction", "sector": "hydrogen"},
    "h2_smr": {"name": "H2 SMR", "description": "Hydrogen production via steam-methane reforming of natural gas", "sector": "hydrogen"},
    "h2_smr_ccs": {"name": "H2 SMR CCS", "description": "Hydrogen via SMR with carbon capture and storage", "sector": "hydrogen"},
    "h2_t/d": {"name": "H2 T&D (gas)", "description": "Transmission/Distribution of gaseous hydrogen", "sector": "hydrogen"},
    "h2b_co2_scrub": {"name": "H2 bio CO2 scrubber", "description": "CO2 scrubber for H2 production from biomass", "sector": "hydrogen"},
    "lh2_bal": {"name": "LH2 balance", "description": "Link technology to stabilize liquid hydrogen production", "sector": "hydrogen"},
    "lh2_exp": {"name": "LH2 export", "description": "Exports of liquid hydrogen", "sector": "hydrogen"},
    "lh2_imp": {"name": "LH2 import", "description": "Imports of liquid hydrogen", "sector": "hydrogen"},
    "lh2_regas": {"name": "LH2 regasification", "description": "Regasification of liquid hydrogen", "sector": "hydrogen"},
    "lh2_t/d": {"name": "LH2 T&D", "description": "Transmission/Distribution of liquid hydrogen", "sector": "hydrogen"},

    # ===== Industry =====
    "back_bio_ind": {"name": "Backstop bio industry", "description": "Backstop for diagnosing model infeasibility", "sector": "industry"},
    "back_fs": {"name": "Backstop feedstock", "description": "Backstop for diagnosing model infeasibility", "sector": "industry"},
    "back_I": {"name": "Backstop industry", "description": "Backstop for diagnosing model infeasibility", "sector": "industry"},
    "cement_CO2": {"name": "Cement CO2", "description": "CO2 emissions from cement production", "sector": "industry"},
    "cement_co2scr": {"name": "Cement CO2 scrubber", "description": "Cement CO2 scrubber (CCS)", "sector": "industry"},
    "coal_i": {"name": "Coal industry thermal", "description": "Coal in industry thermal", "sector": "industry"},
    "elec_i": {"name": "Electricity industry", "description": "Electricity in industry thermal", "sector": "industry"},
    "eth_i": {"name": "Ethanol industry", "description": "Ethanol for liquid fuel in industry thermal", "sector": "industry"},
    "foil_i": {"name": "Fuel oil industry", "description": "Fuel oil for thermal uses in industry", "sector": "industry"},
    "gas_i": {"name": "Gas industry", "description": "Gas for thermal uses in industry", "sector": "industry"},
    "h2_i": {"name": "H2 industry", "description": "Gaseous hydrogen in industry thermal", "sector": "industry"},
    "heat_i": {"name": "Heat industry", "description": "District heating for thermal uses in industry", "sector": "industry"},
    "hp_el_i": {"name": "Electric HP industry", "description": "Electric heat pump in industry thermal", "sector": "industry"},
    "hp_gas_i": {"name": "Gas HP industry", "description": "Natural gas heat pump in industry thermal", "sector": "industry"},
    "loil_i": {"name": "Light oil industry", "description": "Light oil for thermal uses in industry", "sector": "industry"},
    "meth_i": {"name": "Methanol industry", "description": "Methanol for liquid fuel in industry thermal", "sector": "industry"},
    "solar_i": {"name": "Solar thermal industry", "description": "Solar thermal in industry thermal sector", "sector": "industry"},
    "biomass_i": {"name": "Biomass industry", "description": "Biomass in industry thermal", "sector": "industry"},
    "Ispec_1": {"name": "Industry specific conservation 1", "description": "Conservation cost curve step 1 for industry specific demand", "sector": "industry"},
    "Ispec_2": {"name": "Industry specific conservation 2", "description": "Conservation cost curve step 2 for industry specific demand", "sector": "industry"},
    "Ispec_3": {"name": "Industry specific conservation 3", "description": "Conservation cost curve step 3 for industry specific demand", "sector": "industry"},
    "Ispec_4": {"name": "Industry specific conservation 4", "description": "Conservation cost curve step 4 for industry specific demand", "sector": "industry"},
    "Ispec_5": {"name": "Industry specific conservation 5", "description": "Conservation cost curve step 5 for industry specific demand", "sector": "industry"},
    "Ispec_con": {"name": "Industry specific conservation constraint", "description": "Joint diffusion constraint for industry specific conservation", "sector": "industry"},
    "Itherm_1": {"name": "Industry thermal conservation 1", "description": "Conservation cost curve step 1 for industry thermal demand", "sector": "industry"},
    "Itherm_2": {"name": "Industry thermal conservation 2", "description": "Conservation cost curve step 2 for industry thermal demand", "sector": "industry"},
    "Itherm_3": {"name": "Industry thermal conservation 3", "description": "Conservation cost curve step 3 for industry thermal demand", "sector": "industry"},
    "Itherm_4": {"name": "Industry thermal conservation 4", "description": "Conservation cost curve step 4 for industry thermal demand", "sector": "industry"},
    "Itherm_5": {"name": "Industry thermal conservation 5", "description": "Conservation cost curve step 5 for industry thermal demand", "sector": "industry"},
    "Itherm_con": {"name": "Industry thermal conservation constraint", "description": "Joint diffusion constraint for industry thermal conservation", "sector": "industry"},
    "solar_pv_I": {"name": "Solar PV industry", "description": "On-site solar PV in industry specific", "sector": "industry"},
    "h2_fc_I": {"name": "H2 fuel cell industry", "description": "Hydrogen fuel cell cogeneration for industry specific", "sector": "industry"},
    "sp_coal_I": {"name": "Coal specific industry", "description": "Specific use of coal in industry", "sector": "industry"},
    "sp_el_I": {"name": "Electricity specific industry", "description": "Specific use of electricity in industry", "sector": "industry"},
    "sp_eth_I": {"name": "Ethanol specific industry", "description": "Ethanol replacement for specific light oil use in industry", "sector": "industry"},
    "sp_liq_I": {"name": "Light oil specific industry", "description": "Specific use of light oil in industry", "sector": "industry"},
    "sp_meth_I": {"name": "Methanol specific industry", "description": "Methanol replacement for specific light oil use in industry", "sector": "industry"},

    # ===== Land use =====
    "bio_extr_chp": {"name": "Biomass supply (no C)", "description": "Supply of biomass without net C emissions", "sector": "land"},
    "forest_CO2": {"name": "Forest CO2", "description": "CO2 emissions from forests", "sector": "land"},
    "sinks_1": {"name": "Carbon sink 50$/t", "description": "Potential for sinks at 50 US$/t", "sector": "land"},
    "sinks_2": {"name": "Carbon sink 100$/t", "description": "Potential for sinks at 100 US$/t", "sector": "land"},
    "sinks_3": {"name": "Carbon sink 200$/t", "description": "Potential for sinks at 200 US$/t", "sector": "land"},
    "sinks_4": {"name": "Carbon sink 300$/t", "description": "Potential for sinks at 300 US$/t", "sector": "land"},

    # ===== Liquids =====
    "eth_bal": {"name": "Ethanol balance", "description": "Link technology to stabilize ethanol production", "sector": "liquids"},
    "eth_bio": {"name": "Ethanol from biomass", "description": "Ethanol synthesis via biomass gasification", "sector": "liquids"},
    "eth_bio_ccs": {"name": "Ethanol from biomass CCS", "description": "Ethanol via biomass gasification with CCS", "sector": "liquids"},
    "eth_exp": {"name": "Ethanol export", "description": "Exports of ethanol", "sector": "liquids"},
    "eth_imp": {"name": "Ethanol import", "description": "Imports of ethanol", "sector": "liquids"},
    "eth_t/d": {"name": "Ethanol T&D", "description": "Transmission/Distribution of ethanol", "sector": "liquids"},
    "foil_exp": {"name": "Fuel oil export", "description": "Net exports of fuel oil", "sector": "liquids"},
    "foil_imp": {"name": "Fuel oil import", "description": "Net imports of residual oil", "sector": "liquids"},
    "foil_t/d": {"name": "Fuel oil T&D", "description": "Transmission/Distribution of fuel oil", "sector": "liquids"},
    "glb_eth_imp": {"name": "Global ethanol import", "description": "Global net import of ethanol", "sector": "liquids"},
    "glb_foil_exp": {"name": "Global fuel oil export", "description": "Global net export of fuel oil", "sector": "liquids"},
    "glb_foil_imp": {"name": "Global fuel oil import", "description": "Global net import of fuel oil", "sector": "liquids"},
    "glb_loil_exp": {"name": "Global light oil export", "description": "Global net export of light oil", "sector": "liquids"},
    "glb_loil_imp": {"name": "Global light oil import", "description": "Global net import of light oil", "sector": "liquids"},
    "glb_meth_imp": {"name": "Global methanol import", "description": "Global net import of methanol", "sector": "liquids"},
    "glb_oil_exp": {"name": "Global crude oil export", "description": "Global net export of crude oil", "sector": "liquids"},
    "glb_oil_imp": {"name": "Global crude oil import", "description": "Global net import of crude oil", "sector": "liquids"},
    "liq_bio": {"name": "Bio FTL", "description": "Second Generation Ethanol based on Biomass to FTL", "sector": "liquids"},
    "liq_bio_ccs": {"name": "Bio FTL CCS", "description": "Second Generation Ethanol with CCS based on Biomass to FTL", "sector": "liquids"},
    "loil_exp": {"name": "Light oil export", "description": "Net exports of light oil", "sector": "liquids"},
    "loil_imp": {"name": "Light oil import", "description": "Net imports of light oil", "sector": "liquids"},
    "loil_std": {"name": "Light oil standard plant", "description": "Standard light oil power-plant", "sector": "liquids"},
    "loil_t/d": {"name": "Light oil T&D", "description": "Transmission/Distribution of light oil", "sector": "liquids"},
    "meth_coal": {"name": "Methanol from coal", "description": "Methanol synthesis via coal gasification", "sector": "liquids"},
    "meth_coal_ccs": {"name": "Methanol from coal CCS", "description": "Methanol via coal gasification with CCS", "sector": "liquids"},
    "meth_exp": {"name": "Methanol export", "description": "Exports of methanol", "sector": "liquids"},
    "meth_imp": {"name": "Methanol import", "description": "Imports of methanol", "sector": "liquids"},
    "meth_ng": {"name": "Methanol from gas", "description": "Methanol synthesis via natural gas", "sector": "liquids"},
    "meth_ng_ccs": {"name": "Methanol from gas CCS", "description": "Methanol via natural gas with CCS", "sector": "liquids"},
    "meth_t/d": {"name": "Methanol T&D", "description": "Transmission/Distribution of methanol", "sector": "liquids"},
    "meth_bal": {"name": "Methanol balance", "description": "Link technology to stabilize methanol production", "sector": "liquids"},
    "oil_bal": {"name": "Oil balance", "description": "Link technology to stabilize crude oil production", "sector": "liquids"},
    "oil_exp": {"name": "Oil export", "description": "Net exports of crude oil", "sector": "liquids"},
    "oil_imp": {"name": "Oil import", "description": "Net imports of oil", "sector": "liquids"},
    "ref_hil": {"name": "Refinery (high yield)", "description": "New deeply upgraded refineries", "sector": "liquids"},
    "ref_lol": {"name": "Refinery (low yield)", "description": "Existing refineries (low yield)", "sector": "liquids"},
    "SO2_scrub_ref": {"name": "SO2 scrubber refinery", "description": "SO2 scrubber for refineries", "sector": "liquids"},
    "syn_liq": {"name": "Coal liquefaction", "description": "Coal liquefaction and light oil synthesis", "sector": "liquids"},
    "syn_liq_ccs": {"name": "Coal liquefaction CCS", "description": "Coal liquefaction and light oil synthesis with CCS", "sector": "liquids"},
    "plutonium_prod": {"name": "Plutonium production", "description": "Plutonium production", "sector": "nuclear"},

    # ===== Non-CO2 emissions mitigation =====
    "CF4_TCE": {"name": "CF4 TCE", "description": "Tetrafluoromethane total carbon equivalent emissions", "sector": "non-CO2"},
    "CH4_TCE": {"name": "CH4 TCE", "description": "Methane total carbon equivalent emissions", "sector": "non-CO2"},
    "CH4g_TCE": {"name": "CH4 animal TCE", "description": "CH4 emissions from animals in total carbon equivalent", "sector": "non-CO2"},
    "CH4n_TCE": {"name": "CH4 waste TCE", "description": "CH4 emissions from anaerobic waste decomposition in TCE", "sector": "non-CO2"},
    "CH4o_TCE": {"name": "CH4 wastewater TCE", "description": "CH4 from industrial/domestic wastewater in TCE", "sector": "non-CO2"},
    "CO2_TCE": {"name": "CO2 TCE", "description": "CO2 total carbon equivalent emissions", "sector": "non-CO2"},
    "HFC_TCE": {"name": "HFC TCE", "description": "HFC total carbon equivalent emissions", "sector": "non-CO2"},
    "HFCo_TCE": {"name": "HFC solvents TCE", "description": "HFC equiv emissions from solvents and aerosols in TCE", "sector": "non-CO2"},
    "N2O_TCE": {"name": "N2O TCE", "description": "N2O total carbon equivalent emissions", "sector": "non-CO2"},
    "N2OG_TCE": {"name": "N2O soil TCE", "description": "N2O soil emissions total carbon equivalent", "sector": "non-CO2"},
    "N2On_TCE": {"name": "N2O adipic TCE", "description": "N2O adipic acid total carbon equivalent", "sector": "non-CO2"},
    "N2Oo_TCE": {"name": "N2O manure TCE", "description": "N2O from manure and sewage in TCE", "sector": "non-CO2"},
    "SF6_TCE": {"name": "SF6 TCE", "description": "SF6 total carbon equivalent emissions", "sector": "non-CO2"},
    "adipic_thermal": {"name": "Adipic thermal destruction", "description": "Thermal destruction for adipic acid sector", "sector": "non-CO2"},
    "ammonia_secloop": {"name": "Ammonia secondary loop", "description": "Ammonia secondary loop systems", "sector": "non-CO2"},
    "enre_con": {"name": "Enteric fermentation constraint", "description": "Joint diffusion constraint for enteric fermentation mitigation", "sector": "non-CO2"},
    "ent_red1": {"name": "Enteric mitigation 1", "description": "Mitigation for CH4 from animals step 1", "sector": "non-CO2"},
    "ent_red2": {"name": "Enteric mitigation 2", "description": "Mitigation for CH4 from animals step 2", "sector": "non-CO2"},
    "ent_red3": {"name": "Enteric mitigation 3", "description": "Mitigation for CH4 from animals step 3", "sector": "non-CO2"},
    "landfill_compost1": {"name": "Landfill composting 1", "description": "Landfill mitigation via composting step 1", "sector": "non-CO2"},
    "landfill_compost2": {"name": "Landfill composting 2", "description": "Landfill mitigation via composting step 2", "sector": "non-CO2"},
    "landfill_direct1": {"name": "Landfill direct 1", "description": "Landfill direct CH4 mitigation step 1", "sector": "non-CO2"},
    "landfill_direct2": {"name": "Landfill direct 2", "description": "Landfill direct CH4 mitigation step 2", "sector": "non-CO2"},
    "landfill_ele": {"name": "Landfill electricity", "description": "Landfill CH4 mitigation via electricity generation", "sector": "non-CO2"},
    "landfill_flaring": {"name": "Landfill flaring", "description": "Landfill CH4 mitigation via flaring", "sector": "non-CO2"},
    "landfill_heatprdn": {"name": "Landfill heat", "description": "Landfill CH4 mitigation via heat production", "sector": "non-CO2"},
    "landfill_oxdn": {"name": "Landfill oxidation", "description": "Landfill CH4 mitigation via oxidation", "sector": "non-CO2"},
    "leak_repair": {"name": "HFC leak repair", "description": "Leak-repairs for HFC-134a from refrigeration & AC", "sector": "non-CO2"},
    "leak_repairsf6": {"name": "SF6 leak repair", "description": "Recycling gas carts for SF6 recovery during assembly", "sector": "non-CO2"},
    "lfil_con": {"name": "Landfill constraint", "description": "Joint diffusion constraint for landfill mitigation", "sector": "non-CO2"},
    "manu_con": {"name": "Manure constraint", "description": "Joint diffusion constraint for manure management mitigation", "sector": "non-CO2"},
    "mvac_co2": {"name": "Mobile AC CO2", "description": "Transcritical CO2 systems for mobile vehicle air conditioners", "sector": "non-CO2"},
    "nica_con": {"name": "Nitric acid constraint", "description": "Joint diffusion constraint for nitric acid mitigation", "sector": "non-CO2"},
    "nitric_catalytic1": {"name": "Nitric catalytic 1", "description": "Catalytic converter for N2O emissions step 1", "sector": "non-CO2"},
    "nitric_catalytic2": {"name": "Nitric catalytic 2", "description": "Catalytic converter for N2O emissions step 2", "sector": "non-CO2"},
    "nitric_catalytic3": {"name": "Nitric catalytic 3", "description": "Catalytic converter for N2O emissions step 3", "sector": "non-CO2"},
    "nitric_catalytic4": {"name": "Nitric catalytic 4", "description": "Catalytic converter for N2O emissions step 4", "sector": "non-CO2"},
    "nitric_catalytic5": {"name": "Nitric catalytic 5", "description": "Catalytic converter for N2O emissions step 5", "sector": "non-CO2"},
    "nitric_catalytic6": {"name": "Nitric catalytic 6", "description": "Catalytic converter for N2O emissions step 6", "sector": "non-CO2"},
    "nitric_catalytic7": {"name": "Nitric catalytic 7", "description": "Catalytic converter for N2O emissions step 7", "sector": "non-CO2"},
    "recycling_gas1": {"name": "SF6 recycling", "description": "Recycling gas carts for SF6 recovery during maintenance", "sector": "non-CO2"},
    "refrigerant_recover": {"name": "Refrigerant recovery", "description": "Recovery of HFC-134a from refrigeration and AC", "sector": "non-CO2"},
    "repl_hc": {"name": "HC replacement foams", "description": "Replacement with HC for foams", "sector": "non-CO2"},
    "replacement_so2": {"name": "SF6 replacement SO2", "description": "Replacing SF6 by SO2", "sector": "non-CO2"},
    "rice_red1": {"name": "Rice CH4 mitigation 1", "description": "Mitigation for CH4 from rice step 1", "sector": "non-CO2"},
    "rice_red2": {"name": "Rice CH4 mitigation 2", "description": "Mitigation for CH4 from rice step 2", "sector": "non-CO2"},
    "rice_red3": {"name": "Rice CH4 mitigation 3", "description": "Mitigation for CH4 from rice step 3", "sector": "non-CO2"},
    "rire_con": {"name": "Rice mitigation constraint", "description": "Joint diffusion constraint for rice cultivation mitigation", "sector": "non-CO2"},
    "soil_red1": {"name": "Soil N2O mitigation 1", "description": "Mitigation for N2O from soil step 1", "sector": "non-CO2"},
    "soil_red2": {"name": "Soil N2O mitigation 2", "description": "Mitigation for N2O from soil step 2", "sector": "non-CO2"},
    "soil_red3": {"name": "Soil N2O mitigation 3", "description": "Mitigation for N2O from soil step 3", "sector": "non-CO2"},
    "vertical_stud": {"name": "Aluminum CF4 mitigation", "description": "Soderberg process for CF4 from aluminum", "sector": "non-CO2"},

    # ===== Nuclear =====
    "u5-reproc": {"name": "Uranium reprocessing", "description": "Uranium reprocessing", "sector": "nuclear"},

    # ===== CCS transport & disposal =====
    "bco2_tr_dis": {"name": "Bio CO2 transport/disposal", "description": "CO2 transportation and disposal from biomass", "sector": "ccs"},
    "co2_tr_dis": {"name": "CO2 transport/disposal", "description": "CO2 transportation and disposal", "sector": "ccs"},
    "dac_lt": {"name": "DAC low-temp", "description": "Direct air capture (low temperature)", "sector": "ccs"},
    "dac_hte": {"name": "DAC high-temp electric", "description": "Direct air capture (high temperature electric)", "sector": "ccs"},
    "dac_htg": {"name": "DAC high-temp gas", "description": "Direct air capture (high temperature gas)", "sector": "ccs"},

    # ===== Residential / Commercial =====
    "back_rc": {"name": "Backstop R/C", "description": "Backstop for diagnosing model infeasibility", "sector": "residential_commercial"},
    "solar_rc": {"name": "Solar thermal R/C", "description": "Solar thermal in residential/commercial sector", "sector": "residential_commercial"},
    "biomass_rc": {"name": "Biomass R/C", "description": "Biomass heating in residential/commercial sector", "sector": "residential_commercial"},
    "coal_rc": {"name": "Coal R/C", "description": "Coal heating in residential/commercial sector", "sector": "residential_commercial"},
    "elec_rc": {"name": "Electricity R/C", "description": "Electricity heating in residential/commercial sector", "sector": "residential_commercial"},
    "eth_rc": {"name": "Ethanol R/C", "description": "Ethanol in residential/commercial sector", "sector": "residential_commercial"},
    "foil_rc": {"name": "Fuel oil R/C", "description": "Fuel oil heating in residential/commercial sector", "sector": "residential_commercial"},
    "h2_rc": {"name": "H2 R/C", "description": "Hydrogen catalytic heating in residential/commercial", "sector": "residential_commercial"},
    "heat_rc": {"name": "District heat R/C", "description": "District heating in residential/commercial sector", "sector": "residential_commercial"},
    "hp_el_rc": {"name": "Electric HP R/C", "description": "Electric heat pump in residential/commercial sector", "sector": "residential_commercial"},
    "hp_gas_rc": {"name": "Gas HP R/C", "description": "Natural gas heat pump in residential/commercial sector", "sector": "residential_commercial"},
    "loil_rc": {"name": "Light oil R/C", "description": "Light oil heating in residential/commercial sector", "sector": "residential_commercial"},
    "meth_rc": {"name": "Methanol R/C", "description": "Methanol in residential/commercial sector", "sector": "residential_commercial"},
    "RCspec_1": {"name": "R/C specific conservation 1", "description": "Conservation cost curve step 1 for R/C specific demand", "sector": "residential_commercial"},
    "RCspec_2": {"name": "R/C specific conservation 2", "description": "Conservation cost curve step 2 for R/C specific demand", "sector": "residential_commercial"},
    "RCspec_3": {"name": "R/C specific conservation 3", "description": "Conservation cost curve step 3 for R/C specific demand", "sector": "residential_commercial"},
    "RCspec_4": {"name": "R/C specific conservation 4", "description": "Conservation cost curve step 4 for R/C specific demand", "sector": "residential_commercial"},
    "RCspec_5": {"name": "R/C specific conservation 5", "description": "Conservation cost curve step 5 for R/C specific demand", "sector": "residential_commercial"},
    "RCspec_con": {"name": "R/C specific conservation constraint", "description": "Joint diffusion constraint for R/C specific conservation", "sector": "residential_commercial"},
    "RCtherm_1": {"name": "R/C thermal conservation 1", "description": "Conservation cost curve step 1 for R/C thermal demand", "sector": "residential_commercial"},
    "RCtherm_2": {"name": "R/C thermal conservation 2", "description": "Conservation cost curve step 2 for R/C thermal demand", "sector": "residential_commercial"},
    "RCtherm_3": {"name": "R/C thermal conservation 3", "description": "Conservation cost curve step 3 for R/C thermal demand", "sector": "residential_commercial"},
    "RCtherm_4": {"name": "R/C thermal conservation 4", "description": "Conservation cost curve step 4 for R/C thermal demand", "sector": "residential_commercial"},
    "RCtherm_5": {"name": "R/C thermal conservation 5", "description": "Conservation cost curve step 5 for R/C thermal demand", "sector": "residential_commercial"},
    "RCtherm_con": {"name": "R/C thermal conservation constraint", "description": "Joint diffusion constraint for R/C thermal conservation", "sector": "residential_commercial"},
    "solar_pv_RC": {"name": "Solar PV R/C", "description": "On-site solar PV in residential/commercial", "sector": "residential_commercial"},
    "sp_el_RC": {"name": "Electricity specific R/C", "description": "Specific use of electricity in residential/commercial", "sector": "residential_commercial"},
    "h2_fc_RC": {"name": "H2 fuel cell R/C", "description": "Hydrogen fuel cell cogeneration in residential/commercial", "sector": "residential_commercial"},
    "biomass_nc": {"name": "Non-commercial biomass", "description": "Non-commercial biomass", "sector": "residential_commercial"},

    # ===== Solids (coal/biomass T&D) =====
    "bio_ppl_co2scr": {"name": "Bio CO2 scrubber", "description": "CO2 scrubber for biomass power plants", "sector": "solids"},
    "biomass_t/d": {"name": "Biomass T&D", "description": "Transmission/Distribution of biomass", "sector": "solids"},
    "c_ppl_co2scr": {"name": "Coal CO2 scrubber", "description": "CO2 scrubber for coal power plants", "sector": "solids"},
    "cfc_co2scr": {"name": "Coal FC CO2 scrubber", "description": "CO2 scrubber for coal fuel cells (CCS)", "sector": "solids"},
    "coal_bal": {"name": "Coal balance", "description": "Link technology to stabilize coal production", "sector": "solids"},
    "coal_exp": {"name": "Coal export", "description": "Net exports of coal", "sector": "solids"},
    "coal_imp": {"name": "Coal import", "description": "Net imports of coal", "sector": "solids"},
    "coal_t/d": {"name": "Coal T&D", "description": "Transmission/Distribution of coal", "sector": "solids"},
    "coal_t/d-in-06%": {"name": "Coal T&D industry 0.6%S", "description": "Coal T&D for industry imported coal 0.6% S", "sector": "solids"},
    "coal_t/d-in-SO2": {"name": "Coal T&D industry SO2", "description": "Coal T&D for industry processed coal", "sector": "solids"},
    "coal_t/d-rc-06%": {"name": "Coal T&D R/C 0.6%S", "description": "Coal T&D for R/C imported coal 0.6% S", "sector": "solids"},
    "coal_t/d-rc-SO2": {"name": "Coal T&D R/C SO2", "description": "Coal T&D for R/C processed coal", "sector": "solids"},
    "glb_coal_exp": {"name": "Global coal export", "description": "Global net export of coal", "sector": "solids"},
    "glb_coal_imp": {"name": "Global coal import", "description": "Global net import of coal", "sector": "solids"},

    # ===== Transport =====
    "back_trp": {"name": "Backstop transport", "description": "Backstop for diagnosing model infeasibility", "sector": "transport"},
    "coal_trp": {"name": "Coal transport", "description": "Coal-based transport", "sector": "transport"},
    "elec_trp": {"name": "Electric transport", "description": "Electricity-based transport", "sector": "transport"},
    "eth_fc_trp": {"name": "Ethanol FC transport", "description": "Ethanol fuel cell-based transport", "sector": "transport"},
    "eth_ic_trp": {"name": "Ethanol IC transport", "description": "Ethanol IC-engine-based transport", "sector": "transport"},
    "foil_trp": {"name": "Fuel oil transport", "description": "Fuel oil-based transport", "sector": "transport"},
    "gas_trp": {"name": "Gas transport", "description": "Gas-based transport", "sector": "transport"},
    "h2_fc_trp": {"name": "H2 FC transport", "description": "Hydrogen fuel cell-based transport", "sector": "transport"},
    "loil_trp": {"name": "Light oil transport", "description": "Light oil-based transport", "sector": "transport"},
    "meth_fc_trp": {"name": "Methanol FC transport", "description": "Methanol fuel cell-based transport", "sector": "transport"},
    "meth_ic_trp": {"name": "Methanol IC transport", "description": "Methanol IC-engine-based transport", "sector": "transport"},
    "Trans_1": {"name": "Transport conservation 1", "description": "Conservation cost curve step 1 for transport demand", "sector": "transport"},
    "Trans_2": {"name": "Transport conservation 2", "description": "Conservation cost curve step 2 for transport demand", "sector": "transport"},
    "Trans_3": {"name": "Transport conservation 3", "description": "Conservation cost curve step 3 for transport demand", "sector": "transport"},
    "Trans_4": {"name": "Transport conservation 4", "description": "Conservation cost curve step 4 for transport demand", "sector": "transport"},
    "Trans_5": {"name": "Transport conservation 5", "description": "Conservation cost curve step 5 for transport demand", "sector": "transport"},
    "Trans_con": {"name": "Transport conservation constraint", "description": "Joint diffusion constraint for transport conservation", "sector": "transport"},

    # ===== Shipping / Bunkers =====
    "foil_bunker": {"name": "Fuel oil bunker", "description": "Fuel oil demand for international shipping bunkers", "sector": "shipping"},
    "loil_bunker": {"name": "Light oil bunker", "description": "Light oil demand for international shipping bunkers", "sector": "shipping"},
    "meth_bunker": {"name": "Methanol bunker", "description": "Methanol demand for international shipping bunkers", "sector": "shipping"},
    "eth_bunker": {"name": "Ethanol bunker", "description": "Ethanol demand for international shipping bunkers", "sector": "shipping"},
    "LNG_bunker": {"name": "LNG bunker", "description": "LNG demand for international shipping bunkers", "sector": "shipping"},
    "LH2_bunker": {"name": "LH2 bunker", "description": "Liquid hydrogen demand for international shipping bunkers", "sector": "shipping"},
    "LH2_tobunker": {"name": "LH2 to bunker", "description": "Liquid hydrogen to international shipping bunkers", "sector": "shipping"},
    "LNG_occ_bunker": {"name": "LNG occasional bunker", "description": "LNG occasional shipping bunker", "sector": "shipping"},
    "LNG_tobunker": {"name": "LNG to bunker", "description": "LNG to international shipping bunkers", "sector": "shipping"},
    "NH3_tobunker": {"name": "NH3 to bunker", "description": "Ammonia to international shipping bunkers", "sector": "shipping"},
    "eth_tobunker": {"name": "Ethanol to bunker", "description": "Ethanol to international shipping bunkers", "sector": "shipping"},
    "foil_occ_bunker": {"name": "Fuel oil occasional bunker", "description": "Fuel oil occasional shipping bunker", "sector": "shipping"},
    "loil_occ_bunker": {"name": "Light oil occasional bunker", "description": "Light oil occasional shipping bunker", "sector": "shipping"},
    "loil_tobunker": {"name": "Light oil to bunker", "description": "Light oil to international shipping bunkers", "sector": "shipping"},
    "meth_tobunker": {"name": "Methanol to bunker", "description": "Methanol to international shipping bunkers", "sector": "shipping"},

    # ===== Share constraints & system =====
    "useful_feedstock": {"name": "Feedstock share constraint", "description": "Share constraint for industry feedstocks", "sector": "system"},
    "useful_industry_sp": {"name": "Industry specific share", "description": "Share constraint for Industry Specific", "sector": "system"},
    "useful_industry_th": {"name": "Industry thermal share", "description": "Share constraint for Industry Thermal", "sector": "system"},
    "useful_res/comm_sp": {"name": "R/C specific share", "description": "Share constraint for Residential and Commercial Specific", "sector": "system"},
    "useful_res/comm_th": {"name": "R/C thermal share", "description": "Share constraint for Residential and Commercial Thermal", "sector": "system"},
    "useful_transport": {"name": "Transport share", "description": "Share constraint for Transport", "sector": "system"},
    "dom_total": {"name": "Domestic total", "description": "Balance equation for domestic energy supply and net imports", "sector": "system"},
    "dummy_producer": {"name": "Dummy producer", "description": "Dummy technology to avoid infeasibility", "sector": "system"},
    "exp_total": {"name": "Export total", "description": "Balance equation for exported energy supply", "sector": "system"},
    "imp_total": {"name": "Import total", "description": "Balance equation for imported energy supply", "sector": "system"},
}

TECHNOLOGY_CATEGORIES = {
    "Electricity": [k for k, v in MESSAGE_IX_TECHNOLOGIES.items() if v.get("sector") == "electricity"],
    "Extraction": [k for k, v in MESSAGE_IX_TECHNOLOGIES.items() if v.get("sector") == "extraction"],
    "Feedstock": [k for k, v in MESSAGE_IX_TECHNOLOGIES.items() if v.get("sector") == "feedstock"],
    "Gas": [k for k, v in MESSAGE_IX_TECHNOLOGIES.items() if v.get("sector") == "gas"],
    "Heat": [k for k, v in MESSAGE_IX_TECHNOLOGIES.items() if v.get("sector") == "heat"],
    "Hydrogen": [k for k, v in MESSAGE_IX_TECHNOLOGIES.items() if v.get("sector") == "hydrogen"],
    "Industry": [k for k, v in MESSAGE_IX_TECHNOLOGIES.items() if v.get("sector") == "industry"],
    "Land Use": [k for k, v in MESSAGE_IX_TECHNOLOGIES.items() if v.get("sector") == "land"],
    "Liquids": [k for k, v in MESSAGE_IX_TECHNOLOGIES.items() if v.get("sector") == "liquids"],
    "Non-CO2": [k for k, v in MESSAGE_IX_TECHNOLOGIES.items() if v.get("sector") == "non-CO2"],
    "Nuclear": [k for k, v in MESSAGE_IX_TECHNOLOGIES.items() if v.get("sector") == "nuclear"],
    "CCS": [k for k, v in MESSAGE_IX_TECHNOLOGIES.items() if v.get("sector") == "ccs"],
    "Residential & Commercial": [k for k, v in MESSAGE_IX_TECHNOLOGIES.items() if v.get("sector") == "residential_commercial"],
    "Solids": [k for k, v in MESSAGE_IX_TECHNOLOGIES.items() if v.get("sector") == "solids"],
    "Transport": [k for k, v in MESSAGE_IX_TECHNOLOGIES.items() if v.get("sector") == "transport"],
    "Shipping": [k for k, v in MESSAGE_IX_TECHNOLOGIES.items() if v.get("sector") == "shipping"],
    "System": [k for k, v in MESSAGE_IX_TECHNOLOGIES.items() if v.get("sector") == "system"],
}
