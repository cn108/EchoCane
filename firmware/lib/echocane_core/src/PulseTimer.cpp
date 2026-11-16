#include "echocane/PulseTimer.h"

namespace echocane {

PulseTimer::PulseTimer()
    : onMs_(0), offMs_(0), solid_(false), phaseOn_(false), lastTransitionMs_(0) {}

void PulseTimer::reset(uint32_t nowMs) {
  onMs_ = 0;
  offMs_ = 0;
  solid_ = false;
  phaseOn_ = false;
  lastTransitionMs_ = nowMs;
}

void PulseTimer::configure(uint16_t onMs, uint16_t offMs, bool solid,
                           uint32_t nowMs) {
  if (onMs == onMs_ && offMs == offMs_ && solid == solid_) {
    return;
  }

  onMs_ = onMs;
  offMs_ = offMs;
  solid_ = solid;
  phaseOn_ = (onMs > 0);
  lastTransitionMs_ = nowMs;
}

bool PulseTimer::output(uint32_t nowMs) {
  if (solid_) {
    return true;
  }
  if (onMs_ == 0) {
    return false;
  }

  const uint32_t elapsed = nowMs - lastTransitionMs_;
  if (phaseOn_) {
    if (elapsed >= onMs_) {
      phaseOn_ = false;
      lastTransitionMs_ = nowMs;
    }
  } else {
    if (elapsed >= offMs_) {
      phaseOn_ = true;
      lastTransitionMs_ = nowMs;
    }
  }

  return phaseOn_;
}

}  // namespace echocane
