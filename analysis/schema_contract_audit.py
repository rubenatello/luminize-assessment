"""Compare a CSV header with an approved schema contract.

Exit codes: 0 = pass/info, 2 = warning, 3 = blocking drift.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("contract_path", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    contract = json.loads(args.contract_path.read_text(encoding="utf-8"))
    with args.csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        observed = next(csv.reader(handle))

    expected = [column["name"] for column in contract["columns"]]
    required = {
        column["name"] for column in contract["columns"] if column.get("required")
    }
    duplicate_columns = sorted(
        name for name, count in Counter(observed).items() if count > 1
    )
    added = [name for name in observed if name not in expected]
    removed = [name for name in expected if name not in observed]
    missing_required = [name for name in expected if name in required and name not in observed]
    order_changed = not added and not removed and observed != expected

    if duplicate_columns or missing_required:
        severity, status, exit_code = "ERROR", "BLOCK", 3
    elif added or removed:
        severity, status, exit_code = "WARN", "REVIEW", 2
    elif order_changed:
        severity, status, exit_code = "INFO", "PASS", 0
    else:
        severity, status, exit_code = "NONE", "PASS", 0

    payload = {
        "audited_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_file": str(args.csv_path),
        "contract_file": str(args.contract_path),
        "contract_version": contract["contract_version"],
        "schema_hash": hashlib.sha256(
            json.dumps(observed, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "status": status,
        "severity": severity,
        "observed_columns": observed,
        "added_columns": added,
        "removed_columns": removed,
        "missing_required_columns": missing_required,
        "duplicate_columns": duplicate_columns,
        "order_changed": order_changed,
    }
    rendered = json.dumps(payload, indent=2)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
