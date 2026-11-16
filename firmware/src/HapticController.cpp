#include "HapticController.h"

#include <Arduino.h>

namespace echocane {

HapticController::HapticController(uint8_t pin)
    : pin_(pin), timer_(), intensityPercent_(0), active_(false) {}

void HapticController::begin() {
  pinMode(pin_, OUTPUT);
  analogWrite(pin_, 0);
  timer_.reset(millis());
}

void HapticController::apply(const HapticPattern& pattern, uint32_t nowMs) {
  intensityPercent_ = pattern.intensityPercent;
  active_ = pattern.intensityPercent > 0 && pattern.onMs > 0;
  timer_.configure(pattern.onMs, pattern.offMs, false, nowMs);
  if (!active_) {
    timer_.reset(nowMs);
  }
}

void HapticController::update(uint32_t nowMs) {
  uint8_t duty = 0;
  if (active_ && timer_.output(nowMs)) {
    duty = static_cast<uint8_t>(
        (static_cast<uint16_t>(intensityPercent_) * 255U) / 100U);
  }
  analogWrite(pin_, duty);
}

void HapticController::stop() {
  active_ = false;
  analogWrite(pin_, 0);
}

}  // namespace echocane
