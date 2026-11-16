#pragma once

#include <stdint.h>

namespace echocane {

/// Debounces a momentary push button without blocking.
///
/// The caller supplies the raw pressed state (true means pressed) and a
/// millisecond timestamp. A press event is emitted once, after the input has
/// remained stable for the debounce interval.
class ButtonDebouncer {
 public:
  explicit ButtonDebouncer(uint16_t debounceMs);

  void reset();
  bool update(bool rawPressed, uint32_t nowMs);

  bool isPressed() const { return stablePressed_; }

 private:
  uint16_t debounceMs_;
  bool stablePressed_;
  bool lastRawPressed_;
  bool initialized_;
  uint32_t lastChangeMs_;
};

}  // namespace echocane
