#pragma once

#include <stdint.h>

#include "echocane/AppConfig.h"
#include "echocane/PulseTimer.h"

namespace echocane {

/// Drives the motor-driver input as a PWM waveform.
///
/// The PWM signal represents the command that would be sent to the transistor
/// driver; it is not evidence of real tactile output.
class HapticController {
 public:
  explicit HapticController(uint8_t pin);

  void begin();
  void apply(const HapticPattern& pattern, uint32_t nowMs);
  void update(uint32_t nowMs);
  void stop();

  uint8_t pin() const { return pin_; }

 private:
  uint8_t pin_;
  PulseTimer timer_;
  uint8_t intensityPercent_;
  bool active_;
};

}  // namespace echocane
