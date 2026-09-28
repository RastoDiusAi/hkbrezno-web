# HK Brezno — nový web

Návrh a implementácia novej webovej stránky pre hokejový klub HK Brezno.
Frontend je statický, WordPress zostáva redakčným systémom na písanie a
publikovanie článkov.

## Čo je v repozitári

| Súbor | Čo to je |
|---|---|
| [`index.html`](index.html) | **Implementovaný dizajn** — funkčná stránka s 9 podstránkami, routovaním, prilepenou navigáciou a odpočtom do zápasu. Generovaný z design canvasu a obsahových dát. |
| [`build.py`](build.py) | Transpiler: prevedie `design-canvas.dc.html` na samostatný `index.html` bez runtime závislostí. |
| [`design-canvas.dc.html`](design-canvas.dc.html) | Zdrojový design canvas importovaný z projektu na `claude.ai/design`. **Needituje sa priamo** — je to vstup pre `build.py`. |
| [`content/`](content) | Publikačný obsah v Gite vrátane statického snapshotu publikovaných WordPress článkov. |
| [`public/`](public) | Verejné obrázky, tímové logá a dokumenty pripravené pre budúci Next.js statický export. |
| [`scripts/import_hockey_schedule.py`](scripts/import_hockey_schedule.py) | Import programu A tímu a tímových log z Hockey Slovakia. |
| [`scripts/import_wordpress.py`](scripts/import_wordpress.py) | Import článkov, histórie klubu, kontaktu a rozpisu ľadu z WordPress REST API. |
| [`send-form.php`](send-form.php) | Serverový endpoint pre rodičovský formulár na klasickom PHP hostingu, bez databázy. |
| [`NAVRH-STRUKTURY.md`](NAVRH-STRUKTURY.md) | Informačná architektúra a historický návrh. Technologické rozhodnutie je aktualizované podľa aktuálnych pravidiel: Next.js statický export, obsah v Gite, PHP formulár. |
| [`prototyp.html`](prototyp.html) | Skorší vizuálny prototyp (4 obrazovky, responzívny, prepínač Desktop/Mobil) — slúžil na odladenie dizajnového smeru. |
| `assets/` | Logo klubu. Fotografie trénerov chýbajú — pozri nižšie. |

## Zbuildovanie

```bash
python3 build.py
```

Samotný build používa iba štandardnú knižnicu Pythonu 3. Importéry používajú
balík `certifi` z `requirements.txt`. Build vypíše počet
vygenerovaných podstránok, fotomiest, hover pravidiel a publikovaných článkov.
Pri akejkoľvek nevyriešenej šablónovej väzbe alebo chybnom obsahu zlyhá s jasnou
chybou namiesto tichého prepustenia.

Build zároveň:

- validuje články v `content/articles/**/*.md`,
- generuje detail článku do `aktuality/<slug>/index.html`,
- generuje `sitemap.xml`,
- generuje `robots.txt` s blokovaním indexácie demo subdomény,
- synchronizuje obsah `public/` do web rootu podobne, ako to robí Next.js.

Program A tímu a logá súperov sa aktualizujú príkazmi:

```bash
python3 scripts/import_hockey_schedule.py
python3 build.py
```

Importér používa balík `certifi` na overenie HTTPS certifikátov. Vygenerovaný
web ho nepotrebuje.

## WordPress ako redakčný systém

WordPress sa používa iba pri tvorbe obsahu. Návštevník nového webu sa naň
nepripája: publikované príspevky a ich médiá sa počas synchronizácie uložia do
Git repozitára a `build.py` z nich vytvorí statické HTML stránky.

Manuálna synchronizácia:

```bash
python3 -m pip install -r requirements.txt
WORDPRESS_URL=https://www.hkbrezno.sk python3 scripts/import_wordpress.py
python3 build.py
```

Po publikovaní článku vo WordPress administrácii sa do webu prenesú:

- názov, dátum, autor, kategórie a perex,
- celý obsah článku,
- titulný obrázok a obrázky vložené do obsahu,
- pripojené PDF a kancelárske dokumenty,
- SEO metadata, detail článku a záznam v `sitemap.xml`.

Importér zároveň číta publikované WordPress stránky so slugmi `kontakt`,
`historia` a `rozpis-ladu`. Stránka Rozpis ľadu má obsahovať vložený PDF súbor
alebo obrázok; PDF má prednosť a na novom webe sa zobrazí priamo vo vloženom
prehliadači. História, kontaktné údaje a rozpis sa ukladajú do
`content/wordpress/pages.json`, takže verejný web zostáva statický aj pri
dočasnej nedostupnosti WordPressu.

Workflow [`.github/workflows/sync-wordpress.yml`](.github/workflows/sync-wordpress.yml)
kontroluje WordPress každú hodinu. Dá sa spustiť aj ručne alebo okamžite cez
GitHub `repository_dispatch` event typu `wordpress-published`. URL redakčného
WordPressu sa nastavuje repository premennou `WORDPRESS_URL`; bez nej sa použije
aktuálny `https://www.hkbrezno.sk`.

Pred presmerovaním produkčnej domény na nový statický web treba WordPress
presunúť na samostatnú adresu, napríklad `cms.hkbrezno.sk`, a zmeniť
`WORDPRESS_URL`. Redakcia tak zostane dostupná, ale nebude súčasťou verejného
frontendu.

## Bezpečnostná konfigurácia

Súbor [`.htaccess`](.htaccess) na Apache/LiteSpeed hostingu zapína HTTPS
presmerovanie, HSTS, CSP, ochranu proti vloženiu stránky do iframe, zákaz MIME
sniffingu, obmedzenie browserových oprávnení a zákaz výpisu adresárov. Zároveň
blokuje priamy prístup k zdrojovým súborom, konfigurácii a obsahovým JSON-om.

Formulár podporuje tieto serverové premenné:

- `HK_FORM_TO` — cieľová e-mailová adresa klubu,
- `HK_FORM_FROM` — odosielateľ z domény hostingu,
- `HK_ALLOWED_HOSTS` — čiarkou oddelené domény, z ktorých sa smie formulár odoslať,
- `HK_RATE_LIMIT_SALT` — náhodný tajný reťazec na hashovanie IP v rate limite,
- `HK_TRUST_PROXY=1` — iba ak HTTPS ukončuje dôveryhodný reverzný proxy server.

Pred nasadením treba najprv aktivovať platný HTTPS certifikát. Hodnoty `.env`
sa nesmú commitovať; repozitár povoľuje iba dokumentačný `.env.example`.

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
| `onClick="{{ go.xxx }}"` | `data-go="xxx"` + obsluha v externom `site.js` |
| `{{ c.xxx }}` / `{{ u.xxx }}` | `data-nav` / `data-u` + aktívny stav z CSS |
| `{{ nav.* }}` | `data-navbar` + `.is-stuck` |
| `{{ cd.d }}` | `<span data-cd="d">` dopočítaný v JS |
| `style-hover="…"` | `data-hv="N"` + vygenerované `:hover` pravidlo |
| `<image-slot placeholder="X">` | `<div class="slot">` — miesto pre fotografiu |

## Stav a čo ďalej

Hotové:

- 9 podstránok: Domov, Novinky, Zápasy, Rozpis ľadu, Tímy, Klub,
  Pre rodičov, Partneri, Prihláška.
- Routovanie medzi podstránkami, aktívny stav v menu, prilepená navigácia po
  odscrollovaní a živý odpočet do najbližšieho zápasu.
- Kalendár 18 zápasov A tímu bez výsledkov, s logami a dátami importovanými
  z oficiálneho programu Hockey Slovakia.
- Headless WordPress integrácia: aktuálne je importovaných 18 publikovaných
  článkov, história klubu, kontakt a rozpis ľadu vrátane lokálnych kópií médií
  a dokumentov.
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
2. **8 fotomiest** (`.slot`) čaká na skutočné fotografie z klubu.
3. **Migrácia na finálnu Next.js aplikáciu** — cieľ je `output: 'export'`,
   bez API routes, middleware, ISR a bez závislosti od Vercelu.
4. **Nasadenie formulára** — pred testovaním treba na hostingu zapnúť HTTPS a
   nastaviť cieľový e-mail cez `HK_FORM_TO` alebo upraviť fallback v
   `send-form.php`.

## Poznámka k obsahu

Texty a mená mimo aktualít a stránky Klub sú **vzorové dáta** z dizajnového
návrhu. Aktuality a Klub sú importované z WordPressu; program A tímu a tímové
logá z Hockey Slovakia.
