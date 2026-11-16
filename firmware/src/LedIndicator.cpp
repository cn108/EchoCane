#include "LedIndicator.h"

#include <Arduino.h>

namespace echocane {

LedIndicator::LedIndicator(uint8_t pin) : pin_(pin), timer_(), solid_(false) {}

void LedIndicator::begin() {
  pinMode(pin_, OUTPUT);
  digitalWrite(pin_, LOW);
  timer_.reset(millis());
}

void LedIndicator::apply(const LedPattern& pattern, uint32_t nowMs) {
  solid_ = pattern.solid;
  timer_.configure(pattern.onMs, pattern.offMs, pattern.solid, nowMs);
}

void LedIndicator::update(uint32_t nowMs) {
  digitalWrite(pin_, solid_ || timer_.output(nowMs) ? HIGH : LOW);
}

}  // namespace echocane
