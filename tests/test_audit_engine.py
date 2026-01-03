from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from audit_engine.engine import run_audit
from audit_engine.models import AuditConfig, SplitPolicy, QCIssue
from audit_engine.pipeline import (
    aggregate_bank,
    compute_correction_plan,
    compute_ofd_cashless,
    ingest_parse,
    find_collisions_cash_to_cashless,
    final_qc,
    normalize_bank,
    normalize_ofd,
    reconcile_daily,
)
from audit_engine.splitter import split_amount


def make_config() -> AuditConfig:
    return AuditConfig(
        period_from=date(2024, 1, 1),
        period_to=date(2024, 1, 31),
        timezone="Europe/Moscow",
        store_mapping_rules=[{"store_id": "A", "patterns": ["Store A"]}],
        unmapped_policy="allow_with_qc",
        ofddoc_inclusion_mode="with_corr",
        matching_window_seconds=120,
        amount_tolerance=0,
        rounding_policy="rubles_round",
        split_policy=SplitPolicy(
            try_n_parts=[4, 3],
            min_pct=0.20,
            max_pct=0.40,
            require_distinct=True,
            parts_must_be_positive=True,
        ),
    )


def test_normalization_rounding_and_mapping() -> None:
    config = make_config()
    qc_issues: list[QCIssue] = []
    bank_df = pd.DataFrame(
        {
            "datetime": ["2024-01-05 10:00:00"],
            "amount": [10.4],
            "store_raw": ["Store A Main"],
        }
    )
    normalized = normalize_bank(bank_df, config, "acquiring", qc_issues)
    assert normalized.loc[0, "store_id"] == "A"
    assert normalized.loc[0, "amount"] == 10
    assert normalized.loc[0, "date"] == "2024-01-05"


def test_aggregate_bank_totals() -> None:
    config = make_config()
    qc_issues: list[QCIssue] = []
    bank_df = pd.DataFrame(
        {
            "datetime": ["2024-01-05 10:00:00", "2024-01-05 11:00:00"],
            "amount": [100, 50],
            "store_raw": ["Store A Main", "Store A Main"],
        }
    )
    acquiring = normalize_bank(bank_df.iloc[[0]], config, "acquiring", qc_issues)
    sbp = normalize_bank(bank_df.iloc[[1]], config, "sbp", qc_issues)
    aggregated = aggregate_bank(pd.concat([acquiring, sbp], ignore_index=True))
    assert aggregated.loc[0, "bank_card"] == 100
    assert aggregated.loc[0, "bank_sbp"] == 50
    assert aggregated.loc[0, "bank_total"] == 150


def test_mutual_unique_matching() -> None:
    config = make_config()
    qc_issues: list[QCIssue] = []
    bank_df = pd.DataFrame(
        {
            "datetime": ["2024-01-05 10:00:00"],
            "amount": [100],
            "store_raw": ["Store A Main"],
        }
    )
    ofd_df = pd.DataFrame(
        {
            "datetime": ["2024-01-05 10:01:00"],
            "amount_total": [100],
            "amount_cash": [100],
            "amount_cashless": [0],
            "store_raw": ["Store A Main"],
            "doc_type": ["sale"],
        }
    )
    bank_norm = normalize_bank(bank_df, config, "acquiring", qc_issues)
    ofd_norm = normalize_ofd(ofd_df, config, qc_issues)
    collisions, daily = find_collisions_cash_to_cashless(
        bank_norm, ofd_norm, config, qc_issues
    )
    assert len(collisions) == 1
    assert daily.loc[0, "cash_to_cashless_sum"] == 100


def test_ingest_parse_without_source(tmp_path: Path) -> None:
    qc_issues: list[QCIssue] = []
    bank_file = tmp_path / "bank.csv"
    bank_file.write_text("datetime,amount,store_raw\n2024-01-05 10:00:00,100,Store A\n")
    datasets = ingest_parse({"bank_acquiring": str(bank_file)}, qc_issues)
    assert "bank_acquiring" in datasets
    assert not any(
        issue.code == "MISSING_REQUIRED_COLUMNS" and issue.entity_id == "bank_acquiring"
        for issue in qc_issues
    )


def test_ofd_inclusion_modes() -> None:
    config = make_config()
    qc_issues: list[QCIssue] = []
    ofd_df = pd.DataFrame(
        {
            "datetime": ["2024-01-05 10:00:00", "2024-01-05 12:00:00"],
            "amount_total": [100, 50],
            "amount_cash": [0, 0],
            "amount_cashless": [100, 50],
            "store_raw": ["Store A Main", "Store A Main"],
            "doc_type": ["sale", "correction-"],
        }
    )
    normalized = normalize_ofd(ofd_df, config, qc_issues)
    with_corr = compute_ofd_cashless(normalized, config)
    assert with_corr.loc[0, "ofd_cashless"] == 50
    assert with_corr.loc[0, "ofd_rows"] == 2
    config_without = replace(config, ofddoc_inclusion_mode="without_corr")
    without_corr = compute_ofd_cashless(normalized, config_without)
    assert without_corr.loc[0, "ofd_cashless"] == 100
    assert without_corr.loc[0, "ofd_rows"] == 1


def test_coverage_has_bank_even_if_zero() -> None:
    config = make_config()
    qc_issues: list[QCIssue] = []
    bank_df = pd.DataFrame(
        {
            "datetime": ["2024-01-05 10:00:00", "2024-01-05 11:00:00"],
            "amount": [100, 100],
            "is_refund": [False, True],
            "store_raw": ["Store A Main", "Store A Main"],
        }
    )
    bank_norm = normalize_bank(bank_df, config, "acquiring", qc_issues)
    bank_daily = aggregate_bank(bank_norm)
    ofd_daily = pd.DataFrame(columns=["store_id", "date", "ofd_cashless", "ofd_rows"])
    _, coverage = reconcile_daily(bank_daily, ofd_daily, qc_issues)
    assert bank_daily.loc[0, "bank_total"] == 0
    assert bank_daily.loc[0, "bank_rows"] == 2
    assert coverage.loc[0, "has_bank"] is True


def test_coverage_has_ofd_even_if_zero() -> None:
    config = make_config()
    qc_issues: list[QCIssue] = []
    ofd_df = pd.DataFrame(
        {
            "datetime": ["2024-01-05 10:00:00", "2024-01-05 11:00:00"],
            "amount_total": [100, 100],
            "amount_cash": [0, 0],
            "amount_cashless": [100, 100],
            "store_raw": ["Store A Main", "Store A Main"],
            "doc_type": ["sale", "refund"],
        }
    )
    ofd_norm = normalize_ofd(ofd_df, config, qc_issues)
    ofd_daily = compute_ofd_cashless(ofd_norm, config)
    bank_daily = pd.DataFrame(
        columns=["store_id", "date", "bank_card", "bank_sbp", "bank_total", "bank_rows"]
    )
    _, coverage = reconcile_daily(bank_daily, ofd_daily, qc_issues)
    assert ofd_daily.loc[0, "ofd_cashless"] == 0
    assert ofd_daily.loc[0, "ofd_rows"] == 2
    assert coverage.loc[0, "has_ofd"] is True


def test_doc_class_column_present() -> None:
    config = make_config()
    qc_issues: list[QCIssue] = []
    ofd_df = pd.DataFrame(
        {
            "datetime": ["2024-01-05 10:00:00"],
            "amount_total": [100],
            "amount_cash": [0],
            "amount_cashless": [100],
            "store_raw": ["Store A Main"],
            "doc_type": ["correction-"],
        }
    )
    normalized = normalize_ofd(ofd_df, config, qc_issues)
    assert "doc_class" in normalized.columns
    assert normalized.loc[0, "doc_class"] == "correction"


def test_balance_identity_qc_codes() -> None:
    qc_issues: list[QCIssue] = []
    daily = pd.DataFrame(
        {
            "store_id": ["A"],
            "date": ["2024-01-05"],
            "bank_card": [100],
            "bank_sbp": [0],
            "bank_total": [100],
            "ofd_cashless": [80],
            "diff": [20],
        }
    )
    cash_to_cashless = pd.DataFrame(
        {"store_id": ["A"], "date": ["2024-01-05"], "cash_to_cashless_sum": [5]}
    )
    correction_plan = pd.DataFrame(
        {
            "store_id": ["A"],
            "date": ["2024-01-05"],
            "diff_after": [10],
            "to_correct": [10],
        }
    )
    final_qc(daily, cash_to_cashless, correction_plan, qc_issues)
    assert any(
        issue.code == "BALANCE_IDENTITY_DIFF_AFTER_MISMATCH" for issue in qc_issues
    )


def test_split_algorithm_and_failure() -> None:
    policy = make_config().split_policy
    split_ok = split_amount(100, policy)
    assert split_ok.status == "ok"
    assert sum(split_ok.parts) == 100
    assert split_ok.parts == sorted(split_ok.parts)
    assert len(set(split_ok.parts)) == len(split_ok.parts)
    split_fail = split_amount(10, policy)
    assert split_fail.status == "split_failed"


def test_split_bounds_rounding() -> None:
    policy = make_config().split_policy
    split_ok = split_amount(99, policy)
    assert split_ok.status == "ok"
    assert all(20 <= part <= 39 for part in split_ok.parts)


def test_balance_identity() -> None:
    config = make_config()
    qc_issues: list[QCIssue] = []
    daily = pd.DataFrame(
        {
            "store_id": ["A"],
            "date": ["2024-01-05"],
            "bank_card": [100],
            "bank_sbp": [0],
            "bank_total": [100],
            "ofd_cashless": [80],
            "diff": [20],
        }
    )
    cash_to_cashless = pd.DataFrame(
        {"store_id": ["A"], "date": ["2024-01-05"], "cash_to_cashless_sum": [5]}
    )
    correction_plan = compute_correction_plan(
        daily, cash_to_cashless, config, qc_issues
    )
    final_qc(daily, cash_to_cashless, correction_plan, qc_issues)
    assert qc_issues == []


def test_run_audit_stops_on_fatal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = make_config()
    bank_file = tmp_path / "bank.csv"
    bank_file.write_text("datetime,amount,store_raw\ninvalid,100,Store A\n")
    ofd_file = tmp_path / "ofd.csv"
    ofd_file.write_text(
        "datetime,amount_total,amount_cash,amount_cashless,store_raw,doc_type\n"
        "2024-01-05 10:00:00,100,0,100,Store A,sale\n"
    )
    monkeypatch.chdir(tmp_path)
    audit_run_id = run_audit(
        "case-1",
        {"bank_acquiring": str(bank_file), "ofd_export": str(ofd_file)},
        config,
    )
    audit_path = tmp_path / "artifacts" / "case-1" / audit_run_id
    daily = pd.read_csv(audit_path / "daily_reconciliation.csv")
    coverage = pd.read_csv(audit_path / "coverage_matrix.csv")
    assert daily.empty
    assert coverage.empty
