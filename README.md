# HK Brezno — nový web

Návrh a implementácia novej webovej stránky pre hokejový klub HK Brezno
(nahrádza súčasný WordPress na `hkbrezno.sk`).

## Čo je v repozitári

| Súbor | Čo to je |
|---|---|
| [`index.html`](index.html) | **Implementovaný dizajn** — funkčná stránka s 12 podstránkami, routovaním, prilepenou navigáciou a odpočtom do zápasu. Generovaný z design canvasu. |
| [`build.py`](build.py) | Transpiler: prevedie `design-canvas.dc.html` na samostatný `index.html` bez runtime závislostí. |
| [`design-canvas.dc.html`](design-canvas.dc.html) | Zdrojový design canvas importovaný z projektu na `claude.ai/design`. **Needituje sa priamo** — je to vstup pre `build.py`. |
| [`NAVRH-STRUKTURY.md`](NAVRH-STRUKTURY.md) | Návrh informačnej architektúry, obsahových modelov pre CMS, technológie, hostingu a plánu realizácie. |
| [`prototyp.html`](prototyp.html) | Skorší vizuálny prototyp (4 obrazovky, responzívny, prepínač Desktop/Mobil) — slúžil na odladenie dizajnového smeru. |
| `assets/` | Logo klubu. Fotografie trénerov chýbajú — pozri nižšie. |

## Zbuildovanie

```bash
python3 build.py
```

Skript nemá žiadne závislosti (iba štandardná knižnica Pythonu 3). Vypíše počet
vygenerovaných podstránok, fotomiest a hover pravidiel; pri akejkoľvek
nevyriešenej šablónovej väzbe zlyhá s chybou namiesto tichého prepustenia.

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
4. **CMS a hosting** — navrhnuté v [`NAVRH-STRUKTURY.md`](NAVRH-STRUKTURY.md)
   (Astro + Sanity + Cloudflare Pages).

## Poznámka k obsahu

Texty, súpiska, výsledky, tabuľka a mená v tomto repozitári sú **vzorové dáta**
z dizajnového návrhu, nie skutočné údaje klubu.
