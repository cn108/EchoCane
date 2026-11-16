#!/usr/bin/env python3
"""Run the automated Wokwi scenarios.

Requires the Wokwi CLI and a Wokwi CI token. The project's local build and unit
tests do not depend on either. Use --dry-run to print the exact commands.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WOKWI = ROOT / "simulation" / "wokwi"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print commands without running the simulator",
    )
    args = parser.parse_args()

    manifest = json.loads((ROOT / "tests" / "scenarios.json").read_text(encoding="utf-8"))
    firmware = ROOT / ".pio" / "build" / "nanoatmega328" / "firmware.hex"
    if not firmware.is_file():
        print("ERROR: firmware.hex missing; run `pio run -e nanoatmega328` first")
        return 2

    cli = shutil.which("wokwi-cli")
    token = os.environ.get("WOKWI_CLI_TOKEN", "")
    if not args.dry_run:
        if not cli:
            print(
                "ERROR: wokwi-cli is not installed. See "
                "https://docs.wokwi.com/wokwi-ci/cli-installation"
            )
            return 2
        if not token:
            print(
                "ERROR: WOKWI_CLI_TOKEN is not set. Wokwi CI requires a token; "
                "the firmware build and host tests do not."
            )
            return 2

    (ROOT / "test-results").mkdir(exist_ok=True)

    failures = 0
    for entry in manifest:
        command = [
            cli or "wokwi-cli",
            ".",
            "--scenario",
            entry["scenario"],
            "--diagram-file",
            entry["diagram"],
            "--timeout",
            str(entry["timeout_ms"]),
            "--serial-log-file",
            f"../../test-results/wokwi-{entry['name']}.log",
        ]
        print("+", " ".join(command), f"(cwd={WOKWI})")
        if args.dry_run:
            continue

        result = subprocess.run(command, cwd=WOKWI, text=True)
        if result.returncode != 0:
            failures += 1
            print(f"FAILED: {entry['name']} (exit {result.returncode})")
        else:
            print(f"PASSED: {entry['name']}")

    if args.dry_run:
        return 0

    print(f"\n{len(manifest) - failures}/{len(manifest)} scenarios passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
