#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def run(cwd: Path, *args: str) -> None:
    print(f"\n==> {cwd.name}: {' '.join(args)}", flush=True)
    subprocess.run([sys.executable, *args], cwd=cwd, check=True)


def main() -> None:
    run(ROOT / "evidence-gate", "-m", "unittest", "discover", "-s", "tests", "-v")
    run(ROOT / "evidence-gate", "scripts/stress.py", "--iterations", "1000")
    run(ROOT / "async-polling-contract", "-m", "unittest", "-v")
    run(ROOT / "async-polling-contract", "demo.py")
    print("\nALL PUBLIC PROOFS PASSED", flush=True)


if __name__ == "__main__":
    main()
