#!/usr/bin/env python3
"""Render the ngspice driver waveform as a dependency-free SVG."""

from __future__ import annotations

import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
WAVEFORM = HERE / "driver-waveform.txt"
SVG = HERE.parents[1] / "images" / "driver-waveform.svg"
CSV = HERE / "driver-waveform-sampled.csv"

WIDTH = 900
HEIGHT = 620
LEFT = 80
RIGHT = 30
TOP = 60
PANEL_H = 220
GAP = 70
T_MAX_MS = 30.0


def load_rows() -> list[list[float]]:
    rows: list[list[float]] = []
    for line in WAVEFORM.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) >= 6:
            rows.append([float(value) for value in parts[:6]])
    return [row for row in rows if row[0] * 1000 <= T_MAX_MS]


def sx(t_ms: float) -> float:
    return LEFT + (WIDTH - LEFT - RIGHT) * t_ms / T_MAX_MS


def sy(value: float, low: float, high: float, top: float) -> float:
    return top + PANEL_H * (high - value) / (high - low)


def polyline(rows: list[list[float]], index: int, low: float, high: float, top: float) -> str:
    points = " ".join(
        f"{sx(row[0] * 1000):.1f},{sy(row[index], low, high, top):.1f}" for row in rows
    )
    return f'<polyline points="{points}" fill="none" stroke-width="2.2"/>'


def main() -> int:
    rows = load_rows()
    if not rows:
        raise SystemExit("no waveform rows; run ngspice first")

    step = max(1, len(rows) // 700)
    sampled = rows[::step]
    with CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["time_ms", "drive_V", "base_V", "collector_V", "motor_mA", "diode_mA"])
        for row in sampled:
            writer.writerow(
                [
                    f"{row[0] * 1000:.4f}",
                    f"{row[1]:.4f}",
                    f"{row[2]:.4f}",
                    f"{row[3]:.4f}",
                    f"{row[4] * 1000:.4f}",
                    f"{row[5] * 1000:.4f}",
                ]
            )

    plot_rows = sampled[:: max(1, len(sampled) // 450)]
    top1 = TOP
    top2 = TOP + PANEL_H + GAP
    v_low, v_high = 0.0, 6.0
    i_low, i_high = -10.0, 110.0

    ticks = []
    for t in range(0, 31, 5):
        x = sx(t)
        ticks.append(
            f'<line x1="{x:.1f}" y1="{top1}" x2="{x:.1f}" y2="{top2 + PANEL_H}" '
            'stroke="#d9dee7" stroke-width="1"/>'
            f'<text x="{x:.1f}" y="{top2 + PANEL_H + 24}" text-anchor="middle" '
            'font-family="Arial, sans-serif" font-size="12" fill="#4a5568">{t} ms</text>'
        )

    def y_ticks(top: float, low: float, high: float, unit: str, decimals: int) -> str:
        output = []
        for i in range(6):
            value = low + (high - low) * i / 5
            y = sy(value, low, high, top)
            output.append(
                f'<line x1="{LEFT}" y1="{y:.1f}" x2="{WIDTH - RIGHT}" y2="{y:.1f}" '
                'stroke="#edf0f5" stroke-width="1"/>'
                f'<text x="{LEFT - 10}" y="{y + 4:.1f}" text-anchor="end" '
                f'font-family="Arial, sans-serif" font-size="12" fill="#4a5568">'
                f"{value:.{decimals}f} {unit}</text>"
            )
        return "".join(output)

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">
<rect width="100%" height="100%" fill="#ffffff"/>
<style>
  .axis {{ stroke: #718096; stroke-width: 1.2; }}
  .collector {{ stroke: #c53030; }}
  .motor {{ stroke: #2f855a; }}
  .diode {{ stroke: #b7791f; }}
</style>
<text x="{LEFT}" y="32" font-family="Arial, sans-serif" font-size="20" font-weight="bold" fill="#1a202c">EchoCane motor driver — ngspice transient</text>
<text x="{LEFT}" y="50" font-family="Arial, sans-serif" font-size="13" fill="#4a5568">20 ms drive pulse, 47 Ω / 10 mH motor model, 1 kΩ base resistor. Electrical model only; not tactile validation.</text>
{''.join(ticks)}
{y_ticks(top1, v_low, v_high, 'V', 0)}
{y_ticks(top2, i_low, i_high, 'mA', 0)}
<rect x="{LEFT}" y="{top1}" width="{WIDTH - LEFT - RIGHT}" height="{PANEL_H}" fill="none" class="axis"/>
<rect x="{LEFT}" y="{top2}" width="{WIDTH - LEFT - RIGHT}" height="{PANEL_H}" fill="none" class="axis"/>
<g class="collector">{polyline(plot_rows, 3, v_low, v_high, top1)}</g>
<g class="diode">{polyline(plot_rows, 5, i_low, i_high, top2)}</g>
<g class="motor">{polyline(plot_rows, 4, i_low, i_high, top2)}</g>
<line x1="{sx(20):.1f}" y1="{top1}" x2="{sx(20):.1f}" y2="{top2 + PANEL_H}" stroke="#805ad5" stroke-width="1.5" stroke-dasharray="6 4"/>
<text x="{sx(20) + 8:.1f}" y="{top1 + 18}" font-family="Arial, sans-serif" font-size="12" fill="#553c9a">drive off: flyback clamps collector near 5.77 V</text>
<g font-family="Arial, sans-serif" font-size="13" fill="#1a202c">
  <rect x="{WIDTH - 250}" y="20" width="12" height="3" fill="#c53030"/><text x="{WIDTH - 230}" y="26">Collector voltage (V)</text>
  <rect x="{WIDTH - 250}" y="40" width="12" height="3" fill="#2f855a"/><text x="{WIDTH - 230}" y="46">Motor current (mA)</text>
  <rect x="{WIDTH - 250}" y="60" width="12" height="3" fill="#b7791f"/><text x="{WIDTH - 230}" y="66">Flyback diode current (mA)</text>
</g>
<text x="{LEFT}" y="{HEIGHT - 14}" font-family="Arial, sans-serif" font-size="12" fill="#718096">Source: simulation/simulide/driver.cir, ngspice-39. Generated by plot_driver.py.</text>
</svg>
'''
    SVG.write_text(svg, encoding="utf-8")
    print(f"wrote {SVG} and {CSV} ({len(rows)} rows, plotted {len(plot_rows)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
