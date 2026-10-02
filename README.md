# HK Brezno web

Nový responzívny web HK Brezno s oddeleným WordPressom používaným ako headless
CMS. Verejný web je statický a vzniká generovaním HTML súborov v Gite.

## Aktuálna verzia

**`0.6.0-beta.4` (2. 10. 2026)**

Verzia je uložená aj v súbore [`VERSION`](VERSION). Zmeny jednotlivých verzií
sú v [`CHANGELOG.md`](CHANGELOG.md). Táto verzia je pripravená na testovacie
nasadenie; pred ostrou prevádzkou treba dokončiť kroky označené v sekcii
„Pred produkciou“.

Aktuálne funguje:

- 9 obrazoviek: Domov, Novinky, Zápasy A-tímu, Rozpis ľadu, Tímy, Klub,
  Pre rodičov, Partneri a Prihláška;
- responzívna navigácia a rozhranie pre mobil aj desktop;
- kalendár A-tímu bez výsledkov, s logami súperov z Hockey Slovakia;
- články, história, kontakt a rozpis ľadu synchronizované z WordPressu;
- lokálne uložené médiá a dokumenty, takže návštevník nie je závislý od
  dostupnosti WordPressu;
- bezpečnostné hlavičky pre Apache/LiteSpeed a zabezpečený PHP formulár;
- hodinová kontrola nového WordPress obsahu cez GitHub Actions.
- priamy odkaz z hlavnej navigácie na externý klubový E-shop.

Stránka Pre rodičov je zámerne bez obsahu. Partneri zatiaľ používajú zástupné
logá. Hero fotografie a ďalšie vizuály označené ako fotomiesta ešte čakajú na
finálne klubové podklady.

## Architektúra

```text
WordPress CMS (samostatná HTTPS doména)
        |
        | verejné WordPress REST API
        v
scripts/import_wordpress.py
        |
        v
content/wordpress + lokálne médiá
        |
        v
build.py -> index.html + aktuality/* + sitemap.xml + site.js
        |
        v
Apache/LiteSpeed hosting + send-form.php
```

WordPress sa nepoužíva pri načítaní verejnej stránky. Je iba zdrojom obsahu.
Po publikovaní sa obsah importuje, sanitizuje, uloží do Gitu a následne sa
vygeneruje nový statický web.

## Dôležité súbory

| Cesta | Účel |
|---|---|
| [`design-canvas.dc.html`](design-canvas.dc.html) | Zdrojová HTML šablóna vzhľadu a statických sekcií. |
| [`build.py`](build.py) | Validuje dáta a generuje produkčný web. |
| [`index.html`](index.html) | Vygenerovaná hlavná stránka; neupravovať ručne. |
| [`site.js`](site.js) | Vygenerované routovanie, mobilné menu a odpočet. |
| [`content/wordpress/`](content/wordpress) | Git snapshot článkov a CMS stránok. |
| [`content/matches/matches.json`](content/matches/matches.json) | Program A-tímu. |
| [`content/ice-schedule.json`](content/ice-schedule.json) | Dočasný lokálny rozpis ľadu a jeho verzia. |
| [`scripts/import_wordpress.py`](scripts/import_wordpress.py) | Import WordPress článkov, stránok a médií. |
| [`scripts/import_hockey_schedule.py`](scripts/import_hockey_schedule.py) | Import zápasov a tímových log. |
| [`scripts/render_ice_schedule.py`](scripts/render_ice_schedule.py) | Generátor aktuálneho klubového SVG rozpisu. |
| [`send-form.php`](send-form.php) | Serverové spracovanie prihlášky. |
| [`.htaccess`](.htaccess) | HTTPS, bezpečnostné hlavičky a blokovanie zdrojových dát. |
| [`.github/workflows/sync-wordpress.yml`](.github/workflows/sync-wordpress.yml) | Hodinová a manuálna synchronizácia CMS. |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | Kompletný návod na WordPress a produkčné nasadenie. |

## Lokálne spustenie

Požiadavky: Python 3.11 alebo novší. PHP je potrebné iba na lokálny test
odoslania formulára.

```bash
python3 -m pip install -r requirements.txt
python3 build.py
python3 -m http.server 8000
```

Web bude dostupný na `http://localhost:8000`. Jednoduchý Python server
nespracuje `send-form.php`; všetky ostatné časti webu fungujú.

Kontroly pred commitom alebo vydaním:

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile build.py scripts/import_wordpress.py scripts/import_hockey_schedule.py scripts/render_ice_schedule.py
python3 build.py
git diff --check
```

## Aktualizácia obsahu

### WordPress

```bash
WORDPRESS_URL=https://cms.hkbrezno.sk python3 scripts/import_wordpress.py
python3 build.py
```

Importujú sa všetky publikované príspevky dostupné cez REST API. Importér ich
načítava po stránkach po 100 záznamoch. Zároveň načíta publikované stránky so
slugmi:

- `kontakt` - kontaktné a identifikačné údaje klubu;
- `historia` - text histórie klubu;
- `rozpis-ladu` - PDF alebo obrázok aktuálneho rozpisu.

Pri rozpise má PDF prednosť pred obrázkom. Lokálny rozpis v
`content/ice-schedule.json` sa zobrazí dovtedy, kým WordPress neobsahuje novšiu
verziu podľa dátumu `modified`.

### Zápasy A-tímu

```bash
python3 scripts/import_hockey_schedule.py
python3 build.py
```

### Lokálny rozpis ľadu

```bash
python3 scripts/render_ice_schedule.py
python3 build.py
```

## Automatická WordPress synchronizácia

GitHub workflow beží každú hodinu o 17. minúte, manuálne cez
`workflow_dispatch` alebo cez `repository_dispatch` s typom
`wordpress-published`. V GitHub repozitári treba vytvoriť repository variable:

```text
WORDPRESS_URL=https://cms.hkbrezno.sk
```

Naplánované workflow beží iba z predvolenej vetvy repozitára. Vetva preto musí
obsahovať aktuálny workflow a GitHub Actions musí mať právo zapisovať obsah.
Workflow importuje obsah, spustí testy a build a pri zmene vytvorí commit.
Ak premenná `WORDPRESS_URL` chýba alebo nepoužíva HTTPS, workflow zámerne
zlyhá a nevykoná import z náhradnej adresy.
**Workflow sám neposiela súbory na webhosting.** Hosting musí po novom commite
spraviť Git pull/deploy alebo sa musí nahrať nový produkčný balík.

## Nasadenie

Presný postup vrátane oddelenia CMS domény, kontroly REST API, zoznamu súborov
na upload, PHP premenných, SSL a overenia produkcie je v
[`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

Produkčný web potrebuje hosting s:

- Apache alebo LiteSpeed a podporou `.htaccess`;
- PHP 8.1 alebo novším pre `send-form.php`;
- funkčnou funkciou `mail()` alebo správne nastaveným lokálnym mail serverom;
- platným HTTPS certifikátom.

## Pred produkciou

1. Presunúť WordPress z verejnej domény na `cms.hkbrezno.sk` alebo inú
   samostatnú HTTPS adresu.
2. Nastaviť GitHub premennú `WORDPRESS_URL` a otestovať manuálny sync.
3. Nastaviť na hostingu `HK_FORM_TO`, `HK_FORM_FROM`, `HK_ALLOWED_HOSTS` a
   náhodný `HK_RATE_LIMIT_SALT`.
4. Overiť `php -l send-form.php` a skúšobné doručenie oboch e-mailov.
5. Naplniť partnerov, fotomiesta a budúci obsah stránky Pre rodičov.
6. Rozhodnúť, ako sa commity z predvolenej vetvy automaticky nasadia na
   hosting; táto automatizácia zatiaľ nie je súčasťou repozitára.

Bezpečnostné detaily a checklist sú v [`SECURITY.md`](SECURITY.md).
