# Simulation limitations

## 1. Summary

EchoCane was developed without physical hardware. Simulation is therefore the
main behavioural evidence, but it is not equivalent to a bench test or a user
trial. This document records what each tool can and cannot show, and which
results were actually executed.

| Tool | Status | Evidence produced | Not proven |
|---|---|---|---|
| Wokwi | Assets created; **scenarios not executed** | `diagram.json`, five scenario YAMLs, per-scenario diagrams, structural validation | Real sensor acoustics, tactile output, runtime scenario pass |
| SimulIDE | **Not installed** | Build guide, design calculations | A validated `.simu` circuit |
| ngspice | **Executed** | Transient driver measurements and waveform | Real motor torque/vibration, thermal/EMC behaviour |
| KiCad | **Executed** | ERC/DRC reports, Gerbers, drill, STEP, 3D renders | Fabrication, assembly, physical safety |
| Physical hardware | **Not available** | None | Everything real-world |

## 2. Wokwi

### 2.1 What the project provides

- `simulation/wokwi/diagram.json` — Arduino Nano, HC-SR04, mode button, status
  LED, haptic proxy LED, buzzer and resistors.
- `simulation/wokwi/wokwi.toml` — firmware paths into `.pio/build/nanoatmega328`.
- Five automated scenarios:
  1. clear at 300 cm,
  2. caution at 120 cm,
  3. danger at 50 cm,
  4. sensor fault (ECHO tied to GND),
  5. mode button cycling.
- A manual moving-away procedure.
- Per-scenario static diagrams under `simulation/wokwi/scenarios/diagrams/`.
- `tests/validate_simulation.py` — structural validation of all diagrams and
  scenario mappings.

### 2.2 What Wokwi can show

- The firmware boots, prints the banner and emits telemetry.
- The HC-SR04 trigger/echo sequence and the firmware's distance conversion.
- LED and buzzer responses to the alert policy.
- Button input and mode changes.
- The fault path when ECHO is held low.

### 2.3 What Wokwi cannot show

- **Real ultrasonic physics.** The HC-SR04 model uses a distance slider; it does
  not model beam width, multipath, soft/angled/transparent surfaces, cross-talk
  or temperature.
- **Tactile vibration.** Wokwi has no vibration-motor part. The project uses a
  PWM-driven LED and serial telemetry as an actuator proxy. This proves the
  command path, not that a motor vibrates or that a user can feel it.
- **Real acoustics.** The simulated buzzer is not a calibrated sound-pressure
  measurement.
- **Power/electrical reality.** Wokwi does not model the transistor's thermal
  behaviour, motor stall current, USB source sag or PCB parasitics.
- **Automated distance control.** Wokwi's documented automation controls cover
  parts such as pushbuttons, potentiometers, MPU6050, joystick, HX711 and
  photoresistor; the HC-SR04 distance is a manual slider. The project therefore
  uses static per-scenario diagrams rather than claiming a moving-obstacle
  automation that the simulator does not expose. See the official
  [HC-SR04 part documentation](https://docs.wokwi.com/parts/wokwi-hc-sr04) and
  [automation scenarios](https://docs.wokwi.com/wokwi-ci/automation-scenarios).

### 2.4 Execution status

The Wokwi CLI and `WOKWI_CLI_TOKEN` were not available in this environment.
`python tests/validate_simulation.py` passed with 6 diagrams and 0 warnings, but
**no scenario was executed**. No Wokwi serial logs or screenshots are claimed.
The CI workflow can run the scenarios when the repository secret is configured.

## 3. SimulIDE

SimulIDE was not installed, and no validated `.simu` file is included. Creating a
GUI-dependent project without opening it would not be credible evidence.

Instead, [`simulation/simulide/README.md`](../simulation/simulide/README.md)
provides:

- an exact component list and wiring table,
- a step-by-step SimulIDE build procedure,
- a driver test sketch outline,
- the expected qualitative behaviour,
- a clear statement that the `.simu` file must be saved and verified before it is
  reported as executed.

The repository also includes an **executed ngspice** model of the same driver
stage, which is stronger numerical evidence than an unverified SimulIDE file but
still not a tactile validation.

## 4. ngspice model

`simulation/simulide/driver.cir` models:

- a 5 V motor supply and a **4.2 V loaded-GPIO PWM source** (the datasheet VOH
  minimum at 20 mA, used conservatively at the actual ~12 mA),
- a 270 Ω base resistor and a 10 kΩ base pull-down,
- a generic Gummel-Poon PN2222A,
- a 47 Ω / 10 mH motor,
- a generic 1N4007 flyback diode,
- a 20 ms PWM pulse.

Results:

| Quantity | Result |
|---|---:|
| Loaded GPIO voltage | 4.20 V |
| R1 current | 12.14 mA |
| R2 current | 0.092 mA |
| Base current | 12.04 mA |
| Vbe | 0.923 V |
| Vce, on | 0.0945 V |
| Motor current, on | 104.37 mA |
| Vce peak at turn-off | 5.63 V |
| Diode peak | 104.37 mA |
| Q1 dissipation | 9.86 mW |

### 4.1 Model limitations

- The motor is a **lumped** 47 Ω / 10 mH load. A real vibration motor has a
  different resistance, inductance, back-EMF, brush noise and mechanical load.
- The transistor and diode models are generic first-order models, not vendor
  models.
- The simulation does not model temperature, self-heating, PCB copper, supply
  impedance or EMC.
- The 20 ms pulse is a test stimulus, not the firmware's actual PWM pattern.
- The results are indicative, not a substitute for measuring collector voltage,
  motor current, vibration amplitude or sound pressure on a bench.

The waveform is in [`images/driver-waveform.svg`](../images/driver-waveform.svg),
generated by `simulation/simulide/plot_driver.py` from the raw ngspice output.

## 5. KiCad

### 5.1 What was verified

- ERC: 0 errors, 0 warnings.
- DRC: 0 violations, 0 unconnected pads, 0 schematic-parity issues.
- Board statistics generated.
- Gerbers, Excellon drill, drill map, Gerber job file and STEP generated.
- 3D top/bottom renders generated.

### 5.2 What was not verified

- Fabrication at a board house.
- Assembly, solderability, connector fit or enclosure fit.
- EMC, ESD, thermal, vibration or drop behaviour.
- Actual motor current and supply transients on the PCB.
- The Arduino Nano module's 3D model is missing from the installed KiCad library,
  so A1 is absent from the STEP and appears as a footprint outline in renders.
  A CC0 candidate x3d model was found but not included because its geometry and
  origin were not independently verified.

A clean DRC is a design-rule check, not a manufacturing or safety certificate.

## 6. Physical validation gap

No physical hardware was purchased, assembled or tested. In particular:

- no real HC-SR04 measurements,
- no real motor vibration or user perception,
- no real buzzer audibility test,
- no battery/USB source test,
- no cane integration or ergonomics study,
- no user trial with visually impaired participants.

The project must not be described as a working assistive device. It is a
technically informed reconstruction and a simulation/test portfolio.

## 7. Evidence policy

The repository follows these rules:

1. A build result is reported only from an actual compiler run.
2. A unit-test result is reported only from an actual test run.
3. A simulation result is reported only from an actual simulator run.
4. A structural validation is labelled as structural, not as execution.
5. A DRC/ERC result is reported with the exact command and report file.
6. No screenshot, serial log or measurement is fabricated.
7. Missing tools and unexecuted scenarios are stated explicitly.

This is why the README distinguishes **PASS** (executed) from **NOT RUN** and
**NOT PERFORMED**.
