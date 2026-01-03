from __future__ import annotations

import hashlib
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, Optional

import pandas as pd
from zoneinfo import ZoneInfo


def stable_hash(parts: Iterable[object]) -> str:
    joined = "|".join("" if part is None else str(part) for part in parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


def ensure_timezone(dt_series: pd.Series, timezone: str) -> pd.Series:
    tz = ZoneInfo(timezone)

    def _localize(value: Optional[pd.Timestamp]) -> Optional[pd.Timestamp]:
        if pd.isna(value):
            return value
        if value.tzinfo is None:
            return value.tz_localize(tz)
        return value.tz_convert(tz)

    return dt_series.apply(_localize)


def to_date_iso(dt_series: pd.Series) -> pd.Series:
    return dt_series.dt.date.astype("string")


def round_amount(series: pd.Series, policy: str) -> pd.Series:
    if policy == "kopeks_exact":
        return series.astype(float)
    if policy != "rubles_round":
        raise ValueError(f"Unknown rounding policy: {policy}")

    def _round(value: object) -> Optional[int]:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        decimal = Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return int(decimal)

    return series.apply(_round)


def map_store_id(store_raw: str, mapping_rules: list[dict]) -> Optional[str]:
    if store_raw is None or (isinstance(store_raw, float) and pd.isna(store_raw)):
        return None
    raw_lower = store_raw.lower()
    for rule in mapping_rules:
        store_id = rule.get("store_id")
        for pattern in rule.get("patterns", []):
            if pattern.lower() in raw_lower:
                return store_id
    return None


def parse_datetime(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce")


def normalize_boolean(series: pd.Series) -> pd.Series:
    def _to_bool(value: object) -> bool:
        if isinstance(value, bool):
            return value
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return False
        if isinstance(value, (int, float)):
            return bool(value)
        value_str = str(value).strip().lower()
        return value_str in {"1", "true", "yes", "y", "refund"}

    return series.apply(_to_bool)
