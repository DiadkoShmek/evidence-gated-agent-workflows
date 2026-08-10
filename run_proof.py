#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def run(cwd: Path, *args: str) -> None:
    print(f"\n==> {cwd.name}: {' '.join(args)}", flush=True)
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    subprocess.run([sys.executable, *args], cwd=cwd, check=True, env=environment)


def main() -> None:
    run(ROOT, "-m", "unittest", "-v", "test_publication_candidate.py")
    run(ROOT / "evidence-gate", "-m", "unittest", "discover", "-s", "tests", "-v")
    run(ROOT / "evidence-gate", "scripts/stress.py", "--iterations", "1000")
    run(ROOT / "async-polling-contract", "-m", "unittest", "-v")
    run(ROOT / "async-polling-contract", "demo.py")
    run(ROOT / "operating-core-demo", "-m", "unittest", "-v", "tests.test_operating_core_demo")
    run(ROOT / "operating-core-demo", "run_demo.py")
    run(ROOT / "egoh-demo", "-m", "unittest", "-v", "tests.test_egoh_demo")
    run(
        ROOT / "egoh-demo",
        "run_demo.py",
        "--scenario",
        "valid-review",
        "--as-of",
        "2026-07-31T12:01:00+00:00",
        "--expect-decision",
        "review-required",
    )
    print("\nALL PUBLIC PROOFS PASSED", flush=True)


if __name__ == "__main__":
    main()
