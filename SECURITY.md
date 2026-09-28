# Bezpečnosť HK Brezno webu

## Architektúra

Verejný web je statický. WordPress sa používa iba ako oddelená redakcia a jeho
verejné REST API sa číta počas synchronizácie. Produkčný frontend nepotrebuje
prístupové údaje do WordPressu ani databázu.

Importér povoľuje iba HTTPS komunikáciu s nakonfigurovaným WordPress hostom,
kontroluje presmerovania, lokálne kopíruje médiá a HTML filtruje cez zoznam
povolených elementov a atribútov.

## Pred nasadením

1. Aktivovať platný HTTPS certifikát ešte pred nahratím `.htaccess`.
2. Nastaviť `HK_FORM_TO`, `HK_FORM_FROM`, `HK_ALLOWED_HOSTS` a náhodný
   `HK_RATE_LIMIT_SALT` mimo Git repozitára.
3. WordPress presunúť na samostatnú CMS doménu a nastaviť ju ako
   `WORDPRESS_URL` v GitHub repository variables.
4. Vo WordPresse zapnúť automatické bezpečnostné aktualizácie, 2FA pre
   administrátorov, denné zálohy a účty s najnižšími potrebnými právami.
5. Odstrániť nepoužívané WordPress pluginy a témy. XML-RPC vypnúť, ak ho
   nepoužíva žiadna integrácia.
6. Na hostingu overiť bezpečnostné hlavičky a HTTPS presmerovanie napríklad cez
   Mozilla Observatory.

## Kontroly pred vydaním

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile build.py scripts/import_wordpress.py scripts/import_hockey_schedule.py
python3 build.py
git diff --check
```

PHP formulár treba pred produkčným nasadením overiť cez `php -l send-form.php`
a skúšobným odoslaním na HTTPS hostingu. Citlivé údaje z formulára sa nesmú
zapisovať do aplikačných logov ani commitovať do Gitu.

## Hlásenie problému

Bezpečnostný problém neposielajte do verejného issue. Kontaktujte správcu klubu
na `info@hkbrezno.sk` a uveďte URL, popis dopadu a kroky na zopakovanie bez
zverejnenia osobných údajov.
