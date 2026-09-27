# HK Brezno — nový web

Návrh a implementácia novej webovej stránky pre hokejový klub HK Brezno
(nahrádza súčasný WordPress na `hkbrezno.sk`).

## Čo je v repozitári

| Súbor | Čo to je |
|---|---|
| [`index.html`](index.html) | **Implementovaný dizajn** — funkčná stránka s 12 podstránkami, routovaním, prilepenou navigáciou a odpočtom do zápasu. Generovaný z design canvasu. |
| [`build.py`](build.py) | Transpiler: prevedie `design-canvas.dc.html` na samostatný `index.html` bez runtime závislostí. |
| [`design-canvas.dc.html`](design-canvas.dc.html) | Zdrojový design canvas importovaný z projektu na `claude.ai/design`. **Needituje sa priamo** — je to vstup pre `build.py`. |
| [`content/`](content) | Publikačný obsah v Gite: články, tímy, tréneri, partneri, dokumenty. |
| [`public/`](public) | Verejné obrázky a dokumenty pripravené pre budúci Next.js statický export. |
| [`send-form.php`](send-form.php) | Serverový endpoint pre rodičovský formulár na klasickom PHP hostingu, bez databázy. |
| [`NAVRH-STRUKTURY.md`](NAVRH-STRUKTURY.md) | Informačná architektúra a historický návrh. Technologické rozhodnutie je aktualizované podľa aktuálnych pravidiel: Next.js statický export, obsah v Gite, PHP formulár. |
| [`prototyp.html`](prototyp.html) | Skorší vizuálny prototyp (4 obrazovky, responzívny, prepínač Desktop/Mobil) — slúžil na odladenie dizajnového smeru. |
| `assets/` | Logo klubu. Fotografie trénerov chýbajú — pozri nižšie. |

## Zbuildovanie

```bash
python3 build.py
```

Skript nemá žiadne závislosti (iba štandardná knižnica Pythonu 3). Vypíše počet
vygenerovaných podstránok, fotomiest, hover pravidiel a publikovaných článkov.
Pri akejkoľvek nevyriešenej šablónovej väzbe alebo chybnom obsahu zlyhá s jasnou
chybou namiesto tichého prepustenia.

Build zároveň:

- validuje články v `content/articles/**/*.md`,
- generuje detail článku do `aktuality/<slug>/index.html`,
- generuje `sitemap.xml`,
- generuje `robots.txt` s blokovaním indexácie demo subdomény,
- synchronizuje obsah `public/` do web rootu podobne, ako to robí Next.js.

Prezeranie: otvor `index.html` priamo v prehliadači (nepotrebuje server).

### Čo transpiler robí

Design canvas je postavený na runtime `support.js` / `image-slot.js`, ktorý na
produkčnom webe nechceme. `build.py` ho preto odstráni a nahradí:

| Design canvas | Výstup |
|---|---|
| `<helmet>` | skutočný `<head>` |
| `<sc-if value="{{ isXxx }}">` | `<section data-pg="xxx">` + routovanie cez CSS |
| `<sc-if value="{{ isStuck }}">` | `<span data-stuck>` + trieda `.is-stuck` |
| `<sc-for list="{{ roster }}">` | rozbalené nad dátami súpisky (10 hráčov) |
| `onClick="{{ go.xxx }}"` | `onclick="go('xxx')"` |
| `{{ c.xxx }}` / `{{ u.xxx }}` | `data-nav` / `data-u` + aktívny stav z CSS |
| `{{ nav.* }}` | `data-navbar` + `.is-stuck` |
| `{{ cd.d }}` | `<span data-cd="d">` dopočítaný v JS |
| `style-hover="…"` | `data-hv="N"` + vygenerované `:hover` pravidlo |
| `<image-slot placeholder="X">` | `<div class="slot">` — miesto pre fotografiu |

## Stav a čo ďalej

Hotové:

- 12 podstránok: Domov, Novinky, Zápasy, Tabuľka, Tímy, Súpiska, Klub, Štadión,
  Pre rodičov, Partneri, E-shop, Prihláška.
- Routovanie medzi podstránkami, aktívny stav v menu, prilepená navigácia po
  odscrollovaní, živý odpočet do najbližšieho zápasu, 69 hover stavov.
- Základná obsahová štruktúra podľa pravidiel: `content/articles`, `content/pages`,
  `content/teams`, `content/coaches`, `content/partners`, `public/images`,
  `public/documents`, `app`, `components`, `lib/content`.
- Rodičovský formulár odosiela na `send-form.php`; údaje sa neukladajú do
  databázy a SMTP/API tajomstvá nie sú vo frontende.

Zostáva:

1. **Fotografie trénerov** — `assets/trener-1.png` … `trener-8.png` chýbajú.
   Design API ich neprepustilo (limit 256 KiB na súbor), prišli neúplné a preto
   nie sú commitnuté. Karty trénerov sú medzitým prázdne, nie rozbité — obrázok
   sa sám odstráni a presvitá podklad karty. Po doplnení súborov do `assets/`
   sa fotky zobrazia bez zmeny kódu.
2. **48 fotomiest** (`.slot`) čaká na skutočné fotografie z klubu.
3. **Responzivita** — dizajn je zatiaľ fixná plocha 1440 px (tak je navrhnutý
   v canvase). Prepis na mobil je samostatný krok; rodičia web otvárajú
   prevažne na telefóne, takže má vysokú prioritu.
4. **Migrácia na finálnu Next.js aplikáciu** — cieľ je `output: 'export'`,
   bez API routes, middleware, ISR a bez závislosti od Vercelu.
5. **Nasadenie formulára** — pred testovaním treba na hostingu zapnúť HTTPS a
   nastaviť cieľový e-mail cez `HK_FORM_TO` alebo upraviť fallback v
   `send-form.php`.

## Poznámka k obsahu

Texty, súpiska, výsledky, tabuľka a mená v tomto repozitári sú **vzorové dáta**
z dizajnového návrhu, nie skutočné údaje klubu.
