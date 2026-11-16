# Supplementary driver simulation

SimulIDE is **not installed** in the reconstruction environment, and no
validated `.simu` circuit file is included. Creating a binary/GUI-dependent
project without opening it would not be honest evidence, so this directory
contains:

1. `driver_analysis.py` — executable DC design-margin calculations.
2. `driver.cir` — an ngspice transient model of the same driver stage.
3. This guide — exact steps to reproduce the circuit in SimulIDE when it is
   available.

The ngspice run was executed and its measurements are recorded in
`docs/simulation-limitations.md` and `docs/testing-strategy.md`. It models
electrical behaviour only; it cannot prove that a motor vibrates, how strongly
it vibrates, or whether a user can feel it.

Executed result (ngspice-39, generic models):

| Quantity | Result |
|---|---|
| Base current, drive high | 12.34 mA |
| Base-emitter voltage | 0.926 V |
| Collector-emitter voltage, on | 0.094 V |
| Motor current, on | 104.4 mA |
| Collector peak at turn-off | 5.77 V |
| Flyback diode peak | 104.3 mA |
| Transistor dissipation, on | 9.8 mW (0.094 V × 104.4 mA) |

These values come from `driver.cir`; see `ngspice-results.txt` and
`driver-waveform-sampled.csv`. They are simulation output for a lumped motor
model, not bench measurements.

## Circuit to build in SimulIDE

| From | To | Value / part |
|---|---|---|
| +5 V rail | J2 pin 1 / motor + | 5 V |
| Motor − | Q1 collector | PN2222A (TO-92) |
| Q1 emitter | GND | — |
| Nano D6 | R1 | 330 Ω |
| R1 other end | Q1 base | — |
| Q1 base | GND | R2 10 kΩ |
| Motor + | D1 cathode | 1N4007 |
| Motor − / collector | D1 anode | 1N4007 |
| +5 V | C1 / C2 | 100 nF ceramic, 10 µF electrolytic |
| C1/C2 returns | GND | — |

Add a 5 V supply with a common ground. In SimulIDE place an Arduino Nano,
configure its clock to 16 MHz, and load a compiled `.hex`. HC-SR04 support in
SimulIDE depends on the release and on third-party models; this supplementary
circuit deliberately focuses on the driver stage and does not assume a sensor
model. Running the full EchoCane firmware without a working sensor model would
correctly enter the sensor-fault state. Use a square-wave source or the driver
test sketch at the Nano's D6 pin to exercise the transistor.

Suggested test sketch logic:

```
void setup() { pinMode(6, OUTPUT); }
void loop() {
  analogWrite(6, 102);  // 40 %
  delay(1000);
  analogWrite(6, 255);  // 100 %
  delay(1000);
  analogWrite(6, 0);    // off
  delay(1000);
}
```

## SimulIDE procedure

1. Install SimulIDE 1.x and the Arduino toolchain it expects (the official
   SimulIDE guide recommends a working Arduino IDE 1.8.x installation).
2. Place the Nano, PN2222A, 1N4007, 330 Ω, 10 kΩ, the two capacitors and a DC
   motor. Connect them as in the table above.
3. Set the motor model's nominal voltage to 5 V and its resistance to
   approximately 47 Ω so the steady current is about 100 mA.
4. Compile the test sketch to a `.hex`, right-click the Nano and choose
   **Load firmware**.
5. Run the simulation and observe the collector voltage and motor current.
   With 40 % PWM the average current should be roughly 40 % of the 100 % value;
   the flyback diode should clamp the collector during turn-off.
6. Save the `.simu` file under this directory and record the SimulIDE version
   and a screenshot. Do not report the simulation as executed until then.

## Executed alternative: ngspice

`driver.cir` is a first-order transient model of the driver. It includes a
47 Ω / 10 mH motor, PN2222A Gummel-Poon model, 1N4007 diode model, 330 Ω base
resistor and 5 V PWM source. Run it with:

```
ngspice -b -o ngspice-results.txt driver.cir
```

The model demonstrates the intended low-side switching and flyback behaviour.
`plot_driver.py` converts the raw ngspice output into
`images/driver-waveform.svg` and a sampled CSV. It does **not** validate the
real motor's torque, vibration frequency, audible noise, or the user's ability
to perceive the warning. Those require physical hardware and user testing.
