# Scenario 6 — obstacle moving away (manual)

Wokwi's HC-SR04 reference says the simulated distance is changed with the
component's on-screen slider. The sensor is **not** in Wokwi's published list of
parts with automation controls, so this scenario cannot be driven by a
`set-control` step. It is therefore a manual procedure, not an automated test.

## Procedure

1. Build and start the interactive project (see `simulation/wokwi/README.md`).
2. Set the HC-SR04 slider to **45 cm**. Confirm `level=DANGER` in the serial
   monitor.
3. Move the slider to **120 cm** and confirm `level=CAUTION`.
4. Move the slider to **300 cm** and confirm `level=CLEAR`, `free=1`.
5. Move back to **140 cm** and confirm `level=CAUTION`, then **155 cm** and
   confirm it stays `CAUTION` until you pass **160 cm** (hysteresis release).

Expected evidence: serial lines with `level=DANGER`, then `level=CAUTION`, then
`level=CLEAR`, then `level=CAUTION` again. Record a screen capture or save the
serial log; do not claim this test passed without that evidence.

The host test `test_danger_hysteresis_release` covers the same 50 -> 85 -> 91 cm
sequence at the application-logic level, but it does not prove sensor timing.
