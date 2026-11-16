#pragma once

#include <stdint.h>

namespace echocane {

/// Pulse pattern for the vibration motor, expressed as a percentage of PWM duty.
struct HapticPattern {
  uint8_t intensityPercent;
  uint16_t onMs;
  uint16_t offMs;
};

/// Pulse pattern for the optional piezo buzzer.
struct TonePattern {
  uint16_t frequencyHz;
  uint16_t onMs;
  uint16_t offMs;
};

/// Blink pattern for the status LED.
struct LedPattern {
  uint16_t onMs;
  uint16_t offMs;
  bool solid;
};

/// Alert outputs selected for the current warning level and mode.
struct AlertCommand {
  HapticPattern haptic;
  TonePattern tone;
  LedPattern led;
  bool audioEnabled;
};

/// Demonstration parameters. These are engineering defaults, not validated
/// safety thresholds; the physical device would need user testing before use.
struct AppConfig {
  // Distance bands, in centimetres.
  uint16_t cautionThresholdCm = 150;
  uint16_t dangerThresholdCm = 80;
  // Asymmetric hysteresis: warnings engage at the thresholds above and only
  // release once the measured distance has improved by this margin.
  uint16_t hysteresisCm = 10;

  // Documented HC-SR04 measurement range (Wokwi and vendor datasheet).
  uint16_t minValidCm = 2;
  uint16_t maxValidCm = 400;

  // Sensor acquisition.
  uint32_t echoTimeoutUs = 25000;  // 400 cm round trip is ~23.2 ms.
  uint16_t scanIntervalMs = 60;

  // Fault confirmation and recovery.
  uint8_t faultAfterConsecutiveInvalid = 3;
  uint8_t recoverAfterConsecutiveValid = 3;

  // Human interface.
  uint8_t buttonDebounceMs = 30;
  uint16_t telemetryIntervalMs = 500;
  uint16_t modeAnnounceMs = 900;

  // Output patterns.
  HapticPattern cautionHaptic = {40, 180, 320};
  HapticPattern dangerHaptic = {100, 400, 120};
  HapticPattern faultHaptic = {100, 120, 80};

  TonePattern cautionTone = {1800, 60, 1140};
  TonePattern dangerTone = {2400, 90, 210};
  TonePattern faultTone = {1000, 120, 120};

  LedPattern startingLed = {120, 120, false};
  LedPattern clearLed = {40, 1960, false};
  LedPattern cautionLed = {120, 120, false};
  LedPattern dangerLed = {0, 0, true};
  LedPattern faultLed = {60, 60, false};
};

}  // namespace echocane
