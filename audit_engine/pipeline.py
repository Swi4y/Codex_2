from __future__ import annotations

from dataclasses import asdict
from typing import Dict, List, Tuple

import pandas as pd

from .models import AuditConfig, QCIssue
from .splitter import split_amount
from .utils import (
    ensure_timezone,
    map_store_id,
    normalize_boolean,
    parse_datetime,
    round_amount,
    stable_hash,
    to_date_iso,
)


def _doc_class(doc_type: object) -> str:
    doc_value = str(doc_type).strip().lower()
    if doc_value.startswith("correction"):
        return "correction"
    if doc_value == "refund":
        return "refund"
    return "sale"


def ingest_parse(
    input_doc_ids: Dict[str, str],
    qc_issues: List[QCIssue],
) -> Dict[str, pd.DataFrame]:
    datasets: Dict[str, pd.DataFrame] = {}
    required_columns = {
        "bank_acquiring": {"datetime", "amount", "store_raw"},
        "bank_sbp": {"datetime", "amount", "store_raw"},
        "ofd_export": {
            "datetime",
            "amount_total",
            "amount_cash",
            "amount_cashless",
            "store_raw",
            "doc_type",
        },
    }
    for doc_type, path in input_doc_ids.items():
        df = pd.read_csv(path)
        missing = required_columns.get(doc_type, set()) - set(df.columns)
        if missing:
            qc_issues.append(
                QCIssue(
                    code="MISSING_REQUIRED_COLUMNS",
                    severity="fatal",
                    store_id=None,
                    date=None,
                    entity_id=doc_type,
                    message=f"Missing required columns: {sorted(missing)}",
                    details_json={"doc_type": doc_type, "missing": sorted(missing)},
                )
            )
        datasets[doc_type] = df
    return datasets


def normalize_bank(
    df: pd.DataFrame,
    config: AuditConfig,
    source: str,
    qc_issues: List[QCIssue],
) -> pd.DataFrame:
    df = df.copy()
    df["source"] = source
    df["datetime"] = parse_datetime(df["datetime"])
    df["datetime"] = ensure_timezone(df["datetime"], config.timezone)
    invalid_dt = df["datetime"].isna()
    for idx in df[invalid_dt].index:
        qc_issues.append(
            QCIssue(
                code="INVALID_DATETIME_PARSE",
                severity="fatal",
                store_id=None,
                date=None,
                entity_id=str(idx),
                message="Invalid datetime in bank transaction",
                details_json={"row_index": int(idx), "source": source},
            )
        )
    df = df[~invalid_dt].copy()
    df["date"] = to_date_iso(df["datetime"])
    df["amount"] = round_amount(df["amount"], config.rounding_policy)
    invalid_amount = df["amount"].isna()
    for idx in df[invalid_amount].index:
        qc_issues.append(
            QCIssue(
                code="INVALID_AMOUNT_PARSE",
                severity="fatal",
                store_id=None,
                date=None,
                entity_id=str(idx),
                message="Invalid amount in bank transaction",
                details_json={"row_index": int(idx), "source": source},
            )
        )
    df = df[~invalid_amount].copy()
    df["is_refund"] = (
        normalize_boolean(df["is_refund"])
        if "is_refund" in df.columns
        else df["amount"].astype(float) < 0
    )
    df["amount"] = df["amount"].abs()
    df["store_id"] = df["store_raw"].apply(
        lambda value: map_store_id(value, config.store_mapping_rules)
    )
    unmapped = df["store_id"].isna()
    for idx in df[unmapped].index:
        qc_issues.append(
            QCIssue(
                code="UNMAPPED_STORE_BANK",
                severity="fatal" if config.unmapped_policy == "fail" else "warn",
                store_id=None,
                date=None,
                entity_id=str(idx),
                message="Unmapped store in bank transaction",
                details_json={"row_index": int(idx), "store_raw": df.at[idx, "store_raw"]},
            )
        )
    if config.unmapped_policy == "fail" and unmapped.any():
        df = df[~unmapped].copy()
    df["bank_tx_id"] = df.get("bank_tx_id")
    missing_id = df["bank_tx_id"].isna()
    for idx in df[missing_id].index:
        df.at[idx, "bank_tx_id"] = stable_hash(
            [
                df.at[idx, "source"],
                df.at[idx, "datetime"],
                df.at[idx, "amount"],
                df.at[idx, "store_raw"],
                idx,
            ]
        )
    return df


def normalize_ofd(
    df: pd.DataFrame,
    config: AuditConfig,
    qc_issues: List[QCIssue],
) -> pd.DataFrame:
    df = df.copy()
    df["datetime"] = parse_datetime(df["datetime"])
    df["datetime"] = ensure_timezone(df["datetime"], config.timezone)
    invalid_dt = df["datetime"].isna()
    for idx in df[invalid_dt].index:
        qc_issues.append(
            QCIssue(
                code="INVALID_DATETIME_PARSE",
                severity="fatal",
                store_id=None,
                date=None,
                entity_id=str(idx),
                message="Invalid datetime in OFD document",
                details_json={"row_index": int(idx)},
            )
        )
    df = df[~invalid_dt].copy()
    df["date"] = to_date_iso(df["datetime"])
    for field in ["amount_total", "amount_cash", "amount_cashless"]:
        df[field] = round_amount(df[field], config.rounding_policy)
        invalid_amount = df[field].isna()
        for idx in df[invalid_amount].index:
            qc_issues.append(
                QCIssue(
                    code="INVALID_AMOUNT_PARSE",
                    severity="fatal",
                    store_id=None,
                    date=None,
                    entity_id=str(idx),
                    message=f"Invalid {field} in OFD document",
                    details_json={"row_index": int(idx), "field": field},
                )
            )
        df = df[~invalid_amount].copy()
    df["store_id"] = df["store_raw"].apply(
        lambda value: map_store_id(value, config.store_mapping_rules)
    )
    unmapped = df["store_id"].isna()
    for idx in df[unmapped].index:
        qc_issues.append(
            QCIssue(
                code="UNMAPPED_STORE_OFD",
                severity="fatal" if config.unmapped_policy == "fail" else "warn",
                store_id=None,
                date=None,
                entity_id=str(idx),
                message="Unmapped store in OFD document",
                details_json={"row_index": int(idx), "store_raw": df.at[idx, "store_raw"]},
            )
        )
    if config.unmapped_policy == "fail" and unmapped.any():
        df = df[~unmapped].copy()
    if "sign" not in df.columns:
        def _sign(doc_type: object) -> int:
            doc_value = str(doc_type).strip().lower()
            if doc_value.startswith("correction-") or doc_value == "refund":
                return -1
            return 1

        df["sign"] = df["doc_type"].apply(_sign)
    df["doc_class"] = df["doc_type"].apply(_doc_class)
    df["ofd_doc_id"] = df.get("ofd_doc_id")
    missing_id = df["ofd_doc_id"].isna()
    for idx in df[missing_id].index:
        df.at[idx, "ofd_doc_id"] = stable_hash(
            [
                df.at[idx, "datetime"],
                df.at[idx, "amount_total"],
                df.at[idx, "store_raw"],
                idx,
            ]
        )
    return df


def filter_by_period(
    df: pd.DataFrame,
    config: AuditConfig,
    qc_issues: List[QCIssue],
    entity_name: str,
) -> pd.DataFrame:
    df = df.copy()
    period_mask = (df["date"] >= str(config.period_from)) & (
        df["date"] <= str(config.period_to)
    )
    out_of_range = ~period_mask
    for idx in df[out_of_range].index:
        qc_issues.append(
            QCIssue(
                code="PERIOD_OUT_OF_RANGE_ROW",
                severity="warn",
                store_id=df.at[idx, "store_id"] if "store_id" in df.columns else None,
                date=df.at[idx, "date"] if "date" in df.columns else None,
                entity_id=str(idx),
                message=f"{entity_name} row outside period",
                details_json={"row_index": int(idx), "entity": entity_name},
            )
        )
    return df[period_mask].copy()


def aggregate_bank(bank_df: pd.DataFrame) -> pd.DataFrame:
    df = bank_df.copy()
    df["amount_signed"] = df.apply(
        lambda row: -row["amount"] if row["is_refund"] else row["amount"], axis=1
    )
    grouped = (
        df.groupby(["store_id", "date", "source"], as_index=False)["amount_signed"].sum()
    )
    bank_rows = df.groupby(["store_id", "date"], as_index=False).size()
    bank_rows.rename(columns={"size": "bank_rows"}, inplace=True)
    card = grouped[grouped["source"] == "acquiring"].rename(
        columns={"amount_signed": "bank_card"}
    )
    sbp = grouped[grouped["source"] == "sbp"].rename(
        columns={"amount_signed": "bank_sbp"}
    )
    merged = pd.merge(card, sbp, on=["store_id", "date"], how="outer")
    merged["bank_card"] = merged["bank_card"].fillna(0)
    merged["bank_sbp"] = merged["bank_sbp"].fillna(0)
    merged["bank_total"] = merged["bank_card"] + merged["bank_sbp"]
    merged = pd.merge(merged, bank_rows, on=["store_id", "date"], how="left")
    merged["bank_rows"] = merged["bank_rows"].fillna(0).astype(int)
    return merged.sort_values(["store_id", "date"]).reset_index(drop=True)


def compute_ofd_cashless(ofd_df: pd.DataFrame, config: AuditConfig) -> pd.DataFrame:
    df = ofd_df.copy()
    if config.ofddoc_inclusion_mode == "without_corr":
        df = df[df["doc_class"] != "correction"].copy()
    df["cashless_contrib"] = df["amount_cashless"] * df["sign"]
    grouped = df.groupby(["store_id", "date"], as_index=False).agg(
        ofd_cashless=("cashless_contrib", "sum"), ofd_rows=("ofd_doc_id", "size")
    )
    return grouped.sort_values(["store_id", "date"]).reset_index(drop=True)


def reconcile_daily(
    bank_daily: pd.DataFrame,
    ofd_daily: pd.DataFrame,
    qc_issues: List[QCIssue],
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    merged = pd.merge(bank_daily, ofd_daily, on=["store_id", "date"], how="outer")
    merged["bank_total"] = merged["bank_total"].fillna(0)
    merged["ofd_cashless"] = merged["ofd_cashless"].fillna(0)
    merged["bank_card"] = merged["bank_card"].fillna(0)
    merged["bank_sbp"] = merged["bank_sbp"].fillna(0)
    merged["bank_rows"] = merged["bank_rows"].fillna(0).astype(int)
    merged["ofd_rows"] = merged["ofd_rows"].fillna(0).astype(int)
    merged["diff"] = merged["bank_total"] - merged["ofd_cashless"]
    coverage = merged[
        ["store_id", "date", "bank_total", "ofd_cashless", "diff", "bank_rows", "ofd_rows"]
    ].copy()
    coverage["has_bank"] = coverage["bank_rows"] > 0
    coverage["has_ofd"] = coverage["ofd_rows"] > 0
    coverage["coverage_flag"] = coverage.apply(_coverage_flag, axis=1)
    for _, row in coverage.iterrows():
        if row["coverage_flag"] == "bank_only":
            qc_issues.append(
                QCIssue(
                    code="COVERAGE_BANK_ONLY_DAY",
                    severity="warn",
                    store_id=row["store_id"],
                    date=row["date"],
                    entity_id=None,
                    message="Bank data only for day",
                    details_json={},
                )
            )
        if row["coverage_flag"] == "ofd_only":
            qc_issues.append(
                QCIssue(
                    code="COVERAGE_OFD_ONLY_DAY",
                    severity="warn",
                    store_id=row["store_id"],
                    date=row["date"],
                    entity_id=None,
                    message="OFD data only for day",
                    details_json={},
                )
            )
        if row["diff"] < 0:
            qc_issues.append(
                QCIssue(
                    code="NEGATIVE_DIFF_DAY",
                    severity="warn",
                    store_id=row["store_id"],
                    date=row["date"],
                    entity_id=None,
                    message="Negative diff on day",
                    details_json={"diff": row["diff"]},
                )
            )
    daily_reconciliation = merged[
        ["store_id", "date", "bank_card", "bank_sbp", "bank_total", "ofd_cashless", "diff"]
    ].sort_values(["store_id", "date"])
    coverage_output = coverage[
        [
            "store_id",
            "date",
            "has_bank",
            "has_ofd",
            "bank_total",
            "ofd_cashless",
            "coverage_flag",
        ]
    ]
    return (
        daily_reconciliation.reset_index(drop=True),
        coverage_output.sort_values(["store_id", "date"]).reset_index(drop=True),
    )


def _coverage_flag(row: pd.Series) -> str:
    if row["has_bank"] and row["has_ofd"]:
        return "ok"
    if row["has_bank"] and not row["has_ofd"]:
        return "bank_only"
    if not row["has_bank"] and row["has_ofd"]:
        return "ofd_only"
    return "none"


def find_collisions_cash_to_cashless(
    bank_df: pd.DataFrame,
    ofd_df: pd.DataFrame,
    config: AuditConfig,
    qc_issues: List[QCIssue],
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    bank_candidates = bank_df[~bank_df["is_refund"]].copy()
    ofd_candidates = ofd_df[
        (ofd_df["amount_cash"] > 0) & (ofd_df["amount_cashless"] == 0)
    ].copy()
    ofd_candidates = ofd_candidates.sort_values(["store_id", "datetime", "ofd_doc_id"])
    bank_candidates = bank_candidates.sort_values(["store_id", "datetime", "bank_tx_id"])

    bank_to_ofd: Dict[str, List[str]] = {}
    ofd_to_bank: Dict[str, List[str]] = {}
    for _, bank_row in bank_candidates.iterrows():
        candidates = ofd_candidates[
            (ofd_candidates["store_id"] == bank_row["store_id"])
            & (ofd_candidates["amount_cash"].sub(bank_row["amount"]).abs()
               <= config.amount_tolerance)
            & (
                ofd_candidates["datetime"].sub(bank_row["datetime"]).abs().dt.total_seconds()
                <= config.matching_window_seconds
            )
        ]
        bank_to_ofd[bank_row["bank_tx_id"]] = candidates["ofd_doc_id"].tolist()
        for ofd_id in candidates["ofd_doc_id"].tolist():
            ofd_to_bank.setdefault(ofd_id, []).append(bank_row["bank_tx_id"])

    collisions = []
    for bank_id, ofd_ids in bank_to_ofd.items():
        if len(ofd_ids) > 1:
            qc_issues.append(
                QCIssue(
                    code="AMBIGUOUS_MATCH_BANK_TX",
                    severity="warn",
                    store_id=None,
                    date=None,
                    entity_id=bank_id,
                    message="Bank transaction has multiple match candidates",
                    details_json={"candidates": ofd_ids},
                )
            )
    for ofd_id, bank_ids in ofd_to_bank.items():
        if len(bank_ids) > 1:
            qc_issues.append(
                QCIssue(
                    code="AMBIGUOUS_MATCH_OFD_DOC",
                    severity="warn",
                    store_id=None,
                    date=None,
                    entity_id=ofd_id,
                    message="OFD document has multiple match candidates",
                    details_json={"candidates": bank_ids},
                )
            )

    for bank_id, ofd_ids in bank_to_ofd.items():
        if len(ofd_ids) != 1:
            continue
        ofd_id = ofd_ids[0]
        if len(ofd_to_bank.get(ofd_id, [])) != 1:
            continue
        bank_row = bank_candidates[bank_candidates["bank_tx_id"] == bank_id].iloc[0]
        ofd_row = ofd_candidates[ofd_candidates["ofd_doc_id"] == ofd_id].iloc[0]
        delta = abs((ofd_row["datetime"] - bank_row["datetime"]).total_seconds())
        collisions.append(
            {
                "store_id": bank_row["store_id"],
                "date": bank_row["date"],
                "bank_tx_id": bank_id,
                "ofd_doc_id": ofd_id,
                "amount": bank_row["amount"],
                "bank_datetime": bank_row["datetime"],
                "ofd_datetime": ofd_row["datetime"],
                "time_delta_sec": int(delta),
                "rule": "store+amount+timewindow+mutual_unique",
                "notes": None,
            }
        )
    collisions_df = pd.DataFrame(collisions)
    if collisions_df.empty:
        collisions_df = pd.DataFrame(
            columns=[
                "store_id",
                "date",
                "bank_tx_id",
                "ofd_doc_id",
                "amount",
                "bank_datetime",
                "ofd_datetime",
                "time_delta_sec",
                "rule",
                "notes",
            ]
        )
    if collisions_df.empty:
        cash_to_cashless_daily = pd.DataFrame(
            columns=["store_id", "date", "cash_to_cashless_sum", "pairs_count"]
        )
    else:
        cash_to_cashless_daily = (
            collisions_df.groupby(["store_id", "date"], as_index=False)
            .agg(cash_to_cashless_sum=("amount", "sum"), pairs_count=("amount", "size"))
        )
    collisions_registry = collisions_df.drop(columns=["date"]).copy()
    return (
        collisions_registry.sort_values(["store_id", "bank_tx_id", "ofd_doc_id"]).reset_index(
            drop=True
        ),
        cash_to_cashless_daily.sort_values(["store_id", "date"]).reset_index(drop=True),
    )


def compute_correction_plan(
    daily_reconciliation: pd.DataFrame,
    cash_to_cashless_daily: pd.DataFrame,
    config: AuditConfig,
    qc_issues: List[QCIssue],
) -> pd.DataFrame:
    correction = pd.merge(
        daily_reconciliation,
        cash_to_cashless_daily,
        on=["store_id", "date"],
        how="left",
    )
    correction["cash_to_cashless_sum"] = correction["cash_to_cashless_sum"].fillna(0)
    correction["diff_after"] = correction["diff"] - correction["cash_to_cashless_sum"]
    correction["to_correct"] = correction["diff_after"].apply(lambda value: max(0, value))
    plan_rows = []
    for _, row in correction.iterrows():
        split = split_amount(int(row["to_correct"]), config.split_policy)
        if split.status == "split_failed":
            qc_issues.append(
                QCIssue(
                    code="SPLIT_FAILED",
                    severity="warn",
                    store_id=row["store_id"],
                    date=row["date"],
                    entity_id=None,
                    message="Failed to split correction amount",
                    details_json={"to_correct": row["to_correct"]},
                )
            )
        n_parts = len(split.parts)
        parts = split.parts + [None] * (4 - n_parts)
        plan_rows.append(
            {
                "store_id": row["store_id"],
                "date": row["date"],
                "diff_after": row["diff_after"],
                "to_correct": row["to_correct"],
                "n_parts": n_parts if split.status == "ok" else 0,
                "part1": parts[0],
                "part2": parts[1],
                "part3": parts[2],
                "part4": parts[3],
                "split_status": split.status,
            }
        )
    return pd.DataFrame(plan_rows).sort_values(["store_id", "date"]).reset_index(drop=True)


def final_qc(
    daily_reconciliation: pd.DataFrame,
    cash_to_cashless_daily: pd.DataFrame,
    correction_plan: pd.DataFrame,
    qc_issues: List[QCIssue],
) -> None:
    merged = pd.merge(
        daily_reconciliation,
        cash_to_cashless_daily,
        on=["store_id", "date"],
        how="left",
    )
    merged = pd.merge(
        merged,
        correction_plan[["store_id", "date", "diff_after", "to_correct"]],
        on=["store_id", "date"],
        how="left",
    )
    merged["cash_to_cashless_sum"] = merged["cash_to_cashless_sum"].fillna(0)
    merged["diff_after"] = merged["diff_after"].fillna(merged["diff"])
    merged["to_correct"] = merged["to_correct"].fillna(0)
    for _, row in merged.iterrows():
        expected = row["diff"] - row["cash_to_cashless_sum"]
        if expected != row["diff_after"]:
            qc_issues.append(
                QCIssue(
                    code="BALANCE_IDENTITY_DIFF_AFTER_MISMATCH",
                    severity="warn",
                    store_id=row["store_id"],
                    date=row["date"],
                    entity_id=None,
                    message="Balance identity mismatch",
                    details_json={"expected": expected, "diff_after": row["diff_after"]},
                )
            )
        if row["to_correct"] != max(0, row["diff_after"]):
            qc_issues.append(
                QCIssue(
                    code="BALANCE_IDENTITY_TO_CORRECT_MISMATCH",
                    severity="warn",
                    store_id=row["store_id"],
                    date=row["date"],
                    entity_id=None,
                    message="to_correct mismatch with diff_after",
                    details_json={
                        "to_correct": row["to_correct"],
                        "diff_after": row["diff_after"],
                    },
                )
            )


def qc_issues_to_frame(qc_issues: List[QCIssue]) -> pd.DataFrame:
    if not qc_issues:
        return pd.DataFrame(
            columns=["code", "severity", "store_id", "date", "entity_id", "message", "details_json"]
        )
    return pd.DataFrame([asdict(issue) for issue in qc_issues]).sort_values(
        ["severity", "code"], ignore_index=True
    )

