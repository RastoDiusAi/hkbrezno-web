#!/usr/bin/env python3
"""Import the HK Brezno league schedule and team logos from Hockey Slovakia."""

import argparse
import json
import re
import ssl
import unicodedata
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, unquote, urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

import certifi


SOURCE_URL = (
    "https://www.hockeyslovakia.sk/sk/stats/results/1199/"
    "2-slovenska-hokejova-liga"
)
CLUB_NAME = "HK Brezno"
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "content" / "matches" / "matches.json"
LOGO_DIR = ROOT / "public" / "images" / "teams" / "logos"
USER_AGENT = "Mozilla/5.0 (compatible; HKBreznoScheduleImporter/1.0)"
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


def clean(value):
    return " ".join(value.split())


def slugify(value):
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")


def safe_url(url):
    parts = urlsplit(url)
    path = quote(unquote(parts.path), safe="/()")
    return urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))


def fetch(url):
    request = Request(safe_url(url), headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=30, context=SSL_CONTEXT) as response:
        return response.read(), response.headers.get_content_type()


class ScheduleParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.row = None
        self.cell = None
        self.capture_venue = False
        self.venue_parts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = set(attrs.get("class", "").split())
        if tag == "tr" and "fn-tap-row" in classes and "fn-tap-row-sibbling" not in classes:
            self.row = {"cells": [], "matchUrl": ""}
            return
        if self.row is None:
            return
        if tag == "td":
            self.cell = {"text": [], "images": [], "venue": ""}
            return
        if self.cell is None:
            return
        if tag == "img" and attrs.get("src") and attrs.get("alt"):
            self.cell["images"].append({
                "src": urljoin(SOURCE_URL, attrs["src"]),
                "alt": clean(attrs["alt"]),
            })
        if tag == "a" and "/match/" in attrs.get("href", "") and not self.row["matchUrl"]:
            self.row["matchUrl"] = urljoin(SOURCE_URL, attrs["href"])
        if tag == "div" and "td-box" in classes:
            self.capture_venue = True
            self.venue_parts = []

    def handle_data(self, data):
        if self.cell is None:
            return
        value = clean(data)
        if not value:
            return
        self.cell["text"].append(value)
        if self.capture_venue:
            self.venue_parts.append(value)

    def handle_endtag(self, tag):
        if self.row is None:
            return
        if tag == "div" and self.capture_venue:
            self.cell["venue"] = clean(" ".join(self.venue_parts))
            self.capture_venue = False
            self.venue_parts = []
        if tag == "td" and self.cell is not None:
            self.row["cells"].append(self.cell)
            self.cell = None
        if tag == "tr":
            if len(self.row["cells"]) >= 5:
                self.rows.append(self.row)
            self.row = None
            self.cell = None
            self.capture_venue = False


def team_from_cell(cell):
    if not cell["images"]:
        raise ValueError("V riadku zápasu chýba tímové logo")
    image = cell["images"][0]
    return {"name": image["alt"], "sourceLogo": image["src"]}


def parse_matches(source_html):
    parser = ScheduleParser()
    parser.feed(source_html)
    matches = []
    seen = set()

    for row in parser.rows:
        home = team_from_cell(row["cells"][1])
        away = team_from_cell(row["cells"][3])
        if CLUB_NAME not in (home["name"], away["name"]):
            continue

        details = " ".join(row["cells"][4]["text"])
        date_match = re.search(r"\b(\d{2})\.(\d{2})\.(\d{4})\b", details)
        time_match = re.search(r"\b\d{2}:\d{2}\b", details)
        if not date_match or not time_match:
            raise ValueError(f"Neviem prečítať dátum alebo čas zápasu: {details}")

        day, month, year = date_match.groups()
        iso_date = f"{year}-{month}-{day}"
        match_key = (iso_date, time_match.group(0), home["name"], away["name"])
        if match_key in seen:
            continue
        seen.add(match_key)

        home_game = home["name"] == CLUB_NAME
        matches.append({
            "date": iso_date,
            "time": time_match.group(0),
            "home": home["name"],
            "away": away["name"],
            "venue": row["cells"][4]["venue"],
            "location": "home" if home_game else "away",
            "opponent": away["name"] if home_game else home["name"],
            "homeLogoSource": home["sourceLogo"],
            "awayLogoSource": away["sourceLogo"],
            "sourceUrl": row["matchUrl"] or SOURCE_URL,
        })

    return sorted(matches, key=lambda item: (item["date"], item["time"]))


def download_logos(matches):
    LOGO_DIR.mkdir(parents=True, exist_ok=True)
    teams = {}
    for match in matches:
        teams[match["home"]] = match["homeLogoSource"]
        teams[match["away"]] = match["awayLogoSource"]

    local_paths = {}
    for team, source_url in sorted(teams.items()):
        data, content_type = fetch(source_url)
        extension = ".jpg" if content_type in ("image/jpeg", "image/jpg") else ".png"
        filename = f"{slugify(team)}{extension}"
        (LOGO_DIR / filename).write_bytes(data)
        local_paths[team] = f"/images/teams/logos/{filename}"

    for match in matches:
        match["homeLogo"] = local_paths[match["home"]]
        match["awayLogo"] = local_paths[match["away"]]
        del match["homeLogoSource"]
        del match["awayLogoSource"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        help="Lokálny HTML súbor; bez neho sa načíta oficiálna stránka.",
    )
    args = parser.parse_args()

    if args.source:
        source_html = Path(args.source).read_text(encoding="utf-8")
    else:
        source_html = fetch(SOURCE_URL)[0].decode("utf-8")

    matches = parse_matches(source_html)
    if not matches:
        raise SystemExit("Nenašli sa žiadne zápasy HK Brezno")
    download_logos(matches)

    data = {
        "competition": "2. slovenská hokejová liga",
        "season": "2026/2027",
        "club": CLUB_NAME,
        "source": SOURCE_URL,
        "updatedAt": datetime.now(timezone.utc).date().isoformat(),
        "matches": matches,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"OK: {len(matches)} zápasov, {len(set(m['opponent'] for m in matches))} súperov")


if __name__ == "__main__":
    main()
