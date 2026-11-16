#pragma once

#include <stdint.h>

namespace echocane {

/// Result of a single HC-SR04 acquisition attempt.
enum class ReadingStatus : uint8_t {
  Valid = 0,
  Timeout,     ///< No echo pulse arrived before the configured timeout.
  OutOfRange,  ///< An echo arrived but mapped outside the documented range.
};

struct DistanceReading {
  ReadingStatus status;
  uint16_t centimeters;

  static DistanceReading valid(uint16_t cm) {
    DistanceReading r = {ReadingStatus::Valid, cm};
    return r;
  }

  static DistanceReading timeout() {
    DistanceReading r = {ReadingStatus::Timeout, 0};
    return r;
  }

  static DistanceReading outOfRange(uint16_t cm) {
    DistanceReading r = {ReadingStatus::OutOfRange, cm};
    return r;
  }
};

/// Health of the sensing channel, with hysteresis around failures and recovery.
enum class SensorHealth : uint8_t {
  Starting = 0,  ///< No usable measurement yet since boot or reset.
  Ok,
  Degraded,  ///< A recent acquisition failed, but fault confirmation is pending.
  Fault,     ///< Consecutive failures exceeded the configured limit.
};

/// Warning state presented to the user.
enum class AlertLevel : uint8_t {
  Starting = 0,
  Clear,
  Caution,
  Danger,
  Fault,
};

/// User-selectable operating mode.
enum class SystemMode : uint8_t {
  Assist = 0,  ///< Haptic and audible warnings.
  Quiet,       ///< Haptic warnings only; buzzer muted.
  Diagnostic,  ///< Full warnings plus verbose periodic telemetry.
};

const char* toString(ReadingStatus status);
const char* toString(SensorHealth health);
const char* toString(AlertLevel level);
const char* toString(SystemMode mode);

/// Convert an alert level to a comparable ordinal (Fault is most severe).
uint8_t alertSeverity(AlertLevel level);

}  // namespace echocane
