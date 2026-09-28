#!/usr/bin/env python3
"""Render the club-provided weekly ice schedule as a scalable SVG."""

import html
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = (
    ROOT / "public" / "images" / "ice-schedule" / "rozpis-ladu-2026-09-28.svg",
    ROOT / "images" / "ice-schedule" / "rozpis-ladu-2026-09-28.svg",
)

WIDTH = 1372
HEIGHT = 835
HEADER_HEIGHT = 70
ROWS = 11
COL_WIDTH = WIDTH / 7
ROW_HEIGHT = (HEIGHT - HEADER_HEIGHT) / ROWS

GRAY = "#dedede"
PINK = "#f3a7aa"
BLUE = "#11a9dc"
GREEN = "#92d34d"
GOLD = "#ffc20e"
YELLOW = "#fff500"
RED = "#ff0808"


def cell(text="", color=GRAY, span=1, foreground="#000000", size=24):
    return {
        "text": text,
        "color": color,
        "span": span,
        "foreground": foreground,
        "size": size,
    }


DAYS = [
    ("Pondelok", "28.9.", [
        cell("KRASO\n6:00-7:30", PINK),
        cell("5 ŠT\n7:45-8:45", BLUE, foreground="#ffffff"),
        cell("ASA\n9:00-11:00", GREEN),
        cell(),
        cell("6 ŠT\n12:15-13:45", BLUE, foreground="#ffffff"),
        cell("KRASO\n14:00-16:00", PINK),
        cell("3 - 4 r.\n16:15-17:15", BLUE, foreground="#ffffff"),
        cell("3 - 6 BRANKÁRI\n17:00-18:00", BLUE, foreground="#ffffff", size=21),
        cell("7 - 9 BRANKÁRI\n18:15-19:15", BLUE, foreground="#ffffff", size=21),
        cell("SŽ\n19:00-20:15", BLUE, foreground="#ffffff"),
        cell("BOROVIČ\n20:30-21:30", GOLD),
    ]),
    ("Utorok", "29.9.", [
        cell("KRASO\n6:00-6:45", PINK),
        cell("7 ŠT\n6:45-8:00", BLUE, foreground="#ffffff"),
        cell("ASA\n9:00-11:00", GREEN),
        cell(),
        cell("9 ŠT\n12:45-14:00", BLUE, foreground="#ffffff"),
        cell("OPEN ICE MŽ+SŽ\n14:15-15:30", BLUE, foreground="#ffffff", size=20),
        cell("6 r.\n15:45-17:00", BLUE, foreground="#ffffff"),
        cell("0 - 2 r.\n17:15-18:30", BLUE, foreground="#ffffff"),
        cell("A\n18:45-20:00", BLUE, foreground="#ffffff"),
        cell("HK VETERÁNI\n20:30-21:30", GOLD, size=22),
        cell(),
    ]),
    ("Streda", "30.9.", [
        cell("KRASO\n6:00-7:30", PINK),
        cell(),
        cell("ASA\n9:00-11:00", GREEN),
        cell(),
        cell("5 ŠT\n12:15-13:45", BLUE, foreground="#ffffff"),
        cell("KRASO\n14:00-16:00", PINK),
        cell("7 r.\n16:15-17:15", BLUE, foreground="#ffffff"),
        cell("3 - 4 r.\n17:30-18:30", BLUE, foreground="#ffffff"),
        cell("SŽ\n18:45-20:00", BLUE, foreground="#ffffff"),
        cell("BOROVIČ\n20:15-21:15", GOLD),
        cell(),
    ]),
    ("Štvrtok", "1.10.", [
        cell("KRASO\n6:00-6:45", PINK),
        cell("9 ŠT\n6:45-8:00", BLUE, foreground="#ffffff"),
        cell("ASA\n9:00-11:00", GREEN),
        cell("7 ŠT\n12:45-14:00", BLUE, foreground="#ffffff"),
        cell("PHS 1\n14:15-15:15", BLUE, foreground="#ffffff"),
        cell("PHS 2\n15:30-16:30", BLUE, foreground="#ffffff"),
        cell("SŽ + MŽ A\n16:30-17:30", BLUE, foreground="#ffffff", size=22),
        cell("0 - 2 r.\n17:45-18:45", BLUE, foreground="#ffffff"),
        cell("A\n19:00-20:15", BLUE, foreground="#ffffff"),
        cell("HK VETERÁNI\n20:45-21:45", GOLD, size=22),
        cell("SKAČAN\n22:00-23:00", GOLD),
    ]),
    ("Piatok", "2.10.", [
        cell("KRASO\n6:00-7:00", PINK),
        cell("6 ŠT\n7:00-8:00", BLUE, foreground="#ffffff"),
        cell("ASA\n9:00-11:00", GREEN),
        cell(),
        cell(),
        cell("7 r.\n14:30-15:45", BLUE, foreground="#ffffff"),
        cell("4 - 5 r.\n16:00-17:15", BLUE, foreground="#ffffff"),
        cell("SŽ\n17:30-18:45", BLUE, foreground="#ffffff"),
        cell("A\n19:00-20:15", BLUE, foreground="#ffffff"),
        cell("MOCHOVCI\n20:45-21:45", GOLD, size=22),
        cell(),
    ]),
    ("Sobota", "3.10.", [
        cell("4 - 5 r.\n8:15-9:30", BLUE, foreground="#ffffff"),
        cell("SŽ A1- MARTIN\n9:45-12:00", RED, span=2, foreground="#ffffff", size=22),
        cell(),
        cell("KRASO\n12:30-13:30", PINK),
        cell("VEREJNOSŤ\n14:00-15:45", YELLOW, span=2),
        cell("JANOŠTIAK\n16:15-17:45", GOLD, size=22),
        cell("POLOMKA\n18:00-19:00", GOLD),
        cell("HARMANEC\n19:15-20:45", GOLD, size=22),
        cell(),
    ]),
    ("Nedeľa", "4.10.", [
        cell(),
        cell("0 - 3 r.\n10:00-11:15", BLUE, foreground="#ffffff"),
        cell(),
        cell("KUNÁK\n12:45-13:45", GOLD),
        cell("VEREJNOSŤ\n14:15-15:45", YELLOW, span=2),
        cell("OPEN ICE\n16:00-17:30", BLUE, foreground="#ffffff"),
        cell("KUŠPÁL\n18:00-19:00", GOLD),
        cell(),
        cell(),
        cell(),
    ]),
]


def text_element(value, x, y, width, height, foreground, size):
    lines = value.splitlines()
    line_height = size * 1.18
    first_y = y + height / 2 - (len(lines) - 1) * line_height / 2 + size * 0.34
    escaped = [html.escape(line) for line in lines]
    tspans = "".join(
        f'<tspan x="{x + width / 2:.2f}" y="{first_y + i * line_height:.2f}">{line}</tspan>'
        for i, line in enumerate(escaped)
    )
    return (
        f'<text text-anchor="middle" font-size="{size}" fill="{foreground}" '
        f'font-weight="700">{tspans}</text>'
    )


def render():
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
        '<title id="title">Rozpis ľadu od 28. septembra do 4. októbra 2026</title>',
        '<desc id="desc">Týždenný rozpis ľadovej plochy HK Brezno.</desc>',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<g font-family="Arial, Helvetica, sans-serif">',
    ]

    for col, (day, date_label, cells) in enumerate(DAYS):
        x = col * COL_WIDTH
        parts.append(
            f'<rect x="{x:.2f}" y="0" width="{COL_WIDTH:.2f}" height="{HEADER_HEIGHT}" '
            'fill="#ffffff" stroke="#000000" stroke-width="2"/>'
        )
        parts.append(text_element(f"{day}\n{date_label}", x, 0, COL_WIDTH, HEADER_HEIGHT, "#000000", 24))

        row = 0
        for item in cells:
            span = item["span"]
            y = HEADER_HEIGHT + row * ROW_HEIGHT
            height = ROW_HEIGHT * span
            parts.append(
                f'<rect x="{x:.2f}" y="{y:.2f}" width="{COL_WIDTH:.2f}" height="{height:.2f}" '
                f'fill="{item["color"]}" stroke="#000000" stroke-width="2"/>'
            )
            if item["text"]:
                parts.append(text_element(
                    item["text"], x, y, COL_WIDTH, height,
                    item["foreground"], item["size"],
                ))
            row += span
        if row != ROWS:
            raise ValueError(f"{day}: očakávaných {ROWS} riadkov, v dátach je {row}")

    parts.extend(['</g>', '</svg>'])
    payload = "\n".join(parts) + "\n"
    for output in OUTPUTS:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding="utf-8")
        print(f"OK: {output.relative_to(ROOT)}")


if __name__ == "__main__":
    render()
