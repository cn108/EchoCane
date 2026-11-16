# Simulation scenario matrix

The automated scenarios live in `simulation/wokwi/scenarios/`. Each scenario has a
static per-scenario diagram under `simulation/wokwi/scenarios/diagrams/`. Wokwi
does not expose an automation control for the HC-SR04 distance, so separate
diagrams are used instead of a scripted moving obstacle.

| # | Scenario | Diagram | Distance / stimulus | Expected serial evidence | Execution status |
|---|---|---|---|---|---|
| 01 | No obstacle | `diagrams/clear.json` | 300 cm | `level=CLEAR`, `free=1` | **NOT RUN** |
| 02 | Caution range | `diagrams/caution.json` | 120 cm | `level=CAUTION`, `free=0` | **NOT RUN** |
| 03 | Danger range | `diagrams/danger.json` | 50 cm | `level=DANGER`, `free=0` | **NOT RUN** |
| 04 | Sensor fault | `diagrams/sensor_fault.json` | ECHO tied to GND | `health=DEGRADED`, then `level=FAULT` / `health=FAULT`, `free=0` | **NOT RUN** |
| 05 | Mode button | `diagrams/mode_button.json` | 300 cm + button press | `mode=QUIET`, then `mode=DIAGNOSTIC` | **NOT RUN** |
| 06 | Moving away | main `diagram.json` | manual 45 → 120 → 300 cm | `DANGER` → `CAUTION` → `CLEAR` | **MANUAL PROCEDURE** |

## Why no automated moving-away scenario?

Wokwi's HC-SR04 simulated distance is changed with the manual distance slider.
The documented automation controls cover other parts (for example pushbuttons and
potentiometers) but not the ultrasonic distance. A scenario that claims to move
the obstacle automatically would be misleading. The static diagrams plus the
manual procedure are the honest alternative.

The mode-button scenario uses Wokwi's pushbutton automation to press the button;
it is the one scenario that can be fully automated if the CLI/token is available.

## Running the scenarios

```bash
# Build the firmware first
pio run -e nanoatmega328

# Show the commands without requiring a token
python tests/run_wokwi_scenarios.py --dry-run

# Actual execution (requires wokwi-cli and WOKWI_CLI_TOKEN)
export WOKWI_CLI_TOKEN=...
python tests/run_wokwi_scenarios.py
```

The runner writes serial logs to `test-results/` (ignored by Git). It does not
print the token.

## Manual moving-away procedure

1. Build the firmware and open `simulation/wokwi` in VS Code with the Wokwi
   extension.
2. Start the main diagram at 300 cm; confirm `level=CLEAR`, `free=1`.
3. Set the HC-SR04 slider to 45 cm; confirm `level=DANGER`, `free=0`, and the
   strong haptic/buzzer pattern.
4. Increase to 91 cm; confirm the danger state releases to `CAUTION` (not
   immediately clear). At exactly 90 cm the danger state is retained by the
   `> 90 cm` release rule.
5. Increase to 120 cm; confirm `CAUTION`.
6. Increase to 170 cm; confirm `CLEAR`, `free=1`.
7. Record the serial log and the Wokwi version. Until then, this procedure is
   **not executed**.

## Evidence policy

- Structural validity is not execution.
- A scenario is marked **PASS** only after the runner exits successfully and the
  serial log shows the expected records.
- No screenshots or serial logs are included unless they were actually captured.
