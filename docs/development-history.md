# Development history

## 0. Starting point

The original university project's Arduino code, circuit diagrams, motherboard
specifications and hardware documentation were unavailable. This repository is a
**technically informed reconstruction and modernisation**, not a recovered copy
of the original. The work started from the supplied brief and an empty workspace
(apart from tool configuration).

The reconstruction was performed virtually. No components were purchased and no
physical board was assembled.

## 1. Tool discovery

| Tool | Availability | Consequence |
|---|---|---|
| PlatformIO | Installed locally in `.venv` | Nano build and native tests possible |
| Docker | Available (Linux containers) | Native tests and KiCad CLI possible on Windows |
| KiCad CLI | `kicad/kicad:10.0-full` (KiCad 10.0.8) | ERC, DRC, Gerbers, drill, STEP, 3D render |
| Wokwi | Assets created; CLI/token unavailable | Structural validation only; no scenario execution |
| SimulIDE | Not installed | Manual build guide + ngspice alternative |
| ngspice | Installed in a Debian container | Executed transient driver simulation |
| Physical hardware | Not available | No bench or user validation |
| Python | 3.12 in containers; local venv | Validators, generators, plots |

## 2. M1 — Project discovery and requirements reconstruction

**Implemented**

- Reconstructed the problem statement: a supplementary ultrasonic warning aid,
  not a cane replacement.
- Defined functional/non-functional requirements and acceptance criteria.
- Established the explicit safety rule: a sensor failure must never be reported as
  a clear path.
- Selected the classic 5 V Arduino Nano and the component set from the brief.
- Recorded that the original project cannot be reproduced exactly.

**Files**

- `docs/requirements.md`
- `README.md` (overview and constraints)

**Verification**

- Requirements traced to planned tests and artifacts.
- No fabricated original-project claims.

**Remaining**

- Requirements would need clinical/user input before any real deployment.

## 3. M2 — Architecture and hardware specification

**Implemented**

- Split the design into a portable `echocane_core` library and Arduino adapters.
- Fixed the pin map: D9 TRIG, D10 ECHO, D6 haptic, D8 buzzer, D2 button, D7 LED.
- Chose a PN2222A low-side driver, 1 kΩ base resistor, 10 kΩ pull-down, 1N4007
  flyback diode and 100 nF/10 µF decoupling.
- Defined connector pinouts and the 5 V USB power architecture.
- Planned a 100 × 85 mm, 2-layer carrier board.

**Files**

- `firmware/include/Pins.h`
- `firmware/lib/echocane_core/include/echocane/AppConfig.h`
- `docs/architecture.md`
- `docs/hardware-design.md`

**Verification**

- Pin map and component choices reviewed against the Nano's 5 V logic and the
  HC-SR04 interface.

**Remaining**

- Real component tolerances, motor stall current and thermal margins are not
  characterised.

## 4. M3 — Arduino firmware

**Implemented**

- Portable types, configuration, median filter, obstacle detector, safety
  monitor, alert policy, pulse timer, controller and telemetry formatter.
- Arduino adapters for sensor, haptic, audio, LED and serial.
- Cooperative main loop with 60 ms scans, 5 ms button polling, scheduled outputs
  and 500/250 ms telemetry; `pulseIn` is a bounded 25 ms blocking exception.
- Three modes: Assist, Quiet, Diagnostic.
- Fault/recovery policy and explicit `free=1` assertion.

**Files**

- `firmware/lib/echocane_core/**`
- `firmware/include/**`
- `firmware/src/**`
- `platformio.ini`

**Commands**

```bash
./.venv/Scripts/pio.exe run -e nanoatmega328
```

**Result**

```text
Flash: 10,766 / 30,720 bytes (35.0%)
RAM:     779 /  2,048 bytes (38.0%)
SUCCESS
```

This is the pre-audit M3 build. The audit removed an unused configuration field
and the final build is 10,766 B flash / 777 B RAM.

**Failures / notes**

- `pulseIn` remains a bounded blocking call (up to 25 ms). This is documented as a
  limitation and a future input-capture improvement, not hidden.
- `modeAnnounceMs` was reserved and unused at this milestone; it was removed by
  the audit rather than left as dead configuration.

## 5. M4 — Wokwi virtual circuit

**Implemented**

- Main `diagram.json` with Nano, HC-SR04, button, status LED, haptic proxy LED,
  buzzer and resistors.
- `wokwi.toml` pointing at the PlatformIO build.
- Five automated scenario YAMLs and per-scenario static diagrams.
- Manual moving-away procedure.
- Structural validator for diagrams, distances, mappings and firmware presence.

**Files**

- `simulation/wokwi/**`
- `tests/validate_simulation.py`

**Commands**

```bash
python tests/validate_simulation.py
```

**Result**

```text
OK: 6 diagrams validated, scenario mappings present, 0 warning(s)
```

**Blocker**

- `wokwi-cli` and `WOKWI_CLI_TOKEN` were not available. Scenarios were **not
  executed**; no pass/fail claims or serial logs are made.
- Wokwi's HC-SR04 distance is a manual slider; the project uses static diagrams
  instead of pretending a moving-obstacle automation exists.
- Wokwi has no vibration motor; a PWM LED is the actuator proxy.

## 6. M5 — Unit and automated simulation testing

**Implemented**

- 18 Unity tests covering boundaries, hysteresis, filtering, timeout, fault,
  recovery, debounce, patterns, modes, timers and telemetry.
- Native PlatformIO environment.
- Cross-artifact validator for firmware pins, netlist, BOM and Wokwi wiring.
- Token-gated Wokwi runner and CI workflow.

**Commands**

```bash
MSYS_NO_PATHCONV=1 docker run --rm -v "$PWD:/work" -w /work \
  python:3.12-bookworm bash -lc \
  'python -m pip install -q platformio; pio test -e native'

python tests/validate_hardware.py
```

**Result**

```text
18 test cases: 18 succeeded
OK: 12 nets, 19 components, 15 BOM rows and 8 Wokwi links agree
```

**Failure found and fixed**

- After changing the schematic net labels from local to global, the PCB still had
  `/BUTTON`-style net names while the schematic had `BUTTON`. DRC reported 24
  net-conflict parity warnings. Regenerating the PCB from the new netlist fixed
  the mismatch and returned parity to zero.

## 7. M6 — Supplementary SimulIDE / driver analysis

**Implemented**

- SimulIDE build guide with exact wiring table and procedure.
- Executable DC design-margin script.
- ngspice transient model with motor, transistor, diode and base network.
- Waveform plot and sampled CSV.

**Files**

- `simulation/simulide/README.md`
- `simulation/simulide/driver_analysis.py`
- `simulation/simulide/driver.cir`
- `simulation/simulide/plot_driver.py`
- `images/driver-waveform.svg`

**Commands**

```bash
python simulation/simulide/driver_analysis.py
ngspice -b -o ngspice-results.txt driver.cir
python simulation/simulide/plot_driver.py
```

**Result**

- The pre-audit M6 run reported six DC margin checks passing with a 1 kΩ base
  resistor and ngspice at 4.16 mA base, 103.7 mA motor, 0.124 V Vce and 5.77 V
  clamp. The audit found that the check treated a *higher* forced beta as a pass
  and that 1 kΩ was above the 380 Ω saturation limit; see M10 and
  [`circuit-explanation.md`](circuit-explanation.md).

**Blocker**

- SimulIDE was not installed, so no `.simu` file was generated or claimed. The
  guide is a reproducible procedure, not executed evidence.
- The ngspice model is a lumped electrical model; it does not prove tactile
  output.

## 8. M7 — KiCad schematic and PCB

**Implemented**

- Reproducible schematic generator with generic KiCad symbols, net labels,
  power symbols and no-connects.
- Reproducible PCB generator from the KiCad netlist.
- 100 × 85 mm, 2-layer board with 15 electrical footprints, 4 M3 holes, GND zone,
  routed tracks, silkscreen and 3D renders.
- BOM, netlist, ERC/DRC reports, Gerbers, drill, drill map, Gerber job file, STEP,
  PDF/SVG plots and statistics.

**Commands**

```bash
kicad-cli sch erc --severity-all --exit-code-violations \
  -o hardware/verification/schematic-erc.rpt \
  hardware/kicad/EchoCane.kicad_sch

kicad-cli pcb drc --severity-all --exit-code-violations \
  --schematic-parity --refill-zones \
  -o hardware/verification/pcb-drc.rpt \
  hardware/kicad/EchoCane.kicad_pcb
```

**Results**

```text
ERC: 0 errors, 0 warnings
DRC: 0 violations, 0 unconnected pads, 0 schematic parity issues
```

**Failures found and fixed**

1. **Four H1–H4 parity warnings** — the schematic included mounting holes in the
   BOM while the PCB excluded them. Fixed by marking the holes `in_bom no` and
   skipping them in the BOM; ERC/DRC then reached zero.
2. **Net-name mismatch** — changing to global labels changed net names from
   `/BUTTON` to `BUTTON`; the PCB needed regeneration. Fixed by regenerating the
   board from the new netlist.
3. **Cramped first schematic layout** — ERC was clean but labels overlapped and
   the content was concentrated in one corner. The schematic was re-laid out into
   labelled functional blocks with direction-aware labels and rechecked.
4. **Silkscreen overlap** — moving the buzzer label caused a silk-overlap DRC
   warning; repositioning it restored 0 DRC.

**Known limitation**

- The Arduino Nano module's vendor 3D model is absent from the installed KiCad
  library. A1 is missing from the STEP and appears as a footprint outline in the
  3D render. All other available models are included.

## 9. M8 — Engineering verification and documentation

**Implemented**

- README with overview, architecture, status, build/test/simulation instructions,
  PCB previews, limitations and documentation index.
- Requirements, architecture, hardware, circuit, software, testing, simulation
  limitations, safety and history documents.
- Schematic PNG, PCB top/bottom PNG, driver waveform SVG.
- ERC/DRC/stats reports and manufacturing outputs.

**Verification**

- Rebuilt the Nano firmware after all code changes.
- Re-ran the native tests (18 at this milestone; 25 after the audit).
- Re-ran both validators.
- Re-ran ERC and DRC after schematic/PCB changes.
- Re-exported Gerbers, drill, STEP and 3D renders after the final PCB generation.

**Remaining**

- No physical validation.
- No Wokwi execution.
- No SimulIDE `.simu`.
- CI has not been observed running on GitHub.

## 10. M9 — GitHub CI and portfolio presentation

**Implemented**

- `.github/workflows/ci.yml`: firmware build, native tests, structural validators
  and KiCad ERC/DRC.
- `.github/workflows/wokwi.yml`: optional, token-gated Wokwi scenario execution.
- `.gitignore`, MIT license and a clean repository layout.
- Meaningful milestone commits (see Git history).

**Verification**

- Local commands pass.
- YAML is syntactically intended for GitHub Actions; the workflow has not been
  executed on GitHub from this environment.
- The Wokwi job skips with a notice when the secret is absent and never prints or
  commits the token.

## 11. M10 — Independent engineering audit and final verification

**Implemented**

- Independent review of repository structure, firmware, electrical design,
  Wokwi assets, manufacturing outputs, CI and documentation.
- Corrected the inverted forced-beta check and changed R1 from 1 kΩ to 330 Ω;
  then corrected the loaded-GPIO/R2 omission and changed R1 to **270 Ω** using
  the ATmega328P VOH of 4.2 V at 20 mA. Regenerated the schematic, netlist, PCB,
  Gerbers, drill, STEP, plots and 3D renders.
- Removed the optional H5–H6 BOM row that was not represented in the schematic or
  PCB; the BOM is now 15 design rows.
- Moved C2 to provide mechanical clearance from C1 and rerouted the +5 V stub;
  DRC remains clean.
- Added an explicit board title-block revision (0.1), removed dead configuration,
  added overflow-safe echo conversion, and expanded the native suite from 18 to
  25 tests.
- Strengthened Wokwi validation from “connections exist” to exact GPIO and
  per-diagram stimulus mappings.

**Results**

- Nano build: PASS, 10,766 B flash / 777 B RAM.
- Native tests: PASS, 25/25.
- ERC: PASS, 0 errors/0 warnings.
- DRC: PASS, 0 violations, 0 unconnected pads, 0 parity issues.
- Structural validators: PASS, 6 diagrams with explicit mappings; 12 nets, 19
  components, 15 BOM rows and 8 Wokwi links agree.
- ngspice: 4.20 V loaded drive, 12.04 mA base, 104.37 mA motor, 0.0945 V Vce,
  5.63 V clamp, 104.37 mA diode peak.
- Driver paper margins: 11.11 mA pin current, 10.99 mA base, forced beta 9.10,
  109.9 mA forced-beta-10 ceiling; motor worst case remains unverified.
- Wokwi execution and remote CI remain unexecuted/not observed.

## 12. Summary of results

| Area | Result |
|---|---|
| Firmware build | PASS, 10,766 B flash / 777 B RAM |
| Native tests | PASS, 25/25 |
| Wokwi structure | PASS, 6 diagrams with explicit pin/stimulus mappings, 0 warnings |
| Wokwi execution | NOT RUN |
| ERC | PASS, 0/0 |
| DRC | PASS, 0/0/0 parity |
| Cross-artifact | PASS |
| Driver margins | PASS, 270 Ω, forced beta 9.10, 4.2 V loaded GPIO |
| ngspice | EXECUTED |
| SimulIDE | NOT EXECUTED (not installed) |
| Remote GitHub Actions | NOT OBSERVED |
| Physical validation | NOT PERFORMED |

## 13. Next steps (not part of this reconstruction)

1. Build and bench-test the board with a real HC-SR04, motor and buzzer.
2. Measure motor current, stall current, vibration amplitude and sound pressure.
3. Replace `pulseIn` with timer input capture and add a watchdog.
4. Add current sensing or actuator feedback so a failed motor is detectable.
5. Add a fused, protected 5 V input and ESD/transient protection.
6. Design an enclosure and a secure cane mount; test cable strain relief.
7. Run supervised user trials with orientation-and-mobility professionals.
8. Perform EMC, thermal, drop and environmental testing.
9. Revisit thresholds and patterns with user feedback — not before.
10. Only then consider whether the concept is safe enough for any real use.
