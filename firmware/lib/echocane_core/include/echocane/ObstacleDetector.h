#pragma once

#include "echocane/AppConfig.h"
#include "echocane/MedianFilter.h"
#include "echocane/Types.h"

namespace echocane {

/// Converts valid distance samples into a debounced warning level.
///
/// The detector owns the noise filter and the hysteresis state. It deliberately
/// knows nothing about Arduino pins, time sources or actuators.
class ObstacleDetector {
 public:
  explicit ObstacleDetector(const AppConfig& config);

  /// Discard history and return to the clear state.
  void reset();

  /// Add one valid distance sample and return the resulting warning level.
  AlertLevel update(uint16_t centimeters);

  AlertLevel level() const { return level_; }
  uint16_t filteredCm() const { return filter_.median(); }
  bool hasFilteredSample() const { return filter_.hasSample(); }
  uint8_t sampleCount() const { return filter_.count(); }

 private:
  AlertLevel classify(uint16_t centimeters) const;

  const AppConfig& config_;
  MedianFilter filter_;
  AlertLevel level_;
};

}  // namespace echocane
