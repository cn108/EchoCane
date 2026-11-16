#include "echocane/SafetyMonitor.h"

namespace echocane {

SafetyMonitor::SafetyMonitor(const AppConfig& config)
    : config_(config),
      health_(SensorHealth::Starting),
      failures_(0),
      successes_(0) {}

void SafetyMonitor::reset() {
  health_ = SensorHealth::Starting;
  failures_ = 0;
  successes_ = 0;
}

HealthUpdate SafetyMonitor::update(const DistanceReading& reading) {
  if (reading.status == ReadingStatus::Valid) {
    failures_ = 0;

    if (health_ == SensorHealth::Starting) {
      health_ = SensorHealth::Ok;
      successes_ = 1;
    } else if (health_ == SensorHealth::Degraded) {
      if (successes_ < 255) {
        ++successes_;
      }
      if (successes_ >= config_.recoverAfterConsecutiveValid) {
        health_ = SensorHealth::Ok;
      }
    } else if (health_ == SensorHealth::Fault) {
      if (successes_ < 255) {
        ++successes_;
      }
      if (successes_ >= config_.recoverAfterConsecutiveValid) {
        health_ = SensorHealth::Ok;
      }
    } else {
      successes_ = 1;
    }
  } else {
    successes_ = 0;
    if (failures_ < 255) {
      ++failures_;
    }

    if (failures_ >= config_.faultAfterConsecutiveInvalid) {
      health_ = SensorHealth::Fault;
    } else if (health_ == SensorHealth::Ok ||
               health_ == SensorHealth::Starting) {
      // A failed acquisition before the first success is already evidence that
      // the path cannot be assumed clear, so leave STARTING immediately.
      health_ = SensorHealth::Degraded;
    }
  }

  HealthUpdate result;
  result.health = health_;
  result.sampleAccepted =
      (reading.status == ReadingStatus::Valid) && (health_ != SensorHealth::Fault);
  return result;
}

}  // namespace echocane
