#pragma once

#include <stdint.h>

#include "echocane/AppConfig.h"
#include "echocane/Types.h"

namespace echocane {

/// Arduino-facing HC-SR04 driver.
///
/// The echo capture is intrinsically blocking, but it is bounded by the
/// configured timeout (25 ms by default) and is called from a non-blocking
/// scan scheduler. All interpretation happens in the portable core.
class SensorManager {
 public:
  SensorManager(uint8_t trigPin, uint8_t echoPin, const AppConfig& config);

  void begin();
  DistanceReading read();

  uint8_t trigPin() const { return trigPin_; }
  uint8_t echoPin() const { return echoPin_; }

 private:
  uint8_t trigPin_;
  uint8_t echoPin_;
  uint32_t timeoutUs_;
  uint16_t minValidCm_;
  uint16_t maxValidCm_;
};

}  // namespace echocane
