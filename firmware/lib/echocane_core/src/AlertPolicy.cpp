#include "echocane/AlertPolicy.h"

namespace echocane {
namespace {

const HapticPattern kOffHaptic = {0, 0, 0};
const TonePattern kOffTone = {0, 0, 0};

}  // namespace

AlertCommand makeAlertCommand(AlertLevel level, SystemMode mode,
                              const AppConfig& config) {
  AlertCommand command;
  command.haptic = kOffHaptic;
  command.tone = kOffTone;
  command.led = config.startingLed;
  command.audioEnabled = false;

  switch (level) {
    case AlertLevel::Starting:
      command.led = config.startingLed;
      break;

    case AlertLevel::Clear:
      command.led = config.clearLed;
      break;

    case AlertLevel::Caution:
      command.haptic = config.cautionHaptic;
      command.tone = config.cautionTone;
      command.led = config.cautionLed;
      break;

    case AlertLevel::Danger:
      command.haptic = config.dangerHaptic;
      command.tone = config.dangerTone;
      command.led = config.dangerLed;
      break;

    case AlertLevel::Fault:
      command.haptic = config.faultHaptic;
      command.tone = config.faultTone;
      command.led = config.faultLed;
      break;
  }

  command.audioEnabled = (mode != SystemMode::Quiet) && (command.tone.onMs > 0);
  return command;
}

}  // namespace echocane
