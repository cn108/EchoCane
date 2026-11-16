#pragma once

#include "echocane/AlertPolicy.h"
#include "echocane/AppConfig.h"
#include "echocane/ObstacleDetector.h"
#include "echocane/SafetyMonitor.h"
#include "echocane/Types.h"

namespace echocane {

/// Snapshot of the application decision, consumed by the hardware adapters.
struct AlertUpdate {
  AlertLevel level;
  SensorHealth health;
  SystemMode mode;
  ReadingStatus rawStatus;
  uint16_t rawCm;
  bool hasDistance;
  uint16_t filteredCm;
  bool obstacleFree;
  AlertCommand command;
};

/// Owns the safety policy that combines sensor health, filtering, hysteresis
/// and user mode. This class performs no I/O and is fully host-testable.
class EchoCaneController {
 public:
  explicit EchoCaneController(const AppConfig& config);

  AlertUpdate begin();
  AlertUpdate update(const DistanceReading& reading);

  /// Advance to the next operating mode; returns the new mode.
  SystemMode cycleMode();

  const AppConfig& config() const { return config_; }
  SystemMode mode() const { return mode_; }
  SensorHealth health() const { return safety_.health(); }
  AlertLevel level() const { return last_.level; }

 private:
  AlertUpdate compose(AlertLevel level, bool hasDistance, uint16_t filteredCm,
                      ReadingStatus rawStatus, uint16_t rawCm) const;

  const AppConfig& config_;
  SafetyMonitor safety_;
  ObstacleDetector detector_;
  SystemMode mode_;
  AlertUpdate last_;
};

}  // namespace echocane
