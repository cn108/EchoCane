#include <Arduino.h>

#include "AudioController.h"
#include "HapticController.h"
#include "LedIndicator.h"
#include "Pins.h"
#include "SensorManager.h"
#include "SerialReporter.h"
#include "echocane/AppConfig.h"
#include "echocane/ButtonDebouncer.h"
#include "echocane/EchoCaneController.h"

namespace {

const uint32_t kSerialBaud = 115200;
const uint16_t kButtonPollIntervalMs = 5;

echocane::AppConfig g_config;
echocane::SensorManager g_sensor(echo_cane_pins::kUltrasonicTrig,
                                 echo_cane_pins::kUltrasonicEcho, g_config);
echocane::HapticController g_haptic(echo_cane_pins::kHapticPwm);
echocane::AudioController g_audio(echo_cane_pins::kBuzzer);
echocane::LedIndicator g_led(echo_cane_pins::kStatusLed);
echocane::EchoCaneController g_controller(g_config);
echocane::ButtonDebouncer g_button(g_config.buttonDebounceMs);
echocane::SerialReporter g_reporter;

echocane::AlertUpdate g_update;
echocane::AlertLevel g_reportedLevel = echocane::AlertLevel::Starting;
echocane::SensorHealth g_reportedHealth = echocane::SensorHealth::Starting;
uint32_t g_lastScanMs = 0;
uint32_t g_lastButtonPollMs = 0;
uint32_t g_lastTelemetryMs = 0;

void applyOutputs(uint32_t nowMs) {
  g_haptic.apply(g_update.command.haptic, nowMs);
  g_audio.apply(g_update.command.tone, g_update.command.audioEnabled, nowMs);
  g_led.apply(g_update.command.led, nowMs);
}

void reportIfChanged(const char* reason, uint32_t nowMs) {
  if (g_update.level != g_reportedLevel || g_update.health != g_reportedHealth) {
    g_reportedLevel = g_update.level;
    g_reportedHealth = g_update.health;
    g_reporter.event(reason, g_update, nowMs);
  }
}

void pollButton(uint32_t nowMs) {
  const bool rawPressed = digitalRead(echo_cane_pins::kModeButton) == LOW;
  if (!g_button.update(rawPressed, nowMs)) {
    return;
  }

  const echocane::SystemMode mode = g_controller.cycleMode();
  g_update.mode = mode;
  g_update.command =
      echocane::makeAlertCommand(g_update.level, mode, g_config);
  applyOutputs(nowMs);
  g_reporter.event("mode", g_update, nowMs);
}

void scanSensor(uint32_t nowMs) {
  const echocane::DistanceReading reading = g_sensor.read();
  g_update = g_controller.update(reading);
  applyOutputs(nowMs);
  reportIfChanged("state", nowMs);
}

}  // namespace

void setup() {
  g_reporter.begin(kSerialBaud);
  pinMode(echo_cane_pins::kModeButton, INPUT_PULLUP);

  g_sensor.begin();
  g_haptic.begin();
  g_audio.begin();
  g_led.begin();

  g_update = g_controller.begin();
  g_reportedLevel = g_update.level;
  g_reportedHealth = g_update.health;
  applyOutputs(millis());

  g_reporter.banner(g_config);
  g_reporter.report(g_update, millis());

  const uint32_t now = millis();
  g_lastScanMs = now - g_config.scanIntervalMs;
  g_lastButtonPollMs = now;
  g_lastTelemetryMs = now;
}

void loop() {
  const uint32_t now = millis();

  if ((now - g_lastButtonPollMs) >= kButtonPollIntervalMs) {
    g_lastButtonPollMs = now;
    pollButton(now);
  }

  if ((now - g_lastScanMs) >= g_config.scanIntervalMs) {
    g_lastScanMs = now;
    scanSensor(now);
  }

  // Output schedulers run every pass; they are non-blocking.
  g_haptic.update(now);
  g_audio.update(now);
  g_led.update(now);

  const uint32_t telemetryInterval =
      (g_update.mode == echocane::SystemMode::Diagnostic)
          ? static_cast<uint32_t>(g_config.telemetryIntervalMs / 2U)
          : static_cast<uint32_t>(g_config.telemetryIntervalMs);

  if ((now - g_lastTelemetryMs) >= telemetryInterval) {
    g_lastTelemetryMs = now;
    g_reporter.report(g_update, now);
  }
}
