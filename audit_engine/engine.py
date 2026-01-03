from __future__ import annotations

import uuid
from dataclasses import asdict
from typing import Dict, Iterable, List

import pandas as pd

from .models import AuditConfig, QCIssue
from .pipeline import (
    aggregate_bank,
    compute_correction_plan,
    compute_ofd_cashless,
    filter_by_period,
    find_collisions_cash_to_cashless,
    final_qc,
    ingest_parse,
    normalize_bank,
    normalize_ofd,
    qc_issues_to_frame,
    reconcile_daily,
)
from .storage import write_artifacts


def run_audit(
    case_id: str,
    input_doc_ids: Dict[str, str],
    config: AuditConfig,
) -> str:
    audit_run_id = uuid.uuid4().hex
    qc_issues: List[QCIssue] = []
    datasets = ingest_parse(input_doc_ids, qc_issues)

    bank_frames: List[pd.DataFrame] = []
    if "bank_acquiring" in datasets:
        bank_frames.append(normalize_bank(datasets["bank_acquiring"], config, "acquiring", qc_issues))
    if "bank_sbp" in datasets:
        bank_frames.append(normalize_bank(datasets["bank_sbp"], config, "sbp", qc_issues))
    bank_df = pd.concat(bank_frames, ignore_index=True) if bank_frames else pd.DataFrame()
    if bank_df.empty:
        qc_issues.append(
            QCIssue(
                code="BANK_EMPTY_AFTER_FILTER",
                severity="fatal",
                store_id=None,
                date=None,
                entity_id=None,
                message="No bank rows after normalization",
                details_json={},
            )
        )
    ofd_df = (
        normalize_ofd(datasets["ofd_export"], config, qc_issues)
        if "ofd_export" in datasets
        else pd.DataFrame()
    )
    if ofd_df.empty:
        qc_issues.append(
            QCIssue(
                code="OFD_EMPTY_AFTER_FILTER",
                severity="fatal",
                store_id=None,
                date=None,
                entity_id=None,
                message="No OFD rows after normalization",
                details_json={},
            )
        )

    if not bank_df.empty:
        bank_df = filter_by_period(bank_df, config, qc_issues, "bank")
    if not ofd_df.empty:
        ofd_df = filter_by_period(ofd_df, config, qc_issues, "ofd")

    if any(issue.severity == "fatal" for issue in qc_issues):
        tables = _empty_output_tables()
        qc_frame = qc_issues_to_frame(qc_issues)
        write_artifacts(case_id, audit_run_id, tables, qc_frame, asdict(config), input_doc_ids)
        return audit_run_id

    bank_daily = aggregate_bank(bank_df) if not bank_df.empty else pd.DataFrame(
        columns=["store_id", "date", "bank_card", "bank_sbp", "bank_total", "bank_rows"]
    )
    ofd_daily = (
        compute_ofd_cashless(ofd_df, config)
        if not ofd_df.empty
        else pd.DataFrame(columns=["store_id", "date", "ofd_cashless", "ofd_rows"])
    )
    daily_reconciliation, coverage_matrix = reconcile_daily(
        bank_daily, ofd_daily, qc_issues
    )
    collisions_registry, cash_to_cashless_daily = find_collisions_cash_to_cashless(
        bank_df, ofd_df, config, qc_issues
    )
    correction_plan = compute_correction_plan(
        daily_reconciliation, cash_to_cashless_daily, config, qc_issues
    )
    final_qc(daily_reconciliation, cash_to_cashless_daily, correction_plan, qc_issues)

    tables = {
        "daily_reconciliation": daily_reconciliation,
        "collisions_registry": collisions_registry,
        "cash_to_cashless_daily": cash_to_cashless_daily,
        "correction_plan": correction_plan,
        "coverage_matrix": coverage_matrix,
    }
    qc_frame = qc_issues_to_frame(qc_issues)
    write_artifacts(case_id, audit_run_id, tables, qc_frame, asdict(config), input_doc_ids)
    return audit_run_id


def _empty_output_tables() -> Dict[str, pd.DataFrame]:
    return {
        "daily_reconciliation": pd.DataFrame(
            columns=[
                "store_id",
                "date",
                "bank_card",
                "bank_sbp",
                "bank_total",
                "ofd_cashless",
                "diff",
            ]
        ),
        "collisions_registry": pd.DataFrame(
            columns=[
                "store_id",
                "bank_tx_id",
                "ofd_doc_id",
                "amount",
                "bank_datetime",
                "ofd_datetime",
                "time_delta_sec",
                "rule",
                "notes",
            ]
        ),
        "cash_to_cashless_daily": pd.DataFrame(
            columns=["store_id", "date", "cash_to_cashless_sum", "pairs_count"]
        ),
        "correction_plan": pd.DataFrame(
            columns=[
                "store_id",
                "date",
                "diff_after",
                "to_correct",
                "n_parts",
                "part1",
                "part2",
                "part3",
                "part4",
                "split_status",
            ]
        ),
        "coverage_matrix": pd.DataFrame(
            columns=[
                "store_id",
                "date",
                "has_bank",
                "has_ofd",
                "bank_total",
                "ofd_cashless",
                "coverage_flag",
            ]
        ),
    }
