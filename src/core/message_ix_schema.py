"""
Defines the valid MessageIX parameters, their dimensions, and descriptions.
Based on the canonical MESSAGEix scheme.
"""

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
