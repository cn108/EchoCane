#pragma once

#include <stdint.h>

namespace echocane {

/// Convert an HC-SR04 echo pulse width to centimetres using the standard
/// speed-of-sound approximation (58 us/cm round trip), with nearest-centimetre
/// rounding. The caller is responsible for applying the sensor's valid range.
///
/// The input is normally bounded by the 25,000 us pulseIn timeout. The guard
/// keeps this helper defined for the full uint32_t input domain as well.
inline uint32_t centimetersFromEchoPulse(uint32_t durationUs) {
  constexpr uint32_t kRoundUs = 29U;
  constexpr uint32_t kDivisor = 58U;
  if (durationUs > (UINT32_MAX - kRoundUs)) {
    return UINT32_MAX / kDivisor;
  }
  return (durationUs + kRoundUs) / kDivisor;
}

}  // namespace echocane
