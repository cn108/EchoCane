# Testing strategy and results

## 1. Philosophy

EchoCane uses a layered verification strategy because each layer can prove
something different:

| Layer | What it can prove | What it cannot prove |
|---|---|---|
| Host unit tests | Policy logic, boundaries, state transitions, formatting | Real sensor timing, electrical behaviour |
| Structural validators | Wokwi files are well-formed and share the firmware pin map | The simulation runs or the hardware works |
| Firmware build | The Nano target compiles and fits | Any runtime behaviour |
| ngspice | The driver stage behaves plausibly under a lumped model | Real motor torque, vibration, thermal or EMC behaviour |
| KiCad ERC/DRC | Schematic and PCB are internally consistent | Manufacturability, assembly yield, physical safety |
| Wokwi scenarios | Firmware behaviour in a simulated circuit | Real acoustics, optics, user perception |
| Physical/user testing | Real-world behaviour | **Not performed** |

The project deliberately does not treat a clean build or a clean DRC as proof of
safety.

## 2. Executed results

### 2.1 Firmware build

Command:

```bash
./.venv/Scripts/pio.exe run -e nanoatmega328
```

Result:

```text
RAM:   37.9% (used 777 bytes from 2048 bytes)
Flash: 35.0% (used 10766 bytes from 30720 bytes)
SUCCESS
```

The build produces `.pio/build/nanoatmega328/firmware.hex` and `.elf`, which are
the files referenced by `simulation/wokwi/wokwi.toml`.

### 2.2 Native unit tests

Command:

```bash
MSYS_NO_PATHCONV=1 docker run --rm -v "$PWD:/work" -w /work \
  python:3.12-bookworm bash -lc \
  'python -m pip install -q platformio; pio test -e native'
```

Result:

```text
native:test_core PASSED
25 test cases: 25 succeeded
```

| # | Test | What it checks |
|---|---|---|
| 1 | `test_median_filter_rejects_isolated_spike` | A single outlier does not move the median |
| 2 | `test_median_filter_lower_median_for_even_window` | Defined lower-median behaviour for even sample counts |
| 3 | `test_classification_thresholds` | 79/80/150/151 cm boundaries |
| 4 | `test_caution_hysteresis_release` | Caution releases only above 160 cm |
| 5 | `test_danger_hysteresis_release` | Danger releases to caution/clear at the correct margins |
| 6 | `test_single_spike_is_filtered` | A noisy sample does not cause a false danger state |
| 7 | `test_timeout_confirms_fault` | Three timeouts confirm a fault |
| 8 | `test_fault_never_reports_obstacle_free` | `obstacleFree` is false in fault |
| 9 | `test_recovery_requires_consecutive_valid_readings` | Recovery needs three valid readings |
| 10 | `test_out_of_range_counts_as_failure` | Out-of-range is treated as invalid, not clear |
| 11 | `test_invalid_reading_degrades_but_is_not_clear` | A single failure becomes at least caution |
| 12 | `test_button_debouncing_emits_single_press` | Bounce does not produce repeated mode changes |
| 13 | `test_alert_pattern_selection` | Correct patterns for clear/caution/danger/fault |
| 14 | `test_mode_cycling` | Assist → Quiet → Diagnostic → Assist |
| 15 | `test_pulse_timer` | On/off phase scheduling and elapsed-time behaviour |
| 16 | `test_pulse_timer_handles_millis_rollover` | Phase timing survives the 32-bit millis wrap |
| 17 | `test_echo_pulse_conversion_boundaries` | 0/57/58/116/8700/23200/25000 µs conversions |
| 18 | `test_echo_pulse_conversion_is_overflow_safe` | Full uint32 input domain does not wrap |
| 19 | `test_danger_and_caution_release_boundaries` | Exact 90/91 and 160/161 cm release boundaries |
| 20 | `test_recovery_returns_clear_after_three_valid_readings` | Fault recovery reaches clear on the third valid sample |
| 21 | `test_degraded_recovery_holds_caution_until_three_valid_readings` | Degraded recovery remains caution for two valid samples |
| 22 | `test_telemetry_clear_record` | Clear record has `raw=OK`, distances and `free=1` |
| 23 | `test_telemetry_fault_record_not_free` | Fault record never reports free |
| 24 | `test_telemetry_truncates_safely` | Bounded formatting |
| 25 | `test_telemetry_zero_capacity_is_safe` | Null/zero-capacity output is rejected safely |

These tests compile the same `echocane_core` sources used by the Nano build. They
do not compile the Arduino adapters, which require hardware APIs.

### 2.3 Wokwi structural validation

Command:

```bash
python tests/validate_simulation.py
```

Result:

```text
OK: 6 diagrams validated with explicit pin/stimulus mappings, 0 warning(s)
```

This validates JSON structure, required parts, exact Nano GPIO connections,
the expected HC-SR04 distance for each diagram, the sensor-fault ECHO-to-GND
variant, scenario-to-diagram mappings and firmware build presence. It does
**not** execute the simulator. The firmware `.hex`/`.elf` were rebuilt before
this check.

### 2.4 Wokwi scenario execution

**Not executed.** The environment has no `wokwi-cli` and no `WOKWI_CLI_TOKEN`.
The repository provides:

- five automated YAML scenarios,
- a static diagram per scenario,
- a runner (`tests/run_wokwi_scenarios.py`) that is token-gated,
- a CI job that runs only when the secret is configured.

No serial logs, pass/fail results or screenshots from Wokwi are claimed. The
scenario matrix in [simulation/scenarios/README.md](../simulation/scenarios/README.md)
records the expected evidence and its status.

### 2.5 Cross-artifact validation

Command:

```bash
python tests/validate_hardware.py
```

Result:

```text
OK: 12 nets, 19 components, 15 BOM rows and 8 Wokwi links agree
```

The validator parses:

- `firmware/include/Pins.h`,
- the KiCad netlist,
- the BOM CSV,
- `simulation/wokwi/diagram.json`.

It checks the named nets, component membership, BOM values/footprints and the
Wokwi Nano-to-peripheral wiring. It caught a real net-name mismatch during
development: when the schematic moved from local labels (`/BUTTON`) to global
labels (`BUTTON`), the PCB had to be regenerated from the new netlist. The DRC
parity check then returned to zero.

### 2.6 KiCad ERC

Command:

```bash
kicad-cli sch erc --severity-all --exit-code-violations \
  -o hardware/verification/schematic-erc.rpt \
  hardware/kicad/EchoCane.kicad_sch
```

Result:

```text
ERC messages: 0  Errors 0  Warnings 0
```

### 2.7 KiCad DRC and schematic parity

Command:

```bash
kicad-cli pcb drc --severity-all --exit-code-violations \
  --schematic-parity --refill-zones \
  -o hardware/verification/pcb-drc.rpt \
  hardware/kicad/EchoCane.kicad_pcb
```

Result:

```text
Found 0 violations
Found 0 unconnected items
Found 0 schematic parity issues
```

Board statistics are recorded in
`hardware/verification/pcb-stats.txt`; the audit refreshed the dimensions and
pad/drill/component counts and removed stale copper-area figures rather than
carrying them forward from the previous placement.

### 2.8 ngspice driver simulation

Command (inside a Debian container with `ngspice`):

```bash
ngspice -b -o ngspice-results.txt driver.cir
```

Result (47 Ω / 10 mH motor model, generic PN2222A/1N4007 models):

| Measurement | Result |
|---|---|
| Base current, drive high | 12.34 mA |
| Base-emitter voltage | 0.926 V |
| Collector-emitter voltage, on | 0.094 V |
| Motor current, on | 104.4 mA |
| Collector peak at turn-off | 5.77 V |
| Flyback diode peak | 104.3 mA |
| Transistor dissipation | 9.8 mW |

The model includes a 0 V sense source for motor and diode current. It is a
lumped electrical model, not a motor or tactile validation. See
[simulation-limitations.md](simulation-limitations.md).

## 3. Test design details

### 3.1 Boundary and hysteresis tests

The tests inject exact values at and around the thresholds:

- `79 cm` → Danger
- `80 cm` → Caution
- `150 cm` → Caution
- `151 cm` → Clear
- `160 cm` → Caution remains (not clear)
- `161 cm` → Clear after caution
- `90 cm` and `91 cm` for danger release to caution
- `160 cm` and `161 cm` for danger release to clear

This catches off-by-one errors in the inclusive/exclusive comparisons.

### 3.2 Fault injection

Synthetic `DistanceReading::timeout()` and `outOfRange()` values are fed to the
controller. The tests assert:

- the first failures produce `DEGRADED`, not `CLEAR`,
- the third failure produces `FAULT`,
- `obstacleFree` is false throughout,
- recovery requires three consecutive valid readings,
- a failed reading after a clear classification produces at least caution.

### 3.3 Filter tests

The filter is tested with a steady sequence, an isolated spike and an even-sized
window. Because the production capacity is five (odd), the even-window test
documents the lower-median convention used by the implementation.

### 3.4 Timing tests

`ButtonDebouncer` and `PulseTimer` are tested with synthetic timestamps. The
tests cover bounce (multiple raw transitions within the debounce window), a
single stable press, phase changes and elapsed-time behaviour. They do not
measure real interrupt latency or `millis()` drift.

### 3.5 Telemetry tests

The formatter is tested for a clear record (`raw=OK`, distance fields, `free=1`),
a fault record (`free=0`), truncation and null/zero-capacity safety. The clear
record may contain `free=1` only under the valid/clear conditions.

## 4. CI

`.github/workflows/ci.yml` is configured to:

1. Run the native tests.
2. Build the Nano firmware (after tests, because the native test task may clean
   the AVR build directory).
3. Run both structural validators and the driver-margin calculation.
4. Run KiCad ERC/DRC in the `kicad/kicad:10.0` container.

The optional Wokwi workflow is separate (`wokwi.yml`) and runs only when
`WOKWI_CLI_TOKEN` is configured. Neither workflow has been observed running on
GitHub from this environment. The local commands above are the executed
evidence. The Wokwi job skips with a notice when the secret is absent; it never
commits the token.

## 5. What is not tested

| Area | Status |
|---|---|
| Real HC-SR04 timing, beam pattern, cross-talk | Not tested |
| Real vibration motor torque, frequency, noise | Not tested |
| Real buzzer sound pressure level | Not tested |
| USB source behaviour under motor transients | Not tested |
| PCB fabrication, assembly, solder joints | Not tested |
| EMC, ESD, thermal, drop, water resistance | Not tested |
| User perception, ergonomics, cane interaction | Not tested |
| Long-duration reliability / watchdog | Not tested |
| Remote GitHub Actions execution | Not observed |

These are engineering gaps, not footnotes. The device remains an experimental
supplementary aid.
