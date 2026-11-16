#include "SerialReporter.h"

#include <Arduino.h>

#include "Pins.h"
#include "echocane/Telemetry.h"

namespace echocane {

SerialReporter::SerialReporter() : buffer_() {}

void SerialReporter::begin(uint32_t baud) { Serial.begin(baud); }

void SerialReporter::banner(const AppConfig& config) {
  Serial.println(F("EchoCane ready"));
  Serial.println(F("EchoCane virtual reconstruction | firmware 0.1.0"));
  Serial.print(F("Pins: TRIG=D"));
  Serial.print(echo_cane_pins::kUltrasonicTrig);
  Serial.print(F(" ECHO=D"));
  Serial.print(echo_cane_pins::kUltrasonicEcho);
  Serial.print(F(" HAPTIC=D"));
  Serial.print(echo_cane_pins::kHapticPwm);
  Serial.print(F(" BUZZER=D"));
  Serial.print(echo_cane_pins::kBuzzer);
  Serial.print(F(" BUTTON=D"));
  Serial.print(echo_cane_pins::kModeButton);
  Serial.print(F(" LED=D"));
  Serial.println(echo_cane_pins::kStatusLed);

  Serial.print(F("Thresholds (cm): caution="));
  Serial.print(config.cautionThresholdCm);
  Serial.print(F(" danger="));
  Serial.print(config.dangerThresholdCm);
  Serial.print(F(" hysteresis="));
  Serial.println(config.hysteresisCm);
  Serial.println(F("Note: demonstration thresholds, not validated safety limits."));
  Serial.println(F("Telemetry: EC|t=..|raw=..|d=..|f=..|level=..|health=..|mode=..|free=.."));
}

void SerialReporter::report(const AlertUpdate& update, uint32_t uptimeMs) {
  formatTelemetry(buffer_, sizeof(buffer_), uptimeMs, update);
  Serial.println(buffer_);
}

void SerialReporter::event(const char* reason, const AlertUpdate& update,
                           uint32_t uptimeMs) {
  Serial.print(F("EC_EVENT|t="));
  Serial.print(uptimeMs);
  Serial.print(F("|reason="));
  Serial.print(reason);
  Serial.print(F("|level="));
  Serial.print(toString(update.level));
  Serial.print(F("|health="));
  Serial.print(toString(update.health));
  Serial.print(F("|mode="));
  Serial.println(toString(update.mode));
  report(update, uptimeMs);
}

}  // namespace echocane
