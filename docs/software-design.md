# Software design

## 1. Structure

```text
firmware/
├── include/                 Arduino-facing interfaces and pin map
│   ├── Pins.h
│   ├── SensorManager.h
│   ├── HapticController.h
│   ├── AudioController.h
│   ├── LedIndicator.h
│   └── SerialReporter.h
├── src/                     Arduino adapters and composition root
│   ├── SensorManager.cpp
│   ├── HapticController.cpp
│   ├── AudioController.cpp
│   ├── LedIndicator.cpp
│   ├── SerialReporter.cpp
│   └── main.cpp
├── lib/echocane_core/       Portable policy library (no Arduino.h)
│   ├── include/echocane/...
│   └── src/...
└── test/test_core/          Unity host tests
```

| Module | Responsibility | Hardware dependency |
|---|---|---|
| `AppConfig` | Demonstration thresholds, timings and output patterns | None |
| `Types` | Reading status, health, alert level, mode, conversions | None |
| `MedianFilter` | Five-sample median filter | None |
| `ObstacleDetector` | Classification and hysteresis over the filtered distance | None |
| `SafetyMonitor` | Invalid-reading counting, fault confirmation, recovery | None |
| `AlertPolicy` | Pure mapping from level/mode/config to output patterns | None |
| `PulseTimer` | On/off phase scheduling for patterns | None |
| `EchoCaneController` | Composition of health, distance, mode and patterns | None |
| `Telemetry` | Bounded `EC|...` formatting | None |
| `ButtonDebouncer` | Stable-state button edge detection | None |
| `SensorManager` | HC-SR04 trigger/echo acquisition | `pulseIn`, GPIO |
| `HapticController` | PWM output for the motor driver | `analogWrite` |
| `AudioController` | Tone scheduling | `tone`, `noTone` |
| `LedIndicator` | LED pattern output | `digitalWrite` |
| `SerialReporter` | Banner, telemetry, event records | `Serial` |

## 2. Control flow

`main.cpp` constructs the objects once and runs a cooperative loop:

```text
setup():
  Serial.begin(115200)
  button pin = INPUT_PULLUP
  sensor.begin(); haptic.begin(); audio.begin(); led.begin()
  controller.begin() → STARTING snapshot
  print banner and initial telemetry

loop():
  now = millis()
  every 5 ms:  poll button → cycle mode on a stable press
  every 60 ms: read sensor → controller.update() → apply outputs
  every pass:  haptic.update(), audio.update(), led.update()
  every 500 ms (250 ms in Diagnostic): print telemetry
```

A level or health change triggers an `EC_EVENT` line immediately, in addition to
the periodic telemetry. A mode change always emits an event.

### 2.1 Why this shape?

- The sensor is the slowest task; 60 ms gives about 16 updates per second, enough
  for a walking aid demonstration while leaving CPU time for outputs.
- Button polling at 5 ms is fast enough for a human press and cheap.
- Output schedulers run every pass so PWM/tone transitions are not quantised to
  the sensor period.
- The loop never calls `delay()`. The only blocking operation is `pulseIn`, with
  a 25 ms timeout.

## 3. Distance filtering

`MedianFilter` stores five samples in a fixed ring buffer. On each valid reading
it inserts the sample and computes the median with an insertion sort over a
five-element copy.

Why median rather than mean:

- A single spurious short or long echo is rejected.
- The median preserves step changes better than a long moving average.
- Five samples is small enough for the ATmega328P and adds only five scan periods
  of latency (300 ms at 60 ms scans).

The filter is reset on a confirmed fault and on `begin()`. Invalid readings are
not inserted; a failed acquisition holds the last level instead of injecting a
fake distance.

## 4. Classification and hysteresis

`ObstacleDetector::classify` implements the state-dependent rules below.

| Current level | Condition | Next level |
|---|---|---|
| Clear / Starting | `cm < 80` | Danger |
| Clear / Starting | `cm <= 150` | Caution |
| Clear / Starting | otherwise | Clear |
| Caution | `cm < 80` | Danger |
| Caution | `cm > 160` | Clear |
| Caution | otherwise | Caution |
| Danger | `cm > 160` | Clear |
| Danger | `cm > 90` | Caution |
| Danger | otherwise | Danger |
| Fault | any distance | Danger internally; controller presents Fault |

The controller never lets a distance sample clear a confirmed fault. The fault
path resets the detector and presents `FAULT` until the safety monitor recovers.

## 5. Fault and recovery policy

`SafetyMonitor` counts consecutive invalid and valid readings:

```text
on valid:
  failures = 0
  if health == Starting: health = Ok
  if health in {Degraded, Fault}:
      successes++
      if successes >= 3: health = Ok
  else successes = 1

on invalid:
  successes = 0
  failures++
  if failures >= 3: health = Fault
  else if health in {Ok, Starting}: health = Degraded
```

`EchoCaneController` then applies the presentation rule:

- `Fault` → level `Fault`, reset filter, no distance.
- Valid while not `Ok` → at least `Caution`.
- Invalid while not `Fault` → hold the last level, with a minimum of `Caution`.
- `obstacleFree` is true only for `Ok` + `Clear` + valid + has distance.

This is intentionally conservative. A single missed echo produces a caution
indication, not a clear one; a confirmed fault produces a distinct pattern and
never a false "free" assertion.

## 6. Modes and output policy

| Mode | Haptic | Audio | Telemetry |
|---|---|---|---|
| Assist | Yes | Yes | 500 ms |
| Quiet | Yes | No | 500 ms |
| Diagnostic | Yes | Yes | 250 ms |

`AlertPolicy::makeAlertCommand` maps level to patterns:

| Level | Haptic | Tone | LED |
|---|---|---|---|
| Starting | off | off | 120 ms on / 120 ms off |
| Clear | off | off | 40 ms on / 1960 ms off (heartbeat) |
| Caution | 40 %, 180/320 ms | 1800 Hz, 60/1140 ms | 120/120 ms |
| Danger | 100 %, 400/120 ms | 2400 Hz, 90/210 ms | solid |
| Fault | 100 %, 120/80 ms | 1000 Hz, 120/120 ms | 60/60 ms |

Quiet mode suppresses the buzzer but leaves the LED and haptic active. The fault
pattern is deliberately different from danger so a sensor failure is not mistaken
for a very close obstacle.

`PulseTimer` stores the on/off durations and the last transition time. It uses
unsigned elapsed-time comparisons, so it is rollover-safe. Reconfiguring with the
same pattern is a no-op, which avoids resetting the phase on every scan.

## 7. Button handling

`ButtonDebouncer`:

1. Initialises to the first raw state without emitting a press.
2. Restarts a stability timer on any raw change.
3. Emits `true` only when the raw state has been stable for `debounceMs` and the
   stable state changes.

`main.cpp` treats a `true` return as one short press and cycles
Assist → Quiet → Diagnostic → Assist. There is no long-press or double-click
behaviour in this version.

## 8. Serial protocol

Banner:

```text
EchoCane ready
EchoCane virtual reconstruction | firmware 0.1.0
Pins: TRIG=D9 ECHO=D10 HAPTIC=D6 BUZZER=D8 BUTTON=D2 LED=D7
Thresholds (cm): caution=150 danger=80 hysteresis=10
Note: demonstration thresholds, not validated safety limits.
Telemetry: EC|t=..|raw=..|d=..|f=..|level=..|health=..|mode=..|free=..
```

Periodic record:

```text
EC|t=1234|raw=Valid|d=120|f=120|level=CAUTION|health=OK|mode=ASSIST|free=0
```

Event record:

```text
EC_EVENT|t=1234|reason=state|level=DANGER|health=OK|mode=ASSIST
```

`raw` is `Valid`, `Timeout` or `OutOfRange`. `d` is the latest raw distance or
`none`; `f` is the filtered distance or `none`. `free=1` is only emitted for an
explicit clear assertion.

`formatTelemetry` uses `snprintf` into a fixed buffer and truncates safely if the
capacity is too small. It never allocates.

## 9. Timing and rollover

All intervals use:

```cpp
if ((now - last) >= interval) { ... }
```

with `uint32_t` values. This is correct across the 49.7-day `millis()` rollover
and avoids signed overflow.

| Constant | Value |
|---|---|
| Button poll | 5 ms |
| Scan interval | 60 ms |
| Echo timeout | 25,000 µs |
| Telemetry | 500 ms / 250 ms diagnostic |
| Debounce | 30 ms |
| Fault confirmation | 3 invalid readings |
| Recovery | 3 valid readings |

## 10. Memory and performance

- No heap allocation, STL containers, exceptions or RTTI.
- Fixed-size arrays: five-sample filter, fixed telemetry buffer, no dynamic
  strings.
- `F()` macro keeps constant banner strings in flash on AVR.
- `snprintf` is used only for telemetry, not in the control path.
- Final build: 10,766 bytes flash (35.0 %), 779 bytes RAM (38.0 %).

The largest stack use is the telemetry formatting path. The median sort copies
five `uint16_t` values. Both are small relative to the 2 KB SRAM.

## 11. Error handling

| Failure | Handling |
|---|---|
| No echo / timeout | `Timeout` reading; degraded then fault after 3 |
| Echo out of range | `OutOfRange`; same health path |
| Sensor disconnected | Usually timeout or no echo; never clear |
| Button stuck | Debouncer emits at most one transition; no repeated cycling |
| Invalid mode value | `switch` defaults to Assist |
| Telemetry buffer too small | Truncates and returns a bounded length |
| `millis()` rollover | Unsigned subtraction |
| MCU reset | Outputs initialise off; controller starts in STARTING |

## 12. Testability

`echocane_core` has no Arduino dependency. The native test target compiles the
same policy sources and injects:

- synthetic `DistanceReading` sequences,
- custom `AppConfig` thresholds and timings,
- fake timestamps for debounce/pulse tests.

The 18 tests cover classification boundaries, hysteresis release, filtering,
timeout/fault/recovery, button debounce, mode cycling, pattern selection, timers
and telemetry. See [testing-strategy.md](testing-strategy.md).

## 13. Coding conventions

- C++17, `namespace echocane`, fixed-width integer types.
- `const`/`constexpr` for configuration and pure helpers.
- No dynamic allocation; fixed buffers.
- Header guards via `#pragma once`.
- Units in names (`Ms`, `Us`, `Cm`, `Hz`) and comments where ambiguity is possible.
- Arduino-facing code isolated in `firmware/src` and `firmware/include`.
- Generated hardware files are reproducible from scripts; no manual edits to the
  generated `.kicad_sch`/`.kicad_pcb` are expected.

## 14. Known software limitations

- `pulseIn` blocks for up to 25 ms. This is bounded but not fully non-blocking.
  A future version should use Timer1 input capture and an interrupt-driven
  acquisition state machine.
- The five-sample median adds latency and is not a formally characterised filter.
- The mode button has no long-press configuration or persistence across reset.
- Telemetry is text-only; there is no binary protocol or error-detecting checksum.
- There is no watchdog reset in this version.
- The `modeAnnounceMs` configuration field is reserved and not used by the current
  output scheduler.
