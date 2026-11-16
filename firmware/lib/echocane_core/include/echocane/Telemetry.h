#pragma once

#include <stddef.h>
#include <stdint.h>

#include "echocane/EchoCaneController.h"

namespace echocane {

/// Write one machine-readable telemetry record into `out`.
///
/// Format:
/// EC|t=<ms>|raw=<OK|TIMEOUT|OUT_OF_RANGE>|d=<cm|none>|f=<cm|none>|
/// level=<...>|health=<...>|mode=<...>|free=<0|1>
///
/// Returns the number of characters written, excluding the terminator.
size_t formatTelemetry(char* out, size_t capacity, uint32_t uptimeMs,
                       const AlertUpdate& update);

}  // namespace echocane
