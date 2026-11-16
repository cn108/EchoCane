#include "SensorManager.h"

#include <Arduino.h>

#include "echocane/SensorMath.h"

namespace echocane {

SensorManager::SensorManager(uint8_t trigPin, uint8_t echoPin,
                             const AppConfig& config)
    : trigPin_(trigPin),
      echoPin_(echoPin),
      timeoutUs_(config.echoTimeoutUs),
      minValidCm_(config.minValidCm),
      maxValidCm_(config.maxValidCm) {}

void SensorManager::begin() {
  pinMode(trigPin_, OUTPUT);
  digitalWrite(trigPin_, LOW);
  pinMode(echoPin_, INPUT);
}

DistanceReading SensorManager::read() {
  // Datasheet/Wokwi sequence: keep TRIG low briefly, then a >=10 us high pulse.
  digitalWrite(trigPin_, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin_, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin_, LOW);

  const unsigned long durationUs = pulseIn(echoPin_, HIGH, timeoutUs_);
  if (durationUs == 0UL) {
    return DistanceReading::timeout();
  }

  // Speed of sound at ~20 C: 343 m/s. Round trip -> microseconds / 58 = cm.
  const uint32_t centimeters = centimetersFromEchoPulse(durationUs);

  if (centimeters < minValidCm_ || centimeters > maxValidCm_) {
    const uint16_t reported =
        centimeters > 65535UL ? 65535U : static_cast<uint16_t>(centimeters);
    return DistanceReading::outOfRange(reported);
  }

  return DistanceReading::valid(static_cast<uint16_t>(centimeters));
}

}  // namespace echocane
