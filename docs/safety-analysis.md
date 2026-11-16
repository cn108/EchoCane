# Safety analysis

> **Read this first**
> EchoCane is an experimental supplementary aid. It has not been tested on
> physical hardware, with visually impaired users, or in real environments. It is
> not a replacement for a conventional mobility cane, a guide dog, a trained
> orientation-and-mobility instructor, or any certified assistive product. The
> thresholds and patterns in this repository are demonstration parameters.

## 1. Intended use

EchoCane is intended for:

- benchtop demonstration of embedded sensing, filtering, fault handling and
- portfolio evidence of firmware, PCB and test engineering.

It is **not** intended for:

- sole navigation,
- road, traffic or platform-edge use,
- stairs, escalators or drop-offs,
- outdoor weather,
- medical or clinical use,
- use by anyone who would be placed at risk by a missed or false warning.

## 2. Safety concept

The software safety concept is:

1. **A failed sensor is never a clear path.** Timeouts, out-of-range readings and
   disconnected sensors produce at least caution, then a distinct fault.
2. **A fault is distinct from danger.** Fault uses a different haptic/tone/LED
   pattern so the user does not confuse "sensor broken" with "obstacle very
   close".
3. **Recovery is conservative.** Three valid readings are required, and the
   system stays at least at caution while degraded or recovering.
4. **Warnings are graded.** Caution and danger use different intensities and
   rhythms, not just on/off.
5. **Hardware defaults to off.** R2 pulls Q1's base low; the motor is off during
   reset or if D6 floats.
6. **Inductive energy is clamped.** D1 provides a flyback path for the motor.
7. **Current is limited.** R1, R3 and R4 limit base, LED and buzzer current.

These are risk-reduction measures, not a safety certification.

## 3. Hazard analysis

Qualitative severity/likelihood are for the experimental prototype. They are not
a formal ISO 14971 or ISO 26262 analysis.

| ID | Hazard / hazardous situation | Severity | Likelihood | Controls | Residual risk |
|---|---|---|---|---|---|
| H-01 | Angled, narrow or soft obstacle is not detected | High | High | Ultrasonic warning is supplementary; cane remains primary; documentation warns | **High** — cannot be eliminated by this sensor |
| H-02 | Transparent or sound-absorbing obstacle is missed | High | High | Same as H-01; no claim of reliable detection | **High** |
| H-03 | Overhead object is missed | Medium | High | Sensor is forward-facing; documentation says overhead objects are out of scope | **High** |
| H-04 | Stairs, drop-off or platform edge is missed | Critical | High | Explicitly out of scope; user must use a cane/guide; no deployment as a sole aid | **Critical** |
| H-05 | Sensor fails and system reports clear | Critical | Low (policy) / unknown (hardware) | Fault counters, minimum caution, `free=0` on any invalid reading, distinct fault pattern; tests | **Medium** — software tested, hardware unverified |
| H-06 | Stuck ECHO or wiring fault produces plausible but wrong distances | High | Medium | Timeout and range checks catch some faults; no cross-check or redundant sensor | **High** |
| H-07 | False alarm causes startle or desensitisation | Medium | Medium | Hysteresis, median filter, graded patterns; user can switch to Quiet | **Medium** |
| H-08 | Vibration is masked by clothing, grip or motor mounting | High | High | Not tested; documentation warns; no claim of perceptibility | **High** |
| H-09 | Buzzer is inaudible in noise or masks important environmental sound | High | Medium | Quiet mode; visual LED; not tested | **High** |
| H-10 | USB cable causes trip/entanglement or disconnects | Medium | Medium | Tethered prototype only; cable management required; production should use a secured, strain-relieved supply | **Medium** |
| H-11 | Power loss during use | High | Low | Device stops warning; no backup; user must retain cane skills | **High** |
| H-12 | Motor stall or overcurrent heats Q1/PCB | Medium | Low | PN2222A 500 mA class, 0.8 mm tracks, flyback diode; no fuse or current limit; 270 Ω drive is sized for 100 mA, not stall | **Medium** |
| H-13 | Buzzer too loud / uncomfortable | Low | Medium | 100 Ω series resistor; patterns are short; volume not characterised | **Low** |
| H-14 | Button is pressed accidentally and mode changes | Low | Medium | 30 ms debounce, 100 nF RC, 5 ms polling; no lock | **Low** |
| H-15 | User over-relies on the device and reduces cane use | Critical | Medium | Explicit warnings in README/docs; supplementary-aid framing; no user deployment | **High** |
| H-16 | EMC/ESD causes a reset or false output | High | Unknown | No EMC/ESD testing or protection; prototype only | **High** |
| H-17 | PCB or assembly failure (solder, connector, trace) | High | Unknown | DRC clean; not fabricated or assembled | **High** |
| H-18 | Incorrect firmware/pin map after modification | High | Medium | Cross-artifact validator; tests; documented pin map | **Low** for the checked configuration |

## 4. Failure modes and effects

| Failure | Detection | Response | Gap |
|---|---|---|---|
| HC-SR04 disconnected | No echo → `Timeout` | Degraded → caution → fault after 3 | A stuck-high ECHO may look like a long distance; range check catches some cases |
| ECHO stuck low | `pulseIn` returns 0 | Timeout/fault | None in software; hardware fault not diagnosed specifically |
| ECHO stuck high | `pulseIn` may return timeout or a long pulse | Timeout/out-of-range → fault | Not explicitly distinguished from a real long distance |
| Sensor gives random short readings | Median filter + fault counter | Filtered or fault | A repeated plausible error is not detectable |
| Q1 fails short | Motor runs continuously | No software detection | Hardware hazard; no current sensing |
| Q1 fails open | No vibration | User may not notice; LED/audio may still work | No actuator feedback |
| Motor disconnected | No vibration | No detection | No current sensing |
| Buzzer disconnected | No audio | LED/haptic remain | No audio feedback |
| USB unplugged | Firmware stops | No output | No backup |
| Button stuck | One stable press at most | No repeated cycling | Cannot change mode until released |
| MCU reset | Outputs initialise off | Restart in STARTING/caution | Brief loss of warning |

The design has **no actuator feedback**. It cannot prove that the motor is
actually vibrating, only that the PWM command was issued. This is a fundamental
limitation of the prototype.

## 5. Use constraints

If this design were ever developed further, the following would be mandatory:

- Use a conventional cane as the primary mobility aid.
- Do not use near roads, platforms, stairs, escalators, drop-offs or water.
- Do not use as the sole means of detecting obstacles.
- Inspect the sensor, connectors, cable and motor before each use.
- Stop using the device if the fault pattern appears.
- Use a regulated, current-limited 5 V source with a secured cable.
- Do not charge, modify or wear the prototype without an enclosure and strain
  relief.
- Conduct supervised user training and independent safety review before any
  real-world trial.

## 6. Verification status

| Safety claim | Verification | Status |
|---|---|---|
| Fault never reports free | Host tests + code inspection | **PASS (software)** |
| Fault requires 3 invalid readings | Host test | **PASS** |
| Recovery requires 3 valid readings | Host test | **PASS** |
| Hysteresis prevents chatter | Host tests | **PASS** |
| Motor base is pulled low | Schematic + calculation | **PASS (design)** |
| Flyback diode clamps inductive kick | ngspice | **PASS (model)** |
| LED/base/buzzer currents are limited | Calculations | **PASS (paper)** |
| Real sensor detects angled/soft/transparent obstacles | None | **NOT VERIFIED** |
| Real motor is perceptible | None | **NOT VERIFIED** |
| Real buzzer is audible | None | **NOT VERIFIED** |
| PCB is manufacturable and safe | DRC only | **NOT VERIFIED** |
| EMC/ESD/thermal safety | None | **NOT VERIFIED** |
| User can safely use the device | None | **NOT VERIFIED** |

## 7. Conclusion

The software makes a serious attempt to fail safe: it never converts a sensor
failure into an obstacle-free assertion, it uses hysteresis and filtering, and it
presents faults distinctly. The hardware includes the expected protection for a
small inductive load.

However, the largest risks are **not** software bugs. They are the physical and
human factors that simulation cannot cover: missed angled/soft/overhead
obstacles, stairs and drop-offs, tactile/audio perceptibility, power loss,
attachment, and over-reliance. Those risks remain high and are the reason the
project is explicitly a virtual, experimental reconstruction rather than a
validated assistive device.
