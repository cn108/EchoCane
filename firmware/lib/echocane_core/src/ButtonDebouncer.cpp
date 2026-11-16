#include "echocane/ButtonDebouncer.h"

namespace echocane {

ButtonDebouncer::ButtonDebouncer(uint16_t debounceMs)
    : debounceMs_(debounceMs),
      stablePressed_(false),
      lastRawPressed_(false),
      initialized_(false),
      lastChangeMs_(0) {}

void ButtonDebouncer::reset() {
  stablePressed_ = false;
  lastRawPressed_ = false;
  initialized_ = false;
  lastChangeMs_ = 0;
}

bool ButtonDebouncer::update(bool rawPressed, uint32_t nowMs) {
  if (!initialized_) {
    initialized_ = true;
    lastRawPressed_ = rawPressed;
    stablePressed_ = rawPressed;
    lastChangeMs_ = nowMs;
    return false;
  }

  if (rawPressed != lastRawPressed_) {
    // The input changed; restart the stability window without acting on it.
    lastRawPressed_ = rawPressed;
    lastChangeMs_ = nowMs;
    return false;
  }

  if (stablePressed_ == rawPressed) {
    return false;
  }

  if ((nowMs - lastChangeMs_) < debounceMs_) {
    return false;
  }

  stablePressed_ = rawPressed;
  return stablePressed_;
}

}  // namespace echocane
