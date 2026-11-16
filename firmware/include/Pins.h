#pragma once

#include <stdint.h>

namespace echo_cane_pins {

// Classic Arduino Nano (ATmega328P, 5 V). These assignments are shared by the
// firmware, Wokwi diagram and KiCad schematic; change all three together.
static const uint8_t kUltrasonicTrig = 9;   // D9  (PB1)
static const uint8_t kUltrasonicEcho = 10;  // D10 (PB2)
static const uint8_t kHapticPwm = 6;        // D6  (PD6, Timer0A PWM)
static const uint8_t kBuzzer = 8;           // D8  (PB0, tone() uses Timer2)
static const uint8_t kModeButton = 2;       // D2  (PD2, active low)
static const uint8_t kStatusLed = 7;        // D7  (PD7)

}  // namespace echo_cane_pins
