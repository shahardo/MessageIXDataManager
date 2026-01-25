# Electricity Costs by Fuel Source Chart Implementation Plan

## Overview
This document outlines the implementation plan for adding a stacked bar chart displaying scenario electricity costs broken down by fuel source to the MessageIX DataManager results dashboard. The chart will show electricity costs by fuel (coal, gas, nuclear, solar, wind, etc.) over time, with the total bar height representing total electricity costs for each year.

## Current Dashboard Structure
The results file dashboard currently displays:
- **Metrics Row**: 4 key metrics (Primary Energy 2050, Electricity 2050, % Clean Electricity, Emissions 2050)
- **Charts Grid (2x2)**:
  1. Primary Energy Supply over years (stacked bar)
  2. Electricity Generation by source (stacked bar)
  3. Primary Energy Mix pie chart (2050)
  4. Electricity Sources pie chart (2050)

## Proposed Solution: Tabbed Dashboard Interface

### Overall Architecture
Implement a tabbed interface with two main tabs:
- **Tab 1: "Overview"** - Existing 4 charts for general scenario overview
- **Tab 2: "Electricity"** - Electricity-focused charts including the new costs chart

### Electricity Tab Layout
```
Electricity Tab
├── Metrics Row (Electricity 2050, % Clean Electricity, etc.)
└── Charts Grid (2x1)
    ├── Electricity Generation by Fuel Source (existing stacked bar)
    └── Electricity Costs by Fuel Source (new stacked bar)
```

## Data Sources and LCOE Calculation

### Available MESSAGEix Parameters
- `var_cost`: Variable costs by technology [node_loc, tec, year_vtg, year_act, mode, time]
- `total_cost`: Total system cost by year [node, year]
- `inv_cost`: Investment costs [node_loc, tec, year_vtg]
- `fix_cost`: Fixed O&M costs [node_loc, tec, year_vtg, year_act]
- `var_act`: Activity variables (energy production) [node_loc, tec, year_vtg, year_act, mode, time]
- `emission_factor`: Emission factors by technology [node, tec, year_vtg, year_act, mode, time, emission]
- `tax_emission`: Carbon tax rates [node, emission, year]
- `bound_emission`: Emission bounds/constraints

### LCOE Calculation Approach: Realized Unit Costs

The most accurate approach is to calculate **realized unit costs** (LCOE proxy) by reverse-engineering the cost components from optimization results. This provides the intuitive cost breakdown users expect.

#### Core Concept
Calculate total annual costs for each component and divide by total annual generation to get unit costs ($/MWh):
- **Annualized Capex**: Capital recovery from historical investments
- **Fixed Opex**: Based on active capacity
- **Variable Opex**: Based on activity levels
- **Fuel Costs**: Activity × fuel consumption × fuel prices
- **Emission Costs**: Activity × emission factors × emission prices

#### Prerequisites
- Access to optimization results (variables and parameters)
- System discount rate for capital recovery calculations
- Proper alignment of data across nodes, years, technologies, and vintages

#### Required Data Sources
- **Activity**: `ACT` variable (generation by technology)
- **Capacity**: `CAP` and `CAP_NEW` variables
- **Investment**: `investment_cost`, `technical_lifetime`, `interest_rate` parameters
- **Opex**: `fixed_cost`, `variable_cost` parameters
- **Fuels**: `input` parameter, `PRICE_COMMODITY` variable
- **Emissions**: `emission_factor` parameter, `PRICE_EMISSION` variable

#### Calculation Pipeline

**A. Total Generation (Denominator)**
1. Get `ACT` for electricity technologies
2. Sum over modes to get total generation per `[node, year_act, technology]`

**B. Variable Opex (VOM)**
1. Merge `ACT` with `variable_cost` parameter
2. Calculate: `ACT` × `variable_cost`
3. Sum over modes for total variable costs

**C. Fixed Opex (FOM)**
1. Get active capacity from `CAP` variable
2. Merge with `fixed_cost` parameter
3. Calculate: `CAP` × `fixed_cost`

**D. Fuel Costs**
1. Identify fuel inputs using `input` parameter
2. Get fuel prices from `PRICE_COMMODITY`
3. Calculate: `ACT` × `input` × `PRICE_COMMODITY`
4. Sum over all input fuels

**E. Emission Costs**
1. Get emission factors and prices
2. Calculate: `ACT` × `emission_factor` × `PRICE_EMISSION`
3. Sum over emission types

**F. Annualized Capital Costs (Most Complex)**
1. Calculate Capital Recovery Factor (CRF): `CRF = interest_rate × (1+rate)^lifetime / ((1+rate)^lifetime - 1)`
2. For each vintage: `annualized_stream = CAP_NEW × investment_cost × CRF`
3. Map streams to active years: `year_act` where `year_vtg ≤ year_act < year_vtg + lifetime`
4. Sum annualized streams for all active vintages in each operation year

**G. Final Assembly**
1. Combine all cost components into one DataFrame
2. Divide by total generation to get unit costs ($/MWh)
3. Aggregate by fuel categories for chart visualization

### Fuel Technology Mapping
```python
FUEL_CATEGORIES = {
    'Coal': ['coal_ppl', 'coal', 'lignite', 'hard_coal'],
    'Natural Gas': ['gas_ppl', 'ngcc', 'gas', 'natural_gas', 'lng'],
    'Nuclear': ['nuclear', 'nuclear_ppl', 'nuclear_light_water'],
    'Solar': ['solar_pv', 'solar_csp', 'solar', 'pv', 'csp'],
    'Wind': ['wind_onshore', 'wind_offshore', 'wind', 'wind_ppl'],
    'Hydro': ['hydro', 'hydro_ppl', 'hydro_large', 'hydro_small'],
    'Biomass': ['biomass', 'bio_ppl', 'biomass_i', 'biomass_s'],
    'Geothermal': ['geothermal', 'geo_ppl'],
    'Other': []  # Catch-all for unmapped technologies
}
```

## Implementation Steps

### 1. UI Structure Updates
- [ ] **File**: `src/ui/results_file_dashboard.ui`
- [ ] **Changes**:
  - [ ] Replace main `QVBoxLayout` with `QTabWidget`
  - [ ] Create "Overview" and "Electricity" tab pages
  - [ ] Move existing widgets to Overview tab
  - [ ] Add new chart widget for electricity costs

### 2. Python Class Updates
- [ ] **File**: `src/ui/results_file_dashboard.py`
- [ ] **Changes**:
  - [ ] Initialize `QTabWidget` and tab pages
  - [ ] Update `_render_charts()` to handle tab-specific rendering
  - [ ] Add `_render_electricity_costs_chart()` method
  - [ ] Maintain existing chart logic for Overview tab

### 3. Cost Calculation Method
- [ ] **File**: `src/managers/results_analyzer.py`
- [ ] **New Methods**: `calculate_crf()`, `calculate_electricity_cost_breakdown()`

```python
def calculate_crf(self, interest_rate: float, lifetime: float) -> float:
    """Calculates Capital Recovery Factor for annualized capital costs."""
    if interest_rate == 0:
        return 1 / lifetime

    # Handle infinite lifetime or very long lifetimes to prevent overflow
    lifetime = min(lifetime, 100)

    rate_factor = (1 + interest_rate) ** lifetime
    crf = (interest_rate * rate_factor) / (rate_factor - 1)
    return crf

def calculate_electricity_cost_breakdown(self, scenario: ScenarioData, regions=None, electricity_commodity='electr') -> pd.DataFrame:
    """
    Analyzes a MESSAGEix scenario to break down electricity generation costs
    by technology and cost component (Capex, Opex, Fuels, Emissions).

    Returns DataFrame with unit costs ($/MWh) by technology and year.
    """
    if regions is None:
        regions = list(scenario.sets.get('node', pd.Series()).values)

    # Get default interest rate for CRF calculation
    interest_rate = 0.05  # Default 5%
    try:
        interest_par = scenario.get_parameter('interest_rate')
        if interest_par and not interest_par.df.empty:
            interest_rate = interest_par.df['value'].mean()
    except:
        pass

    # Identify electricity generating technologies
    output_param = scenario.get_parameter('output')
    if output_param:
        elec_techs = output_param.df[output_param.df['commodity'] == electricity_commodity]['technology'].unique().tolist()
    else:
        # Fallback: assume common electricity technologies
        elec_techs = ['coal_ppl', 'gas_ppl', 'nuclear', 'hydro', 'solar_pv', 'wind']

    # Get activity (generation) data
    act_param = scenario.get_parameter('ACT')
    if not act_param or act_param.df.empty:
        raise ValueError("ACT parameter not found - cannot calculate generation costs")

    # Filter for electricity technologies
    act_df = act_param.df[act_param.df['technology'].isin(elec_techs)].copy()

    # Total Generation per tech per year (sum over modes)
    gen_total = act_df.groupby(['node', 'year_act', 'technology'])['value'].sum().reset_index(name='total_gen_MWh')
    gen_total = gen_total[gen_total['total_gen_MWh'] > 0.001].copy()

    # --- Component Calculations ---

    # Variable Opex (VOM)
    vom_total = self._calculate_variable_opex(act_df, scenario, elec_techs)

    # Fixed Opex (FOM)
    fom_total = self._calculate_fixed_opex(scenario, elec_techs)

    # Fuel Costs
    fuel_total = self._calculate_fuel_costs(act_df, scenario, elec_techs)

    # Emission Costs
    em_total = self._calculate_emission_costs(act_df, scenario, elec_techs)

    # Annualized Investment Costs (CAPEX) - Most Complex
    capex_total = self._calculate_capex_costs(scenario, elec_techs, interest_rate)

    # --- Final Assembly ---
    final_df = gen_total.copy()

    # Merge all cost components
    cost_dfs = [capex_total, fom_total, vom_total, fuel_total, em_total]
    for df in cost_dfs:
        if not df.empty:
            final_df = pd.merge(final_df, df, on=['node', 'year_act', 'technology'], how='left')

    # Fill missing costs with zero
    cost_cols = ['cost_capex_total', 'cost_fom_total', 'cost_vom_total', 'cost_fuel_total', 'cost_em_total']
    final_df[cost_cols] = final_df[cost_cols].fillna(0)

    # Calculate Unit Costs ($/MWh)
    for col in cost_cols:
        unit_col = col.replace('cost_', 'Unit_').replace('_total', '')
        final_df[unit_col] = final_df[col] / final_df['total_gen_MWh']

    # Calculate Total Unit Cost
    unit_cost_cols = [col for col in final_df.columns if col.startswith('Unit_')]
    final_df['Unit_Total_LCOE_Proxy'] = final_df[unit_cost_cols].sum(axis=1)

    return final_df

def _calculate_variable_opex(self, act_df: pd.DataFrame, scenario: ScenarioData, elec_techs: list) -> pd.DataFrame:
    """Calculate variable operating costs."""
    var_cost_param = scenario.get_parameter('variable_cost')
    if not var_cost_param or var_cost_param.df.empty:
        return pd.DataFrame(columns=['node', 'year_act', 'technology', 'cost_vom_total'])

    vom_df = pd.merge(act_df, var_cost_param.df,
                     on=['node', 'technology', 'year_act', 'mode', 'time'],
                     how='left', suffixes=('_act', '_cost'))
    vom_df['cost_vom_total'] = vom_df['value_act'] * vom_df['value_cost']
    return vom_df.groupby(['node', 'year_act', 'technology'])['cost_vom_total'].sum().reset_index()

def _calculate_fixed_opex(self, scenario: ScenarioData, elec_techs: list) -> pd.DataFrame:
    """Calculate fixed operating costs based on capacity."""
    cap_param = scenario.get_parameter('CAP')
    fix_cost_param = scenario.get_parameter('fixed_cost')

    if not cap_param or not fix_cost_param or cap_param.df.empty or fix_cost_param.df.empty:
        return pd.DataFrame(columns=['node', 'year_act', 'technology', 'cost_fom_total'])

    fom_df = pd.merge(cap_param.df.rename(columns={'value': 'capacity'}),
                     fix_cost_param.df.rename(columns={'value': 'fix_cost'}),
                     on=['node', 'technology', 'year_act'], how='left')
    fom_df['cost_fom_total'] = fom_df['capacity'] * fom_df['fix_cost']
    return fom_df.groupby(['node', 'year_act', 'technology'])['cost_fom_total'].sum().reset_index()

def _calculate_fuel_costs(self, act_df: pd.DataFrame, scenario: ScenarioData, elec_techs: list) -> pd.DataFrame:
    """Calculate fuel costs."""
    input_param = scenario.get_parameter('input')
    price_param = scenario.get_parameter('PRICE_COMMODITY')

    if not input_param or not price_param or input_param.df.empty or price_param.df.empty:
        return pd.DataFrame(columns=['node', 'year_act', 'technology', 'cost_fuel_total'])

    # Filter fuel inputs
    fuel_commodities = price_param.df['commodity'].unique()
    fuel_inputs = input_param.df[input_param.df['commodity'].isin(fuel_commodities)]

    fuel_consumption = pd.merge(act_df, fuel_inputs,
                               on=['node', 'technology', 'year_act', 'mode', 'time'],
                               how='inner', suffixes=('_act', '_input'))
    fuel_consumption['fuel_qty'] = fuel_consumption['value_act'] * fuel_consumption['value_input']

    fuel_costs_df = pd.merge(fuel_consumption, price_param.df,
                            left_on=['node', 'year_act', 'commodity', 'time'],
                            right_on=['node', 'year', 'commodity', 'time'], how='left')
    fuel_costs_df['cost_fuel_total'] = fuel_costs_df['fuel_qty'] * fuel_costs_df['value']
    return fuel_costs_df.groupby(['node', 'year_act', 'technology'])['cost_fuel_total'].sum().reset_index()

def _calculate_emission_costs(self, act_df: pd.DataFrame, scenario: ScenarioData, elec_techs: list) -> pd.DataFrame:
    """Calculate emission costs."""
    em_factor_param = scenario.get_parameter('emission_factor')
    em_price_param = scenario.get_parameter('PRICE_EMISSION')

    if not em_factor_param or not em_price_param or em_factor_param.df.empty or em_price_param.df.empty:
        return pd.DataFrame(columns=['node', 'year_act', 'technology', 'cost_em_total'])

    emissions_qty = pd.merge(act_df, em_factor_param.df,
                            on=['node', 'technology', 'year_act', 'mode', 'time'], how='inner')
    emissions_qty['em_qty'] = emissions_qty['value_act'] * emissions_qty['value']

    em_costs_df = pd.merge(emissions_qty, em_price_param.df,
                          left_on=['node', 'year_act', 'emission', 'time'],
                          right_on=['node', 'year', 'emission', 'time'], how='left')
    em_costs_df['cost_em_total'] = em_costs_df['em_qty'] * em_costs_df['value']
    return em_costs_df.groupby(['node', 'year_act', 'technology'])['cost_em_total'].sum().reset_index()

def _calculate_capex_costs(self, scenario: ScenarioData, elec_techs: list, interest_rate: float) -> pd.DataFrame:
    """Calculate annualized capital costs - the most complex component."""
    cap_new_param = scenario.get_parameter('CAP_NEW')
    inv_cost_param = scenario.get_parameter('investment_cost')
    lifetime_param = scenario.get_parameter('technical_lifetime')

    if not cap_new_param or not inv_cost_param or not lifetime_param:
        return pd.DataFrame(columns=['node', 'year_act', 'technology', 'cost_capex_total'])

    # Merge capacity investments with costs and lifetimes
    capex_df = pd.merge(cap_new_param.df, inv_cost_param.df,
                       on=['node', 'technology', 'year_vtg'],
                       how='inner', suffixes=('_cap', '_cost'))

    # Add lifetimes (try vintage-specific first, then technology-level)
    lifetime_df = lifetime_param.df.copy()
    capex_df = pd.merge(capex_df, lifetime_df,
                       on=['node', 'technology', 'year_vtg'], how='left')

    # Fill missing lifetimes
    capex_df['lifetime'] = capex_df.get('lifetime', 30).fillna(30)

    # Calculate CRF and annualized costs
    capex_df['crf'] = capex_df.apply(lambda row: self.calculate_crf(interest_rate, row['lifetime']), axis=1)
    capex_df['overnight_cost'] = capex_df['value_cap'] * capex_df['value_cost']
    capex_df['annualized_inv_cost_stream'] = capex_df['overnight_cost'] * capex_df['crf']

    # Expand to all active years for each vintage
    model_years = sorted(scenario.options.get('MaxYear', 2050), scenario.options.get('MinYear', 2020))
    if 'year' in scenario.sets:
        model_years = sorted(scenario.sets['year'].tolist())

    expanded_capex = []
    for _, row in capex_df.iterrows():
        vtg = row['year_vtg']
        life = row['lifetime']
        stream_cost = row['annualized_inv_cost_stream']

        # Find years where this vintage is active
        active_years = [y for y in model_years if vtg <= y < vtg + life]

        for year_act in active_years:
            expanded_capex.append({
                'node': row['node'],
                'technology': row['technology'],
                'year_act': year_act,
                'cost_capex_total': stream_cost
            })

    capex_long_df = pd.DataFrame(expanded_capex)

    # Sum costs for same technology in same operation year
    if not capex_long_df.empty:
        return capex_long_df.groupby(['node', 'year_act', 'technology'])['cost_capex_total'].sum().reset_index()
    else:
        return pd.DataFrame(columns=['node', 'year_act', 'technology', 'cost_capex_total'])
```

### 4. Chart Rendering
- [ ] **File**: `src/ui/results_file_dashboard.py`
- [ ] **New Method**: `_render_electricity_costs_chart()`
- [ ] **Implementation**:
  - [ ] Use existing `_render_stacked_bar_chart()` method
  - [ ] Format data for Plotly stacked bar chart
  - [ ] Set appropriate titles and labels

### 5. Testing and Validation
- [ ] **File**: `tests/test_dashboard_calculations.py`
- [ ] **Add Tests**:
  - [ ] Cost calculation logic
  - [ ] Fuel mapping functionality
  - [ ] Chart data formatting
  - [ ] Edge cases (missing data, etc.)

## Data Processing Logic

### Cost Data Extraction
1. Try to find `var_cost` parameter in scenario
2. If not available, calculate from activity * cost rates
3. Handle different data formats (wide vs. long format)

### Fuel Aggregation
1. Map each technology to fuel category
2. Sum costs across all technologies in each fuel category
3. Handle unmapped technologies in "Other" category

### Time Series Alignment
1. Ensure cost data aligns with generation years
2. Handle missing years gracefully
3. Apply appropriate aggregation (sum, average, etc.)

## Chart Specifications

### Visual Design
- **Chart Type**: Stacked bar chart
- **X-axis**: Years
- **Y-axis**: Cost (currency units, e.g., USD/MWh or total USD)
- **Stack Elements**: Fuel sources (Coal, Gas, Nuclear, Renewables, etc.)
- **Optional**: Separate emissions costs visualization (e.g., hatched patterns or separate series)
- **Colors**: Consistent with existing dashboard theme
- **Title**: "Electricity Costs by Fuel Source (incl. Emissions)"

### Data Structure for Chart
```python
chart_data = {
    'years': [2020, 2030, 2040, 2050, 2060],
    'series': [
        {'name': 'Coal', 'data': [100, 120, 140, 160, 180]},
        {'name': 'Natural Gas', 'data': [200, 180, 160, 140, 120]},
        {'name': 'Nuclear', 'data': [150, 150, 150, 150, 150]},
        {'name': 'Solar', 'data': [50, 80, 120, 180, 250]},
        {'name': 'Wind', 'data': [30, 60, 100, 150, 200]},
        # ... other fuels
    ]
}
```

## Potential Challenges and Solutions

### Data Availability
- **Challenge**: Not all MESSAGEix result files contain detailed cost breakdowns
- **Solution**: Implement fallback calculation from activity * cost rates

### Technology Naming Variations
- **Challenge**: Different models use different technology names
- **Solution**: Flexible mapping system with regex patterns and catch-all categories

### Cost Component Selection
- **Challenge**: Deciding which costs to include (variable, fixed, investment, emissions)
- **Solution**: Configurable cost components with defaults based on LCOE methodology:
  - **Base costs**: var_cost, fix_cost, inv_cost (levelized over lifetime)
  - **Emissions costs**: emission_factor × tax_emission (when carbon pricing active)
  - **Optional**: Include/exclude specific components based on user preferences

### Performance Considerations
- **Challenge**: Large datasets with many technologies and years
- **Solution**: Efficient pandas operations and caching of processed data

## Testing Strategy

### Unit Tests
- Cost calculation functions
- Fuel mapping logic
- Data formatting for charts
- Error handling for missing data

### Integration Tests
- Full dashboard rendering with sample data
- Tab switching functionality
- Chart interactivity (zoom, hover, etc.)

### Sample Data Testing
- Test with real MESSAGEix result files
- Validate against known cost calculations
- Performance testing with large datasets

## Success Criteria
1. Dashboard displays tabbed interface with Overview and Electricity tabs
2. Electricity tab shows both generation and costs charts
3. Costs chart displays stacked bars by fuel source over time
4. Chart handles missing data gracefully
5. Performance acceptable with typical MESSAGEix datasets
6. Code follows project conventions and includes appropriate tests

## Future Enhancements
- Add cost breakdown tooltip showing detailed components
- Implement cost sensitivity analysis
- Add export functionality for chart data
- Support for different LCOE calculation methodologies
- Integration with other cost-related parameters
