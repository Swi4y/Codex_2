from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict

import pandas as pd


def write_artifacts(
    case_id: str,
    audit_run_id: str,
    tables: Dict[str, pd.DataFrame],
    qc_issues: pd.DataFrame,
    config: dict,
    input_doc_ids: Dict[str, str],
) -> Dict[str, str]:
    base = Path("artifacts") / case_id / audit_run_id
    base.mkdir(parents=True, exist_ok=True)
    artifact_paths: Dict[str, str] = {}
    for name, df in tables.items():
        path = base / f"{name}.csv"
        df.to_csv(path, index=False)
        artifact_paths[name] = str(path)
    qc_path = base / "qc_issues.json"
    qc_issues.to_json(qc_path, orient="records", force_ascii=False, indent=2)
    artifact_paths["qc_issues"] = str(qc_path)
    audit_run_record = {
        "audit_run_id": audit_run_id,
        "case_id": case_id,
        "created_at": datetime.utcnow().isoformat(),
        "config": config,
        "input_doc_ids": input_doc_ids,
        "artifacts": artifact_paths,
    }
    record_path = base / "audit_run.json"
    record_path.write_text(json.dumps(audit_run_record, ensure_ascii=False, indent=2))
    artifact_paths["audit_run"] = str(record_path)
    return artifact_paths
