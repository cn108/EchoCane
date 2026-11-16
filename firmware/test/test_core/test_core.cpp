#include <string.h>
#include <unity.h>

#include "echocane/AlertPolicy.h"
#include "echocane/AppConfig.h"
#include "echocane/ButtonDebouncer.h"
#include "echocane/EchoCaneController.h"
#include "echocane/MedianFilter.h"
#include "echocane/ObstacleDetector.h"
#include "echocane/PulseTimer.h"
#include "echocane/Telemetry.h"

namespace {

using namespace echocane;

AppConfig config;
EchoCaneController controller(config);

void feed(uint16_t cm, uint8_t samples = 5) {
  for (uint8_t i = 0; i < samples; ++i) {
    controller.update(DistanceReading::valid(cm));
  }
}

AlertLevel levelFor(uint16_t cm, uint8_t samples = 5) {
  EchoCaneController local(config);
  local.begin();
  for (uint8_t i = 0; i < samples; ++i) {
    local.update(DistanceReading::valid(cm));
  }
  return local.level();
}

void forceFault() {
  controller.update(DistanceReading::timeout());
  controller.update(DistanceReading::timeout());
  controller.update(DistanceReading::timeout());
}

}  // namespace

void setUp() { controller.begin(); }

void tearDown() {}

void test_median_filter_rejects_isolated_spike() {
  MedianFilter filter;
  TEST_ASSERT_FALSE(filter.hasSample());
  filter.add(100);
  filter.add(102);
  filter.add(400);
  filter.add(101);
  filter.add(99);
  TEST_ASSERT_EQUAL_UINT8(5, filter.count());
  TEST_ASSERT_EQUAL_UINT16(101, filter.median());
  filter.reset();
  TEST_ASSERT_FALSE(filter.hasSample());
}

void test_median_filter_lower_median_for_even_window() {
  MedianFilter filter;
  filter.add(10);
  filter.add(20);
  filter.add(30);
  filter.add(40);
  TEST_ASSERT_EQUAL_UINT16(20, filter.median());
}

void test_classification_thresholds() {
  TEST_ASSERT_EQUAL_INT(static_cast<int>(AlertLevel::Clear), static_cast<int>(levelFor(151)));
  TEST_ASSERT_EQUAL_INT(static_cast<int>(AlertLevel::Caution), static_cast<int>(levelFor(150)));
  TEST_ASSERT_EQUAL_INT(static_cast<int>(AlertLevel::Caution), static_cast<int>(levelFor(80)));
  TEST_ASSERT_EQUAL_INT(static_cast<int>(AlertLevel::Danger), static_cast<int>(levelFor(79)));
  TEST_ASSERT_EQUAL_INT(static_cast<int>(AlertLevel::Clear), static_cast<int>(levelFor(400)));
}

void test_caution_hysteresis_release() {
  TEST_ASSERT_EQUAL_INT(static_cast<int>(AlertLevel::Caution),
                        static_cast<int>(levelFor(120)));
  TEST_ASSERT_EQUAL_INT(static_cast<int>(AlertLevel::Caution),
                        static_cast<int>(levelFor(120)));
  controller.begin();
  feed(120);
  feed(155);
  TEST_ASSERT_EQUAL_INT(static_cast<int>(AlertLevel::Caution),
                        static_cast<int>(controller.level()));
  feed(161);
  TEST_ASSERT_EQUAL_INT(static_cast<int>(AlertLevel::Clear),
                        static_cast<int>(controller.level()));
}

void test_danger_hysteresis_release() {
  controller.begin();
  feed(50);
  TEST_ASSERT_EQUAL_INT(static_cast<int>(AlertLevel::Danger),
                        static_cast<int>(controller.level()));
  feed(85);
  TEST_ASSERT_EQUAL_INT(static_cast<int>(AlertLevel::Danger),
                        static_cast<int>(controller.level()));
  feed(91);
  TEST_ASSERT_EQUAL_INT(static_cast<int>(AlertLevel::Caution),
                        static_cast<int>(controller.level()));
}

void test_single_spike_is_filtered() {
  controller.begin();
  feed(300);
  TEST_ASSERT_EQUAL_INT(static_cast<int>(AlertLevel::Clear),
                        static_cast<int>(controller.level()));
  controller.update(DistanceReading::valid(20));
  TEST_ASSERT_EQUAL_INT(static_cast<int>(AlertLevel::Clear),
                        static_cast<int>(controller.level()));
  feed(20, 4);
  TEST_ASSERT_EQUAL_INT(static_cast<int>(AlertLevel::Danger),
                        static_cast<int>(controller.level()));
}

void test_timeout_confirms_fault() {
  controller.begin();
  TEST_ASSERT_EQUAL_INT(static_cast<int>(SensorHealth::Starting),
                        static_cast<int>(controller.health()));

  controller.update(DistanceReading::timeout());
  TEST_ASSERT_EQUAL_INT(static_cast<int>(SensorHealth::Degraded),
                        static_cast<int>(controller.health()));
  TEST_ASSERT_EQUAL_INT(static_cast<int>(AlertLevel::Caution),
                        static_cast<int>(controller.level()));

  controller.update(DistanceReading::timeout());
  TEST_ASSERT_EQUAL_INT(static_cast<int>(SensorHealth::Degraded),
                        static_cast<int>(controller.health()));

  const AlertUpdate update = controller.update(DistanceReading::timeout());
  TEST_ASSERT_EQUAL_INT(static_cast<int>(SensorHealth::Fault),
                        static_cast<int>(update.health));
  TEST_ASSERT_EQUAL_INT(static_cast<int>(AlertLevel::Fault),
                        static_cast<int>(update.level));
  TEST_ASSERT_FALSE(update.obstacleFree);
  TEST_ASSERT_FALSE(update.hasDistance);
}

void test_fault_never_reports_obstacle_free() {
  controller.begin();
  feed(300);
  TEST_ASSERT_TRUE(controller.update(DistanceReading::valid(300)).obstacleFree);

  forceFault();
  TEST_ASSERT_FALSE(controller.update(DistanceReading::valid(300)).obstacleFree);
}

void test_recovery_requires_consecutive_valid_readings() {
  controller.begin();
  forceFault();
  TEST_ASSERT_EQUAL_INT(static_cast<int>(SensorHealth::Fault),
                        static_cast<int>(controller.health()));

  controller.update(DistanceReading::valid(120));
  TEST_ASSERT_EQUAL_INT(static_cast<int>(SensorHealth::Fault),
                        static_cast<int>(controller.health()));
  TEST_ASSERT_EQUAL_INT(static_cast<int>(AlertLevel::Fault),
                        static_cast<int>(controller.level()));

  controller.update(DistanceReading::valid(120));
  TEST_ASSERT_EQUAL_INT(static_cast<int>(SensorHealth::Fault),
                        static_cast<int>(controller.health()));

  const AlertUpdate recovered = controller.update(DistanceReading::valid(120));
  TEST_ASSERT_EQUAL_INT(static_cast<int>(SensorHealth::Ok),
                        static_cast<int>(recovered.health));
  TEST_ASSERT_EQUAL_INT(static_cast<int>(AlertLevel::Caution),
                        static_cast<int>(recovered.level));
}

void test_out_of_range_counts_as_failure() {
  controller.begin();
  controller.update(DistanceReading::outOfRange(500));
  controller.update(DistanceReading::outOfRange(500));
  const AlertUpdate update = controller.update(DistanceReading::outOfRange(500));
  TEST_ASSERT_EQUAL_INT(static_cast<int>(SensorHealth::Fault),
                        static_cast<int>(update.health));
  TEST_ASSERT_EQUAL_INT(static_cast<int>(ReadingStatus::OutOfRange),
                        static_cast<int>(update.rawStatus));
}

void test_invalid_reading_degrades_but_is_not_clear() {
  controller.begin();
  feed(300);
  TEST_ASSERT_TRUE(controller.level() == AlertLevel::Clear);

  const AlertUpdate update = controller.update(DistanceReading::timeout());
  TEST_ASSERT_EQUAL_INT(static_cast<int>(SensorHealth::Degraded),
                        static_cast<int>(update.health));
  TEST_ASSERT_EQUAL_INT(static_cast<int>(AlertLevel::Caution),
                        static_cast<int>(update.level));
  TEST_ASSERT_FALSE(update.obstacleFree);
}

void test_button_debouncing_emits_single_press() {
  ButtonDebouncer button(30);
  TEST_ASSERT_FALSE(button.update(false, 0));
  TEST_ASSERT_FALSE(button.update(true, 1));
  TEST_ASSERT_FALSE(button.update(false, 10));
  TEST_ASSERT_FALSE(button.update(true, 20));
  TEST_ASSERT_FALSE(button.update(true, 49));
  TEST_ASSERT_TRUE(button.update(true, 51));
  TEST_ASSERT_FALSE(button.update(true, 60));
  TEST_ASSERT_FALSE(button.update(false, 80));
  TEST_ASSERT_FALSE(button.update(false, 111));
  TEST_ASSERT_FALSE(button.update(false, 120));
}

void test_alert_pattern_selection() {
  const AlertCommand caution =
      makeAlertCommand(AlertLevel::Caution, SystemMode::Assist, config);
  TEST_ASSERT_EQUAL_UINT8(40, caution.haptic.intensityPercent);
  TEST_ASSERT_TRUE(caution.audioEnabled);

  const AlertCommand quiet =
      makeAlertCommand(AlertLevel::Danger, SystemMode::Quiet, config);
  TEST_ASSERT_EQUAL_UINT8(100, quiet.haptic.intensityPercent);
  TEST_ASSERT_FALSE(quiet.audioEnabled);

  const AlertCommand clear =
      makeAlertCommand(AlertLevel::Clear, SystemMode::Assist, config);
  TEST_ASSERT_EQUAL_UINT8(0, clear.haptic.intensityPercent);
  TEST_ASSERT_EQUAL_UINT16(0, clear.tone.onMs);
  TEST_ASSERT_FALSE(clear.audioEnabled);

  const AlertCommand fault =
      makeAlertCommand(AlertLevel::Fault, SystemMode::Diagnostic, config);
  TEST_ASSERT_EQUAL_UINT16(1000, fault.tone.frequencyHz);
  TEST_ASSERT_TRUE(fault.led.onMs > 0);
}

void test_mode_cycling() {
  controller.begin();
  TEST_ASSERT_EQUAL_INT(static_cast<int>(SystemMode::Assist),
                        static_cast<int>(controller.mode()));
  TEST_ASSERT_EQUAL_INT(static_cast<int>(SystemMode::Quiet),
                        static_cast<int>(controller.cycleMode()));
  TEST_ASSERT_EQUAL_INT(static_cast<int>(SystemMode::Diagnostic),
                        static_cast<int>(controller.cycleMode()));
  TEST_ASSERT_EQUAL_INT(static_cast<int>(SystemMode::Assist),
                        static_cast<int>(controller.cycleMode()));
}

void test_pulse_timer() {
  PulseTimer timer;
  timer.reset(0);
  timer.configure(100, 200, false, 0);
  TEST_ASSERT_TRUE(timer.output(0));
  TEST_ASSERT_TRUE(timer.output(99));
  TEST_ASSERT_FALSE(timer.output(100));
  TEST_ASSERT_FALSE(timer.output(299));
  TEST_ASSERT_TRUE(timer.output(300));

  timer.configure(0, 0, true, 300);
  TEST_ASSERT_TRUE(timer.output(300));

  timer.configure(0, 0, false, 300);
  TEST_ASSERT_FALSE(timer.output(300));
}

void test_telemetry_clear_record() {
  controller.begin();
  feed(300);
  const AlertUpdate update = controller.update(DistanceReading::valid(300));
  char buffer[128];
  const size_t length = formatTelemetry(buffer, sizeof(buffer), 1234, update);
  TEST_ASSERT_TRUE(length > 0);
  TEST_ASSERT_NOT_NULL(strstr(buffer, "EC|t=1234"));
  TEST_ASSERT_NOT_NULL(strstr(buffer, "level=CLEAR"));
  TEST_ASSERT_NOT_NULL(strstr(buffer, "health=OK"));
  TEST_ASSERT_NOT_NULL(strstr(buffer, "mode=ASSIST"));
  TEST_ASSERT_NOT_NULL(strstr(buffer, "free=1"));
}

void test_telemetry_fault_record_not_free() {
  controller.begin();
  forceFault();
  const AlertUpdate update = controller.update(DistanceReading::timeout());
  char buffer[128];
  formatTelemetry(buffer, sizeof(buffer), 2500, update);
  TEST_ASSERT_NOT_NULL(strstr(buffer, "level=FAULT"));
  TEST_ASSERT_NOT_NULL(strstr(buffer, "health=FAULT"));
  TEST_ASSERT_NOT_NULL(strstr(buffer, "raw=TIMEOUT"));
  TEST_ASSERT_NOT_NULL(strstr(buffer, "d=none"));
  TEST_ASSERT_NOT_NULL(strstr(buffer, "free=0"));
}

void test_telemetry_truncates_safely() {
  controller.begin();
  const AlertUpdate update = controller.update(DistanceReading::valid(100));
  char buffer[16];
  const size_t length = formatTelemetry(buffer, sizeof(buffer), 1, update);
  TEST_ASSERT_TRUE(length < sizeof(buffer));
  TEST_ASSERT_EQUAL_INT('\0', buffer[length]);
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_median_filter_rejects_isolated_spike);
  RUN_TEST(test_median_filter_lower_median_for_even_window);
  RUN_TEST(test_classification_thresholds);
  RUN_TEST(test_caution_hysteresis_release);
  RUN_TEST(test_danger_hysteresis_release);
  RUN_TEST(test_single_spike_is_filtered);
  RUN_TEST(test_timeout_confirms_fault);
  RUN_TEST(test_fault_never_reports_obstacle_free);
  RUN_TEST(test_recovery_requires_consecutive_valid_readings);
  RUN_TEST(test_out_of_range_counts_as_failure);
  RUN_TEST(test_invalid_reading_degrades_but_is_not_clear);
  RUN_TEST(test_button_debouncing_emits_single_press);
  RUN_TEST(test_alert_pattern_selection);
  RUN_TEST(test_mode_cycling);
  RUN_TEST(test_pulse_timer);
  RUN_TEST(test_telemetry_clear_record);
  RUN_TEST(test_telemetry_fault_record_not_free);
  RUN_TEST(test_telemetry_truncates_safely);
  return UNITY_END();
}
