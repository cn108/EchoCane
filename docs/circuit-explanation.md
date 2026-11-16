# Circuit explanation and calculations

This document explains the electrical intent behind the schematic and records the
calculations used to choose component values. Calculations are paper design
checks; the ngspice results are a simulation of a lumped model. Neither is a
bench measurement.

## 1. Power and ground

The board is powered from a regulated external 5 V USB source. The Nano's USB
connector is the mechanical and electrical entry point; the carrier board does
not include a second regulator or a battery charger.

- +5 V is distributed to the Nano 5V pin, J1.1 (HC-SR04), J2.1 (motor), D1
  cathode, C1.1 and C2.1.
- GND is distributed to the Nano GND pins, J1.4, Q1 emitter, R2.2, C1.2, C2.2,
  C3.2, D2 cathode, SW1.2 and BZ1.2.
- A bottom-layer GND zone provides the return path. Motor current returns from
  Q1's emitter to the ground zone; the +5 V feed and motor low side use wider
  0.8 mm tracks.

### 1.1 Estimated current

| Load | Estimate | Basis |
|---|---|---|
| Nano board | 25 mA | ATmega plus USB-serial/power-LED allowance; not measured |
| HC-SR04 | 15 mA | Typical module peak, not measured |
| Motor | 100 mA | 5 V / 47 Ω design point |
| Base drive through R1 | 11.1 mA | Loaded 4.2 V GPIO through 270 Ω; D6 source current |
| Buzzer | 10 mA | Piezo tone current estimate |
| LED | 13.6 mA | (5 − 2) V / 220 Ω |
| **Total** | **174.7 mA** | Sum of design estimates |

A 500 mA USB source leaves 325.3 mA of nominal headroom. The 0.12 mA in R2 is
inside the 11.1 mA R1 current and is not added again. Motor stall current is not
known and may exceed 100 mA; the source, connector and wiring must be sized for
the real motor. The drive calculation supports about 110 mA at the
forced-beta-10 target; a 150 mA stress case is not covered.

## 2. Ultrasonic sensor interface

The HC-SR04 is a 5 V module:

- TRIG requires a high pulse of at least 10 µs.
- ECHO goes high for the round-trip time.
- The common approximation is `distance_cm = echo_high_us / 58`.
- The nominal range is 2–400 cm, so the maximum round-trip time is about
  `400 × 58 = 23,200 µs`.

Firmware sends a 10 µs pulse on D9 and measures ECHO on D10 with a 25,000 µs
timeout. The timeout is deliberately above the 23.2 ms maximum so a valid 400 cm
echo is not truncated at the 20 °C approximation. If ECHO never rises, `pulseIn`
returns 0 and the reading is `Timeout`. If the computed distance is below 2 cm or
above 400 cm, the reading is `OutOfRange`. The 343 m/s assumption is temperature-
dependent; at lower temperatures a 400 cm echo can approach the 25 ms limit. That
margin is documented, not measured.

The ECHO output is a 5 V logic signal. The Nano is a 5 V board, so no level
shifter is required. If a 3.3 V controller were substituted, a divider or level
shifter would be mandatory.

## 3. Vibration-motor driver

```text
+5 V ── J2.1 ── motor ── J2.2 ── Q1 collector
                                  │
                                  ├── D1 anode; D1 cathode to +5 V
                                  │
D6 ── R1 270 Ω ── Q1 base          │
                    │             │
                   R2 10 kΩ      Q1 emitter ── GND
                    │
                   GND
```

Q1 is a PN2222A NPN low-side switch. R1 limits base current; R2 keeps the base
low when D6 is floating or the MCU is resetting. D1 clamps the inductive kick when
Q1 turns off.

### 3.1 Loaded GPIO and base current

The previous calculation used an ideal 5 V GPIO and omitted R2. The ATmega328P
 datasheet guarantees **VOH ≥ 4.2 V at IOH = −20 mA, VCC = 5 V, over −40 to
+85 °C**. The actual pin current is only about 11 mA, but 4.2 V is used here as a
conservative DC bound. The datasheet's typical curve is higher at this lower
current; that is not used for design.

With VBE(sat) = 1.2 V (the datasheet maximum at 150 mA / 15 mA, applied
conservatively at 100 mA) and R1 = 270 Ω:

```text
I_R1 = (VOH − VBE) / R1
     = (4.2 − 1.2) / 270
     = 11.11 mA

I_R2 = VBE / R2
     = 1.2 / 10,000
     = 0.120 mA

Ib = I_R1 − I_R2
   = 11.11 − 0.120
   = 10.99 mA

V_R1 = VOH − VBE = 3.0 V
P_R1 = 3.0² / 270 = 33.3 mW
```

The R1 current, not the base current, is the D6 source current: **11.11 mA**,
below the ATmega328P's recommended 20 mA continuous per-pin limit (absolute
maximum 40 mA). If VBE falls to 0.6 V, the pin current is 13.33 mA and the base
current is 13.27 mA; the pin still has 6.67 mA of margin to the recommended limit.
The 0.25 W R1 has at least a 5:1 power margin over the 48 mW worst case.

ngspice, using the same 4.2 V source, 270 Ω and R2, gives 12.14 mA through R1,
0.092 mA through R2 and 12.04 mA into the base. The simulation's VBE is only
0.923 V, so its base current is higher than the conservative paper value; that is
expected, not a contradiction.

### 3.2 Forced beta and load current

For a 100 mA motor:

```text
forced beta = Ic / Ib = 100 mA / 10.99 mA = 9.10
```

A forced beta at or below 10 is the conservative target for hard saturation. With
the loaded GPIO and R2 loading, the maximum base resistor is:

```text
R1(max) = (4.2 − 1.2) / (100 mA / 10 + 1.2 V / 10 kΩ)
        = 3.0 / 0.01012
        = 296.4 Ω
```

Therefore **270 Ω** is selected. 300 Ω gives 9.88 mA, forced beta 10.12, and is
above the 296.4 Ω limit; 330 Ω gives 8.97 mA, forced beta 11.15, and is clearly
outside it. The selected drive would support at most about **109.9 mA** at forced
beta 10. That is a ceiling of the calculation, not a motor rating. A 150 mA
stress case gives forced beta 13.6, so the design does not claim coverage of that
case. **The real motor's free-run and stall currents remain unverified.**

If a lower-gain transistor or a different motor were used, R1 would need to be
recalculated against both the forced-beta target and the Nano pin limit; simply
lowering R1 without checking the pin current is not acceptable.

### 3.3 Transistor versus logic-level MOSFET

The 330 Ω, 300 Ω and 270 Ω BJT cases are compared in
[`hardware-design.md`](hardware-design.md#22-driver-alternatives-considered). The
270 Ω BJT is retained because it fits the existing TO-92 footprint and meets the
loaded-GPIO target. An IRLZ44N TO-220 MOSFET has a 35 mΩ vendor parametric
maximum at 4.5 V gate drive and a conservative 39 mΩ bound from its 4 V maximum
(the 5 V maximum is 28 mΩ), so its conduction loss at 100 mA is only about
0.39 mW. It is electrically viable, but it
requires a different footprint, gate resistor and pull-down, and its 66 nC gate
charge is much larger than the BJT base charge. It is not a drop-in replacement
for revision 0.1.

### 3.4 Output stage

The ngspice transient model uses a 4.2 V loaded-GPIO source, 270 Ω, R2, a
47 Ω / 10 mH motor and a 20 ms drive pulse:

| Quantity | Result |
|---|---:|
| Drive voltage, loaded | 4.20 V |
| R1 current, drive high | 12.14 mA |
| R2 current | 0.092 mA |
| Base current, drive high | 12.04 mA |
| Base-emitter voltage | 0.923 V |
| Motor current, on | 104.37 mA |
| Collector-emitter voltage, on | 0.0945 V |
| Transistor dissipation, on | 9.86 mW |
| Motor voltage, on | 4.91 V |
| Collector peak at turn-off | 5.63 V |
| Flyback diode peak | 104.37 mA |

The motor inductance and the 100 mA load are assumptions. A 47 Ω, 10 mH lumped
model gives an
electrical time constant of:

```text
τ = L / R = 10 mH / 47 Ω = 213 µs
```

so the current reaches its steady value quickly compared with the 20 ms pulse.
The flyback diode carries the inductor current at turn-off and clamps the
collector near 5 V plus a diode drop; the simulated peak is 5.63 V. A 1N4007 is
rated for 1000 V and 1 A, far above this stress. Its relatively slow recovery is
acceptable for a small motor; a Schottky diode would reduce turn-off loss but is
not necessary for this prototype.

![ngspice driver waveform](../images/driver-waveform.svg)

The waveform is generated from `simulation/simulide/driver.cir` by
`plot_driver.py`. It is a model, not a measurement of a physical motor.

### 3.4 Why a flyback diode is mandatory

Without D1, turning off Q1 would force the motor current to collapse through the
transistor's parasitic capacitance and the supply, producing a large inductive
spike that can exceed the transistor's Vce rating and disrupt the 5 V rail. D1
provides a confined path for the stored energy.

## 4. Status LED

D7 drives D2 through R3:

```text
I_LED = (5.0 − Vf) / 220 Ω
```

With a green LED Vf of about 2.0 V:

```text
I_LED = 3.0 / 220 = 13.6 mA
P_R3  = 3.0² / 220 = 40.9 mW
```

13.6 mA is within the Nano pin limit and provides a bright indicator. The LED is
a status/output proxy, not a substitute for the motor.

## 5. Mode button and debounce

SW1 connects D2 to GND. D2 is configured as `INPUT_PULLUP`, so the pin reads HIGH
when released and LOW when pressed. C3 (100 nF) from D2 to GND forms an RC filter
with the internal pull-up (approximately 20–50 kΩ):

```text
τ = R_pullup × C = 30 kΩ × 100 nF = 3 ms
```

The firmware additionally requires 30 ms of stable state. The hardware filter
removes fast contact bounce; the firmware debounce prevents a single press from
being counted multiple times. The RC time constant is an estimate because the
internal pull-up has a wide tolerance.

## 6. Buzzer

BZ1 is a 5 V piezo buzzer driven from D8 through R4 (100 Ω). The series resistor
limits current and reduces the load on the pin; a piezo element is largely
capacitive, so the DC current is small and the acoustic output depends on the
drive frequency and the buzzer's resonant frequency. The firmware uses `tone()`
on D8 with 1800 Hz (caution), 2400 Hz (danger) and 1000 Hz (fault). The actual
sound pressure level has not been measured.

## 7. Decoupling

- C1 (100 nF ceramic) is a high-frequency bypass for the motor/connector supply.
- C2 (10 µF electrolytic) provides bulk charge for motor starts and transients.
- The Nano module has its own USB input capacitance; no additional regulator is
  added.

The capacitors are placed near the motor connector and the +5 V distribution.
The bottom GND zone provides a short return path.

## 8. Signal integrity and protection

- Series resistors on the LED and buzzer limit pin current.
- R1 limits base current; R2 defines Q1's off state.
- D1 clamps the motor's inductive kick.
- The HC-SR04 ECHO is 5 V, compatible with the 5 V Nano.
- There is no reverse-polarity protection on the +5 V input. The design assumes a
  keyed/known USB source; a production version should add a fuse, reverse
  polarity protection and transient suppression.
- There is no ESD protection on the connectors. A production version should add
  TVS diodes or a protected connector.
- The motor connector is not keyed; the motor has no polarity requirement for
  vibration, but the wiring should be documented.

## 9. What the circuit does not prove

- The motor model does not prove torque, vibration amplitude, frequency or user
  perception.
- The buzzer model does not prove sound pressure level or audibility in noise.
- The HC-SR04 model does not reproduce acoustic beam width, multipath, soft or
  angled surfaces, or cross-talk.
- The 5 V USB source, connectors, PCB and assembly have not been physically
    tested. Motor stall current and starting torque are unknown; the 270 Ω base
  drive is sized for the 100 mA design point, not for an arbitrary stall
  condition, and its forced-beta-10 ceiling is about 109.9 mA at the assumed
  loaded GPIO voltage.
- The calculations use generic transistor/diode models and estimated motor
  parameters.

These gaps are carried into the [safety analysis](safety-analysis.md) and
[simulation limitations](simulation-limitations.md).
