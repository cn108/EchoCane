# Requirements

## 1. Context

EchoCane is a virtual reconstruction of an undergraduate smart-walking-stick
concept. The original code, circuit diagrams and motherboard documentation are
not available. These requirements are therefore **reconstructed from the project
brief**, not recovered from the original project, and they deliberately separate
demonstration behaviour from claims of clinical or safety performance.

The system is an experimental supplementary aid. It is not a replacement for a
conventional mobility cane.

## 2. Stakeholders and use context

| Stakeholder | Need |
|---|---|
| Visually impaired user | Understandable, early warning of nearby obstacles without masking a cane |
| Developer / maintainer | Testable policy code, clear hardware interfaces, reproducible artifacts |
| Reviewer / recruiter | Evidence of engineering judgement, verification and honest limitations |
| Manufacturer (future) | Consistent schematic, PCB, BOM, drill and Gerber outputs |

The intended demonstration context is an indoor, dry, benchtop environment with a
5 V USB supply. Outdoor use, rain, rough terrain, stairs and drop-offs are outside
the validated scope.

## 3. Functional requirements

| ID | Requirement | Verification |
|---|---|---|
| FR-01 | Acquire distance with an HC-SR04 over a documented 2–400 cm range. | `SensorManager`, range checks, native tests |
| FR-02 | Report `CLEAR` when the filtered distance is above 150 cm. | Unit tests; Wokwi scenario 01 (not executed) |
| FR-03 | Report `CAUTION` for 80–150 cm inclusive, with a caution pattern. | Unit tests; Wokwi scenario 02 (not executed) |
| FR-04 | Report `DANGER` below 80 cm, with a strong pattern. | Unit tests; Wokwi scenario 03 (not executed) |
| FR-05 | Treat timeout, no echo and out-of-range readings as invalid; never as clear. | Unit tests; fault diagram (not executed) |
| FR-06 | Filter noise with a bounded median filter. | Five-sample median tests |
| FR-07 | Apply hysteresis so warning states do not chatter at thresholds. | Boundary/release tests |
| FR-08 | Debounce the mode button in firmware and with an RC filter. | Debounce test; circuit calculation |
| FR-09 | Confirm a sensor fault after 3 invalid readings; recover after 3 valid readings. | Fault/recovery tests |
| FR-10 | Provide Assist, Quiet and Diagnostic modes; a short press cycles modes. | Mode tests; Wokwi scenario 05 (not executed) |
| FR-11 | Emit machine-readable serial telemetry and event records. | Telemetry tests; serial reporter |
| FR-12 | Schedule scans, outputs and telemetry without `delay()` in the main loop. | Code inspection; `PulseTimer` tests |
| FR-13 | Drive a vibration motor through a transistor and a flyback diode. | Schematic, PCB, ngspice |
| FR-14 | Provide an optional audible warning through a buzzer. | Schematic, PCB, pattern tests |
| FR-15 | Provide a status LED for operating/fault state. | Schematic, PCB, pattern tests |

### 3.1 Threshold semantics

The brief defines:

| Distance | Level |
|---|---|
| above 150 cm | no obstacle warning (`CLEAR`) |
| 80–150 cm | caution (`CAUTION`) |
| below 80 cm | strong warning (`DANGER`) |

Boundary handling is explicit:

- `150 cm` is caution.
- `80 cm` is caution.
- `79 cm` is danger.
- A caution state releases to clear only above `160 cm` (150 + 10 cm hysteresis).
- A danger state releases to caution above `90 cm` (80 + 10 cm), and to clear
  above `160 cm`.

These values are demonstration parameters. They are not validated safety
thresholds and must not be presented as such.

### 3.2 Fault and recovery semantics

- A single invalid acquisition changes health from `OK` to `DEGRADED` (or from
  `STARTING` to `DEGRADED`).
- While degraded, the displayed level is at least `CAUTION`.
- Three consecutive invalid acquisitions confirm `FAULT`; the level becomes
  `FAULT`, the filter is reset and no distance is displayed.
- Three consecutive valid acquisitions restore `OK`. Until then the level is at
  least `CAUTION`.
- A bad reading never produces `obstacleFree = true`.
- `obstacleFree` is true only when health is `OK`, the level is `CLEAR`, the raw
  reading is valid and a filtered distance exists.

## 4. Hardware requirements

| ID | Requirement | Verification |
|---|---|---|
| HR-01 | Use a classic 5 V Arduino Nano (ATmega328P, 30-pin) as the controller. | PlatformIO target; BOM; schematic |
| HR-02 | Use the pin map in `Pins.h` consistently across firmware, Wokwi and KiCad. | `tests/validate_hardware.py` |
| HR-03 | Switch the motor with a PN2222A NPN low-side stage, 1 kΩ base resistor and 10 kΩ pull-down. | Schematic; ngspice |
| HR-04 | Include a 1N4007 flyback diode across the motor. | Schematic; ngspice transient |
| HR-05 | Decouple the motor supply with 100 nF ceramic and 10 µF bulk capacitance. | Schematic; PCB |
| HR-06 | Expose the HC-SR04 and motor through keyed/clear 2.54 mm headers. | Schematic; PCB |
| HR-07 | Debounce the mode button with 100 nF hardware capacitance in addition to firmware debouncing. | Schematic; calculation |
| HR-08 | Provide a visible status LED with a 220 Ω series resistor. | Schematic; calculation |
| HR-09 | Provide a 2-layer, 100 × 85 mm carrier board with M3 mounting holes. | PCB; stats |
| HR-10 | Produce ERC-clean schematic, DRC-clean PCB and manufacturing files. | Reports; Gerbers; drill |
| HR-11 | Use a commercial regulated 5 V USB source; do not design a Li-ion charger. | Requirements; docs |

## 5. Non-functional requirements

| ID | Requirement | Evidence |
|---|---|---|
| NFR-01 | Keep application policy independent of Arduino headers. | `firmware/lib/echocane_core` has no `Arduino.h` |
| NFR-02 | Avoid dynamic allocation in the firmware. | No `new`, `malloc` or STL containers in firmware |
| NFR-03 | Fit the Nano's 2 KB RAM and 30 KB flash with margin. | 779 B RAM (38 %), 10,766 B flash (35 %) |
| NFR-04 | Provide host tests for every safety-relevant policy. | 18/18 native tests |
| NFR-05 | Keep the main loop free of long unbounded delays. | Scheduled scans/outputs; bounded `pulseIn` timeout |
| NFR-06 | Make hardware assumptions and simulation limits explicit. | README; limitations; safety analysis |
| NFR-07 | Support local builds/tests without Wokwi or a paid token. | `pio` build/test; structural validators |
| NFR-08 | Provide reproducible schematic/PCB generators and commands. | `hardware/generate_*.py`; docs |
| NFR-09 | Use consistent naming, fixed-width types and documented units. | Source headers and comments |
| NFR-10 | Do not fabricate test, simulation or manufacturing evidence. | Status tables and reports |

## 6. Interfaces

### 6.1 Sensor interface

```cpp
struct DistanceReading {
  ReadingStatus status;  // Valid, Timeout, OutOfRange
  uint16_t centimeters;
};
```

`SensorManager` issues a 10 µs TRIG pulse and measures ECHO high time with a
25,000 µs timeout. Distance is `(durationUs + 29) / 58` cm. Values below 2 cm or
above 400 cm are `OutOfRange`.

### 6.2 User interface

| Input/output | Behaviour |
|---|---|
| Mode button (D2, active low) | Short press cycles Assist → Quiet → Diagnostic → Assist |
| Haptic motor (D6 PWM) | Patterned duty; 0 % in clear, 40 % caution, 100 % danger |
| Buzzer (D8) | Tone patterns; muted in Quiet mode |
| Status LED (D7) | Starting blink, clear heartbeat, caution blink, danger solid, fault fast blink |
| Serial (USB, 115200) | Banner, periodic `EC|...` telemetry, `EC_EVENT|...` transitions |

### 6.3 Telemetry record

```text
EC|t=<ms>|raw=<Valid|Timeout|OutOfRange>|d=<cm|none>|f=<cm|none>|level=<...>|health=<...>|mode=<...>|free=<0|1>
```

`free=1` is an explicit assertion that the path is believed clear. It is never
set from a failed acquisition.

## 7. Acceptance criteria

| Criterion | Status |
|---|---|
| Nano firmware compiles | **PASS** |
| Core logic passes automated tests | **PASS** (18/18) |
| Wokwi files open and are structurally valid | **PASS** (structure only) |
| All required obstacle scenarios demonstrated | **NOT EXECUTED** (assets provided) |
| Sensor failures handled correctly | **PASS** in host tests; hardware unverified |
| KiCad schematic complete and consistent with firmware | **PASS** (ERC 0; cross-artifact check) |
| PCB exists and passes configured DRC | **PASS** (0/0/0) |
| Manufacturing outputs generated | **PASS** (files present; not fabricated) |
| Engineering documentation complete | **PASS** |
| GitHub Actions configured and available checks pass | **CONFIGURED**; GitHub run not observed here |
| Screenshots and test evidence included | **PASS** for build/tests/PCB; Wokwi screenshots absent |
| Limitations honestly documented | **PASS** |

## 8. Out of scope

- Clinical validation, user trials or claims of replacing a white cane.
- Detection of drop-offs, stairs, overhead obstacles, soft/transparent obstacles
  or complex outdoor scenes.
- Battery charging, Li-ion protection, regulatory certification or EMC testing.
- Production sourcing, assembly, enclosure design or manufacturability sign-off.
- Real-time guarantees beyond the documented cooperative scheduling.

## 9. Assumptions and open questions

1. The Nano is powered from a regulated 5 V USB source capable of at least
   500 mA; motor stall current is not characterised.
2. The HC-SR04 is the common 5 V module with a 2–400 cm nominal range.
3. The vibration motor is a small 5 V coin/bar motor drawing approximately
   100 mA at 5 V; this is an estimate, not a datasheet measurement.
4. The buzzer is a 5 V piezo buzzer; the 100 Ω series resistor limits current
   but the acoustic output is not characterised.
5. The PCB uses through-hole parts for a hand-solderable prototype.
6. The design uses generic KiCad symbols/footprints; a production BOM would need
   manufacturer part numbers, tolerances and ratings.
