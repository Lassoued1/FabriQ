from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.agent import answer_question
from app.database import SQLiteDatabase, create_database_from_env


GOLDEN_FILE = ROOT / "evaluation" / "golden.json"
PARAPHRASE_FILE = ROOT / "evaluation" / "paraphrases.json"
GERMAN_FILE = ROOT / "evaluation" / "german.json"
REPORT_DIR = ROOT / "reports"
EVALUATION_SUITES = {
    "golden": GOLDEN_FILE,
    "paraphrases": PARAPHRASE_FILE,
    "german": GERMAN_FILE,
}
REPORT_FILES = {
    "golden": REPORT_DIR / "evaluation-latest.json",
    "paraphrases": REPORT_DIR / "evaluation-paraphrases-latest.json",
    "german": REPORT_DIR / "evaluation-german-latest.json",
}


def main() -> int:
    suite = _suite_from_args(sys.argv[1:])
    if suite not in EVALUATION_SUITES:
        print(f"Unknown evaluation suite: {suite}")
        print(f"Allowed suites: {', '.join(EVALUATION_SUITES)}")
        return 2

    suite_file = EVALUATION_SUITES[suite]
    report_file = REPORT_FILES[suite]
    cases = json.loads(suite_file.read_text(encoding="utf-8"))
    database = create_database_from_env() if "--database=env" in sys.argv else SQLiteDatabase()
    results = [_evaluate_case(database, case) for case in cases]
    passed = sum(1 for result in results if result["passed"])
    total = len(results)
    report = {
        "created_at": datetime.now(UTC).isoformat(),
        "suite": suite,
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "accuracy": round(passed / total, 4) if total else 0,
        "database": database.dialect,
        "results": results,
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_file.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")

    print(f"FabriQ evaluation ({suite}): {passed}/{total} passed ({report['accuracy']:.0%})")
    print(f"Report: {report_file}")
    for result in results:
        status = "OK" if result["passed"] else "FAIL"
        print(f"- {status} {result['id']}: {', '.join(result['failures']) or 'all checks passed'}")

    return 0 if passed == total else 1


def _suite_from_args(args: list[str]) -> str:
    for arg in args:
        if arg.startswith("--suite="):
            return arg.split("=", 1)[1].strip() or "golden"

    return "golden"


def _evaluate_case(connection: Any, case: dict[str, Any]) -> dict[str, Any]:
    response = answer_question(connection, case["question"])
    failures: list[str] = []

    # Cas negatifs : la question est hors perimetre ou dangereuse, la seule
    # reponse valide est une demande de clarification sans aucune execution.
    if case.get("expects_clarification"):
        if not response.needs_clarification:
            failures.append(f"expected clarification, got intent={response.intent!r}")
        if response.intent is not None:
            failures.append(f"intent routed on out-of-scope question: {response.intent!r}")
        if response.rows:
            failures.append(f"rows returned on out-of-scope question: {len(response.rows)}")
        if response.sql:
            failures.append("sql generated on out-of-scope question")
        return {
            "id": case["id"],
            "question": case["question"],
            "passed": not failures,
            "failures": failures,
            "intent": response.intent,
            "row_count": len(response.rows),
            "chart_type": None,
            "sql": response.sql,
        }

    if response.intent != case["expected_intent"]:
        failures.append(f"intent={response.intent!r}, expected={case['expected_intent']!r}")

    if not response.validation.ok:
        failures.append(f"validation blocked: {response.validation.blocked}")

    if len(response.rows) < case["min_rows"]:
        failures.append(f"row_count={len(response.rows)}, expected>={case['min_rows']}")

    if "max_rows" in case and len(response.rows) > case["max_rows"]:
        failures.append(f"row_count={len(response.rows)}, expected<={case['max_rows']}")

    if "expected_sql_contains" in case and case["expected_sql_contains"] not in (response.sql or ""):
        failures.append(f"sql does not contain {case['expected_sql_contains']!r}")

    missing_columns = sorted(set(case["required_columns"]) - set(response.columns))
    if missing_columns:
        failures.append(f"missing_columns={missing_columns}")

    chart_type = response.chart.type if response.chart else None
    if chart_type != case["expected_chart_type"]:
        failures.append(f"chart_type={chart_type!r}, expected={case['expected_chart_type']!r}")

    return {
        "id": case["id"],
        "question": case["question"],
        "passed": not failures,
        "failures": failures,
        "intent": response.intent,
        "row_count": len(response.rows),
        "chart_type": chart_type,
        "sql": response.sql,
    }


if __name__ == "__main__":
    raise SystemExit(main())
