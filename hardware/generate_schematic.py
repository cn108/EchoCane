#!/usr/bin/env python3
"""Generate the EchoCane KiCad schematic and BOM.

Run inside the KiCad container so the system symbol libraries are available:

  docker run --rm -v "$PWD:/work" -w /work kicad/kicad:10.0 \
      python3 hardware/generate_schematic.py

The generator embeds only the symbols it uses. Peripheral blocks are drawn with
visible orthogonal wiring; global labels are used only for the long Nano-to-block
signals and for net-name preservation. KiCad ERC remains the authority on
connectivity.
"""

from __future__ import annotations

import csv
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "hardware" / "kicad"
SCHEMATIC = OUT / "EchoCane.kicad_sch"
BOM = ROOT / "hardware" / "bom" / "EchoCane-BOM.csv"
SYMBOL_ROOT = Path("/usr/share/kicad/symbols")
PROJECT = "EchoCane"
ROOT_UUID = str(uuid.uuid5(uuid.NAMESPACE_URL, "echocane/root-sheet"))
PAPER = "A4"
POWER_INDEX = 0

# Child symbol -> (library, parent symbol). The parent is embedded under the
# child name because KiCad's derived-symbol syntax is awkward in a standalone
# generated schematic.
SYMBOLS: dict[str, tuple[str, str]] = {
    "Device:R": ("Device", "R"),
    "Device:C": ("Device", "C"),
    "Device:C_Polarized": ("Device", "C_Polarized"),
    "Device:LED": ("Device", "LED"),
    "Device:D": ("Device", "D"),
    "Device:Buzzer": ("Device", "Buzzer"),
    "Switch:SW_Push": ("Switch", "SW_Push"),
    "Connector_Generic:Conn_01x04": ("Connector_Generic", "Conn_01x04"),
    "Connector_Generic:Conn_01x02": ("Connector_Generic", "Conn_01x02"),
    # Classic Nano v3.0 has the same 30-pin interface as the v2.x symbol.
    "MCU_Module:Arduino_Nano_v2.x": ("MCU_Module", "Arduino_Nano_v2.x"),
    # Generic EBC NPN symbol; the BOM/value select the PN2222A.
    "Transistor_BJT:Q_NPN_EBC": ("Transistor_BJT", "Q_NPN_EBC"),
    "power:+5V": ("power", "+5V"),
    "power:GND": ("power", "GND"),
    "power:PWR_FLAG": ("power", "PWR_FLAG"),
    "Mechanical:MountingHole": ("Mechanical", "MountingHole"),
}

FOOTPRINTS = {
    "A1": "Module:Arduino_Nano",
    "J1": "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
    "J2": "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
    "Q1": "Package_TO_SOT_THT:TO-92_Inline",
    "R1": "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
    "R2": "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
    "R3": "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
    "R4": "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
    "C1": "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm",
    "C2": "Capacitor_THT:CP_Radial_D5.0mm_P2.00mm",
    "C3": "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm",
    "D1": "Diode_THT:D_DO-41_SOD81_P7.62mm_Horizontal",
    "D2": "LED_THT:LED_D5.0mm",
    "SW1": "Button_Switch_THT:SW_PUSH_6mm",
    "BZ1": "Buzzer_Beeper:Buzzer_12x9.5RM7.6",
    "H1": "MountingHole:MountingHole_3.2mm_M3",
    "H2": "MountingHole:MountingHole_3.2mm_M3",
    "H3": "MountingHole:MountingHole_3.2mm_M3",
    "H4": "MountingHole:MountingHole_3.2mm_M3",
}


@dataclass
class Part:
    ref: str
    symbol: str
    value: str
    x: float
    y: float
    description: str
    nets: dict[str, str | None] = field(default_factory=dict)


PARTS: list[Part] = [
    Part(
        "A1",
        "MCU_Module:Arduino_Nano_v2.x",
        "Arduino Nano v3.x",
        120,
        100,
        "ATmega328P 5 V Arduino Nano module",
        {
            "4": "GND",
            "5": "BUTTON",
            "9": "HAPTIC_PWM",
            "10": "LED_CMD",
            "11": "BUZZER_CMD",
            "12": "US_TRIG",
            "13": "US_ECHO",
            "27": "+5V",
            "29": "GND",
        },
    ),
    Part(
        "J1",
        "Connector_Generic:Conn_01x04",
        "HC-SR04",
        40,
        75,
        "4-pin HC-SR04 ultrasonic sensor connector",
        {"1": "+5V", "2": "US_TRIG", "3": "US_ECHO", "4": "GND"},
    ),
    Part(
        "J2",
        "Connector_Generic:Conn_01x02",
        "Vibration motor",
        40,
        110,
        "2-pin vibration motor connector",
        {"1": "+5V", "2": "MOTOR_NEG"},
    ),
    Part(
        "Q1",
        "Transistor_BJT:Q_NPN_EBC",
        "PN2222A",
        70,
        145,
        "NPN low-side motor switch, TO-92",
        {"1": "GND", "2": "Q_BASE", "3": "MOTOR_NEG"},
    ),
    Part(
        "R1",
        "Device:R",
        "270",
        55,
        130,
        "Base current limit resistor",
        {"1": "HAPTIC_PWM", "2": "Q_BASE"},
    ),
    Part(
        "R2",
        "Device:R",
        "10k",
        60,
        155,
        "Base pull-down resistor",
        {"1": "Q_BASE", "2": "GND"},
    ),
    Part(
        "D1",
        "Device:D",
        "1N4007",
        85,
        140,
        "Flyback diode across the motor",
        {"1": "+5V", "2": "MOTOR_NEG"},
    ),
    Part(
        "C1",
        "Device:C",
        "100nF",
        100,
        155,
        "Motor supply decoupling, ceramic",
        {"1": "+5V", "2": "GND"},
    ),
    Part(
        "C2",
        "Device:C_Polarized",
        "10uF",
        110,
        155,
        "Motor supply bulk capacitor",
        {"1": "+5V", "2": "GND"},
    ),
    Part(
        "SW1",
        "Switch:SW_Push",
        "MODE",
        170,
        70,
        "Mode push button, active low",
        {"1": "BUTTON", "2": "GND"},
    ),
    Part(
        "C3",
        "Device:C",
        "100nF",
        170,
        85,
        "Button hardware debounce capacitor",
        {"1": "BUTTON", "2": "GND"},
    ),
    Part(
        "R3",
        "Device:R",
        "220",
        170,
        110,
        "Status LED series resistor",
        {"1": "LED_CMD", "2": "LED_A"},
    ),
    Part(
        "D2",
        "Device:LED",
        "Green",
        175,
        125,
        "Status indicator LED, 5 mm",
        {"1": "GND", "2": "LED_A"},
    ),
    Part(
        "R4",
        "Device:R",
        "100",
        170,
        145,
        "Buzzer series resistor",
        {"1": "BUZZER_CMD", "2": "BUZZER_A"},
    ),
    Part(
        "BZ1",
        "Device:Buzzer",
        "Buzzer",
        185,
        155,
        "5 V piezo buzzer",
        {"1": "BUZZER_A", "2": "GND"},
    ),
    Part("H1", "Mechanical:MountingHole", "MountingHole", 235, 60, "M3 PCB mounting hole", {}),
    Part("H2", "Mechanical:MountingHole", "MountingHole", 255, 60, "M3 PCB mounting hole", {}),
    Part("H3", "Mechanical:MountingHole", "MountingHole", 235, 80, "M3 PCB mounting hole", {}),
    Part("H4", "Mechanical:MountingHole", "MountingHole", 255, 80, "M3 PCB mounting hole", {}),
]



LAYOUT = {
    "A1": (190, 105),
    "J1": (45, 55),
    "J2": (155, 88),
    "Q1": (140, 125),
    "R1": (105, 115),
    "R2": (115, 140),
    "D1": (125, 105),
    "C1": (235, 105),
    "C2": (255, 105),
    "SW1": (45, 100),
    "C3": (70, 110),
    "R3": (50, 160),
    "D2": (70, 160),
    "R4": (95, 55),
    "BZ1": (135, 55),
    "H1": (95, 185),
    "H2": (115, 185),
    "H3": (95, 197),
    "H4": (115, 197),
}

HEADINGS = [
    ("ULTRASONIC SENSOR", 25, 38),
    ("MODE INPUT", 25, 78),
    ("STATUS LED", 25, 140),
    ("MOTOR DRIVER", 95, 80),
    ("AUDIO WARNING", 90, 38),
    ("ARDUINO NANO", 170, 70),
    ("POWER SOURCE", 215, 38),
    ("SUPPLY DECOUPLING", 225, 90),
    ("MECHANICAL", 95, 172),
]

def uid(*parts: object) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "echocane/" + "/".join(map(str, parts))))


def esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def balanced_block(text: str, start: int) -> str:
    depth = 0
    in_string = False
    escaped = False
    for i in range(start, len(text)):
        c = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif c == chr(92):
                escaped = True
            elif c == '"':
                in_string = False
        else:
            if c == '"':
                in_string = True
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
    raise ValueError("unbalanced symbol block")


def read_symbol_block(lib: str, name: str, lib_id: str) -> tuple[str, bool]:
    text = (SYMBOL_ROOT / f"{lib}.kicad_sym").read_text(encoding="utf-8")
    marker = f'(symbol "{name}"'
    start = text.find(marker)
    if start < 0:
        raise SystemExit(f"symbol {lib}:{name} not found")
    block = balanced_block(text, start)
    block = block.replace(marker, f'(symbol "{lib_id}"', 1)
    return block, '(extends "' in block


def pin_map(block: str) -> dict[str, tuple[float, float, float]]:
    pins: dict[str, tuple[float, float, float]] = {}
    for match in re.finditer(
        r"\(pin\s+\w+\s+\w+\s*\(at\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\)"
        r".*?\(number\s+\"([^\"]+)\"",
        block,
        re.S,
    ):
        number = match.group(4)
        pins.setdefault(number, (float(match.group(1)), float(match.group(2)), float(match.group(3))))
    return pins


SYMBOL_BLOCKS: dict[str, str] = {}
SYMBOL_PINS: dict[str, dict[str, tuple[float, float, float]]] = {}
for lib_id, (lib, requested) in SYMBOLS.items():
    child_block, derived = read_symbol_block(lib, requested, lib_id)
    base_name = lib_id.split(":", 1)[1]
    if derived:
        parent_name = re.search(r'\(extends\s+"([^"]+)"', child_block).group(1)
        parent_id = f"{lib}:{parent_name}"
        parent_block, _ = read_symbol_block(lib, parent_name, parent_id)
        SYMBOL_BLOCKS[parent_id] = parent_block
        pins = pin_map(parent_block)
        if not pins:
            raise SystemExit(f"no pins parsed for parent {parent_id}")
    else:
        pins = pin_map(child_block)
        if not pins and lib_id != "Mechanical:MountingHole":
            raise SystemExit(f"no pins parsed for {lib_id}")
    SYMBOL_BLOCKS[lib_id] = child_block
    SYMBOL_PINS[lib_id] = pins


def pin_position(part: Part, pin: str) -> tuple[float, float, float]:
    px, py, angle = SYMBOL_PINS[part.symbol][pin]
    return snap(part.x + px), snap(part.y - py), angle


def outward(angle: float) -> tuple[float, float]:
    # Library pin angle points into the body. The stub goes the other way; the
    # schematic Y axis is inverted relative to the library.
    if angle == 0:
        return -1.0, 0.0
    if angle == 180:
        return 1.0, 0.0
    if angle == 90:
        return 0.0, 1.0
    if angle == 270:
        return 0.0, -1.0
    raise ValueError(f"unsupported pin angle {angle}")


def fmt(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def snap(value: float) -> float:
    """Snap a coordinate to KiCad's 1.27 mm connection grid."""
    return round(value / 1.27) * 1.27


def property_block(name: str, value: str, x: float, y: float, hidden: bool = False, size: float = 1.27) -> str:
    hide = "\n\t\t\t\t(hide yes)" if hidden else ""
    return f"""\t\t(property "{esc(name)}" "{esc(value)}"
\t\t\t(at {fmt(x)} {fmt(y)} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size {size} {size})
\t\t\t\t){hide}
\t\t\t)
\t\t)"""


def wire(x1: float, y1: float, x2: float, y2: float, tag: str) -> str:
    return f"""\t(wire
\t\t(pts
\t\t\t(xy {fmt(x1)} {fmt(y1)}) (xy {fmt(x2)} {fmt(y2)})
\t\t)
\t\t(stroke
\t\t\t(width 0)
\t\t\t(type default)
\t\t)
\t\t(uuid "{uid('wire', tag)}")
\t)"""


def label(name: str, x: float, y: float, tag: str, dx: float = 1.0) -> str:
    justify = "right" if dx < 0 else "left"
    return f"""	(global_label "{esc(name)}"
		(shape bidirectional)
		(at {fmt(x)} {fmt(y)} 0)
		(effects
			(font
				(size 1.27 1.27)
			)
			(justify {justify})
		)
		(uuid "{uid('label', tag)}")
		(property "Intersheetrefs" "${{INTERSHEET_REFS}}"
			(at {fmt(x)} {fmt(y)} 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(hide yes)
			)
		)
	)"""


def heading(text: str, x: float, y: float) -> str:
    return f"""\t(text "{esc(text)}"
\t\t(at {fmt(x)} {fmt(y)} 0)
\t\t(effects
\t\t\t(font
\t\t\t\t(size 2 2)
\t\t\t\t(bold yes)
\t\t\t)
\t\t\t(justify left bottom)
\t\t)
\t\t(uuid "{uid('heading', text)}")
\t)"""


def note(text: str, x: float, y: float, tag: str) -> str:
    return f"""\t(text "{esc(text)}"
\t\t(at {fmt(x)} {fmt(y)} 0)
\t\t(effects
\t\t\t(font
\t\t\t\t(size 1.5 1.5)
\t\t\t)
\t\t\t(justify left bottom)
\t\t)
\t\t(uuid "{uid('note', tag)}")
\t)"""


def no_connect(x: float, y: float, tag: str) -> str:
    return f"""\t(no_connect
\t\t(at {fmt(x)} {fmt(y)})
\t\t(uuid "{uid('nc', tag)}")
\t)"""


def power_symbol(lib_id: str, x: float, y: float, tag: str) -> str:
    global POWER_INDEX
    POWER_INDEX += 1
    ref_prefix = "#PWR" if lib_id != "power:PWR_FLAG" else "#FLG"
    reference = f"{ref_prefix}{POWER_INDEX:03d}"
    value_y = y - 3.81 if lib_id == "power:+5V" else y + 3.81
    return f"""\t(symbol
\t\t(lib_id "{lib_id}")
\t\t(at {fmt(x)} {fmt(y)} 0)
\t\t(unit 1)
\t\t(exclude_from_sim no)
\t\t(in_bom no)
\t\t(on_board no)
\t\t(dnp no)
\t\t(uuid "{uid('power', tag)}")
\t\t(property "Reference" "{reference}"
\t\t\t(at {fmt(x)} {fmt(y - 2.54)} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(hide yes)
\t\t\t)
\t\t)
\t\t(property "Value" "{lib_id.split(':', 1)[1]}"
\t\t\t(at {fmt(x)} {fmt(value_y)} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t)
\t\t)
\t\t(property "Footprint" ""
\t\t\t(at {fmt(x)} {fmt(y)} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(hide yes)
\t\t\t)
\t\t)
\t\t(property "Datasheet" ""
\t\t\t(at {fmt(x)} {fmt(y)} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(hide yes)
\t\t\t)
\t\t)
\t\t(pin "1"
\t\t\t(uuid "{uid('powerpin', tag)}")
\t\t)
\t\t(instances
\t\t\t(project "{PROJECT}"
\t\t\t\t(path "/{ROOT_UUID}"
\t\t\t\t\t(reference "{reference}")
\t\t\t\t\t(unit 1)
\t\t\t\t)
\t\t\t)
\t\t)
\t)"""


def property_positions(part: Part) -> tuple[float, float, float, float, bool]:
    sym = part.symbol
    if part.ref == "A1":
        return part.x + 15.24, part.y - 27.94, part.x + 15.24, part.y - 27.94, True
    if sym.startswith("Device:R") or sym.startswith("Device:C"):
        return part.x + 3.81, part.y - 1.27, part.x + 3.81, part.y + 1.27, False
    if sym in ("Device:D", "Device:LED"):
        return part.x, part.y - 7.62, part.x, part.y - 5.08, False
    if sym in ("Switch:SW_Push", "Connector_Generic:Conn_01x04", "Connector_Generic:Conn_01x02"):
        return part.x, part.y - 12.7, part.x, part.y - 10.16, False
    if sym in ("Device:Buzzer", "Transistor_BJT:Q_NPN_EBC"):
        return part.x + 3.81, part.y - 1.27, part.x + 3.81, part.y + 1.27, False
    if sym == "Mechanical:MountingHole":
        return part.x + 2.54, part.y - 1.27, part.x + 2.54, part.y + 1.27, True
    return part.x - 10.16, part.y - 3.81, part.x - 10.16, part.y - 1.27, False


def symbol_instance(part: Part) -> str:
    pins = SYMBOL_PINS[part.symbol]
    ref_x, ref_y, val_x, val_y, hide_value = property_positions(part)
    value_hide = "\n\t\t\t\t(hide yes)" if hide_value else ""
    pin_entries = "\n".join(
        f'\t\t(pin "{number}"\n\t\t\t(uuid "{uid("pin", part.ref, number)}")\n\t\t)'
        for number in pins
    )
    return f"""\t(symbol
\t\t(lib_id "{part.symbol}")
\t\t(at {fmt(part.x)} {fmt(part.y)} 0)
\t\t(unit 1)
\t\t(exclude_from_sim no)
\t\t(in_bom {"no" if part.ref.startswith("H") else "yes"})
\t\t(on_board yes)
\t\t(dnp no)
\t\t(uuid "{uid('part', part.ref)}")
\t\t(property "Reference" "{part.ref}"
\t\t\t(at {fmt(ref_x)} {fmt(ref_y)} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(justify left)
\t\t\t)
\t\t)
\t\t(property "Value" "{esc(part.value)}"
\t\t\t(at {fmt(val_x)} {fmt(val_y)} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t){value_hide}
\t\t\t\t(justify left)
\t\t\t)
\t\t)
\t\t(property "Footprint" "{esc(FOOTPRINTS[part.ref])}"
\t\t\t(at {fmt(part.x)} {fmt(part.y)} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(hide yes)
\t\t\t)
\t\t)
\t\t(property "Datasheet" "~"
\t\t\t(at {fmt(part.x)} {fmt(part.y)} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(hide yes)
\t\t\t)
\t\t)
\t\t(property "Description" "{esc(part.description)}"
\t\t\t(at {fmt(part.x)} {fmt(part.y)} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(hide yes)
\t\t\t)
\t\t)
{pin_entries}
\t\t(instances
\t\t\t(project "{PROJECT}"
\t\t\t\t(path "/{ROOT_UUID}"
\t\t\t\t\t(reference "{part.ref}")
\t\t\t\t\t(unit 1)
\t\t\t\t)
\t\t\t)
\t\t)
\t)"""


def generate() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    BOM.parent.mkdir(parents=True, exist_ok=True)

    body: list[str] = []
    for part in PARTS:
        part.x, part.y = LAYOUT.get(part.ref, (part.x, part.y))
        part.x = snap(part.x)
        part.y = snap(part.y)
        body.append(symbol_instance(part))

    by_ref = {part.ref: part for part in PARTS}

    def pin(ref: str, number: str) -> tuple[float, float]:
        x, y, _ = pin_position(by_ref[ref], number)
        return x, y

    def add_path(points: list[tuple[float, float]], tag: str) -> None:
        for index, (a, b) in enumerate(zip(points, points[1:])):
            body.append(wire(a[0], a[1], b[0], b[1], f"{tag}:{index}"))

    def add_junction(x: float, y: float, tag: str) -> None:
        body.append(
            f"""\t(junction
\t\t(at {fmt(x)} {fmt(y)})
\t\t(diameter 0)
\t\t(color 0 0 0 0)
\t\t(uuid "{uid('junction', tag)}")
\t)"""
        )

    def add_power(lib_id: str, x: float, y: float, dx: float, dy: float, tag: str) -> None:
        ex, ey = snap(x + dx), snap(y + dy)
        body.append(wire(x, y, ex, ey, f"{tag}:wire"))
        body.append(power_symbol(lib_id, ex, ey, f"{tag}:symbol"))

    def add_label(name: str, x: float, y: float, tag: str, dx: float = 1.0) -> None:
        body.append(label(name, x, y, tag, dx))

    # ------------------------------------------------------------------
    # Arduino Nano: signal labels on the left edge, supply pins top/bottom.
    # ------------------------------------------------------------------
    nano_signals = {
        "5": "BUTTON",
        "9": "HAPTIC_PWM",
        "10": "LED_CMD",
        "11": "BUZZER_CMD",
        "12": "US_TRIG",
        "13": "US_ECHO",
    }
    for number, net in nano_signals.items():
        x, y = pin("A1", number)
        ex = snap(x - 3.81)
        body.append(wire(x, y, ex, y, f"A1:{number}:stub"))
        add_label(net, ex, y, f"A1:{number}", -1.0)

    # Join the two Nano ground pins visibly, then attach one GND symbol.
    g4x, g4y = pin("A1", "4")
    g29x, g29y = pin("A1", "29")
    gy = snap(g4y + 3.81)
    add_path([(g4x, g4y), (g4x, gy), (g29x, gy)], "A1:gnd")
    body.append(wire(g29x, g29y, g29x, gy, "A1:29:gnd"))
    add_junction(g29x, gy, "A1:gnd")
    add_power("power:GND", g29x, gy, 0, 3.81, "A1:gnd")

    # +5 V pin is on the Nano's top edge.
    p5x, p5y = pin("A1", "27")
    add_path([(p5x, p5y), (p5x, snap(p5y - 9.53))], "A1:5v")
    body.append(power_symbol("power:+5V", p5x, snap(p5y - 9.53), "A1:5v:symbol"))

    # ------------------------------------------------------------------
    # Ultrasonic connector J1.
    # ------------------------------------------------------------------
    j1_1 = pin("J1", "1")
    j1_2 = pin("J1", "2")
    j1_3 = pin("J1", "3")
    j1_4 = pin("J1", "4")
    add_path([j1_1, (snap(j1_1[0] - 7.62), j1_1[1]), (snap(j1_1[0] - 7.62), snap(j1_1[1] - 5.08))], "J1:1")
    body.append(power_symbol("power:+5V", snap(j1_1[0] - 7.62), snap(j1_1[1] - 5.08), "J1:1:symbol"))
    body.append(wire(*j1_2, snap(j1_2[0] - 5.08), j1_2[1], "J1:2:stub"))
    add_label("US_TRIG", snap(j1_2[0] - 5.08), j1_2[1], "J1:2", -1.0)
    body.append(wire(*j1_3, snap(j1_3[0] - 5.08), j1_3[1], "J1:3:stub"))
    add_label("US_ECHO", snap(j1_3[0] - 5.08), j1_3[1], "J1:3", -1.0)
    add_path([j1_4, (snap(j1_4[0] - 7.62), j1_4[1]), (snap(j1_4[0] - 7.62), snap(j1_4[1] + 5.08))], "J1:4")
    body.append(power_symbol("power:GND", snap(j1_4[0] - 7.62), snap(j1_4[1] + 5.08), "J1:4:symbol"))

    # ------------------------------------------------------------------
    # Mode button and its hardware debounce capacitor.
    # ------------------------------------------------------------------
    sw1_1 = pin("SW1", "1")
    sw1_2 = pin("SW1", "2")
    c3_1 = pin("C3", "1")
    c3_2 = pin("C3", "2")
    add_path([sw1_1, (sw1_1[0], c3_1[1]), c3_1], "SW1:1")
    add_label("BUTTON", *sw1_1, "SW1:1", -1.0)
    add_path([sw1_2, (sw1_2[0], c3_2[1]), c3_2], "SW1:2")
    body.append(wire(c3_2[0], c3_2[1], c3_2[0], snap(c3_2[1] + 5.08), "C3:2:gnd"))
    add_junction(c3_2[0], c3_2[1], "SW1:2")
    body.append(power_symbol("power:GND", c3_2[0], snap(c3_2[1] + 5.08), "C3:2:gnd:symbol"))

    # ------------------------------------------------------------------
    # Status LED: D7 -> R3 -> LED anode; LED cathode -> GND.
    # ------------------------------------------------------------------
    r3_1 = pin("R3", "1")
    r3_2 = pin("R3", "2")
    d2_1 = pin("D2", "1")
    d2_2 = pin("D2", "2")
    body.append(wire(r3_1[0], r3_1[1], r3_1[0], snap(r3_1[1] - 5.08), "R3:1:stub"))
    add_label("LED_CMD", r3_1[0], snap(r3_1[1] - 5.08), "R3:1", 1.0)
    add_path([r3_2, (snap(r3_2[0] - 15.24), r3_2[1]), (snap(r3_2[0] - 15.24), d2_2[1])], "R3:2")
    body.append(wire(snap(r3_2[0] - 15.24), r3_2[1], snap(r3_2[0] - 15.24), snap(r3_2[1] + 5.08), "R3:2:label"))
    add_junction(snap(r3_2[0] - 15.24), r3_2[1], "LED_A")
    add_label("LED_A", snap(r3_2[0] - 15.24), snap(r3_2[1] + 5.08), "R3:2", -1.0)
    body.append(wire(snap(r3_2[0] - 15.24), d2_2[1], d2_2[0], d2_2[1], "R3:2:led"))
    body.append(wire(d2_1[0], d2_1[1], snap(d2_1[0] - 5.08), d2_1[1], "D2:1:gnd"))
    body.append(power_symbol("power:GND", snap(d2_1[0] - 5.08), d2_1[1], "D2:1:gnd:symbol"))

    # ------------------------------------------------------------------
    # Motor driver: base resistor, pull-down, NPN switch, flyback diode.
    # ------------------------------------------------------------------
    r1_1 = pin("R1", "1")
    r1_2 = pin("R1", "2")
    q_b = pin("Q1", "2")
    q_c = pin("Q1", "3")
    q_e = pin("Q1", "1")
    r2_1 = pin("R2", "1")
    r2_2 = pin("R2", "2")
    j2_1 = pin("J2", "1")
    j2_2 = pin("J2", "2")
    d1_1 = pin("D1", "1")
    d1_2 = pin("D1", "2")

    add_label("HAPTIC_PWM", *r1_1, "R1:1", -1.0)
    add_path([r1_2, (r1_2[0], q_b[1]), q_b], "R1:2:base")
    body.append(wire(r2_1[0], q_b[1], r2_1[0], r2_1[1], "R2:1:base"))
    add_junction(r2_1[0], q_b[1], "Q_BASE")
    add_label("Q_BASE", r1_2[0], q_b[1], "Q_BASE", -1.0)

    body.append(wire(r2_2[0], r2_2[1], r2_2[0], snap(r2_2[1] + 5.08), "R2:2:gnd"))
    body.append(power_symbol("power:GND", r2_2[0], snap(r2_2[1] + 5.08), "R2:2:gnd:symbol"))
    body.append(wire(q_e[0], q_e[1], q_e[0], snap(q_e[1] + 5.08), "Q1:1:gnd"))
    body.append(power_symbol("power:GND", q_e[0], snap(q_e[1] + 5.08), "Q1:1:gnd:symbol"))

    add_power("power:+5V", *j2_1, -5.08, 0, "J2:1")
    add_path([j2_2, (snap(j2_2[0] - 10.16), j2_2[1]), (snap(j2_2[0] - 10.16), q_c[1]), q_c], "J2:2:motor")
    add_label("MOTOR_NEG", snap(j2_2[0] - 10.16), j2_2[1], "J2:2", -1.0)
    body.append(wire(d1_2[0], d1_2[1], snap(j2_2[0] - 10.16), d1_2[1], "D1:2:motor"))
    add_junction(snap(j2_2[0] - 10.16), d1_2[1], "MOTOR_NEG")
    add_power("power:+5V", *d1_1, -5.08, 0, "D1:1")

    # Motor-supply decoupling.
    for ref in ("C1", "C2"):
        c1 = pin(ref, "1")
        c2 = pin(ref, "2")
        add_power("power:+5V", *c1, 0, -6.35, f"{ref}:1")
        add_power("power:GND", *c2, 0, 6.35, f"{ref}:2")

    # ------------------------------------------------------------------
    # Audio warning: D8 -> R4 -> buzzer; buzzer return -> GND.
    # ------------------------------------------------------------------
    r4_1 = pin("R4", "1")
    r4_2 = pin("R4", "2")
    bz1_1 = pin("BZ1", "1")
    bz1_2 = pin("BZ1", "2")
    add_label("BUZZER_CMD", *r4_1, "R4:1", -1.0)
    add_path([r4_2, (snap(r4_2[0] + 20.32), r4_2[1]), (snap(r4_2[0] + 20.32), bz1_1[1])], "R4:2")
    body.append(wire(snap(r4_2[0] + 20.32), r4_2[1], snap(r4_2[0] + 20.32), snap(r4_2[1] + 5.08), "R4:2:label"))
    add_junction(snap(r4_2[0] + 20.32), r4_2[1], "BUZZER_A")
    add_label("BUZZER_A", snap(r4_2[0] + 20.32), snap(r4_2[1] + 5.08), "R4:2", -1.0)
    body.append(wire(snap(r4_2[0] + 20.32), bz1_1[1], bz1_1[0], bz1_1[1], "R4:2:buzzer"))
    body.append(wire(bz1_2[0], bz1_2[1], snap(bz1_2[0] - 12.7), bz1_2[1], "BZ1:2:gnd"))
    body.append(wire(snap(bz1_2[0] - 12.7), bz1_2[1], snap(bz1_2[0] - 12.7), snap(bz1_2[1] + 7.62), "BZ1:2:gnd:drop"))
    body.append(power_symbol("power:GND", snap(bz1_2[0] - 12.7), snap(bz1_2[1] + 7.62), "BZ1:2:gnd:symbol"))

    # ------------------------------------------------------------------
    # Power source: the Nano's USB VBUS is the only 5 V source. Its 5V pin
    # is an output; the +5V net is driven there, so only GND needs a flag.
    # ------------------------------------------------------------------
    body.append(note("5V SOURCE: NANO USB VBUS", 215, 44, "pwr:source"))
    body.append(note("USB -> Nano Schottky -> 5V pin -> +5V", 215, 48, "pwr:path"))
    body.append(note("5V pin is OUTPUT; no external 5V input", 215, 52, "pwr:output"))
    body.append(note("Do not backfeed while USB connected", 215, 56, "pwr:backfeed"))
    body.append(note("GND PWR_FLAG: ERC reference only", 215, 60, "pwr:flag"))
    body.append(power_symbol("power:GND", snap(250), snap(65), "pwr:gnd"))
    body.append(power_symbol("power:PWR_FLAG", snap(235), snap(65), "pwrflag:gnd"))
    body.append(wire(snap(235), snap(65), snap(250), snap(65), "pwr:gnd:link"))

    # Every unused Nano pin gets an explicit no-connect marker.
    a1 = by_ref["A1"]
    used_nano_pins = set(nano_signals) | {"4", "27", "29"}
    for number in SYMBOL_PINS[a1.symbol]:
        if number not in used_nano_pins:
            x, y, _ = pin_position(a1, number)
            body.append(no_connect(x, y, f"A1:{number}"))

    for text, hx, hy in HEADINGS:
        body.append(heading(text, hx, hy))
    body.append(note("BUTTON: D2 = INPUT_PULLUP (internal)", 25, 128, "button:pullup"))
    body.append(note("SW1 to GND; C3 = 100 nF debounce", 25, 132, "button:debounce"))
    body.append(note("D1 1N4007: 1A avg / 30A surge", 95, 158, "diode:ratings"))
    body.append(note("PWM 976.6 Hz; trr <=30 us << 1.024 ms", 95, 162, "diode:pwm"))

    title = """\t(text "EchoCane carrier board — virtual reconstruction"
\t\t(at 30 20 0)
\t\t(effects
\t\t\t(font
\t\t\t\t(size 3 3)
\t\t\t\t(bold yes)
\t\t\t)
\t\t\t(justify left bottom)
\t\t)
\t\t(uuid "e7c4e1a3-21a1-4df2-9f3e-2a1d8f4a1c11")
\t)
\t(text "Experimental supplementary aid. Not a validated safety device, not a replacement for a conventional mobility cane."
\t\t(at 30 26 0)
\t\t(effects
\t\t\t(font
\t\t\t\t(size 1.8 1.8)
\t\t\t)
\t\t\t(justify left bottom)
\t\t)
\t\t(uuid "e7c4e1a3-21a1-4df2-9f3e-2a1d8f4a1c12")
\t)
\t(text "Pin map: D2=BUTTON  D6=HAPTIC_PWM  D7=LED_CMD  D8=BUZZER_CMD  D9=US_TRIG  D10=US_ECHO  5V=+5V  GND=GND"
\t\t(at 30 31 0)
\t\t(effects
\t\t\t(font
\t\t\t\t(size 1.5 1.5)
\t\t\t)
\t\t\t(justify left bottom)
\t\t)
\t\t(uuid "e7c4e1a3-21a1-4df2-9f3e-2a1d8f4a1c13")
\t)
"""

    lib_symbols = "\n".join(
        "\n".join("\t\t" + line if line else line for line in SYMBOL_BLOCKS[lib_id].splitlines())
        for lib_id in SYMBOL_BLOCKS
    )

    schematic = f"""(kicad_sch
\t(version 20250114)
\t(generator "eeschema")
\t(generator_version "10.0")
\t(uuid "{ROOT_UUID}")
\t(paper "{PAPER}")
\t(title_block
\t\t(title "EchoCane Carrier Board")
\t\t		(date "2026-11-16")
\t\t(rev "0.1")
\t\t(company "EchoCane virtual reconstruction")
\t\t(comment 1 "Experimental prototype — not physically validated")
\t)
\t(lib_symbols
{lib_symbols}
\t)
{title}
{chr(10).join(body)}
\t(sheet_instances
\t\t(path "/"
\t\t\t(page "1")
\t\t)
\t)
\t(embedded_fonts no)
)
"""
    SCHEMATIC.write_text(schematic, encoding="utf-8")

    with BOM.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Reference", "Value", "Footprint", "Description", "Qty"])
        for part in PARTS:
            if part.ref.startswith("H"):
                continue
            writer.writerow([part.ref, part.value, FOOTPRINTS[part.ref], part.description, 1])

    print(f"wrote {SCHEMATIC.relative_to(ROOT)} and {BOM.relative_to(ROOT)}")


if __name__ == "__main__":
    generate()
