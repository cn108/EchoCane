#pragma once

#include <stdint.h>

namespace echocane {

/// Non-blocking square-wave generator used for haptic, audio and LED outputs.
///
/// A configuration with onMs == 0 means "always off"; solid means "always on".
/// Reconfiguring with identical values preserves phase.
class PulseTimer {
 public:
  PulseTimer();

  void reset(uint32_t nowMs);
  void configure(uint16_t onMs, uint16_t offMs, bool solid, uint32_t nowMs);
  bool output(uint32_t nowMs);

  bool isSolid() const { return solid_; }

 private:
  uint16_t onMs_;
  uint16_t offMs_;
  bool solid_;
  bool phaseOn_;
  uint32_t lastTransitionMs_;
};

}  // namespace echocane
