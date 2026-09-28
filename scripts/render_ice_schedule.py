#!/usr/bin/env python3
"""Render the club-provided weekly training schedule as a branded SVG."""

import base64
import html
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = (
    ROOT / "public" / "images" / "ice-schedule" / "rozpis-ladu-2026-09-28.svg",
    ROOT / "images" / "ice-schedule" / "rozpis-ladu-2026-09-28.svg",
)
LOGO = ROOT / "assets" / "logo-hk-brezno.png"

WIDTH = 1387
HEIGHT = 1132
TABLE_TOP = 238
TABLE_BOTTOM = 984
HEADER_HEIGHT = 69
ROWS = 11
COL_WIDTH = WIDTH / 7
ROW_HEIGHT = (TABLE_BOTTOM - TABLE_TOP - HEADER_HEIGHT) / ROWS

NAVY = "#062b55"
RED = "#e30613"
WHITE = "#ffffff"
INK = "#092c55"


def cell(text="-", span=1, size=20):
    return {"text": text, "span": span, "size": size}


DAYS = [
    ("Pondelok", "28.9.", [
        cell("KRASO\n6:00 - 7:30"), cell("5 ŠT\n7:45 - 8:45"),
        cell("ASA\n9:00 - 11:00"), cell(), cell("6 ŠT\n12:15 - 13:45"),
        cell("KRASO\n14:00 - 16:00"), cell("3 - 4 r.\n16:15 - 17:15"),
        cell("3 - 6 BRANKÁRI\n17:00 - 18:00", size=18),
        cell("7 - 9 BRANKÁRI\n18:15 - 19:15", size=18),
        cell("SŽ\n19:00 - 20:15"), cell("BOROVIČ\n20:30 - 21:30"),
    ]),
    ("Utorok", "29.9.", [
        cell("KRASO\n6:00 - 6:45"), cell("7 ŠT\n6:45 - 8:00"),
        cell("ASA\n9:00 - 11:00"), cell(), cell("9 ŠT\n12:45 - 14:00"),
        cell("OPEN ICE MŽ+SŽ\n14:15 - 15:30", size=17), cell("6 r.\n15:45 - 17:00"),
        cell("0 - 2 r.\n17:15 - 18:30"), cell("A\n18:45 - 20:00"),
        cell("HK VETERÁNI\n20:30 - 21:30", size=18), cell(),
    ]),
    ("Streda", "30.9.", [
        cell("KRASO\n6:00 - 7:30"), cell(), cell("ASA\n9:00 - 11:00"), cell(),
        cell("5 ŠT\n12:15 - 13:45"), cell("KRASO\n14:00 - 16:00"),
        cell("7 r.\n16:15 - 17:15"), cell("3 - 4 r.\n17:30 - 18:30"),
        cell("SŽ\n18:45 - 20:00"), cell("BOROVIČ\n20:15 - 21:15"), cell(),
    ]),
    ("Štvrtok", "1.10.", [
        cell("KRASO\n6:00 - 6:45"), cell("9 ŠT\n6:45 - 8:00"),
        cell("ASA\n9:00 - 11:00"), cell("7 ŠT\n12:45 - 14:00"),
        cell("PHS 1\n14:15 - 15:15"), cell("PHS 2\n15:30 - 16:30"),
        cell("SŽ + MŽ A\n16:30 - 17:30"), cell("0 - 2 r.\n17:45 - 18:45"),
        cell("A\n19:00 - 20:15"), cell("HK VETERÁNI\n20:45 - 21:45", size=18),
        cell("SKAČAN\n22:00 - 23:00"),
    ]),
    ("Piatok", "2.10.", [
        cell("KRASO\n6:00 - 7:00"), cell("6 ŠT\n7:00 - 8:00"),
        cell("ASA\n9:00 - 11:00"), cell(), cell("7 r.\n14:30 - 15:45"),
        cell("4 - 5 r.\n16:00 - 17:15"), cell("SŽ\n17:30 - 18:45"),
        cell("A\n19:00 - 20:15"), cell("MOCHOVCI\n20:45 - 21:45", size=18),
        cell(), cell(),
    ]),
    ("Sobota", "3.10.", [
        cell("4 - 5 r.\n8:15 - 9:30"),
        cell("SŽ A1 - MARTIN\n9:45 - 12:00", span=2, size=19), cell(),
        cell("VEREJNOSŤ\n14:00 - 15:45", span=2),
        cell("JANOŠTIAK\n16:15 - 17:45"), cell("POLOMKA\n18:00 - 19:00"),
        cell("HARMANEC\n19:15 - 20:45"), cell(), cell(),
    ]),
    ("Nedeľa", "4.10.", [
        cell(), cell("0 - 3 r.\n10:00 - 11:15"), cell(), cell(),
        cell("VEREJNOSŤ\n14:15 - 15:45", span=2),
        cell("OPEN ICE\n16:00 - 17:30"), cell("KUŠPÁL\n18:00 - 19:00"),
        cell(), cell(), cell(),
    ]),
]


def multiline_text(value, x, y, width, height, size, weight="700"):
    lines = value.splitlines()
    line_height = size * 1.22
    first_y = y + height / 2 - (len(lines) - 1) * line_height / 2 + size * 0.35
    tspans = "".join(
        f'<tspan x="{x + width / 2:.2f}" y="{first_y + i * line_height:.2f}">'
        f'{html.escape(line)}</tspan>'
        for i, line in enumerate(lines)
    )
    return (
        f'<text text-anchor="middle" font-size="{size}" fill="{WHITE}" '
        f'font-weight="{weight}">{tspans}</text>'
    )


def render():
    logo_data = base64.b64encode(LOGO.read_bytes()).decode("ascii")
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
        '<title id="title">Rozpis tréningov od 28. septembra do 4. októbra 2026</title>',
        '<desc id="desc">Týždenný rozpis tréningov HK Brezno pre sezónu 2026/2027.</desc>',
        '<defs>',
        '<pattern id="dots" width="11" height="11" patternUnits="userSpaceOnUse">'
        '<circle cx="2" cy="2" r="1.4" fill="#cad1d8" opacity=".62"/>'
        '<circle cx="7" cy="7" r=".8" fill="#d8dde2" opacity=".75"/></pattern>',
        '<linearGradient id="flag" x1="0" x2="1"><stop stop-color="#e30613"/>'
        '<stop offset=".48" stop-color="#fff"/><stop offset="1" stop-color="#17487c"/></linearGradient>',
        '</defs>',
        '<rect width="100%" height="100%" fill="#f8f8f7"/>',
        '<rect width="100%" height="100%" fill="url(#dots)"/>',
        '<g font-family="Arial, Helvetica, sans-serif">',
        '<text x="68" y="80" font-size="25" font-weight="800" letter-spacing="2">SEZÓNA</text>',
        '<text x="66" y="151" font-size="66" font-weight="900" fill="#0a315e">#26/27</text>',
        '<text x="385" y="151" font-size="155" font-weight="900" fill="#e30613" '
        'font-family="Impact, Arial Black, sans-serif" letter-spacing="3">ROZPIS</text>',
        '<text x="790" y="205" font-size="69" font-style="italic" fill="#0a315e" '
        'font-family="Georgia, serif">Tréningov</text>',
        '<text x="1228" y="88" text-anchor="middle" font-size="33" font-weight="900" '
        'fill="#0a315e"><tspan x="1228">VIAC</tspan><tspan x="1228" dy="35">AKO</tspan>'
        '<tspan x="1228" dy="35">HOKEJ</tspan></text>',
        '<g stroke="#777" stroke-width="8"><path d="M61 191l23 23m0-23l-23 23"/>'
        '<path d="M133 191l23 23m0-23l-23 23"/><path d="M205 191l23 23m0-23l-23 23"/>'
        '<path d="M277 191l23 23m0-23l-23 23"/></g>',
        '<path d="M1387 18l-54 54v146l54-54z" fill="#777"/>'
        '<path d="M1387 76l-38 38v31l38-38z" fill="#fff"/>',
        f'<rect x="0" y="{TABLE_TOP}" width="{WIDTH}" height="{TABLE_BOTTOM - TABLE_TOP}" fill="{NAVY}"/>',
    ]

    for col, (day, date_label, cells) in enumerate(DAYS):
        x = col * COL_WIDTH
        parts.append(
            f'<rect x="{x:.2f}" y="{TABLE_TOP}" width="{COL_WIDTH:.2f}" '
            f'height="{HEADER_HEIGHT}" fill="{NAVY}" stroke="{WHITE}" stroke-width="1.4"/>'
        )
        parts.append(multiline_text(
            f"{day}\n{date_label}", x, TABLE_TOP, COL_WIDTH, HEADER_HEIGHT, 21, "800"
        ))
        row = 0
        for item in cells:
            span = item["span"]
            y = TABLE_TOP + HEADER_HEIGHT + row * ROW_HEIGHT
            height = ROW_HEIGHT * span
            parts.append(
                f'<rect x="{x:.2f}" y="{y:.2f}" width="{COL_WIDTH:.2f}" '
                f'height="{height:.2f}" fill="{NAVY}" stroke="{WHITE}" stroke-width="1.2"/>'
            )
            parts.append(multiline_text(
                item["text"], x, y, COL_WIDTH, height, item["size"], "700"
            ))
            row += span
        if row != ROWS:
            raise ValueError(f"{day}: očakávaných {ROWS} riadkov, v dátach je {row}")

    parts.extend([
        f'<image href="data:image/png;base64,{logo_data}" x="68" y="995" width="135" height="135" '
        'preserveAspectRatio="xMidYMid meet"/>',
        '<text x="693.5" y="1091" text-anchor="middle" font-size="60" font-weight="900" '
        f'fill="{INK}" font-family="Impact, Arial Black, sans-serif" letter-spacing="2">'
        '28.9. - 4.10. 2026</text>',
        '<rect x="310" y="1062" width="132" height="10" fill="url(#flag)"/>',
        '<rect x="1015" y="1062" width="132" height="10" fill="url(#flag)"/>',
        '<g stroke="#777" stroke-width="8"><path d="M1090 1014l23 23m0-23l-23 23"/>'
        '<path d="M1164 1014l23 23m0-23l-23 23"/><path d="M1238 1014l23 23m0-23l-23 23"/>'
        '<path d="M1312 1014l23 23m0-23l-23 23"/></g>',
        '</g>',
        '</svg>',
    ])
    payload = "\n".join(parts) + "\n"
    for output in OUTPUTS:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding="utf-8")
        print(f"OK: {output.relative_to(ROOT)}")


if __name__ == "__main__":
    render()
