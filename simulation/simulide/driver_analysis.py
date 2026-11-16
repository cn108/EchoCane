#!/usr/bin/env python3
"""DC design-margin checks for the EchoCane vibration-motor driver.

Assumptions are deliberately explicit. This is a design calculation, not a
measurement of a physical motor or transistor.

The important change from the earlier revision is that the ATmega328P output is
not treated as an ideal 5 V source. Microchip's ATmega328P datasheet guarantees
VOH >= 4.2 V at IOH = -20 mA and VCC = 5 V over -40 to +85 C. This script uses
4.2 V as a conservative design bound even though the actual pin current is only
about 11 mA, and it subtracts the current diverted by the 10 kOhm base pull-down.
"""

from __future__ import annotations

import json
from pathlib import Path

VCC = 5.0
VOH_MIN = 4.2
VOH_TEST_CURRENT_A = 0.020
VBE_SAT = 1.2
VBE_LOW = 0.6
VCE_SAT = 0.3
MOTOR_DESIGN_A = 0.100
MOTOR_STRESS_A = 0.150
RBASE_SELECTED_OHM = 270.0
RBASE_OPTIONS_OHM = (330.0, 300.0, 270.0)
RBASE_PULLDOWN_OHM = 10000.0
FORCED_BETA_TARGET = 10.0
NANO_RECOMMENDED_PIN_A = 0.020
NANO_ABSOLUTE_PIN_A = 0.040
USB_BUDGET_A = 0.500
NANO_BOARD_MA = 25.0
HC_SR04_PEAK_MA = 15.0
BUZZER_MA = 10.0
LED_VF = 2.0
LED_R = 220.0
PWM_HZ = 976.6

MOSFET_RDS_ON_4V5_VENDOR_MAX_OHM = 0.035
MOSFET_RDS_ON_4V_MAX_OHM = 0.039
MOSFET_RDS_ON_5V_MAX_OHM = 0.028
MOSFET_QG_MAX_NC = 66.0


def drive_case(
    rbase_ohm: float,
    *,
    voh: float = VOH_MIN,
    vbe: float = VBE_SAT,
    motor_current_a: float = MOTOR_DESIGN_A,
) -> dict[str, float | bool]:
    """Calculate the loaded base-drive and saturation margins for one resistor."""
    r1_current = (voh - vbe) / rbase_ohm
    r2_current = vbe / RBASE_PULLDOWN_OHM
    base_current = r1_current - r2_current
    forced_beta = motor_current_a / base_current
    max_motor_for_target = base_current * FORCED_BETA_TARGET
    r1_power = (voh - vbe) ** 2 / rbase_ohm
    return {
        "rbase_ohm": rbase_ohm,
        "vdrive_V": voh,
        "vbe_V": vbe,
        "r1_current_mA": r1_current * 1000,
        "r2_current_mA": r2_current * 1000,
        "base_current_mA": base_current * 1000,
        "forced_beta": forced_beta,
        "max_motor_current_mA": max_motor_for_target * 1000,
        "r1_power_mW": r1_power * 1000,
        "pin_current_mA": r1_current * 1000,
        "pin_margin_mA": (NANO_RECOMMENDED_PIN_A - r1_current) * 1000,
        "passes_forced_beta": forced_beta <= FORCED_BETA_TARGET,
        "passes_pin_limit": r1_current <= NANO_RECOMMENDED_PIN_A,
    }


def main() -> int:
    selected = drive_case(RBASE_SELECTED_OHM)
    old_ideal = {
        "vdrive_V": VCC,
        "rbase_ohm": 330.0,
        "base_current_mA": (VCC - VBE_SAT) / 330.0 * 1000,
        "forced_beta": MOTOR_DESIGN_A / ((VCC - VBE_SAT) / 330.0),
        "r1_power_mW": (VCC - VBE_SAT) ** 2 / 330.0 * 1000,
        "note": (
            "Earlier paper result. It is not a valid loaded-GPIO result because "
            "it uses an ideal 5 V pin and omits the R2 pull-down."
        ),
    }
    options = [drive_case(value) for value in RBASE_OPTIONS_OHM]
    worst_case_pin = drive_case(
        RBASE_SELECTED_OHM, voh=VOH_MIN, vbe=VBE_LOW, motor_current_a=MOTOR_DESIGN_A
    )
    stress = drive_case(
        RBASE_SELECTED_OHM, voh=VOH_MIN, vbe=VBE_SAT, motor_current_a=MOTOR_STRESS_A
    )
    r1_saturation_limit = (VOH_MIN - VBE_SAT) / (
        MOTOR_DESIGN_A / FORCED_BETA_TARGET + VBE_SAT / RBASE_PULLDOWN_OHM
    )
    led_current = (VCC - LED_VF) / LED_R
    led_power = (VCC - LED_VF) ** 2 / LED_R
    transistor_power = VCE_SAT * MOTOR_DESIGN_A
    motor_voltage = VCC - VCE_SAT
    budget = {
        "nano_board_mA": NANO_BOARD_MA,
        "hc_sr04_peak_mA": HC_SR04_PEAK_MA,
        "motor_design_mA": MOTOR_DESIGN_A * 1000,
        "base_drive_mA": selected["r1_current_mA"],
        "buzzer_mA": BUZZER_MA,
        "status_led_mA": led_current * 1000,
    }
    budget["total_mA"] = sum(budget.values())
    mosfet_dissipation_100ma = MOSFET_RDS_ON_4V_MAX_OHM * MOTOR_DESIGN_A**2
    mosfet_dissipation_150ma = MOSFET_RDS_ON_4V_MAX_OHM * MOTOR_STRESS_A**2
    mosfet_gate_charge_current = MOSFET_QG_MAX_NC * 1e-9 * PWM_HZ

    results = {
        "assumptions": {
            "vcc_V": VCC,
            "voh_min_V": VOH_MIN,
            "voh_test_current_mA": VOH_TEST_CURRENT_A * 1000,
            "vbe_sat_V": VBE_SAT,
            "vbe_low_V": VBE_LOW,
            "vce_sat_V": VCE_SAT,
            "motor_design_current_A": MOTOR_DESIGN_A,
            "motor_stress_current_A": MOTOR_STRESS_A,
            "rbase_selected_ohm": RBASE_SELECTED_OHM,
            "rbase_pulldown_ohm": RBASE_PULLDOWN_OHM,
            "forced_beta_target": FORCED_BETA_TARGET,
            "nano_recommended_pin_mA": NANO_RECOMMENDED_PIN_A * 1000,
            "nano_absolute_pin_mA": NANO_ABSOLUTE_PIN_A * 1000,
        },
        "previous_ideal_calculation": {
            key: round(value, 3) if isinstance(value, float) else value
            for key, value in old_ideal.items()
        },
        "selected_base_drive": {
            key: round(value, 3) if isinstance(value, float) else value
            for key, value in selected.items()
        },
        "r1_saturation_limit_ohm": round(r1_saturation_limit, 2),
        "r1_options": [
            {key: round(value, 3) if isinstance(value, float) else value for key, value in option.items()}
            for option in options
        ],
        "worst_case_pin_current": {
            key: round(value, 3) if isinstance(value, float) else value
            for key, value in worst_case_pin.items()
        },
        "motor_stress_case": {
            key: round(value, 3) if isinstance(value, float) else value
            for key, value in stress.items()
        },
        "output_stage": {
            "motor_voltage_V": round(motor_voltage, 3),
            "transistor_power_mW": round(transistor_power * 1000, 3),
            "flyback_diode": "1N4007, cathode to +5V, anode to collector",
        },
        "status_led": {
            "current_mA": round(led_current * 1000, 3),
            "resistor_power_mW": round(led_power * 1000, 3),
            "nano_pin_limit_mA": NANO_RECOMMENDED_PIN_A * 1000,
        },
        "power_budget": {
            key: round(value, 3) for key, value in budget.items()
        },
        "usb_budget_margin_mA": round((USB_BUDGET_A * 1000) - budget["total_mA"], 3),
        "motor_current_status": {
            "design_mA": MOTOR_DESIGN_A * 1000,
            "stress_case_mA": MOTOR_STRESS_A * 1000,
            "stress_forced_beta": round(stress["forced_beta"], 3),
            "worst_case": "NOT VERIFIED - no motor datasheet or stall measurement",
            "note": (
                "100 mA is a design assumption, not a motor maximum. The "
                "selected drive supports up to the calculated forced-beta "
                "ceiling; a real motor's free-run and stall currents must be "
                "measured before claiming coverage."
            ),
        },
        "mosfet_comparison": {
            "part": "IRLZ44N",
            "package": "TO-220",
            "vds_V": 55,
            "id_A": 47,
            "rds_on_4v5_vendor_max_ohm": MOSFET_RDS_ON_4V5_VENDOR_MAX_OHM,
            "rds_on_4v_max_ohm": MOSFET_RDS_ON_4V_MAX_OHM,
            "rds_on_5v_max_ohm": MOSFET_RDS_ON_5V_MAX_OHM,
            "rds_on_4v5_conservative_ohm": MOSFET_RDS_ON_4V_MAX_OHM,
            "vgs_threshold_max_V": 2.0,
            "qg_max_nC": MOSFET_QG_MAX_NC,
            "dissipation_at_100mA_mW": round(mosfet_dissipation_100ma * 1000, 3),
            "dissipation_at_150mA_mW": round(mosfet_dissipation_150ma * 1000, 3),
            "average_gate_charge_current_uA": round(mosfet_gate_charge_current * 1e6, 3),
            "selection": "NOT SELECTED for revision 0.1",
            "reason": (
                "It meets the 4.5 V gate-drive requirement (35 mOhm vendor "
                "parametric maximum; 39 mOhm conservative bound from the 4 V "
                "datasheet maximum) and has very low conduction loss, but it is a "
                "TO-220 part that does not fit the existing TO-92 footprint; "
                "the added board area, gate charge and ESD handling are not "
                "justified for a 100 mA design point when a 270 ohm base "
                "resistor already meets the target."
            ),
        },
        "checks": {
            "selected_forced_beta_at_most_10": selected["passes_forced_beta"],
            "selected_r1_within_nano_recommended_pin": selected["passes_pin_limit"],
            "selected_r1_power_within_0p25W": selected["r1_power_mW"] <= 250.0,
            "selected_motor_design_within_beta_ceiling": (
                MOTOR_DESIGN_A * 1000 <= selected["max_motor_current_mA"]
            ),
            "worst_case_pin_within_nano_recommended_pin": (
                worst_case_pin["pin_current_mA"] <= NANO_RECOMMENDED_PIN_A * 1000
            ),
            "r1_saturation_limit_is_at_least_selected": (
                r1_saturation_limit >= RBASE_SELECTED_OHM
            ),
            "power_budget_within_usb": budget["total_mA"] <= USB_BUDGET_A * 1000,
            "pulldown_does_not_dominate_base": (
                RBASE_PULLDOWN_OHM >= 10 * RBASE_SELECTED_OHM
            ),
            "mosfet_has_conservative_4v5_bound": (
                MOSFET_RDS_ON_4V_MAX_OHM <= 0.05
            ),
            "mosfet_gate_peak_with_330_ohm_within_pin": (
                (VOH_MIN / 330.0) <= NANO_RECOMMENDED_PIN_A
            ),
        },
        "not_verified": [
            "motor free-run, stall, starting and worst-case operating current",
            "transistor and diode behaviour at temperature extremes",
            "GPIO VOH at the actual load and temperature",
            "PCB thermal rise, connector drop and USB-source sag",
        ],
    }

    output = Path(__file__).resolve().parent / "driver-analysis.json"
    output.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))

    failed = [name for name, passed in results["checks"].items() if not passed]
    if failed:
        print("FAILED: " + ", ".join(failed))
        return 1
    print("All selected-design checks passed (paper calculation).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
