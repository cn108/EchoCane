#!/usr/bin/env python3
"""DC design-margin checks for the EchoCane vibration-motor driver.

Assumptions are deliberately explicit. This is a design calculation, not a
measurement of a physical motor or transistor.
"""

from __future__ import annotations

import json
from pathlib import Path

VCC = 5.0
VBE_SAT = 1.2
VCE_SAT = 0.3
MOTOR_CURRENT_A = 0.10
RBASE_OHM = 330.0
RBASE_PULLDOWN_OHM = 10000.0
FORCED_BETA_TARGET = 10.0
NANO_PIN_LIMIT_A = 0.020
USB_BUDGET_A = 0.500
LED_VF = 2.0
LED_R = 220.0
BUTTON_CAP_F = 100e-9
BUTTON_PULLUP_OHM = 30000.0


def main() -> int:
    base_current = (VCC - VBE_SAT) / RBASE_OHM
    forced_beta = MOTOR_CURRENT_A / base_current
    max_base_resistor = (VCC - VBE_SAT) / (MOTOR_CURRENT_A / FORCED_BETA_TARGET)
    base_resistor_power = (VCC - VBE_SAT) ** 2 / RBASE_OHM
    transistor_power = VCE_SAT * MOTOR_CURRENT_A
    motor_voltage = VCC - VCE_SAT
    led_current = (VCC - LED_VF) / LED_R
    led_resistor_power = (VCC - LED_VF) ** 2 / LED_R
    button_tau = BUTTON_PULLUP_OHM * BUTTON_CAP_F
    budget = {
        "nano_quiescent_mA": 20,
        "hc_sr04_peak_mA": 15,
        "motor_mA": MOTOR_CURRENT_A * 1000,
        "buzzer_mA": 10,
        "status_led_mA": led_current * 1000,
    }
    budget["total_mA"] = sum(budget.values())

    results = {
        "assumptions": {
            "vcc_V": VCC,
            "vbe_sat_V": VBE_SAT,
            "vce_sat_V": VCE_SAT,
            "motor_current_A": MOTOR_CURRENT_A,
            "rbase_ohm": RBASE_OHM,
            "forced_beta_target": FORCED_BETA_TARGET,
        },
        "base_drive": {
            "base_current_mA": round(base_current * 1000, 3),
            "forced_beta": round(forced_beta, 2),
            "max_base_resistor_for_target_ohm": round(max_base_resistor, 1),
            "base_resistor_power_mW": round(base_resistor_power * 1000, 3),
            "nano_pin_limit_mA": NANO_PIN_LIMIT_A * 1000,
            "pin_current_margin_mA": round((NANO_PIN_LIMIT_A - base_current) * 1000, 3),
        },
        "output_stage": {
            "motor_voltage_V": round(motor_voltage, 3),
            "transistor_power_mW": round(transistor_power * 1000, 3),
            "flyback_diode": "1N4007, cathode to +5V, anode to collector",
        },
        "status_led": {
            "current_mA": round(led_current * 1000, 2),
            "resistor_power_mW": round(led_resistor_power * 1000, 2),
            "nano_pin_limit_mA": NANO_PIN_LIMIT_A * 1000,
        },
        "button": {
            "rc_time_constant_ms": round(button_tau * 1000, 3),
            "firmware_debounce_ms": 30,
        },
        "power_budget": {key: round(value, 2) for key, value in budget.items()},
        "usb_budget_margin_mA": round((USB_BUDGET_A * 1000) - budget["total_mA"], 1),
        "checks": {},
    }

    checks = {
        "base_current_within_nano_pin": base_current < NANO_PIN_LIMIT_A,
        # A lower forced beta means more base current. For hard saturation the
        # forced beta must be at or below the target, not above it.
        "forced_beta_at_most_10": forced_beta <= FORCED_BETA_TARGET,
        "base_resistor_within_saturation_limit": RBASE_OHM <= max_base_resistor,
        "base_resistor_at_least_220_ohm": RBASE_OHM >= 220,
        "led_current_within_nano_pin": led_current < NANO_PIN_LIMIT_A,
        "power_budget_within_usb": budget["total_mA"] < USB_BUDGET_A * 1000,
        "pulldown_does_not_load_base": RBASE_PULLDOWN_OHM >= 10 * RBASE_OHM,
    }
    results["checks"] = checks

    output = Path(__file__).resolve().parent / "driver-analysis.json"
    output.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))

    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        print("FAILED: " + ", ".join(failed))
        return 1
    print("All driver design-margin checks passed (paper calculation).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
