# HK Brezno — návrh novej webovej stránky

Návrh štruktúry, obsahových modelov, technológie a dizajn systému pre redesign
`hkbrezno.sk`.

---

## 1. Audit súčasného stavu

Súčasný web je WordPress (dodávateľ Naštartovač) s touto navigáciou:

`Domov · O klube (Kontakt, Tréneri, Vedenie, Historia, Kódexy) · Nábor nových
rytierov · Mládež · Rozpis ľadu · Aktuality · Na stiahnutie`

### Čo funguje

- Aktuality sa reálne píšu a sú aktuálne — klub obsah tvorí, to je najdôležitejšie.
- Partneri/sponzori a sociálne siete sú viditeľné.
- Základná štruktúra „O klube" je logická.

### Kľúčové problémy

| # | Problém | Dopad |
|---|---------|-------|
| 1 | **Rozpis ľadu je PNG obrázok** (`ROZPIS-LADU-23.3.-29.3.png`) | Nečitateľné na mobile, nedá sa hľadať, nedá sa pridať do kalendára, nedá sa filtrovať podľa kategórie. Rodič musí zoomovať. Zároveň je zjavne neaktuálny (marec). |
| 2 | **Stránka „Mládež" je len fotogaléria** | Neexistujú stránky jednotlivých kategórií — žiadne súpisky, tréneri kategórie, rozpis ani výsledky. Najžiadanejší obsah pre rodiča na webe nie je. |
| 3 | **Chýbajú zápasy, výsledky a tabuľky** | Web nedokáže odpovedať na „kedy a s kým hráme". |
| 4 | **Minirytiersky turnaj nemá miesto na webe** | Vlajkový event klubu (3. ročník, 30. 8. 2026) žije len na plagáte a Facebooku. |
| 5 | **„Rodičia v obraze" newsletter nemá archív** | Informácie zaniknú v e-mailoch, noví rodičia sa k nim nedostanú. |
| 6 | **Grafika webu nezodpovedá vizuálnej identite klubu** | Identita z plagátov (rytier, tmavomodrá + červená, condensed typografia) je silná a konzistentná — web ju nevyužíva. |
| 7 | **Obsah je v obrázkoch namiesto dát** | Rozpis, princípy TJ, turnaj — všetko ako grafika. Nulové SEO, nulová dostupnosť, každá zmena = práca v grafickom editore. |
| 8 | **WordPress = priebežná údržba** | Aktualizácie jadra a pluginov, bezpečnostné riziko, spomalenie. |

### Hlavný záver

Web dnes funguje ako **vývesná tabuľa**. Má fungovať ako **prevádzkový nástroj
klubu** — miesto, kde rodič za 10 sekúnd na mobile zistí, kedy má dieťa tréning,
a kde tréner za 2 minúty zverejní rozpis.

---

## 2. Cieľ a princípy návrhu

1. **Mobile-first.** Rodič otvára web na telefóne v aute pred zimákom. Všetko
   dôležité má byť viditeľné bez zoomovania a scrollovania.
2. **Obsah ako dáta, nie ako obrázok.** Rozpis, zápasy a súpisky sú štruktúrované
   záznamy v CMS. Z tých istých dát potom vzniká web, kalendár (.ics) aj export.
3. **Jeden zdroj pravdy.** Tréner zadá tréning raz → zobrazí sa v rozpise ľadu, na
   stránke kategórie, v kalendári rodiča aj v „dnes na ľade" na homepage.
4. **Správa bez technika.** Kto vie použiť Facebook, zvládne CMS. Slovenské
   rozhranie, predpripravené šablóny, žiadny HTML ani grafika.
5. **Bez údržby a v podstate bez nákladov na hosting.** Statický web = nič sa
   nehackne, nič netreba aktualizovať, načíta sa okamžite.
6. **Identita klubu na prvom mieste.** Vizuál z plagátov (rytier, štít, chevrony,
   ľadová textúra) prenesený do dizajn systému webu.

---

## 3. Nová informačná architektúra

### Hlavná navigácia (5 položiek — nie 7)

```
KLUB        TÍMY        ROZPIS A ZÁPASY        NÁBOR        AKTUALITY
                                                    [ Podpor nás ]  ← CTA button
```

Sekundárna navigácia (v hlavičke vpravo / v pätičke): `Rodičia · Turnaj ·
Galéria · Partneri · Kontakt`

### Kompletná mapa stránok

```
/                                Domov
│
├── /klub
│   ├── /klub/o-nas              O klube — vízia, filozofia, misia
│   ├── /klub/vedenie            Vedenie klubu (karty s fotkou a kontaktom)
│   ├── /klub/treneri            Trénerský tím (licencie, kategórie)
│   ├── /klub/historia           História klubu (timeline)
│   ├── /klub/filozofia          Princípy a kódexy
│   │                            ├─ Princípy tvorby TJ  ← obsah z prílohy, ako web
│   │                            ├─ Etický kódex hráča
│   │                            ├─ Kódex rodiča
│   │                            └─ Kódex trénera
│   └── /klub/kontakt            Kontakt + mapa zimného štadióna
│
├── /timy                        Prehľad kategórií (mriežka kariet)
│   ├── /timy/prípravka
│   ├── /timy/1-stupen           (šablóna je pre všetky rovnaká:)
│   ├── /timy/mladsi-ziaci        • hlavička s kategóriou a ročníkmi
│   ├── /timy/starsi-ziaci        • tréneri kategórie + kontakt
│   ├── /timy/kadeti              • najbližšie tréningy (auto z rozpisu)
│   ├── /timy/dorast              • najbližšie zápasy + posledné výsledky
│   ├── /timy/juniori             • súpiska (číslo, meno, pozícia, ročník)
│   └── /timy/seniori             • tabuľka súťaže
│                                 • galéria a aktuality kategórie
│                                 • tlačidlo „Pridať do kalendára" (.ics)
│
├── /rozpis                      Rozpis ľadu — týždenná mriežka
│   │                            filtre: kategória · typ (ľad/suchá/zápas)
│   │                            prepínač týždňov, „dnes" zvýraznené
│   │                            export .ics pre celý klub aj pre kategóriu
│   ├── /zapasy                  Zápasy — najbližšie + odohrané
│   ├── /zapasy/<id>             Detail zápasu (zostava, priebeh, report, foto)
│   └── /tabulky                 Tabuľky súťaží podľa kategórie
│
├── /nabor                       Nábor nových rytierov
│   ├── kto sa môže prihlásiť, čo treba, koľko to stojí
│   ├── prvé tri tréningy zdarma / výstroj na zapožičanie
│   ├── FAQ pre rodičov (rozklikávacie)
│   └── ONLINE PRIHLÁŠKA         ← formulár, nie PDF na stiahnutie
│
├── /aktuality                   Výpis článkov + filter podľa kategórie/tímu
│   └── /aktuality/<slug>        Detail článku
│
├── /rodicia                     Rodičia v obraze — informačný rozcestník
│   ├── /rodicia/newsletter      Archív newslettera „Rodičia v obraze"
│   ├── /rodicia/platby          Členské, klubové príspevky, splatnosti
│   ├── /rodicia/vystroj         Aká výstroj, kde kúpiť, veľkosti
│   ├── /rodicia/ako-to-funguje  Prvý mesiac v klube, prax pred tréningom
│   └── /rodicia/dokumenty       Na stiahnutie (nahrádza pôvodné /na-stiahnutie)
│
├── /turnaj                      Minirytiersky turnaj — vlastný „mini-web"
│   ├── /turnaj/2026             3. ročník: 30. 8. 2026
│   │                            program, zúčastnené tímy, harmonogram,
│   │                            Putovný rytiersky štít, partneri, prihláška tímu
│   ├── /turnaj/2025             archív ročníka (výsledky, galéria, víťaz)
│   └── /turnaj/2024             archív ročníka
│
├── /galeria                     Fotogaléria a videá (albumy podľa tímu/eventu)
│
├── /partneri                    Partneri a podpora
│   ├── logá partnerov po úrovniach (hlavný / partner / podporovateľ)
│   ├── 2 % z dane — vysvetlenie + predplnené tlačivá
│   └── „Chcem podporiť klub" — sponzorské balíčky + kontakt
│
└── /hladame-dobrovolnikov       (voliteľné) rozhodcovia, dobrovoľníci na turnaj
```

### Homepage — poradie sekcií

Poradie je zámerne podľa toho, čo návštevník naozaj potrebuje, nie podľa
dôležitosti pre klub.

1. **Hero** — klubový crest, motto „Trénujme s účelom. Hrajme s odvahou.",
   diagonálny červený rez, ľadová textúra na pozadí. Dve CTA: *Nábor* / *Rozpis ľadu*.
2. **Dnes / tento týždeň na ľade** — kompaktný pás najbližších tréningov a zápasov
   (auto-generované z rozpisu). Toto je najžiadanejšia informácia na webe.
3. **Najbližší zápas + posledné výsledky** — karty so skóre.
4. **Aktuality** — 3 najnovšie články.
5. **Nábor — banner** — „Každý veľký hokejista bol raz malým rytierom." + tlačidlo.
6. **Minirytiersky turnaj** — banner s dátumom a odpočtom (v sezóne turnaja).
7. **Naše kategórie** — mriežka kariet tímov.
8. **Hodnoty klubu** — ikonový riadok: čestnosť · rešpekt · srdce · odvaha ·
   tímovosť · radosť z hry · fair play (presne ako na plagáte turnaja).
9. **Partneri** — pás log.
10. **Pätička** — kontakt, sociálne siete, dokumenty, 2 % z dane, GDPR.

---

## 4. Obsahové modely v CMS

Toto je jadro návrhu — z týchto typov záznamov sa generuje celý web.

| Typ záznamu | Polia | Kto spravuje |
|---|---|---|
| **Aktualita** | titulok, perex, hlavná foto, text, kategória, súvisiaci tím, autor, dátum, „pripnuté" | marketing |
| **Kategória / tím** | názov, ročníky, súťaž, tréneri (odkaz), popis, hlavná foto, poradie | admin |
| **Hráč** | meno, číslo, pozícia, ročník, foto, tím (odkaz), *(voliteľne skryť pre GDPR)* | tréner |
| **Tréner / člen vedenia** | meno, rola, licencia, foto, e-mail, telefón, kategórie | admin |
| **Tréningový slot** | dátum, od–do, tím(y), typ (ľad / suchá / regenerácia / zápas), plocha, tréner, poznámka | tréner |
| **Zápas** | dátum a čas, súťaž, domáci / hostia, miesto, tím, skóre, stav (plánovaný / odohraný), strelci, report (odkaz na aktualitu), galéria | tréner / admin |
| **Tabuľka súťaže** | súťaž, sezóna, riadky (tím, Z, V, R, P, skóre, body) *alebo* odkaz na externú tabuľku | admin |
| **Turnaj** | ročník, dátum, miesto, tímy, harmonogram, partneri, výsledky, galéria, plagát | admin |
| **Dokument** | názov, súbor, kategória, pre koho (rodič / hráč / verejnosť) | admin |
| **Partner** | názov, logo, web, úroveň, poradie | admin |
| **Newsletter** | číslo, dátum, obsah *alebo* PDF, sezóna | marketing |
| **Album galérie** | názov, dátum, fotky, tím, event | marketing |
| **Stránka** | titulok, slug, sekcie (stavebnica blokov), SEO | admin |

### Čo z toho vzniká automaticky

- **Rozpis ľadu** = zobrazenie tréningových slotov → už žiadny PNG obrázok.
- **`.ics` kalendár** pre klub a pre každú kategóriu → rodič si raz pridá odkaz do
  Google/Apple kalendára a rozpis mu tam padá sám. **Toto samo o sebe rieši
  najväčšiu bolesť súčasného webu.**
- **„Tento týždeň na ľade"** na homepage.
- **Najbližšie tréningy a zápasy** na stránke každej kategórie.
- **Súpiska** kategórie.
- **RSS** pre aktuality.

### Roly a oprávnenia

| Rola | Môže |
|---|---|
| **Administrátor** (webmaster) | všetko |
| **Editor** (marketing) | aktuality, galéria, newsletter, stránky |
| **Tréner** | tréningové sloty, zápasy a súpiska **len svojej kategórie** |
| **Prezerajúci** | náhľad pred zverejnením |

Kľúčové: tréner nemá prístup do zvyšku webu a nemôže nič pokaziť. To je podmienka,
aby rozpis reálne udržiavali tréneri a nie jeden preťažený človek.

---

## 5. Technológia a hosting

### Odporúčaná varianta: Astro + Sanity + Cloudflare Pages

| Vrstva | Riešenie | Cena |
|---|---|---|
| Web (frontend) | **Astro 5** — statické generovanie, automatická optimalizácia obrázkov, takmer nulový JavaScript | — |
| CMS | **Sanity** — hostované, slovenské rozhranie, roly, náhľad, mobilná editácia | 0 € (free tier) |
| Hosting | **Cloudflare Pages** — CDN, HTTPS, neobmedzený prenos | 0 € |
| Formuláre | **Cloudflare Worker** alebo Web3Forms → e-mail | 0 € |
| Vyhľadávanie | **Pagefind** — statické, bez servera | 0 € |
| Newsletter | MailerLite / Buttondown + archív na webe | 0 € do ~500 kontaktov |
| Domény | existujúca `hkbrezno.sk` | súčasná cena |

**Ako to funguje v praxi:** tréner v CMS pridá tréning a klikne „Publikovať" →
webhook spustí prebuild → web je aktualizovaný do ~30 sekúnd. Rodič vidí novú
verziu, ale server v skutočnosti servíruje len hotové HTML.

**Prečo toto:**

- **Nič netreba udržiavať.** Žiadne aktualizácie pluginov, žiadne bezpečnostné
  záplaty, web sa nedá hacknúť cez prihlasovací formulár, pretože žiadny na
  hostingu nie je.
- **Rýchlosť.** Lighthouse 95+ a načítanie pod 1 s aj na mobilnom dáta na
  zimáku — reálny scenár použitia.
- **Cena.** Prakticky 0 € ročne za hosting namiesto platby za shared hosting.
- **Grafická voľnosť.** Vizuál z plagátov sa dá presne prepísať do kódu bez
  obchádzania obmedzení WordPress témy.

**Riziko, ktoré treba pomenovať:** klub nemá „klikací" editor stránok ako v
WordPress. Riešenie: stránky sa skladajú z pripravených blokov v CMS
(hero, text, mriežka kariet, galéria, tabuľka, CTA banner, pás partnerov), takže
editor skladá stránku z komponentov — nie píše HTML, ale ani nemá voľnú ruku
pokaziť dizajn. To je pre klub s dobrovoľníkmi výhoda, nie strata.

### Alternatíva, ak klub trvá na WordPress

WordPress s **vlastnou block témou** (nie kúpená šablóna) + ACF pre obsahové
modely + WP Cron pre rozpis, na slovenskom hostingu (Websupport, ~40 €/rok).

- **Pre:** klub pozná rozhranie, ktokoľvek na Slovensku to vie potom prevziať.
- **Proti:** priebežná údržba a bezpečnosť, výrazne pomalší web, `.ics` export a
  rozpis treba doprogramovať v PHP, dizajnová voľnosť menšia.

**Odporúčanie:** varianta Astro + Sanity. WordPress voľte len vtedy, ak je
podmienkou, aby web mohol prevziať bežný lokálny WP dodávateľ.

### Tretia možnosť pre nulové priebežné náklady

Astro + **Decap CMS** (obsah priamo v Git repozitári, prihlásenie cez GitHub) —
absolútne 0 € navždy, ale rozhranie je oproti Sanity spartánske a nemá poriadne
roly. Vhodné, ak by budúci rozpočet klubu nemal priestor ani na free-tier riziko.

---

## 6. Dizajn systém (odvodený z priložených grafík)

Vizuálna identita na plagátoch je konzistentná a silná. Prenášam ju 1:1 do webu.

### Farby

| Rola | Hodnota | Použitie |
|---|---|---|
| Navy (základ) | `#0B1526` | pozadie hero, hlavička, pätička |
| Navy 800 | `#132340` | karty na tmavom pozadí |
| Klubová červená | `#C8102E` | akcent, čísla, CTA, diagonálne pásy |
| Ocelová šedá | `#8A94A6` | helma rytiera, sekundárny text, ikony |
| Ľadová biela | `#F5F7FA` | pozadie obsahových sekcií |
| Zlatá (turnaj) | `#C9A227` | výhradne turnaj, štít, ocenenia |

### Typografia

- **Nadpisy:** kondenzovaný ťažký sans-serif (Barlow Condensed 800 / Oswald),
  VEĽKÝMI, tesný riadkový preklad — presne ako „PRINCÍPY TVORBY TJ".
- **Text:** Barlow alebo Inter, 17–18 px, dobrá čitateľnosť pre rodičov.
- **Motto a slogany:** kurzívny brush/script rez — „*Trénujme s účelom. Hrajme s
  odvahou.*", „*Na ľade bojuj ako rytier. Mimo ľadu buď priateľ.*"
- Všetky rezy musia mať plnú slovenskú diakritiku (ľ, ť, ď, ĺ, ŕ, ô, ä).

### Vizuálne motívy z plagátov

- **Diagonálne rezy a chevrony** — červeno/šedé šikmé pásy ako oddeľovače sekcií.
- **Ľadová/grain textúra** — jemná na tmavých pozadiach.
- **Silueta štadióna a reflektory** — hero pozadie s tmavým prekrytím.
- **Tvar štítu** — karty tímov a hodnôt, medaily, turnajové ocenenia.
- **Kresba klziska a X/O taktické značky** — ikonografia trénerských sekcií.
- **Číslované bloky s červenou linkou** — presne layout z plagátu „Princípy tvorby
  TJ": veľké červené číslo, kondenzovaný nadpis, odrážky, ikona vľavo,
  fotografia vpravo. Toto je hotový komponent pre celú sekciu `/klub/filozofia`.

### Komponentová knižnica

`Hero s crestom` · `Karta tímu (štít)` · `Karta zápasu so skóre` · `Týždenná mriežka
rozpisu` · `Číslovaný princíp` · `Riadok hodnôt s ikonami` · `Citátový banner
(script font)` · `Pás partnerov` · `Karta trénera` · `Riadok súpisky` · `Tabuľka
súťaže` · `Odpočet do turnaja` · `FAQ akordeón` · `Formulár prihlášky` ·
`Mriežka galérie` · `Karta dokumentu na stiahnutie`

### Nefunkčné požiadavky

- Lighthouse ≥ 95 vo všetkých štyroch kategóriách.
- WCAG 2.1 AA — kontrast, klávesová navigácia, alt texty.
- Otvorené grafy pre Facebook (klub tam publikuje najviac) — automatické OG
  obrázky s crestom a titulkom článku.
- Štruktúrované dáta `SportsTeam` a `SportsEvent` → zápasy a turnaj sa môžu
  zobraziť priamo v Google výsledkoch.

---

## 7. Migrácia a spustenie

1. **Export obsahu** zo súčasného WordPress cez REST API (`/wp-json/wp/v2/posts`,
   `pages`, `media`) → skript naimportuje aktuality, stránky a médiá do nového CMS.
2. **Mapa presmerovaní 301** zo starých URL na nové, aby sa nestratilo SEO ani
   odkazy zdieľané na Facebooku. Osobitne `/mladez/` → `/timy`, `/rozpis-ladu/` →
   `/rozpis`, `/na-stiahnutie/` → `/rodicia/dokumenty`.
3. **Prepis obsahu z obrázkov na text** — princípy TJ, rozpis, turnajové plagáty.
   Toto je manuálna práca, ale robí sa raz a je to najväčší jednotlivý prínos pre
   SEO aj dostupnosť.
4. **Zaškolenie** — 90 minút s trénermi (rozpis a súpiska) a 60 minút s marketingom
   (aktuality a galéria) + krátke video návody uložené v CMS.

### Fázy

| Fáza | Obsah | Odhad |
|---|---|---|
| 0 | Obsahová inventúra, súpisky kategórií, zber podkladov od trénerov | 1 týždeň |
| 1 | Dizajn systém + návrh homepage, tímu a rozpisu | 2 týždne |
| 2 | Astro projekt, CMS schémy, roly, komponenty | 2 týždne |
| 3 | Migrácia obsahu + prepis grafík na text | 1–2 týždne |
| 4 | Rozpis, zápasy, `.ics`, formuláre, vyhľadávanie | 1 týždeň |
| 5 | QA, SEO, presmerovania, zaškolenie, spustenie | 1 týždeň |

Celkovo ~7–9 týždňov. Fáza 0 je na strane klubu a je najčastejšou príčinou
zdržania — súpisky a rozpis treba dodať v použiteľnej podobe.

---

## 8. Zhrnutie prínosu

| Dnes | Po redesigne |
|---|---|
| Rozpis ako PNG, neaktuálny | Rozpis ako dáta + `.ics` do kalendára rodiča |
| „Mládež" = fotogaléria | 8 stránok kategórií so súpiskou, rozpisom a výsledkami |
| Žiadne zápasy ani výsledky | Zápasy, výsledky, tabuľky |
| Turnaj len na Facebooku | Vlastná sekcia `/turnaj` s archívom ročníkov |
| Newsletter zaniká v e-mailoch | Verejný archív `Rodičia v obraze` |
| Prihláška ako PDF | Online prihláška do nábor |
| Grafika mimo identity klubu | Dizajn systém odvodený z plagátov |
| WordPress + údržba + hosting | Statický web, 0 € hosting, bez údržby |
| Obsah spravuje jeden človek | Tréneri spravujú svoju kategóriu sami |

---

## 9. Čo treba rozhodnúť pred štartom

1. **Technológia** — Astro + Sanity (odporúčané) vs. WordPress s vlastnou témou.
2. **GDPR pri súpiskách** — zverejňovať mená a fotky detí? Odporúčam: meno,
   číslo a ročník pri žiakoch a starších, u prípravky bez mien; fotky len so
   súhlasom rodiča.
3. **Zoznam kategórií a súťaží** pre sezónu 2026/2027 — pre presnú štruktúru `/timy`.
4. **Kto bude tréning zadávať** — jeden správca rozpisu, alebo každý tréner
   svoju kategóriu? (Návrh predpokladá druhé.)
5. **Zdroj tabuliek** — ručne, alebo prevzaté z `hockeyslovakia.sk`?
