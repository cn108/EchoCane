#!/usr/bin/env python3
"""Generate the EchoCane KiCad schematic and BOM.

Run inside the KiCad container so the system symbol libraries are available:

  docker run --rm -v "$PWD:/work" -w /work kicad/kicad:10.0 \
      python3 hardware/generate_schematic.py

The generator embeds only the symbols it uses, attaches every used pin to a
short wire stub with a net label (or a power symbol), and places no-connect
flags on unused Nano pins. KiCad ERC remains the authority on connectivity.
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
PAPER = "A3"

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
    "A1": (210, 150),
    "J1": (55, 80),
    "J2": (55, 125),
    "Q1": (350, 160),
    "R1": (310, 160),
    "R2": (330, 185),
    "D1": (365, 140),
    "C1": (315, 220),
    "C2": (335, 220),
    "SW1": (70, 180),
    "C3": (95, 200),
    "R3": (70, 230),
    "D2": (95, 245),
    "R4": (320, 80),
    "BZ1": (360, 80),
    "H1": (250, 250),
    "H2": (270, 250),
    "H3": (250, 270),
    "H4": (270, 270),
}

HEADINGS = [
    ("ULTRASONIC SENSOR", 30, 60),
    ("MODE INPUT", 30, 160),
    ("STATUS LED", 30, 215),
    ("MOTOR DRIVER", 290, 120),
    ("AUDIO WARNING", 300, 60),
    ("SUPPLY DECOUPLING", 290, 205),
    ("ARDUINO NANO", 170, 110),
    ("POWER ENTRY", 240, 215),
    ("MECHANICAL", 240, 240),
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


def no_connect(x: float, y: float, tag: str) -> str:
    return f"""\t(no_connect
\t\t(at {fmt(x)} {fmt(y)})
\t\t(uuid "{uid('nc', tag)}")
\t)"""


def power_symbol(lib_id: str, x: float, y: float, tag: str) -> str:
    ref_prefix = "#PWR" if lib_id != "power:PWR_FLAG" else "#FLG"
    return f"""\t(symbol
\t\t(lib_id "{lib_id}")
\t\t(at {fmt(x)} {fmt(y)} 0)
\t\t(unit 1)
\t\t(exclude_from_sim no)
\t\t(in_bom no)
\t\t(on_board no)
\t\t(dnp no)
\t\t(uuid "{uid('power', tag)}")
\t\t(property "Reference" "{ref_prefix}"
\t\t\t(at {fmt(x)} {fmt(y - 2.54)} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(hide yes)
\t\t\t)
\t\t)
\t\t(property "Value" "{lib_id.split(':', 1)[1]}"
\t\t\t(at {fmt(x)} {fmt(y + 3.81)} 0)
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
\t\t\t\t\t(reference "{ref_prefix}{abs(hash(tag)) % 1000}")
\t\t\t\t\t(unit 1)
\t\t\t\t)
\t\t\t)
\t\t)
\t)"""


def property_positions(part: Part) -> tuple[float, float, float, float, bool]:
    sym = part.symbol
    if part.ref == "A1":
        return part.x - 22, part.y - 28, part.x - 22, part.y - 28, True
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
        for number, net in part.nets.items():
            if net is None:
                continue
            x, y, angle = pin_position(part, number)
            dx, dy = outward(angle)
            ex, ey = x + dx * 3.81, y + dy * 3.81
            body.append(wire(x, y, ex, ey, f"{part.ref}:{number}"))
            if part.ref == "A1" and number in ("4", "29"):
                continue
            body.append(label(net, ex, ey, f"{part.ref}:{number}", dx))

        # Every unused Nano pin gets an explicit no-connect marker.
        if part.ref == "A1":
            for number in SYMBOL_PINS[part.symbol]:
                if number not in part.nets:
                    x, y, _ = pin_position(part, number)
                    body.append(no_connect(x, y, f"A1:{number}"))

    # The Nano has two adjacent ground pins. Join them to one label so the
    # schematic remains readable; this is electrically the same GND net.
    a1 = next(part for part in PARTS if part.ref == "A1")
    g1 = pin_position(a1, "4")
    g2 = pin_position(a1, "29")
    gy = snap(g1[1] + 3.81)
    body.append(wire(g1[0], g1[1], g1[0], gy, "A1:4:gnd"))
    body.append(wire(g1[0], gy, g2[0], gy, "A1:gnd:link"))
    body.append(wire(g2[0], g2[1], g2[0], gy, "A1:29:gnd"))
    body.append(label("GND", g2[0], gy, "A1:gnd", 1.0))

    for text, hx, hy in HEADINGS:
        body.append(heading(text, hx, hy))

    # Power entry: explicit +5V/GND sources plus PWR_FLAGs for ERC.
    px, py = snap(250), snap(230)
    body.append(power_symbol("power:+5V", px, py, "pwr:+5v"))
    body.append(wire(px, py, px, py + 3.81, "pwr:+5v:stub"))
    body.append(label("+5V", px, py + 3.81, "pwr:+5v:label", 1.0))
    gx = snap(270)
    body.append(power_symbol("power:GND", gx, py, "pwr:gnd"))
    body.append(power_symbol("power:PWR_FLAG", gx, py - 7.62, "pwrflag:gnd"))
    body.append(wire(gx, py, gx, py - 7.62, "pwr:gnd:link"))

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
