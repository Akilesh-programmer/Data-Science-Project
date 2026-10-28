"""
Data loader service — reads and preprocesses the Kaggle EV charging station CSV.
Caches the cleaned DataFrame in memory for fast API access.
"""
import os
import pandas as pd
import numpy as np
from functools import lru_cache

DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data",
    "global_ev_charging_station.csv",
)


class DataStore:
    """Singleton-ish in-memory data store."""

    _instance = None
    df: pd.DataFrame = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # ── loading & cleaning ──────────────────────────────────────
    def load(self, path: str = DATA_PATH):
        print(f"[DataStore] Loading CSV from {path} ...")
        raw = pd.read_csv(path)
        self.df = self._clean(raw)
        print(f"[DataStore] Loaded {len(self.df):,} rows, {self.df.shape[1]} cols")

    @staticmethod
    def _clean(df: pd.DataFrame) -> pd.DataFrame:
        # Drop rows with missing lat/lng
        df = df.dropna(subset=["Latitude", "Longitude"])

        # Clamp obviously wrong power values (> 1000 kW is likely data error)
        df["MaxPowerKW"] = df["MaxPowerKW"].clip(upper=1000)

        # Fill missing text fields
        text_cols = [
            "Town", "StateOrProvince", "Postcode", "UsageCost",
            "Operator", "ConnectionTypes", "AddressTitle", "UsageType", "Country", "StatusType"
        ]
        for col in text_cols:
            if col in df.columns:
                df[col] = df[col].fillna("Unknown")

        # Derive helper columns
        df["IsFastCharge"] = df["FastChargeCount"] > 0
        df["PowerCategory"] = pd.cut(
            df["MaxPowerKW"],
            bins=[0, 7, 22, 50, 150, 1000],
            labels=["Slow (≤7 kW)", "Medium (7–22 kW)", "Fast (22–50 kW)",
                     "Rapid (50–150 kW)", "Ultra-Rapid (>150 kW)"],
            include_lowest=True,
        )
        return df

    # ── query helpers ───────────────────────────────────────────
    def filter_stations(
        self,
        country: str | None = None,
        connector_type: str | None = None,
        min_power: float | None = None,
        max_power: float | None = None,
        status: str | None = None,
        year: int | None = None,
        operator: str | None = None,
        bbox: tuple | None = None,   # (min_lat, min_lng, max_lat, max_lng)
    ) -> pd.DataFrame:
        mask = pd.Series(True, index=self.df.index)
        if country:
            c_low = country.lower().strip()
            aliases = {
                "us": "united states",
                "usa": "united states",
                "uk": "united kingdom",
                "de": "germany",
                "es": "spain",
                "ca": "canada",
                "fr": "france",
                "it": "italy",
                "nl": "netherlands",
                "se": "sweden",
                "no": "norway",
                "in": "india",
                "au": "australia",
                "jp": "japan",
            }
            target = aliases.get(c_low, c_low)
            # Match exact lower or contains
            c_series = self.df["Country"].astype(str).str.lower()
            mask &= (c_series == target) | (c_series.str.contains(target, regex=False))
        if connector_type:
            mask &= self.df["ConnectionTypes"].str.contains(
                connector_type, case=False, na=False
            )
        if min_power is not None:
            mask &= self.df["MaxPowerKW"] >= min_power
        if max_power is not None:
            mask &= self.df["MaxPowerKW"] <= max_power
        if status:
            mask &= self.df["StatusType"].str.lower() == status.lower()
        if year is not None:
            mask &= self.df["YearCreated"] == year
        if operator:
            mask &= self.df["Operator"].str.contains(
                operator, case=False, na=False
            )
        if bbox:
            min_lat, min_lng, max_lat, max_lng = bbox
            mask &= (
                (self.df["Latitude"] >= min_lat)
                & (self.df["Latitude"] <= max_lat)
                & (self.df["Longitude"] >= min_lng)
                & (self.df["Longitude"] <= max_lng)
            )
        return self.df[mask]

    def get_station_by_id(self, station_id: int) -> dict | None:
        row = self.df[self.df["StationID"] == station_id]
        if row.empty:
            return None
        return row.iloc[0].to_dict()


# Module-level convenience
store = DataStore()
