#include "echocane/EchoCaneController.h"

namespace echocane {
namespace {

AlertLevel higher(AlertLevel a, AlertLevel b) {
  return alertSeverity(a) >= alertSeverity(b) ? a : b;
}

}  // namespace

EchoCaneController::EchoCaneController(const AppConfig& config)
    : config_(config),
      safety_(config),
      detector_(config),
      mode_(SystemMode::Assist),
      last_() {
  last_.level = AlertLevel::Starting;
  last_.health = SensorHealth::Starting;
  last_.mode = mode_;
  last_.rawStatus = ReadingStatus::Timeout;
  last_.rawCm = 0;
  last_.hasDistance = false;
  last_.filteredCm = 0;
  last_.obstacleFree = false;
  last_.command = makeAlertCommand(last_.level, mode_, config_);
}

AlertUpdate EchoCaneController::begin() {
  safety_.reset();
  detector_.reset();
  mode_ = SystemMode::Assist;

  const DistanceReading none = DistanceReading::timeout();
  AlertUpdate update = compose(none, AlertLevel::Starting, false, 0,
                               ReadingStatus::Timeout, 0);
  last_ = update;
  return update;
}

AlertUpdate EchoCaneController::update(const DistanceReading& reading) {
  const HealthUpdate health = safety_.update(reading);

  AlertLevel level = AlertLevel::Starting;
  bool hasDistance = detector_.hasFilteredSample();
  uint16_t filteredCm = detector_.filteredCm();

  if (health.health == SensorHealth::Fault) {
    // A confirmed sensor fault must never look like a clear path.
    detector_.reset();
    level = AlertLevel::Fault;
    hasDistance = false;
    filteredCm = 0;
  } else if (reading.status == ReadingStatus::Valid) {
    level = detector_.update(reading.centimeters);
    hasDistance = true;
    filteredCm = detector_.filteredCm();

    // While the channel is recovering or newly degraded, retain at least a
    // caution indication even if the filtered distance is clear.
    if (health.health != SensorHealth::Ok) {
      level = higher(level, AlertLevel::Caution);
    }
  } else {
    // No usable echo. Hold the last classified warning, but never report an
    // obstacle-free path from a failed acquisition: the minimum is CAUTION.
    level = higher(detector_.hasFilteredSample() ? detector_.level()
                                                 : AlertLevel::Caution,
                   AlertLevel::Caution);
    if (health.health == SensorHealth::Starting) {
      level = AlertLevel::Starting;
    }
  }

  AlertUpdate update = compose(reading, level, hasDistance, filteredCm,
                               reading.status, reading.centimeters);
  last_ = update;
  return update;
}

SystemMode EchoCaneController::cycleMode() {
  switch (mode_) {
    case SystemMode::Assist:
      mode_ = SystemMode::Quiet;
      break;
    case SystemMode::Quiet:
      mode_ = SystemMode::Diagnostic;
      break;
    case SystemMode::Diagnostic:
    default:
      mode_ = SystemMode::Assist;
      break;
  }

  last_.mode = mode_;
  last_.command = makeAlertCommand(last_.level, mode_, config_);
  return mode_;
}

AlertUpdate EchoCaneController::compose(const DistanceReading& reading,
                                        AlertLevel level, bool hasDistance,
                                        uint16_t filteredCm,
                                        ReadingStatus rawStatus,
                                        uint16_t rawCm) const {
  AlertUpdate update;
  update.level = level;
  update.health = safety_.health();
  update.mode = mode_;
  update.rawStatus = rawStatus;
  update.rawCm = rawCm;
  update.hasDistance = hasDistance;
  update.filteredCm = filteredCm;
  update.obstacleFree = (update.health == SensorHealth::Ok) &&
                        (level == AlertLevel::Clear) &&
                        (rawStatus == ReadingStatus::Valid) && hasDistance;
  update.command = makeAlertCommand(level, mode_, config_);
  (void)reading;
  return update;
}

}  // namespace echocane
