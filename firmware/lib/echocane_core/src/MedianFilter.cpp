#include "echocane/MedianFilter.h"

namespace echocane {

MedianFilter::MedianFilter() : samples_(), count_(0), next_(0) {}

void MedianFilter::reset() {
  count_ = 0;
  next_ = 0;
}

void MedianFilter::add(uint16_t sample) {
  samples_[next_] = sample;
  next_ = static_cast<uint8_t>((next_ + 1) % kCapacity);
  if (count_ < kCapacity) {
    ++count_;
  }
}

uint16_t MedianFilter::median() const {
  if (count_ == 0) {
    return 0;
  }

  // Copy the live window into a small local array and insertion-sort it.
  // Five elements is cheap enough for the 16 MHz ATmega328P.
  uint16_t sorted[kCapacity];
  for (uint8_t i = 0; i < count_; ++i) {
    sorted[i] = samples_[i];
  }

  for (uint8_t i = 1; i < count_; ++i) {
    const uint16_t value = sorted[i];
    int8_t j = static_cast<int8_t>(i) - 1;
    while (j >= 0 && sorted[j] > value) {
      sorted[j + 1] = sorted[j];
      --j;
    }
    sorted[j + 1] = value;
  }

  return sorted[(count_ - 1) / 2];
}

}  // namespace echocane
