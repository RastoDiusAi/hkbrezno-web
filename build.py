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
  onClick="{{ go.xxx }}"        -> onclick="go('xxx')"
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
from datetime import date, datetime, timezone

HERE = pathlib.Path(__file__).parent
SRC = HERE / "design-canvas.dc.html"
OUT = HERE / "index.html"
CONTENT = HERE / "content"
PUBLIC = HERE / "public"
SITE_URL = "https://novyweb.smartitbiz.com"

PAGES = ['domov', 'novinky', 'zapasy', 'tabulka', 'timy', 'supiska',
         'klub', 'stadion', 'rodicia', 'partneri', 'eshop', 'prihlaska']

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

MATCH_TARGET = '2026-09-12T17:30:00'   # najbližší zápas z pôvodnej logiky

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
                       ("name", "slug", "active", "order"))
    validate_json_file(CONTENT / "coaches" / "coaches.json",
                       ("name", "role", "active", "order"))
    validate_json_file(CONTENT / "documents" / "documents.json",
                       ("title", "file", "active", "order"))
    return load_articles()


def page_shell(title, description, canonical, body_html):
    safe_title = html_lib.escape(title)
    safe_meta_title = html_lib.escape(f"{title} | HK Brezno")
    safe_description = html_lib.escape(description)
    safe_canonical = html_lib.escape(canonical)
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
<link rel="canonical" href="{safe_canonical}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="">
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&amp;family=Barlow+Condensed:wght@500;600;700&amp;family=Barlow:wght@400;500;600;700&amp;display=swap" rel="stylesheet">
<style>
body{{margin:0;background:#E7ECF1;color:#0B1B33;font-family:'Barlow',system-ui,sans-serif;line-height:1.65}}
a{{color:#CE1126;text-decoration:none}}a:hover{{color:#9E0C1C}}
.top{{background:linear-gradient(112deg,#0D2242 0%,#14315C 52%,#1C4074 100%);color:#fff;border-bottom:3px solid #CE1126}}
.wrap{{max-width:940px;margin:0 auto;padding:28px 22px}}
.brand{{display:flex;align-items:center;gap:12px;font-family:'Archivo Black',sans-serif;letter-spacing:.02em}}
.brand img{{width:48px;height:48px}}
.hero{{padding:58px 22px 50px}}
.eyebrow{{font-family:'Barlow Condensed',sans-serif;color:#CE1126;letter-spacing:.2em;text-transform:uppercase;font-weight:700;font-size:13px}}
h1{{font-family:'Archivo Black',sans-serif;font-size:clamp(36px,8vw,64px);line-height:.98;margin:12px 0 18px;letter-spacing:0}}
main{{background:#fff;margin:34px auto 60px;max-width:880px;padding:42px clamp(22px,5vw,58px);box-shadow:0 14px 34px rgba(11,27,51,.12)}}
main h1{{font-size:38px}}main h2{{font-family:'Archivo Black',sans-serif;margin-top:34px}}main p{{font-size:18px;color:#334155}}main li{{font-size:18px;color:#334155;margin:7px 0}}
.meta{{color:#CBD5E1;font-family:'Barlow Condensed',sans-serif;letter-spacing:.12em;text-transform:uppercase;font-weight:700}}
</style>
</head>
<body>
<header class="top">
  <div class="wrap brand"><img src="/assets/logo-hk-brezno.png" alt="HK Brezno"><span>HK Brezno</span></div>
  <div class="wrap hero">
    <div class="eyebrow">Aktuality</div>
    <h1>{safe_title}</h1>
    <div class="meta">{safe_description}</div>
  </div>
</header>
<main>
{body_html}
</main>
</body>
</html>
"""


def generate_article_pages(articles):
    for article in articles:
        out_dir = HERE / "aktuality" / article["slug"]
        out_dir.mkdir(parents=True, exist_ok=True)
        body_html = markdown_to_html(article["body"])
        canonical = f"{SITE_URL}/aktuality/{article['slug']}/"
        page = page_shell(
            article["title"],
            article["description"],
            canonical,
            body_html,
        )
        (out_dir / "index.html").write_text(page, encoding="utf-8")


def generate_seo_files(articles):
    urls = [f"{SITE_URL}/"]
    urls.extend(f"{SITE_URL}/aktuality/{article['slug']}/" for article in articles)
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>',
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    now = datetime.now(timezone.utc).date().isoformat()
    for url in urls:
        sitemap.append("  <url>")
        sitemap.append(f"    <loc>{html_lib.escape(url)}</loc>")
        sitemap.append(f"    <lastmod>{now}</lastmod>")
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
if n != 1:
    fail(f"očakával som 1 sc-for, našiel {n}")


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

    # onClick="{{ go.xxx }}" -> onclick="go('xxx')"
    attrs = re.sub(r'\sonClick="\{\{\s*go\.(\w+)\s*\}\}"',
                   lambda g: f' onclick="go(\'{g.group(1)}\')"', attrs)

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
  [data-navbar] nav button {{
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
<script>
(function () {{
  var PAGES = {PAGES!r};

  window.go = function (page) {{
    if (PAGES.indexOf(page) === -1) return;
    document.documentElement.dataset.page = page;
    document.documentElement.classList.remove('nav-open');  /* zavri mobilné menu */
    window.scrollTo(0, 0);
    onScroll();
  }};

  /* prilepenie navigácie po odscrollovaní hlavičky */
  var bar = document.querySelector('[data-navbar]');

  /* mobilný hamburger: vloží tlačidlo do lišty a prepína .nav-open */
  if (bar) {{
    var burger = document.createElement('button');
    burger.className = 'hk-burger';
    burger.setAttribute('aria-label', 'Menu');
    burger.innerHTML = '<span></span><span></span><span></span>';
    burger.addEventListener('click', function () {{
      document.documentElement.classList.toggle('nav-open');
    }});
    bar.appendChild(burger);
    /* klik mimo menu ho zavrie */
    document.addEventListener('click', function (e) {{
      if (!document.documentElement.classList.contains('nav-open')) return;
      if (bar.contains(e.target)) return;
      document.documentElement.classList.remove('nav-open');
    }});
  }}
  function onScroll() {{
    var y = window.scrollY || document.documentElement.scrollTop || 0;
    if (bar) bar.classList.toggle('is-stuck', y > 120);
  }}
  window.addEventListener('scroll', onScroll, {{ passive: true }});
  onScroll();

  /* odpočet do najbližšieho zápasu */
  var target = new Date('{MATCH_TARGET}').getTime();
  var cells = document.querySelectorAll('[data-cd]');
  function pad(n) {{ return String(n).padStart(2, '0'); }}
  function tick() {{
    var diff = Math.max(0, target - Date.now());
    var v = {{
      d: pad(Math.floor(diff / 86400000)),
      h: pad(Math.floor(diff / 3600000) % 24),
      m: pad(Math.floor(diff / 60000) % 60),
      s: pad(Math.floor(diff / 1000) % 60)
    }};
    cells.forEach(function (el) {{ el.textContent = v[el.dataset.cd]; }});
  }}
  tick();
  setInterval(tick, 1000);
}})();
</script>
</body>
</html>
"""

OUT.write_text(html, encoding='utf-8')
generate_article_pages(articles)
generate_seo_files(articles)
print(f"OK  {OUT.name}: {len(html)} znakov, {n_slots} fotomiest, "
      f"{len(hover_rules)} hover pravidiel, {len(PAGES)} stránok, "
      f"{len(articles)} publikovaných článkov")
