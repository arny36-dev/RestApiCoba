# API Dokumentácia — RestApiCoba (Zamestnanci)

Návod, ako používať toto API. Každý endpoint je popísaný: **čo robí, čo mu treba
poslať, čo vráti a čo môže pokaziť.** Na konci sú hotové príklady použitia
("recepty") pre bežné situácie.

---

## Obsah

1. [Základné informácie](#1-základné-informácie)
2. [Autentifikácia (API kľúč)](#2-autentifikácia-api-kľúč)
3. [Stavové kódy](#3-stavové-kódy)
4. [Prehľad endpointov](#4-prehľad-endpointov)
5. [Polia zamestnanca — kompletná referencia](#5-polia-zamestnanca--kompletná-referencia)
6. [Typy zamestnancov](#6-typy-zamestnancov)
7. [Endpointy detailne](#7-endpointy-detailne)
8. [Príklady použitia (recepty)](#8-príklady-použitia-recepty)
9. [Časté chyby](#9-časté-chyby)

---

## 1. Základné informácie

- **Základná adresa:** `http://127.0.0.1:8000`
- **Prefix API:** `/api/v1`
- Všetky dáta sa posielajú aj vracajú vo formáte **JSON**.
- Pri posielaní tela (POST, PUT, PATCH) treba hlavičku `Content-Type: application/json`.
- Ku každej požiadavke na zamestnancov treba **API kľúč** (viď kapitola 2).
- API pracuje so zamestnancami: vie ich **vypísať, zobraziť, pridať, upraviť
  a deaktivovať**. **Nič sa nikdy fyzicky nezmaže** (mazanie = deaktivácia).
- Všetky záznamy patria pod **objekt 127** — nastavuje sa automaticky, nedá sa zmeniť.
- Interaktívne rozhranie na skúšanie v prehliadači: **http://127.0.0.1:8000/docs**
  (vpravo hore tlačidlo **Authorize** → zadaj API kľúč).

---

## 2. Autentifikácia (API kľúč)

Každá požiadavka na `/api/v1/employees` a `/api/v1/employee-types` musí obsahovať
hlavičku:

```
X-API-Key: <tvoj-api-kľúč>
```

- Kľúč je uložený v súbore `.env` v premennej `API_KEY`.
- Bez kľúča alebo so zlým kľúčom API vráti **401** a nič nevykoná.
- Endpointy `GET /health` a `GET /api/v1/db/health` kľúč **nevyžadujú**.

**Príklad — bez kľúča (odmietnuté):**
```bash
curl http://127.0.0.1:8000/api/v1/employees
# 401  {"detail":"Chýbajúci alebo neplatný API kľúč"}
```

**Príklad — s kľúčom (funguje):**
```bash
curl -H "X-API-Key: <tvoj-api-kľúč>" http://127.0.0.1:8000/api/v1/employees
```

> V ďalších príkladoch používame skratku `KEY="<tvoj-api-kľúč>"` a potom
> `-H "X-API-Key: $KEY"`.

---

## 3. Stavové kódy

| Kód | Význam | Kedy nastane |
| --- | --- | --- |
| `200` | OK | Požiadavka prebehla úspešne |
| `201` | Vytvorené | Nový zamestnanec bol pridaný (POST) |
| `401` | Neautorizované | Chýbajúci alebo nesprávny API kľúč |
| `404` | Nenájdené | Zamestnanec s daným `id` neexistuje alebo je neaktívny |
| `409` | Konflikt | Databáza odmietla zápis (porušenie obmedzení) |
| `422` | Neplatné údaje | Zlé alebo chýbajúce polia v tele požiadavky |
| `500` | Chyba servera | Neočakávaná chyba |
| `503` | Databáza nedostupná | Nedá sa pripojiť k databáze |

Chybová odpoveď má vždy tvar:
```json
{ "detail": "Zrozumiteľný popis chyby" }
```
Pri validačných chybách (422) je `detail` zoznam s presným polohou chyby (pole a dôvod).

---

## 4. Prehľad endpointov

| Čo chcem urobiť | Metóda | Adresa | Kľúč? |
| --- | --- | --- | :---: |
| Zistiť, či API beží | `GET` | `/health` | nie |
| Zistiť, či funguje databáza | `GET` | `/api/v1/db/health` | nie |
| Vypísať **všetkých** zamestnancov | `GET` | `/api/v1/employees` | áno |
| Zobraziť jedného zamestnanca | `GET` | `/api/v1/employees/{id}` | áno |
| Pridať zamestnanca | `POST` | `/api/v1/employees` | áno |
| Upraviť zamestnanca | `PUT` / `PATCH` | `/api/v1/employees/{id}` | áno |
| Deaktivovať zamestnanca | `DELETE` | `/api/v1/employees/{id}` | áno |
| Vypísať typy zamestnancov | `GET` | `/api/v1/employee-types` | áno |

---

## 5. Polia zamestnanca — kompletná referencia

### 5.1 Polia, ktoré posielaš ty (vstup pri POST / PUT / PATCH)

| Pole | Typ | Povinné | Max znakov | Povolené hodnoty | Popis |
| --- | --- | :---: | :---: | --- | --- |
| `surname` | text | **áno** (pri POST) | 1–50 | ľubovoľný text | Priezvisko zamestnanca. |
| `forename` | text | nie | 0–50 | ľubovoľný text | Meno (krstné). |
| `type` | text | nie | 0–50 | **len názov z tabuľky typov** (kap. 6) | Kategória zamestnanca. Musí presne sedieť s existujúcim typom. |
| `rfid` | text | nie | 0–50 | číslice/znaky karty | Číslo prístupovej **RFID/NFC karty** (ako číslo čipovej karty). |
| `rfid_gate` | číslo | nie | — | `0` alebo `1` | Smie prejsť cez **veľkú bránu**? `1` = áno, `0` = nie. |
| `rfid_littlegate` | číslo | nie | — | `0` alebo `1` | Smie prejsť cez **braničku (malá bránka pre peších)**? `1` = áno, `0` = nie. |
| `ecv` | text | nie | 0–50 | napr. `ZA605JD` | Evidenčné číslo vozidla (ŠPZ). |
| `allowed_from` | dátum a čas | nie | — | ISO 8601 | Prístup platný **od** (napr. `2025-01-01T00:00:00`). |
| `allowed_to` | dátum a čas | nie | — | ISO 8601 | Prístup platný **do** (napr. `2199-01-01T00:00:00` = bez obmedzenia). |
| `note` | text | nie | 0–200 | ľubovoľný text | Poznámka (napr. dôvod prístupu). |

**Dôležité pravidlá:**
- **Iné polia sú zakázané.** Ak pošleš neznáme pole (napr. `object_id`, `id`,
  `active`, `xyz`), API vráti **422** (`Extra inputs are not permitted`).
- `object_id` sa **nedá poslať** — vždy sa nastaví na `127`.
- Pri `PUT`/`PATCH` musí byť aspoň **jedno** upraviteľné pole, inak **422**.

### 5.2 Vysvetlenie kľúčových polí

- **`rfid`** — je to identifikátor bezkontaktnej karty/čipu (RFID/NFC), teda „číslo
  karty", ktorou sa človek prikladá k čítačke. Ukladá sa ako text (môže mať aj
  úvodné nuly), max 50 znakov. Napr. `"0234839966"`.
- **`rfid_gate`** — či daná karta **otvorí veľkú bránu** (hlavný vjazd, typicky pre
  autá / veľký vstup). `1` = smie prejsť, `0` = nesmie.
- **`rfid_littlegate`** — či daná karta **otvorí braničku** (malá bránka pre peších
  vedľa hlavnej brány). `1` = smie prejsť, `0` = nesmie.
- Tieto dve polia sú nezávislé: človek môže mať povolenú bránu aj braničku, len
  jedno z nich, alebo nič.
- **`allowed_from` / `allowed_to`** — časové okno platnosti prístupu. Formát je
  ISO 8601: `RRRR-MM-DDThh:mm:ss`. Ak má prístup platiť „navždy", dáva sa vzdialený
  dátum, napr. `2199-01-01T00:00:00`.

### 5.3 Polia, ktoré nastavuje systém automaticky (vidíš ich len v odpovedi)

| Pole | Popis |
| --- | --- |
| `id` | Jedinečné číslo záznamu (prideľuje databáza). Používa sa v URL. |
| `object_id` | Vždy `127`. |
| `active` | `1` = aktívny, `0` = deaktivovaný (po DELETE). Pri vytvorení vždy `1`. |
| `bozp_state` | Stav BOZP školenia. Pri vytvorení `"NO BOZP"`. Cez API sa neupravuje. |
| `bozp_required` | Či je BOZP potrebné (`0`/`1`). Pri vytvorení `0`. Cez API sa neupravuje. |
| `created` | Dátum a čas vytvorenia (nastaví sa automaticky). |
| `modified` | Dátum a čas poslednej úpravy (nastaví sa automaticky). |
| `row_id` | Interný technický identifikátor (UUID), môže byť `null`. |

### 5.4 Vzor kompletnej odpovede (jeden zamestnanec)

```json
{
  "id": 393,
  "object_id": 127,
  "forename": "Jozef",
  "surname": "Comorek",
  "type": "Zamestnanec 1B",
  "rfid": "0234839966",
  "rfid_gate": 1,
  "rfid_littlegate": 0,
  "ecv": "ZA605JD",
  "allowed_from": "2023-09-19T11:58:00",
  "allowed_to": "2199-01-01T00:00:00",
  "note": "vstupy kvôli autu",
  "row_id": "398fad29-0ec9-11ef-a405-48210b3d677f",
  "created": "2024-05-10T14:31:28",
  "modified": "2026-04-23T10:01:21",
  "active": 1,
  "bozp_required": 1,
  "bozp_state": "OK"
}
```

---

## 6. Typy zamestnancov

Pole `type` **musí** byť jeden z názvov z tabuľky typov. Ak pošleš iný text, API
vráti **422**. Aktuálny zoznam vždy získaš zavolaním:

```bash
curl -H "X-API-Key: $KEY" http://127.0.0.1:8000/api/v1/employee-types
```

**Aktuálne dostupné typy (objekt 127):**

| Typ | Bežné použitie |
| --- | --- |
| `Dopravca` | Vodič/dopravca s prístupom (zvyčajne cez veľkú bránu). |
| `Externý partner` | Externá spolupracujúca firma/osoba. |
| `Externý zamestnanec` | Zamestnanec externej firmy. |
| `Návšteva 1` | Návšteva — kategória 1. |
| `Návšteva 2` | Návšteva — kategória 2. |
| `Návšteva 3` | Návšteva — kategória 3. |
| `Návšteva 4` | Návšteva — kategória 4. |
| `Zamestnanec 1` | Interný zamestnanec — kategória 1. |
| `Zamestnanec 1A` | Interný zamestnanec — kategória 1A. |
| `Zamestnanec 1B` | Interný zamestnanec — kategória 1B. |
| `Zamestnanec 1C` | Interný zamestnanec — kategória 1C. |
| `Zamestnanec 2` | Interný zamestnanec — kategória 2. |
| `Zamestnanec 3` | Interný zamestnanec — kategória 3. |
| `Zamestnanec 4` | Interný zamestnanec — kategória 4. |

> Poznámka: názvy sú presné reťazce vrátane medzier a diakritiky. Zoznam sa môže
> v čase meniť — smerodajný je vždy výstup z `/api/v1/employee-types`.

---

## 7. Endpointy detailne

### 7.1 `GET /health` — beží API?

Overí, že aplikácia je nažive. **Kľúč netreba.**

```bash
curl http://127.0.0.1:8000/health
```
Odpoveď `200`:
```json
{ "status": "ok" }
```

---

### 7.2 `GET /api/v1/db/health` — funguje databáza?

Otvorí skutočné spojenie do databázy. **Kľúč netreba.**

```bash
curl http://127.0.0.1:8000/api/v1/db/health
```
Odpoveď `200`:
```json
{ "status": "ok", "database": "connected" }
```
Ak databáza nie je dostupná, vráti `503` s popisom.

---

### 7.3 `GET /api/v1/employees` — vypíš všetkých zamestnancov

Vráti **všetkých aktívnych** zamestnancov objektu 127, zoradených podľa
priezviska, mena a `id`. **Bez filtrov a bez stránkovania** — všetko naraz.

```bash
curl -H "X-API-Key: $KEY" http://127.0.0.1:8000/api/v1/employees
```
Odpoveď `200`:
```json
{
  "data": [
    { "id": 12, "surname": "Comorek", "forename": "Jozef", "type": "Zamestnanec 1B", "...": "..." },
    { "id": 45, "surname": "Novák",   "forename": "Peter", "type": "Dopravca",       "...": "..." }
  ]
}
```
> Prípadné query parametre (napr. `?surname=...`) sa **ignorujú** — endpoint vždy
> vráti kompletný zoznam.

---

### 7.4 `GET /api/v1/employees/{id}` — zobraz jedného zamestnanca

```bash
curl -H "X-API-Key: $KEY" http://127.0.0.1:8000/api/v1/employees/393
```
- `200` → objekt zamestnanca (ako v kap. 5.4).
- `404` → neexistuje alebo je deaktivovaný (`{"detail":"Zamestnanec 393 neexistuje alebo je neaktívny"}`).

---

### 7.5 `POST /api/v1/employees` — pridaj zamestnanca

Povinné je len `surname`. Ostatné polia sú nepovinné (viď kap. 5.1).

```bash
curl -X POST http://127.0.0.1:8000/api/v1/employees \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "surname": "Novák",
    "forename": "Peter",
    "type": "Zamestnanec 1",
    "rfid": "0234839966",
    "rfid_gate": 1,
    "rfid_littlegate": 1,
    "ecv": "ZA605JD",
    "allowed_from": "2025-01-01T00:00:00",
    "allowed_to": "2199-01-01T00:00:00",
    "note": "Nový stály zamestnanec"
  }'
```
- `201` → vráti sa celý vytvorený záznam (s `id`, `object_id: 127`, `active: 1`, časmi).
- Systém automaticky doplní: `object_id=127`, `active=1`, `bozp_state="NO BOZP"`,
  `bozp_required=0`, `created`, `modified`.
- `422` → chýba `surname`, zlý `type`, `rfid_gate` mimo `0/1`, alebo neznáme pole.

---

### 7.6 `PUT` / `PATCH` `/api/v1/employees/{id}` — uprav zamestnanca

Obe metódy upravia len polia, ktoré pošleš (ostatné ostanú nezmenené). Musíš
poslať aspoň jedno pole.

```bash
# Zmena poznámky a vypnutie prístupu cez braničku
curl -X PATCH http://127.0.0.1:8000/api/v1/employees/393 \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{ "note": "Zmena zaradenia", "rfid_littlegate": 0 }'
```
- `200` → vráti sa celý upravený záznam.
- `404` → zamestnanec neexistuje alebo je neaktívny.
- `422` → prázdne telo, zlý `type`, `rfid_gate` mimo `0/1`, alebo neznáme pole.
- `surname`, ak ho pošleš, musí mať 1–50 znakov. `id`, `active`, `object_id` sa upraviť nedajú.

---

### 7.7 `DELETE /api/v1/employees/{id}` — deaktivuj zamestnanca

**Soft delete** — záznam sa fyzicky nezmaže, len sa nastaví `active = 0`. Prestane
sa zobrazovať v zozname a v deteile (404), ale ostáva v databáze.

```bash
curl -X DELETE -H "X-API-Key: $KEY" http://127.0.0.1:8000/api/v1/employees/393
```
Odpoveď `200`:
```json
{ "status": "deleted", "id": 393 }
```
- `404` → zamestnanec už neexistuje alebo je už deaktivovaný.

---

### 7.8 `GET /api/v1/employee-types` — vypíš typy

Vráti povolené hodnoty pre pole `type` (aktívne typy objektu 127).

```bash
curl -H "X-API-Key: $KEY" http://127.0.0.1:8000/api/v1/employee-types
```
Odpoveď `200`:
```json
{ "data": [ { "id": 1, "name": "Zamestnanec 1", "...": "..." } ] }
```

---

## 8. Príklady použitia (recepty)

Nasledujúce „defaultné" nastavenia sú odporúčané vzory pre bežné situácie.
Uprav si podľa potreby.

### Recept A — Stály zamestnanec s plným prístupom
Karta otvára bránu aj braničku, platnosť „navždy".
```json
{
  "surname": "Novák",
  "forename": "Peter",
  "type": "Zamestnanec 1",
  "rfid": "0011002233",
  "rfid_gate": 1,
  "rfid_littlegate": 1,
  "allowed_from": "2025-01-01T00:00:00",
  "allowed_to": "2199-01-01T00:00:00",
  "note": "Stály zamestnanec"
}
```

### Recept B — Dopravca (len veľká brána, autom)
Prejde cez bránu (auto), nie cez braničku pre peších. Vyplnené ŠPZ.
```json
{
  "surname": "Kováč",
  "forename": "Ján",
  "type": "Dopravca",
  "rfid": "0055667788",
  "rfid_gate": 1,
  "rfid_littlegate": 0,
  "ecv": "BA123XY",
  "allowed_from": "2025-06-01T06:00:00",
  "allowed_to": "2199-01-01T00:00:00",
  "note": "Zásobovanie"
}
```

### Recept C — Návšteva na jeden deň (len branička)
Peší vstup cez braničku, časovo obmedzený na jeden deň.
```json
{
  "surname": "Horváth",
  "forename": "Eva",
  "type": "Návšteva 1",
  "rfid": "0099887766",
  "rfid_gate": 0,
  "rfid_littlegate": 1,
  "allowed_from": "2025-07-14T08:00:00",
  "allowed_to": "2025-07-14T18:00:00",
  "note": "Návšteva – rokovanie"
}
```

### Recept D — Zamestnanec bez karty (zatiaľ bez prístupu)
Evidovaný, ale bez RFID a bez povolení. Prístup sa doplní neskôr cez PATCH.
```json
{
  "surname": "Malá",
  "forename": "Zuzana",
  "type": "Zamestnanec 2",
  "rfid_gate": 0,
  "rfid_littlegate": 0,
  "note": "Karta bude pridelená neskôr"
}
```

### Recept E — Odobratie prístupu (bez zmazania)
Zamestnanec ostáva evidovaný, ale kartu už nepustí nikde.
```bash
curl -X PATCH http://127.0.0.1:8000/api/v1/employees/393 \
  -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{ "rfid_gate": 0, "rfid_littlegate": 0, "allowed_to": "2025-07-14T00:00:00" }'
```

---

## 9. Časté chyby

| Situácia | Kód | Príklad odpovede |
| --- | --- | --- |
| Chýba API kľúč | 401 | `{"detail":"Chýbajúci alebo neplatný API kľúč"}` |
| Chýba `surname` | 422 | `{"detail":[{"loc":["body","surname"],"msg":"Field required"}]}` |
| Neplatný `type` | 422 | `{"detail":"Neplatný typ zamestnanca: 'XY'. Použite niektorý z názvov z GET /api/v1/employee-types."}` |
| `rfid_gate` iné než 0/1 | 422 | `{"detail":[{"loc":["body","rfid_gate"],"msg":"Input should be less than or equal to 1"}]}` |
| Poslané zakázané pole (napr. `object_id`) | 422 | `{"detail":[{"loc":["body","object_id"],"msg":"Extra inputs are not permitted"}]}` |
| Prázdne telo pri PATCH/PUT | 422 | `{"detail":"Telo požiadavky musí obsahovať aspoň jedno upraviteľné pole"}` |
| Neexistujúci/neaktívny zamestnanec | 404 | `{"detail":"Zamestnanec 999 neexistuje alebo je neaktívny"}` |

---

*Tip: Najrýchlejšie si všetko vyskúšaš cez interaktívne rozhranie na
**http://127.0.0.1:8000/docs** — klikni **Authorize**, vlož API kľúč a skúšaj
jednotlivé endpointy priamo v prehliadači.*
