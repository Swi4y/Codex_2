from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Literal, Optional

Severity = Literal["fatal", "warn", "info"]


@dataclass(frozen=True)
class SplitPolicy:
    try_n_parts: List[int]
    min_pct: float
    max_pct: float
    require_distinct: bool
    parts_must_be_positive: bool


@dataclass(frozen=True)
class AuditConfig:
    period_from: date
    period_to: date
    timezone: str
    store_mapping_rules: List[Dict[str, Any]]
    unmapped_policy: Literal["fail", "allow_with_qc"]
    ofddoc_inclusion_mode: Literal["with_corr", "without_corr"]
    matching_window_seconds: int
    amount_tolerance: float
    rounding_policy: Literal["rubles_round", "kopeks_exact"]
    split_policy: SplitPolicy


@dataclass
class QCIssue:
    code: str
    severity: Severity
    store_id: Optional[str]
    date: Optional[str]
    entity_id: Optional[str]
    message: str
    details_json: Dict[str, Any] = field(default_factory=dict)


QCErrorCodes = {
    "UNMAPPED_STORE_BANK",
    "UNMAPPED_STORE_OFD",
    "INVALID_DATETIME_PARSE",
    "INVALID_AMOUNT_PARSE",
    "PERIOD_OUT_OF_RANGE_ROW",
    "MISSING_REQUIRED_COLUMNS",
    "BANK_EMPTY_AFTER_FILTER",
    "OFD_EMPTY_AFTER_FILTER",
    "COVERAGE_BANK_ONLY_DAY",
    "COVERAGE_OFD_ONLY_DAY",
    "NEGATIVE_DIFF_DAY",
    "AMBIGUOUS_MATCH_BANK_TX",
    "AMBIGUOUS_MATCH_OFD_DOC",
    "SPLIT_FAILED",
    "CORR_MODE_SENSITIVITY",
    "ROWS_REMOVED_AS_NONRELEVANT",
    "ROUNDING_APPLIED",
    "TIMEZONE_ASSUMED",
    "BALANCE_IDENTITY_DIFF_AFTER_MISMATCH",
    "BALANCE_IDENTITY_TO_CORRECT_MISMATCH",
}
