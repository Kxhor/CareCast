#!/usr/bin/env python3
"""CareCast verification script (TRD §12, AT-44).

Runs automated test suites, dependency vulnerability audits (pip-audit),
and sanity checks. Exits with non-zero exit code on any failure.
"""

from __future__ import annotations

import subprocess
import sys
from typing import NamedTuple


class CheckResult(NamedTuple):
    name: str
    passed: bool
    details: str


def run_command(name: str, cmd: list[str]) -> CheckResult:
    print(f"--> Running check: {name} ({' '.join(cmd)})")
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        passed = proc.returncode == 0
        return CheckResult(name, passed, proc.stdout)
    except Exception as err:
        return CheckResult(name, False, f"Execution failed: {err}")


def main() -> int:
    checks = [
        ("Pytest Test Suite", [sys.executable, "-m", "pytest", "-q"]),
        ("Package Import Smoke Test", [sys.executable, "-c", "import carecast"]),
        ("Dependency Vulnerability Audit", [sys.executable, "-m", "pip_audit"]),
    ]

    results: list[CheckResult] = []
    all_passed = True

    print("==================================================")
    print("CareCast Verification Suite")
    print(f"Python interpreter: {sys.executable}")
    print("==================================================")

    for name, cmd in checks:
        res = run_command(name, cmd)
        results.append(res)
        if not res.passed:
            all_passed = False
            print(f"[FAIL] {name}\nOutput:\n{res.details}")
        else:
            print(f"[PASS] {name}")

    print("\n---------------- Summary ----------------")
    for res in results:
        status = "PASS" if res.passed else "FAIL"
        print(f"[{status}] {res.name}")
    print("-----------------------------------------")

    if all_passed:
        print("ALL VERIFICATION CHECKS PASSED.")
        return 0
    else:
        print("VERIFICATION FAILED.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
