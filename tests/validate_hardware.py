#!/usr/bin/env python3
"""Cross-check EchoCane's pin map, schematic netlist, BOM and Wokwi wiring.

This is a consistency check, not an electrical simulation. KiCad ERC/DRC remain
the authoritative checks for the schematic and PCB.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PINS_H = ROOT / "firmware" / "include" / "Pins.h"
NETLIST = ROOT / "hardware" / "kicad" / "EchoCane.net"
BOM = ROOT / "hardware" / "bom" / "EchoCane-BOM.csv"
DIAGRAM = ROOT / "simulation" / "wokwi" / "diagram.json"

errors: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def balanced_blocks(text: str, marker: str) -> list[str]:
    blocks: list[str] = []
    start = 0
    while True:
        index = text.find(marker, start)
        if index < 0:
            return blocks
        depth = 0
        in_string = False
        escaped = False
        for i in range(index, len(text)):
            c = text[i]
            if in_string:
                if escaped:
                    escaped = False
                elif c == chr(92):
                    escaped = True
                elif c == '"':
                    in_string = False
            else:
                if c == '"':
                    in_string = True
                elif c == "(":
                    depth += 1
                elif c == ")":
                    depth -= 1
                    if depth == 0:
                        blocks.append(text[index : i + 1])
                        start = i + 1
                        break
        else:
            return blocks


def parse_netlist() -> tuple[dict[str, dict[str, str]], dict[str, set[tuple[str, str]]]]:
    text = NETLIST.read_text(encoding="utf-8")
    components: dict[str, dict[str, str]] = {}
    for block in balanced_blocks(text, "(comp\n"):
        ref = re.search(r'\(ref "([^"]+)"\)', block)
        value = re.search(r'\(value "([^"]*)"\)', block)
        footprint = re.search(r'\(footprint "([^"]*)"\)', block)
        if ref and value and footprint:
            components[ref.group(1)] = {
                "value": value.group(1),
                "footprint": footprint.group(1),
            }

    nets: dict[str, set[tuple[str, str]]] = {}
    section = text[text.find("(nets") :]
    for block in balanced_blocks(section, "(net\n"):
        name = re.search(r'\(name "([^"]+)"\)', block)
        if not name:
            continue
        nodes = {
            (m.group(1), m.group(2))
            for m in re.finditer(
                r'\(node\s+\(ref "([^"]+)"\)\s+\(pin "([^"]+)"\)', block
            )
        }
        nets[name.group(1)] = nodes
    return components, nets


def main() -> int:
    pins_text = PINS_H.read_text(encoding="utf-8")
    pin_values = {
        match.group(1): int(match.group(2))
        for match in re.finditer(r"(k\w+)\s*=\s*(\d+);", pins_text)
    }
    expected_pins = {
        "kUltrasonicTrig": 9,
        "kUltrasonicEcho": 10,
        "kHapticPwm": 6,
        "kBuzzer": 8,
        "kModeButton": 2,
        "kStatusLed": 7,
    }
    for macro, expected in expected_pins.items():
        found = re.search(rf"{macro}\s*=\s*(\d+)", pins_text)
        check(found is not None, f"Pins.h missing {macro}")
        if found:
            check(int(found.group(1)) == expected, f"{macro} is not D{expected}")
            check(pin_values.get(macro) == expected, f"{macro} parse inconsistency")

    components, nets = parse_netlist()

    expected_nets: dict[str, set[tuple[str, str]]] = {
        "US_TRIG": {("A1", "12"), ("J1", "2")},
        "US_ECHO": {("A1", "13"), ("J1", "3")},
        "HAPTIC_PWM": {("A1", "9"), ("R1", "1")},
        "LED_CMD": {("A1", "10"), ("R3", "1")},
        "BUZZER_CMD": {("A1", "11"), ("R4", "1")},
        "BUTTON": {("A1", "5"), ("SW1", "1"), ("C3", "1")},
        "Q_BASE": {("R1", "2"), ("R2", "1"), ("Q1", "2")},
        "MOTOR_NEG": {("Q1", "3"), ("J2", "2"), ("D1", "2")},
        "LED_A": {("R3", "2"), ("D2", "2")},
        "BUZZER_A": {("R4", "2"), ("BZ1", "1")},
        "+5V": {
            ("A1", "27"),
            ("J1", "1"),
            ("J2", "1"),
            ("D1", "1"),
            ("C1", "1"),
            ("C2", "1"),
        },
        "GND": {
            ("A1", "4"),
            ("A1", "29"),
            ("J1", "4"),
            ("Q1", "1"),
            ("R2", "2"),
            ("C1", "2"),
            ("C2", "2"),
            ("C3", "2"),
            ("D2", "1"),
            ("SW1", "2"),
            ("BZ1", "2"),
        },
    }

    for net, expected_nodes in expected_nets.items():
        actual_name = net if net in nets else "/" + net
        check(actual_name in nets, f"netlist missing net {net}")
        if actual_name in nets:
            check(
                nets[actual_name] == expected_nodes,
                f"net {net}: expected {sorted(expected_nodes)}, got {sorted(nets[actual_name])}",
            )

    bom_rows: dict[str, dict[str, str]] = {}
    with BOM.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if "-" not in row["Reference"]:
                bom_rows[row["Reference"]] = row

    for ref, info in components.items():
        # Mechanical mounting holes are PCB features, not BOM line items.
        if ref.startswith("H") and ref[1:].isdigit():
            continue
        check(ref in bom_rows, f"BOM missing {ref}")
        if ref in bom_rows:
            check(bom_rows[ref]["Value"] == info["value"], f"BOM value mismatch for {ref}")
            check(
                bom_rows[ref]["Footprint"] == info["footprint"],
                f"BOM footprint mismatch for {ref}",
            )

    diagram = json.loads(DIAGRAM.read_text(encoding="utf-8"))
    links: set[frozenset[str]] = set()
    for connection in diagram["connections"]:
        links.add(frozenset((connection[0], connection[1])))

    expected_links = [
        ("nano:9", "ultrasonic1:TRIG"),
        ("nano:10", "ultrasonic1:ECHO"),
        ("nano:6", "rHaptic:1"),
        ("nano:8", "bz1:2"),
        ("nano:2", "btn1:1.r"),
        ("nano:7", "rStatus:1"),
        ("ultrasonic1:VCC", "nano:5V"),
        ("ultrasonic1:GND", "nano:GND.1"),
    ]
    for a, b in expected_links:
        check(frozenset((a, b)) in links, f"Wokwi diagram missing {a} <-> {b}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"\n{len(errors)} cross-artifact error(s)")
        return 1

    print(
        f"OK: {len(expected_nets)} nets, {len(components)} components, "
        f"{len(bom_rows)} BOM rows and {len(expected_links)} Wokwi links agree"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
