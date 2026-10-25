#!/usr/bin/env python3
"""Lightweight evaluation for chunking-method predictions.

Usage:
    python eval_chunking_decisions.py --dataset path/to/examples.json

Expected dataset format:
    [
      {"path": "samples/structured_report.pdf", "expected": "hierarchical"},
      {"path": "samples/notes.txt", "expected": "recursive"}
    ]

You may also pass a dict with a "cases" key.
"""

import argparse
import json
from pathlib import Path

from utils import choose_chunking_method


def _load_cases(path: str) -> list[dict]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        if "cases" in payload:
            return payload["cases"]
        raise ValueError("JSON dataset must contain a list of cases or a 'cases' key.")
    if isinstance(payload, list):
        return payload
    raise ValueError("Dataset must be a JSON list or a dict with a 'cases' list.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate chunking method predictions.")
    parser.add_argument("--dataset", required=True, help="Path to a JSON dataset of labeled examples.")
    parser.add_argument("--show-reasons", action="store_true", help="Print the rule reason for each case.")
    args = parser.parse_args()

    cases = _load_cases(args.dataset)
    if not cases:
        raise ValueError("The dataset is empty.")

    total = 0
    correct = 0

    for index, item in enumerate(cases, start=1):
        total += 1
        path = item["path"]
        expected = item["expected"]
        result = choose_chunking_method(path)
        predicted = result["chunking_method"]
        is_correct = predicted == expected
        correct += int(is_correct)

        status = "PASS" if is_correct else "FAIL"
        print(f"[{index}/{total}] {status} {path}: predicted={predicted}, expected={expected}")
        if args.show_reasons:
            print(f"  reason: {result['reason']}")

    accuracy = correct / total if total else 0.0
    print(f"\nAccuracy: {accuracy:.2%} ({correct}/{total})")


if __name__ == "__main__":
    main()

