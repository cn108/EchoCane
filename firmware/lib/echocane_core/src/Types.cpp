#include "echocane/Types.h"

namespace echocane {
namespace {

const char* const kReadingNames[] = {"OK", "TIMEOUT", "OUT_OF_RANGE"};
const char* const kHealthNames[] = {"STARTING", "OK", "DEGRADED", "FAULT"};
const char* const kAlertNames[] = {"STARTING", "CLEAR", "CAUTION", "DANGER", "FAULT"};
const char* const kModeNames[] = {"ASSIST", "QUIET", "DIAGNOSTIC"};

}  // namespace

const char* toString(ReadingStatus status) {
  const uint8_t index = static_cast<uint8_t>(status);
  return index < (sizeof(kReadingNames) / sizeof(kReadingNames[0]))
             ? kReadingNames[index]
             : "UNKNOWN";
}

const char* toString(SensorHealth health) {
  const uint8_t index = static_cast<uint8_t>(health);
  return index < (sizeof(kHealthNames) / sizeof(kHealthNames[0]))
             ? kHealthNames[index]
             : "UNKNOWN";
}

const char* toString(AlertLevel level) {
  const uint8_t index = static_cast<uint8_t>(level);
  return index < (sizeof(kAlertNames) / sizeof(kAlertNames[0]))
             ? kAlertNames[index]
             : "UNKNOWN";
}

const char* toString(SystemMode mode) {
  const uint8_t index = static_cast<uint8_t>(mode);
  return index < (sizeof(kModeNames) / sizeof(kModeNames[0]))
             ? kModeNames[index]
             : "UNKNOWN";
}

uint8_t alertSeverity(AlertLevel level) {
  switch (level) {
    case AlertLevel::Fault:
      return 4;
    case AlertLevel::Danger:
      return 3;
    case AlertLevel::Caution:
      return 2;
    case AlertLevel::Clear:
      return 1;
    case AlertLevel::Starting:
    default:
      return 0;
  }
}

}  // namespace echocane
