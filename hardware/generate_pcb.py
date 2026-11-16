#!/usr/bin/env python3
"""Generate the EchoCane carrier PCB from the exported KiCad netlist.

Run inside the KiCad container:

  docker run --rm -v "$PWD:/work" -w /work kicad/kicad:10.0 \
      python3 hardware/generate_pcb.py

The board is a two-layer through-hole carrier. All signal routing is explicit
in this file; the bottom copper is a GND zone. Pad net assignment comes from
EchoCane.net so the PCB cannot silently disagree with the schematic.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parents[1]
NETLIST = ROOT / "hardware" / "kicad" / "EchoCane.net"
BOARD_PATH = ROOT / "hardware" / "kicad" / "EchoCane.kicad_pcb"

BOARD_W = 100.0
BOARD_H = 85.0

PLACEMENT = {
    # ref: (x, y, rotation)
    "A1": (30, 10, 0),
    "J1": (8, 55, 0),
    "J2": (88, 60, 0),
    "Q1": (66, 62, 0),
    "R1": (50, 60, 0),
    "R2": (50, 68, 0),
    "D1": (70, 55, 0),
    "C1": (80, 45, 0),
    "C2": (90, 50, 0),
    "SW1": (8, 30, 0),
    "C3": (18, 36, 0),
    "R3": (35, 62, 0),
    "D2": (35, 75, 0),
    "R4": (60, 20, 0),
    "BZ1": (72, 12, 0),
}

MOUNTING_HOLES = [(5, 5), (95, 5), (5, 80), (95, 80)]


def mm(value: float) -> int:
    return pcbnew.FromMM(value)


def point(x: float, y: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I_MM(x, y)


def balanced_blocks(text: str, marker: str) -> list[str]:
    blocks: list[str] = []
    start = 0
    while True:
        index = text.find(marker, start)
        if index < 0:
            return blocks
        depth = 0
        in_string = False
        escaped = False
        for i in range(index, len(text)):
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
                        blocks.append(text[index : i + 1])
                        start = i + 1
                        break
        else:
            return blocks


def parse_netlist() -> tuple[dict[str, dict[str, str]], dict[str, list[tuple[str, str]]]]:
    text = NETLIST.read_text(encoding="utf-8")
    components: dict[str, dict[str, str]] = {}
    for block in balanced_blocks(text, "(comp\n"):
        ref = re.search(r'\(ref "([^"]+)"\)', block)
        value = re.search(r'\(value "([^"]*)"\)', block)
        footprint = re.search(r'\(footprint "([^"]*)"\)', block)
        if not (ref and value and footprint):
            raise SystemExit(f"malformed component block: {block[:80]}")
        desc = re.search(r'\(description "([^"]*)"\)', block)
        components[ref.group(1)] = {
            "value": value.group(1),
            "footprint": footprint.group(1),
            "description": desc.group(1) if desc else "",
        }

    nets: dict[str, list[tuple[str, str]]] = {}
    net_section = text[text.find("(nets") :]
    for block in balanced_blocks(net_section, "(net\n"):
        name_match = re.search(r'\(name "([^"]+)"\)', block)
        if not name_match:
            continue
        name = name_match.group(1)
        nodes = [
            (m.group(1), m.group(2))
            for m in re.finditer(
                r'\(node\s+\(ref "([^"]+)"\)\s+\(pin "([^"]+)"\)', block
            )
        ]
        nets[name] = nodes
    return components, nets


def footprint_path(lib_id: str) -> tuple[str, str]:
    lib, name = lib_id.split(":", 1)
    return f"/usr/share/kicad/footprints/{lib}.pretty", name


def add_footprint(board, ref: str, value: str, description: str, lib_id: str, x: float, y: float, rotation: float):
    path, name = footprint_path(lib_id)
    fp = pcbnew.FootprintLoad(path, name)
    if fp is None:
        raise SystemExit(f"cannot load footprint {lib_id}")
    fp.SetPosition(point(x, y))
    if rotation:
        fp.SetOrientationDegrees(rotation)
    fp.SetReference(ref)
    fp.SetValue(value)
    fp.SetFPIDAsString(lib_id)
    if description:
        fp.GetField("Description").SetText(description)
    board.Add(fp)
    return fp


def add_track(board, net, layer, width: float, start, end):
    track = pcbnew.PCB_TRACK(board)
    track.SetStart(point(*start))
    track.SetEnd(point(*end))
    track.SetWidth(mm(width))
    track.SetLayer(layer)
    track.SetNet(net)
    board.Add(track)


def add_via(board, net, x: float, y: float):
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(point(x, y))
    via.SetWidth(mm(0.8))
    via.SetDrill(mm(0.4))
    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    via.SetNet(net)
    board.Add(via)


def add_edge(board, x1, y1, x2, y2):
    segment = pcbnew.PCB_SHAPE(board)
    segment.SetShape(pcbnew.SHAPE_T_SEGMENT)
    segment.SetStart(point(x1, y1))
    segment.SetEnd(point(x2, y2))
    segment.SetLayer(pcbnew.Edge_Cuts)
    segment.SetWidth(mm(0.1))
    board.Add(segment)


def add_silk_text(board, text: str, x: float, y: float, size: float = 1.5, layer=pcbnew.F_SilkS):
    label = pcbnew.PCB_TEXT(board)
    label.SetText(text)
    label.SetPosition(point(x, y))
    label.SetLayer(layer)
    label.SetTextSize(pcbnew.VECTOR2I_MM(size, size))
    label.SetTextThickness(mm(0.25))
    label.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
    label.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
    board.Add(label)


def add_gnd_zone(board, gnd_net):
    zone = pcbnew.ZONE(board)
    zone.SetLayer(pcbnew.B_Cu)
    zone.SetNet(gnd_net)
    zone.SetLocalClearance(mm(0.3))
    zone.SetMinThickness(mm(0.25))
    zone.SetThermalReliefGap(mm(0.3))
    zone.SetThermalReliefSpokeWidth(mm(0.6))
    outline = zone.Outline()
    outline.NewOutline()
    inset = 0.6
    outline.Append(point(inset, inset).x, point(inset, inset).y)
    outline.Append(point(BOARD_W - inset, inset).x, point(BOARD_W - inset, inset).y)
    outline.Append(point(BOARD_W - inset, BOARD_H - inset).x, point(BOARD_W - inset, BOARD_H - inset).y)
    outline.Append(point(inset, BOARD_H - inset).x, point(inset, BOARD_H - inset).y)
    board.Add(zone)
    return zone


def main() -> int:
    components, nets = parse_netlist()

    board = pcbnew.CreateEmptyBoard()
    board.SetCopperLayerCount(2)
    design = board.GetDesignSettings()
    design.SetBoardThickness(mm(1.6))
    title = board.GetTitleBlock()
    title.SetTitle("EchoCane Carrier Board")
    title.SetRevision("0.1")
    title.SetDate("2026-11-16")
    title.SetCompany("EchoCane virtual reconstruction")
    title.SetComment(1, "Experimental prototype - not physically validated")

    net_items = {}
    for name in sorted(nets):
        net = pcbnew.NETINFO_ITEM(board, name)
        board.Add(net)
        net_items[name] = net

    def net_of(name: str):
        return net_items.get(name) or net_items.get("/" + name)

    footprints = {}
    for ref, (x, y, rotation) in PLACEMENT.items():
        if ref not in components:
            raise SystemExit(f"{ref} missing from netlist")
        info = components[ref]
        footprints[ref] = add_footprint(
            board, ref, info["value"], info["description"], info["footprint"], x, y, rotation
        )

    for ref, hole_x, hole_y in (
        ("H1", 5, 5),
        ("H2", 95, 5),
        ("H3", 5, 80),
        ("H4", 95, 80),
    ):
        hole = add_footprint(
            board,
            ref,
            "MountingHole",
            "M3 PCB mounting hole",
            "MountingHole:MountingHole_3.2mm_M3",
            hole_x,
            hole_y,
            0,
        )
        hole.SetAttributes(hole.GetAttributes() | pcbnew.FP_EXCLUDE_FROM_BOM)

    # Assign pad nets from the schematic netlist.
    assigned = 0
    for net_name, nodes in nets.items():
        net = net_items[net_name]
        for ref, pin in nodes:
            fp = footprints.get(ref)
            if fp is None:
                continue
            pads = [pad for pad in fp.Pads() if pad.GetNumber() == pin]
            if not pads:
                raise SystemExit(f"net {net_name}: {ref} has no pad {pin}")
            for pad in pads:
                pad.SetNet(net)
                assigned += 1

    def pad(ref: str, pin: str) -> tuple[float, float]:
        matches = [p for p in footprints[ref].Pads() if p.GetNumber() == pin]
        if not matches:
            raise SystemExit(f"{ref} pad {pin} not found")
        pos = matches[0].GetPosition()
        return pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y)

    f_cu = pcbnew.F_Cu
    b_cu = pcbnew.B_Cu

    # Signal routing, top copper. Waypoints are chosen to avoid pads of other
    # nets; the DRC is the final check.
    d9 = pad("A1", "12")
    d10 = pad("A1", "13")
    d6 = pad("A1", "9")
    d7 = pad("A1", "10")
    d8 = pad("A1", "11")
    d2 = pad("A1", "5")
    j1_2, j1_3 = pad("J1", "2"), pad("J1", "3")
    j1_1, j1_4 = pad("J1", "1"), pad("J1", "4")
    j2_1, j2_2 = pad("J2", "1"), pad("J2", "2")
    r1_1, r1_2 = pad("R1", "1"), pad("R1", "2")
    r2_1, r2_2 = pad("R2", "1"), pad("R2", "2")
    q1_e, q1_b, q1_c = pad("Q1", "1"), pad("Q1", "2"), pad("Q1", "3")
    d1_k, d1_a = pad("D1", "1"), pad("D1", "2")
    c1_1, c1_2 = pad("C1", "1"), pad("C1", "2")
    c2_1, c2_2 = pad("C2", "1"), pad("C2", "2")
    # SW1 has two pads per electrical contact; route to the right-hand pad.
    sw1_1, sw1_2 = (14.5, 30.0), (14.5, 34.5)
    c3_1, c3_2 = pad("C3", "1"), pad("C3", "2")
    r3_1, r3_2 = pad("R3", "1"), pad("R3", "2")
    d2_1, d2_2 = pad("D2", "1"), pad("D2", "2")
    r4_1, r4_2 = pad("R4", "1"), pad("R4", "2")
    bz1_1, bz1_2 = pad("BZ1", "1"), pad("BZ1", "2")
    a1_5v = pad("A1", "27")

    # US_TRIG and US_ECHO: two parallel left-side channels.
    add_track(board, net_of("US_TRIG"), f_cu, 0.5, j1_2, (20, j1_2[1]))
    add_track(board, net_of("US_TRIG"), f_cu, 0.5, (20, j1_2[1]), (20, d9[1]))
    add_track(board, net_of("US_TRIG"), f_cu, 0.5, (20, d9[1]), d9)

    add_track(board, net_of("US_ECHO"), f_cu, 0.5, j1_3, (24, j1_3[1]))
    add_track(board, net_of("US_ECHO"), f_cu, 0.5, (24, j1_3[1]), (24, d10[1]))
    add_track(board, net_of("US_ECHO"), f_cu, 0.5, (24, d10[1]), d10)

    # BUTTON: D2 -> button and hardware debounce capacitor.
    add_track(board, net_of("BUTTON"), f_cu, 0.5, d2, (26, d2[1]))
    add_track(board, net_of("BUTTON"), f_cu, 0.5, (26, d2[1]), (26, 28))
    add_track(board, net_of("BUTTON"), f_cu, 0.5, (26, 28), (18, 28))
    add_track(board, net_of("BUTTON"), f_cu, 0.5, (18, 28), c3_1)
    add_track(board, net_of("BUTTON"), f_cu, 0.5, c3_1, (18, 32))
    add_track(board, net_of("BUTTON"), f_cu, 0.5, (18, 32), (14.5, 32))
    add_track(board, net_of("BUTTON"), f_cu, 0.5, (14.5, 32), sw1_1)
    add_track(board, net_of("BUTTON"), f_cu, 0.5, sw1_1, (8, 30))

    # HAPTIC_PWM: route inside the Nano pin rows, then down to the base resistor.
    add_track(board, net_of("HAPTIC_PWM"), f_cu, 0.5, d6, (42, d6[1]))
    add_track(board, net_of("HAPTIC_PWM"), f_cu, 0.5, (42, d6[1]), (42, r1_1[1]))
    add_track(board, net_of("HAPTIC_PWM"), f_cu, 0.5, (42, r1_1[1]), r1_1)

    # LED command and LED anode.
    add_track(board, net_of("LED_CMD"), f_cu, 0.5, d7, (33, d7[1]))
    add_track(board, net_of("LED_CMD"), f_cu, 0.5, (33, d7[1]), (33, r3_1[1]))
    add_track(board, net_of("LED_CMD"), f_cu, 0.5, (33, r3_1[1]), r3_1)
    add_track(board, net_of("LED_A"), f_cu, 0.5, r3_2, (42.62, 75))
    add_track(board, net_of("LED_A"), f_cu, 0.5, (42.62, 75), d2_2)

    # Buzzer command: bottom-layer route under the Nano, above the +5 V bus.
    add_track(board, net_of("BUZZER_CMD"), b_cu, 0.5, d8, (28, d8[1]))
    add_track(board, net_of("BUZZER_CMD"), b_cu, 0.5, (28, d8[1]), (28, 6))
    add_track(board, net_of("BUZZER_CMD"), b_cu, 0.5, (28, 6), (58, 6))
    add_track(board, net_of("BUZZER_CMD"), b_cu, 0.5, (58, 6), (58, 20))
    add_track(board, net_of("BUZZER_CMD"), b_cu, 0.5, (58, 20), r4_1)
    add_track(board, net_of("BUZZER_A"), f_cu, 0.5, r4_2, (70, 20))
    add_track(board, net_of("BUZZER_A"), f_cu, 0.5, (70, 20), (70, 12))
    add_track(board, net_of("BUZZER_A"), f_cu, 0.5, (70, 12), bz1_1)

    # Base network and motor low side.
    add_track(board, net_of("Q_BASE"), f_cu, 0.5, r1_2, (57.62, 58))
    add_track(board, net_of("Q_BASE"), f_cu, 0.5, (57.62, 58), (67.27, 58))
    add_track(board, net_of("Q_BASE"), f_cu, 0.5, (67.27, 58), q1_b)
    add_track(board, net_of("Q_BASE"), f_cu, 0.5, (60, 58), (60, 72))
    add_track(board, net_of("Q_BASE"), f_cu, 0.5, (60, 72), (50, 72))
    add_track(board, net_of("Q_BASE"), f_cu, 0.5, (50, 72), r2_1)

    add_track(board, net_of("MOTOR_NEG"), f_cu, 0.8, q1_c, (72, q1_c[1]))
    add_track(board, net_of("MOTOR_NEG"), f_cu, 0.8, (72, q1_c[1]), (72, 55))
    add_track(board, net_of("MOTOR_NEG"), f_cu, 0.8, (72, 55), d1_a)
    add_track(board, net_of("MOTOR_NEG"), f_cu, 0.8, (72, q1_c[1]), (88, q1_c[1]))
    add_track(board, net_of("MOTOR_NEG"), f_cu, 0.8, (88, q1_c[1]), j2_2)

    # +5V distribution on the bottom layer. The GND plane clears around it.
    add_track(board, net_of("+5V"), b_cu, 0.8, a1_5v, (47, a1_5v[1]))
    add_track(board, net_of("+5V"), b_cu, 0.8, (47, a1_5v[1]), (47, 52))
    add_track(board, net_of("+5V"), b_cu, 0.8, (47, 52), (8, 52))
    add_track(board, net_of("+5V"), b_cu, 0.8, (8, 52), j1_1)
    add_track(board, net_of("+5V"), b_cu, 0.8, (47, 52), (88, 52))
    add_track(board, net_of("+5V"), b_cu, 0.8, (88, 52), j2_1)
    add_track(board, net_of("+5V"), b_cu, 0.8, (70, 52), d1_k)
    add_track(board, net_of("+5V"), b_cu, 0.8, (80, 52), c1_1)
    add_track(board, net_of("+5V"), b_cu, 0.8, (88, 52), (90, 52))
    add_track(board, net_of("+5V"), b_cu, 0.8, (90, 52), c2_1)

    # Board outline, mounting holes, and legend.
    add_edge(board, 0, 0, BOARD_W, 0)
    add_edge(board, BOARD_W, 0, BOARD_W, BOARD_H)
    add_edge(board, BOARD_W, BOARD_H, 0, BOARD_H)
    add_edge(board, 0, BOARD_H, 0, 0)

    add_silk_text(board, "ECHOCANE v0.1", 50, 80, 2.2)
    add_silk_text(board, "EXPERIMENTAL AID - NOT A VALIDATED SAFETY DEVICE", 50, 3, 0.9)
    add_silk_text(board, "HC-SR04", 8, 49, 1.2)
    add_silk_text(board, "MOTOR", 88, 56, 1.2)
    add_silk_text(board, "MODE", 8, 26, 1.2)
    add_silk_text(board, "BUZZER", 84, 20, 1.2)
    add_silk_text(board, "+5V  GND", 92, 40, 0.9)
    add_silk_text(board, "D9 TRIG / D10 ECHO", 17, 45, 0.8)

    # Keep reference fields clear of neighbouring silkscreen and pads.
    footprints["C1"].Reference().SetPosition(point(84, 42))
    footprints["C2"].Reference().SetPosition(point(84, 54))
    footprints["Q1"].Reference().SetPosition(point(70, 66))
    footprints["D1"].Reference().SetPosition(point(64, 52))
    footprints["SW1"].Reference().SetPosition(point(16, 26))

    gnd_net = net_of("GND")
    add_gnd_zone(board, gnd_net)

    pcbnew.SaveBoard(str(BOARD_PATH), board)
    print(f"wrote {BOARD_PATH.relative_to(ROOT)}: {len(footprints)} footprints, {assigned} pad nets")
    for ref in PLACEMENT:
        for p in footprints[ref].Pads():
            if p.GetNumber() in ("1", "2", "3", "4"):
                pos = p.GetPosition()
                print(ref, p.GetNumber(), round(pcbnew.ToMM(pos.x), 2), round(pcbnew.ToMM(pos.y), 2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
