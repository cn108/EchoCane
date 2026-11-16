# EchoCane outstanding limitations register

- **Register date:** 2026-11-16
- **Revision audited:** board/firmware 0.1
- **Status vocabulary:** `PASS`, `FAIL`, `NOT VERIFIED`, `NOT APPLICABLE`
- **Rule:** a limitation is closed only with evidence that directly addresses it;
  a clean build, DRC or structural check does not close a physical limitation.

| ID | Limitation | Impact | Evidence / current state | Status | Closure condition |
|---|---|---|---|---|---|
| LIM-01 | No physical EchoCane hardware exists | Firmware, sensor, actuator, power and PCB behaviour are unmeasured | No Arduino, HC-SR04, motor, buzzer, PCB or cane assembly was available | **NOT VERIFIED** | Build and bench-test a unit; record supply, current, timing and output measurements |
| LIM-02 | Wokwi scenarios were not executed | The simulated runtime path is unproven; only structure and mappings are checked | `wokwi-cli` and `WOKWI_CLI_TOKEN` unavailable; no serial logs claimed | **NOT VERIFIED** | Run all five automated scenarios with a token; archive serial logs and results |
| LIM-03 | SimulIDE is not installed and no `.simu` file exists | No GUI-simulator execution evidence | Build guide and calculations only | **NOT VERIFIED** | Install SimulIDE, build the documented circuit, save `.simu`, run and record measurements |
| LIM-04 | Motor current, stall current, torque and vibration are unknown | 100 mA design point and 270 Ω base drive may not cover a different motor; thermal/current margins unproven | 47 Ω / 10 mH model only; no motor datasheet or measurement; forced-beta-10 ceiling about 109.9 mA | **NOT VERIFIED** | Measure the chosen motor's free-run and stall current; verify transistor/base drive and supply |
| LIM-05 | No thermal, EMC, ESD, inrush, drop or long-duration testing | Production robustness and safety are unknown | No bench/EMC/thermal chamber; no enclosure | **NOT VERIFIED** | Run applicable bench/EMC/thermal/reliability tests and document results |
| LIM-06 | No fabrication, DFM, assembly or connector-fit test | Gerbers are outputs, not manufacturing approval | No board house, assembly or physical inspection | **NOT VERIFIED** | Obtain a DFM review, fabricate, assemble and inspect the board |
| LIM-07 | No Arduino Nano 3D model | A1 is a footprint outline in renders and missing from STEP; mechanical fit is less complete | Official KiCad library lacks the referenced Nano model; CC0 x3d candidate not dimensionally verified | **NOT VERIFIED** | Include a licensed, dimensionally checked model and regenerate STEP/renders |
| LIM-08 | Remote GitHub Actions was not observed | Remote CI pass is not established | Workflows parse and local equivalents pass; no remote run result | **NOT VERIFIED** | Push/trigger the workflows and record the GitHub run ID and result |
| LIM-09 | Ultrasonic temperature/surface assumptions are unverified | 343 m/s / 58 µs·cm⁻¹ and the 25 ms timeout may reject valid long echoes at low temperature; soft/angled/transparent surfaces can be missed | Calculation and code review only; no chamber or surface tests | **NOT VERIFIED** | Test at temperature extremes and against representative surfaces |
| LIM-10 | Power source and protection are not validated | USB source sag, reverse polarity, ESD, inrush and fault current are unhandled/unmeasured | Regulated 5 V USB assumption; no fuse/TVS/reverse protection | **NOT VERIFIED** | Test the intended source; add and validate protection for a production design |
| LIM-11 | Buzzer SPL and haptic perception are not measured | Audible/tactile warning effectiveness is unknown | Generic buzzer and motor models only; no user study | **NOT VERIFIED** | Measure SPL/vibration and conduct supervised user testing |
| LIM-12 | No user, ergonomic or cane-integration study | The device is not demonstrated as a usable assistive aid | No participants or cane hardware | **NOT VERIFIED** | Run an ethics-approved, supervised user/ergonomics study |
| LIM-13 | No watchdog or input-capture redesign | `pulseIn` can block for 25 ms; a hung loop has no watchdog reset | Bounded blocking is documented; no watchdog in firmware | **NOT VERIFIED** | Implement and test watchdog/input-capture in a future revision; do not claim current coverage |
| LIM-14 | Driver uses generic SPICE models and a conservative constant 4.2 V GPIO source | Absolute transistor/diode behaviour, actual GPIO VOH and worst-case gain are not guaranteed | Generic Gummel-Poon PN2222A and 1N4007 models; 4.2 V is the datasheet minimum at 20 mA, not a measured curve | **NOT VERIFIED** | Repeat with vendor models and bench measurements over temperature, including GPIO VOH under load |
| LIM-15 | Formal EMC/ESD and safety certification absent | The design is not a certified medical or safety device | No standards testing or certification | **NOT VERIFIED** | Complete applicable standards testing and certification before any real use |
| NA-01 | Paste layers, pick-and-place and reflow profile | Not required for the all-through-hole prototype | 15 THT footprints, 0 SMD | **NOT APPLICABLE** | Revisit only if the design moves to SMD |
| NA-02 | Li-ion charger/protection | Not part of this tethered USB prototype | Regulated 5 V USB architecture | **NOT APPLICABLE** | Add a separately validated power path if battery operation is required |
| NA-03 | Production enclosure drawing | No enclosure is claimed | Board-only reconstruction | **NOT APPLICABLE** | Add mechanical enclosure design if the product scope expands |

## Closed audit findings

These were defects found during the audit and are retained here for traceability;
they are not open limitations:

| ID | Closed finding | Closure evidence |
|---|---|---|
| CL-01 | Inverted forced-beta check and 1 kΩ base resistor above the 380 Ω saturation limit | R1 corrected to 330 Ω, then to **270 Ω** after the loaded-GPIO/R2 review; corrected check and ngspice pass |
| CL-02 | Optional H5–H6 BOM row with no schematic/PCB representation | Row removed; 15-row BOM; cross-artifact validator passes |
| CL-03 | C1/C2 bodies tangent | C2 moved to (90,50); DRC 0; render inspected |
| CL-04 | Board title/revision missing after regeneration | Generator writes 0.1; Gerber job reports 0.1 |
| CL-05 | Test coverage gaps | 7 edge-case tests added; 25/25 pass |
| CL-06 | Stale documentation values / `raw=Valid` | Docs corrected to implementation and new evidence |
| CL-07 | Wokwi validation did not assert exact GPIO/stimulus | Exact validator passes all 6 diagrams |
| CL-08 | 330 Ω driver result assumed ideal 5 V GPIO and omitted R2 | Loaded 4.2 V VOH, R2 and 270 Ω give forced beta 9.10; 330/300 Ω rejected |
| CL-09 | Power budget omitted base-drive current and used a low Nano allowance | Budget revised to 174.7 mA with 325.3 mA USB margin |

## Status summary

| Status | Count | Meaning |
|---|---:|---|
| PASS | 0 in this register | No physical/external limitation is closed by the audit |
| FAIL | 0 open | All identified local defects were corrected and rechecked |
| NOT VERIFIED | 15 | Physical, external or runtime checks not performed |
| NOT APPLICABLE | 3 | Paste/SMD assembly, Li-ion charging, enclosure |

The project is complete as a virtual reconstruction only; LIM-01 through LIM-15
must remain visible wherever the project is presented.
