# Postprocessing Calculations Roadmap

This document describes the calculations needed for each postprocessing analysis in the MessageIX Data Manager.

**Status Legend:** [DONE] = Implemented | [PARTIAL] = Partially implemented | [ ] = Not started

---

## 1. Electricity

### 1.1 Power Plants Capacity (with Renewables) [BROKEN - #3, #12]

**Implementation:** `_calculate_power_capacity_with_renewables()`
**Output:** "Power capacity with renewables (MW)"

**Calculation:**
1. Get all technologies from `output` parameter where `level = "secondary"` and `commodity = "electr"`
2. Include renewable technologies by also checking `input` parameter where `level = "renewable"`
3. Get `CAP` (capacity) variable for these technologies
4. Group by technology type (fossil, nuclear, hydro, solar, wind, biomass, etc.)
5. Optionally add `CAP_NEW` for new capacity additions

**Data sources:**
- `CAP` variable - installed capacity by technology
- `CAP_NEW` variable - new capacity additions
- `output` parameter - to identify electricity-producing technologies
- `input` parameter with `level = "renewable"` - to identify renewable technologies

---

### 1.2 Electricity Generation by Source [DONE]

**Implementation:** `_calculate_electricity_generation_by_source()`
**Output:** "Electricity generation by source (TWh)"

**Calculation:**
1. Get technologies that output electricity: `output` where `commodity = "electr"` and `level = "secondary"`
2. Get `ACT` (activity) for these technologies
3. Multiply ACT by `output` parameter value to get actual electricity output
4. Group by technology or fuel type (coal, gas, oil, nuclear, hydro, solar, wind, biomass)
5. Convert units from GWa to TWh or PJ

**Data sources:**
- `ACT` variable - technology activity levels
- `output` parameter - electricity output coefficients
- Technology naming conventions to map to fuel types

---

### 1.3 Electricity Use by Sector [BROKEN - #2]

**Implementation:** `_calculate_electricity_use_by_sector()`
**Output:** "Electricity use by sector (TWh)"

**Calculation:**
1. Get technologies that input electricity: `input` where `commodity = "electr"`
2. Filter by output commodity to identify sector:
   - Transport: `output` commodity = "transport"
   - Industry: `output` commodity in ["i_spec", "i_therm"]
   - Buildings: `output` commodity in ["rc_spec", "rc_therm", "non-comm"]
   - Other/grid losses: remaining electricity use
3. Get `ACT` for these technologies
4. Multiply ACT by `input` parameter value to get electricity consumption
5. Group by sector

**Data sources:**
- `ACT` variable
- `input` parameter - electricity input coefficients
- `output` parameter - to identify sector by output commodity

---

## 2. Emissions

### 2.1 Emissions by Sector [MISSING - #6]

**Implementation:** `_calculate_emissions_by_sector()`
**Output:** "Emissions by sector (Mt)"

**Calculation:**
1. Get `EMISS` variable (emissions by technology)
2. Map technologies to sectors using `output` parameter:
   - Power: technologies outputting "electr"
   - Transport: technologies outputting "transport"
   - Industry: technologies outputting "i_spec", "i_therm"
   - Buildings: technologies outputting "rc_spec", "rc_therm"
   - Other: remaining technologies
3. Sum emissions by sector and emission type (CO2, CH4, etc.)

**Data sources:**
- `EMISS` variable - emissions by technology and type
- `output` parameter - for sector mapping
- `emission_factor` parameter - optional, for verification

---

### 2.2 Emissions by Source (Fuel) [MISSING - #6]

**Implementation:** `_calculate_emissions_by_fuel()`
**Output:** "Emissions by fuel (Mt)"

**Calculation:**
1. Get `EMISS` variable
2. Map technologies to fuel types using `input` parameter:
   - Coal technologies: input commodity = "coal"
   - Gas technologies: input commodity = "gas"
   - Oil technologies: input commodity in ["lightoil", "fueloil", "crudeoil"]
3. Alternatively, use `emission_factor` parameter grouped by input commodity
4. Sum emissions by fuel type

**Data sources:**
- `EMISS` variable
- `input` parameter - for fuel mapping
- `emission_factor` parameter

---

## 3. Energy Balance

### 3.1 Energy Export by Fuel [DONE - #8 fixed]

**Implementation:** `_calculate_energy_exports_by_fuel()`
**Output:** "Energy exports by fuel (PJ)"

**Calculation:**
1. Find export technologies: technology names ending with "_exp" or containing "export"
2. Get `ACT` for these technologies
3. Multiply by `input` or `output` parameter to get export volumes
4. Group by commodity (fuel type)
5. Convert to PJ

**Data sources:**
- `ACT` variable
- `input`/`output` parameters
- Technology naming convention for exports

---

### 3.2 Energy Import by Fuel [DONE - #8 fixed]

**Implementation:** `_calculate_energy_imports_by_fuel()`
**Output:** "Energy imports by fuel (PJ)"

**Calculation:**
1. Find import technologies: technology names ending with "_imp" or containing "import"
2. Get `ACT` for these technologies
3. Multiply by `output` parameter to get import volumes
4. Group by commodity (fuel type)
5. Convert to PJ

**Data sources:**
- `ACT` variable
- `output` parameter
- Technology naming convention for imports

---

### 3.3 Feedstock by Fuel [DONE]

**Implementation:** `_calculate_feedstock_by_fuel()`
**Output:** "Feedstock by fuel (PJ)"

**Calculation:**
1. Get technologies from `output` where `commodity = "i_feed"` (industrial feedstock)
2. These are technologies using fuels for non-energy purposes (petrochemicals, etc.)
3. Get `ACT` for these technologies
4. Multiply by `input` parameter to get fuel consumption for feedstock
5. Group by input commodity (fuel type)

**Implementation Details:**
- Uses `_model_output()` to get activity * input coefficients
- Groups by input commodity to show fuel type breakdown (coal, gas, oil, biomass)
- Adds historical data via `_add_history()`
- Unit conversion: 31.536 (GWa → PJ)

**Data sources:**
- `ACT` variable
- `input` parameter
- `output` parameter filtered by "i_feed"

---

### 3.4 Oil Derivatives Supply [DONE]

**Implementation:** `_calculate_oil_derivatives_supply()`
**Output:** "Oil derivatives supply (PJ)"

**Calculation:**
1. Find refinery technologies: output commodities include oil products (lightoil, fueloil, diesel, gasoline, etc.)
2. Get `ACT` for refinery technologies
3. Multiply by `output` parameter to get production of each oil derivative
4. Subtract exports, add imports for each derivative
5. Group by oil product type

**Data sources:**
- `ACT` variable
- `output` parameter - refinery outputs
- Import/export technologies for oil products

---

### 3.6 Oil Derivatives Use [DONE]

**Implementation:** `_calculate_oil_derivatives_use()`
**Output:** "Oil derivatives use by sector (PJ)"

**Calculation:**
1. Get technologies that input oil products: `input` where commodity in oil_products
2. Filter out refinery technologies (they produce, not consume)
3. Map to sectors using `output` parameter:
   - Power generation: output "electr"
   - Industry: output "i_spec", "i_therm"
   - Buildings: output "rc_spec", "rc_therm"
   - Transport: output "transport"
   - Other: remaining technologies
4. Get `ACT` for these technologies
5. Multiply by `input` parameter value
6. Group by sector

**Implementation Details:**
- Oil products tracked: lightoil, loil_rc, loil_i, fueloil, foil_rc, foil_i, diesel, gasoline, kerosene, naphtha, lpg
- Uses `_map_technologies_to_sectors()` for sector mapping
- Excludes refinery technologies (identified by output of oil products)
- Exports tracked separately via technology naming conventions
- Unit conversion: 31.536 (GWa → PJ)

**Data sources:**
- `ACT` variable
- `input` parameter - oil product consumption
- `output` parameter - for sector mapping and to identify refineries


### 3.5 Primary Energy Supply [DONE - #8 fixed]

**Implementation:** `_calculate_energy_balances()` (existing)
**Output:** "Primary energy supply (PJ)"

**Calculation:**
1. Get technologies from `output` where `level = "primary"`
2. Get `ACT` for these technologies
3. Multiply by `output` parameter value
4. Add renewable inputs: `input` where `level = "renewable"`
5. Add/subtract imports and exports
6. Group by primary fuel (coal, oil, gas, nuclear, hydro, solar, wind, biomass)

**Data sources:**
- `ACT` variable
- `output` parameter with `level = "primary"`
- `input` parameter with `level = "renewable"`
- Import/export technologies

---

## 4. Fuels

### 4.1 Gas Supply by Source [DONE]

**Implementation:** `_calculate_gas_supply_by_source()`
**Output:** "Gas supply by source (PJ)"

**Calculation:**
1. **Domestic production:** Technologies that output gas at primary level
   - `output` where `commodity = "gas"` and `level = "primary"`
2. **Imports:** Gas import technologies ("gas_imp" or similar)
   - Searches technology names for case-insensitive "_imp" suffix
   - Also discovers from input parameter data
3. **Exports:** Gas export technologies ("gas_exp" or similar)
   - Searches technology names for case-insensitive "_exp" suffix
   - Also discovers from output parameter data
4. Get `ACT` for all these technologies
5. Multiply by relevant parameter values (activity × coefficient)
6. Present as: Production + Imports - Exports = Total Supply

**Implementation Details:**
- Uses helper function `calculate_gas_supply_from_tecs()` for clean data processing
- Handles column name variations (technology vs tec)
- Aligns results by year index for proper DataFrame construction
- Unit conversion: 31.536 (GWa → PJ)

**Visualization:**
- Production + Imports: Stacked bars above zero
- Exports: Red bars below zero (barmode='relative')
- Total Supply: Green line with markers and value labels

**Data sources:**
- `ACT` variable
- `output` parameter for production
- `input` parameter for exports
- Import/export technology naming conventions

---

### 4.2 Gas Utilization by Sector [DONE]

**Implementation:** `_calculate_gas_utilization_by_sector()`
**Output:** "Gas use by sector (PJ)"

**Calculation:**
1. Get technologies that input gas: `input` where `commodity = "gas"`
2. Map to sectors using `output` parameter:
   - Power generation: output "electr"
   - Industry: output "i_spec", "i_therm"
   - Buildings: output "rc_spec", "rc_therm"
   - Transport: output "transport"
   - Exports: technology names containing "_exp" or "export"
3. Get `ACT` for these technologies
4. Multiply by `input` parameter value
5. Group by sector

**Implementation Details:**
- Simplified commodity filter to ["gas"]
- Added export detection via technology naming conventions
- Uses `_map_technologies_to_sectors()` for sector mapping
- Handles column name variations (technology vs tec)
- Unit conversion: 31.536 (GWa → PJ)
- Removes empty "Other" column from results

**Data sources:**
- `ACT` variable
- `input` parameter
- `output` parameter for sector mapping

---

## 5. Sectoral Use

### 5.1 Buildings by Fuel [DONE]

**Implementation:** `_calculate_buildings_by_fuel()`
**Output:** "Buildings energy by fuel (PJ)"

**Calculation:**
1. Get technologies from `output` where `commodity` in ["rc_spec", "rc_therm", "non-comm"]
2. Get `ACT` for these technologies
3. Multiply by `input` parameter to get fuel consumption
4. Group by input commodity (electricity, gas, oil, biomass, etc.)
5. Add historical data from `historical_activity`

**Data sources:**
- `ACT` variable
- `input` parameter
- `output` parameter
- `historical_activity` parameter

---

### 5.2 Industry by Fuel [DONE]

**Implementation:** `_calculate_industry_by_fuel()`
**Output:** "Industry energy by fuel (PJ)"

**Calculation:**
1. Get technologies from `output` where `commodity` in ["i_spec", "i_therm"]
2. Get `ACT` for these technologies
3. Multiply by `input` parameter to get fuel consumption
4. Group by input commodity
5. Add historical data from `historical_activity`

**Data sources:**
- `ACT` variable
- `input` parameter
- `output` parameter
- `historical_activity` parameter

---

## 6. Prices

### 6.1 Energy Price by Sector [DONE]

**Implementation:** `_calculate_prices_by_sector()`
**Output:** "Energy price by sector ($/MWh)"

**Calculation:**
1. Get `PRICE_COMMODITY` variable
2. Filter by commodities representing sectoral demand:
   - Transport: "transport"
   - Industry: "i_spec", "i_therm"
   - Buildings: "rc_spec", "rc_therm"
3. These prices represent the marginal cost of delivering energy to each sector

**Data sources:**
- `PRICE_COMMODITY` variable

---

### 6.2 Energy Price by Fuel [DONE]

**Implementation:** `_calculate_prices_by_fuel()`
**Output:** "Energy price by fuel ($/MWh)"

**Calculation:**
1. Get `PRICE_COMMODITY` variable
2. Filter by fuel commodities at final/secondary level:
   - Electricity: "electr"
   - Gas: "gas" at final level
   - Oil products: "lightoil", "fueloil", etc.
3. Group by fuel type and level

**Data sources:**
- `PRICE_COMMODITY` variable

---

### 6.3 Primary Energy Prices by Fuel [DONE]

**Implementation:** `_calculate_prices()` (existing)
**Output:** "Primary Energy Prices ($/MWh)"

**Calculation:**
1. Get `PRICE_COMMODITY` variable
2. Filter by level = "primary"
3. Group by commodity (coal, oil, gas, uranium, etc.)

**Data sources:**
- `PRICE_COMMODITY` variable with level filter

---

### 6.4 Secondary Energy Prices by Fuel [DONE]

**Implementation:** `_calculate_prices()` (existing)
**Output:** "Secondary Energy Prices ($/MWh)"

**Calculation:**
1. Get `PRICE_COMMODITY` variable
2. Filter by level = "secondary"
3. Group by commodity

**Data sources:**
- `PRICE_COMMODITY` variable with level filter

---

### 6.5 Electricity Price (LCOE - Levelized Cost of Electricity) [DONE]

**Implementation:** `_calculate_electricity_lcoe()`
**Output:** "Electricity LCOE ($/MWh)"

**Calculation:**
1. Get `PRICE_COMMODITY` for electricity at secondary level
2. This represents the system-wide marginal cost of electricity
3. For average LCOE, weight by generation:
   - LCOE_avg = Sum(Generation_i * MarginalCost_i) / Total_Generation

**Data sources:**
- `PRICE_COMMODITY` variable for "electr"
- `ACT` variable for generation weights

---

### 6.6 Electricity Price by Source (Detailed LCOE) [DONE]

**Implementation:** `_calculate_electricity_price_by_source()`
**Output:** "Electricity cost by source ($/MWh)"

**Calculation:**
For each electricity-generating technology, calculate LCOE components:

1. **CAPEX component:**
   - Get `inv_cost` parameter (investment cost per capacity)
   - Get `CAP_NEW` variable (new capacity)
   - Annualize using discount rate and lifetime: `inv_cost * CRF / capacity_factor`
   - CRF (Capital Recovery Factor) = r(1+r)^n / ((1+r)^n - 1)

2. **Fixed O&M component:**
   - Get `fix_cost` parameter (fixed cost per capacity per year)
   - Divide by capacity factor to get per-MWh cost

3. **Variable O&M component:**
   - Get `var_cost` parameter (variable cost per activity)
   - Direct cost per MWh

4. **Fuel cost component:**
   - Get `input` parameter (fuel input per electricity output)
   - Get fuel price from `PRICE_COMMODITY` at primary/secondary level
   - Fuel_cost = input_coefficient * fuel_price

5. **Emission cost component:**
   - Get `emission_factor` parameter
   - Get `PRICE_EMISSION` variable (carbon price)
   - Emission_cost = emission_factor * carbon_price

6. **Total LCOE by source:**
   - LCOE_source = CAPEX + Fixed_OM + Variable_OM + Fuel + Emissions

7. **Weighted system LCOE:**
   - Weight each source's LCOE by its share of generation
   - System_LCOE = Sum(LCOE_i * Share_i)

**Data sources:**
- `inv_cost` parameter - investment costs
- `fix_cost` parameter - fixed O&M costs
- `var_cost` parameter - variable O&M costs
- `input` parameter - fuel input coefficients
- `output` parameter - electricity output coefficients
- `emission_factor` parameter - emissions per activity
- `PRICE_COMMODITY` variable - fuel prices
- `PRICE_EMISSION` variable - emission/carbon prices
- `ACT` variable - for generation shares
- `CAP`, `CAP_NEW` variables - for capacity
- `technical_lifetime` parameter - for annualization
- `discount_rate` or model-wide discount rate

**Notes:**
- Capacity factor can be derived from ACT / (CAP * 8760 hours)
- For existing plants, use historical average costs or current market prices
- Consider including transmission/distribution costs for delivered electricity price

---

## Implementation Summary

**Status Legend:** DONE = Working | BROKEN = Has issues | MISSING = Not displayed in UI | PARTIAL = Incomplete

| Category | Section | Status | Method | Issue # |
|----------|---------|--------|--------|---------|
| Electricity | Power Capacity with Renewables | BROKEN | `_calculate_power_capacity_with_renewables()` | #3, #12 |
| Electricity | Power Capacity (New) | BROKEN | `_calculate_power_capacity_new()` | #4 |
| Electricity | Generation by Source | DONE | `_calculate_electricity_generation_by_source()` | - |
| Electricity | Use by Sector | DONE | `_calculate_electricity_use_by_sector()` | #2 (fixed) |
| Emissions | Total | DONE | `_calculate_emissions()` | #5 (fixed) |
| Emissions | By Sector | DONE | `_calculate_emissions_by_sector()` | #6 (fixed) |
| Emissions | By Fuel | DONE | `_calculate_emissions_by_fuel()` | #6 (fixed) |
| Energy Balance | Final Energy Consumption | DONE | `_calculate_energy_balances()` | #7 (fixed) |
| Energy Balance | Exports by Fuel | DONE | `_calculate_energy_exports_by_fuel()` | #8 (fixed) |
| Energy Balance | Imports by Fuel | DONE | `_calculate_energy_imports_by_fuel()` | #8 (fixed) |
| Energy Balance | Feedstock by Fuel | DONE | `_calculate_feedstock_by_fuel()` | - |
| Energy Balance | Oil Derivatives Supply | DONE | `_calculate_oil_derivatives_supply()` | - |
| Energy Balance | Oil Derivatives Use | DONE | `_calculate_oil_derivatives_use()` | #11 (fixed) |
| Energy Balance | Primary Supply | DONE | `_calculate_energy_balances()` | #8 (fixed) |
| Fuels | Gas Supply | DONE | `_calculate_gas_supply_by_source()` | - |
| Fuels | Gas Utilization | DONE | `_calculate_gas_utilization_by_sector()` | - |
| Sectoral | Buildings by Fuel | DONE | `_calculate_buildings_by_fuel()` | #15 (fixed by #8 DataFrame fix) |
| Sectoral | Industry by Fuel | DONE | `_calculate_industry_by_fuel()` | #15 (fixed by #8 DataFrame fix) |
| Prices | By Sector | DONE | `_calculate_prices_by_sector()` | - |
| Prices | By Fuel | BROKEN | `_calculate_prices_by_fuel()` | #13 |
| Prices | Primary Prices | MISSING | `_calculate_prices()` | #14 |
| Prices | Secondary Prices | MISSING | `_calculate_prices()` | #14 |
| Prices | Electricity LCOE | MISSING | `_calculate_electricity_lcoe()` | #14 |
| Prices | Cost by Source | PARTIALLY DONE | `_calculate_electricity_price_by_source()` | #1 |

---

## Common Patterns

### Technology-to-Sector Mapping
```
Power:     output.commodity == "electr" AND output.level == "secondary"
Transport: output.commodity == "transport"
Industry:  output.commodity IN ("i_spec", "i_therm")
Buildings: output.commodity IN ("rc_spec", "rc_therm", "non-comm")
```

### Technology-to-Fuel Mapping
Use `input` parameter commodity to identify fuel type:
- Coal: input.commodity == "coal"
- Gas: input.commodity == "gas"
- Oil: input.commodity IN ("lightoil", "fueloil", "crudeoil")
- Electricity: input.commodity == "electr"
- Renewables: input.level == "renewable"

### Import/Export Identification
- Imports: technology name ends with "_imp"
- Exports: technology name ends with "_exp" or contains "_exp"

### Unit Conversions
- GWa to PJ: multiply by 31.536 (1 GWa = 31.536 PJ)
- GWa to TWh: multiply by 8.76 (1 GWa = 8760 GWh = 8.76 TWh)

---

## Helper Functions Added

The following helper functions were added to support the calculations:

| Function | Purpose |
|----------|---------|
| `_get_sector_commodities()` | Maps sectors to output commodities |
| `_get_fuel_commodities()` | Maps fuel categories to commodity names |
| `_map_technologies_to_sectors()` | Maps technologies to sectors based on output |
| `_get_technologies_by_input_fuel()` | Gets technologies using specific fuel inputs |
| `_get_technologies_by_output()` | Gets technologies with specific outputs |
| `_get_renewable_technologies()` | Gets technologies with renewable inputs |
| `_calculate_fuel_use_by_sector()` | Common helper for sectoral fuel calculations |

---

## Known Issues and Fixes (2026-02-07)

This section documents identified problems with the current postprocessing implementation and their suggested fixes.

### Issue 1: Electricity Cost by Source - Shows Only Nuclear

**Problem:** The electricity cost by source calculation only displays nuclear, but should show all sources (gas, coal, solar, wind, etc.). Nuclear may not even be applicable to the current model.

**Suggested Fix:**
1. Review technology filtering in `_calculate_electricity_price_by_source()` - ensure all electricity-generating technologies are captured
2. Check that the filter includes technologies from both `output` (commodity="electr") AND `input` (level="renewable")
3. Verify technology name matching patterns work for actual technology names in the data
4. Add fallback to include technologies with cost data even if not matched by output commodity

---

### Issue 2: Electricity Use by Sector - Numbers Too High, Wrong Sectors [FIXED]

**Problem:** The electricity use numbers are too high, there shouldn't be a "power" sector (power generates, doesn't consume), and sectors should show actual technology names like `elec_i`, `hp_el_i`, `electric heating`, etc.

**Fix Applied (2026-02-07):**
1. Changed `_calculate_electricity_use_by_sector()` to filter for technologies that input electricity at "final" level
2. Explicitly excluded power generation technologies (those outputting "electr" at secondary level)
3. Groups by actual technology names instead of abstract sector categories
4. Fixed bug where empty historical data DataFrame caused all values to become zero
5. Unit conversion GWa to TWh (×8.76) is applied correctly
6. Added separate calculations for losses and curtailment:
   - **Storage losses**: Calculated as input - output for storage technologies (stor_ppl)
   - **Grid/T&D losses**: Calculated as input - output for transmission technologies (elec_t_d, grid)
   - **Renewables curtailment**: Calculated as potential generation - actual generation for renewable technologies

**Changes made to `results_postprocessor.py`:**
- Rewrote `_calculate_electricity_use_by_sector()` method (lines 1107-1190)
- Added `_calculate_losses()` helper method for storage/grid losses
- Added `_calculate_curtailment()` helper method for renewables curtailment
- Now shows: consumer technologies + Storage losses + Grid losses + Curtailment

---

### Issue 3: Power Plant Capacity - Renewables Missing

**Problem:** Power plant capacity calculation does not show renewable capacity (solar, wind, hydro, etc.).

**Suggested Fix:**
1. Ensure `input` parameter with `level = "renewable"` is being queried to identify renewable technologies
2. Add these technologies to the capacity query alongside the `output` commodity="electr" filter
3. Check that `CAP` variable includes renewable technology names
4. May need to use OR logic: technologies that output electricity OR have renewable inputs

---

### Issue 4: Power Plant New Capacity - Renewables Missing

**Problem:** Same as Issue 3 - new capacity additions don't include renewables.

**Suggested Fix:**
1. Apply same fix as Issue 3 to the `CAP_NEW` variable query
2. Ensure renewable technologies are included in the technology filter

---

### Issue 5: Emissions - Go Up Instead of Down [FIXED]

**Problem:** Emissions trajectory shows increasing emissions over time, but decarbonization scenarios should show decreasing emissions.

**Root Cause:** The original `_calculate_emissions()` method only fetched "TCE" (Total Carbon Equivalent) emissions and did not include historical emissions from the `historical_emission` parameter.

**Fix Applied (2026-02-07):**
1. Rewrote `_calculate_emissions()` to get all emission types (not just "TCE")
2. Added support for `historical_emission` parameter to include historical years
3. Properly combines historical and model data using `combine_first()`
4. Filters to plot years and removes zero columns
5. Updated `_calculate_emissions_by_sector()` to include historical data
6. Updated `_calculate_emissions_by_fuel()` to filter by plot years properly

**Changes made to `results_postprocessor.py`:**
- Rewrote `_calculate_emissions()` method (lines 893-955)
- Rewrote `_calculate_emissions_by_sector()` method to include historical emissions
- Updated `_calculate_emissions_by_fuel()` to filter by plot years

**Note:** If emissions still show an upward trend after this fix, it may be a data issue (the scenario itself does not model decarbonization) rather than a code issue.

---

### Issue 6: Missing - Emissions by Sector, Emissions by Source [FIXED]

**Problem:** These analyses are documented as [DONE] but are not appearing in the UI.

**Root Cause (discovered via debug):** The EMISS variable has structure `[node, emission, type_tec, year, lvl, mrg]`:
- NO 'technology' column - has `type_tec` instead (sector categories like "import", "all", etc.)
- The `emission` column contains emission types (TCE, CO2, CH4, etc.)
- The `emission_factor` parameter contains emissions CONVERSION technologies (CO2_TCE, CH4_TCE) not actual plant emission factors

**Fix Applied (2026-02-07):**
1. **Emissions by sector**: Now uses `type_tec` column from EMISS to group by sector/category
2. **Emissions by type**: Now uses `emission` column from EMISS to group by emission type (CO2, CH4, TCE, etc.)
3. Removed fallback to ACT × emission_factor since it doesn't work with this data structure

**Output names:**
- "Emissions by sector (Mt)" - grouped by type_tec values
- "Emissions by type (Mt)" - grouped by emission type (was "Emissions by fuel")

**Changes made to `results_postprocessor.py`:**
- Rewrote `_calculate_emissions_by_sector()` to use `type_tec` column
- Rewrote `_calculate_emissions_by_fuel()` → now outputs "Emissions by type (Mt)" using `emission` column

---

### Issue 7: Final Energy Consumption - Only Oil Products, Only Historical Years [FIXED]

**Problem:** Final energy consumption shows only fueloil and lightoil for years 2000-2015 (historical). Missing: electricity, natural gas, coal, biomass. Missing: model years (2020+).

**Root Cause:** The original implementation looked for technologies that OUTPUT at "final" level, which only captured oil products. It should look at what end-use technologies CONSUME (their inputs).

**Fix Applied (2026-02-07):**
1. Changed approach: instead of filtering by `output.level == "final"`, now filters by `output.commodity` in end-use sectors (transport, i_spec, i_therm, rc_spec, rc_therm, non-comm)
2. Changed from getting OUTPUT (what is produced at final level) to INPUT (what fuels end-use technologies consume)
3. Properly combines historical_activity with ACT variable for full time series
4. Added safety check for empty historical data to prevent all-zero results

**Changes made to `results_postprocessor.py`:**
- Rewrote final energy consumption section in `_calculate_energy_balances()` (lines 850-867)
- End-use commodities: transport, i_spec, i_therm, rc_spec, rc_therm, non-comm
- Now shows all fuels: electricity, gas, coal, biomass, oil products, etc.
- Includes both historical years and model years

---

### Issue 8: Missing - Energy Export/Import by Fuel, Feedstock by Fuel, Primary Energy Supply [FIXED]

**Problem:** These analyses are documented as [DONE] or [PARTIAL] but are not appearing in the UI.

**Root Causes (discovered via debug):**
1. **Pandas DataFrame addition bug:** When `_add_history()` returns a DataFrame with index but no columns (no historical data), the pattern `(df_hist + df).fillna(0)` zeros out ALL values. Pandas treats missing columns in the addition as NaN, and fillna(0) replaces them with 0 instead of preserving the original data. This affected ALL calculations that combine model data with historical data, not just Issue 8.
2. **Export parameter mismatch:** `_calculate_energy_exports_by_fuel()` used `"input"` parameter for export technologies, but export techs often don't have `input` defined. Should use `"output"` (matching the working `_calculate_trade()` method).
3. **Technology set dependency:** Methods relied solely on `self.msg.set("technology")` which may be empty if the technology set wasn't loaded.

**Fix Applied (2026-02-10):**
1. **Core fix - DataFrame addition:** Replaced all 22 instances of `(df_hist + df).fillna(0)` and `(df + df_hist).fillna(0)` with `df.add(df_hist, fill_value=0)`. The `.add(fill_value=0)` method correctly preserves values when one DataFrame has no columns.
2. **Export parameter fix:** Changed `_calculate_energy_exports_by_fuel()` to use `"output"` parameter instead of `"input"` for export technologies.
3. **Robust technology discovery:** Added `_get_all_technology_names()` helper that falls back to extracting technology names from the ACT variable when the technology set is empty.

**Changes made to `results_postprocessor.py`:**
- Added `_get_all_technology_names()` helper method
- Changed `_calculate_energy_exports_by_fuel()` to use `"output"` and `_get_all_technology_names()`
- Changed `_calculate_energy_imports_by_fuel()` to use `_get_all_technology_names()`
- Replaced 22 instances of buggy DataFrame addition pattern across the file
- Removed redundant guard check in `_calculate_energy_balances()` final energy section

---

### Issue 9: Gas Supply by Source - Missing Imports/Exports, Wrong Quantity and Timing

**Problem:** Gas supply doesn't show imports or exports. Quantity is too high. Decrease should start in 2050 but shows only in 2080.

**Suggested Fix:**
1. Review import/export technology matching - may not match actual technology names (check for variations like `gas_import`, `imp_gas`, etc.)
2. Verify unit conversion (GWa to PJ)
3. Check if production and trade are being combined correctly
4. Validate against expected scenario data - may be a data issue

---

### Issue 10: Missing - Gas Utilization by Sector

**Problem:** This analysis is documented as [DONE] but is not appearing in the UI.

**Suggested Fix:**
1. Verify `_calculate_gas_utilization_by_sector()` method exists and is called
2. Register in the postprocessor's analysis list

---

### Issue 11: Oil Derivatives Use - FIXED

**Status:** Implemented `_calculate_oil_derivatives_use()`

**Solution:**
1. Created new calculation `_calculate_oil_derivatives_use()` that tracks consumption of oil products by sector
2. Finds technologies with `input` commodity in oil products list
3. Maps to sectors using `output` commodity
4. Excludes refinery technologies (they produce, not consume)
5. Multiplies ACT by input coefficient
6. Results in "Oil derivatives use by sector (PJ)"


### Issue 12: Power Capacity with Renewables is Redundant

**Problem:** Now that renewables should be included in the main power capacity calculation, the separate "with renewables" variant is redundant.

**Suggested Fix:**
1. Merge into single "Power Plant Capacity" calculation that always includes renewables
2. Remove the separate "Power Capacity with Renewables" analysis
3. Update UI to show single unified capacity view

---

### Issue 13: Energy Price by Fuel - Wrong, Missing Sources, Jumps/Dips

**Problem:** Only shows light oil, missing other fuels (gas, coal, electricity). Many years omitted. Illogical jumps and dips in values.

**Suggested Fix:**
1. Expand commodity filter to include: electr, gas, coal, biomass, lightoil, fueloil
2. Include all levels (primary, secondary, final) with clear labeling
3. Investigate jumps/dips - may be due to:
   - Missing data interpolation
   - Incorrect year filtering
   - Multiple price entries being averaged incorrectly
4. Consider smoothing or flagging suspicious values

---

### Issue 14: Missing - Primary Energy Prices, Secondary Energy Prices, Electricity LCOE

**Problem:** These analyses are documented as [DONE] but are not appearing in the UI.

**Suggested Fix:**
1. Verify the corresponding methods exist and are called
2. Register these calculations in the postprocessor's analysis list
3. For LCOE: may need to simplify calculation to just use `PRICE_COMMODITY` for electricity at secondary level

---

### Issue 15: Missing - Buildings by Fuel, Industry by Fuel

**Problem:** Sectoral energy use analyses are documented as [DONE] but are not appearing in the UI.

**Suggested Fix:**
1. Verify `_calculate_buildings_by_fuel()` and `_calculate_industry_by_fuel()` methods exist and are called
2. Register these calculations in the postprocessor's analysis list
3. Ensure `historical_activity` is combined with `ACT` for full time series

---

## Priority Order for Fixes

| Priority | Issue | Complexity | Impact |
|----------|-------|------------|--------|
| 1 | Issue 8: Missing energy balance analyses | Medium | DONE |
| 2 | Issue 7: Final energy consumption incomplete | Medium | DONE |
| 3 | Issue 3/4: Renewables missing from capacity | Low | High - key data missing |
| 4 | Issue 6: Missing emissions analyses | Low | DONE |
| 5 | Issue 5: Emissions direction wrong | Medium | DONE |
| 6 | Issue 13: Price data issues | Medium | Medium - data quality |
| 7 | Issue 2: Electricity use by sector | Medium | DONE |
| 8 | Issue 9: Gas supply issues | Medium | Medium - incorrect values |
| 9 | Issue 1: LCOE missing sources | Medium | DONE |
| 10 | Issue 14/15: Missing price/sectoral analyses | Low | Medium - missing features |
| 11 | Issue 10: Missing gas utilization | Low | Low - missing feature |
| 12 | Issue 11: Oil derivatives use | Medium | Low - new feature |
| 13 | Issue 12: Remove redundancy | Low | Low - cleanup |

---

## Implementation Notes

### Common Root Causes

1. **DataFrame addition bug (FIXED)** - `(df_hist + df).fillna(0)` zeros out all values when `_add_history()` returns DataFrame with no columns. Fixed by using `df.add(df_hist, fill_value=0)` everywhere.
2. **Methods exist but not registered** - Many calculations are implemented but not added to the postprocessor's analysis list that populates the UI
3. **Technology name matching too restrictive** - Patterns like `_imp`, `_exp` may not match all variations
4. **Renewable technologies not included** - Need to check `input.level = "renewable"` in addition to `output.commodity = "electr"`
5. **Historical vs model years not combined** - Need to merge `historical_activity` with `ACT` variable
6. **Unit conversion errors** - Verify GWa to PJ (×31.536) and GWa to TWh (×8.76) conversions
