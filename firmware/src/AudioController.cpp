#include "AudioController.h"

#include <Arduino.h>

namespace echocane {

AudioController::AudioController(uint8_t pin)
    : pin_(pin),
      timer_(),
      frequencyHz_(0),
      toneMs_(0),
      enabled_(false),
      playing_(false) {}

void AudioController::begin() {
  pinMode(pin_, OUTPUT);
  digitalWrite(pin_, LOW);
  timer_.reset(millis());
}

void AudioController::apply(const TonePattern& pattern, bool enabled,
                            uint32_t nowMs) {
  frequencyHz_ = pattern.frequencyHz;
  toneMs_ = pattern.onMs;
  enabled_ = enabled && pattern.frequencyHz > 0 && pattern.onMs > 0;
  timer_.configure(pattern.onMs, pattern.offMs, false, nowMs);
  if (!enabled_) {
    stop();
  }
}

void AudioController::update(uint32_t nowMs) {
  const bool want = enabled_ && timer_.output(nowMs);

  if (want && !playing_) {
    tone(pin_, frequencyHz_, toneMs_);
    playing_ = true;
  } else if (!want && playing_) {
    noTone(pin_);
    playing_ = false;
  }
}

void AudioController::stop() {
  if (playing_) {
    noTone(pin_);
    playing_ = false;
  }
}

}  // namespace echocane
