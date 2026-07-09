# API Dokumentácia — RestApiCoba (Zamestnanci)

Jednoduchý návod, ako používať toto API. Netreba žiadne špeciálne znalosti —
každý endpoint je popísaný: čo robí, čo mu treba poslať a čo vráti.

---

## 1. Základné informácie

- **Základná adresa:** `http://127.0.0.1:8000`
- Všetky dáta sa posielajú aj vracajú vo formáte **JSON**.
- Pri posielaní dát (POST, PUT, PATCH) treba hlavičku `Content-Type: application/json`.
- API pracuje so zamestnancami — vie ich **vypísať, vyhľadať, pridať, upraviť
  a deaktivovať**. Nič sa nikdy fyzicky nemaže.
- Interaktívne rozhranie na klikanie a skúšanie: **http://127.0.0.1:8000/docs**

### Rýchly prehľad všetkých endpointov

| Čo chcem urobiť | Metóda | Adresa |
| --- | --- | --- |
| Zistiť, či API beží | `GET` | `/health` |
| Zistiť, či funguje databáza | `GET` | `/api/v1/db/health` |
| Vypísať / vyhľadať zamestnancov | `GET` | `/api/v1/employees` |
| Zobraziť jedného zamestnanca | `GET` | `/api/v1/employees/{id}` |
| Pridať zamestnanca | `POST` | `/api/v1/employees` |
| Upraviť zamestnanca | `PUT` alebo `PATCH` | `/api/v1/employees/{id}` |
| Vymazať zamestnanca (deaktivovať) | `DELETE` | `/api/v1/employees/{id}` |
| Vypísať typy zamestnancov | `GET` | `/api/v1/employee-types` |

### Ako čítať odpovede — stavové kódy

| Kód | Význam |
| --- | --- |
| **200** | Všetko prebehlo v poriadku |
| **201** | Záznam bol úspešne vytvorený |
| **404** | Záznam neexistuje (alebo je neaktívny) |
| **422** | Poslal si nesprávne údaje — v odpovedi je napísané, čo je zle |
| **503** | Databáza je nedostupná |
| **500** | Neočakávaná chyba servera |

Každá chyba má vždy rovnaký tvar — pole `detail` s vysvetlením po slovensky:

```json
{ "detail": "Zamestnanec 999 neexistuje alebo je neaktívny" }
```

---

## 2. Kontrola, či všetko beží

### `GET /health` — beží API?

Nič sa neposiela. Odpoveď:

```json
{ "status": "ok" }
```

### `GET /api/v1/db/health` — funguje databáza?

API sa skutočne pripojí k databáze a spraví testovací dotaz. Odpoveď pri úspechu:

```json
{ "status": "ok", "database": "connected" }
```

Ak databáza nefunguje, príde kód **503** a v `detail` je dôvod (bez hesla).

```bash
curl "http://127.0.0.1:8000/api/v1/db/health"
```

---

## 3. Zoznam a vyhľadávanie zamestnancov

### `GET /api/v1/employees`

Vráti zoznam **aktívnych** zamestnancov, zoradený podľa priezviska a mena.
Vymazaní (deaktivovaní) zamestnanci sa v zozname nikdy neukážu.

**Parametre** (všetky sú nepovinné, pridávajú sa do adresy za `?`):

| Parameter | Typ | Čo robí | Príklad |
| --- | --- | --- | --- |
| `page` | číslo | Ktorú stranu zobraziť (od 1) | `page=2` |
| `page_size` | číslo | Koľko záznamov na stranu (max 100) | `page_size=50` |
| `forename` | text | Hľadá v mene (stačí časť slova) | `forename=jan` |
| `surname` | text | Hľadá v priezvisku (stačí časť slova) | `surname=novak` |
| `type` | text | Hľadá podľa typu zamestnanca | `type=dopravca` |
| `rfid` | text | Hľadá podľa RFID čipu | `rfid=1234` |
| `rfid_gate` | 0 / 1 / 2 | Prístup cez bránu: `0` = nie, `1` = áno, `2` = všetci | `rfid_gate=1` |
| `rfid_littlegate` | 0 / 1 / 2 | Prístup cez malú bránu (rovnako ako brána) | `rfid_littlegate=0` |
| `ecv` | text | Hľadá podľa EČV vozidla | `ecv=MT123` |
| `note` | text | Hľadá v poznámke | `note=servis` |
| `bozp_state` | text | Hľadá podľa stavu BOZP školenia | `bozp_state=OK` |
| `object_id` | číslo | Objekt — keď sa nezadá, použije sa predvolený | `object_id=127` |

**Dobré vedieť:**
- Textové hľadanie nerozlišuje veľké a malé písmená a stačí časť slova —
  `surname=nov` nájde „Novák" aj „Kovaľnová".
- Filtre sa dajú kombinovať: `?surname=novak&rfid_gate=1&page=1&page_size=20`
- `page_size` väčšie ako 100 vráti chybu 422.

**Príklad:**

```bash
curl "http://127.0.0.1:8000/api/v1/employees?surname=novak&page=1&page_size=5"
```

**Odpoveď:**

```json
{
  "data": [
    {
      "id": 12,
      "object_id": 127,
      "forename": "Ján",
      "surname": "Novák",
      "type": "Zamestnanec",
      "rfid": "0012345678",
      "rfid_gate": 1,
      "rfid_littlegate": 0,
      "ecv": "MT123AB",
      "allowed_from": "2026-01-01T08:00:00",
      "allowed_to": "2026-12-31T23:59:59",
      "note": "servisný technik",
      "row_id": "abc-123-...",
      "created": "2026-01-01T08:00:00",
      "modified": "2026-06-01T10:30:00",
      "active": 1,
      "bozp_required": 0,
      "bozp_state": "OK"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 5,
    "total": 337,
    "pages": 68
  }
}
```

Časť `pagination` hovorí: si na strane 1, po 5 záznamov, spolu je 337
zamestnancov, teda 68 strán.

---

## 4. Detail jedného zamestnanca

### `GET /api/v1/employees/{id}`

Namiesto `{id}` sa dá číslo zamestnanca. Vráti všetky jeho údaje (rovnaké
polia ako v zozname vyššie).

```bash
curl "http://127.0.0.1:8000/api/v1/employees/12"
```

- Ak zamestnanec neexistuje **alebo je deaktivovaný**, príde **404**.

---

## 5. Pridanie zamestnanca

### `POST /api/v1/employees`

**Povinné je iba priezvisko (`surname`).** Všetko ostatné je nepovinné.

| Pole | Typ | Povinné? | Význam |
| --- | --- | --- | --- |
| `surname` | text (max 50) | **áno** | Priezvisko |
| `forename` | text (max 50) | nie | Meno |
| `type` | text (max 50) | nie | Typ zamestnanca (pozri `/employee-types`) |
| `rfid` | text (max 50) | nie | Číslo RFID čipu |
| `rfid_gate` | 0 alebo 1 | nie | Prístup cez bránu |
| `rfid_littlegate` | 0 alebo 1 | nie | Prístup cez malú bránu |
| `ecv` | text (max 50) | nie | EČV vozidla |
| `allowed_from` | dátum a čas | nie | Odkedy má prístup |
| `allowed_to` | dátum a čas | nie | Dokedy má prístup |
| `note` | text (max 200) | nie | Poznámka |
| `object_id` | číslo | nie | Objekt — keď sa nezadá, doplní sa predvolený |

Dátum a čas sa píše v tvare `2026-01-01T08:00:00`.

**Automaticky sa nastaví** (netreba a ani sa nedá poslať):
`active = 1` (aktívny), `bozp_state = "NO BOZP"`, `bozp_required = 0`,
dátumy `created` a `modified`.

**Príklad:**

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/employees" \
  -H "Content-Type: application/json" \
  -d '{
    "forename": "Ján",
    "surname": "Novák",
    "type": "Zamestnanec",
    "rfid": "0012345678",
    "rfid_gate": 1,
    "ecv": "MT123AB",
    "note": "servisný technik"
  }'
```

**Odpoveď:** kód **201** a celý vytvorený zamestnanec aj s prideleným `id`.

**Časté chyby (422):**
- chýba `surname`
- poslané pole, ktoré neexistuje (preklep v názve)
- `rfid_gate` iné ako 0 alebo 1
- pokus poslať `id` alebo `active` — tie sa nastavujú automaticky

---

## 6. Úprava zamestnanca

### `PUT /api/v1/employees/{id}` alebo `PATCH /api/v1/employees/{id}`

Obe metódy fungujú rovnako: **pošli len tie polia, ktoré chceš zmeniť** —
ostatné ostanú nezmenené. Upraviteľné polia sú rovnaké ako pri pridávaní
(okrem `object_id`): `forename`, `surname`, `type`, `rfid`, `rfid_gate`,
`rfid_littlegate`, `ecv`, `allowed_from`, `allowed_to`, `note`.

**Nedá sa zmeniť:** `id` ani `active` (pokus vráti 422).

**Príklad — zmena poznámky a RFID:**

```bash
curl -X PATCH "http://127.0.0.1:8000/api/v1/employees/12" \
  -H "Content-Type: application/json" \
  -d '{ "note": "presunutý na vrátnicu", "rfid": "0099887766" }'
```

**Odpoveď:** kód **200** a celý zamestnanec už s novými údajmi.
Dátum `modified` sa aktualizuje automaticky.

- Ak zamestnanec neexistuje alebo je deaktivovaný → **404**.
- Prázdne telo požiadavky → **422**.

---

## 7. Vymazanie zamestnanca (deaktivácia)

### `DELETE /api/v1/employees/{id}`

> ⚠️ **Dôležité:** Záznam sa **nikdy fyzicky nemaže.** API len nastaví
> `active = 0` — zamestnanec zmizne zo zoznamov a z detailu, ale v databáze
> ostáva navždy.

```bash
curl -X DELETE "http://127.0.0.1:8000/api/v1/employees/12"
```

**Odpoveď:**

```json
{ "status": "deleted", "id": 12 }
```

- Druhé vymazanie toho istého zamestnanca vráti **404** (už je neaktívny).

---

## 8. Typy zamestnancov

### `GET /api/v1/employee-types`

Vráti zoznam aktívnych typov zamestnancov (napr. Dopravca, Návšteva,
Externý partner...), zoradený podľa názvu. **Iba na čítanie** — typy sa cez
toto API nedajú pridávať ani meniť.

```bash
curl "http://127.0.0.1:8000/api/v1/employee-types"
```

**Odpoveď:**

```json
{
  "data": [
    { "id": 1, "name": "Dopravca", "active": 1, "object_id": 127, "..." : "..." },
    { "id": 2, "name": "Externý partner", "active": 1, "object_id": 127, "..." : "..." }
  ]
}
```

Hodnota z poľa `name` sa dá použiť ako `type` pri pridávaní zamestnanca.

---

## 9. Význam polí zamestnanca

| Pole | Význam |
| --- | --- |
| `id` | Jedinečné číslo zamestnanca (prideľuje databáza) |
| `object_id` | Číslo objektu/areálu, ku ktorému zamestnanec patrí |
| `forename` / `surname` | Meno / priezvisko |
| `type` | Typ zamestnanca (text, pozri `/employee-types`) |
| `rfid` | Číslo prístupového RFID čipu |
| `rfid_gate` | Prístup cez hlavnú bránu: 1 = má, 0 = nemá |
| `rfid_littlegate` | Prístup cez malú bránu: 1 = má, 0 = nemá |
| `ecv` | Evidenčné číslo vozidla |
| `allowed_from` / `allowed_to` | Odkedy / dokedy má povolený prístup |
| `note` | Ľubovoľná poznámka |
| `active` | 1 = aktívny, 0 = vymazaný (deaktivovaný) |
| `bozp_state` | Stav BOZP školenia (napr. `OK`, `EXPIRED`, `NO BOZP`) |
| `bozp_required` | 1 = vyžaduje sa BOZP školenie, 0 = nevyžaduje |
| `created` / `modified` | Kedy bol záznam vytvorený / naposledy zmenený |
| `row_id` | Interný identifikátor databázy (netreba riešiť) |
