#pragma once

#include <stdint.h>

#include "echocane/AppConfig.h"
#include "echocane/EchoCaneController.h"

namespace echocane {

/// Human-readable boot banner plus machine-readable periodic telemetry.
class SerialReporter {
 public:
  SerialReporter();

  void begin(uint32_t baud);
  void banner(const AppConfig& config);
  void report(const AlertUpdate& update, uint32_t uptimeMs);
  void event(const char* reason, const AlertUpdate& update, uint32_t uptimeMs);

 private:
  char buffer_[128];
};

}  // namespace echocane
