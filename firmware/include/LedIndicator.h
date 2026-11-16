#pragma once

#include <stdint.h>

#include "echocane/AppConfig.h"
#include "echocane/PulseTimer.h"

namespace echocane {

/// Status LED: slow heartbeat when clear, rapid when caution/fault, solid when
/// an obstacle is in the danger band.
class LedIndicator {
 public:
  explicit LedIndicator(uint8_t pin);

  void begin();
  void apply(const LedPattern& pattern, uint32_t nowMs);
  void update(uint32_t nowMs);

 private:
  uint8_t pin_;
  PulseTimer timer_;
  bool solid_;
};

}  // namespace echocane
