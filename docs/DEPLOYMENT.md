# Nasadenie HK Brezno webu

Tento návod zodpovedá verzii uvedenej v súbore [`../VERSION`](../VERSION).
Verejný frontend a WordPress musia používať dve rozdielne adresy.

Odporúčané rozdelenie:

```text
https://www.hkbrezno.sk       verejný statický web
https://cms.hkbrezno.sk       WordPress administrácia a REST API
```

## 1. Príprava WordPressu

1. Vytvorte subdoménu `cms.hkbrezno.sk` a aktivujte na nej HTTPS.
2. Presuňte existujúce WordPress súbory a databázu alebo zmeňte DNS tak, aby
   WordPress zostal dostupný na CMS subdoméne.
3. Vo WordPresse nastavte „WordPress Address“ aj „Site Address“ na
   `https://cms.hkbrezno.sk` a znovu uložte trvalé odkazy.
4. Overte, že bez prihlásenia fungujú tieto adresy:

```text
https://cms.hkbrezno.sk/wp-json/wp/v2/posts?status=publish&per_page=1
https://cms.hkbrezno.sk/wp-json/wp/v2/pages?slug=kontakt&status=publish
https://cms.hkbrezno.sk/wp-json/wp/v2/pages?slug=historia&status=publish
https://cms.hkbrezno.sk/wp-json/wp/v2/pages?slug=rozpis-ladu&status=publish
```

Importér nepotrebuje WordPress heslo. Číta iba verejný publikovaný obsah cez
HTTPS a odmietne inú schému, neočakávaný host alebo nebezpečné presmerovanie.

## 2. Obsah vo WordPresse

### Články

Bežný príspevok stačí zverejniť. Synchronizujú sa názov, dátum, autor,
kategórie, perex, obsah, titulný obrázok, obrázky v článku a priložené PDF či
kancelárske dokumenty. Náhľady a súkromné príspevky sa neimportujú.

### Klub

Publikované stránky musia mať slug `kontakt` a `historia`. Importér z nich
vytvorí obsah podstránky Klub. Odkazy na pôvodný WordPress sa na verejnom webe
nezobrazujú.

### Rozpis ľadu

Publikovaná stránka musí mať slug `rozpis-ladu`. Do obsahu vložte jeden aktuálny
PDF súbor alebo obrázok. Ak stránka obsahuje oboje, použije sa PDF.

Web momentálne obsahuje lokálny rozpis s hodnotou:

```text
modified = 2026-09-28T16:45:00
```

WordPress rozpis ho automaticky nahradí iba vtedy, keď má stránka
`rozpis-ladu` novší dátum `modified`. Pri výmene rozpisu preto aktualizujte a
uložte stránku, nestačí v knižnici médií prepísať súbor pod rovnakým názvom.

## 3. Nastavenie GitHubu

V `Settings -> Secrets and variables -> Actions -> Variables` vytvorte:

```text
WORDPRESS_URL=https://cms.hkbrezno.sk
```

V `Settings -> Actions -> General -> Workflow permissions` povoľte
`Read and write permissions`, pretože sync workflow vytvára commit.
Bez platnej HTTPS hodnoty `WORDPRESS_URL` workflow skončí chybou ešte pred
importom; zámerne nepoužíva náhradnú produkčnú adresu.

Workflow `Sync WordPress content`:

- beží každú hodinu o 17. minúte;
- dá sa spustiť tlačidlom `Run workflow`;
- podporuje `repository_dispatch` event `wordpress-published`;
- spustí testy, import a build;
- commitne iba zmenené CMS dáta a vygenerovaný web.

GitHub plánované workflow používa predvolenú vetvu. Pred zapnutím automatickej
synchronizácie preto zlúčte vydanú verziu do predvolenej produkčnej vetvy.

## 4. Manuálna synchronizácia a build

```bash
git pull
python3 -m pip install -r requirements.txt
WORDPRESS_URL=https://cms.hkbrezno.sk python3 scripts/import_wordpress.py
python3 -m unittest discover -s tests -v
python3 build.py
```

Po úspešnom builde commitnite všetky zmenené CMS snapshoty, médiá a generované
súbory. Produkcia sa nesmie buildovať priamo z necommitovaných lokálnych dát.

## 5. Súbory pre webhosting

Do document rootu verejnej domény nahrajte iba:

```text
.htaccess
index.html
site.js
send-form.php
robots.txt
sitemap.xml
assets/
images/
documents/
aktuality/
```

Priečinky `scripts`, `tests`, `content`, `.git` a zdrojové dokumenty na hosting
nepatria. Ak hosting nasadzuje celý Git repozitár, `.htaccess` blokuje priamy
webový prístup k citlivým zdrojovým typom, ale samostatný deploy adresár je
čistejšie riešenie.

Po nahratí nastavte vlastníka súborov podľa hostingu. Bežné oprávnenia sú 755
pre priečinky a 644 pre súbory. `send-form.php` nepotrebuje zapisovať do
webového adresára; rate limit používa systémový dočasný adresár PHP.

## 6. Konfigurácia formulára

Na hostingu nastavte serverové environment premenné:

```text
HK_FORM_TO=info@hkbrezno.sk
HK_FORM_FROM=no-reply@hkbrezno.sk
HK_ALLOWED_HOSTS=hkbrezno.sk,www.hkbrezno.sk
HK_RATE_LIMIT_SALT=<dlhy-nahodny-retazec>
```

`HK_TRUST_PROXY=1` nastavte iba vtedy, keď HTTPS ukončuje dôveryhodný reverzný
proxy server a hosting správne nastavuje `X-Forwarded-Proto`.

Adresa `HK_FORM_FROM` musí existovať na doméne hostingu a musí mať správne SPF,
DKIM a DMARC. Server musí podporovať PHP `mail()`. Ak hosting `mail()` blokuje,
formulár treba pred produkciou prepojiť na SMTP alebo transakčné e-mailové API.

## 7. DNS a HTTPS

1. Nasmerujte `cms.hkbrezno.sk` na WordPress hosting.
2. Nasmerujte `www.hkbrezno.sk` a koreňovú doménu na statický/PHP hosting.
3. Aktivujte certifikát pre všetky používané hosty.
4. Až potom nahrajte produkčný `.htaccess`, ktorý vynucuje HTTPS a HSTS.

WordPress CMS nesmie byť vložený v iframe verejnej stránky. Verejný web používa
iba jeho REST API počas synchronizácie.

## 8. Produkčná kontrola

Po nasadení overte:

```text
https://www.hkbrezno.sk/
https://www.hkbrezno.sk/?page=novinky
https://www.hkbrezno.sk/?page=zapasy
https://www.hkbrezno.sk/?page=rozpisladu
https://www.hkbrezno.sk/?page=klub
https://www.hkbrezno.sk/sitemap.xml
https://www.hkbrezno.sk/robots.txt
```

Následne:

1. otvorte web na mobile aj desktope;
2. otvorte aspoň jeden detail článku a jeho obrázky;
3. overte PDF alebo obrázok rozpisu;
4. odošlite testovaciu prihlášku a skontrolujte e-mail klubu aj potvrdenie;
5. overte HTTPS presmerovanie a bezpečnostné hlavičky;
6. zverejnite testovací WordPress článok, spustite workflow a overte, že po
   deployi pribudol na verejnom webe.

## 9. Čo automatizácia zatiaľ nerobí

Repozitár momentálne neobsahuje workflow pre upload na konkrétny hosting.
WordPress sync vytvorí a pushne commit, ale produkcia sa aktualizuje až po
nasadení tohto commitu. Podľa hostingu treba doplniť jednu z možností:

- Git deployment/pull z produkčnej vetvy;
- SFTP/rsync workflow s hostingovými secrets;
- hostingový deploy hook spustený po úspešnom sync workflow.

Konkrétny deploy workflow sa má pridať až po výbere hostingu a bezpečnom
uložení prístupových údajov v GitHub Actions secrets.
