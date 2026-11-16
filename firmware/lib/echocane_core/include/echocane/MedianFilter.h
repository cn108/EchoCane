#pragma once

#include <stdint.h>

namespace echocane {

/// Fixed-size median filter used to reject short ultrasonic spikes.
///
/// No heap allocation is performed. The filter stores up to five samples and
/// reports the lower median for an even sample count, which keeps the result
/// deterministic without floating point arithmetic.
class MedianFilter {
 public:
  static const uint8_t kCapacity = 5;

  MedianFilter();

  void reset();
  void add(uint16_t sample);

  bool hasSample() const { return count_ > 0; }
  uint8_t count() const { return count_; }
  uint16_t median() const;

 private:
  uint16_t samples_[kCapacity];
  uint8_t count_;
  uint8_t next_;
};

}  // namespace echocane
