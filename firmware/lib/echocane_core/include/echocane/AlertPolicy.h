#pragma once

#include "echocane/AppConfig.h"
#include "echocane/Types.h"

namespace echocane {

/// Map a warning level and user mode to actuator commands.
///
/// Quiet mode mutes only the buzzer; the tactile channel remains active so the
/// device never relies on audio alone.
AlertCommand makeAlertCommand(AlertLevel level, SystemMode mode,
                              const AppConfig& config);

}  // namespace echocane
