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

HERE = pathlib.Path(__file__).parent
SRC = HERE / "design-canvas.dc.html"
OUT = HERE / "index.html"

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

hover_rules = []   # index -> CSS deklarácie


def fail(msg):
    sys.exit(f"build.py: {msg}")


# ---------------------------------------------------------------- 0. načítanie
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
<meta name="viewport" content="width=1440">
<title>HK Brezno — Rytieri z Brezna</title>
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
    window.scrollTo(0, 0);
    onScroll();
  }};

  /* prilepenie navigácie po odscrollovaní hlavičky */
  var bar = document.querySelector('[data-navbar]');
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
print(f"OK  {OUT.name}: {len(html)} znakov, {n_slots} fotomiest, "
      f"{len(hover_rules)} hover pravidiel, {len(PAGES)} stránok")
