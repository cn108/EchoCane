# EchoCane independent engineering audit

- **Audit date:** 2026-11-16
- **Scope:** entire repository at the audited revision
- **Auditor role:** independent senior embedded-systems engineer
- **Posture:** adversarial review; previously reported passes were re-checked rather than trusted
- **Classification vocabulary:** `PASS`, `FAIL`, `NOT VERIFIED`, `NOT APPLICABLE`

## 1. Executive summary

The reconstruction is internally coherent and its available local verification is
green after correction. The audit found and fixed real defects that the earlier
reports did not expose:

1. The driver-margin script treated a **higher** forced beta as a pass, although
   hard saturation needs a **lower** forced beta. The 1 kΩ base resistor was above
   the 380 Ω limit implied by the project’s own forced-beta-10 target. R1 was
   changed to **330 Ω**, and the check now asserts the correct inequality.
2. The 330 Ω result was still not defensible: it assumed an ideal 5 V GPIO and
   omitted the 10 kΩ pull-down. Using the ATmega328P datasheet VOH of **4.2 V at
   −20 mA**, the loaded limit is **296.4 Ω**; 330 Ω gives forced beta 11.1 and
   300 Ω gives 10.12. R1 was changed again to **270 Ω**, which gives 11.0 mA of
   base current and forced beta 9.10 at 100 mA.
3. The BOM contained an optional `H5-H6` socket-header row that had no schematic
   or PCB representation. It was removed; the design BOM is 15 rows.
4. C1 and C2 bodies were exactly tangent (two 5 mm bodies with centres 5 mm
   apart). C2 was moved to `(90, 50)` mm and the +5 V stub was rerouted; DRC is
   clean and the render shows mechanical clearance.
5. Regenerating the PCB from an empty board had dropped the title block. The
   generator now writes title/revision 0.1, and the Gerber job file reports
   revision 0.1.
6. The firmware test suite did not cover exact release boundaries, recovery to
   clear, millis rollover, echo-conversion overflow or zero-capacity telemetry.
   Seven tests were added; the suite is now **25/25**.
7. Documentation described the old 1 kΩ design and `raw=Valid`, while the code
   emits `raw=OK`; these and other stale values were corrected.
8. Wokwi validation previously checked that pins existed, not that the exact GPIO
   and per-diagram stimulus were correct. It now asserts the complete wiring and
   expected distance for every diagram.
9. The power budget omitted the GPIO base-drive current and used 20 mA for the
   Nano board. The revised estimate is 174.7 mA, leaving 325.3 mA of nominal USB
   headroom; stall current remains unknown.

**Final local result:** all executed local checks pass. The project is complete as
a **virtual engineering reconstruction**, but it is not physically validated, the
Wokwi scenarios were not executed, remote GitHub Actions was not observed, and
the Nano 3D model is not included. Those are disclosed limitations, not passes.

## 2. Environment and method

| Item | Value |
|---|---|
| Host | Windows, Git Bash; repository `C:\Users\Chukwuka Nwabueze\ECHOCANE` |
| Nano toolchain | PlatformIO, `atmelavr`, Arduino AVR 5.4.0, AVR GCC 7.3.0 |
| Native tests | `python:3.12-bookworm`, PlatformIO native, Unity |
| KiCad | `kicad/kicad:10.0-full` / `kicad/kicad:10.0`, KiCad 10.0.8 |
| ngspice | ngspice-44.2 in the KiCad container |
| Wokwi | `wokwi-cli` and `WOKWI_CLI_TOKEN` unavailable |
| Physical hardware | none available |

Method: inspect every tracked directory and file category; read the firmware and
its tests; independently inspect KiCad symbols, footprints and pad numbering;
recalculate the driver; re-run builds, tests, validators, ERC, DRC and ngspice;
compare regenerated manufacturing data with the committed outputs; inspect the
CI workflows; and cross-check every documentation claim against evidence.

## 3. Findings and dispositions

The table records the issue as found, the correction, and the final state. A
`FAIL` that has a verified correction is retained in the audit trail as a resolved
finding; it is not hidden by rewriting history.

| ID | Finding | Initial | Final | Evidence |
|---|---|---|---|---|
| REP-01 | Missing source files, broken references, duplicate implementations, temporary files or committed credentials | PASS | PASS | `git ls-files`, full file sweep, link check, `.gitignore`; no credentials or temp files found |
| REP-02 | Optional `H5-H6` BOM row had no schematic/PCB component | FAIL | PASS | Row removed from `generate_schematic.py`; BOM now 15 rows; `validate_hardware.py` passes |
| FW-01 | Forced-beta check had the inequality backwards; 1 kΩ was above the 380 Ω saturation limit | FAIL | PASS | `driver_analysis.py` corrected; R1 1 kΩ → 330 Ω → 270 Ω after loaded-GPIO review; check passes; ngspice re-run |
| FW-02 | Echo-pulse conversion lacked a portable overflow guard/test | FAIL | PASS | `SensorMath.h` added; `SensorManager` uses it; boundary and full-domain tests pass |
| FW-03 | Missing tests for exact release boundaries, recovery-to-clear, millis wrap, zero-capacity telemetry | FAIL | PASS | 7 tests added; 25/25 native tests pass |
| FW-04 | Dead `modeAnnounceMs` configuration and unused `compose()` parameter | FAIL | PASS | Removed; Nano build passes at 10,766 B flash / 777 B RAM |
| FW-05 | Documentation said `raw=Valid`; firmware emits `raw=OK` | FAIL | PASS | Docs corrected; clear-record test asserts `raw=OK` |
| FW-06 | Review of timing, filtering, hysteresis, fault/recovery, debounce, PWM, blocking and startup | PASS | PASS | Code review plus 25 host tests; bounded `pulseIn` documented; no unbounded loop wait |
| FW-07 | Real sensor timing, temperature and acoustic assumptions | NOT VERIFIED | NOT VERIFIED | No hardware; 343 m/s / 58 µs·cm⁻¹ and 25 ms timeout documented as assumptions |
| HW-01 | Nano pin assignments, PN2222A EBC, D1/LED/C2 polarity, connector numbering | PASS | PASS | KiCad symbol/pad inspection; netlist/pad map; table below |
| HW-02 | Base resistor sized for the stated 100 mA load | FAIL | PASS | 270 Ω: 11.11 mA pin current, 0.12 mA R2, 10.99 mA base, forced beta 9.10; ngspice 12.04 mA base, beta 8.66; pin limit respected |
| HW-08 | 330 Ω result assumed ideal 5 V GPIO and omitted R2; loaded GPIO invalidates it | FAIL | PASS | Datasheet VOH 4.2 V at 20 mA; loaded limit 296.4 Ω; 330 Ω and 300 Ω rejected; 270 Ω selected; loaded model re-run |
| HW-03 | Flyback diode polarity and rating | PASS | PASS | 1N4007 cathode to +5 V, anode to collector; 1000 V/1 A vs 5.63 V/104.4 mA model stress |
| HW-04 | Power, decoupling, ground, trace widths and clearances | PASS | PASS | 0.5 mm signal / 0.8 mm motor and +5 V; bottom GND zone; DRC 0; physical current/thermal not measured |
| HW-05 | C1/C2 body clearance | FAIL | PASS | C2 moved to `(90,50)`; +5 V stub rerouted; DRC 0; 3D render inspected |
| HW-06 | PCB title block/revision lost during regeneration | FAIL | PASS | Generator sets title, revision 0.1, date and company; Gerber job revision 0.1 |
| HW-07 | Arduino Nano 3D model absent | NOT VERIFIED | NOT VERIFIED | Official KiCad library lacks model; CC0 x3d candidate found but not dimensionally verified, so not included |
| SIM-01 | Six Wokwi diagrams: parts, GPIO, polarity/proxy wiring and stimulus | PASS | PASS | Exact validator passes all 6 diagrams; distances 300/120/50/300/300 and fault ECHO→GND |
| SIM-02 | Wokwi scenario execution | NOT VERIFIED | NOT VERIFIED | No `wokwi-cli`, no token; no serial logs claimed |
| SIM-03 | Manual moving-away procedure reproducibility | NOT VERIFIED | NOT VERIFIED | Procedure documented; not executed |
| SIM-04 | ngspice model and assumptions | PASS | PASS | Executed; values below; lumped motor and generic models disclosed |
| MFG-01 | Gerber layer completeness | PASS | PASS | 2 copper, 2 silk, 2 mask, 1 outline + job file; no paste by design |
| MFG-02 | Drill correspondence | PASS | PASS | Excellon T1–T6 matches 63 PTH + 4 NPTH; drill map present |
| MFG-03 | Board outline and dimensions | PASS | PASS | 100 × 85 mm outline; mounting holes at 5/95 mm corners |
| MFG-04 | Copper, GND zone, footprints, unconnected pads | PASS | PASS | DRC 0/0/0; parity 0; 15 THT + 4 holes |
| MFG-05 | Manufacturing files match latest board | PASS | PASS | Regenerated outputs match committed Gerber/drill text except creation timestamps; revision 0.1 |
| MFG-06 | Fabrication/assembly approval | NOT VERIFIED | NOT VERIFIED | No board house, assembly or physical inspection |
| CI-01 | Workflow YAML, paths, dependencies and local equivalents | PASS | PASS | YAML parses; local commands pass; native test ordering documented |
| CI-02 | Remote GitHub Actions execution | NOT VERIFIED | PASS | EchoCane CI run 43788851832 passed firmware/tests and KiCad ERC/DRC on GitHub |
| DOC-01 | Documentation matches implementation | FAIL | PASS | 1 kΩ/old ngspice/raw names/mode distance/test count corrected; audit links added |
| DOC-02 | Local Markdown links and asset references | PASS | PASS | Link check passes; images present |
| IMP-01 | Architecture/testability/memory/readability review | PASS | PASS | Portable core, fixed buffers, no heap; optional future input-capture/watchdog work documented |
| PHY-01 | Physical, user, EMC, thermal, drop, acoustic validation | NOT VERIFIED | NOT VERIFIED | No hardware or users |
| NA-01 | Paste layers, pick-and-place and reflow profile | NOT APPLICABLE | NOT APPLICABLE | All 15 electrical footprints are through-hole |
| NA-02 | Li-ion charger/protection | NOT APPLICABLE | NOT APPLICABLE | Design is a tethered regulated 5 V USB prototype |

## 4. Repository audit

- `git ls-files` was inspected in full. There are no tracked `.env`, token,
  credential, backup, `.orig`, `.rej`, `*.tmp` or editor-swap files.
- `.pio`, `.venv`, `.freebuff`, `test-results`, the raw ngspice waveform and local
  editor state are ignored. The generated `driver-waveform.txt` was not committed.
- `hardware/kicad/EchoCane.kicad_prl` is not tracked.
- No duplicate firmware implementation was found. The portable core and the
  Arduino adapters have distinct responsibilities.
- The BOM now has exactly the 15 electrical components represented in the
  netlist; H1–H4 are mechanical holes and are excluded from the BOM.
- README commands were re-run from the repository root; the build, native tests,
  validators, ERC, DRC and ngspice commands all work with the documented
  containers/toolchain.
- The local Markdown link check passes for the files changed by this audit.

## 5. Firmware audit

### 5.1 Architecture and memory

`echocane_core` is independent of `Arduino.h`; `firmware/src` contains the
Arduino adapters. The final Nano build is:

```text
Flash: 10,766 / 30,720 bytes (35.0 %)
RAM:     777 /  2,048 bytes (37.9 %)
SUCCESS
```

There is no heap allocation, STL container, exception or RTTI in the firmware.
The median filter is a fixed five-element array; telemetry uses a fixed 128-byte
buffer. The largest stack path is telemetry formatting, and the median sort copies
five `uint16_t` values.

### 5.2 Distance acquisition

`SensorManager` emits a 2 µs low, 10 µs high TRIG pulse, then calls
`pulseIn(ECHO, HIGH, 25,000)`. The 25 ms timeout is above the ~23.2 ms round trip
for 400 cm at 343 m/s. A zero pulse is a timeout. The conversion is now the
portable `centimetersFromEchoPulse()` helper:

```text
cm = round(durationUs / 58)
```

The helper guards the `durationUs + 29` addition against `uint32_t` overflow and
the caller applies the 2–400 cm range. Tests cover 0, 57, 58, 116, 8,700, 23,200
and 25,000 µs and the full input domain.

**Assumption:** 343 m/s at about 20 °C. At lower temperatures the speed of sound
is lower, so a valid 400 cm echo can approach or exceed the 25 ms timeout. This is
a real temperature-dependent margin and is not verified on hardware.

### 5.3 Filtering, hysteresis and state transitions

- A five-sample median rejects one isolated spike and uses the lower median for
  even counts. The first valid sample is accepted, so the device warns early
  rather than waiting for a full window; this is conservative and documented.
- Thresholds are strict `< 80 cm` for danger and `<= 150 cm` for caution.
- Caution releases only above 160 cm; danger releases to caution above 90 cm and
  directly to clear only above 160 cm. Exact tests cover 90/91 and 160/161.
- Three consecutive invalid readings confirm `FAULT`; three consecutive valid
  readings recover. The controller never reports `obstacleFree` during fault and
  holds at least caution during degraded/recovering states.
- New tests verify recovery to clear on the third valid reading and verify that
  two valid readings after degradation/fault still do not clear.

### 5.4 Debounce, PWM and warning timing

- The button is active-low with `INPUT_PULLUP`, a 100 nF hardware capacitor and a
  30 ms stable-state debounce. The host test covers bounce and a single press.
- D6 uses `analogWrite` (0/102/255 for 0/40/100 %) and D8 uses `tone()`. They are
  on different timers in this configuration; no pin/timer conflict was found.
- `PulseTimer` uses unsigned `millis()` subtraction. A new rollover test configures
  a pattern 50 ms before wrap and verifies the on/off transitions across the wrap.
- `pulseIn` blocks for at most 25 ms. The 60 ms scan period leaves bounded
  headroom, but the loop is not hard-real-time. Serial output can also block if
  the transmit buffer is full; telemetry is only 2 Hz / 4 Hz and the buffer is
  fixed. A future input-capture design is documented as an improvement, not
  claimed as implemented.

### 5.5 Startup and failure behaviour

Outputs are initialised off; the controller starts in `STARTING`; the first scan
is scheduled immediately; a missing sensor degrades to caution and then fault.
A failed reading never becomes a clear assertion. No uninitialised control-path
state was found. `AlertCommand` is fully initialised before use.

### 5.6 Test coverage added

The suite now contains 25 tests, including:

- echo conversion boundaries and overflow;
- exact danger/caution release boundaries;
- fault recovery to clear after exactly three valid readings;
- degraded recovery remaining caution for two valid readings;
- `millis()` rollover in `PulseTimer`;
- `raw=OK` and both distance fields in a clear telemetry record;
- null/zero-capacity telemetry safety.

No existing test was weakened or removed.

## 6. Electrical audit

### 6.1 Independent pin and polarity check

The Nano symbol in `MCU_Module` and the board pad map agree:

| Signal | Nano symbol pad | Board pad | Destination |
|---|---:|---:|---|
| D2 / button | 5 | 5 | SW1 to GND; internal pull-up; C3 to GND |
| D6 / haptic PWM | 9 | 9 | R1 → Q1 base |
| D7 / LED | 10 | 10 | R3 → D2 anode |
| D8 / buzzer | 11 | 11 | R4 → BZ1 positive |
| D9 / TRIG | 12 | 12 | J1 pin 2 |
| D10 / ECHO | 13 | 13 | J1 pin 3 |
| +5 V | 27 | 27 | J1.1, J2.1, D1 cathode, C1.1, C2.1 |
| GND | 4, 29 | 4, 29 | J1.4, Q1 emitter, R2.2, C1.2, C2.2, C3.2, D2 cathode, SW1.2, BZ1.2 |

Component polarity/numbering was checked against the KiCad library symbols and
footprint pads:

- **Q1 PN2222A:** `Q_NPN_EBC` has pin 1 = E, 2 = B, 3 = C; board pad 1 = GND,
  pad 2 = `Q_BASE`, pad 3 = `MOTOR_NEG`. TO-92 inline footprint pads are 1–2–3.
- **D1 1N4007:** symbol pin 1 = K, pin 2 = A; board pad 1 = +5 V, pad 2 =
  `MOTOR_NEG`. Flyback polarity is correct.
- **D2 LED:** symbol pin 1 = K, pin 2 = A; board pad 1 = GND, pad 2 = `LED_A`.
- **C1/C2:** pad 1 = +5 V, pad 2 = GND; `CP_Radial` pad 1 is the positive pad.
- **BZ1:** pad 1 = + (driven through R4), pad 2 = GND.
- **J1/J2:** sequential 1–4 and 1–2 headers; J1 is +5 V/TRIG/ECHO/GND, J2 is
  +5 V/motor negative.

### 6.2 Driver recalculation

The earlier 330 Ω result is retained as a failure case, not as the design:

| Quantity | Previous ideal-5 V result | Revised loaded-GPIO result |
|---|---:|---:|
| GPIO model | 5.0 V ideal | **4.2 V guaranteed VOH at 20 mA** |
| R2 loading | omitted | 10 kΩ, 0.12 mA at VBE 1.2 V |
| R1 | 330 Ω | **270 Ω** |
| R1 / pin current | 11.515 mA | 11.111 mA |
| Base current | 11.515 mA | **10.991 mA** |
| Forced beta at 100 mA | 8.68 | **9.10** |
| Forced-beta-10 R1 limit | 380 Ω (ideal) | **296.4 Ω** |
| R1 power | 43.8 mW | 33.3 mW |
| Pin margin to 20 mA | 8.49 mA | 8.89 mA |

The ATmega328P datasheet guarantees VOH ≥ 4.2 V at IOH = −20 mA and VCC = 5 V
over −40 to +85 °C. The actual pin current is about 11 mA; using 4.2 V rather than
the higher typical value is conservative. VBE(sat) is assumed to be 1.2 V, the
PN2222A datasheet maximum at 150 mA / 15 mA, applied at 100 mA. R2 diverts
0.12 mA from the base node; the GPIO still sources the full 11.11 mA through R1.

```text
I_R1 = (4.2 - 1.2) / 270       = 11.11 mA
I_R2 = 1.2 / 10,000             = 0.120 mA
Ib   = 11.11 - 0.120            = 10.99 mA
beta = 100 / 10.99              = 9.10
R1(max) = 3.0 / (0.010 + 0.00012) = 296.4 Ω
P_R1 = 3.0^2 / 270              = 33.3 mW
```

Component comparison at the same loaded-GPIO and VBE assumptions:

| R1 | Base current | Forced beta | Max motor at beta 10 | Result |
|---:|---:|---:|---:|---|
| 330 Ω | 8.97 mA | 11.15 | 89.7 mA | **rejected** |
| 300 Ω | 9.88 mA | 10.12 | 98.8 mA | **rejected**: above 296.4 Ω limit |
| **270 Ω** | **10.99 mA** | **9.10** | **109.9 mA** | **selected** |

At VBE = 0.6 V the pin current is 13.33 mA and the base current is 13.27 mA, so
the worst-case pin current is still below the recommended 20 mA continuous limit
(absolute maximum 40 mA). The 0.25 W R1 dissipates 48 mW at that extreme.

**Worst-case motor operating current:** no defensible number can be stated
without a motor datasheet or stall measurement. The 100 mA figure is a design
point. The selected drive supports about **109.9 mA** at the forced-beta-10
target; a 150 mA stress case has forced beta 13.6 and is not covered. Stall is
`NOT VERIFIED`.

The updated ngspice model uses the same 4.2 V source, 270 Ω and R2. Its lower
simulated VBE (0.923 V) gives more base current than the conservative paper
case:

| Quantity | Paper | ngspice |
|---|---:|---:|
| Loaded drive voltage | 4.2 V assumed | 4.20 V |
| R1 current | 11.11 mA | 12.14 mA |
| R2 current | 0.12 mA | 0.092 mA |
| Base current | 10.99 mA | 12.04 mA |
| Vbe | 1.2 V assumed | 0.923 V |
| Vce, on | 0.3 V assumed | 0.0945 V |
| Motor current | 100 mA assumed | 104.37 mA |
| Motor voltage | 4.7 V | 4.91 V |
| Q1 dissipation | 30 mW conservative | 9.86 mW |
| Collector peak at turn-off | — | 5.63 V |
| Diode peak | — | 104.37 mA |

The 1N4007 is rated 1000 V and 1 A, far above the model's 5.63 V / 104.4 mA. The
model is not a manufacturer model and does not prove thermal or EMC behaviour.

### 6.3 Power, decoupling and grounding

The revised design estimate is 174.7 mA on a 500 mA regulated USB source, leaving
325.3 mA of nominal headroom:

| Load | Estimate |
|---|---:|
| Nano board allowance | 25 mA |
| HC-SR04 peak | 15 mA |
| Motor design point | 100 mA |
| GPIO/base drive through R1 | 11.1 mA |
| Buzzer | 10 mA |
| Status LED | 13.6 mA |
| **Total** | **174.7 mA** |

The 0.12 mA in R2 is part of the 11.1 mA R1 current and is not counted twice. The
motor is assumed to be 100 mA at 5 V; **stall current is unknown** and can exceed
this. The source, connector and 0.8 mm +5 V/motor traces must be sized for the
real motor before use.

C1 (100 nF) and C2 (10 µF) are near the motor supply. The audit moved C2 from
`(80,50)` to `(90,50)` mm because the original 5 mm centre spacing made the two
5 mm bodies tangent; the new spacing is 10 mm horizontally plus the 5 mm vertical
offset, with a clear DRC result. C3 debounces the button. The bottom-layer GND
zone is continuous around the routed +5 V and buzzer-command tracks. There is no
reverse-polarity, fuse, TVS/ESD or inrush protection; these are documented
production gaps, not hidden features.

### 6.4 Trace widths, clearance, holes and footprints

- Board: 100 × 85 mm outline, 2 layers, 1.6 mm FR-4, 0 vias.
- Signal traces: 0.5 mm; motor low side and +5 V distribution: 0.8 mm.
- Minimum configured clearance: 0.62 mm; minimum track: 0.5 mm; minimum drill:
  0.75 mm.
- 63 PTH pads, 4 NPTH 3.2 mm mounting holes at (5,5), (95,5), (5,80), (95,80).
- 15 THT electrical footprints, 0 SMD, 0 paste layers.
- All footprints are standard KiCad library footprints; the board is a
  hand-solder prototype, not a production assembly.

The 0.8 mm traces are conservative for the 100 mA model but have not been
thermally or electrically tested. A 1000 V diode is electrically oversized for a
5 V motor, which is acceptable for a prototype; its slow recovery is not an EMC
qualification.

## 7. Simulation audit

### 7.1 Wokwi

The six diagrams are:

| Diagram | Distance/stimulus | ECHO wiring | Structural result |
|---|---|---|---|
| main `diagram.json` | 300 cm | D10 | PASS |
| `clear.json` | 300 cm | D10 | PASS |
| `caution.json` | 120 cm | D10 | PASS |
| `danger.json` | 50 cm | D10 | PASS |
| `mode_button.json` | 300 cm + button | D10 | PASS |
| `sensor_fault.json` | 300 cm; ECHO tied to GND | GND.2 | PASS |

The validator checks all common links: HC-SR04 VCC/GND/TRIG, button to D2 and
GND, status LED chain on D7, haptic proxy chain on D6, and buzzer on D8. It checks
the expected distance per diagram and the fault-specific ECHO connection. It also
checks that the Nano, sensor, button and buzzer parts exist and that all scenario
YAML files and diagrams exist. Result:

```text
OK: 6 diagrams validated with explicit pin/stimulus mappings, 0 warning(s)
```

The Wokwi scenario **execution** remains `NOT VERIFIED`: `wokwi-cli` and
`WOKWI_CLI_TOKEN` are unavailable. `run_wokwi_scenarios.py --dry-run` prints five
valid commands, but a dry run is not an execution. No serial logs are claimed.

The manual moving-away procedure is documented and structurally consistent, but
it was not executed. Wokwi's HC-SR04 distance is a manual slider; the static
per-scenario diagrams are the honest alternative to pretending there is an
automation control.

### 7.2 ngspice

`driver.cir` was run with ngspice-44.2 after the loaded-GPIO correction. The
measured values are in the table above. The model includes a 47 Ω / 10 mH motor,
generic PN2222A Gummel-Poon model, generic 1N4007, **4.2 V loaded-GPIO source**,
**270 Ω**, **10 kΩ pull-down** and a 20 ms pulse. The constant 4.2 V source is a
conservative DC bound, not a fit to the GPIO curve. The model does not include
temperature, self-heating, back-EMF, brush noise, supply impedance, PCB parasitics
or EMC. It is a design check, not a bench measurement.

## 8. PCB manufacturing audit

### 8.1 Gerber and drill completeness

The Gerber job lists:

| File | Function | Polarity |
|---|---|---|
| `EchoCane-F_Cu.gtl` | Copper, L1, top | Positive |
| `EchoCane-B_Cu.gbl` | Copper, L2, bottom | Positive |
| `EchoCane-F_Silkscreen.gto` | Legend, top | Positive |
| `EchoCane-B_Silkscreen.gbo` | Legend, bottom | Positive |
| `EchoCane-F_Mask.gts` | Solder mask, top | Negative |
| `EchoCane-B_Mask.gbs` | Solder mask, bottom | Negative |
| `EchoCane-Edge_Cuts.gm1` | Profile | Positive |

There are no paste layers because every electrical footprint is through-hole.
The Excellon drill file is metric, mixed plating, with tools:

```text
T1 0.750 mm (3 PTH)
T2 0.800 mm (14 PTH)
T3 0.900 mm (2 PTH)
T4 1.000 mm (38 PTH)
T5 1.100 mm (6 PTH)
T6 3.200 mm (4 NPTH)
```

The drill map PDF and Gerber job file are present. The job file reports revision
0.1, 2 layers, 1.6 mm thickness and a 100.1 × 85.1 mm Gerber bounding box; the
0.1 mm is the outline stroke width around the actual 100 × 85 mm board. The
outline coordinates are 0/100 mm and 0/−85 mm.

### 8.2 Correspondence with the board

The Gerbers, drill file, STEP, PDF, SVG, schematic PDF/SVG and renders were
regenerated from the audited KiCad files. A second export into a temporary
directory was compared line-by-line with the committed Gerber/drill content after
removing creation-date metadata; every copper, mask, silk, outline and drill file
matched. The job files and PDFs matched in size. This establishes that the
committed manufacturing outputs correspond to the current board revision, not an
older one.

### 8.3 What remains unverified

- No board house has checked the files; no fabrication panel or DFM review was
  performed.
- The drill file is mixed-plating; a fabricator may require separate PTH/NPTH
  files or a different format.
- No assembly, solderability, connector fit, enclosure fit, EMC, ESD, thermal,
  vibration or drop test was performed.
- The Arduino Nano 3D model is absent; `A1` is a footprint outline in the render
  and is omitted from the STEP. The official KiCad library does not contain the
  referenced `Module.3dshapes/Arduino_Nano_WithMountingHoles.step`. A CC0 x3d
  candidate exists (`g200kg/kicad-lib-arduino`), but it was not independently
  dimensionally verified and is not included. The board geometry and pad map do
  not depend on the visual model.

## 9. Continuous-integration audit

`ci.yml` parses as YAML and defines two jobs:

1. `firmware`: native tests, Nano build, Wokwi structural validation,
   cross-artifact validation and driver-margin calculation.
2. `kicad`: ERC and DRC in `kicad/kicad:10.0`, with verification-report artifact
   upload.

`wokwi.yml` is separate and token-gated. It builds the firmware, checks for the
secret, installs the CLI only when the token is present, runs the scenarios and
uploads serial logs. It does not print the token. It skips with a notice when
the token is absent.

The native tests run before the Nano build because the native test task can clean
the AVR build directory; that ordering is required for the structural validator's
firmware-presence check. Local equivalents all pass. **Remote GitHub Actions
execution is `NOT VERIFIED`**: no run was observed, so no remote pass is claimed.

## 10. Documentation audit

Documentation was checked against the implementation and corrected where stale:

- R1 value, base current, forced-beta reasoning and ngspice numbers.
- RAM from 779 to 777 bytes; test count from 18 to 25.
- Telemetry `raw=OK` instead of `raw=Valid`.
- Wokwi mode-button diagram is 300 cm, not 120 cm.
- Optional H5–H6 sourcing is no longer described as a BOM row.
- BOM is 15 rows; board revision 0.1; C1/C2 clearance; 3D model limitation.
- Added this audit report and the limitations register; README now links both.

The local Markdown link check passes and the image assets exist. The documents
still distinguish executed checks from structural checks, and physical/user
validation remains explicitly outstanding.

## 11. Performance and engineering review

The architecture is appropriate for an ATmega328P Nano:

- The portable policy core is the right separation: it makes the safety logic
  host-testable while keeping Arduino APIs in adapters.
- Fixed buffers and no heap fit the 2 KB SRAM constraint.
- A five-sample median is a reasonable low-cost spike filter; it adds up to five
  scan intervals of latency but the first sample still warns.
- Asymmetric hysteresis is appropriate; the 10 cm release band is a demonstration
  choice, not a validated ergonomic value.
- The 270 Ω base resistor is consistent with the loaded-GPIO forced-beta target
  and the Nano pin limit. The 330 Ω and 300 Ω cases are retained as rejected
  alternatives. A logic-level IRLZ44N MOSFET is electrically viable at 4.5 V
  (35 mΩ vendor parametric maximum; 39 mΩ conservative bound) but would require
  a TO-220 footprint, gate resistor and pull-down; it is not a drop-in
  replacement for this prototype.
- The largest remaining firmware improvement is replacing `pulseIn` with timer
  input capture, which would remove the 25 ms blocking window. That would be a
  new implementation and is not included in this audit.
- A watchdog, checksummed telemetry, connector protection, reverse-polarity
  protection and a proper power path are sensible production improvements, not
  changes that can be meaningfully verified without hardware.

No unnecessary feature was added. The original modular structure was retained.

## 12. Correction trail

| File(s) | Change |
|---|---|
| `hardware/generate_schematic.py` | R1 value 1 kΩ → 330 Ω → **270 Ω**; removed optional H5–H6 BOM row |
| `hardware/generate_pcb.py` | C2 moved to (90,50), +5 V stub rerouted, C2 reference moved, board title/revision set |
| `hardware/kicad/*`, `hardware/bom/*`, `hardware/gerber/*`, `hardware/pcb/*`, `hardware/schematic/*` | Regenerated from the corrected generators/netlist |
| `firmware/lib/echocane_core/include/echocane/AppConfig.h` | Removed unused `modeAnnounceMs` |
| `firmware/lib/echocane_core/{include,src}/EchoCaneController.*` | Removed unused `compose()` parameter |
| `firmware/lib/echocane_core/include/echocane/SensorMath.h`, `firmware/src/SensorManager.cpp` | Added overflow-safe portable echo conversion |
| `firmware/test/test_core/test_core.cpp` | Added 7 edge-case tests; 25 total |
| `simulation/simulide/driver_analysis.py`, `driver.cir`, `plot_driver.py` | Corrected forced-beta check; loaded 4.2 V GPIO/R2 model; R1 270 Ω; regenerated ngspice/waveform |
| `tests/validate_simulation.py` | Exact GPIO/polarity/stimulus validation for all 6 diagrams |
| `README.md`, `docs/*`, `simulation/**/README.md` | Corrected values, links, audit/limitations register |

## 13. Reproduction commands

Run from the repository root. On Linux/macOS replace `.venv/Scripts/` with
`.venv/bin/`.

```bash
# 1. Nano firmware
./.venv/Scripts/pio.exe run -e nanoatmega328

# 2. Native unit tests (25)
MSYS_NO_PATHCONV=1 docker run --rm -v "$PWD:/work" -w /work \
  python:3.12-bookworm bash -lc \
  'python -m pip install -q platformio; pio test -e native'

# 3. Structural and cross-artifact checks
python tests/validate_simulation.py
python tests/validate_hardware.py
python simulation/simulide/driver_analysis.py

# 4. ngspice (KiCad image contains ngspice)
MSYS_NO_PATHCONV=1 docker run --rm -v "$PWD:/work" -w /work/simulation/simulide \
  kicad/kicad:10.0-full bash -lc \
  'ngspice -b -o ngspice-results.txt driver.cir'
python simulation/simulide/plot_driver.py

# 5. Wokwi command preview (not execution)
python tests/run_wokwi_scenarios.py --dry-run

# 6. KiCad ERC/DRC
MSYS_NO_PATHCONV=1 docker run --rm -v "$PWD:/work" -w /work \
  kicad/kicad:10.0-full bash -lc '
  kicad-cli sch erc --severity-all --exit-code-violations \
    -o hardware/verification/schematic-erc.rpt \
    hardware/kicad/EchoCane.kicad_sch &&
  kicad-cli pcb drc --severity-all --exit-code-violations \
    --schematic-parity --refill-zones \
    -o hardware/verification/pcb-drc.rpt \
    hardware/kicad/EchoCane.kicad_pcb'

# 7. Regenerate schematic/netlist/BOM and PCB
MSYS_NO_PATHCONV=1 docker run --rm -v "$PWD:/work" -w /work \
  kicad/kicad:10.0-full bash -lc '
  python3 hardware/generate_schematic.py &&
  kicad-cli sch export netlist --format kicadsexpr \
    -o hardware/kicad/EchoCane.net hardware/kicad/EchoCane.kicad_sch &&
  python3 hardware/generate_pcb.py'

# 8. Regenerate manufacturing/plot outputs
MSYS_NO_PATHCONV=1 docker run --rm -v "$PWD:/work" -w /work \
  kicad/kicad:10.0-full bash -lc '
  kicad-cli pcb export gerbers \
    -l F.Cu,B.Cu,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts \
    -o hardware/gerber/ hardware/kicad/EchoCane.kicad_pcb &&
  kicad-cli pcb export drill --format excellon --excellon-units mm \
    --generate-map --map-format pdf -o hardware/gerber/ \
    hardware/kicad/EchoCane.kicad_pcb &&
  kicad-cli pcb export step --force -o hardware/pcb/EchoCane.step \
    hardware/kicad/EchoCane.kicad_pcb &&
  kicad-cli pcb export pdf \
    -l F.Cu,B.Cu,F.Silkscreen,B.Silkscreen,Edge.Cuts --mode-single \
    -o hardware/pcb/EchoCane-pcb.pdf hardware/kicad/EchoCane.kicad_pcb &&
  kicad-cli pcb export svg \
    -l F.Cu,B.Cu,F.Silkscreen,B.Silkscreen,Edge.Cuts --mode-single \
    -o hardware/pcb/EchoCane-pcb.svg hardware/kicad/EchoCane.kicad_pcb'
```

Remote Wokwi execution requires `wokwi-cli` and `WOKWI_CLI_TOKEN`; never commit
the token. Remote GitHub Actions execution requires pushing the repository and
observing the workflow run. The repository has since been pushed and
[EchoCane CI run 43788851832](https://github.com/cn108/EchoCane/actions/runs/43788851832)
passed both the firmware/tests and KiCad ERC/DRC jobs. Wokwi scenarios remain
unexecuted because no CLI token is configured.

## 14. Residual limitations

See [`limitations-register.md`](limitations-register.md) for the itemised,
outstanding limitations and their closure conditions. The most important are:

- no physical hardware, user, acoustic, thermal, EMC, ESD, drop or reliability
  testing;
- no Wokwi execution and no serial logs;
- no SimulIDE `.simu` file;
- no remote GitHub Actions result;
- no fabrication/DFM/assembly approval;
- no Arduino Nano 3D model;
- motor stall current and worst-case transistor gain unmeasured;
- ultrasonic temperature and surface assumptions unverified.

## 15. Audit conclusion

**Available local verification: PASS.** The corrected repository builds, passes
25 native tests, passes both structural validators, passes the corrected driver
margin checks, passes ERC and DRC, and has manufacturing outputs that match the
current board. The audit corrections are recorded rather than hidden.

**Physical and external verification: NOT VERIFIED.** The project must not be
presented as a validated mobility aid, a manufactured board or a remotely
CI-verified build. It is a technically audited virtual reconstruction with
explicit, reproducible evidence and explicit limitations.
