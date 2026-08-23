"""Command-line evaluation report generator."""

import argparse
import json
from pathlib import Path

from support_agent.services.evaluation_report import evaluate


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate the support agent gold cases")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = evaluate(args.data_dir)
    document = json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(document, encoding="utf-8")
    print(document, end="")
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
