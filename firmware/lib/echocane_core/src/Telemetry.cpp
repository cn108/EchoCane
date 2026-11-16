#include "echocane/Telemetry.h"

#include <stdio.h>

namespace echocane {

size_t formatTelemetry(char* out, size_t capacity, uint32_t uptimeMs,
                       const AlertUpdate& update) {
  if (out == nullptr || capacity == 0) {
    return 0;
  }

  char distance[8];
  char filtered[8];

  if (update.rawStatus == ReadingStatus::Valid) {
    snprintf(distance, sizeof(distance), "%u",
             static_cast<unsigned>(update.rawCm));
  } else {
    snprintf(distance, sizeof(distance), "none");
  }

  if (update.hasDistance) {
    snprintf(filtered, sizeof(filtered), "%u",
             static_cast<unsigned>(update.filteredCm));
  } else {
    snprintf(filtered, sizeof(filtered), "none");
  }

  const int written = snprintf(
      out, capacity,
      "EC|t=%lu|raw=%s|d=%s|f=%s|level=%s|health=%s|mode=%s|free=%u",
      static_cast<unsigned long>(uptimeMs), toString(update.rawStatus), distance,
      filtered, toString(update.level), toString(update.health),
      toString(update.mode), update.obstacleFree ? 1U : 0U);

  if (written < 0) {
    out[0] = '\0';
    return 0;
  }

  const size_t length = static_cast<size_t>(written);
  return length < capacity ? length : capacity - 1;
}

}  // namespace echocane
