# Electricity Price Calculation Implementation Plan

## Overview
This document outlines the comprehensive implementation plan for extracting and calculating electricity generation costs from MESSAGEix scenarios, including capex, fixed and variable opex, fuel, and emissions costs. The system will handle both model horizon capacity (`CAP_NEW`) and legacy capacity (`historical_new_capacity`) to provide accurate LCOE (Levelized Cost of Energy) calculations.

## Architecture Overview

### Core Components
1. **Capacity Tracking System**: Maintains arrays of installed capacity by technology and vintage year
2. **Cost Calculation Engine**: Breaks down costs into components (Capex, Opex, Fuels, Emissions)
3. **Data Integration Layer**: Handles both input scenario data and optimization results
4. **LCOE Calculator**: Produces unit costs ($/MWh) for each technology and year

### Key Data Flows
```
Input Scenario ──> Cost Parameters ──> Capacity Tracking ──> Cost Calculation ──> LCOE Output
     │                      │                      │                      │
     ├── CAP_NEW           ├── inv_cost          ├── year_vintage       ├── Capex
     ├── historical_new_capacity  ├── fix_cost          ├── year_act           ├── Opex
     ├── technical_lifetime       ├── var_cost          └── lifetime           ├── Fuel
     └── emission_factor          ├── input              capacity arrays       └── Emissions
                                   └── tax_emission
```

## Historical Capacity Integration

### Legacy Capacity Handling
The `historical_new_capacity` parameter represents capacity additions that occurred before the model horizon. These need special handling because:

1. **Different Structure**: Historical capacity uses `year_vtg` (vintage year) but represents past investments
2. **Cost Mapping**: Same cost parameters apply but need to be matched by technology and vintage
3. **Lifetime Extension**: Historical capacity may still be operating within the model horizon
4. **Annualization**: Historical investments need to be annualized using the same CRF approach

### Implementation Strategy
```python
# 1. Extract historical capacity data
hist_cap_param = scenario.get_parameter('historical_new_capacity')

# 2. Map to cost parameters (same as model horizon capacity)
hist_df = pd.merge(hist_cap_param.df, inv_cost_param.df,
                  on=['node', 'technology', 'year_vtg'], how='inner')

# 3. Calculate annualized costs for each vintage
hist_df['annualized_cost'] = hist_df['capacity'] * hist_df['inv_cost'] * crf

# 4. Expand to all active years within model horizon
for each historical vintage:
    active_years = [y for y in model_years if vintage_year <= y < vintage_year + lifetime]
    for year in active_years:
        add annualized cost to that year
```

## Cost Component Calculations

### 1. Capital Expenditure (CAPEX)
**Purpose**: Annualized investment costs for capacity additions
**Data Sources**:
- `CAP_NEW`: New capacity investments in model horizon
- `historical_new_capacity`: Legacy capacity additions
- `investment_cost`: Overnight capital costs
- `technical_lifetime`: Technology lifetimes
- `interest_rate`: Discount rate for CRF calculation

**Calculation**:
```python
# Capital Recovery Factor
crf = interest_rate * (1 + interest_rate)^lifetime / ((1 + interest_rate)^lifetime - 1)

# Annualized CAPEX per vintage
annualized_capex = capacity * inv_cost * crf

# Distribute across active years
for year in active_years:
    capex_costs[technology][year] += annualized_capex
```

### 2. Fixed Operating Expenditure (FOM)
**Purpose**: Fixed O&M costs based on installed capacity
**Data Sources**:
- `CAP`: Total installed capacity by technology and year
- `fixed_cost`: Fixed O&M cost rates

**Calculation**:
```python
fom_costs = capacity * fixed_cost_rate
```

### 3. Variable Operating Expenditure (VOM)
**Purpose**: Variable O&M costs based on generation activity
**Data Sources**:
- `ACT`: Technology activity (generation) levels
- `variable_cost`: Variable O&M cost rates

**Calculation**:
```python
vom_costs = activity * variable_cost_rate
```

### 4. Fuel Costs
**Purpose**: Energy carrier costs for power generation
**Data Sources**:
- `input`: Fuel input requirements by technology
- `PRICE_COMMODITY`: Fuel prices by commodity and year

**Calculation**:
```python
fuel_consumption = activity * input_coefficient
fuel_costs = fuel_consumption * fuel_price
```

### 5. Emission Costs
**Purpose**: Carbon and other emission costs
**Data Sources**:
- `emission_factor`: Emissions per unit activity
- `PRICE_EMISSION`: Emission prices/taxes

**Calculation**:
```python
emissions = activity * emission_factor
emission_costs = emissions * emission_price
```

## Capacity Tracking Architecture

### Vintage Year Management
To properly handle `year_vintage` and `year_act` parameters, the system maintains capacity arrays:

```python
class CapacityTracker:
    def __init__(self):
        # tech -> vintage_year -> year -> capacity
        self.capacity_matrix = defaultdict(lambda: defaultdict(dict))

    def add_capacity(self, technology, vintage_year, year, capacity):
        """Add capacity for a specific technology vintage in a given year"""
        self.capacity_matrix[technology][vintage_year][year] = capacity

    def get_total_capacity(self, technology, year):
        """Sum all vintage capacities active in a given year"""
        total = 0
        for vintage_year, yearly_caps in self.capacity_matrix[technology].items():
            lifetime = self.get_technology_lifetime(technology, vintage_year)
            if year >= vintage_year and year < vintage_year + lifetime:
                total += yearly_caps.get(year, 0)
        return total
```

### Historical vs Model Horizon Capacity
- **Historical Capacity**: `historical_new_capacity` represents past investments
  - Added once at vintage year
  - Remains active until end of lifetime
  - Costs calculated from vintage year investment

- **Model Horizon Capacity**: `CAP_NEW` represents future investments
  - Can be added in any model year
  - Follows same lifetime rules
  - Costs calculated based on investment timing

## Input File Structure Requirements

### Solar Scenario Data Excel File Structure
The "files/solar scenario data.xlsx" should contain MESSAGEix parameter sheets:

#### Investment & Capacity Parameters
- `inv_cost`: Investment costs by technology and vintage [node, technology, year_vtg, value]
- `fix_cost`: Fixed O&M costs [node, technology, year_vtg, value]
- `var_cost`: Variable O&M costs [node, technology, year_vtg, value]
- `technical_lifetime`: Technology lifetimes [node, technology, year_vtg, value]
- `historical_new_capacity`: Legacy capacity additions [node, technology, year_vtg, value]

#### Fuel & Emission Parameters
- `input`: Fuel input coefficients [node, technology, year_vtg, commodity, value]
- `emission_factor`: Emission factors [node, technology, year_vtg, emission, value]

#### Economic Parameters
- `interest_rate`: Discount rate for CRF [value]

### Data Format Standards
- All parameters should use MESSAGEix standard dimensions
- Units must be consistent (e.g., costs in $/kW, emissions in kg/MWh)
- Time series data should cover the full model horizon

## Implementation Phases

### Phase 1: Core Infrastructure
- [x] **Capacity Tracker Class**: Implement vintage-based capacity management
- [ ] **Cost Parameter Loader**: Extract cost data from input scenarios
- [x] **CRF Calculator**: Implement capital recovery factor calculations

### Phase 2: Cost Component Calculations
- [x] **CAPEX Calculator**: Handle both historical and model horizon capacity
- [ ] **OPEX Calculators**: Fixed and variable operating cost calculations
- [ ] **Fuel Cost Calculator**: Energy carrier cost calculations
- [ ] **Emission Cost Calculator**: Environmental cost calculations

### Phase 3: Integration & Testing
- [x] **LCOE Assembly**: Combine all cost components into final unit costs
- [ ] **Data Validation**: Ensure cost calculations are reasonable
- [ ] **Performance Optimization**: Handle large datasets efficiently

### Phase 4: Enhanced Features
- [ ] **Technology Mapping**: Group technologies by fuel type for visualization
- [ ] **Sensitivity Analysis**: Test impact of different assumptions
- [ ] **Export Functionality**: Allow cost data export for further analysis
- [ ] **Extensibility**: Easy to add new cost components or modify existing calculations

## Key Technical Considerations

### Data Handling Challenges
- **Missing Parameters**: Graceful fallback when cost data is incomplete
- **Unit Conversions**: Ensure consistent units across all calculations
- **Time Series Alignment**: Proper handling of different time resolutions

### Performance Optimization
- **Memory Management**: Efficient storage of capacity matrices
- **Calculation Batching**: Group calculations by technology/year combinations
- **Caching**: Store intermediate results to avoid redundant calculations

### Validation & Error Handling
- **Data Quality Checks**: Validate input parameters for reasonableness
- **Cost Range Validation**: Flag unusually high or low cost estimates
- **Debug Logging**: Detailed logging for troubleshooting cost calculations

## Testing Strategy

### Unit Tests
- [ ] Individual cost component calculations
- [ ] Capacity tracking logic
- [ ] CRF calculations with edge cases

### Integration Tests
- [ ] Full LCOE calculation pipeline
- [ ] Historical capacity handling
- [ ] Multi-technology scenarios

### Validation Tests
- [ ] Compare against known MESSAGEix results
- [ ] Cross-check with alternative calculation methods
- [ ] Performance benchmarking

## Success Criteria
- [x] **Accurate Cost Breakdown**: LCOE calculations match expected values within tolerance
- [x] **Historical Capacity Support**: Legacy capacity properly integrated into calculations
- [ ] **Performance**: Handle large scenarios (100+ technologies, 50+ years) efficiently
- [x] **Maintainability**: Clean, well-documented code following project conventions
- [ ] **Extensibility**: Easy to add new cost components or modify existing calculations

## Usage Example
```python
# Load solar scenario
scenario = mainwindow.input_manager.get_scenario_by_file_path("files/solar scenario data.xlsx")

# Calculate electricity costs
cost_breakdown = results_analyzer.calculate_electricity_cost_breakdown(scenario)

# Results include:
# - Unit_Capex: $/MWh from capital costs
# - Unit_Fom: $/MWh from fixed O&M
# - Unit_Vom: $/MWh from variable O&M
# - Unit_Fuel: $/MWh from fuel costs
# - Unit_Em: $/MWh from emission costs
# - Unit_Total_LCOE_Proxy: Total levelized cost
