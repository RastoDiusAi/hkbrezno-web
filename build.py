#!/usr/bin/env python3
"""
Prevedie design-canvas súbor `HK Brezno Web.dc.html` (z projektu claude.ai/design)
na samostatnú, funkčnú webovú stránku `index.html` bez závislosti na runtime
`support.js` / `image-slot.js`.

Mapovanie:
  <helmet>…</helmet>            -> skutočný <head>
  <x-dc>                        -> zahodené
  <sc-if value="{{ isXxx }}">   -> <section class="pg" data-pg="xxx">   (routovanie cez CSS)
  <sc-if value="{{ isStuck }}"> -> <span data-stuck>                    (prilepená navigácia)
  <sc-for list="{{ roster }}">  -> rozbalené nad dátami súpisky
  onClick="{{ go.xxx }}"        -> data-go="xxx"
  {{ c.xxx }} / {{ u.xxx }}     -> statická farba + data-nav / data-u (aktívny stav z CSS)
  {{ nav.* }}                   -> data-navbar + trieda .is-stuck
  {{ cd.d|h|m|s }}              -> <span data-cd="…"> (dopočíta JS)
  style-hover="…"               -> data-hv="N" + vygenerované :hover pravidlo
  <image-slot placeholder="X">  -> <div class="slot"><span>X</span></div>

Spustenie:  python3 build.py
"""
import re
import sys
import pathlib
import html as html_lib
import json
import shutil
from datetime import date, datetime

HERE = pathlib.Path(__file__).parent
SRC = HERE / "design-canvas.dc.html"
OUT = HERE / "index.html"
CONTENT = HERE / "content"
PUBLIC = HERE / "public"
SITE_URL = "https://novyweb.smartitbiz.com"

PAGES = ['domov', 'novinky', 'zapasy', 'rozpisladu', 'timy', 'klub',
         'rodicia', 'partneri', 'prihlaska']

ROSTER = [
    ('1',  'Brankár',  'Tomáš Ferko',      27, 22, 0),
    ('30', 'Brankár',  'Adam Šulek',       21,  9, 0),
    ('4',  'Obranca',  'Martin Kováč',     31, 22, 14),
    ('7',  'Obranca',  'Jakub Hrušovský',  24, 21, 9),
    ('22', 'Obranca',  'Denis Turčan',     19, 18, 6),
    ('9',  'Útočník',  'Lukáš Bella',      26, 22, 31),
    ('11', 'Útočník',  'Peter Šmál',       23, 22, 27),
    ('17', 'Útočník',  'Michal Dovala',    28, 20, 24),
    ('19', 'Útočník',  'Filip Krupa',      20, 19, 15),
    ('91', 'Útočník',  'Samuel Piliar',    18, 14, 11),
]

# start tag, ktorý korektne preskočí `>` vnútri hodnôt atribútov
TAG_RE = re.compile(r'<([a-zA-Z][\w-]*)((?:[^>"]|"[^"]*")*?)(/?)>')
SLUG_RE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')

hover_rules = []   # index -> CSS deklarácie


def fail(msg):
    sys.exit(f"build.py: {msg}")


def parse_scalar(value):
    value = value.strip()
    if value in ("true", "false"):
        return value == "true"
    if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value


def parse_frontmatter(text, source):
    if not text.startswith("---\n"):
        fail(f"{source}: chýba front matter blok")
    end = text.find("\n---", 4)
    if end == -1:
        fail(f"{source}: front matter nie je ukončený")
    meta_text = text[4:end].strip("\n")
    body = text[end + 4:].lstrip("\n")
    meta = {}
    current_list = None
    for line in meta_text.splitlines():
        if not line.strip():
            continue
        if line.startswith("  - "):
            if current_list is None:
                fail(f"{source}: položka zoznamu bez kľúča: {line}")
            meta[current_list].append(parse_scalar(line[4:]))
            continue
        current_list = None
        if ":" not in line:
            fail(f"{source}: neplatný riadok front matter: {line}")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            fail(f"{source}: prázdny kľúč vo front matter")
        if value == "":
            meta[key] = []
            current_list = key
        else:
            meta[key] = parse_scalar(value)
    return meta, body


def markdown_to_html(markdown):
    out = []
    paragraph = []
    in_list = False

    def flush_paragraph():
        if paragraph:
            text = " ".join(paragraph)
            out.append(f"<p>{html_lib.escape(text)}</p>")
            paragraph.clear()

    def close_list():
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    for raw in markdown.splitlines():
        line = raw.rstrip()
        if not line:
            flush_paragraph()
            close_list()
            continue
        if line.startswith("# "):
            flush_paragraph()
            close_list()
            out.append(f"<h1>{html_lib.escape(line[2:].strip())}</h1>")
            continue
        if line.startswith("## "):
            flush_paragraph()
            close_list()
            out.append(f"<h2>{html_lib.escape(line[3:].strip())}</h2>")
            continue
        if line.startswith("### "):
            flush_paragraph()
            close_list()
            out.append(f"<h3>{html_lib.escape(line[4:].strip())}</h3>")
            continue
        if line.startswith("- "):
            flush_paragraph()
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{html_lib.escape(line[2:].strip())}</li>")
            continue
        paragraph.append(line.strip())

    flush_paragraph()
    close_list()
    return "\n".join(out)


def validate_article(path):
    meta, body = parse_frontmatter(path.read_text(encoding="utf-8"), path)
    required = ("title", "slug", "date", "description", "published")
    for key in required:
        if key not in meta:
            fail(f"{path}: chýba povinné pole `{key}`")
    if not isinstance(meta["published"], bool):
        fail(f"{path}: `published` musí byť true alebo false")
    if not SLUG_RE.match(str(meta["slug"])):
        fail(f"{path}: `slug` musí používať malé písmená, čísla a pomlčky")
    try:
        article_date = date.fromisoformat(str(meta["date"]))
    except ValueError:
        fail(f"{path}: `date` musí byť vo formáte YYYY-MM-DD")
    publish_date = meta.get("publishDate")
    if publish_date:
        try:
            publish_date = date.fromisoformat(str(publish_date))
        except ValueError:
            fail(f"{path}: `publishDate` musí byť vo formáte YYYY-MM-DD")
    return {
        "title": str(meta["title"]),
        "slug": str(meta["slug"]),
        "date": article_date,
        "publishDate": publish_date,
        "description": str(meta["description"]),
        "cover": str(meta.get("cover", "")),
        "author": str(meta.get("author", "HK Brezno")),
        "tags": meta.get("tags", []),
        "published": meta["published"],
        "body": body,
        "bodyHtml": "",
        "categories": meta.get("categories", []),
        "source": "local",
        "sourceUrl": "",
        "path": path,
    }


def load_articles():
    article_dir = CONTENT / "articles"
    if not article_dir.exists():
        return []
    articles = [validate_article(path) for path in sorted(article_dir.rglob("*.md"))]
    today = date.today()
    published = []
    seen = set()
    for article in articles:
        if article["slug"] in seen:
            fail(f"duplicitný slug článku: {article['slug']}")
        seen.add(article["slug"])
        if not article["published"]:
            continue
        if article["publishDate"] and article["publishDate"] > today:
            continue
        published.append(article)
    return sorted(published, key=lambda item: item["date"], reverse=True)


def load_wordpress_articles():
    path = CONTENT / "wordpress" / "posts.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"{path}: neplatný JSON ({exc})")
    if not isinstance(data, dict) or not isinstance(data.get("posts"), list):
        fail(f"{path}: očakávam objekt s poľom `posts`")

    articles = []
    required = (
        "title", "slug", "date", "description", "cover", "author",
        "categories", "tags", "bodyHtml", "sourceUrl",
    )
    for i, post in enumerate(data["posts"], start=1):
        if not isinstance(post, dict):
            fail(f"{path}: článok {i} nie je objekt")
        for key in required:
            if key not in post:
                fail(f"{path}: článku {i} chýba `{key}`")
        if not SLUG_RE.match(str(post["slug"])):
            fail(f"{path}: článok {i} má neplatný `slug`")
        try:
            article_date = date.fromisoformat(str(post["date"]))
        except ValueError:
            fail(f"{path}: článok {i} má neplatný `date`")
        articles.append({
            "title": str(post["title"]),
            "slug": str(post["slug"]),
            "date": article_date,
            "publishDate": None,
            "description": str(post["description"]),
            "cover": str(post["cover"]),
            "author": str(post["author"]),
            "tags": post["tags"],
            "categories": post["categories"],
            "published": True,
            "body": "",
            "bodyHtml": str(post["bodyHtml"]),
            "source": "wordpress",
            "sourceUrl": str(post["sourceUrl"]),
            "path": path,
        })
    return articles


def load_wordpress_pages():
    path = CONTENT / "wordpress" / "pages.json"
    if not path.exists():
        fail(f"chýba {path}; spusti scripts/import_wordpress.py")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"{path}: neplatný JSON ({exc})")
    if not isinstance(data, dict) or data.get("schemaVersion") != 1:
        fail(f"{path}: nepodporovaná schéma")
    if not isinstance(data.get("club"), dict):
        fail(f"{path}: chýba objekt `club`")
    if not isinstance(data.get("iceSchedule"), dict):
        fail(f"{path}: chýba objekt `iceSchedule`")
    contact = data["club"].get("contact")
    history = data["club"].get("history")
    if not isinstance(contact, dict) or not isinstance(history, dict):
        fail(f"{path}: neplatný obsah stránky Klub")
    if not isinstance(history.get("blocks"), list):
        fail(f"{path}: história nemá zoznam `blocks`")
    return data


def apply_ice_schedule_override(pages):
    path = CONTENT / "ice-schedule.json"
    if not path.exists():
        return pages
    try:
        override = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"{path}: neplatný JSON ({exc})")
    required = ("title", "modified", "sourceLabel", "sourceUrl", "asset", "assetType")
    if not isinstance(override, dict) or any(key not in override for key in required):
        fail(f"{path}: neplatný lokálny rozpis ľadu")
    if override["assetType"] not in ("image", "pdf"):
        fail(f"{path}: `assetType` musí byť image alebo pdf")
    asset_path = HERE / str(override["asset"]).lstrip("/")
    if not asset_path.is_file():
        fail(f"{path}: súbor rozpisu neexistuje: {asset_path}")

    wordpress_modified = str(pages["iceSchedule"].get("modified", ""))
    if str(override["modified"]) > wordpress_modified:
        pages["iceSchedule"] = override
    return pages


def merge_articles(local_articles, wordpress_articles):
    articles = local_articles + wordpress_articles
    seen = set()
    for article in articles:
        if article["slug"] in seen:
            fail(f"duplicitný slug článku: {article['slug']}")
        seen.add(article["slug"])
    return sorted(articles, key=lambda item: item["date"], reverse=True)


def validate_json_file(path, required_keys):
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"{path}: neplatný JSON ({exc})")
    if not isinstance(data, list):
        fail(f"{path}: očakávam zoznam objektov")
    for i, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            fail(f"{path}: položka {i} nie je objekt")
        for key in required_keys:
            if key not in item:
                fail(f"{path}: položke {i} chýba `{key}`")


def validate_content():
    validate_json_file(CONTENT / "partners" / "partners.json",
                       ("name", "active", "order"))
    validate_json_file(CONTENT / "teams" / "teams.json",
                       ("name", "slug", "competition", "competitionUrl", "active", "order"))
    validate_json_file(CONTENT / "coaches" / "coaches.json",
                       ("name", "role", "active", "order"))
    validate_json_file(CONTENT / "documents" / "documents.json",
                       ("title", "file", "active", "order"))
    return merge_articles(load_articles(), load_wordpress_articles())


def load_match_schedule():
    path = CONTENT / "matches" / "matches.json"
    if not path.exists():
        fail(f"chýba {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"{path}: neplatný JSON ({exc})")
    if not isinstance(data, dict) or not isinstance(data.get("matches"), list):
        fail(f"{path}: očakávam objekt s poľom `matches`")
    if not data["matches"]:
        fail(f"{path}: program neobsahuje žiadne zápasy")
    required_root = ("competition", "season", "club", "source", "updatedAt")
    for key in required_root:
        if key not in data:
            fail(f"{path}: chýba `{key}`")
    required_match = (
        "date", "time", "home", "away", "venue", "location", "opponent",
        "homeLogo", "awayLogo", "sourceUrl",
    )
    for i, match in enumerate(data["matches"], start=1):
        if not isinstance(match, dict):
            fail(f"{path}: zápas {i} nie je objekt")
        for key in required_match:
            if key not in match:
                fail(f"{path}: zápasu {i} chýba `{key}`")
        try:
            date.fromisoformat(match["date"])
            datetime.strptime(match["time"], "%H:%M")
        except (TypeError, ValueError):
            fail(f"{path}: zápas {i} má neplatný dátum alebo čas")
        if match["location"] not in ("home", "away"):
            fail(f"{path}: zápas {i} má neplatné `location`")
    return data


SK_DAYS = ("Pondelok", "Utorok", "Streda", "Štvrtok", "Piatok", "Sobota", "Nedeľa")
SK_MONTHS = (
    "január", "február", "marec", "apríl", "máj", "jún",
    "júl", "august", "september", "október", "november", "december",
)


def article_category(article):
    values = article.get("categories") or article.get("tags") or ["Klub"]
    return str(values[0])


def article_date_label(article_date):
    return f"{article_date.day}. {article_date.month}. {article_date.year}"


def article_reading_minutes(article):
    source = article.get("bodyHtml") or article.get("body", "")
    words = re.sub(r"<[^>]+>", " ", source).split()
    return max(1, round(len(words) / 200))


def article_media(article, large=False):
    title = html_lib.escape(article["title"])
    if article.get("cover"):
        cover = html_lib.escape(article["cover"].lstrip("/"), quote=True)
        return f'<img src="{cover}" alt="{title}" loading="lazy">'
    size_class = " large" if large else ""
    return (
        f'<div class="article-card-fallback{size_class}">'
        '<img src="assets/logo-hk-brezno.png" alt="" loading="lazy">'
        '</div>'
    )


def render_article_card(article):
    title = html_lib.escape(article["title"])
    description = html_lib.escape(article["description"])
    category = html_lib.escape(article_category(article))
    href = f"aktuality/{html_lib.escape(article['slug'], quote=True)}/"
    return f"""
      <a class="article-card" href="{href}">
        <div class="article-card-media">{article_media(article)}</div>
        <div class="article-card-body">
          <div class="article-card-meta"><span>{category}</span><time datetime="{article['date'].isoformat()}">{article_date_label(article['date'])}</time></div>
          <h3>{title}</h3>
          <p>{description}</p>
        </div>
      </a>"""


def render_home_articles(articles):
    cards = "".join(render_article_card(article) for article in articles[:3])
    if not cards:
        cards = '<p class="article-empty">Zatiaľ neboli publikované žiadne novinky.</p>'
    return f'<div class="article-home-grid">{cards}</div>'


def render_news_page(articles):
    cards = "".join(render_article_card(article) for article in articles)
    if not cards:
        cards = '<p class="article-empty">Zatiaľ neboli publikované žiadne novinky.</p>'
    return f"""
  <div>
    <div class="match-hero">
      <div>Aktuality HK Brezno</div>
      <h1>NOVINKY</h1>
    </div>
    <div class="article-news-page">
      <div class="article-news-heading">
        <h2>ČO JE NOVÉ V KLUBE</h2>
        <span>{len(articles)} publikovaných článkov</span>
      </div>
      <div class="article-grid">{cards}</div>
    </div>
  </div>
"""


def render_club_page(pages):
    club = pages["club"]
    contact = club["contact"]
    history = club["history"]
    history_parts = []
    lead_used = False
    for block in history.get("blocks", []):
        tag = str(block.get("tag", "p")).lower()
        value = str(block.get("text", "")).strip()
        if not value or tag == "h1":
            continue
        safe_value = html_lib.escape(value).replace("\n", "<br>")
        if tag == "h2":
            history_parts.append(f"<h2>{safe_value}</h2>")
        elif tag in ("h3", "h4", "h5", "h6"):
            css_class = "club-history-lead" if not lead_used else "club-history-emphasis"
            history_parts.append(f'<p class="{css_class}">{safe_value}</p>')
            lead_used = True
        else:
            history_parts.append(f"<p>{safe_value}</p>")

    address = "<br>".join(html_lib.escape(str(item)) for item in contact.get("address", []))
    email = html_lib.escape(contact.get("email", "info@hkbrezno.sk"))
    return f"""
  <div>
    <div class="match-hero">
      <div>Hokejový klub Brezno</div>
      <h1>KLUB</h1>
    </div>
    <figure class="club-arena">
      <img src="images/club/arena-brezno.jpg" alt="Aréna Brezno, domovský zimný štadión HK Brezno">
      <figcaption>Aréna Brezno · Zimný štadión Ladislava Horského</figcaption>
    </figure>
    <div class="club-page">
      <article class="club-history">
        <div class="section-kicker">Od prvého klziska po dnešok</div>
        <h2>HISTÓRIA KLUBU</h2>
        <div class="club-history-content">{''.join(history_parts)}</div>
      </article>
      <aside class="club-contact">
        <div class="section-kicker">Kontakt a identifikačné údaje</div>
        <h2>{html_lib.escape(contact.get('name', 'Hokejový klub Brezno'))}</h2>
        <dl>
          <div><dt>Adresa</dt><dd>{address}</dd></div>
          <div><dt>E-mail</dt><dd><a href="mailto:{email}">{email}</a></dd></div>
          <div><dt>IČO</dt><dd>{html_lib.escape(contact.get('companyId', ''))}</dd></div>
          <div><dt>DIČ</dt><dd>{html_lib.escape(contact.get('taxId', ''))}</dd></div>
          <div><dt>IČ DPH</dt><dd>{html_lib.escape(contact.get('vatId', ''))}</dd></div>
          <div><dt>Registrácia</dt><dd>{html_lib.escape(contact.get('registry', ''))}<br>{html_lib.escape(contact.get('registryNumber', ''))}</dd></div>
        </dl>
      </aside>
    </div>
  </div>
"""


def render_ice_schedule_page(pages):
    schedule = pages["iceSchedule"]
    asset = html_lib.escape(str(schedule.get("asset", "")).lstrip("/"), quote=True)
    asset_type = schedule.get("assetType", "")
    modified = str(schedule.get("modified", ""))[:10]
    modified_label = ""
    if modified:
        try:
            modified_date = date.fromisoformat(modified)
            modified_label = article_date_label(modified_date)
        except ValueError:
            modified_label = html_lib.escape(modified)

    if asset and asset_type == "pdf":
        media = (
            f'<iframe class="ice-schedule-frame" src="{asset}" '
            'title="Aktuálny rozpis ľadu HK Brezno"></iframe>'
        )
    elif asset and asset_type == "image":
        media = f'<img class="ice-schedule-image" src="{asset}" alt="Aktuálny rozpis ľadu HK Brezno">'
    else:
        media = '<p class="ice-schedule-empty">Rozpis ľadu momentálne nie je zverejnený.</p>'

    action = ""
    if asset:
        label = "Otvoriť PDF" if asset_type == "pdf" else "Otvoriť v plnej veľkosti"
        action = f'<a class="ice-schedule-open" href="{asset}" target="_blank" rel="noopener noreferrer">{label}</a>'
    meta = f'Aktualizované {modified_label}' if modified_label else ''
    return f"""
  <div>
    <div class="match-hero">
      <div>Aktuálny týždenný program</div>
      <h1>ROZPIS ĽADU</h1>
    </div>
    <div class="ice-schedule-page">
      <div class="ice-schedule-heading">
        <div><div class="section-kicker">Zimný štadión Brezno</div><h2>ROZPIS ĽADOVEJ PLOCHY</h2></div>
        {action}
      </div>
      <div class="ice-schedule-media">{media}</div>
      {f'<div class="ice-schedule-meta">{meta}</div>' if meta else ''}
    </div>
  </div>
"""


def match_logo(path):
    return html_lib.escape(path.lstrip("/"), quote=True)


def render_match_team(name, logo, side):
    safe_name = html_lib.escape(name)
    safe_logo = match_logo(logo)
    return (
        f'<div class="match-team match-team-{side}">'
        f'<img src="{safe_logo}" alt="Logo {safe_name}" loading="lazy">'
        f'<span>{safe_name}</span></div>'
    )


def render_match_page(schedule):
    matches = schedule["matches"]
    today = date.today()
    upcoming = [m for m in matches if date.fromisoformat(m["date"]) >= today]
    featured = upcoming[0] if upcoming else matches[-1]
    featured_date = date.fromisoformat(featured["date"])
    featured_location = "Doma" if featured["location"] == "home" else "Vonku"
    featured_html = f"""
    <div class="match-next">
      <div class="match-next-label">Najbližší zápas · {featured_location}</div>
      <div class="match-next-teams">
        {render_match_team(featured['home'], featured['homeLogo'], 'home')}
        <div class="match-next-center">
          <strong>{html_lib.escape(featured['time'])}</strong>
          <span>{SK_DAYS[featured_date.weekday()]} {featured_date.day}. {featured_date.month}. {featured_date.year}</span>
          <small>{html_lib.escape(featured['venue'])}</small>
        </div>
        {render_match_team(featured['away'], featured['awayLogo'], 'away')}
      </div>
      <a class="match-source-link" href="{html_lib.escape(featured['sourceUrl'], quote=True)}" target="_blank" rel="noopener noreferrer">Detail zápasu na Hockey Slovakia</a>
    </div>"""

    groups = []
    current_month = None
    for match in matches:
        match_date = date.fromisoformat(match["date"])
        month_key = (match_date.year, match_date.month)
        if month_key != current_month:
            if current_month is not None:
                groups.append("</div>")
            current_month = month_key
            groups.append(
                f'<div class="match-month"><h2>{SK_MONTHS[match_date.month - 1]} '
                f'{match_date.year}</h2>'
            )
        location = "Doma" if match["location"] == "home" else "Vonku"
        location_class = "home" if match["location"] == "home" else "away"
        past_class = " is-past" if match_date < today else ""
        safe_url = html_lib.escape(match["sourceUrl"], quote=True)
        groups.append(f"""
        <a class="match-row{past_class}" href="{safe_url}" target="_blank" rel="noopener noreferrer" aria-label="{html_lib.escape(match['home'])} proti {html_lib.escape(match['away'])}, {match_date.day}. {match_date.month}. {match_date.year}">
          <div class="match-date"><strong>{match_date.day}. {match_date.month}.</strong><span>{SK_DAYS[match_date.weekday()]}</span></div>
          <div class="match-pair">
            {render_match_team(match['home'], match['homeLogo'], 'home')}
            <span class="match-vs">VS</span>
            {render_match_team(match['away'], match['awayLogo'], 'away')}
          </div>
          <div class="match-info"><strong>{html_lib.escape(match['time'])}</strong><span>{html_lib.escape(match['venue'])}</span></div>
          <span class="match-location {location_class}">{location}</span>
        </a>""")
    if current_month is not None:
        groups.append("</div>")

    source = html_lib.escape(schedule["source"], quote=True)
    updated = html_lib.escape(schedule["updatedAt"])
    return f"""
  <div>
    <div class="match-hero">
      <div>Sezóna {html_lib.escape(schedule['season'])} · {html_lib.escape(schedule['competition'])}</div>
      <h1>ZÁPASY A-TÍMU</h1>
    </div>
    <div class="match-page">
      {featured_html.strip()}
      <div class="match-calendar-heading"><h2>VŠETKY ZÁPASY A-TÍMU</h2><span>Doma aj vonku · bez výsledkov</span></div>
      <div class="match-calendar">{''.join(groups)}</div>
      <div class="match-calendar-source">Aktualizované {updated} · <a href="{source}" target="_blank" rel="noopener noreferrer">Oficiálny program Hockey Slovakia</a></div>
    </div>
  </div>
"""


def render_home_schedule(schedule):
    today = date.today()
    upcoming = [m for m in schedule["matches"] if date.fromisoformat(m["date"]) >= today]
    featured = upcoming[0] if upcoming else schedule["matches"][-1]
    match_date = date.fromisoformat(featured["date"])

    def home_team(name, logo, role):
        safe_name = html_lib.escape(name)
        return f"""
          <div style="display: flex; align-items: center; gap: 18px">
            <div style="width: 62px; height: 62px; flex: 0 0 62px; background: #fff; display: grid; place-items: center; border: 1px solid #2B4C7E"><img src="{match_logo(logo)}" alt="Logo {safe_name}" style="width: 50px; height: 50px; object-fit: contain"></div>
            <div><div style="font-family: 'Barlow Condensed', sans-serif; font-weight: 800; color: #fff; font-size: 18px">{safe_name}</div><div style="font-family: 'Barlow Condensed', sans-serif; color: #8C9AB0; letter-spacing: .14em; text-transform: uppercase; font-size: 13px">{role}</div></div>
          </div>"""

    feature = f"""
    <div style="background: linear-gradient(112deg, #0D2242 0%, #14315C 52%, #1C4074 100%); padding: 0 48px; display: grid; grid-template-columns: 1.15fr 1fr; gap: 0; align-items: stretch; border-bottom: 1px solid #21406E">
      <div style="padding: 38px 48px 38px 0; border-right: 1px solid #21406E">
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 20px"><span style="width: 8px; height: 8px; background: #CE1126; border-radius: 50%; animation: hkPulse 1.6s infinite"></span><span style="font-family: 'Barlow Condensed', sans-serif; color: #CE1126; letter-spacing: .2em; text-transform: uppercase; font-size: 13px; font-weight: 700">Najbližší zápas A tímu seniorov</span></div>
        <div style="display: flex; align-items: center; gap: 28px">
          {home_team(featured['home'], featured['homeLogo'], 'Domáci').strip()}
          <span style="font-family: 'Barlow Condensed', sans-serif; font-weight: 800; color: #CE1126; font-size: 22px">VS</span>
          {home_team(featured['away'], featured['awayLogo'], 'Hostia').strip()}
        </div>
        <div style="display: flex; gap: 28px; margin-top: 24px; font-family: 'Barlow Condensed', sans-serif; color: #C3C9D2; letter-spacing: .1em; text-transform: uppercase; font-size: 15px"><span>{SK_DAYS[match_date.weekday()]} {match_date.day}. {match_date.month}. {match_date.year} · {html_lib.escape(featured['time'])}</span><span style="color: #3A4C68">|</span><span>{html_lib.escape(featured['venue'])}</span></div>
      </div>
      <div style="padding: 38px 0 38px 48px; display: flex; flex-direction: column; justify-content: center">
        <div style="font-family: 'Barlow Condensed', sans-serif; color: #8C9AB0; letter-spacing: .2em; text-transform: uppercase; font-size: 13px; margin-bottom: 18px">Do zápasu zostáva</div>
        <div style="display: flex; gap: 12px">
          <div style="background: #07172C; border-top: 3px solid #CE1126; padding: 16px 0; width: 92px; text-align: center"><div style="font-family: 'Barlow Condensed', sans-serif; font-weight: 800; color: #fff; font-size: 34px; line-height: 1">{{{{ cd.d }}}}</div><div style="font-family: 'Barlow Condensed', sans-serif; color: #8C9AB0; letter-spacing: .16em; text-transform: uppercase; font-size: 12px; margin-top: 6px">Dní</div></div>
          <div style="background: #07172C; border-top: 3px solid #CE1126; padding: 16px 0; width: 92px; text-align: center"><div style="font-family: 'Barlow Condensed', sans-serif; font-weight: 800; color: #fff; font-size: 34px; line-height: 1">{{{{ cd.h }}}}</div><div style="font-family: 'Barlow Condensed', sans-serif; color: #8C9AB0; letter-spacing: .16em; text-transform: uppercase; font-size: 12px; margin-top: 6px">Hodín</div></div>
          <div style="background: #07172C; border-top: 3px solid #CE1126; padding: 16px 0; width: 92px; text-align: center"><div style="font-family: 'Barlow Condensed', sans-serif; font-weight: 800; color: #fff; font-size: 34px; line-height: 1">{{{{ cd.m }}}}</div><div style="font-family: 'Barlow Condensed', sans-serif; color: #8C9AB0; letter-spacing: .16em; text-transform: uppercase; font-size: 12px; margin-top: 6px">Minút</div></div>
          <div style="background: #07172C; border-top: 3px solid #CE1126; padding: 16px 0; width: 92px; text-align: center"><div style="font-family: 'Barlow Condensed', sans-serif; font-weight: 800; color: #CE1126; font-size: 34px; line-height: 1">{{{{ cd.s }}}}</div><div style="font-family: 'Barlow Condensed', sans-serif; color: #8C9AB0; letter-spacing: .16em; text-transform: uppercase; font-size: 12px; margin-top: 6px">Sekúnd</div></div>
        </div>
      </div>
    </div>"""

    ticker_matches = upcoming[:4] if upcoming else schedule["matches"][-4:]
    ticker_items = []
    for match in ticker_matches:
        item_date = date.fromisoformat(match["date"])
        location = "doma" if match["location"] == "home" else "vonku"
        ticker_items.append(
            f'<span><strong style="color: #fff; font-family: \'Barlow Condensed\', sans-serif; font-weight: 800; font-size: 14px">{item_date.day}. {item_date.month}. · {html_lib.escape(match["time"])}</strong> '
            f'{html_lib.escape(match["opponent"])} · {location}</span>'
        )
    ticker = (
        '<div style="padding: 22px 48px; display: flex; align-items: center; gap: 30px; '
        'overflow: hidden; background: #07172C">'
        '<span style="font-family: \'Barlow Condensed\', sans-serif; font-weight: 800; color: #fff; font-size: 13px; '
        'letter-spacing: .06em; background: #CE1126; padding: 8px 14px; white-space: nowrap">'
        'ĎALŠIE ZÁPASY A TÍMU SENIOROV</span><div style="display: flex; gap: 28px; align-items: center; '
        'font-family: \'Barlow Condensed\', sans-serif; font-size: 16px; color: #C3C9D2; '
        'white-space: nowrap">' + '<span style="color: #2B4C7E">/</span>'.join(ticker_items) + '</div></div>'
    )
    return feature, ticker


def next_match_target(schedule):
    today = date.today()
    upcoming = [m for m in schedule["matches"] if date.fromisoformat(m["date"]) >= today]
    match = upcoming[0] if upcoming else schedule["matches"][-1]
    return f"{match['date']}T{match['time']}:00"


def page_shell(article, canonical, body_html):
    safe_title = html_lib.escape(article["title"])
    safe_meta_title = html_lib.escape(f"{article['title']} | HK Brezno")
    safe_description = html_lib.escape(article["description"])
    safe_canonical = html_lib.escape(canonical)
    category = html_lib.escape(article_category(article))
    author = html_lib.escape(article["author"])
    cover = ""
    social_image = ""
    if article.get("cover"):
        cover_path = html_lib.escape(article["cover"], quote=True)
        cover = f'<img class="article-cover" src="{cover_path}" alt="{safe_title}">'
        social_image = f'<meta property="og:image" content="{html_lib.escape(SITE_URL + article["cover"], quote=True)}">'
    return f"""<!DOCTYPE html>
<html lang="sk">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{safe_meta_title}</title>
<meta name="description" content="{safe_description}">
<meta property="og:title" content="{safe_meta_title}">
<meta property="og:description" content="{safe_description}">
<meta property="og:type" content="article">
<meta property="article:published_time" content="{article['date'].isoformat()}">
{social_image}
<link rel="canonical" href="{safe_canonical}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="">
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&amp;family=Barlow+Condensed:wght@500;600;700&amp;family=Barlow:wght@400;500;600;700&amp;display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:#E7ECF1;color:#0B1B33;font-family:'Barlow',system-ui,sans-serif;line-height:1.65}}
a{{color:#CE1126;text-decoration:none}}a:hover{{color:#9E0C1C}}
.top{{background:linear-gradient(112deg,#0D2242 0%,#14315C 52%,#1C4074 100%);color:#fff;border-bottom:3px solid #CE1126}}
.wrap{{max-width:940px;margin:0 auto;padding:28px 22px}}
.brand{{display:flex;align-items:center;gap:12px;color:#fff;font-family:'Barlow Condensed',sans-serif;font-weight:800;letter-spacing:.02em}}
.brand:hover{{color:#fff}}
.brand img{{width:48px;height:48px}}
.hero{{padding:58px 22px 50px}}
.eyebrow{{font-family:'Barlow Condensed',sans-serif;color:#CE1126;letter-spacing:.2em;text-transform:uppercase;font-weight:700;font-size:13px}}
h1{{font-family:'Barlow Condensed',sans-serif;font-weight:800;font-size:clamp(36px,8vw,64px);line-height:.98;margin:12px 0 18px;letter-spacing:0}}
main{{background:#fff;margin:34px auto 60px;max-width:880px;padding:42px clamp(22px,5vw,58px);box-shadow:0 14px 34px rgba(11,27,51,.12)}}
main h1{{font-size:38px}}main h2{{font-family:'Barlow Condensed',sans-serif;font-weight:800;margin-top:34px}}main p{{font-size:18px;color:#334155}}main li{{font-size:18px;color:#334155;margin:7px 0}}
main img{{max-width:100%;height:auto}}main figure{{margin:28px 0}}main figcaption{{color:#6E7C90;font-size:14px}}
main blockquote{{margin:28px 0;padding:4px 0 4px 22px;border-left:4px solid #CE1126;color:#334155}}
.article-cover{{display:block;width:100%;max-height:500px;object-fit:cover;margin:0 0 34px}}
.article-source{{margin-top:42px;padding-top:22px;border-top:1px solid #E1E6EC;color:#6E7C90;font-size:14px}}
.meta{{color:#CBD5E1;font-family:'Barlow Condensed',sans-serif;letter-spacing:.12em;text-transform:uppercase;font-weight:700}}
</style>
</head>
<body>
<header class="top">
  <a class="wrap brand" href="/"><img src="/assets/logo-hk-brezno.png" alt="HK Brezno"><span>HK Brezno</span></a>
  <div class="wrap hero">
    <div class="eyebrow">{category}</div>
    <h1>{safe_title}</h1>
    <div class="meta">{article_date_label(article['date'])} · {author} · {article_reading_minutes(article)} min čítania</div>
  </div>
</header>
<main>
{cover}
{body_html}
</main>
</body>
</html>
"""


def generate_article_pages(articles):
    article_root = HERE / "aktuality"
    if article_root.exists():
        shutil.rmtree(article_root)
    for article in articles:
        out_dir = article_root / article["slug"]
        out_dir.mkdir(parents=True, exist_ok=True)
        body_html = article["bodyHtml"] or markdown_to_html(article["body"])
        canonical = f"{SITE_URL}/aktuality/{article['slug']}/"
        page = page_shell(article, canonical, body_html)
        (out_dir / "index.html").write_text(page, encoding="utf-8")


def generate_seo_files(articles, schedule):
    content_dates = [date.fromisoformat(schedule["updatedAt"])]
    content_dates.extend(article["date"] for article in articles)
    urls = [(f"{SITE_URL}/", max(content_dates).isoformat())]
    urls.extend(
        (f"{SITE_URL}/aktuality/{article['slug']}/", article["date"].isoformat())
        for article in articles
    )
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>',
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url, last_modified in urls:
        sitemap.append("  <url>")
        sitemap.append(f"    <loc>{html_lib.escape(url)}</loc>")
        sitemap.append(f"    <lastmod>{last_modified}</lastmod>")
        sitemap.append("  </url>")
    sitemap.append("</urlset>")
    (HERE / "sitemap.xml").write_text("\n".join(sitemap) + "\n", encoding="utf-8")
    (HERE / "robots.txt").write_text(
        "User-agent: *\nDisallow: /\n\n"
        f"Sitemap: {SITE_URL}/sitemap.xml\n",
        encoding="utf-8",
    )


def sync_public_assets():
    if not PUBLIC.exists():
        return
    for child in PUBLIC.iterdir():
        if child.name.startswith("."):
            continue
        target = HERE / child.name
        if child.is_dir():
            target.mkdir(exist_ok=True)
            for src in child.rglob("*"):
                if src.is_dir() or src.name.startswith("."):
                    continue
                rel = src.relative_to(child)
                dst = target / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
        else:
            shutil.copy2(child, target / child.name)


# ---------------------------------------------------------------- 0. načítanie
articles = validate_content()
wordpress_pages = apply_ice_schedule_override(load_wordpress_pages())
schedule = load_match_schedule()
match_target = next_match_target(schedule)
sync_public_assets()

if not SRC.exists():
    fail(f"chýba {SRC.name} — najprv stiahni .dc.html z design projektu")
src = SRC.read_text(encoding='utf-8')

m = re.search(r'<helmet>(.*?)</helmet>', src, re.S)
if not m:
    fail("v zdroji nie je <helmet> blok")
helmet = m.group(1)

m = re.search(r'</helmet>(.*?)</x-dc>', src, re.S)
if not m:
    fail("v zdroji nie je telo medzi </helmet> a </x-dc>")
body = m.group(1)

home_feature, home_ticker = render_home_schedule(schedule)
for start, end, replacement in (
    ("HOME_NEXT_MATCH_START", "HOME_NEXT_MATCH_END", ""),
    ("HOME_MATCH_TICKER_START", "HOME_MATCH_TICKER_END", ""),
    ("HOME_ARTICLES_START", "HOME_ARTICLES_END",
     render_home_articles(articles) + home_feature + home_ticker),
):
    body, count = re.subn(
        rf'[ \t]*<!-- {start} -->.*?<!-- {end} -->',
        replacement.strip(),
        body,
        flags=re.S,
    )
    if count != 1:
        fail(f"očakával som 1 blok {start}, našiel {count}")

body, n_home_removed = re.subn(
    r'\s*<!-- HOME_REMOVED_START -->.*?<!-- HOME_REMOVED_END -->',
    '',
    body,
    flags=re.S,
)
if n_home_removed != 1:
    fail(f"očakával som 1 blok odstráneného obsahu domov, našiel {n_home_removed}")

# Zápasy sa generujú z Gitom spravovaného JSON-u; staré vzorové skóre zo
# zdrojového canvasu sa do výsledku vôbec nedostane.
body, n_matches_page = re.subn(
    r'<sc-if value="\{\{ isZapasy \}\}">.*?</sc-if>',
    '<sc-if value="{{ isZapasy }}">' + render_match_page(schedule) + '</sc-if>',
    body,
    flags=re.S,
)
if n_matches_page != 1:
    fail(f"očakával som 1 sekciu zápasov, našiel {n_matches_page}")

body, n_news_page = re.subn(
    r'<sc-if value="\{\{ isNovinky \}\}">.*?</sc-if>',
    '<sc-if value="{{ isNovinky }}">' + render_news_page(articles) + '</sc-if>',
    body,
    flags=re.S,
)
if n_news_page != 1:
    fail(f"očakával som 1 sekciu noviniek, našiel {n_news_page}")

body, n_club_page = re.subn(
    r'<sc-if value="\{\{ isKlub \}\}">.*?</sc-if>',
    '<sc-if value="{{ isKlub }}">' + render_club_page(wordpress_pages) + '</sc-if>',
    body,
    flags=re.S,
)
if n_club_page != 1:
    fail(f"očakával som 1 sekciu klubu, našiel {n_club_page}")

body, n_ice_page = re.subn(
    r'<sc-if value="\{\{ isRozpisladu \}\}">.*?</sc-if>',
    '<sc-if value="{{ isRozpisladu }}">' + render_ice_schedule_page(wordpress_pages) + '</sc-if>',
    body,
    flags=re.S,
)
if n_ice_page != 1:
    fail(f"očakával som 1 sekciu rozpisu ľadu, našiel {n_ice_page}")

# Zrušené podstránky sa odstránia ešte pred spracovaním routovania.
for removed_page in ("Tabulka", "Eshop", "Supiska", "Stadion"):
    body, count = re.subn(
        rf'\s*<sc-if value="\{{\{{ is{removed_page} \}}\}}">.*?</sc-if>',
        '',
        body,
        flags=re.S,
    )
    if count != 1:
        fail(f"očakával som 1 sekciu is{removed_page}, našiel {count}")

# z helmetu vyhodíme runtime image-slotu, štýly a fonty si ponecháme
helmet = re.sub(r'<script[^>]*image-slot\.js[^>]*>\s*</script>', '', helmet)
fonts = "\n".join(l for l in helmet.splitlines()
                  if 'fonts.googleapis' in l or 'fonts.gstatic' in l)
m = re.search(r'<style>(.*?)</style>', helmet, re.S)
base_css = m.group(1).strip() if m else ''


# ------------------------------------------------------------- 1. sc-for
def expand_roster(match):
    inner = match.group(1)
    out = []
    for i, (num, pos, name, age, gp, pts) in enumerate(ROSTER):
        row = inner
        for key, val in (('num', num), ('pos', pos), ('name', name),
                         ('age', age), ('gp', gp), ('pts', pts),
                         ('slot', f'r-{i}')):
            row = row.replace('{{ p.%s }}' % key, str(val))
        out.append(row)
    return "".join(out)


body, n = re.subn(r'<sc-for\b[^>]*>(.*?)</sc-for>', expand_roster, body, flags=re.S)
if n != 0:
    fail(f"po odstránení súpisky nemal zostať sc-for, našiel {n}")


# -------------------------------------------------------------- 2. sc-if
def transform_sc_if(text):
    """Nahradí sc-if bloky sekciami stránok / obalom prilepenej navigácie."""
    out, stack, pos = [], [], 0
    token = re.compile(r'<sc-if\b((?:[^>"]|"[^"]*")*)>|</sc-if>')
    for t in token.finditer(text):
        out.append(text[pos:t.start()])
        pos = t.end()
        if t.group(0).startswith('</'):
            if not stack:
                fail("nepárový </sc-if>")
            out.append(stack.pop())
            continue
        attrs = t.group(1)
        cond = re.search(r'value="\{\{\s*(\w+)\s*\}\}"', attrs)
        if not cond:
            fail(f"sc-if bez rozpoznanej podmienky: {attrs}")
        name = cond.group(1)
        if name == 'isStuck':
            out.append('<span data-stuck>')
            stack.append('</span>')
        elif name.startswith('is'):
            page = name[2:].lower()
            if page not in PAGES:
                fail(f"neznáma stránka v sc-if: {name}")
            out.append(f'<section class="pg" data-pg="{page}">')
            stack.append('</section>')
        else:
            fail(f"neznáma sc-if podmienka: {name}")
    out.append(text[pos:])
    if stack:
        fail("neuzavretý <sc-if>")
    return "".join(out)


body = transform_sc_if(body)


# ------------------------------------------- 3. atribúty na start tagoch
def transform_tag(m):
    tag, attrs, selfclose = m.group(1), m.group(2), m.group(3)

    # onClick="{{ go.xxx }}" -> data-go="xxx" (obsluha je v externom site.js)
    attrs = re.sub(r'\sonClick="\{\{\s*go\.(\w+)\s*\}\}"',
                   lambda g: f' data-go="{g.group(1)}"', attrs)

    # aktívna farba položky menu -> statická + marker data-nav
    nav_item = re.search(r'\{\{\s*c\.(\w+)\s*\}\}', attrs)
    if nav_item:
        attrs = attrs.replace('{{ c.%s }}' % nav_item.group(1), '#A9B7CB')
        attrs += f' data-nav="{nav_item.group(1)}"'

    # podčiarknutie aktívnej položky -> transparent + marker data-u
    if re.search(r'\{\{\s*u\.\w+\s*\}\}', attrs):
        attrs = re.sub(r'\{\{\s*u\.\w+\s*\}\}', 'transparent', attrs)
        attrs += ' data-u'

    # {{ nav.* }} -> deklarácie preberá CSS (data-navbar + .is-stuck)
    if re.search(r'\{\{\s*nav\.\w+\s*\}\}', attrs):
        attrs = re.sub(r'\s*[a-z-]+:\s*\{\{\s*nav\.\w+\s*\}\};?', '', attrs)
        attrs += ' data-navbar'

    # style-hover -> data-hv + vygenerované pravidlo
    hv = re.search(r'\sstyle-hover="([^"]*)"', attrs)
    if hv:
        decls = [d.strip() for d in hv.group(1).split(';') if d.strip()]
        hover_rules.append("; ".join(d + ' !important' for d in decls))
        attrs = attrs.replace(hv.group(0), f' data-hv="{len(hover_rules) - 1}"')

    # pomocné atribúty design canvasu
    attrs = re.sub(r'\shint-placeholder-\w+="[^"]*"', '', attrs)

    # fotky trénerov: ak súbor chýba, nechaj presvitať podklad karty
    if tag == 'img' and 'assets/trener-' in attrs:
        attrs += ' onerror="this.remove()"'

    # ---- responzívne markery -----------------------------------------
    # Priradí data-r tokeny pre elementy, ktoré media queries menia na
    # mobile/tablete. Inline štýly majú vysokú špecificitu, takže pravidlá
    # nižšie používajú !important a cielia na tieto stabilné markery.
    style = re.search(r'\sstyle="([^"]*)"', attrs)
    if style:
        s = style.group(1)
        tokens = []
        # fluidný obsahový wrapper (fixná šírka 1440px -> max-width)
        if 'width: 1440px; margin: 0 auto' in s:
            attrs = attrs.replace('width: 1440px; margin: 0 auto',
                                  'width: 100%; max-width: 1440px; margin: 0 auto')
            tokens.append('wrap')
        # horizontálny padding sekcií (0 48px) -> menší na mobile
        if re.search(r'padding:\s*0 48px', s):
            tokens.append('pad')
        if re.search(r'padding:\s*(\d+)px 48px', s):
            tokens.append('padx')
        # akýkoľvek grid -> na mobile jeden stĺpec (okrem dekoratívnych ✕)
        if 'grid-template-columns:' in s and 'repeat(5, 22px)' not in s \
                and 'repeat(4, 22px)' not in s:
            tokens.append('grid')
        # dátové tabuľky s pevnými px stĺpcami (súpiska) alebo tabuľka ligy
        # -> vodorovný scroll (nemá zmysel ich lámať do stĺpca)
        if re.search(r'grid-template-columns:\s*\d+px 1fr(?: \d+px)+', s) \
                or '1.2fr repeat(5, 1fr)' in s:
            tokens.append('wide')
        # obrí nadpis hero -> plynulé zmenšenie
        if 'font-size: 116px' in s:
            tokens.append('h1')
        # hlavičkový blok (obsahuje logo-riadok, veľké logo a navigáciu).
        # Na mobile mu zrušíme rezervovanú výšku 118px, ale necháme ho v toku,
        # lebo navigácia (fixná lišta) je jeho potomok — display:none by ju
        # tiež odstránil z renderu.
        if 'z-index: 5; height: 118px' in s:
            tokens.append('header')
        # horný riadok hlavičky (text sezóny + CTA) -> na mobile skry
        if 'height: 76px' in s and 'justify-content: space-between' in s:
            tokens.append('hdrhide')
        # veľké centrované logo v hlavičke -> na mobile skry (logo je v lište)
        if 'left: 50%; top: 2px; transform: translateX(-50%); z-index: 7' in s:
            tokens.append('hdrhide')
        # prvky s pevnou pixelovou šírkou, ktoré by pretiekli
        if re.search(r'width:\s*760px', s):
            tokens.append('fixw')
        # dekoratívny pruh vpravo (right: 0; width: 160px) -> skry
        if 'right: 0; top: 0; width: 160px' in s:
            tokens.append('deco')
        # dekoratívne, absolútne umiestnené logá s nízkou opacitou (presvitajú) -> skry
        if 'opacity: .07' in s and ('left: 320px' in s or 'width: 780px' in s):
            tokens.append('deco')
        # veľké vertikálne padding-y hero obsahu -> zmenši
        if 'padding: 96px 48px 130px' in s:
            tokens.append('heropad')
        # nezalamovacie riadky (VS zápas, ticker výsledkov) -> na mobile
        # buď zalom, alebo nechaj scrollovať; označíme ich ako 'row'
        if 'white-space: nowrap' in s and ('gap: 34px' in s or 'gap: 22px' in s
                                           or "letter-spacing: .04em" in s):
            tokens.append('row')
        if tokens:
            attrs += ' data-r="%s"' % " ".join(tokens)

    return f'<{tag}{attrs}{selfclose}>'


body = TAG_RE.sub(transform_tag, body)


# -------------------------------------------------------- 4. image-slot
def transform_slot(m):
    label = re.search(r'placeholder="([^"]*)"', m.group(1))
    label = label.group(1) if label else 'Foto'
    return f'<div class="slot"><span>{label}</span></div>'


body, n_slots = re.subn(
    r'<image-slot\b((?:[^>"]|"[^"]*")*)>\s*</image-slot>', transform_slot, body)


# ------------------------------------------------------------ 5. countdown
for unit in ('d', 'h', 'm', 's'):
    body = body.replace('{{ %s }}' % ('cd.' + unit),
                        f'<span data-cd="{unit}">--</span>')

# 6. cesty k obrázkom a kontrola, že nezostala žiadna nevyriešená väzba
body = body.replace('src="./assets/', 'src="assets/')
leftover = re.findall(r'\{\{[^}]*\}\}', body)
if leftover:
    fail(f"nevyriešené väzby: {sorted(set(leftover))[:8]}")
if '<sc-' in body or '<image-slot' in body or 'style-hover' in body:
    fail("v tele zostali prvky design canvasu")


# ------------------------------------------------------------ 7. výstup
page_css = "\n".join(
    f'html[data-page="{p}"] [data-pg="{p}"]{{display:block}}\n'
    f'html[data-page="{p}"] [data-nav="{p}"]{{color:#fff !important}}\n'
    f'html[data-page="{p}"] [data-nav="{p}"] [data-u]{{background:#CE1126 !important}}'
    for p in PAGES)

hover_css = "\n".join(f'[data-hv="{i}"]:hover{{{r}}}' for i, r in enumerate(hover_rules))

site_js = f"""(function () {{
  'use strict';
  var PAGES = {json.dumps(PAGES)};

  function go(page, updateHistory) {{
    if (PAGES.indexOf(page) === -1) return;
    document.documentElement.dataset.page = page;
    document.documentElement.classList.remove('nav-open');
    if (updateHistory !== false) {{
      var url = page === 'domov' ? location.pathname : location.pathname + '?page=' + encodeURIComponent(page);
      history.pushState({{ page: page }}, '', url);
    }}
    window.scrollTo(0, 0);
    onScroll();
  }}

  var requestedPage = new URLSearchParams(location.search).get('page');
  if (requestedPage && PAGES.indexOf(requestedPage) !== -1) go(requestedPage, false);
  window.addEventListener('popstate', function () {{
    var page = new URLSearchParams(location.search).get('page') || 'domov';
    go(page, false);
  }});

  document.addEventListener('click', function (event) {{
    var trigger = event.target.closest('[data-go]');
    if (!trigger) return;
    event.preventDefault();
    go(trigger.dataset.go);
  }});

  var bar = document.querySelector('[data-navbar]');
  if (bar) {{
    var burger = document.createElement('button');
    burger.className = 'hk-burger';
    burger.type = 'button';
    burger.setAttribute('aria-label', 'Menu');
    burger.setAttribute('aria-expanded', 'false');
    for (var i = 0; i < 3; i += 1) burger.appendChild(document.createElement('span'));
    burger.addEventListener('click', function () {{
      var isOpen = document.documentElement.classList.toggle('nav-open');
      burger.setAttribute('aria-expanded', String(isOpen));
    }});
    bar.appendChild(burger);
    document.addEventListener('click', function (event) {{
      if (!document.documentElement.classList.contains('nav-open')) return;
      if (bar.contains(event.target)) return;
      document.documentElement.classList.remove('nav-open');
      burger.setAttribute('aria-expanded', 'false');
    }});
  }}

  function onScroll() {{
    var y = window.scrollY || document.documentElement.scrollTop || 0;
    if (bar) bar.classList.toggle('is-stuck', y > 120);
  }}
  window.addEventListener('scroll', onScroll, {{ passive: true }});
  onScroll();

  var target = new Date('{match_target}').getTime();
  var cells = document.querySelectorAll('[data-cd]');
  function pad(number) {{ return String(number).padStart(2, '0'); }}
  function tick() {{
    var diff = Math.max(0, target - Date.now());
    var values = {{
      d: pad(Math.floor(diff / 86400000)),
      h: pad(Math.floor(diff / 3600000) % 24),
      m: pad(Math.floor(diff / 60000) % 60),
      s: pad(Math.floor(diff / 1000) % 60)
    }};
    cells.forEach(function (element) {{ element.textContent = values[element.dataset.cd]; }});
  }}
  tick();
  window.setInterval(tick, 1000);
}})();
"""

html = f"""<!DOCTYPE html>
<html lang="sk" data-page="domov">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>HK Brezno — Rytieri z Brezna</title>
<meta name="description" content="Nový statický web HK Brezno pre aktuality, tímy, zápasy, rodičov a nábor mladých hokejistov.">
<meta property="og:title" content="HK Brezno — Rytieri z Brezna">
<meta property="og:description" content="Nový statický web HK Brezno pre aktuality, tímy, zápasy, rodičov a nábor mladých hokejistov.">
<meta property="og:type" content="website">
<link rel="canonical" href="{SITE_URL}/">
{fonts}
<style>
{base_css}

/* ---- routovanie stránok ---------------------------------------------- */
.pg {{ display: none }}
{page_css}

/* ---- prilepená navigácia -------------------------------------------- */
[data-navbar] {{ position: absolute; top: auto; bottom: -42px; padding: 0 30px;
                 box-shadow: 0 16px 34px rgba(11,27,51,.35) }}
[data-navbar].is-stuck {{ position: fixed; top: 0; bottom: auto; padding: 0 16px 0 12px;
                          box-shadow: 0 10px 30px rgba(11,27,51,.4) }}
[data-stuck] {{ display: none }}
[data-navbar].is-stuck [data-stuck] {{ display: contents }}

/* ---- miesto pre fotografiu (nahrádza <image-slot>) ------------------ */
.slot {{ position: absolute; inset: 0; display: grid; place-items: center; overflow: hidden;
         background: linear-gradient(180deg, #EEF2F7, #DBE2EB);
         box-shadow: inset 0 0 0 1px rgba(20,49,92,.14) }}
.slot::before {{ content: ""; position: absolute; inset: 0;
                 background: repeating-linear-gradient(115deg, rgba(255,255,255,.55) 0 10px,
                             rgba(255,255,255,0) 10px 26px) }}
.slot span {{ position: relative; max-width: 80%; text-align: center;
              font-family: 'Barlow Condensed', sans-serif; font-size: 13px;
              letter-spacing: .16em; text-transform: uppercase; color: #7C8BA1 }}
.slot span::before {{ content: "◻"; display: block; font-size: 20px; letter-spacing: 0;
                      color: #A7B4C6; margin-bottom: 6px }}

/* ---- hover stavy z design canvasu ----------------------------------- */
{hover_css}

/* ==== RESPONZIVITA ===================================================== */
/* Layout je pôvodne fixný na 1440 px s inline štýlmi (vysoká špecificita),
   preto pravidlá nižšie používajú !important a cielia na data-r markery,
   ktoré pridáva build.py. */

/* obrázok-vodoznak na pozadí nech neprelieza na malých displejoch */
@media (max-width: 1024px) {{
  img[alt=""] {{ max-width: 100% !important; height: auto }}
}}

/* žiadny vodorovný pretok na malých displejoch */
@media (max-width: 1024px) {{
  html, body {{ max-width: 100%; overflow-x: hidden }}
}}

/* --- tablet a menej (<= 1024px) --------------------------------------- */
@media (max-width: 1024px) {{
  [data-r~="pad"]  {{ padding-left: 28px !important; padding-right: 28px !important }}
  [data-r~="padx"] {{ padding-left: 28px !important; padding-right: 28px !important }}
  /* viacstĺpcové mriežky na 2 stĺpce */
  [data-r~="grid"] {{ grid-template-columns: repeat(2, minmax(0, 1fr)) !important }}
  [data-r~="h1"]   {{ font-size: 8.5vw !important }}
  /* nezalamovacie riadky (VS, ticker) nech sa zalomia už na tablete */
  [data-r~="row"] {{ flex-wrap: wrap !important; white-space: normal !important;
                     gap: 16px !important; max-width: 100% }}
  /* dátové tabuľky scrollujú vodorovne aj na tablete */
  [data-r~="wide"] {{ display: block !important; overflow-x: auto !important;
                      -webkit-overflow-scrolling: touch }}
  [data-r~="wide"] > * {{ min-width: 620px }}
}}

/* --- mobil (<= 720px) -------------------------------------------------- */
@media (max-width: 720px) {{
  html, body {{ overflow-x: hidden }}
  [data-r~="pad"]  {{ padding-left: 18px !important; padding-right: 18px !important }}
  [data-r~="padx"] {{ padding-left: 18px !important; padding-right: 18px !important }}

  /* takmer všetky mriežky do jedného stĺpca */
  [data-r~="grid"] {{ grid-template-columns: minmax(0, 1fr) !important }}

  /* tabuľky s pevnými stĺpcami (súpiska/tabuľka) nechaj scrollovať vodorovne */
  [data-r~="wide"] {{
    display: block !important;
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch;
    white-space: nowrap;
  }}
  [data-r~="wide"] > * {{ min-width: 640px }}

  /* hero nadpis a odsadenia */
  [data-r~="h1"] {{ font-size: 46px !important; line-height: .95 !important }}
  [data-r~="heropad"] {{ padding: 40px 18px 56px !important }}

  /* prvky s pevnou šírkou nech sa zmestia */
  [data-r~="fixw"] {{ width: 100% !important; max-width: 100% !important }}
  /* dekoratívne prvky, ktoré by spôsobili vodorovný pretok, skry */
  [data-r~="deco"] {{ display: none !important }}
  /* nezalamovacie riadky nechaj plynúť / scrollovať vodorovne */
  [data-r~="row"] {{
    flex-wrap: wrap !important;
    white-space: normal !important;
    gap: 14px !important;
    max-width: 100%;
  }}

  /* horný info-pás skry (telefón/mail sú v pätičke) */
  body [style*="height: 40px"][style*="border-bottom: 1px solid rgba(20,49,92,.1)"] {{
    display: none !important;
  }}
}}

/* ==== MOBILNÁ NAVIGÁCIA (hamburger) =================================== */
/* Tlačidlo + backdrop vkladá JS; tu je len ich vzhľad a správanie. */
.hk-burger {{ display: none }}
@media (max-width: 900px) {{
  /* schovaj širokú desktopovú lištu a ukáž hamburger */
  [data-navbar] {{
    position: fixed !important; top: 0 !important; left: 0 !important;
    right: 0 !important; bottom: auto !important; transform: none !important;
    width: 100% !important; height: 56px !important;
    padding: 0 16px !important; clip-path: none !important;
    justify-content: space-between !important; z-index: 200 !important;
  }}
  [data-navbar] nav {{
    position: fixed; top: 56px; left: 0; right: 0;
    max-height: calc(100vh - 56px); overflow-y: auto;
    flex-direction: column !important; align-items: stretch !important;
    height: auto !important; gap: 0 !important;
    background: linear-gradient(180deg, #0D2242, #14315C);
    border-bottom: 3px solid #CE1126;
    box-shadow: 0 20px 40px rgba(11,27,51,.5);
    transform: translateY(-120%); transition: transform .25s ease;
  }}
  [data-navbar] nav button, [data-navbar] nav .nav-external {{
    width: 100%; padding: 16px 20px !important;
    flex-direction: row !important; justify-content: flex-start !important;
    border-bottom: 1px solid rgba(255,255,255,.08);
    font-size: 16px !important;
  }}
  [data-navbar] nav button span {{ display: none !important }}  /* podčiarkovač skry */
  html.nav-open [data-navbar] nav {{ transform: translateY(0) }}

  .hk-burger {{
    display: inline-flex; flex-direction: column; justify-content: center;
    gap: 5px; width: 44px; height: 44px; padding: 0 10px; margin-left: auto;
    background: none; border: 0; cursor: pointer; z-index: 210;
  }}
  .hk-burger span {{ display: block; height: 2px; background: #fff; border-radius: 2px;
                     transition: transform .25s ease, opacity .2s ease }}
  html.nav-open .hk-burger span:nth-child(1) {{ transform: translateY(7px) rotate(45deg) }}
  html.nav-open .hk-burger span:nth-child(2) {{ opacity: 0 }}
  html.nav-open .hk-burger span:nth-child(3) {{ transform: translateY(-7px) rotate(-45deg) }}

  /* logo v prilepenej lište nech je vždy vidno vľavo */
  [data-navbar] [data-stuck] {{ display: contents !important }}
  /* CTA tlačidlo v lište skry na mobile (je dostupné v menu / hero) */
  [data-navbar] [data-stuck] button {{ display: none !important }}

  /* hlavička: zruš rezervovanú výšku (navigácia je fixná lišta), ale nechaj
     ju v renderi kvôli potomkovi [data-navbar] */
  [data-r~="header"] {{ height: auto !important; padding: 0 !important }}
  /* logo-riadok a veľké centrované logo skry — nahrádza ich lišta */
  [data-r~="hdrhide"] {{ display: none !important }}

  /* logo v lište je vždy viditeľné vľavo */
  [data-navbar] [data-stuck] {{ display: contents !important }}
  [data-navbar] [data-stuck] img {{ display: block !important; height: 40px !important;
                                    margin-right: auto !important }}

  /* keďže je lišta fixná hore, odsaď obsah pod ňu */
  body {{ padding-top: 56px }}
}}

/* wrapper na mobile nesmie spôsobiť vodorovný pretok */
@media (max-width: 720px) {{
  [data-r~="wrap"] {{ overflow-x: clip !important }}
}}
</style>
</head>
<body>
{body}
<script src="site.js" defer></script>
</body>
</html>
"""

OUT.write_text(html, encoding='utf-8')
(HERE / "site.js").write_text(site_js, encoding="utf-8")
generate_article_pages(articles)
generate_seo_files(articles, schedule)
print(f"OK  {OUT.name}: {len(html)} znakov, {n_slots} fotomiest, "
      f"{len(hover_rules)} hover pravidiel, {len(PAGES)} stránok, "
      f"{len(articles)} publikovaných článkov")
