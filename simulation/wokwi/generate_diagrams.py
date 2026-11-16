#!/usr/bin/env python3
"""Generate EchoCane Wokwi diagrams from one authoritative layout.

Wokwi's HC-SR04 does not expose an automation control for distance (verified
against the Wokwi part and automation documentation). Automated scenarios
therefore use separate diagrams with a fixed initial distance. The interactive
diagram keeps the distance slider available for the manual moving-obstacle
procedure.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCENARIO_DIR = ROOT / "scenarios" / "diagrams"

NANO = "nano"


def parts(distance: int) -> list[dict]:
    return [
        {
            "type": "wokwi-arduino-nano",
            "id": NANO,
            "top": 0,
            "left": 0,
            "attrs": {},
        },
        {
            "type": "wokwi-hc-sr04",
            "id": "ultrasonic1",
            "top": -40,
            "left": -260,
            "attrs": {"distance": str(distance)},
        },
        {
            "type": "wokwi-pushbutton",
            "id": "btn1",
            "top": 110,
            "left": -240,
            "attrs": {"color": "blue", "xray": "1", "label": "MODE"},
        },
        {
            "type": "wokwi-led",
            "id": "ledStatus",
            "top": -80,
            "left": 170,
            "attrs": {"color": "green", "label": "STATUS"},
        },
        {
            "type": "wokwi-resistor",
            "id": "rStatus",
            "top": -20,
            "left": 165,
            "attrs": {"value": "220"},
        },
        {
            "type": "wokwi-led",
            "id": "ledHaptic",
            "top": -80,
            "left": 285,
            "attrs": {"color": "red", "label": "HAPTIC CMD"},
        },
        {
            "type": "wokwi-resistor",
            "id": "rHaptic",
            "top": -20,
            "left": 280,
            "attrs": {"value": "220"},
        },
        {
            "type": "wokwi-buzzer",
            "id": "bz1",
            "top": -20,
            "left": 400,
            "attrs": {"volume": "0.05", "mode": "smooth"},
        },
    ]


def diagram(distance: int, fault: bool = False) -> dict:
    echo_target = f"{NANO}:GND.2" if fault else f"{NANO}:10"
    return {
        "version": 1,
        "author": "EchoCane virtual reconstruction",
        "editor": "wokwi",
        "parts": parts(distance),
        "connections": [
            ["ultrasonic1:VCC", f"{NANO}:5V", "red", []],
            ["ultrasonic1:GND", f"{NANO}:GND.1", "black", []],
            ["ultrasonic1:TRIG", f"{NANO}:9", "orange", []],
            # Grounded ECHO produces a deterministic echo timeout for the fault
            # scenario; the sensor is still powered and triggered.
            ["ultrasonic1:ECHO", echo_target, "blue", []],
            ["btn1:1.r", f"{NANO}:2", "green", []],
            ["btn1:2.r", f"{NANO}:GND.2", "black", []],
            [f"{NANO}:7", "rStatus:1", "green", []],
            ["rStatus:2", "ledStatus:A", "green", []],
            ["ledStatus:C", f"{NANO}:GND.2", "black", []],
            [f"{NANO}:6", "rHaptic:1", "purple", []],
            ["rHaptic:2", "ledHaptic:A", "purple", []],
            ["ledHaptic:C", f"{NANO}:GND.2", "black", []],
            ["bz1:2", f"{NANO}:8", "yellow", []],
            ["bz1:1", f"{NANO}:GND.2", "black", []],
        ],
    }


def write(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    SCENARIO_DIR.mkdir(parents=True, exist_ok=True)
    write(ROOT / "diagram.json", diagram(300))
    write(SCENARIO_DIR / "clear.json", diagram(300))
    write(SCENARIO_DIR / "caution.json", diagram(120))
    write(SCENARIO_DIR / "danger.json", diagram(50))
    write(SCENARIO_DIR / "sensor_fault.json", diagram(300, fault=True))
    write(SCENARIO_DIR / "mode_button.json", diagram(300))
    print("Generated 6 Wokwi diagrams")


if __name__ == "__main__":
    main()
