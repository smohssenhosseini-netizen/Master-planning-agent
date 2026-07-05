import json
import math
import re
import html
from io import BytesIO

from openai import OpenAI

import altair as alt
import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="AI Master Planning Optimization Agent", layout="wide")

SAVED_INPUTS_FILE = Path(__file__).parent / "saved_inputs.json"
INPUT_CELLS = {
    "cost_luxury": "B5", "cost_semi": "B6", "cost_apartment": "B7", "cost_mixed": "B8",
    "marketing_cost_pct": "B9", "soft_cost_pct": "B10",
    "price_luxury": "B11", "price_semi": "B12", "price_apartment": "B13", "price_mixed": "B14",
    "cashflow_luxury": "B17", "cashflow_semi": "B18", "cashflow_apartment": "B19", "cashflow_mixed": "B20",
    "prob_luxury": "B30", "prob_semi": "B31", "prob_apartment": "B32", "prob_mixed": "B33",
    "profit_weight": "B36", "cashflow_weight": "B37", "prob_weight": "B38",
    "total_land_area": "B41", "road_pct": "B43", "walkway_pct": "B44", "green_pct": "B45", "micromobility_pct": "B46",
    "luxury_plot": "B50", "luxury_footprint": "B51", "luxury_gfa": "B52", "luxury_builtup": "B53",
    "apt_parking_area": "B56", "apt_parking_stories": "B57", "apt_common_floors": "B58", "apt_res_floors": "B59",
    "apt_buildings": "B60", "apt_unit_area": "B61", "apt_visitor_parking_pct": "B62",
    "semi_plot": "B65", "semi_footprint": "B66", "semi_gfa": "B67", "semi_builtup": "B68",
    "mixed_parking_area": "B71", "mixed_parking_stories": "B72", "mixed_commercial_floors": "B73",
    "mixed_commercial_units_per_floor": "B74", "mixed_res_floors": "B75",
    "mixed_commercial_unit_area": "B76", "mixed_res_unit_area": "B77",
    # Apartment parking and unit mix
    "apt_parking_1bhk": "E56",
    "apt_parking_2bhk": "E57",
    "apt_parking_3bhk": "E58",
    "apt_parking_4bhk": "E59",
    "apt_pct_1bhk": "E60",
    "apt_pct_2bhk": "E61",
    "apt_pct_3bhk": "E62",
    "apt_pct_4bhk": "E63",

    # Business Center parking and unit mix
    "mixed_parking_commercial_unit": "E71",
    "mixed_parking_1bhk": "E72",
    "mixed_parking_2bhk": "E73",
    "mixed_parking_3bhk": "E74",
    "mixed_parking_4bhk": "E75",
    "mixed_pct_1bhk": "E76",
    "mixed_pct_2bhk": "E77",
    "mixed_pct_3bhk": "E78",
    "mixed_pct_4bhk": "E79",
    "mixed_visitor_parking_pct": "B78",
    "construction_pace_luxury": "G5",
    "construction_pace_semi": "G6",
    "construction_pace_apartment": "G7",
    "construction_pace_mixed": "G8",
    "construction_pace_infrastructure": "G9",
    "absorption_luxury_per_month": "G11",
    "absorption_semi_per_month": "G12",
    "absorption_apartment_per_month": "G13",
    "absorption_commercial_per_month": "G14",
    "absorption_office_per_month": "G15",
}

CASHFLOW_OPTIONS = ["Late", "Slow", "Normal", "Semi-Fast", "Fast"]

DEFAULT_INPUTS = {
    "cost_luxury": 350.0,
    "cost_semi": 350.0,
    "cost_apartment": 550.0,
    "cost_mixed": 800.0,
    "marketing_cost_pct": 0.0,
    "soft_cost_pct": 0.0,
    "price_luxury": 925.0,
    "price_semi": 850.0,
    "price_apartment": 900.0,
    "price_mixed": 801.0,
    "cashflow_luxury": "Semi-Fast",
    "cashflow_semi": "Normal",
    "cashflow_apartment": "Fast",
    "cashflow_mixed": "Slow",
    "prob_luxury": 0.85,
    "prob_semi": 0.85,
    "prob_apartment": 0.90,
    "prob_mixed": 0.70,
    "profit_weight": 0.50,
    "cashflow_weight": 0.35,
    "prob_weight": 0.15,
    "total_land_area": 54854.0,
    "road_pct": 0.18,
    "walkway_pct": 0.06,
    "green_pct": 0.10,
    "micromobility_pct": 0.12,
    "luxury_plot": 480.0,
    "luxury_footprint": 150.0,
    "luxury_gfa": 264.0,
    "luxury_builtup": 300.0,
    "apt_parking_area": 43.2,
    "apt_parking_stories": 1.0,
    "apt_common_floors": 1.0,
    "apt_res_floors": 4.0,
    "apt_buildings": 4.0,
    "apt_unit_area": 80.0,
    "apt_visitor_parking_pct": 0.20,
    "semi_plot": 230.0,
    "semi_footprint": 87.0,
    "semi_gfa": 140.0,
    "semi_builtup": 162.0,
    "mixed_parking_area": 43.2,
    "mixed_parking_stories": 2.0,
    "mixed_commercial_floors": 2.0,
    "mixed_commercial_units_per_floor": 25.0,
    "mixed_res_floors": 4.0,
    "mixed_commercial_unit_area": 50.0,
    "mixed_res_unit_area": 140.0,
    "apt_parking_1bhk": 1.0,
    "apt_parking_2bhk": 1.0,
    "apt_parking_3bhk": 2.0,
    "apt_parking_4bhk": 2.0,
    "apt_pct_1bhk": 0.60,
    "apt_pct_2bhk": 0.40,
    "apt_pct_3bhk": 0.0,
    "apt_pct_4bhk": 0.0,
    "mixed_parking_commercial_unit": 1.0,
    "mixed_parking_1bhk": 1.0,
    "mixed_parking_2bhk": 1.0,
    "mixed_parking_3bhk": 2.0,
    "mixed_parking_4bhk": 2.0,
    "mixed_pct_1bhk": 0.0,
    "mixed_pct_2bhk": 0.0,
    "mixed_pct_3bhk": 0.60,
    "mixed_pct_4bhk": 0.40,
    "mixed_visitor_parking_pct": 1.0,
    "construction_pace_luxury": 100.0,
    "construction_pace_semi": 100.0,
    "construction_pace_apartment": 130.0,
    "construction_pace_mixed": 130.0,
    "construction_pace_infrastructure": 1000.0,
    "absorption_luxury_per_month": 1.0,
    "absorption_semi_per_month": 2.0,
    "absorption_apartment_per_month": 12.0,
    "absorption_commercial_per_month": 3.0,
    "absorption_office_per_month": 2.0,
}


def safe_number(value, fallback=0.0):
    return fallback if value is None else float(value)


def cashflow_index(value):
    return CASHFLOW_OPTIONS.index(value) if value in CASHFLOW_OPTIONS else 2


def load_default_inputs():
    return DEFAULT_INPUTS.copy()


def safe_div(numerator, denominator, fallback=0.0):
    return fallback if denominator in (None, 0) else numerator / denominator


def rounddown(value):
    return math.floor(value)


def roundup(value):
    return math.ceil(value)


def cashflow_score(value):
    return {
        "Late": 1.0,
        "Slow": 2.0,
        "Normal": 3.0,
        "Semi-Fast": 4.0,
        "Fast": 5.0,
    }.get(value, 3.0)


def cashflow_start_factor(value):
    return {
        "Fast": 0.10,
        "Semi-Fast": 0.20,
        "Normal": 0.35,
        "Slow": 0.55,
        "Late": 1.00,
    }.get(value, 0.35)


def build_monthly_cashflow(d, result_values):
    components = [
        {
            "name": "Luxury Villas",
            "start_month": 1,
            "capex": result_values["capex_luxury"],
            "revenue": result_values["revenue_luxury"],
            "units": result_values["luxury_units"],
            "construction_workload": result_values["builtup_luxury"],
            "construction_pace": d["construction_pace_luxury"],
            "absorption_per_month": d["absorption_luxury_per_month"],
            "cashflow": d["cashflow_luxury"],
        },
        {
            "name": "Semi-detached Villas",
            "start_month": 1,
            "capex": result_values["capex_semi"],
            "revenue": result_values["revenue_semi"],
            "units": result_values["semi_units"],
            "construction_workload": result_values["builtup_semi"],
            "construction_pace": d["construction_pace_semi"],
            "absorption_per_month": d["absorption_semi_per_month"],
            "cashflow": d["cashflow_semi"],
        },
        {
            "name": "Apartments",
            "start_month": 4,
            "capex": result_values["capex_apartments"],
            "revenue": result_values["revenue_apartments"],
            "units": result_values["apartments_total_units"],
            "construction_workload": result_values["builtup_apartments"],
            "construction_pace": d["construction_pace_apartment"],
            "absorption_per_month": d["absorption_apartment_per_month"],
            "cashflow": d["cashflow_apartment"],
        },
        {
            "name": "Business Center",
            "start_month": 10,
            "capex": result_values["capex_mixed"],
            "revenue": result_values["revenue_mixed"],
            "units": result_values["mixed_commercial_units"] + result_values["mixed_Office_units"],
            "construction_workload": result_values["builtup_mixed"],
            "construction_pace": d["construction_pace_mixed"],
            "absorption_per_month": d["absorption_commercial_per_month"] + d["absorption_office_per_month"],
            "cashflow": d["cashflow_mixed"],
        },
        {
            "name": "Infrastructure",
            "start_month": 1,
            "capex": result_values["infrastructure_cost"],
            "revenue": 0,
            "units": 0,
            "construction_workload": result_values["gfa_total"],
            "construction_pace": d["construction_pace_infrastructure"],
            "absorption_per_month": 0,
            "cashflow": "Normal",
        },
    ]

    planned = []
    for component in components:
        construction_months = max(
            1,
            int(math.ceil(safe_div(component["construction_workload"], component["construction_pace"], 1))),
        )
        absorption_months = 0
        if component["revenue"] > 0 and component["units"] > 0:
            absorption_months = max(
                1,
                int(math.ceil(safe_div(component["units"], component["absorption_per_month"], 1))),
            )
        duration_months = max(construction_months, absorption_months or 0)
        construction_start = component["start_month"]
        construction_end = construction_start + duration_months - 1
        revenue_start = construction_start + int(math.floor(duration_months * cashflow_start_factor(component["cashflow"])))
        revenue_end = revenue_start + absorption_months - 1 if absorption_months else 0
        planned.append(
            {
                **component,
                "construction_months": construction_months,
                "absorption_months": absorption_months,
                "duration_months": duration_months,
                "construction_start": construction_start,
                "construction_end": construction_end,
                "revenue_start": revenue_start,
                "revenue_end": revenue_end,
            }
        )

    construction_completion = max(component["construction_end"] for component in planned if component["capex"] > 0)
    revenue_completion = max([component["revenue_end"] for component in planned if component["revenue_end"] > 0] or [0])
    estimated_completion = max(construction_completion, revenue_completion)
    typology_durations = {
        component["name"]: component["duration_months"]
        for component in planned
        if component["capex"] > 0
    }

    monthly = []
    cumulative_net = 0
    peak_funding_gap = 0
    for month in range(1, estimated_completion + 1):
        cost_outflow = 0
        revenue_inflow = 0
        for component in planned:
            if component["capex"] > 0 and component["construction_start"] <= month <= component["construction_end"]:
                cost_outflow += safe_div(component["capex"], component["duration_months"])
            if component["revenue"] > 0 and component["revenue_start"] <= month <= component["revenue_end"]:
                revenue_inflow += safe_div(component["revenue"], component["absorption_months"])
        net_cashflow = revenue_inflow - cost_outflow
        cumulative_net += net_cashflow
        peak_funding_gap = min(peak_funding_gap, cumulative_net)
        monthly.append(
            {
                "Month": month,
                "Construction Cost": cost_outflow,
                "Revenue": revenue_inflow,
                "Net Cashflow": net_cashflow,
                "Cumulative Cashflow": cumulative_net,
            }
        )

    return {
        "construction_completion_months": construction_completion,
        "revenue_completion_months": revenue_completion,
        "estimated_completion_months": estimated_completion,
        "total_duration_months": estimated_completion,
        "typology_durations": typology_durations,
        "peak_funding_gap": abs(peak_funding_gap),
        "cashflow_monthly": monthly,
    }


def run_python_model(data):
    d = {**DEFAULT_INPUTS, **data}

    sellable_land_use_area = (
        1
        - d["road_pct"]
        - d["walkway_pct"]
        - d["green_pct"]
        - d["micromobility_pct"]
    )

    cost_uplift_factor = 1 + safe_number(d["marketing_cost_pct"]) / 100 + safe_number(d["soft_cost_pct"]) / 100
    effective_cost_luxury = d["cost_luxury"] * cost_uplift_factor
    effective_cost_semi = d["cost_semi"] * cost_uplift_factor
    effective_cost_apartment = d["cost_apartment"] * cost_uplift_factor
    effective_cost_mixed = d["cost_mixed"] * cost_uplift_factor

    profit_luxury_score_base = safe_div(d["price_luxury"] - d["cost_luxury"], d["price_luxury"])
    profit_semi_score_base = safe_div(d["price_semi"] - d["cost_semi"], d["price_semi"])
    profit_apartments_score_base = safe_div(d["price_apartment"] - d["cost_apartment"], d["price_apartment"])
    profit_mixed_score_base = safe_div(d["price_mixed"] - d["cost_mixed"], d["price_mixed"])
    max_profit_score_base = max(
        profit_luxury_score_base,
        profit_semi_score_base,
        profit_apartments_score_base,
        profit_mixed_score_base,
    )

    profit_luxury_score = safe_div(profit_luxury_score_base, max_profit_score_base) * 5
    profit_semi_score = safe_div(profit_semi_score_base, max_profit_score_base) * 5
    profit_apartments_score = safe_div(profit_apartments_score_base, max_profit_score_base) * 5
    profit_mixed_score = safe_div(profit_mixed_score_base, max_profit_score_base) * 5

    cashflow_luxury_score = 0 if profit_luxury_score_base < 0.2 else cashflow_score(d["cashflow_luxury"])
    cashflow_semi_score = 0 if profit_semi_score_base < 0.2 else cashflow_score(d["cashflow_semi"])
    cashflow_apartments_score = 0 if profit_apartments_score_base < 0.2 else cashflow_score(d["cashflow_apartment"])
    cashflow_mixed_score = 0 if profit_mixed_score_base < 0.2 else cashflow_score(d["cashflow_mixed"])

    max_probability = max(d["prob_luxury"], d["prob_semi"], d["prob_apartment"], d["prob_mixed"])
    probability_luxury_score = 0 if profit_luxury_score_base < 0.2 else safe_div(d["prob_luxury"], max_probability) * 5
    probability_semi_score = 0 if profit_semi_score_base < 0.2 else safe_div(d["prob_semi"], max_probability) * 5
    probability_apartments_score = 0 if profit_apartments_score_base < 0.2 else safe_div(d["prob_apartment"], max_probability) * 5
    probability_mixed_score = 0 if profit_mixed_score_base < 0.2 else safe_div(d["prob_mixed"], max_probability) * 5

    overall_luxury = (
        profit_luxury_score * d["profit_weight"]
        + cashflow_luxury_score * d["cashflow_weight"]
        + probability_luxury_score * d["prob_weight"]
    )
    overall_semi = (
        profit_semi_score * d["profit_weight"]
        + cashflow_semi_score * d["cashflow_weight"]
        + probability_semi_score * d["prob_weight"]
    )
    overall_apartments = (
        profit_apartments_score * d["profit_weight"]
        + cashflow_apartments_score * d["cashflow_weight"]
        + probability_apartments_score * d["prob_weight"]
    )
    overall_mixed = (
        profit_mixed_score * d["profit_weight"]
        + cashflow_mixed_score * d["cashflow_weight"]
        + probability_mixed_score * d["prob_weight"]
    )
    overall_total = overall_luxury + overall_semi + overall_apartments + overall_mixed

    allocation_luxury = safe_div(overall_luxury, overall_total) * sellable_land_use_area
    allocation_semi = safe_div(overall_semi, overall_total) * sellable_land_use_area
    allocation_apartments = safe_div(overall_apartments, overall_total) * sellable_land_use_area
    allocation_mixed = safe_div(overall_mixed, overall_total) * sellable_land_use_area

    luxury_land = allocation_luxury * d["total_land_area"]
    luxury_units = rounddown(safe_div(luxury_land, d["luxury_plot"]))
    luxury_total_gfa = luxury_units * d["luxury_gfa"]
    luxury_total_builtup = d["luxury_builtup"] * luxury_units

    semi_land = allocation_semi * d["total_land_area"]
    semi_units = rounddown(safe_div(semi_land, d["semi_plot"]))
    semi_total_gfa = semi_units * d["semi_gfa"]
    semi_total_builtup = d["semi_builtup"] * semi_units

    apartments_land = allocation_apartments * d["total_land_area"]
    apt_parking_mix = (
        d["apt_parking_1bhk"] * d["apt_pct_1bhk"]
        + d["apt_parking_2bhk"] * d["apt_pct_2bhk"]
        + d["apt_parking_3bhk"] * d["apt_pct_3bhk"]
        + d["apt_parking_4bhk"] * d["apt_pct_4bhk"]
    )
    apartments_parking_max = rounddown(safe_div(apartments_land, d["apt_parking_area"])) * d["apt_parking_stories"]
    apartments_visitor_parking = roundup(apartments_parking_max - safe_div(apartments_parking_max, 1 + d["apt_visitor_parking_pct"]))
    apartments_parking_no_visitor = apartments_parking_max - apartments_visitor_parking
    apartments_total_units = safe_div(apartments_parking_no_visitor, apt_parking_mix)
    apartments_units_per_floor = safe_div(apartments_total_units, d["apt_buildings"] * d["apt_res_floors"])
    apartments_land_per_building = safe_div(apartments_land, d["apt_buildings"])
    apartments_ground_footprint = safe_div(d["apt_unit_area"] * apartments_units_per_floor, 0.75)
    apartments_sellable_per_building = d["apt_unit_area"] * apartments_total_units
    apartments_gfa_per_building = apartments_ground_footprint * 0.9 * (d["apt_res_floors"] + d["apt_common_floors"])
    apartments_builtup_per_building = apartments_ground_footprint * (d["apt_res_floors"] + d["apt_common_floors"]) + apartments_land_per_building
    apartments_total_gfa = apartments_gfa_per_building * d["apt_buildings"]
    apartments_total_builtup = apartments_builtup_per_building * d["apt_buildings"]

    mixed_land = allocation_mixed * d["total_land_area"]
    mixed_parking_mix = (
        d["mixed_parking_1bhk"] * d["mixed_pct_1bhk"]
        + d["mixed_parking_2bhk"] * d["mixed_pct_2bhk"]
        + d["mixed_parking_3bhk"] * d["mixed_pct_3bhk"]
        + d["mixed_parking_4bhk"] * d["mixed_pct_4bhk"]
    )
    mixed_parking_max = rounddown(safe_div(mixed_land, d["mixed_parking_area"]) * d["mixed_parking_stories"])
    mixed_visitor_parking = roundup(mixed_parking_max - safe_div(mixed_parking_max, 1 + d["mixed_visitor_parking_pct"]))
    mixed_parking_commercial = mixed_parking_max - mixed_visitor_parking
    mixed_commercial_units = 0 if d["mixed_commercial_floors"] * d["mixed_commercial_units_per_floor"] > mixed_parking_commercial else d["mixed_commercial_floors"] * d["mixed_commercial_units_per_floor"]
    mixed_res_units_raw = rounddown(safe_div(mixed_parking_commercial - mixed_commercial_units * d["mixed_parking_commercial_unit"], d["mixed_res_floors"] * mixed_parking_mix))
    mixed_res_units_avg = 0 if mixed_res_units_raw < 0 else mixed_res_units_raw
    mixed_Office_units = mixed_res_units_avg * d["mixed_res_floors"]
    mixed_commercial_sellable = d["mixed_commercial_unit_area"] * mixed_commercial_units
    mixed_Office_sellable = d["mixed_res_unit_area"] * mixed_Office_units
    mixed_ground_footprint = max(
        safe_div(mixed_commercial_units, d["mixed_commercial_floors"]) * d["mixed_commercial_unit_area"] * 2,
        safe_div(d["mixed_res_unit_area"] * mixed_res_units_avg, 0.75),
    )
    mixed_total_gfa = (
        mixed_ground_footprint * d["mixed_commercial_floors"]
        + safe_div(d["mixed_res_unit_area"] * mixed_res_units_avg, 0.75) * d["mixed_res_floors"]
    ) * 0.9
    mixed_total_builtup = mixed_ground_footprint * (d["mixed_res_floors"] + d["mixed_commercial_floors"]) + mixed_land

    gfa_luxury = luxury_total_gfa
    gfa_semi = semi_total_gfa
    gfa_apartments = apartments_total_gfa
    gfa_mixed = mixed_total_gfa
    gfa_total = gfa_luxury + gfa_semi + gfa_apartments + gfa_mixed

    builtup_luxury = luxury_total_builtup
    builtup_semi = semi_total_builtup
    builtup_apartments = apartments_total_builtup
    builtup_mixed = mixed_total_builtup
    builtup_total = builtup_luxury + builtup_semi + builtup_apartments + builtup_mixed

    capex_luxury = gfa_luxury * effective_cost_luxury
    capex_semi = gfa_semi * effective_cost_semi
    capex_apartments = gfa_apartments * effective_cost_apartment
    capex_mixed = gfa_mixed * effective_cost_mixed
    infrastructure_cost = gfa_total * (90 + 60) * cost_uplift_factor
    capex_total = capex_luxury + capex_semi + capex_apartments + capex_mixed + infrastructure_cost

    revenue_luxury = gfa_luxury * d["price_luxury"]
    revenue_semi = gfa_semi * d["price_semi"]
    revenue_apartments = gfa_apartments * d["price_apartment"]
    revenue_mixed = gfa_mixed * d["price_mixed"]
    revenue_total = revenue_luxury + revenue_semi + revenue_apartments + revenue_mixed

    profit_luxury = safe_div(revenue_luxury - capex_luxury, revenue_luxury)
    profit_semi = safe_div(revenue_semi - capex_semi, revenue_semi)
    profit_apartments = safe_div(revenue_apartments - capex_apartments, revenue_apartments)
    profit_mixed = safe_div(revenue_mixed - capex_mixed, revenue_mixed)
    profit_general = safe_div(revenue_total - capex_total, revenue_total)

    delivery_cashflow = build_monthly_cashflow(
        d,
        {
            "capex_luxury": capex_luxury,
            "capex_semi": capex_semi,
            "capex_apartments": capex_apartments,
            "capex_mixed": capex_mixed,
            "infrastructure_cost": infrastructure_cost,
            "revenue_luxury": revenue_luxury,
            "revenue_semi": revenue_semi,
            "revenue_apartments": revenue_apartments,
            "revenue_mixed": revenue_mixed,
            "luxury_units": luxury_units,
            "semi_units": semi_units,
            "apartments_total_units": apartments_total_units,
            "mixed_commercial_units": mixed_commercial_units,
            "mixed_Office_units": mixed_Office_units,
            "builtup_luxury": builtup_luxury,
            "builtup_semi": builtup_semi,
            "builtup_apartments": builtup_apartments,
            "builtup_mixed": builtup_mixed,
            "gfa_total": gfa_total,
        },
    )

    return {
        "sellable_land_use_area": sellable_land_use_area,
        "gfa_luxury": gfa_luxury,
        "gfa_semi": gfa_semi,
        "gfa_apartments": gfa_apartments,
        "gfa_mixed": gfa_mixed,
        "gfa_total": gfa_total,
        "builtup_luxury": builtup_luxury,
        "builtup_semi": builtup_semi,
        "builtup_apartments": builtup_apartments,
        "builtup_mixed": builtup_mixed,
        "builtup_total": builtup_total,
        "allocation_luxury": allocation_luxury,
        "allocation_semi": allocation_semi,
        "allocation_apartments": allocation_apartments,
        "allocation_mixed": allocation_mixed,
        "luxury_land": luxury_land,
        "luxury_units": luxury_units,
        "luxury_total_gfa": luxury_total_gfa,
        "luxury_total_builtup": luxury_total_builtup,
        "apartments_land": apartments_land,
        "apartments_parking_max": apartments_parking_max,
        "apartments_visitor_parking": apartments_visitor_parking,
        "apartments_parking_no_visitor": apartments_parking_no_visitor,
        "apartments_total_units": apartments_total_units,
        "apartments_buildings": d["apt_buildings"],
        "apartments_res_floors": d["apt_res_floors"],
        "apartments_units_per_floor": apartments_units_per_floor,
        "apartments_land_per_building": apartments_land_per_building,
        "apartments_ground_footprint": apartments_ground_footprint,
        "apartments_sellable_per_building": apartments_sellable_per_building,
        "apartments_gfa_per_building": apartments_gfa_per_building,
        "apartments_builtup_per_building": apartments_builtup_per_building,
        "apartments_total_gfa": apartments_total_gfa,
        "apartments_total_builtup": apartments_total_builtup,
        "semi_land": semi_land,
        "semi_units": semi_units,
        "semi_total_gfa": semi_total_gfa,
        "semi_total_builtup": semi_total_builtup,
        "mixed_land": mixed_land,
        "mixed_parking_max": mixed_parking_max,
        "mixed_visitor_parking": mixed_visitor_parking,
        "mixed_parking_commercial": mixed_parking_commercial,
        "mixed_res_units_avg": mixed_res_units_avg,
        "mixed_commercial_units": mixed_commercial_units,
        "mixed_Office_units": mixed_Office_units,
        "mixed_commercial_sellable": mixed_commercial_sellable,
        "mixed_Office_sellable": mixed_Office_sellable,
        "mixed_ground_footprint": mixed_ground_footprint,
        "mixed_total_gfa": mixed_total_gfa,
        "mixed_total_builtup": mixed_total_builtup,
        "capex_luxury": capex_luxury,
        "capex_semi": capex_semi,
        "capex_apartments": capex_apartments,
        "capex_mixed": capex_mixed,
        "infrastructure_cost": infrastructure_cost,
        "capex_total": capex_total,
        "revenue_luxury": revenue_luxury,
        "revenue_semi": revenue_semi,
        "revenue_apartments": revenue_apartments,
        "revenue_mixed": revenue_mixed,
        "revenue_total": revenue_total,
        "profit_luxury": profit_luxury,
        "profit_semi": profit_semi,
        "profit_apartments": profit_apartments,
        "profit_mixed": profit_mixed,
        "profit_general": profit_general,
        **delivery_cashflow,
    }


def apply_defaults(defaults):
    for key, value in defaults.items():
        st.session_state[key] = value


def collect_data():
    return {key: st.session_state[key] for key in INPUT_CELLS.keys()}
def save_current_inputs():
    data = collect_data()
    data["project_name"] = st.session_state.project_name
    data["location"] = st.session_state.location
    st.session_state.defaults = data.copy()
    st.session_state.saved_inputs_session = data
    try:
        with open(SAVED_INPUTS_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception:
        pass


def load_saved_inputs():
    saved_inputs = st.session_state.get("saved_inputs_session")
    if saved_inputs:
        return saved_inputs
    if SAVED_INPUTS_FILE.exists():
        try:
            with open(SAVED_INPUTS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return None
    return None

def apply_ai_suggestion(approach):
    if approach == "Balanced":
        st.session_state.profit_weight = 0.40
        st.session_state.cashflow_weight = 0.30
        st.session_state.prob_weight = 0.30
    elif approach == "Maximize Profitability":
        st.session_state.profit_weight = 0.60
        st.session_state.cashflow_weight = 0.20
        st.session_state.prob_weight = 0.20
    elif approach == "Fast Cashflow":
        st.session_state.profit_weight = 0.25
        st.session_state.cashflow_weight = 0.55
        st.session_state.prob_weight = 0.20
        st.session_state.cashflow_apartment = "Fast"
        st.session_state.cashflow_mixed = "Semi-Fast"
    elif approach == "Highest Salability":
        st.session_state.profit_weight = 0.25
        st.session_state.cashflow_weight = 0.25
        st.session_state.prob_weight = 0.50
        st.session_state.prob_luxury = 0.70
        st.session_state.prob_semi = 0.85
        st.session_state.prob_apartment = 0.90
        st.session_state.prob_mixed = 0.75


def fmt(value, unit=""):
    if value is None:
        return "-"
    return f"{value:,.0f}{unit}"


def get_optional_secret(name):
    try:
        return st.secrets[name]
    except Exception:
        return ""


def require_password():
    app_password = str(get_optional_secret("APP_PASSWORD") or "").strip()
    if not app_password or st.session_state.get("authenticated", False):
        return

    st.title("AI Master Planning Optimization Agent")
    st.caption("Enter the access password to continue.")
    entered_password = st.text_input("Password", type="password")

    if st.button("Enter", type="primary"):
        if entered_password == app_password:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password.")

    st.stop()


def nav_button(label, page_name):
    active = st.session_state.page == page_name

    if active:
        st.sidebar.markdown(
            f"""
            <div style="
                background-color:rgba(30, 64, 175, 0.35);
                border-left:4px solid #60a5fa;
                color:#f8fafc;
                padding:0.65rem 0.85rem;
                border-radius:0.35rem;
                font-weight:600;
                margin-bottom:0.35rem;
            ">
                {label}
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        if st.sidebar.button(label, use_container_width=True):
            st.session_state.page = page_name
            st.rerun()


if "defaults_loaded" not in st.session_state:

    excel_defaults = load_default_inputs()
    st.session_state.defaults = excel_defaults

    saved_inputs = load_saved_inputs()

    if saved_inputs:
        apply_defaults(saved_inputs)
    else:
        apply_defaults(excel_defaults)
        

    if "project_name" not in st.session_state:
        st.session_state.project_name = saved_inputs.get("project_name", "NH13B - Sarooj Oasis") if saved_inputs else "NH13B - Sarooj Oasis"

    if "location" not in st.session_state:
        st.session_state.location = saved_inputs.get("location", "Muscat, Oman") if saved_inputs else "Muscat, Oman"

    st.session_state.defaults_loaded = True

if "page" not in st.session_state:
    st.session_state.page = "Dashboard"

if "defaults" not in st.session_state:
    st.session_state.defaults = load_default_inputs()

for key, value in DEFAULT_INPUTS.items():
    if key not in st.session_state:
        st.session_state[key] = value
    if key not in st.session_state.defaults:
        st.session_state.defaults[key] = value

if "result" not in st.session_state:
    st.session_state.result = None

if "scenarios" not in st.session_state:
    st.session_state.scenarios = []

if "scenario_ai_review" not in st.session_state:
    st.session_state.scenario_ai_review = ""



st.markdown("""
<style>
.block-container {
    padding-top: 2rem;
    position: relative;
    z-index: 1;
}
h1 {font-size: 42px !important; font-weight: 800 !important;}

h2, h3 {
    font-size: 1.55rem !important;
}

[data-testid="stMetricValue"] {
    font-size: 1.35rem !important;
    font-weight: 700 !important;
    line-height: 1.25 !important;
}

[data-testid="stMetricLabel"] {
    font-size: 0.82rem !important;
    color: rgba(49, 51, 63, 0.72) !important;
}

.delivery-input-label {
    min-height: 4.25rem;
    font-size: 1rem;
    line-height: 1.35;
    font-weight: 500;
    color: var(--text-color);
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    margin-bottom: 0.35rem;
}

.delivery-input-label span {
    font-weight: 400;
}

[data-testid="stHeader"] {
    background: transparent;
}

.advisor-stat-card {
    background: var(--background-color);
    border: 1px solid rgba(128, 128, 128, 0.28);
    border-radius: 14px;
    padding: 10px 14px;
    margin-bottom: 12px;
}

.advisor-muted {
    color: rgba(128, 128, 128, 0.95);
}

.advisor-strong {
    color: var(--text-color);
}

.advisor-divider {
    margin: 4px 0;
    border: 0;
    border-top: 1px solid rgba(128, 128, 128, 0.25);
}

.advisor-section-title {
    font-size: 16px;
    font-weight: 800;
    margin: 4px 0 4px;
}

.advisor-metric {
    margin: 0;
    padding: 2px 0 3px;
}

.advisor-metric-label {
    font-size: 12px;
    margin-bottom: 2px;
}

.advisor-metric-value {
    font-size: 18px;
    font-weight: 700;
    line-height: 1.15;
}

.advisor-caption {
    font-size: 12px;
    line-height: 1.12;
    margin-top: 2px;
}

.advisor-program-list {
    font-size: 12px;
    line-height: 1.25;
}

div[data-testid="stMarkdownContainer"] > .advisor-metric,
div[data-testid="stMarkdownContainer"] > .advisor-section-title {
    margin-top: 0 !important;
    margin-bottom: 0 !important;
}

div[data-testid="stMarkdownContainer"] hr.advisor-divider {
    margin-top: 5px !important;
    margin-bottom: 5px !important;
}

.typology-column-title {
    font-size: 1.12rem;
    font-weight: 800;
    line-height: 1.15;
    margin: 0 0 1rem 0;
    white-space: nowrap;
}

.comparison-card {
    border: 1px solid rgba(128, 128, 128, 0.24);
    border-radius: 12px;
    padding: 14px 16px;
    margin: 8px 0 12px;
    background: rgba(128, 128, 128, 0.04);
}

.comparison-card-title {
    font-size: 15px;
    font-weight: 800;
    margin-bottom: 8px;
}

.comparison-card-value {
    font-size: 24px;
    font-weight: 700;
    line-height: 1.1;
}

.ai-review-panel {
    border: 1px solid rgba(96, 165, 250, 0.35);
    border-left: 4px solid #60a5fa;
    border-radius: 12px;
    padding: 16px 18px;
    background: rgba(96, 165, 250, 0.08);
    line-height: 1.55;
}

.ai-recommendation-panel {
    border: 1px solid rgba(34, 197, 94, 0.35);
    border-left: 4px solid #22c55e;
    border-radius: 12px;
    padding: 14px 16px;
    margin-top: 16px;
    background: rgba(34, 197, 94, 0.08);
}
</style>
""", unsafe_allow_html=True)

require_password()

st.sidebar.title("Project Workspace")
st.sidebar.caption("INPUTS")

nav_button("Project Setup", "Dashboard")
nav_button("Financial Parameters", "Financial")
nav_button("Design Assumptions", "Design")

st.sidebar.divider()

st.sidebar.caption("OUTPUT")

if st.sidebar.button("⚡ Run Optimization", use_container_width=True, type="primary"):
    with st.spinner("Running optimization engine..."):
        st.session_state.result = run_python_model(collect_data())

    st.rerun()

nav_button("Optimization Results", "Results")
nav_button("Scenario Comparison", "Comparison")

st.sidebar.divider()


if st.sidebar.button("💾 Save Current Inputs", use_container_width=True):
    save_current_inputs()
    st.sidebar.success("Inputs saved.")

if st.sidebar.button("↩ Reset to Defaults", use_container_width=True):
    apply_defaults(st.session_state.defaults)
    st.session_state.result = None
    st.session_state.page = "Dashboard"
    st.rerun()














def calculate_strategy_weights(capex_capacity, cash_recovery_need, profit_priority, market_risk_tolerance):
    profit = 0.40
    cashflow = 0.30
    probability = 0.30

    if capex_capacity == "Fully self-funded":
        profit += 0.20
        cashflow -= 0.10
    elif capex_capacity == "Partially funded":
        cashflow += 0.10
    elif capex_capacity == "Dependent on early sales":
        cashflow += 0.25
        profit -= 0.10

    if cash_recovery_need == "Not critical":
        profit += 0.10
        cashflow -= 0.05
    elif cash_recovery_need == "Important":
        cashflow += 0.05
    elif cash_recovery_need == "Critical":
        cashflow += 0.20
        profit -= 0.10

    if profit_priority == "Maximum profit":
        profit += 0.20
        cashflow -= 0.10
    elif profit_priority == "Fast return":
        cashflow += 0.10
        probability += 0.15
        profit -= 0.10

    if market_risk_tolerance == "Low risk only":
        probability += 0.25
        profit -= 0.10
    elif market_risk_tolerance == "Moderate":
        probability += 0.05
    elif market_risk_tolerance == "High":
        profit += 0.10
        probability -= 0.10

    profit = max(profit, 0.05)
    cashflow = max(cashflow, 0.05)
    probability = max(probability, 0.05)

    total = profit + cashflow + probability

    return (
        round(profit / total, 2),
        round(cashflow / total, 2),
        round(probability / total, 2),
    )
















def extract_budget_omr(text):
    text = text.lower().replace(",", "")
    match = re.search(r"(\d+(?:\.\d+)?)\s*(m|mn|million|millions)\b", text)
    if match:
        return float(match.group(1)) * 1_000_000

    match = re.search(r"(\d+(?:\.\d+)?)\s*(k|thousand)\b", text)
    if match:
        return float(match.group(1)) * 1_000

    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:omr|rial|rials)\b", text)
    if match:
        return float(match.group(1))

    return None


def apply_strategy_guardrails(ai_result, project_description):
    text = project_description.lower()
    budget = extract_budget_omr(text)

    weights = {
        "profit_weight": safe_number(ai_result.get("profit_weight"), 0.40),
        "cashflow_weight": safe_number(ai_result.get("cashflow_weight"), 0.30),
        "sale_probability_weight": safe_number(ai_result.get("sale_probability_weight"), 0.30),
    }

    if budget is not None:
        if budget <= 5_000_000:
            weights["cashflow_weight"] += 0.18
            weights["profit_weight"] -= 0.10
            weights["sale_probability_weight"] -= 0.08
            budget_note = "Limited available capital increases the importance of early cash recovery."
        elif budget >= 50_000_000:
            weights["profit_weight"] += 0.12
            weights["cashflow_weight"] -= 0.10
            weights["sale_probability_weight"] -= 0.02
            budget_note = "Strong available capital reduces cashflow pressure and allows more profitability focus."
        else:
            budget_note = "Available capital appears moderate, so the budget has not strongly shifted the weights."
    else:
        budget_note = None

    if "slow sales" in text or "market uncertainty" in text or "absorption" in text:
        weights["sale_probability_weight"] += 0.08
        weights["profit_weight"] -= 0.04
        weights["cashflow_weight"] -= 0.04

    if "balanced profitability and cashflow" in text or "balanced" in text:
        weights["profit_weight"] = (weights["profit_weight"] + 0.35) / 2
        weights["cashflow_weight"] = (weights["cashflow_weight"] + 0.35) / 2

    explanation = ai_result.get("explanation", "")
    if budget_note:
        explanation = f"{budget_note} {explanation}".strip()

    weights["explanation"] = explanation or "Weights were adjusted using the project strategy answers."
    return weights


def normalize_ai_weights(ai_result):
    weights = {
        "profit_weight": safe_number(ai_result.get("profit_weight"), 0.40),
        "cashflow_weight": safe_number(ai_result.get("cashflow_weight"), 0.30),
        "sale_probability_weight": safe_number(ai_result.get("sale_probability_weight"), 0.30),
    }

    weights = {key: min(max(value, 0.05), 0.80) for key, value in weights.items()}
    total = sum(weights.values())

    if total <= 0:
        weights = {
            "profit_weight": 0.40,
            "cashflow_weight": 0.30,
            "sale_probability_weight": 0.30,
        }
        total = 1.0

    normalized = {key: round(value / total, 2) for key, value in weights.items()}
    difference = round(1.0 - sum(normalized.values()), 2)
    largest_key = max(normalized, key=normalized.get)
    normalized[largest_key] = round(normalized[largest_key] + difference, 2)

    normalized["explanation"] = ai_result.get(
        "explanation",
        "Weights were normalized from the AI recommendation so the optimization priorities sum to 1.00.",
    )

    return normalized


def ai_recommend_weights(project_description, capex_capacity, cash_recovery_need, profit_priority, market_risk_tolerance):
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

    prompt = f"""
You are an AI master planning and real estate development advisor.

Recommend optimization weights for a master planning model.

Interpret the free-text project context carefully:
- Increase profit_weight when the client prioritizes maximum profit, premium positioning, long-term value, or accepts higher market risk.
- Increase cashflow_weight when the client mentions early sales, fast capital recovery, limited funding, financing constraints, or construction cash pressure.
- Increase sale_probability_weight when the client mentions low risk, market uncertainty, slow sales, high construction cost concern, or absorption risk.
- Use balanced weights only when the answers are genuinely balanced.
- Each weight must be between 0.05 and 0.80.

The weights must sum to 1.00:
- profit_weight
- cashflow_weight
- sale_probability_weight

Project context:
{project_description}

Developer strategy:
Funding: {capex_capacity}
Capital recovery: {cash_recovery_need}
Business objective: {profit_priority}
Market risk: {market_risk_tolerance}

Return only valid JSON in this exact format:
{{
  "profit_weight": 0.40,
  "cashflow_weight": 0.30,
  "sale_probability_weight": 0.30,
  "explanation": "short explanation"
}}
"""

    response = client.responses.create(
        model="gpt-5.5",
        input=prompt,
    )

    ai_result = json.loads(response.output_text)
    ai_result = apply_strategy_guardrails(ai_result, project_description)
    return normalize_ai_weights(ai_result)


def build_results_excel(result):
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y.%m.%d - %H.%M")
    export_filename = f"{timestamp} - CMP Optimization results.xlsx"

    input_rows = [

        ("Project", "Project Name", st.session_state.project_name),
        ("Project", "Location", st.session_state.location),


    ]

    INPUT_LABELS = {
        "cost_luxury": ("Financial", "Luxury Villas Construction Cost"),
        "cost_semi": ("Financial", "Semi-detached Villas Construction Cost"),
        "cost_apartment": ("Financial", "Apartments Construction Cost"),
        "cost_mixed": ("Financial", "Business Center Construction Cost"),
        "marketing_cost_pct": ("Financial", "Marketing Costs"),
        "soft_cost_pct": ("Financial", "Soft Costs"),

        "price_luxury": ("Financial", "Luxury Villas Selling Price"),
        "price_semi": ("Financial", "Semi-detached Villas Selling Price"),
        "price_apartment": ("Financial", "Apartments Selling Price"),
        "price_mixed": ("Financial", "Business Center Selling Price"),

        "cashflow_luxury": ("Financial", "Luxury Villas Cashflow"),
        "cashflow_semi": ("Financial", "Semi-detached Villas Cashflow"),
        "cashflow_apartment": ("Financial", "Apartments Cashflow"),
        "cashflow_mixed": ("Financial", "Business Center Cashflow"),

        "prob_luxury": ("Financial", "Luxury Villas Sale Probability"),
        "prob_semi": ("Financial", "Semi-detached Villas Sale Probability"),
        "prob_apartment": ("Financial", "Apartments Sale Probability"),
        "prob_mixed": ("Financial", "Business Center Sale Probability"),

        "profit_weight": ("Strategy", "Profitability Weight"),
        "cashflow_weight": ("Strategy", "Cashflow Weight"),
        "prob_weight": ("Strategy", "Sale Probability Weight"),

        "total_land_area": ("Project", "Total Land Area"),

        "road_pct": ("Site Allocation", "Roads"),
        "walkway_pct": ("Site Allocation", "Walkways"),
        "green_pct": ("Site Allocation", "Public Realm / Green Areas"),
        "micromobility_pct": ("Site Allocation", "Micromobility"),

        "luxury_plot": ("Luxury Villas", "Plot Area"),
        "luxury_footprint": ("Luxury Villas", "Footprint"),
        "luxury_gfa": ("Luxury Villas", "GFA per Villa"),
        "luxury_builtup": ("Luxury Villas", "Built-up Area per Villa"),

        "apt_parking_area": ("Apartments", "Required Parking Area per Vehicle"),
        "apt_parking_stories": ("Apartments", "Number of Parking Stories"),
        "apt_common_floors": ("Apartments", "Common / Lobby Floors"),
        "apt_res_floors": ("Apartments", "Residential Floors per Building"),
        "apt_buildings": ("Apartments", "Number of Residential Buildings"),
        "apt_unit_area": ("Apartments", "Average Unit Area"),
        "apt_visitor_parking_pct": ("Apartments", "Visitor Parking Allocation"),

        "apt_parking_1bhk": ("Apartments", "Required Parking per 1-BHK Unit"),
        "apt_parking_2bhk": ("Apartments", "Required Parking per 2-BHK Unit"),
        "apt_parking_3bhk": ("Apartments", "Required Parking per 3-BHK Unit"),
        "apt_parking_4bhk": ("Apartments", "Required Parking per 4-BHK Unit"),
        "apt_pct_1bhk": ("Apartments", "Percentage of 1-BHK Units"),
        "apt_pct_2bhk": ("Apartments", "Percentage of 2-BHK Units"),
        "apt_pct_3bhk": ("Apartments", "Percentage of 3-BHK Units"),
        "apt_pct_4bhk": ("Apartments", "Percentage of 4-BHK Units"),

        "semi_plot": ("Semi-detached Villas", "Plot Area"),
        "semi_footprint": ("Semi-detached Villas", "Footprint"),
        "semi_gfa": ("Semi-detached Villas", "GFA per Villa"),
        "semi_builtup": ("Semi-detached Villas", "Built-up Area per Villa"),

        "mixed_parking_area": ("Business Center", "Required Parking Area per Vehicle"),
        "mixed_parking_stories": ("Business Center", "Number of Parking Stories"),
        "mixed_commercial_floors": ("Business Center", "Number of Commercial Floors"),
        "mixed_commercial_units_per_floor": ("Business Center", "Commercial Units per Floor"),
        "mixed_res_floors": ("Business Center", "Office Floors"),
        "mixed_commercial_unit_area": ("Business Center", "Commercial Unit Area"),
        "mixed_res_unit_area": ("Business Center", "Office Unit Area"),

        "mixed_parking_commercial_unit": ("Business Center", "Required Parking per Commercial Unit"),
        "mixed_parking_1bhk": ("Business Center", "Required Parking per 1-BHK Unit"),
        "mixed_parking_2bhk": ("Business Center", "Required Parking per 2-BHK Unit"),
        "mixed_parking_3bhk": ("Business Center", "Required Parking per 3-BHK Unit"),
        "mixed_parking_4bhk": ("Business Center", "Required Parking per 4-BHK Unit"),
        "mixed_pct_1bhk": ("Business Center", "Percentage of 1-BHK Units"),
        "mixed_pct_2bhk": ("Business Center", "Percentage of 2-BHK Units"),
        "mixed_pct_3bhk": ("Business Center", "Percentage of 3-BHK Units"),
        "mixed_pct_4bhk": ("Business Center", "Percentage of 4-BHK Units"),
        "mixed_visitor_parking_pct": ("Business Center", "Visitor Parking Allocation"),
    }

    for key, value in collect_data().items():
        category, label = INPUT_LABELS.get(key, ("Model Input", key))
        input_rows.append((category, label, value))

    inputs_df = pd.DataFrame(
        input_rows,
        columns=["Category", "Parameter", "Value"]
    )

    executive_summary = pd.DataFrame({
        "Metric": [
            "Investment Required",
            "Expected Revenue",
            "Expected Profit Margin",
            "Total Duration",
            "Peak Funding Gap",
            "Sellable Land Use Percentage",
            "Total GFA",
            "Total Built-up Area",
        ],
        "Value": [
            result["capex_total"],
            result["revenue_total"],
            result["profit_general"],
            result["total_duration_months"],
            result["peak_funding_gap"],
            result["sellable_land_use_area"],
            result["gfa_total"],
            result["builtup_total"],
        ],
    })

    development_mix = pd.DataFrame({
        "Typology": [
            "Luxury Villas",
            "Semi-detached Villas",
            "Apartments",
            "Business Center",
        ],
        "Development Program": [
            f"{result['luxury_units']:,.0f} Villas",
            f"{result['semi_units']:,.0f} Villas",
            f"{result['apartments_buildings']:,.0f} Residential Buildings / {result['apartments_total_units']:,.0f} Units",
            f"{result['mixed_commercial_units']:,.0f} Commercial Units / {result['mixed_Office_units']:,.0f} Office Units",
        ],
        "Allocation %": [
            result["allocation_luxury"],
            result["allocation_semi"],
            result["allocation_apartments"],
            result["allocation_mixed"],
        ],
        "Land Area": [
            result["luxury_land"],
            result["semi_land"],
            result["apartments_land"],
            result["mixed_land"],
        ],
        "GFA": [
            result["gfa_luxury"],
            result["gfa_semi"],
            result["gfa_apartments"],
            result["gfa_mixed"],
        ],
        "Built-up": [
            result["builtup_luxury"],
            result["builtup_semi"],
            result["builtup_apartments"],
            result["builtup_mixed"],
        ],
        "CAPEX": [
            result["capex_luxury"],
            result["capex_semi"],
            result["capex_apartments"],
            result["capex_mixed"],
        ],
        "Revenue": [
            result["revenue_luxury"],
            result["revenue_semi"],
            result["revenue_apartments"],
            result["revenue_mixed"],
        ],
        "Profit %": [
            result["profit_luxury"],
            result["profit_semi"],
            result["profit_apartments"],
            result["profit_mixed"],
        ],
    })

    luxury_details = pd.DataFrame({
        "Output": [
            "Total land area",
            "Maximum possible number of villas",
            "Total GFA",
            "Total built-up area",
        ],
        "Value": [
            result["luxury_land"],
            result["luxury_units"],
            result["luxury_total_gfa"],
            result["luxury_total_builtup"],
        ],
    })

    semi_details = pd.DataFrame({
        "Output": [
            "Total land area",
            "Maximum possible number of villas",
            "Total GFA",
            "Total built-up area",
        ],
        "Value": [
            result["semi_land"],
            result["semi_units"],
            result["semi_total_gfa"],
            result["semi_total_builtup"],
        ],
    })

    apartments_details = pd.DataFrame({
        "Output": [
            "Total Land area",
            "Maximum possible number of Parking spaces",
            "Visitors Parking spaces",
            "Maximum parking spaces excluding visitors",
            "Total number of apartment units",
            "Number of residential buildings",
            "Number of residential floors in each building",
            "Number of units in each floor",
            "Land area for each building",
            "Ground floor footprint",
            "Total sellable area for one building",
            "Total GFA for one building including GF, amenities, and corridors",
            "Total built-up for one building including basement",
            "Total GFA for all apartments",
            "Total built-up for all apartments",
        ],
        "Value": [
            result["apartments_land"],
            result["apartments_parking_max"],
            result["apartments_visitor_parking"],
            result["apartments_parking_no_visitor"],
            result["apartments_total_units"],
            result["apartments_buildings"],
            result["apartments_res_floors"],
            result["apartments_units_per_floor"],
            result["apartments_land_per_building"],
            result["apartments_ground_footprint"],
            result["apartments_sellable_per_building"],
            result["apartments_gfa_per_building"],
            result["apartments_builtup_per_building"],
            result["apartments_total_gfa"],
            result["apartments_total_builtup"],
        ],
    })

    mixed_details = pd.DataFrame({
        "Output": [
            "Total Land area",
            "Maximum possible number of Parking spaces",
            "Visitors Parking spaces",
            "Parking spaces for commercial units",
            "Average number of units in Office floors",
            "Number of commercial units",
            "Number of Office units",
            "Sellable area of commercial units",
            "Sellable area of Office units",
            "Ground floor footprint",
            "Total GFA including amenities and corridors",
            "Total built-up including basement",
        ],
        "Value": [
            result["mixed_land"],
            result["mixed_parking_max"],
            result["mixed_visitor_parking"],
            result["mixed_parking_commercial"],
            result["mixed_res_units_avg"],
            result["mixed_commercial_units"],
            result["mixed_Office_units"],
            result["mixed_commercial_sellable"],
            result["mixed_Office_sellable"],
            result["mixed_ground_footprint"],
            result["mixed_total_gfa"],
            result["mixed_total_builtup"],
        ],
    })

    cashflow_df = cashflow_dataframe(result)

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        inputs_df.to_excel(writer, sheet_name="Project Inputs", index=False)

        executive_summary.to_excel(writer, sheet_name="Executive Summary", index=False)
        development_mix.to_excel(writer, sheet_name="Development Mix", index=False)
        luxury_details.to_excel(writer, sheet_name="Luxury Villas", index=False)
        semi_details.to_excel(writer, sheet_name="Semi Villas", index=False)
        apartments_details.to_excel(writer, sheet_name="Apartments", index=False)
        mixed_details.to_excel(writer, sheet_name="Business Center", index=False)
        cashflow_df.to_excel(writer, sheet_name="Monthly Cashflow", index=False)

    return export_filename, output.getvalue()


def create_scenario_snapshot(name):
    from datetime import datetime

    result = dict(st.session_state.result or {})
    inputs = collect_data()
    strategy = {
        "Investment Strategy": st.session_state.get("ai_investment_strategy", ""),
        "Definition of Success": st.session_state.get("ai_success_definition", ""),
        "Main Concerns": st.session_state.get("ai_main_concerns", ""),
        "Profitability Weight": st.session_state.get("profit_weight", 0),
        "Cashflow Weight": st.session_state.get("cashflow_weight", 0),
        "Sale Probability Weight": st.session_state.get("prob_weight", 0),
    }

    return {
        "name": name.strip(),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "inputs": inputs,
        "strategy": strategy,
        "result": result,
    }


def scenario_comparison_rows(scenarios):
    rows = []
    for scenario in scenarios:
        result = scenario["result"]
        inputs = scenario["inputs"]
        rows.append(
            {
                "Scenario": scenario["name"],
                "Investment (M OMR)": result.get("capex_total", 0) / 1_000_000,
                "Revenue (M OMR)": result.get("revenue_total", 0) / 1_000_000,
                "Profit Margin": result.get("profit_general", 0),
                "Total Duration (months)": result.get("total_duration_months", result.get("estimated_completion_months", 0)),
                "Peak Funding Gap (M OMR)": result.get("peak_funding_gap", 0) / 1_000_000,
                "Sellable Land Use": result.get("sellable_land_use_area", 0),
                "GFA (k sqm)": result.get("gfa_total", 0) / 1000,
                "BUA (k sqm)": result.get("builtup_total", 0) / 1000,
                "Luxury Villas": result.get("luxury_units", 0),
                "Semi Villas": result.get("semi_units", 0),
                "Apartment Buildings": result.get("apartments_buildings", 0),
                "Apartment Units": result.get("apartments_total_units", 0),
                "Commercial Units": result.get("mixed_commercial_units", 0),
                "Office Units": result.get("mixed_Office_units", 0),
                "Apartment Parking Stories": inputs.get("apt_parking_stories", 0),
                "Business Parking Stories": inputs.get("mixed_parking_stories", 0),
            }
        )
    return pd.DataFrame(rows)


def build_scenario_comparison_excel(scenarios, ai_review=""):
    from datetime import datetime

    output = BytesIO()
    comparison_df = scenario_comparison_rows(scenarios)

    detail_rows = []
    for scenario in scenarios:
        result = scenario["result"]
        inputs = scenario["inputs"]
        strategy = scenario["strategy"]
        detail_rows.extend(
            [
                (scenario["name"], "Saved At", scenario["created_at"]),
                (scenario["name"], "Investment Strategy", strategy.get("Investment Strategy", "")),
                (scenario["name"], "Definition of Success", strategy.get("Definition of Success", "")),
                (scenario["name"], "Main Concerns", strategy.get("Main Concerns", "")),
                (scenario["name"], "Profitability Weight", strategy.get("Profitability Weight", "")),
                (scenario["name"], "Cashflow Weight", strategy.get("Cashflow Weight", "")),
                (scenario["name"], "Sale Probability Weight", strategy.get("Sale Probability Weight", "")),
                (scenario["name"], "Luxury Allocation", result.get("allocation_luxury", 0)),
                (scenario["name"], "Semi-detached Allocation", result.get("allocation_semi", 0)),
                (scenario["name"], "Apartments Allocation", result.get("allocation_apartments", 0)),
                (scenario["name"], "Business Center Allocation", result.get("allocation_mixed", 0)),
                (scenario["name"], "Total Duration Months", result.get("total_duration_months", result.get("estimated_completion_months", 0))),
                (scenario["name"], "Peak Funding Gap", result.get("peak_funding_gap", 0)),
                (scenario["name"], "Apartment Parking Stories", inputs.get("apt_parking_stories", 0)),
                (scenario["name"], "Business Center Parking Stories", inputs.get("mixed_parking_stories", 0)),
                (scenario["name"], "Apartment 1-BHK Mix", inputs.get("apt_pct_1bhk", 0)),
                (scenario["name"], "Apartment 2-BHK Mix", inputs.get("apt_pct_2bhk", 0)),
                (scenario["name"], "Apartment 3-BHK Mix", inputs.get("apt_pct_3bhk", 0)),
                (scenario["name"], "Apartment 4-BHK Mix", inputs.get("apt_pct_4bhk", 0)),
            ]
        )

    details_df = pd.DataFrame(detail_rows, columns=["Scenario", "Item", "Value"])
    review_df = pd.DataFrame({"AI Scenario Review": [ai_review]}) if ai_review else pd.DataFrame()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        comparison_df.to_excel(writer, sheet_name="Scenario Comparison", index=False)
        details_df.to_excel(writer, sheet_name="Scenario Details", index=False)
        if not review_df.empty:
            review_df.to_excel(writer, sheet_name="AI Review", index=False)
        for scenario in scenarios:
            cashflow_df = cashflow_dataframe(scenario["result"])
            if not cashflow_df.empty:
                sheet_name = excel_sheet_name(scenario["name"])[:20]
                cashflow_df.to_excel(writer, sheet_name=f"{sheet_name} Cashflow", index=False)

    filename = f"{datetime.now().strftime('%Y.%m.%d - %H.%M')} - Scenario Comparison.xlsx"
    return filename, output.getvalue()


def excel_sheet_name(name):
    cleaned = re.sub(r"[\[\]\:\*\?\/\\]", " ", str(name)).strip()
    return (cleaned or "Scenario")[:25]


def scenario_financial_chart(comparison_df):
    chart_data = comparison_df.melt(
        id_vars=["Scenario"],
        value_vars=["Investment (M OMR)", "Revenue (M OMR)"],
        var_name="Metric",
        value_name="Value",
    )
    return (
        alt.Chart(chart_data)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("Scenario:N", sort=None, title=None),
            y=alt.Y("Value:Q", title="M OMR"),
            color=alt.Color("Metric:N", title=None),
            xOffset="Metric:N",
            tooltip=[
                alt.Tooltip("Scenario:N"),
                alt.Tooltip("Metric:N"),
                alt.Tooltip("Value:Q", format=".1f"),
            ],
        )
        .properties(height=260)
    )


def scenario_yield_chart(comparison_df):
    chart_data = comparison_df.melt(
        id_vars=["Scenario"],
        value_vars=["GFA (k sqm)", "BUA (k sqm)"],
        var_name="Metric",
        value_name="Value",
    )
    return (
        alt.Chart(chart_data)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("Scenario:N", sort=None, title=None),
            y=alt.Y("Value:Q", title="k sqm"),
            color=alt.Color("Metric:N", title=None),
            xOffset="Metric:N",
            tooltip=[
                alt.Tooltip("Scenario:N"),
                alt.Tooltip("Metric:N"),
                alt.Tooltip("Value:Q", format=".1f"),
            ],
        )
        .properties(height=260)
    )


def scenario_profit_chart(comparison_df):
    return (
        alt.Chart(comparison_df)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("Scenario:N", sort=None, title=None),
            y=alt.Y("Profit Margin:Q", title="Profit Margin", axis=alt.Axis(format="%")),
            color=alt.value("#fb4b4b"),
            tooltip=[
                alt.Tooltip("Scenario:N"),
                alt.Tooltip("Profit Margin:Q", format=".1%"),
            ],
        )
        .properties(height=220)
    )


def scenario_allocation_donut(scenario):
    result = scenario["result"]
    chart_data = pd.DataFrame(
        {
            "Typology": ["Luxury Villas", "Semi-detached Villas", "Apartments", "Business Center"],
            "Allocation": [
                result.get("allocation_luxury", 0),
                result.get("allocation_semi", 0),
                result.get("allocation_apartments", 0),
                result.get("allocation_mixed", 0),
            ],
        }
    )
    return (
        alt.Chart(chart_data)
        .mark_arc(innerRadius=58, outerRadius=105)
        .encode(
            theta=alt.Theta("Allocation:Q"),
            color=alt.Color("Typology:N", title=None),
            tooltip=[
                alt.Tooltip("Typology:N"),
                alt.Tooltip("Allocation:Q", format=".1%"),
            ],
        )
        .properties(height=260)
    )


def cashflow_dataframe(result):
    return pd.DataFrame(result.get("cashflow_monthly", []))


def cashflow_chart(result):
    cashflow_df = cashflow_dataframe(result)
    if cashflow_df.empty:
        return None

    chart_df = cashflow_df.copy()
    chart_df["Construction Cost"] = -chart_df["Construction Cost"].abs() / 1_000_000
    chart_df["Revenue"] = chart_df["Revenue"] / 1_000_000
    chart_df["Net Cashflow"] = chart_df["Net Cashflow"] / 1_000_000
    chart_df["Cumulative Cashflow"] = chart_df["Cumulative Cashflow"] / 1_000_000

    monthly_df = chart_df.melt(
        id_vars=["Month"],
        value_vars=["Construction Cost", "Revenue"],
        var_name="Metric",
        value_name="Value M OMR",
    )

    monthly_bars = (
        alt.Chart(monthly_df)
        .mark_bar(opacity=0.75)
        .encode(
            x=alt.X("Month:Q", title="Month", axis=alt.Axis(tickCount=12, labelAngle=0)),
            y=alt.Y("Value M OMR:Q", title="Monthly cashflow (M OMR)"),
            color=alt.Color(
                "Metric:N",
                title=None,
                legend=alt.Legend(orient="bottom", direction="horizontal"),
                scale=alt.Scale(
                    domain=["Revenue", "Construction Cost"],
                    range=["#ef4444", "#3b82c6"],
                ),
            ),
            tooltip=[
                alt.Tooltip("Month:Q", format=".0f"),
                alt.Tooltip("Metric:N"),
                alt.Tooltip("Value M OMR:Q", title="Value (M OMR)", format=",.2f"),
            ],
        )
    )

    net_line = (
        alt.Chart(chart_df)
        .mark_line(color="#111827", strokeWidth=2)
        .encode(
            x=alt.X("Month:Q", title="Month", axis=alt.Axis(tickCount=12, labelAngle=0)),
            y=alt.Y("Net Cashflow:Q", title="Monthly cashflow (M OMR)"),
            tooltip=[
                alt.Tooltip("Month:Q", format=".0f"),
                alt.Tooltip("Net Cashflow:Q", title="Net cashflow (M OMR)", format=",.2f"),
            ],
        )
    )

    zero_rule = alt.Chart(pd.DataFrame({"Value M OMR": [0]})).mark_rule(color="#9ca3af").encode(y="Value M OMR:Q")
    monthly_layer = alt.layer(monthly_bars, net_line, zero_rule)

    cumulative_line = (
        alt.Chart(chart_df)
        .mark_line(color="#22c55e", strokeWidth=3)
        .encode(
            x=alt.X("Month:Q", title="Month", axis=alt.Axis(tickCount=12, labelAngle=0)),
            y=alt.Y(
                "Cumulative Cashflow:Q",
                title="Cumulative cash position (M OMR)",
                axis=alt.Axis(orient="right"),
            ),
            tooltip=[
                alt.Tooltip("Month:Q", format=".0f"),
                alt.Tooltip("Cumulative Cashflow:Q", title="Cumulative (M OMR)", format=",.2f"),
            ],
        )
    )

    return (
        alt.layer(monthly_layer, cumulative_line)
        .resolve_scale(y="independent")
        .properties(
            height=330,
            width="container",
            title="Project Cashflow: bars show monthly revenue/cost, dark line is monthly net, green line is cumulative cash position",
        )
        .configure_view(strokeWidth=0)
    )


def scenario_completion_chart(comparison_df):
    return (
        alt.Chart(comparison_df)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("Scenario:N", sort=None, title=None),
            y=alt.Y("Total Duration (months):Q", title="Months"),
            color=alt.value("#60a5fa"),
            tooltip=[
                alt.Tooltip("Scenario:N"),
                alt.Tooltip("Total Duration (months):Q", format=".0f"),
                alt.Tooltip("Peak Funding Gap (M OMR):Q", format=".1f"),
            ],
        )
        .properties(height=220)
    )


def format_ai_review_html(text):
    formatted_lines = []
    in_recommendation = False
    for raw_line in text.splitlines():
        line = html.escape(raw_line.strip())
        if not line:
            formatted_lines.append("<div style='height:8px;'></div>")
        elif line.lower() in ("recommendation", "final recommendation"):
            if not in_recommendation:
                formatted_lines.append("<div class='ai-recommendation-panel'>")
                in_recommendation = True
            formatted_lines.append(f"<h4 style='margin:0 0 10px;'>Recommendation</h4>")
        elif line.startswith("#"):
            formatted_lines.append(f"<h4 style='margin:10px 0 6px;'>{line.lstrip('# ').strip()}</h4>")
        elif line.startswith("- ") or line.startswith("* "):
            formatted_lines.append(f"<div style='margin:4px 0 4px 14px;'>• {line[2:]}</div>")
        elif re.match(r"^\d+\.", line):
            formatted_lines.append(f"<div style='font-weight:800;margin:12px 0 6px;'>{line}</div>")
        else:
            formatted_lines.append(f"<div style='margin:4px 0 8px;'>{line}</div>")
    if in_recommendation:
        formatted_lines.append("</div>")
    return "\n".join(formatted_lines)


def generate_scenario_ai_review(scenarios):
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

    scenario_payload = []
    for scenario in scenarios:
        result = scenario["result"]
        inputs = scenario["inputs"]
        scenario_payload.append(
            {
                "name": scenario["name"],
                "investment_m_omr": round(result.get("capex_total", 0) / 1_000_000, 2),
                "revenue_m_omr": round(result.get("revenue_total", 0) / 1_000_000, 2),
                "profit_margin": round(result.get("profit_general", 0), 4),
                "total_duration_months": result.get("total_duration_months", result.get("estimated_completion_months", 0)),
                "peak_funding_gap_m_omr": round(result.get("peak_funding_gap", 0) / 1_000_000, 2),
                "gfa_k_sqm": round(result.get("gfa_total", 0) / 1000, 2),
                "bua_k_sqm": round(result.get("builtup_total", 0) / 1000, 2),
                "luxury_villas": round(result.get("luxury_units", 0)),
                "semi_villas": round(result.get("semi_units", 0)),
                "apartment_units": round(result.get("apartments_total_units", 0)),
                "commercial_units": round(result.get("mixed_commercial_units", 0)),
                "office_units": round(result.get("mixed_Office_units", 0)),
                "apartment_parking_stories": inputs.get("apt_parking_stories", 0),
                "business_parking_stories": inputs.get("mixed_parking_stories", 0),
                "strategy": scenario["strategy"],
            }
        )

    prompt = f"""
You are a senior real estate master planning advisor.

Compare these masterplan scenarios and provide a concise executive assessment.
Focus on investment requirement, revenue, profit margin, development yield, unit mix, parking assumptions, total duration, peak funding gap, and market/sales risk.
Use plain text with short numbered scenario headings and hyphen bullet points.

For each scenario:
- give 2-3 pros
- give 2-3 cons or risks

Then recommend one scenario and explain why.
If two scenarios are close, say so and explain the trade-off.

Scenarios:
{json.dumps(scenario_payload, indent=2)}
"""

    response = client.responses.create(
        model="gpt-5.5",
        input=prompt,
    )
    return response.output_text












page = st.session_state.page
main_content, right_panel = st.columns([3, 1], gap="large")
with main_content:

    st.caption("Engineering Department")
    st.title("AI Master Planning Optimization Agent")
    st.caption("Decision-support platform for land-use allocation, development yield, investment requirement, revenue, and profitability.")

    def sync_dashboard_inputs():
        st.session_state.project_name = st.session_state.project_name_widget
        st.session_state.location = st.session_state.location_widget
        st.session_state.total_land_area = st.session_state.total_land_area_widget

        st.session_state.ai_investment_strategy = st.session_state.ai_investment_strategy_widget
        st.session_state.ai_success_definition = st.session_state.ai_success_definition_widget
        st.session_state.ai_main_concerns = st.session_state.ai_main_concerns_widget




    if page == "Dashboard":
        st.subheader("Project Definition")

        st.text_input(
            "Project Name",
            value=st.session_state.get("project_name", ""),
            key="project_name_widget",
            on_change=sync_dashboard_inputs,
        )

        st.text_input(
            "Location",
            value=st.session_state.get("location", ""),
            key="location_widget",
            on_change=sync_dashboard_inputs,
        )

        st.number_input(
            "Total Land Area (sqm)",
            value=safe_number(st.session_state.get("total_land_area", 0)),
            key="total_land_area_widget",
            on_change=sync_dashboard_inputs,
        )

        st.divider()

        st.markdown("### AI Project Strategy Assessment")

        st.markdown("#### 1. Investment Strategy")
        st.caption("Tell us about your available budget, financing approach, and investment strategy.")
        st.markdown(
            """
            <div style="font-size:12px; color:#a8adb5; line-height:1.35;">
            <b>Examples</b><br>
            • Fully self-funded<br>
            • Around 15 million OMR available<br>
            • Need early sales to support construction<br>
            • Prefer low initial investment
            </div>
            """,
            unsafe_allow_html=True,
        )

        ai_investment_strategy = st.text_area(
            "",
            height=120,
            value=st.session_state.get("ai_investment_strategy", ""),
            key="ai_investment_strategy_widget",
            label_visibility="collapsed",
            on_change=sync_dashboard_inputs,
        )

        st.markdown("#### 2. Definition of Success")
        st.caption("Describe what would make this project successful from a business perspective.")
        st.markdown(
            """
            <div style="font-size:12px; color:#a8adb5; line-height:1.35;">
            <b>Examples</b><br>
            • Maximum profit<br>
            • Fast capital recovery<br>
            • Balanced profitability and cashflow<br>
            • Premium long-term development
            </div>
            """,
            unsafe_allow_html=True,
        )

        ai_success_definition = st.text_area(
            "",
            height=120,
            value=st.session_state.get("ai_success_definition", ""),
            key="ai_success_definition_widget",
            label_visibility="collapsed",
            on_change=sync_dashboard_inputs,
        )

        st.markdown("#### 3. Main Concerns")
        st.caption("Describe the risks or challenges that are most important to you.")
        st.markdown(
            """
            <div style="font-size:12px; color:#a8adb5; line-height:1.35;">
            <b>Examples</b><br>
            • Slow sales<br>
            • High construction cost<br>
            • Market uncertainty<br>
            • Low-risk investment
            </div>
            """,
            unsafe_allow_html=True,
        )

        ai_main_concerns = st.text_area(
            "",
            height=120,
            value=st.session_state.get("ai_main_concerns", ""),
            key="ai_main_concerns_widget",
            label_visibility="collapsed",
            on_change=sync_dashboard_inputs,
        )

        ai_project_context = (
            st.session_state.get("ai_investment_strategy", "").strip()
            + "\n\n"
            + st.session_state.get("ai_success_definition", "").strip()
            + "\n\n"
            + st.session_state.get("ai_main_concerns", "").strip()
        )
        




        

        

        
        



    elif page == "Financial":
        st.subheader("Financial Inputs")

        overhead_cols = st.columns(2)
        with overhead_cols[0]:
            st.session_state.marketing_cost_pct = st.number_input(
                "Marketing Costs (%)",
                min_value=0.0,
                max_value=100.0,
                value=safe_number(st.session_state.marketing_cost_pct),
                step=0.5,
                key="input_marketing_cost_pct",
            )
        with overhead_cols[1]:
            st.session_state.soft_cost_pct = st.number_input(
                "Soft Costs (%)",
                min_value=0.0,
                max_value=100.0,
                value=safe_number(st.session_state.soft_cost_pct),
                step=0.5,
                key="input_soft_cost_pct",
            )

        st.divider()

        st.markdown("### Delivery and Absorption Assumptions")
        st.caption("Construction pace is in built-up sqm/month. Sales and leasing absorption is in units/month.")
        delivery_cols = st.columns(5)
        with delivery_cols[0]:
            st.markdown('<div class="delivery-input-label">Luxury Construction<br>Pace<br><span>(sqm/month)</span></div>', unsafe_allow_html=True)
            st.session_state.construction_pace_luxury = st.number_input(
                " ",
                min_value=1.0,
                value=safe_number(st.session_state.construction_pace_luxury),
                step=10.0,
                key="input_construction_pace_luxury",
                label_visibility="collapsed",
            )
            st.markdown('<div class="delivery-input-label">Luxury Sales<br>Absorption<br><span>(units/month)</span></div>', unsafe_allow_html=True)
            st.session_state.absorption_luxury_per_month = st.number_input(
                " ",
                min_value=0.1,
                value=safe_number(st.session_state.absorption_luxury_per_month),
                step=1.0,
                key="input_absorption_luxury_per_month",
                label_visibility="collapsed",
            )
        with delivery_cols[1]:
            st.markdown('<div class="delivery-input-label">Semi Construction<br>Pace<br><span>(sqm/month)</span></div>', unsafe_allow_html=True)
            st.session_state.construction_pace_semi = st.number_input(
                " ",
                min_value=1.0,
                value=safe_number(st.session_state.construction_pace_semi),
                step=10.0,
                key="input_construction_pace_semi",
                label_visibility="collapsed",
            )
            st.markdown('<div class="delivery-input-label">Semi Sales<br>Absorption<br><span>(units/month)</span></div>', unsafe_allow_html=True)
            st.session_state.absorption_semi_per_month = st.number_input(
                " ",
                min_value=0.1,
                value=safe_number(st.session_state.absorption_semi_per_month),
                step=1.0,
                key="input_absorption_semi_per_month",
                label_visibility="collapsed",
            )
        with delivery_cols[2]:
            st.markdown('<div class="delivery-input-label">Apartment Construction<br>Pace<br><span>(sqm/month)</span></div>', unsafe_allow_html=True)
            st.session_state.construction_pace_apartment = st.number_input(
                " ",
                min_value=1.0,
                value=safe_number(st.session_state.construction_pace_apartment),
                step=50.0,
                key="input_construction_pace_apartment",
                label_visibility="collapsed",
            )
            st.markdown('<div class="delivery-input-label">Apartment Sales<br>Absorption<br><span>(units/month)</span></div>', unsafe_allow_html=True)
            st.session_state.absorption_apartment_per_month = st.number_input(
                " ",
                min_value=0.1,
                value=safe_number(st.session_state.absorption_apartment_per_month),
                step=1.0,
                key="input_absorption_apartment_per_month",
                label_visibility="collapsed",
            )
        with delivery_cols[3]:
            st.markdown('<div class="delivery-input-label">Business Construction<br>Pace<br><span>(sqm/month)</span></div>', unsafe_allow_html=True)
            st.session_state.construction_pace_mixed = st.number_input(
                " ",
                min_value=1.0,
                value=safe_number(st.session_state.construction_pace_mixed),
                step=50.0,
                key="input_construction_pace_mixed",
                label_visibility="collapsed",
            )
            st.markdown('<div class="delivery-input-label">Commercial Sales/Leasing<br>Absorption<br><span>(units/month)</span></div>', unsafe_allow_html=True)
            st.session_state.absorption_commercial_per_month = st.number_input(
                " ",
                min_value=0.1,
                value=safe_number(st.session_state.absorption_commercial_per_month),
                step=1.0,
                key="input_absorption_commercial_per_month",
                label_visibility="collapsed",
            )
        with delivery_cols[4]:
            st.markdown('<div class="delivery-input-label">Infrastructure<br>Pace<br><span>(sqm/month)</span></div>', unsafe_allow_html=True)
            st.session_state.construction_pace_infrastructure = st.number_input(
                " ",
                min_value=1.0,
                value=safe_number(st.session_state.construction_pace_infrastructure),
                step=100.0,
                key="input_construction_pace_infrastructure",
                label_visibility="collapsed",
            )
            st.markdown('<div class="delivery-input-label">Office Sales/Leasing<br>Absorption<br><span>(units/month)</span></div>', unsafe_allow_html=True)
            st.session_state.absorption_office_per_month = st.number_input(
                " ",
                min_value=0.1,
                value=safe_number(st.session_state.absorption_office_per_month),
                step=1.0,
                key="input_absorption_office_per_month",
                label_visibility="collapsed",
            )

        st.divider()

        cols = st.columns(4)
        typologies = [
            ("Luxury Villas", "luxury"),
            ("Semi-detached Villas", "semi"),
            ("Apartments", "apartment"),
            ("Business Center", "mixed"),
        ]

        for col, (label, key) in zip(cols, typologies):
            with col:
                st.markdown(f'<div class="typology-column-title">{label}</div>', unsafe_allow_html=True)
                st.session_state[f"cost_{key}"] = st.number_input(
                    "Construction Cost",
                    value=safe_number(st.session_state[f"cost_{key}"]),
                    key=f"input_cost_{key}",
                )
                st.session_state[f"price_{key}"] = st.number_input(
                    "Sellable Price",
                    value=safe_number(st.session_state[f"price_{key}"]),
                    key=f"input_price_{key}",
                )
                st.session_state[f"cashflow_{key}"] = st.selectbox(
                    "Cashflow",
                    CASHFLOW_OPTIONS,
                    index=cashflow_index(st.session_state[f"cashflow_{key}"]),
                    key=f"input_cashflow_{key}",
                )
                prob_key = "prob_apartment" if key == "apartment" else f"prob_{key}"
                probability_percent = st.number_input(
                    "Sale Probability (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=safe_number(st.session_state[prob_key]) * 100,
                    step=1.0,
                    key=f"input_prob_{key}",
                )
                st.session_state[prob_key] = probability_percent / 100






    elif page == "Design":
        st.subheader("Design Assumptions")


        st.markdown("### Site Allocation")

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            road_pct_percent = st.number_input(
                "Roads (%)",
                min_value=0.0,
                max_value=100.0,
                value=safe_number(st.session_state.road_pct) * 100,
                step=1.0,
                key="design_road_pct",
            )
            st.session_state.road_pct = road_pct_percent / 100

        with c2:
            walkway_pct_percent = st.number_input(
                "Walkways (%)",
                min_value=0.0,
                max_value=100.0,
                value=safe_number(st.session_state.walkway_pct) * 100,
                step=1.0,
                key="design_walkway_pct",
            )
            st.session_state.walkway_pct = walkway_pct_percent / 100

        with c3:
            green_pct_percent = st.number_input(
                "Public Realm (%)",
                min_value=0.0,
                max_value=100.0,
                value=safe_number(st.session_state.green_pct) * 100,
                step=1.0,
                key="design_green_pct",
            )
            st.session_state.green_pct = green_pct_percent / 100

        with c4:
            micromobility_pct_percent = st.number_input(
                "Micromobility (%)",
                min_value=0.0,
                max_value=100.0,
                value=safe_number(st.session_state.micromobility_pct) * 100,
                step=1.0,
                key="design_micromobility_pct",
            )
            st.session_state.micromobility_pct = micromobility_pct_percent / 100

        st.divider()

        st.markdown("## Residential Typologies")

        with st.expander("🏡 Luxury Villas", expanded=False):
            st.session_state.luxury_plot = st.number_input("Luxury Plot Area", value=safe_number(st.session_state.luxury_plot), key="design_luxury_plot")
            st.session_state.luxury_footprint = st.number_input("Luxury Footprint", value=safe_number(st.session_state.luxury_footprint), key="design_luxury_footprint")
            st.session_state.luxury_gfa = st.number_input("Luxury GFA / Villa", value=safe_number(st.session_state.luxury_gfa), key="design_luxury_gfa")
            st.session_state.luxury_builtup = st.number_input("Luxury Built-up / Villa", value=safe_number(st.session_state.luxury_builtup), key="design_luxury_builtup")

        with st.expander("🏘 Semi-detached Villas", expanded=False):
            st.session_state.semi_plot = st.number_input("Semi-detached Plot Area", value=safe_number(st.session_state.semi_plot), key="design_semi_plot")
            st.session_state.semi_footprint = st.number_input("Semi-detached Footprint", value=safe_number(st.session_state.semi_footprint), key="design_semi_footprint")
            st.session_state.semi_gfa = st.number_input("Semi-detached GFA / Villa", value=safe_number(st.session_state.semi_gfa), key="design_semi_gfa")
            st.session_state.semi_builtup = st.number_input("Semi-detached Built-up / Villa", value=safe_number(st.session_state.semi_builtup), key="design_semi_builtup")

        with st.expander("🏢 Apartments", expanded=False):
            st.session_state.apt_parking_area = st.number_input("Apartment Parking Area / Car", value=safe_number(st.session_state.apt_parking_area), key="design_apt_parking_area")
            st.session_state.apt_parking_stories = st.number_input("Apartment Parking Stories", value=safe_number(st.session_state.apt_parking_stories), key="design_apt_parking_stories")
            st.session_state.apt_common_floors = st.number_input("Apartment Common / Lobby Floors", value=safe_number(st.session_state.apt_common_floors), key="design_apt_common_floors")
            st.session_state.apt_res_floors = st.number_input("Apartment Residential Floors", value=safe_number(st.session_state.apt_res_floors), key="design_apt_res_floors")
            st.session_state.apt_buildings = st.number_input("Number of Residential Buildings", value=safe_number(st.session_state.apt_buildings), key="design_apt_buildings")
            st.session_state.apt_unit_area = st.number_input("Apartment Average Unit Area", value=safe_number(st.session_state.apt_unit_area), key="design_apt_unit_area")
            visitor_parking = st.number_input(    "Apartment Visitor Parking (%)",    value=safe_number(st.session_state.apt_visitor_parking_pct) * 100,    step=5.0,)

            st.session_state.apt_visitor_parking_pct = visitor_parking / 100

            st.markdown("#### Parking Requirement by Unit Type")

            st.session_state.apt_parking_1bhk = st.number_input("Parking / 1-BHK Unit", value=safe_number(st.session_state.apt_parking_1bhk), key="design_apt_parking_1bhk")
            st.session_state.apt_parking_2bhk = st.number_input("Parking / 2-BHK Unit", value=safe_number(st.session_state.apt_parking_2bhk), key="design_apt_parking_2bhk")
            st.session_state.apt_parking_3bhk = st.number_input("Parking / 3-BHK Unit", value=safe_number(st.session_state.apt_parking_3bhk), key="design_apt_parking_3bhk")
            st.session_state.apt_parking_4bhk = st.number_input("Parking / 4-BHK Unit", value=safe_number(st.session_state.apt_parking_4bhk), key="design_apt_parking_4bhk")

            st.markdown("#### Residential Unit Mix")

            st.session_state.apt_pct_1bhk = st.number_input("1-BHK Units (%)", value=safe_number(st.session_state.apt_pct_1bhk), key="design_apt_pct_1bhk")
            st.session_state.apt_pct_2bhk = st.number_input("2-BHK Units (%)", value=safe_number(st.session_state.apt_pct_2bhk), key="design_apt_pct_2bhk")
            st.session_state.apt_pct_3bhk = st.number_input("3-BHK Units (%)", value=safe_number(st.session_state.apt_pct_3bhk), key="design_apt_pct_3bhk")
            st.session_state.apt_pct_4bhk = st.number_input("4-BHK Units (%)", value=safe_number(st.session_state.apt_pct_4bhk), key="design_apt_pct_4bhk")


        st.markdown("## Business Center Development")

        with st.expander("🏬 Business Center Building", expanded=False):
            st.session_state.mixed_parking_area = st.number_input("Business Center Parking Area / Car", value=safe_number(st.session_state.mixed_parking_area), key="design_mixed_parking_area")
            st.session_state.mixed_parking_stories = st.number_input("Business Center Parking Stories", value=safe_number(st.session_state.mixed_parking_stories), key="design_mixed_parking_stories")
            st.session_state.mixed_commercial_floors = st.number_input("Business Center Commercial Floors", value=safe_number(st.session_state.mixed_commercial_floors), key="design_mixed_commercial_floors")
            st.session_state.mixed_commercial_units_per_floor = st.number_input("Business Center Commercial Units / Floor", value=safe_number(st.session_state.mixed_commercial_units_per_floor), key="design_mixed_commercial_units_per_floor")
            st.session_state.mixed_res_floors = st.number_input("Business Center Office Floors", value=safe_number(st.session_state.mixed_res_floors), key="design_mixed_res_floors")
            st.session_state.mixed_commercial_unit_area = st.number_input("Business Center Commercial Unit Area", value=safe_number(st.session_state.mixed_commercial_unit_area), key="design_mixed_commercial_unit_area")
            st.session_state.mixed_res_unit_area = st.number_input("Business Center Office Unit Area", value=safe_number(st.session_state.mixed_res_unit_area), key="design_mixed_res_unit_area")

            st.markdown("#### Parking Requirement by Unit Type")

            st.session_state.mixed_parking_commercial_unit = st.number_input("Parking / Commercial Unit", value=safe_number(st.session_state.mixed_parking_commercial_unit), key="design_mixed_parking_commercial_unit")
            st.session_state.mixed_parking_1bhk = st.number_input("Parking / 1-BHK Unit", value=safe_number(st.session_state.mixed_parking_1bhk), key="design_mixed_parking_1bhk")
            st.session_state.mixed_parking_2bhk = st.number_input("Parking / 2-BHK Unit", value=safe_number(st.session_state.mixed_parking_2bhk), key="design_mixed_parking_2bhk")
            st.session_state.mixed_parking_3bhk = st.number_input("Parking / 3-BHK Unit", value=safe_number(st.session_state.mixed_parking_3bhk), key="design_mixed_parking_3bhk")
            st.session_state.mixed_parking_4bhk = st.number_input("Parking / 4-BHK Unit", value=safe_number(st.session_state.mixed_parking_4bhk), key="design_mixed_parking_4bhk")

            st.markdown("#### Office Unit Mix")

            st.session_state.mixed_pct_1bhk = st.number_input("1-BHK Units (%)", value=safe_number(st.session_state.mixed_pct_1bhk), key="design_mixed_pct_1bhk")
            st.session_state.mixed_pct_2bhk = st.number_input("2-BHK Units (%)", value=safe_number(st.session_state.mixed_pct_2bhk), key="design_mixed_pct_2bhk")
            st.session_state.mixed_pct_3bhk = st.number_input("3-BHK Units (%)", value=safe_number(st.session_state.mixed_pct_3bhk), key="design_mixed_pct_3bhk")
            st.session_state.mixed_pct_4bhk = st.number_input("4-BHK Units (%)", value=safe_number(st.session_state.mixed_pct_4bhk), key="design_mixed_pct_4bhk")

            st.markdown("#### Visitor Parking")

            visitor_parking = st.number_input(    "Visitor Parking Allocation (%)",    value=safe_number(st.session_state.mixed_visitor_parking_pct) * 100,    step=5.0,)

            st.session_state.mixed_visitor_parking_pct = visitor_parking / 100








    elif page == "Results":
        

        result = st.session_state.result

        if result is None:
            st.info("No optimization has been run yet. Go to Dashboard and press Run Optimization.")
        else:
            st.markdown("## Project Performance")
            st.markdown("### Financial Outcome")

            k1, k2, k3 = st.columns(3)

            k1.metric(
                "Investment Required",
                f"OMR {result['capex_total']/1_000_000:.1f} M"
            )

            k2.metric(
                "Expected Revenue",
                f"OMR {result['revenue_total']/1_000_000:.1f} M"
            )

            k3.metric(
                "Expected Profit Margin",
                f"{result['profit_general']:.1%}"
            )

            st.markdown("### Delivery Duration")
            st.caption("Typology durations are driven by construction pace and sales/leasing absorption. Apartments start from month 4; business center starts 6 months after apartments.")
            duration_values = result.get("typology_durations", {})
            duration_cols = st.columns(3)
            duration_cols[0].metric("Luxury Villas", f"{duration_values.get('Luxury Villas', 0):.0f} months")
            duration_cols[1].metric("Semi-detached Villas", f"{duration_values.get('Semi-detached Villas', 0):.0f} months")
            duration_cols[2].metric("Apartments", f"{duration_values.get('Apartments', 0):.0f} months")
            duration_cols = st.columns(3)
            duration_cols[0].metric("Business Center", f"{duration_values.get('Business Center', 0):.0f} months")
            duration_cols[1].metric("Infrastructure", f"{duration_values.get('Infrastructure', 0):.0f} months")
            duration_cols[2].metric("Total Duration", f"{result['total_duration_months']:.0f} months")

            st.markdown("### Funding Requirement")
            funding_cols = st.columns(3)
            funding_cols[0].metric("Peak Funding Gap", f"OMR {result['peak_funding_gap']/1_000_000:.1f} M")

            st.divider()

            st.markdown("## Project Cashflow")
            st.caption("Values are shown in M OMR. Costs are negative outflows, revenue is positive inflow, the dark line is monthly net cashflow, and the green line is cumulative cash position.")
            cashflow_visual = cashflow_chart(result)
            if cashflow_visual is not None:
                st.altair_chart(cashflow_visual, use_container_width=True)

            st.markdown("## Development Yield")

            left, d1, d2, d3, right = st.columns([0.4, 1, 1, 1, 0.4])

            d1.metric(
                "Sellable Land Use Percentage",
                f"{result['sellable_land_use_area']:.0%}"
            )

            d2.metric(
                "Total GFA",
                f"{result['gfa_total']/1000:.1f}k sqm"
            )

            d3.metric(
                "Total Built-up Area",
                f"{result['builtup_total']/1000:.1f}k sqm"
            )

            st.divider()



            try:
                export_filename, export_data = build_results_excel(result)
                st.download_button(
                    "💾 Save Results",
                    data=export_data,
                    file_name=export_filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            except Exception as error:
                st.error(f"Could not prepare the results file: {error}")

            st.subheader("Development Mix")
            st.caption("Recommended land-use allocation and development yield by typology.")
            
            
            major_df = pd.DataFrame(
        {
            "Typology": [
                "Luxury Villas",
                "Semi-detached Villas",
                "Apartments",
                "Business Center",
            ],

            
            "Development Program": [
                f"{result['luxury_units']:,.0f} Villas",
                f"{result['semi_units']:,.0f} Villas",
                f"{result['apartments_buildings']:,.0f} Residential Buildings / {result['apartments_total_units']:,.0f} Units",
                f"{result['mixed_commercial_units']:,.0f} Commercial Units / {result['mixed_Office_units']:,.0f} Office Units",
            ],


            "Allocation %": [
                result["allocation_luxury"],
                result["allocation_semi"],
                result["allocation_apartments"],
                result["allocation_mixed"],
            ],
            "Land Area": [
                result["luxury_land"],
                result["semi_land"],
                result["apartments_land"],
                result["mixed_land"],
            ],
            "GFA": [
                result["gfa_luxury"],
                result["gfa_semi"],
                result["gfa_apartments"],
                result["gfa_mixed"],
            ],
            "Built-up": [
                result["builtup_luxury"],
                result["builtup_semi"],
                result["builtup_apartments"],
                result["builtup_mixed"],
            ],



            "CAPEX": [
                result["capex_luxury"],
                result["capex_semi"],
                result["capex_apartments"],
                result["capex_mixed"],
            ],
            "Revenue": [
                result["revenue_luxury"],
                result["revenue_semi"],
                result["revenue_apartments"],
                result["revenue_mixed"],
            ],
            "Profit %": [
                result["profit_luxury"],
                result["profit_semi"],
                result["profit_apartments"],
                result["profit_mixed"],
            ],






    })

            st.dataframe(
                major_df.style.format({
                    "Allocation %": "{:.1%}",
                    "Land Area": "{:,.0f}",
                    "GFA": "{:,.0f}",
                    "Built-up": "{:,.0f}",
                    "CAPEX": "{:,.0f}",
                    "Revenue": "{:,.0f}",
                    "Profit %": "{:.1%}",
                }),
                use_container_width=True,
            )


            st.subheader("Detailed Development Outputs")

            with st.expander("🏡 Luxury Villas", expanded=False):
                st.write(f"Total land area: {fmt(result['luxury_land'], ' sqm')}")
                st.write(f"Maximum possible number of villas: {fmt(result['luxury_units'])}")
                st.write(f"Total GFA: {fmt(result['luxury_total_gfa'], ' sqm')}")
                st.write(f"Total built-up area: {fmt(result['luxury_total_builtup'], ' sqm')}")

            with st.expander("🏘 Semi-detached Villas", expanded=False):
                st.write(f"Total land area: {fmt(result['semi_land'], ' sqm')}")
                st.write(f"Maximum possible number of villas: {fmt(result['semi_units'])}")
                st.write(f"Total GFA: {fmt(result['semi_total_gfa'], ' sqm')}")
                st.write(f"Total built-up area: {fmt(result['semi_total_builtup'], ' sqm')}")

            with st.expander("🏢 Apartments", expanded=False):
                apartments_details = pd.DataFrame({
                    "Output": [
                        "Total Land area",
                        "Maximum possible number of Parking spaces",
                        "Visitors Parking spaces",
                        "Maximum parking spaces excluding visitors",
                        "Total number of apartment units",
                        "Number of buildings",
                        "Number of residential floors in each building",
                        "Number of units in each floor",
                        "Land area for each building",
                        "Ground floor footprint",
                        "Total sellable area for one building",
                        "Total GFA for one building including GF, amenities, and corridors",
                        "Total built-up for one building including basement",
                        "Total GFA for all apartments",
                        "Total built-up for all apartments",
                    ],
                    "Value": [
                        result["apartments_land"],
                        result["apartments_parking_max"],
                        result["apartments_visitor_parking"],
                        result["apartments_parking_no_visitor"],
                        result["apartments_total_units"],
                        result["apartments_buildings"],
                        result["apartments_res_floors"],
                        result["apartments_units_per_floor"],
                        result["apartments_land_per_building"],
                        result["apartments_ground_footprint"],
                        result["apartments_sellable_per_building"],
                        result["apartments_gfa_per_building"],
                        result["apartments_builtup_per_building"],
                        result["apartments_total_gfa"],
                        result["apartments_total_builtup"],
                    ],
                })
                for _, row in apartments_details.iterrows():
                    st.write(f"**{row['Output']}:** {fmt(row['Value'])}")

            with st.expander("🏬 Business Center", expanded=False):
                mixed_details = pd.DataFrame({
                    "Output": [
                        "Total Land area",
                        "Maximum possible number of Parking spaces",
                        "Visitors Parking spaces",
                        "Parking spaces",
                        "Average number of units in Office floors",
                        "Number of commercial units",
                        "Number of Office units",
                        "Sellable area of commercial units",
                        "Sellable area of Office units",
                        "Ground floor footprint",
                        "Total GFA including amenities and corridors",
                        "Total built-up including basement",
                    ],
                    "Value": [
                        result["mixed_land"],
                        result["mixed_parking_max"],
                        result["mixed_visitor_parking"],
                        result["mixed_parking_commercial"],
                        result["mixed_res_units_avg"],
                        result["mixed_commercial_units"],
                        result["mixed_Office_units"],
                        result["mixed_commercial_sellable"],
                        result["mixed_Office_sellable"],
                        result["mixed_ground_footprint"],
                        result["mixed_total_gfa"],
                        result["mixed_total_builtup"],
                    ],
                })
                for _, row in mixed_details.iterrows():
                    st.write(f"**{row['Output']}:** {fmt(row['Value'])}")

    elif page == "Comparison":
        st.markdown("## Scenario Comparison")

        scenarios = st.session_state.scenarios
        if not scenarios:
            st.info("No scenarios saved yet. Run an optimization, open Optimization Results, then confirm the result as a scenario.")
        else:
            st.caption(f"{len(scenarios)} saved scenario(s) in this browser session.")

            comparison_df = scenario_comparison_rows(scenarios)

            best_profit = comparison_df.loc[comparison_df["Profit Margin"].idxmax()]
            lowest_investment = comparison_df.loc[comparison_df["Investment (M OMR)"].idxmin()]
            highest_revenue = comparison_df.loc[comparison_df["Revenue (M OMR)"].idxmax()]
            fastest_completion = comparison_df.loc[comparison_df["Total Duration (months)"].idxmin()]
            lowest_gap = comparison_df.loc[comparison_df["Peak Funding Gap (M OMR)"].idxmin()]

            s1, s2, s3 = st.columns(3)
            with s1:
                st.markdown(
                    f"""
                    <div class="comparison-card">
                        <div class="comparison-card-title">Best Profit Margin</div>
                        <div class="comparison-card-value">{best_profit['Profit Margin']:.1%}</div>
                        <div class="advisor-muted">{best_profit['Scenario']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with s2:
                st.markdown(
                    f"""
                    <div class="comparison-card">
                        <div class="comparison-card-title">Lowest Investment</div>
                        <div class="comparison-card-value">{lowest_investment['Investment (M OMR)']:.1f} M</div>
                        <div class="advisor-muted">{lowest_investment['Scenario']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with s3:
                st.markdown(
                    f"""
                    <div class="comparison-card">
                        <div class="comparison-card-title">Highest Revenue</div>
                        <div class="comparison-card-value">{highest_revenue['Revenue (M OMR)']:.1f} M</div>
                        <div class="advisor-muted">{highest_revenue['Scenario']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            s4, s5 = st.columns(2)
            with s4:
                st.markdown(
                    f"""
                    <div class="comparison-card">
                        <div class="comparison-card-title">Fastest Completion</div>
                        <div class="comparison-card-value">{fastest_completion['Total Duration (months)']:.0f} months</div>
                        <div class="advisor-muted">{fastest_completion['Scenario']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with s5:
                st.markdown(
                    f"""
                    <div class="comparison-card">
                        <div class="comparison-card-title">Lowest Funding Gap</div>
                        <div class="comparison-card-value">{lowest_gap['Peak Funding Gap (M OMR)']:.1f} M</div>
                        <div class="advisor-muted">{lowest_gap['Scenario']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.markdown("### Visual Comparison")
            chart_left, chart_right = st.columns(2)
            with chart_left:
                st.markdown("#### Investment vs Revenue")
                st.altair_chart(scenario_financial_chart(comparison_df), use_container_width=True)
            with chart_right:
                st.markdown("#### Development Yield")
                st.altair_chart(scenario_yield_chart(comparison_df), use_container_width=True)

            chart_left, chart_right = st.columns(2)
            with chart_left:
                st.markdown("#### Profit Margin")
                st.altair_chart(scenario_profit_chart(comparison_df), use_container_width=True)
            with chart_right:
                st.markdown("#### Development Mix")
                selected_scenario_name = st.selectbox(
                    "Scenario",
                    [scenario["name"] for scenario in scenarios],
                    key="allocation_donut_scenario",
                )
                selected_scenario = next(
                    scenario for scenario in scenarios if scenario["name"] == selected_scenario_name
                )
                st.altair_chart(scenario_allocation_donut(selected_scenario), use_container_width=True)

            chart_left, chart_right = st.columns(2)
            with chart_left:
                st.markdown("#### Completion Time")
                st.altair_chart(scenario_completion_chart(comparison_df), use_container_width=True)
            with chart_right:
                st.markdown("#### Selected Scenario Cashflow")
                selected_cashflow_chart = cashflow_chart(selected_scenario["result"])
                if selected_cashflow_chart is not None:
                    st.altair_chart(selected_cashflow_chart, use_container_width=True)

            st.markdown("### Scenario Metrics")
            st.dataframe(
                comparison_df.style.format({
                    "Investment (M OMR)": "{:.1f}",
                    "Revenue (M OMR)": "{:.1f}",
                    "Profit Margin": "{:.1%}",
                    "Total Duration (months)": "{:.0f}",
                    "Peak Funding Gap (M OMR)": "{:.1f}",
                    "Sellable Land Use": "{:.0%}",
                    "GFA (k sqm)": "{:.1f}",
                    "BUA (k sqm)": "{:.1f}",
                    "Luxury Villas": "{:,.0f}",
                    "Semi Villas": "{:,.0f}",
                    "Apartment Buildings": "{:,.0f}",
                    "Apartment Units": "{:,.0f}",
                    "Commercial Units": "{:,.0f}",
                    "Office Units": "{:,.0f}",
                    "Apartment Parking Stories": "{:,.0f}",
                    "Business Parking Stories": "{:,.0f}",
                }),
                use_container_width=True,
            )

            st.markdown("### Saved Scenario Details")
            for index, scenario in enumerate(scenarios):
                result = scenario["result"]
                inputs = scenario["inputs"]
                with st.expander(scenario["name"], expanded=False):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Investment Required", f"OMR {result.get('capex_total', 0)/1_000_000:.1f} M")
                    c2.metric("Expected Revenue", f"OMR {result.get('revenue_total', 0)/1_000_000:.1f} M")
                    c3.metric("Profit Margin", f"{result.get('profit_general', 0):.1%}")
                    c1.metric("Total Duration", f"{result.get('total_duration_months', result.get('estimated_completion_months', 0)):.0f} months")
                    c2.metric("Peak Funding Gap", f"OMR {result.get('peak_funding_gap', 0)/1_000_000:.1f} M")

                    st.write(f"Apartment parking stories: {fmt(inputs.get('apt_parking_stories', 0))}")
                    st.write(f"Business center parking stories: {fmt(inputs.get('mixed_parking_stories', 0))}")
                    st.write(
                        "Apartment unit mix: "
                        f"1-BHK {inputs.get('apt_pct_1bhk', 0):.0%}, "
                        f"2-BHK {inputs.get('apt_pct_2bhk', 0):.0%}, "
                        f"3-BHK {inputs.get('apt_pct_3bhk', 0):.0%}, "
                        f"4-BHK {inputs.get('apt_pct_4bhk', 0):.0%}"
                    )
                    st.write(f"Saved: {scenario['created_at']}")

                    if st.button("Remove Scenario", key=f"remove_scenario_{index}", use_container_width=True):
                        st.session_state.scenarios.pop(index)
                        st.session_state.scenario_ai_review = ""
                        st.rerun()

            st.divider()
            st.markdown("### AI Scenario Review")
            if len(scenarios) < 2:
                st.info("Save at least two scenarios to generate a meaningful AI comparison.")
            else:
                if st.button("Generate AI Scenario Review", use_container_width=True):
                    try:
                        with st.spinner("Reviewing scenarios..."):
                            st.session_state.scenario_ai_review = generate_scenario_ai_review(scenarios)
                    except Exception as error:
                        st.error(f"AI scenario review failed: {error}")

                if st.session_state.scenario_ai_review:
                    st.markdown(
                        f"""
                        <div class="ai-review-panel">
                        {format_ai_review_html(st.session_state.scenario_ai_review)}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            try:
                comparison_filename, comparison_data = build_scenario_comparison_excel(
                    scenarios,
                    st.session_state.scenario_ai_review,
                )
                st.download_button(
                    "Download Comparison Excel",
                    data=comparison_data,
                    file_name=comparison_filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            except Exception as error:
                st.error(f"Could not prepare the comparison file: {error}")

    st.markdown('<hr class="advisor-divider">', unsafe_allow_html=True)






with right_panel:



    



    st.markdown(
        """
        <div style="
            position:absolute;
            top:0;
            bottom:-100vh;
            left:-1.35rem;
            width:1px;
            background:rgba(128, 128, 128, 0.28);
        "></div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("### AI Project Advisor")

    result = st.session_state.result

    if result is not None:
        st.markdown("#### Scenario Builder")
        st.caption("Save the current optimization as a scenario before changing assumptions.")
        scenario_name = st.text_input(
            "Scenario name",
            value=f"Scenario {len(st.session_state.scenarios) + 1}",
            key="scenario_name_input",
        )
        if st.button("Confirm as Scenario", use_container_width=True, type="primary"):
            if not scenario_name.strip():
                st.warning("Please enter a scenario name.")
            else:
                st.session_state.scenarios.append(create_scenario_snapshot(scenario_name))
                st.session_state.scenario_ai_review = ""
                st.success(f"Saved {scenario_name.strip()} for comparison.")

        if st.session_state.scenarios:
            st.caption(f"{len(st.session_state.scenarios)} scenario(s) saved.")
            if st.button("Open Scenario Comparison", use_container_width=True):
                st.session_state.page = "Comparison"
                st.rerun()

        st.markdown('<hr class="advisor-divider">', unsafe_allow_html=True)

    land_area_value = safe_number(
        st.session_state.get(
            "total_land_area",
            st.session_state.defaults.get("total_land_area", 0),
        )
    )

    st.markdown(
        f"""
        <div class="advisor-metric">
            <div class="advisor-metric-label advisor-muted">Total Land Area</div>
            <div class="advisor-metric-value advisor-strong">{land_area_value:,.0f} sqm</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<hr class="advisor-divider">', unsafe_allow_html=True)

    if result is not None:

        st.markdown(
            """
            <div class="advisor-section-title">
                📊 Project Performance
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""
            <div class="advisor-metric">
                <div class="advisor-metric-label advisor-muted">Investment Required</div>
                <div class="advisor-metric-value advisor-strong">{result['capex_total']/1_000_000:.1f} M OMR</div>
                <div class="advisor-caption advisor-muted">Includes infrastructure works Includes client contribution</div>
            </div>
            <hr class="advisor-divider">
            <div class="advisor-metric">
                <div class="advisor-metric-label advisor-muted">Expected Revenue</div>
                <div class="advisor-metric-value advisor-strong">{result['revenue_total']/1_000_000:.1f} M OMR</div>
            </div>
            <hr class="advisor-divider">
            <div class="advisor-metric">
                <div class="advisor-metric-label advisor-muted">Expected Profit Margin</div>
                <div class="advisor-metric-value advisor-strong">{result['profit_general']:.1%}</div>
            </div>
            <hr class="advisor-divider">
            <div class="advisor-metric">
                <div class="advisor-metric-label advisor-muted">Total Duration</div>
                <div class="advisor-metric-value advisor-strong">{result['total_duration_months']:.0f} months</div>
                <div class="advisor-caption advisor-muted">Based on phased starts, construction pace, and absorption</div>
            </div>
            <hr class="advisor-divider">
            <div class="advisor-metric">
                <div class="advisor-metric-label advisor-muted">Peak Funding Gap</div>
                <div class="advisor-metric-value advisor-strong">{result['peak_funding_gap']/1_000_000:.1f} M OMR</div>
            </div>
            <hr class="advisor-divider">
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="advisor-section-title">
                🏗 Development Yield
            </div>
            """,
            unsafe_allow_html=True,
        )

        y1, y2 = st.columns(2)

        with y1:
            st.markdown(
                f"""
                <div class="advisor-muted" style="font-size:12px;">Total GFA</div>
                <div class="advisor-strong" style="font-size:18px;font-weight:700;">
                    {result['gfa_total']/1000:.1f}k sqm
                </div>
                """,
                unsafe_allow_html=True,
            )

        with y2:
            st.markdown(
                f"""
                <div class="advisor-muted" style="font-size:12px;">Total BUA</div>
                <div class="advisor-strong" style="font-size:18px;font-weight:700;">
                    {result['builtup_total']/1000:.1f}k sqm
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown(
            "<hr class='advisor-divider'>",
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="advisor-section-title">
                🏘 Development Program
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""
        <div class="advisor-program-list">

        <div style="display:flex; justify-content:space-between;">
        <span class="advisor-muted">Luxury Villas</span>
        <b>{result['luxury_units']:,.0f}</b>
        </div>

        <div style="display:flex; justify-content:space-between;">
        <span class="advisor-muted">Semi-detached</span>
        <b>{result['semi_units']:,.0f}</b>
        </div>

        <div style="display:flex; justify-content:space-between;">
        <span class="advisor-muted">Apartment Buildings</span>
        <b>{result['apartments_buildings']:,.0f}</b>
        </div>

        <div style="display:flex; justify-content:space-between;">
        <span class="advisor-muted">Apartment Units</span>
        <b>{result['apartments_total_units']:,.0f}</b>
        </div>

        <div style="display:flex; justify-content:space-between;">
        <span class="advisor-muted">Commercial Units</span>
        <b>{result['mixed_commercial_units']:,.0f}</b>
        </div>

        <div style="display:flex; justify-content:space-between;">
        <span class="advisor-muted">Office Units</span>
        <b>{result['mixed_Office_units']:,.0f}</b>
        </div>

        </div>
        """,
            unsafe_allow_html=True,
        )

    else:
        st.info("Run optimization to view major outputs.")

    st.divider()

    if st.button("🤖 Generate AI Recommendation", use_container_width=True):

        if not (
            st.session_state.get("ai_investment_strategy", "").strip()
            and st.session_state.get("ai_success_definition", "").strip()
            and st.session_state.get("ai_main_concerns", "").strip()
        ):
            st.warning("Complete the three AI strategy questions first.")
        else:
            ai_project_context = (
                st.session_state.ai_investment_strategy.strip()
                + "\n\n"
                + st.session_state.ai_success_definition.strip()
                + "\n\n"
                + st.session_state.ai_main_concerns.strip()
            )

            try:
                ai_result = ai_recommend_weights(
                    ai_project_context,
                    "AI interpreted",
                    "AI interpreted",
                    "AI interpreted",
                    "AI interpreted",
                )
            except Exception as exc:
                st.error(f"AI recommendation failed: {exc}")
                ai_result = None

            if ai_result:
                st.session_state.profit_weight = ai_result["profit_weight"]
                st.session_state.cashflow_weight = ai_result["cashflow_weight"]
                st.session_state.prob_weight = ai_result["sale_probability_weight"]

                st.session_state.right_profit_weight = ai_result["profit_weight"]
                st.session_state.right_cashflow_weight = ai_result["cashflow_weight"]
                st.session_state.right_prob_weight = ai_result["sale_probability_weight"]
                st.session_state.ai_explanation = ai_result["explanation"]

                st.rerun()

    st.markdown("#### 🎯 Optimization Priorities")

    st.session_state.profit_weight = st.slider(
        "Profitability",
        0.0,
        1.0,
        safe_number(st.session_state.profit_weight),
        0.05,
        key="right_profit_weight",
    )

    st.session_state.cashflow_weight = st.slider(
        "Cashflow",
        0.0,
        1.0,
        safe_number(st.session_state.cashflow_weight),
        0.05,
        key="right_cashflow_weight",
    )

    st.session_state.prob_weight = st.slider(
        "Sale Probability",
        0.0,
        1.0,
        safe_number(st.session_state.prob_weight),
        0.05,
        key="right_prob_weight",
    )

    if "ai_explanation" in st.session_state:
        st.divider()
        st.markdown("#### 🤖 AI Recommendation")
        st.success(st.session_state.ai_explanation)






st.caption("AI Master Planning Optimization Agent | Version 1.0")
