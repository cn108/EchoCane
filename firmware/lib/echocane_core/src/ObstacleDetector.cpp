#include "echocane/ObstacleDetector.h"

namespace echocane {

ObstacleDetector::ObstacleDetector(const AppConfig& config)
    : config_(config), filter_(), level_(AlertLevel::Clear) {}

void ObstacleDetector::reset() {
  filter_.reset();
  level_ = AlertLevel::Clear;
}

AlertLevel ObstacleDetector::update(uint16_t centimeters) {
  filter_.add(centimeters);
  level_ = classify(filter_.median());
  return level_;
}

AlertLevel ObstacleDetector::classify(uint16_t centimeters) const {
  const uint16_t caution = config_.cautionThresholdCm;
  const uint16_t danger = config_.dangerThresholdCm;
  const uint16_t release = config_.hysteresisCm;

  switch (level_) {
    case AlertLevel::Clear:
    case AlertLevel::Starting:
      // The brief defines 80-150 cm as caution and strictly below 80 cm as
      // danger, so the comparison at the danger threshold is exclusive.
      if (centimeters < danger) {
        return AlertLevel::Danger;
      }
      if (centimeters <= caution) {
        return AlertLevel::Caution;
      }
      return AlertLevel::Clear;

    case AlertLevel::Caution:
      if (centimeters < danger) {
        return AlertLevel::Danger;
      }
      if (centimeters > static_cast<uint16_t>(caution + release)) {
        return AlertLevel::Clear;
      }
      return AlertLevel::Caution;

    case AlertLevel::Danger:
      if (centimeters > static_cast<uint16_t>(danger + release)) {
        return centimeters > static_cast<uint16_t>(caution + release)
                   ? AlertLevel::Clear
                   : AlertLevel::Caution;
      }
      return AlertLevel::Danger;

    case AlertLevel::Fault:
    default:
      // The controller owns fault presentation; a distance sample alone cannot
      // clear a fault.
      return AlertLevel::Danger;
  }
}

}  // namespace echocane
