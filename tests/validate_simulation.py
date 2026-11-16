#!/usr/bin/env python3
"""Validate EchoCane Wokwi assets without requiring a Wokwi token.

This is deliberately a structural check, not a simulation run. It catches
unknown part types, invalid pin references, duplicate IDs, out-of-range sensor
attributes, broken scenario mappings and missing build artefacts.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WOKWI = ROOT / "simulation" / "wokwi"

PIN_MAP = {
    "wokwi-arduino-nano": {
        "2", "3", "5", "6", "7", "8", "9", "10",
        "5V", "GND.1", "GND.2", "GND.3",
    },
    "wokwi-hc-sr04": {"VCC", "TRIG", "ECHO", "GND"},
    "wokwi-pushbutton": {"1.l", "1.r", "2.l", "2.r"},
    "wokwi-led": {"A", "C"},
    "wokwi-resistor": {"1", "2"},
    "wokwi-buzzer": {"1", "2"},
}

errors: list[str] = []
warnings: list[str] = []

# Each diagram has a deliberate stimulus and, except for the fault case, the
# same electrical wiring. Keep these assertions explicit so a renamed or
# mis-wired diagram cannot pass merely because its JSON is well formed.
EXPECTED_DIAGRAMS = {
    "diagram.json": (300, "nano:10"),
    "scenarios/diagrams/clear.json": (300, "nano:10"),
    "scenarios/diagrams/caution.json": (120, "nano:10"),
    "scenarios/diagrams/danger.json": (50, "nano:10"),
    "scenarios/diagrams/mode_button.json": (300, "nano:10"),
    "scenarios/diagrams/sensor_fault.json": (300, "nano:GND.2"),
}

COMMON_LINKS = [
    ("ultrasonic1:VCC", "nano:5V"),
    ("ultrasonic1:GND", "nano:GND.1"),
    ("ultrasonic1:TRIG", "nano:9"),
    ("btn1:1.r", "nano:2"),
    ("btn1:2.r", "nano:GND.2"),
    ("nano:7", "rStatus:1"),
    ("rStatus:2", "ledStatus:A"),
    ("ledStatus:C", "nano:GND.2"),
    ("nano:6", "rHaptic:1"),
    ("rHaptic:2", "ledHaptic:A"),
    ("ledHaptic:C", "nano:GND.2"),
    ("nano:8", "bz1:2"),
    ("bz1:1", "nano:GND.2"),
]


def check_diagram(path: Path) -> None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - report exact parse problem
        errors.append(f"{path.relative_to(ROOT)}: invalid JSON: {exc}")
        return

    if data.get("version") != 1:
        errors.append(f"{path.relative_to(ROOT)}: version must be 1")

    parts = data.get("parts", [])
    by_id = {}
    for part in parts:
        part_id = part.get("id")
        part_type = part.get("type")
        if not part_id or not part_type:
            errors.append(f"{path.relative_to(ROOT)}: part missing id/type")
            continue
        if part_id in by_id:
            errors.append(f"{path.relative_to(ROOT)}: duplicate part id {part_id}")
        if part_type not in PIN_MAP:
            errors.append(f"{path.relative_to(ROOT)}: unknown part type {part_type}")
        by_id[part_id] = part

    if not any(p.get("type") == "wokwi-arduino-nano" for p in parts):
        errors.append(f"{path.relative_to(ROOT)}: no Arduino Nano part")

    for part in parts:
        if part.get("type") == "wokwi-hc-sr04":
            distance = int(part.get("attrs", {}).get("distance", "0"))
            if not 2 <= distance <= 400:
                errors.append(
                    f"{path.relative_to(ROOT)}: HC-SR04 distance {distance} out of range"
                )

    relative = path.relative_to(WOKWI).as_posix()
    expected = EXPECTED_DIAGRAMS.get(relative)
    if expected is None:
        errors.append(f"{path.relative_to(ROOT)}: no expected stimulus mapping")
    else:
        expected_distance, expected_echo = expected
        actual_distance = None
        for part in parts:
            if part.get("type") == "wokwi-hc-sr04":
                actual_distance = int(part.get("attrs", {}).get("distance", "0"))
        if actual_distance != expected_distance:
            errors.append(
                f"{path.relative_to(ROOT)}: expected distance {expected_distance}, "
                f"got {actual_distance}"
            )

        links = {
            frozenset((connection[0], connection[1]))
            for connection in data.get("connections", [])
            if len(connection) >= 2
        }
        for first, second in [*COMMON_LINKS, ("ultrasonic1:ECHO", expected_echo)]:
            if frozenset((first, second)) not in links:
                errors.append(
                    f"{path.relative_to(ROOT)}: missing {first} <-> {second}"
                )

    connected_pins: set[tuple[str, str]] = set()
    for connection in data.get("connections", []):
        if len(connection) < 2:
            errors.append(f"{path.relative_to(ROOT)}: malformed connection {connection}")
            continue
        for endpoint in connection[:2]:
            if ":" not in endpoint:
                errors.append(f"{path.relative_to(ROOT)}: bad endpoint {endpoint}")
                continue
            part_id, pin = endpoint.split(":", 1)
            if part_id not in by_id:
                errors.append(f"{path.relative_to(ROOT)}: unknown part id {part_id}")
                continue
            part_type = by_id[part_id]["type"]
            if pin not in PIN_MAP.get(part_type, set()):
                errors.append(
                    f"{path.relative_to(ROOT)}: {part_type} has no pin {pin}"
                )
            connected_pins.add((part_id, pin))

    # Every endpoint in the explicit link list must be connected. This also
    # checks that the sensor, button, LED, haptic proxy and buzzer are present.
    for first, second in COMMON_LINKS:
        for endpoint in (first, second):
            part_id, pin = endpoint.split(":", 1)
            if part_id not in by_id:
                errors.append(f"{path.relative_to(ROOT)}: missing {part_id}")
            elif (part_id, pin) not in connected_pins:
                errors.append(f"{path.relative_to(ROOT)}: {endpoint} not connected")


def check_scenarios() -> None:
    manifest_path = ROOT / "tests" / "scenarios.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        errors.append(f"tests/scenarios.json: invalid JSON: {exc}")
        return

    for entry in manifest:
        scenario = WOKWI / entry["scenario"]
        diagram = WOKWI / entry["diagram"]
        if not scenario.is_file():
            errors.append(f"missing scenario {scenario.relative_to(ROOT)}")
        else:
            text = scenario.read_text(encoding="utf-8")
            for key in ("name:", "version:", "steps:"):
                if key not in text:
                    errors.append(
                        f"{scenario.relative_to(ROOT)}: missing {key.strip(':')}"
                    )
        if not diagram.is_file():
            errors.append(f"missing diagram {diagram.relative_to(ROOT)}")


def check_build_outputs() -> None:
    for name in ("firmware.hex", "firmware.elf"):
        path = ROOT / ".pio" / "build" / "nanoatmega328" / name
        if not path.is_file():
            warnings.append(
                f"{path.relative_to(ROOT)} missing; run `pio run -e nanoatmega328` "
                "before opening Wokwi"
            )


def main() -> int:
    diagrams = [WOKWI / "diagram.json", *sorted((WOKWI / "scenarios" / "diagrams").glob("*.json"))]
    for path in diagrams:
        check_diagram(path)
    check_scenarios()
    check_build_outputs()

    for warning in warnings:
        print(f"WARN: {warning}")
    for error in errors:
        print(f"ERROR: {error}")

    if errors:
        print(f"\n{len(errors)} structural error(s)")
        return 1

    print(
        f"OK: {len(diagrams)} diagrams validated with explicit pin/stimulus "
        f"mappings, {len(warnings)} warning(s)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
