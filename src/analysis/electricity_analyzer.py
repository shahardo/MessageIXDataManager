"""
Electricity domain analyzer for MESSAGEix results.

Handles:
- Power plant capacity and new capacity
- Electricity generation by source
- Electricity use by sector (with storage/grid losses)
- Power capacity with renewables
- LCOE calculation
- Electricity price by source
- Dashboard metrics (primary energy, clean electricity %, emissions)
- Electricity cost breakdown
"""

import pandas as pd
from typing import Dict, List, Optional, Any

from core.data_models import ScenarioData, Parameter
from analysis.base_analyzer import BaseAnalyzer, ScenarioDataWrapper


class ElectricityAnalyzer(BaseAnalyzer):
    """Handles electricity domain calculations."""

    def calculate(self, nodeloc: str, yr: int) -> None:
        """Run all electricity calculations and populate self.results."""
        self._calculate_power_plant_results(nodeloc, yr)
        self._calculate_electricity_use(nodeloc, yr)
        self._calculate_electricity_generation_by_source(nodeloc, yr)
        self._calculate_electricity_use_by_sector(nodeloc, yr)
        self._calculate_power_capacity_with_renewables(nodeloc, yr)
        self._calculate_electricity_lcoe(nodeloc, yr)
        self._calculate_electricity_price_by_source(nodeloc, yr)

    # =========================================================================
    # Power Plant Results
    # =========================================================================

    def _calculate_power_plant_results(self, nodeloc: str, yr: int) -> None:
        """Calculate power plant activity and capacity metrics."""
        cap = self.msg.var("CAP", {"year_vtg": self.plotyrs})
        cap_new = self.msg.var("CAP_NEW", {"year_vtg": self.plotyrs})
        cap_hist = self.msg.par("historical_new_capacity", {"year_vtg": self.plotyrs})

        output_par = self.msg.par("output", {"commodity": "electr", "level": "secondary"})
        if output_par.empty:
            return

        tec = output_par["technology"].tolist()
        tec = list(set(tec + ["stor_ppl"]))

        # Power plant capacity
        if not cap.empty:
            ppl_cap = cap.loc[cap.technology.isin(tec)][["technology", "year_act", "lvl"]]
            ppl_cap = ppl_cap.groupby(["technology", "year_act"], as_index=False).sum(numeric_only=True)
            ppl_cap = ppl_cap.pivot(index="year_act", columns="technology")
            ppl_cap = ppl_cap[ppl_cap.columns[(ppl_cap != 0).any()]]
            if len(ppl_cap.columns) > 0:
                ppl_cap.columns = ppl_cap.columns.droplevel(0)
            ppl_cap = ppl_cap.loc[:, (ppl_cap > 0).any()]

            ppl_cap_mapped = self._mappings(ppl_cap, groupby="technology")
            self.results["Power plant capacity (MW)"] = ppl_cap_mapped * self.UNIT_GW_TO_MW

        # Power plant new capacity
        if not cap_new.empty:
            ppl_cap_new = cap_new.loc[(cap_new.technology.isin(tec)) & (cap_new.lvl > 0)][
                ["technology", "year_vtg", "lvl"]
            ]
            if not ppl_cap_new.empty:
                ppl_cap_new = ppl_cap_new.pivot(index="year_vtg", columns="technology")
                if len(ppl_cap_new.columns) > 0:
                    ppl_cap_new.columns = ppl_cap_new.columns.droplevel(0)

                if not cap_hist.empty:
                    ppl_cap_hist = cap_hist.loc[(cap_hist.technology.isin(tec)) & (cap_hist.value > 0)][
                        ["technology", "year_vtg", "value"]
                    ]
                    if not ppl_cap_hist.empty:
                        ppl_cap_hist = ppl_cap_hist.pivot(index="year_vtg", columns="technology")
                        if len(ppl_cap_hist.columns) > 0:
                            ppl_cap_hist.columns = ppl_cap_hist.columns.droplevel(0)
                        ppl_cap_new = ppl_cap_new.add(ppl_cap_hist, fill_value=0)

                cap_new_tot = ppl_cap_new.fillna(0)
                cap_new_tot = cap_new_tot[cap_new_tot.columns[(cap_new_tot > 0.001).any()]]
                cap_new_mapped = self._mappings(cap_new_tot, groupby="technology")
                self.results["Power plant new capacity (MW)"] = cap_new_mapped * self.UNIT_GW_TO_MW

        # Power plant activity (electricity generation)
        elec = self._plotdf(tec, ["electr"], "output", yr)

        if not elec.empty and "stor_ppl" in elec.columns:
            d_stor = self.msg.par("input", {"technology": "stor_ppl"})
            d_stor = d_stor.loc[d_stor["year_act"].isin(self.plotyrs)][
                ["technology", "year_act", "value"]
            ]
            if not d_stor.empty:
                d_stor = d_stor.groupby(["year_act"]).mean(numeric_only=True)
                elec["stor_ppl"] *= -d_stor["value"]

        elec_mapped = self._mappings(elec, groupby="technology")
        self.results["Electricity generation (TWh)"] = elec_mapped * self.UNIT_GWA_TO_TWH

    def _calculate_electricity_use(self, nodeloc: str, yr: int) -> None:
        """Calculate electricity usage by sector."""
        tecs = list(
            set(self.msg.par("input", {"commodity": "electr", "level": "final"}).get("technology", []))
        )
        tecs = tecs + ["stor_ppl"]

        df, df2 = self._model_output(tecs, nodeloc, "input", "electr")
        if df.empty:
            return

        df = self._group(df, ["year_act", "technology"], "product", 0.0, yr)

        df_hist = self._add_history(tecs, nodeloc, df2, "technology")
        df = df.add(df_hist, fill_value=0)

        rename_map = {
            "sp_el_RC": "buildings",
            "sp_el_I": "industry",
            "elec_trp": "transport"
        }
        df = df.rename(rename_map, axis=1)

        self.results["Electricity use (TWh)"] = df * self.UNIT_GWA_TO_TWH

    def _calculate_electricity_generation_by_source(self, nodeloc: str, yr: int) -> None:
        """Calculate electricity generation grouped by source/fuel type."""
        output_par = self.msg.par("output", {"commodity": ["electr"]})
        if output_par.empty:
            return

        tecs = list(set(output_par.technology))

        renewable_tecs = self._get_renewable_technologies()
        for tec in renewable_tecs:
            tec_output = self.msg.par("output", {"technology": [tec], "commodity": ["electr"]})
            if not tec_output.empty and tec not in tecs:
                tecs.append(tec)

        all_tecs = self.msg.set("technology")
        if len(all_tecs) > 0:
            renewable_patterns = ['solar', 'wind', 'hydro', 'geo', 'bio_ppl', 'csp']
            for tec in all_tecs:
                tec_str = str(tec).lower()
                if any(pattern in tec_str for pattern in renewable_patterns):
                    tec_output = self.msg.par("output", {"technology": [tec], "commodity": ["electr"]})
                    if not tec_output.empty and tec not in tecs:
                        tecs.append(tec)

        if not tecs:
            return

        df, df2 = self._model_output(tecs, nodeloc, "output", "electr")
        if df.empty:
            return

        df = self._group(df, ["year_act", "technology"], "product", 0.0, yr)
        df_mapped = self._mappings(df, groupby="technology")

        self.results["Electricity generation by source (TWh)"] = df_mapped * self.UNIT_GWA_TO_TWH

    def _calculate_electricity_use_by_sector(self, nodeloc: str, yr: int) -> None:
        """Calculate electricity consumption by consuming technologies."""
        all_input_par = self.msg.par("input", {"commodity": ["electr"]})
        if all_input_par.empty:
            return

        all_elec_tecs = list(set(all_input_par['technology'].tolist()))

        storage_tecs = [t for t in all_elec_tecs if "stor" in t.lower()]
        grid_tecs = [t for t in all_elec_tecs if any(g in t.lower() for g in ["elec_t_d", "grid", "t_d"])]

        final_input_par = self.msg.par("input", {"commodity": ["electr"], "level": ["final"]})
        if not final_input_par.empty:
            final_elec_tecs = list(set(final_input_par['technology'].tolist()))
        else:
            final_elec_tecs = all_elec_tecs

        output_elec = self.msg.par("output", {"commodity": ["electr"], "level": ["secondary"]})
        power_gen_tecs = set(output_elec['technology'].tolist()) if not output_elec.empty else set()

        exclude_tecs = power_gen_tecs | set(storage_tecs) | set(grid_tecs)
        consumer_tecs = [t for t in final_elec_tecs if t not in exclude_tecs]

        result_df = pd.DataFrame()

        if consumer_tecs:
            df, df2 = self._model_output(consumer_tecs, nodeloc, "input", "electr")
            if not df.empty:
                df = self._group(df, ["year_act", "technology"], "product", 0.0, yr)
                df_hist = self._add_history(consumer_tecs, nodeloc, df2, "technology")
                if not df_hist.empty and len(df_hist.columns) > 0:
                    df = df.add(df_hist, fill_value=0)
                result_df = df

        storage_losses = self._calculate_losses(storage_tecs, nodeloc, yr)
        if storage_losses is not None and not storage_losses.empty:
            result_df["Storage losses"] = storage_losses

        grid_losses = self._calculate_losses(grid_tecs, nodeloc, yr)
        if grid_losses is not None and not grid_losses.empty:
            result_df["Grid losses"] = grid_losses

        curtailment = self._calculate_curtailment(nodeloc, yr)
        if curtailment is not None and not curtailment.empty:
            result_df["Curtailment"] = curtailment

        if not result_df.empty:
            result_df = result_df.fillna(0)

        if not result_df.empty:
            result_df = result_df.loc[:, (result_df != 0).any()]

        if result_df.empty:
            return

        self.results["Electricity use by sector (TWh)"] = result_df * self.UNIT_GWA_TO_TWH

    def _calculate_losses(self, tecs: List[str], nodeloc: str, yr: int) -> Optional[pd.Series]:
        """Calculate losses for storage or grid technologies (input - output)."""
        if not tecs:
            return None

        df_in, _ = self._model_output(tecs, nodeloc, "input", "electr")
        if df_in.empty:
            return None

        df_out, _ = self._model_output(tecs, nodeloc, "output", "electr")

        input_by_year = df_in.groupby("year_act")["product"].sum()

        if not df_out.empty:
            output_by_year = df_out.groupby("year_act")["product"].sum()
            losses = input_by_year.subtract(output_by_year, fill_value=0)
        else:
            losses = input_by_year

        losses = losses.clip(lower=0)

        return losses if not losses.empty and losses.sum() > 0 else None

    def _calculate_curtailment(self, nodeloc: str, yr: int) -> Optional[pd.Series]:
        """Calculate renewables curtailment."""
        renewable_tecs = self._get_renewable_technologies()
        if not renewable_tecs:
            return None

        act = self.msg.var("ACT", {"technology": renewable_tecs})
        if act.empty:
            return None

        cap = self.msg.var("CAP", {"technology": renewable_tecs})
        if cap.empty:
            return None

        output_par = self.msg.par("output", {"technology": renewable_tecs, "commodity": ["electr"]})
        if output_par.empty:
            return None

        act_by_year = act.groupby("year_act")["lvl"].sum()
        cap_by_year = cap.groupby("year_act")["lvl"].sum()
        avg_cf = output_par["value"].mean() if not output_par.empty else 0.3

        potential_by_year = cap_by_year * avg_cf
        curtailment = potential_by_year.subtract(act_by_year, fill_value=0)
        curtailment = curtailment.clip(lower=0)

        return curtailment if not curtailment.empty and curtailment.sum() > 0 else None

    def _calculate_power_capacity_with_renewables(self, nodeloc: str, yr: int) -> None:
        """Calculate power plant capacity including renewables."""
        cap = self.msg.var("CAP", {"year_vtg": self.plotyrs})
        if cap.empty:
            return

        output_par = self.msg.par("output", {"commodity": ["electr"]})
        tecs_elec = list(set(output_par.technology)) if not output_par.empty else []

        renewable_tecs = self._get_renewable_technologies()
        for tec in renewable_tecs:
            tec_output = self.msg.par("output", {"technology": [tec], "commodity": ["electr"]})
            if not tec_output.empty and tec not in tecs_elec:
                tecs_elec.append(tec)

        all_tecs_in_model = self.msg.set("technology")
        if len(all_tecs_in_model) > 0:
            renewable_patterns = ['solar', 'wind', 'hydro', 'geo', 'bio_ppl', 'csp']
            for tec in all_tecs_in_model:
                tec_str = str(tec).lower()
                if any(pattern in tec_str for pattern in renewable_patterns):
                    tec_output = self.msg.par("output", {"technology": [tec], "commodity": ["electr"]})
                    if not tec_output.empty and tec not in tecs_elec:
                        tecs_elec.append(tec)

        all_tecs = list(set(tecs_elec + ["stor_ppl"]))

        ppl_cap = cap.loc[cap.technology.isin(all_tecs)][["technology", "year_act", "lvl"]]
        if ppl_cap.empty:
            return

        ppl_cap = ppl_cap.groupby(["technology", "year_act"], as_index=False).sum(numeric_only=True)
        ppl_cap = ppl_cap.pivot(index="year_act", columns="technology")
        ppl_cap = ppl_cap[ppl_cap.columns[(ppl_cap != 0).any()]]
        if len(ppl_cap.columns) > 0:
            ppl_cap.columns = ppl_cap.columns.droplevel(0)
        ppl_cap = ppl_cap.loc[:, (ppl_cap > 0).any()]

        ppl_cap_mapped = self._mappings(ppl_cap, groupby="technology")
        self.results["Power capacity with renewables (MW)"] = ppl_cap_mapped * self.UNIT_GW_TO_MW

    def _calculate_electricity_lcoe(self, nodeloc: str, yr: int) -> None:
        """Calculate Levelized Cost of Electricity (LCOE) by source."""
        output_par = self.msg.par("output", {"commodity": "electr", "level": "secondary"})
        if output_par.empty:
            return

        tecs = list(set(output_par.technology))

        act = self.msg.var("ACT", {"technology": tecs})
        if act.empty:
            return

        inv_cost = self.msg.par("inv_cost", {"technology": tecs})
        fix_cost = self.msg.par("fix_cost", {"technology": tecs})
        var_cost = self.msg.par("var_cost", {"technology": tecs})

        lcoe_results = {}

        for tec in tecs:
            tec_act = act[act['technology'] == tec]
            if tec_act.empty:
                continue

            tec_var = var_cost[var_cost['technology'] == tec] if not var_cost.empty else pd.DataFrame()
            year_col = 'year_act' if 'year_act' in tec_act.columns else 'year'

            for _, row in tec_act.iterrows():
                year = row.get(year_col, row.get('year_vtg'))
                activity = row.get('lvl', 0)
                if activity <= 0 or year not in self.plotyrs:
                    continue

                var = tec_var[tec_var['year_act'] == year]['value'].mean() if not tec_var.empty else 0
                if pd.isna(var):
                    var = 0

                if year not in lcoe_results:
                    lcoe_results[year] = {}
                if tec not in lcoe_results[year]:
                    lcoe_results[year][tec] = {'cost': var * 0.1142, 'activity': activity}
                else:
                    lcoe_results[year][tec]['activity'] += activity

        if lcoe_results:
            year_lcoe = {}
            for year, tec_data in lcoe_results.items():
                total_act = sum(d['activity'] for d in tec_data.values())
                if total_act > 0:
                    weighted_lcoe = sum(d['cost'] * d['activity'] for d in tec_data.values()) / total_act
                    year_lcoe[year] = weighted_lcoe

            if year_lcoe:
                result_df = pd.DataFrame({'LCOE': year_lcoe}).T
                result_df.index.name = 'year'
                self.results["Electricity LCOE ($/MWh)"] = result_df

    def _calculate_electricity_price_by_source(self, nodeloc: str, yr: int) -> None:
        """Calculate electricity generation cost breakdown by source.

        Method: for each technology, compute total costs (VOM + FOM + CAPEX + fuel + emissions)
        in M$/yr, then express as a cost contribution per MWh of TOTAL system generation:

            cost_contribution[tec, year] = total_cost[tec, year]
                                            / total_system_generation[year]
                                            × 0.1142   (M$/GWa → $/MWh)

        This additive formulation lets the stacked bar sum to the system-average LCOE.
        Technologies with zero activity in a year contribute zero cost.
        """
        # Find electricity-producing technologies (secondary output of 'electr')
        output_par = self.msg.par("output", {"commodity": "electr", "level": "secondary"})
        if output_par.empty:
            return

        tecs = list(set(output_par.technology))

        # Get activity levels and restrict to plot years
        act = self.msg.var("ACT", {"technology": tecs})
        if act.empty:
            return

        act = act[act['year_act'].isin(self.plotyrs)]
        if act.empty:
            return

        # Aggregate activity: sum across modes/vintages; drop zero-activity rows
        # (technologies that have been retired should not carry any costs)
        act_grouped = act.groupby(['year_act', 'technology'])['lvl'].sum().reset_index()
        act_grouped = act_grouped[act_grouped['lvl'] > 0]
        if act_grouped.empty:
            return

        costs = act_grouped.copy()
        costs['total_cost'] = 0.0  # will accumulate all 5 cost components

        # 1. Variable O&M: total_cost += ACT × var_cost
        #    (var_cost in M$/GWa, ACT in GWa → product in M$)
        var_cost = self.msg.par("var_cost", {"technology": tecs})
        if not var_cost.empty:
            vc_avg = var_cost.groupby(['year_act', 'technology'])['value'].mean().reset_index()
            costs = costs.merge(vc_avg, on=['year_act', 'technology'], how='left', suffixes=('', '_vc'))
            costs['total_cost'] += costs['lvl'] * costs['value'].fillna(0)
            costs.drop(columns=['value'], inplace=True)

        # 2. Fixed O&M: total_cost += CAP × fix_cost
        #    (fix_cost in M$/GW·yr, CAP in GW → product in M$/yr)
        cap = self.msg.var("CAP", {"technology": tecs})
        fix_cost = self.msg.par("fix_cost", {"technology": tecs})

        if not cap.empty and not fix_cost.empty:
            cap = cap[cap['year_act'].isin(self.plotyrs)]
            cap_grouped = cap.groupby(['year_act', 'technology'])['lvl'].sum().reset_index()

            fc_avg = fix_cost.groupby(['year_act', 'technology'])['value'].mean().reset_index()

            fc_calc = cap_grouped.merge(fc_avg, on=['year_act', 'technology'], how='inner')
            fc_calc['fom_cost'] = fc_calc['lvl'] * fc_calc['value']

            costs = costs.merge(fc_calc[['year_act', 'technology', 'fom_cost']], on=['year_act', 'technology'], how='left')
            costs['total_cost'] += costs['fom_cost'].fillna(0)
            costs.drop(columns=['fom_cost'], inplace=True)

        # 3. Annualized Investment Cost: total_cost += CAP_NEW × inv_cost × CRF
        #    Each vintage is active from year_vtg to year_vtg + lifetime.
        #    CRF = r(1+r)^L / ((1+r)^L - 1) converts overnight cost to annual payment.
        cap_new = self.msg.var("CAP_NEW", {"technology": tecs})
        inv_cost = self.msg.par("inv_cost", {"technology": tecs})
        lifetime = self.msg.par("technical_lifetime", {"technology": tecs})

        r = 0.05  # default discount rate
        ir_param = self.msg.par("interest_rate")
        if not ir_param.empty:
            r = ir_param['value'].mean()

        if not cap_new.empty and not inv_cost.empty:
            inv_cost_renamed = inv_cost.rename(columns={'value': 'value_cost'})
            # Join: each vintage of new capacity gets its investment cost
            inv_data = cap_new.merge(inv_cost_renamed, on=['node_loc', 'technology', 'year_vtg'])

            if not lifetime.empty:
                lt_avg = lifetime.groupby('technology')['value'].mean().reset_index()
                lt_avg = lt_avg.rename(columns={'value': 'lifetime'})
                inv_data = inv_data.merge(lt_avg, on='technology', how='left')
                inv_data['lifetime'] = inv_data['lifetime'].fillna(30)
            else:
                inv_data['lifetime'] = 30  # fallback: 30-year default lifetime

            inv_data['crf'] = inv_data['lifetime'].apply(lambda l: self._calculate_crf(r, l))
            # Annualised cost = capacity installed × overnight cost × CRF
            inv_data['ann_cost'] = inv_data['lvl'] * inv_data['value_cost'] * inv_data['crf']

            # Spread annualised cost across all active years (vtg ≤ y < vtg + lifetime)
            ann_costs = []
            for _, row in inv_data.iterrows():
                vtg = int(row['year_vtg'])
                life = int(row['lifetime'])
                cost = row['ann_cost']
                tech = row['technology']

                end_year = vtg + life
                for y in self.plotyrs:
                    if vtg <= y < end_year:
                        ann_costs.append({'year_act': y, 'technology': tech, 'inv_cost': cost})

            if ann_costs:
                ac_df = pd.DataFrame(ann_costs)
                # Sum contributions from multiple vintages active in the same year
                ac_grouped = ac_df.groupby(['year_act', 'technology'])['inv_cost'].sum().reset_index()

                costs = costs.merge(ac_grouped, on=['year_act', 'technology'], how='left')
                costs['total_cost'] += costs['inv_cost'].fillna(0)
                costs.drop(columns=['inv_cost'], inplace=True)

        # 4. Fuel Costs: total_cost += ACT × input_efficiency × commodity_price
        #    (input in PJ/GWa, price in M$/PJ, ACT in GWa → M$/yr)
        input_par = self.msg.par("input", {"technology": tecs})
        price_com = self.msg.var("PRICE_COMMODITY", {"node": nodeloc})

        if not input_par.empty and not price_com.empty:
            # Average efficiency across modes/vintages per (year, technology, commodity)
            in_avg = input_par.groupby(['year_act', 'technology', 'commodity'])['value'].mean().reset_index()
            pr_avg = price_com.groupby(['year', 'commodity'])['lvl'].mean().reset_index()

            # Join on both year and commodity to get correct year-specific prices
            fuel_calc = in_avg.merge(pr_avg, left_on=['year_act', 'commodity'], right_on=['year', 'commodity'], how='inner')
            fuel_calc['fuel_unit_cost'] = fuel_calc['value'] * fuel_calc['lvl']  # M$/GWa per unit input

            # Sum over multiple input commodities per technology
            fuel_cost_per_act = fuel_calc.groupby(['year_act', 'technology'])['fuel_unit_cost'].sum().reset_index()

            costs = costs.merge(fuel_cost_per_act, on=['year_act', 'technology'], how='left')
            costs['total_cost'] += costs['lvl'] * costs['fuel_unit_cost'].fillna(0)
            costs.drop(columns=['fuel_unit_cost'], inplace=True)

        # 5. Emission Costs: total_cost += ACT × emission_factor × carbon_price
        #    (emission_factor in tCO2/GWa, price in M$/tCO2, ACT in GWa → M$/yr)
        emission_factor = self.msg.par("emission_factor", {"technology": tecs})
        emission_price = self.msg.var("PRICE_EMISSION", {"node": nodeloc})

        if not emission_factor.empty and not emission_price.empty:
            ef_avg = emission_factor.groupby(['year_act', 'technology', 'emission'])['value'].mean().reset_index()
            ep_avg = emission_price.groupby(['year', 'emission'])['lvl'].mean().reset_index()

            # Join on year + emission type so CO2, CH4, etc. are priced separately
            em_calc = ef_avg.merge(ep_avg, left_on=['year_act', 'emission'], right_on=['year', 'emission'], how='inner')
            em_calc['em_unit_cost'] = em_calc['value'] * em_calc['lvl']  # M$/GWa per unit activity

            # Sum over all emission types per technology
            em_cost_per_act = em_calc.groupby(['year_act', 'technology'])['em_unit_cost'].sum().reset_index()

            costs = costs.merge(em_cost_per_act, on=['year_act', 'technology'], how='left')
            costs['total_cost'] += costs['lvl'] * costs['em_unit_cost'].fillna(0)
            costs.drop(columns=['em_unit_cost'], inplace=True)

        # Convert to cost contribution per MWh of TOTAL system generation.
        # Using total generation as denominator (not per-technology) ensures the
        # contributions are additive and sum to the system-average cost.
        yearly_total_act = costs.groupby('year_act')['lvl'].transform('sum')
        costs['cost_contribution'] = 0.0
        nonzero_mask = yearly_total_act > 0
        costs.loc[nonzero_mask, 'cost_contribution'] = (
            costs.loc[nonzero_mask, 'total_cost'] / yearly_total_act[nonzero_mask]
        ) * 0.1142  # M$/GWa → $/MWh conversion

        # Guard against any division artefacts
        costs['cost_contribution'] = costs['cost_contribution'].replace(
            [float('inf'), float('-inf')], 0
        ).fillna(0)

        # Pivot to wide format (year_act index, technology columns)
        result_df = costs[['year_act', 'technology', 'cost_contribution']].pivot(
            index='year_act', columns='technology', values='cost_contribution'
        )

        # Map individual technologies to named fuel categories (e.g. coal_ppl → "coal")
        result_mapped = self._mappings(result_df, groupby="technology")
        self.results["Electricity cost by source ($/MWh)"] = result_mapped

    # =========================================================================
    # CRF Calculation (used both in postprocessor and dashboard cost breakdown)
    # =========================================================================

    @staticmethod
    def _calculate_crf(interest_rate: float, lifetime: float) -> float:
        """Calculates Capital Recovery Factor."""
        if interest_rate == 0:
            return 1 / lifetime if lifetime > 0 else 0
        if lifetime <= 0:
            return 0
        lifetime = min(lifetime, 100)
        rate_factor = (1 + interest_rate) ** lifetime
        return (interest_rate * rate_factor) / (rate_factor - 1)

    @staticmethod
    def calculate_crf(interest_rate: float, lifetime: float) -> float:
        """Public interface for CRF calculation (for use in ResultsAnalyzer)."""
        return ElectricityAnalyzer._calculate_crf(interest_rate, lifetime)

    # =========================================================================
    # Dashboard Metrics (moved from ResultsAnalyzer)
    # =========================================================================

    @staticmethod
    def calculate_dashboard_metrics(scenario: ScenarioData) -> Dict[str, float]:
        """
        Calculate dashboard metrics for a given scenario.

        Computes the four key metrics displayed in the dashboard top row:
        - Total primary energy (2050)
        - Total electricity (2050)
        - % Clean electricity (2050)
        - Total emissions (2050)

        Args:
            scenario: ScenarioData object containing the scenario to analyze

        Returns:
            Dictionary with metric values.
        """
        import pandas as pd

        metrics = {
            'primary_energy_2050': 0.0,
            'electricity_2050': 0.0,
            'clean_electricity_pct': 0.0,
            'emissions_2050': 0.0
        }

        # 1. Primary energy 2050
        primary_energy_names = ['Primary energy supply (PJ)', 'var_primary_energy', 'primary_energy']
        primary_energy_param = None
        for name in primary_energy_names:
            primary_energy_param = scenario.get_parameter(name)
            if primary_energy_param:
                break

        if primary_energy_param and not primary_energy_param.df.empty:
            df = primary_energy_param.df
            year_col = 'year' if 'year' in df.columns else 'year_act'
            df_2050 = df[df[year_col] == 2050]
            if not df_2050.empty:
                for col in df_2050.columns:
                    if col != year_col and pd.api.types.is_numeric_dtype(df_2050[col]):
                        metrics['primary_energy_2050'] += df_2050[col].sum()

        # 2. Electricity 2050
        electricity_names = ['Electricity generation (TWh)', 'var_electricity', 'var_electricity_generation', 'var_electricity_consumption']
        electricity_param = None
        for name in electricity_names:
            electricity_param = scenario.get_parameter(name)
            if electricity_param:
                break

        if electricity_param and not electricity_param.df.empty:
            df = electricity_param.df
            year_col = 'year' if 'year' in df.columns else 'year_act'
            df_2050 = df[df[year_col] == 2050]
            if not df_2050.empty:
                for col in df_2050.columns:
                    if col not in [year_col, 'region'] and pd.api.types.is_numeric_dtype(df_2050[col]):
                        metrics['electricity_2050'] += df_2050[col].sum()

        # 3. Clean electricity percentage
        if electricity_param and not electricity_param.df.empty:
            df = electricity_param.df
            year_col = 'year' if 'year' in df.columns else 'year_act'
            df_2050 = df[df[year_col] == 2050]

            if not df_2050.empty:
                clean_technologies = ['nuclear', 'solar', 'solar PV', 'solar CSP', 'wind', 'hydro', 'biomass', 'geothermal', 'renewable']
                clean_electricity = 0.0
                total_electricity = 0.0

                if 'technology' in df_2050.columns and 'value' in df_2050.columns:
                    tech_sums = df_2050.groupby('technology')['value'].sum()
                    for tech, val in tech_sums.items():
                        total_electricity += val
                        if tech.lower() in [t.lower() for t in clean_technologies]:
                            clean_electricity += val
                else:
                    for col in df_2050.columns:
                        if col not in [year_col, 'region'] and pd.api.types.is_numeric_dtype(df_2050[col]):
                            val = df_2050[col].sum()
                            total_electricity += val
                            if col.lower() in [t.lower() for t in clean_technologies]:
                                clean_electricity += val

                if total_electricity > 0:
                    metrics['clean_electricity_pct'] = (clean_electricity / total_electricity) * 100

        # 4. Emissions 2050
        emissions_names = ['Total GHG emissions (MtCeq)', 'var_emissions', 'emissions']
        emissions_param = None
        for name in emissions_names:
            emissions_param = scenario.get_parameter(name)
            if emissions_param:
                break

        if emissions_param and not emissions_param.df.empty:
            df = emissions_param.df
            year_col = 'year' if 'year' in df.columns else 'year_act'
            df_2050 = df[df[year_col] == 2050]
            if not df_2050.empty:
                for col in df_2050.columns:
                    if col != year_col and pd.api.types.is_numeric_dtype(df_2050[col]):
                        metrics['emissions_2050'] += df_2050[col].sum()

        return metrics

    @staticmethod
    def calculate_electricity_cost_breakdown(
        scenario: ScenarioData,
        input_cost_scenario: Optional[ScenarioData] = None,
        regions: Optional[List[str]] = None,
        electricity_commodity: str = 'electr'
    ) -> pd.DataFrame:
        """
        Analyzes a MESSAGEix scenario to break down electricity generation costs
        by technology and cost component (Capex, Opex, Fuels, Emissions).

        Returns DataFrame with unit costs ($/MWh) by technology and year.

        Args:
            scenario: ScenarioData with result variables
            input_cost_scenario: Optional ScenarioData with input cost parameters
            regions: Optional list of regions (auto-detected if None)
            electricity_commodity: Name of electricity commodity
        """
        import pandas as pd

        if regions is None:
            if scenario.sets and isinstance(scenario.sets, dict) and 'node' in scenario.sets:
                regions = list(scenario.sets['node'].values)
            else:
                all_regions = set()
                for param_name, param in scenario.parameters.items():
                    if hasattr(param.df, 'columns'):
                        if 'node' in param.df.columns:
                            all_regions.update(param.df['node'].unique())
                        elif 'region' in param.df.columns:
                            all_regions.update(param.df['region'].unique())
                regions = list(all_regions) if all_regions else ['World']

        interest_rate = 0.05
        try:
            interest_par = scenario.get_parameter('interest_rate')
            if interest_par and not interest_par.df.empty:
                interest_rate = interest_par.df['value'].mean()
        except Exception:
            pass

        output_param = scenario.get_parameter('output')
        if output_param:
            elec_techs = output_param.df[output_param.df['commodity'] == electricity_commodity]['technology'].unique().tolist()
        else:
            elec_gen_param = scenario.get_parameter('Electricity generation (TWh)')
            if elec_gen_param and not elec_gen_param.df.empty:
                tech_cols = [col for col in elec_gen_param.df.columns if col not in ['year', 'year_act', 'node', 'region']]
                elec_techs = tech_cols
            else:
                elec_techs = ['coal', 'gas', 'nuclear', 'hydro', 'solar', 'wind']

        # Get activity data
        act_param = None
        for param_name in ['ACT', 'var_act', 'activity', 'Activity']:
            act_param = scenario.get_parameter(param_name)
            if act_param and not act_param.df.empty:
                break

        if not act_param or act_param.df.empty:
            for param_name in ['Electricity generation (TWh)', 'var_electricity', 'var_electricity_generation']:
                elec_param = scenario.get_parameter(param_name)
                if elec_param and not elec_param.df.empty:
                    act_df = elec_param.df.copy()
                    id_cols = ['year']
                    value_cols = [col for col in act_df.columns if col not in id_cols]
                    act_df = act_df.melt(id_vars=id_cols, value_vars=value_cols,
                                         var_name='technology', value_name='value')
                    act_df['value'] = act_df['value'] * 1000000
                    act_df['year_act'] = act_df['year']
                    act_df['node'] = 'World'
                    act_df['mode'] = 'M1'
                    act_df['time'] = 'year'
                    act_param = Parameter('ACT_synthetic', act_df, {'result_type': 'variable'})
                    break

            if not act_param:
                raise ValueError("Neither ACT nor electricity generation parameters found")

        act_df = act_param.df[act_param.df['technology'].isin(elec_techs)].copy()

        if 'node' not in act_df.columns:
            act_df['node'] = 'World'

        gen_total = act_df.groupby(['node', 'year_act', 'technology'])['value'].sum().reset_index(name='total_gen_MWh')
        gen_total = gen_total[gen_total['total_gen_MWh'] > 0.001].copy()

        active_techs = gen_total['technology'].unique()
        act_df = act_df[act_df['technology'].isin(active_techs)].copy()

        # Use input cost scenario if available, else use simplified costs
        has_detailed_costs = False
        cost_scenario = None

        if input_cost_scenario is not None:
            cost_scenario = input_cost_scenario
            has_detailed_costs = True

        # Initialize empty cost frames
        vom_total = pd.DataFrame(columns=['node', 'year_act', 'technology', 'cost_vom_total'])
        fom_total = pd.DataFrame(columns=['node', 'year_act', 'technology', 'cost_fom_total'])
        fuel_total = pd.DataFrame(columns=['node', 'year_act', 'technology', 'cost_fuel_total'])
        em_total = pd.DataFrame(columns=['node', 'year_act', 'technology', 'cost_em_total'])
        capex_total = pd.DataFrame(columns=['node', 'year_act', 'technology', 'cost_capex_total'])

        if has_detailed_costs and cost_scenario:
            capex_total = ElectricityAnalyzer._calculate_capex_costs_static(
                cost_scenario, elec_techs, interest_rate
            )

        final_df = gen_total.copy()
        cost_cols = ['cost_capex_total', 'cost_fom_total', 'cost_vom_total', 'cost_fuel_total', 'cost_em_total']
        for col in cost_cols:
            final_df[col] = 0.0

        cost_dfs = [
            ('capex', capex_total),
            ('fom', fom_total),
            ('vom', vom_total),
            ('fuel', fuel_total),
            ('em', em_total)
        ]

        for cost_type, df in cost_dfs:
            if not df.empty and len(df) > 0:
                col_name = f'cost_{cost_type}_total'
                merge_df = df[['node', 'year_act', 'technology', col_name]].copy()
                final_df = pd.merge(final_df, merge_df, on=['node', 'year_act', 'technology'],
                                    how='left', suffixes=('', '_new'))
                final_df[col_name] = final_df[f'{col_name}_new'].fillna(final_df[col_name])
                final_df = final_df.drop(columns=[f'{col_name}_new'])

        for col in cost_cols:
            unit_col = col.replace('cost_', 'Unit_').replace('_total', '')
            final_df[unit_col] = final_df[col] / final_df['total_gen_MWh']

        unit_cost_cols = [col for col in final_df.columns if col.startswith('Unit_')]
        final_df['Unit_Total_LCOE_Proxy'] = final_df[unit_cost_cols].sum(axis=1)

        return final_df

    @staticmethod
    def _calculate_capex_costs_static(
        scenario: ScenarioData, elec_techs: list, interest_rate: float
    ) -> pd.DataFrame:
        """Calculate annualized capital costs (static version for use without self)."""
        cap_new_param = scenario.get_parameter('CAP_NEW')
        inv_cost_param = scenario.get_parameter('investment_cost')
        lifetime_param = scenario.get_parameter('technical_lifetime')
        hist_cap_param = scenario.get_parameter('historical_new_capacity')

        if not cap_new_param or not inv_cost_param or not lifetime_param:
            return pd.DataFrame(columns=['node', 'year_act', 'technology', 'cost_capex_total'])

        capex_df = pd.merge(cap_new_param.df, inv_cost_param.df,
                            on=['node', 'technology', 'year_vtg'],
                            how='inner', suffixes=('_cap', '_cost'))

        lifetime_df = lifetime_param.df.copy()
        capex_df = pd.merge(capex_df, lifetime_df, on=['node', 'technology', 'year_vtg'], how='left')

        if 'lifetime' not in capex_df.columns:
            capex_df['lifetime'] = 30
        else:
            capex_df['lifetime'] = capex_df['lifetime'].fillna(30)

        capex_df['crf'] = capex_df.apply(
            lambda row: ElectricityAnalyzer._calculate_crf(interest_rate, row['lifetime']), axis=1
        )
        capex_df['overnight_cost'] = capex_df['value_cap'] * capex_df['value_cost']
        capex_df['annualized_inv_cost_stream'] = capex_df['overnight_cost'] * capex_df['crf']

        historical_capex = pd.DataFrame()
        if hist_cap_param and not hist_cap_param.df.empty:
            hist_df = hist_cap_param.df.copy()
            hist_df = pd.merge(hist_df, inv_cost_param.df,
                               left_on=['node', 'technology', 'year_vtg'],
                               right_on=['node', 'technology', 'year_vtg'],
                               how='inner', suffixes=('_hist', '_cost'))
            hist_df = pd.merge(hist_df, lifetime_df, on=['node', 'technology', 'year_vtg'], how='left')

            if 'lifetime' not in hist_df.columns:
                hist_df['lifetime'] = 30
            else:
                hist_df['lifetime'] = hist_df['lifetime'].fillna(30)

            hist_df['crf'] = hist_df.apply(
                lambda row: ElectricityAnalyzer._calculate_crf(interest_rate, row['lifetime']), axis=1
            )
            hist_df['overnight_cost'] = hist_df['value_hist'] * hist_df['value_cost']
            hist_df['annualized_inv_cost_stream'] = hist_df['overnight_cost'] * hist_df['crf']

            min_year = scenario.options.get('MinYear', 2020)
            max_year = scenario.options.get('MaxYear', 2050)
            if 'year' in scenario.sets:
                model_years = sorted(scenario.sets['year'].tolist())
            else:
                model_years = list(range(min_year, max_year + 1))

            expanded_hist_capex = []
            for _, row in hist_df.iterrows():
                vtg = row['year_vtg']
                life = row['lifetime']
                stream_cost = row['annualized_inv_cost_stream']
                active_years = [y for y in model_years if vtg <= y < vtg + life]
                for year_act in active_years:
                    expanded_hist_capex.append({
                        'node': row['node'],
                        'technology': row['technology'],
                        'year_act': year_act,
                        'cost_capex_total': stream_cost
                    })

            historical_capex = pd.DataFrame(expanded_hist_capex)

        min_year = scenario.options.get('MinYear', 2020)
        max_year = scenario.options.get('MaxYear', 2050)
        if 'year' in scenario.sets:
            model_years = sorted(scenario.sets['year'].tolist())
        else:
            model_years = list(range(min_year, max_year + 1))

        expanded_capex = []
        for _, row in capex_df.iterrows():
            vtg = row['year_vtg']
            life = row['lifetime']
            stream_cost = row['annualized_inv_cost_stream']
            active_years = [y for y in model_years if vtg <= y < vtg + life]
            for year_act in active_years:
                expanded_capex.append({
                    'node': row['node'],
                    'technology': row['technology'],
                    'year_act': year_act,
                    'cost_capex_total': stream_cost
                })

        capex_long_df = pd.DataFrame(expanded_capex)

        if not historical_capex.empty:
            capex_long_df = pd.concat([capex_long_df, historical_capex], ignore_index=True)

        if not capex_long_df.empty:
            return capex_long_df.groupby(['node', 'year_act', 'technology'])['cost_capex_total'].sum().reset_index()
        else:
            return pd.DataFrame(columns=['node', 'year_act', 'technology', 'cost_capex_total'])
