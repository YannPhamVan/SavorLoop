from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / ".test-results"


def main() -> int:
    RESULTS.mkdir(exist_ok=True)
    for report in (RESULTS / "backend.xml", RESULTS / "frontend.xml"):
        report.unlink(missing_ok=True)

    checks: list[tuple[str, Sequence[str]]] = [
        (
            "Backend unit and integration tests",
            [
                sys.executable,
                "-m",
                "pytest",
                "--junitxml=.test-results/backend.xml",
            ],
        ),
        (
            "Frontend tests",
            [
                "npm",
                "--prefix",
                "frontend",
                "test",
                "--",
                "--reporter=junit",
                "--outputFile=../.test-results/frontend.xml",
            ],
        ),
        ("Frontend production build", ["npm", "--prefix", "frontend", "run", "build"]),
    ]

    failed_checks: list[str] = []
    for name, command in checks:
        print(f"\n== {name} ==", flush=True)
        try:
            if sys.platform == "win32" and command[0] == "npm":
                result = subprocess.run(
                    subprocess.list2cmdline(command),
                    cwd=ROOT,
                    check=False,
                    shell=True,
                )
            else:
                result = subprocess.run(command, cwd=ROOT, check=False)
        except OSError as error:
            print(f"Could not run command: {error}", file=sys.stderr, flush=True)
            failed_checks.append(name)
            continue

        if result.returncode:
            failed_checks.append(name)
            print(f"{name} failed with exit code {result.returncode}.", flush=True)
        else:
            print(f"{name} passed.", flush=True)

    print("\nJUnit reports: .test-results/backend.xml and .test-results/frontend.xml")
    if failed_checks:
        print(f"Verification failed: {', '.join(failed_checks)}.", file=sys.stderr)
        return 1

    print("All verification checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
