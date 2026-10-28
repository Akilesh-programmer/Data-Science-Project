"""
Analytics service — aggregations, distributions, and trend calculations.
"""
import pandas as pd
import numpy as np
from .data_loader import store


def summary_stats() -> dict:
    df = store.df
    operational = (df["StatusType"] == "Operational").sum()
    return {
        "total_stations": len(df),
        "total_countries": df["Country"].nunique(),
        "total_operators": df["Operator"].nunique(),
        "avg_power_kw": round(float(df["MaxPowerKW"].mean()), 2),
        "median_power_kw": round(float(df["MaxPowerKW"].median()), 2),
        "operational_pct": round(operational / len(df) * 100, 1),
        "fast_charge_pct": round(df["IsFastCharge"].mean() * 100, 1),
    }


def top_countries(n: int = 15) -> list[dict]:
    counts = store.df["Country"].value_counts().head(n)
    return [{"country": c, "count": int(v)} for c, v in counts.items()]


def year_growth() -> list[dict]:
    counts = store.df["YearCreated"].value_counts().sort_index()
    cumulative = counts.cumsum()
    return [
        {"year": int(y), "count": int(c), "cumulative": int(cumulative[y])}
        for y, c in counts.items()
    ]


def connector_distribution() -> list[dict]:
    # Simplify connector types to major categories
    def simplify(conn_str) -> str:
        if not isinstance(conn_str, str):
            return "Other"
        conn = conn_str.lower()
        if "ccs" in conn and "type 2" in conn:
            return "CCS (Type 2)"
        if "ccs" in conn and "type 1" in conn:
            return "CCS (Type 1)"
        if "chademo" in conn:
            return "CHAdeMO"
        if "tesla" in conn:
            return "Tesla"
        if "type 2" in conn:
            return "Type 2"
        if "type 1" in conn or "j1772" in conn:
            return "Type 1 (J1772)"
        if "schuko" in conn or "cee" in conn:
            return "Schuko / CEE"
        return "Other"

    simplified = store.df["ConnectionTypes"].apply(simplify)
    counts = simplified.value_counts()
    total = counts.sum()
    return [
        {
            "connector_type": str(ct),
            "count": int(c),
            "percentage": round(c / total * 100, 1),
        }
        for ct, c in counts.items()
    ]


def power_distribution() -> list[dict]:
    counts = store.df["PowerCategory"].value_counts().sort_index()
    total = counts.sum()
    return [
        {
            "range_label": str(label),
            "count": int(c),
            "percentage": round(c / total * 100, 1),
        }
        for label, c in counts.items()
    ]


def operator_share(n: int = 10) -> list[dict]:
    counts = store.df["Operator"].value_counts().head(n)
    total = len(store.df)
    return [
        {
            "operator": str(op),
            "count": int(c),
            "percentage": round(c / total * 100, 1),
        }
        for op, c in counts.items()
    ]


def status_breakdown() -> list[dict]:
    counts = store.df["StatusType"].value_counts()
    total = counts.sum()
    return [
        {"status": str(s), "count": int(c), "percentage": round(c / total * 100, 1)}
        for s, c in counts.items()
    ]


def heatmap_data(sample_size: int = 10000) -> list[dict]:
    """Return lat/lng/intensity points for frontend heatmap rendering."""
    df = store.df[["Latitude", "Longitude", "MaxPowerKW"]].copy()
    if len(df) > sample_size:
        df = df.sample(n=sample_size, random_state=42)
    # Normalize power as intensity (0–1)
    max_power = df["MaxPowerKW"].max()
    df["intensity"] = (df["MaxPowerKW"] / max_power).clip(0.1, 1.0)
    return df[["Latitude", "Longitude", "intensity"]].to_dict(orient="records")


def country_growth_timeseries(top_n: int = 5) -> dict:
    """Year-by-year station counts for top N countries."""
    top = store.df["Country"].value_counts().head(top_n).index.tolist()
    subset = store.df[store.df["Country"].isin(top)]
    pivot = (
        subset.groupby(["YearCreated", "Country"])
        .size()
        .unstack(fill_value=0)
        .cumsum()
    )
    result = {}
    for country in pivot.columns:
        result[country] = [
            {"year": int(y), "cumulative": int(v)}
            for y, v in pivot[country].items()
        ]
    return result
