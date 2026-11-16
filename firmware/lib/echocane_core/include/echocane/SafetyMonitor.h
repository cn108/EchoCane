#pragma once

#include "echocane/AppConfig.h"
#include "echocane/Types.h"

namespace echocane {

struct HealthUpdate {
  SensorHealth health;
  bool sampleAccepted;
};

/// Tracks sensor availability with separate failure and recovery thresholds.
///
/// A single timeout degrades the channel but does not immediately declare a
/// fault; repeated failures do. After a confirmed fault, several consecutive
/// valid readings are required before the channel is trusted again.
class SafetyMonitor {
 public:
  explicit SafetyMonitor(const AppConfig& config);

  void reset();
  HealthUpdate update(const DistanceReading& reading);

  SensorHealth health() const { return health_; }
  bool isFault() const { return health_ == SensorHealth::Fault; }
  uint8_t consecutiveFailures() const { return failures_; }
  uint8_t consecutiveSuccesses() const { return successes_; }

 private:
  const AppConfig& config_;
  SensorHealth health_;
  uint8_t failures_;
  uint8_t successes_;
};

}  // namespace echocane
