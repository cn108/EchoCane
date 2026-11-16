#pragma once

#include <stdint.h>

#include "echocane/AppConfig.h"
#include "echocane/PulseTimer.h"

namespace echocane {

/// Non-blocking buzzer controller built on Arduino tone()/noTone().
class AudioController {
 public:
  explicit AudioController(uint8_t pin);

  void begin();
  void apply(const TonePattern& pattern, bool enabled, uint32_t nowMs);
  void update(uint32_t nowMs);
  void stop();

  uint8_t pin() const { return pin_; }

 private:
  uint8_t pin_;
  PulseTimer timer_;
  uint16_t frequencyHz_;
  uint16_t toneMs_;
  bool enabled_;
  bool playing_;
};

}  // namespace echocane
