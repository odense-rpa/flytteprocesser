# Flytteprocesser

Automatisering der behandler flyttesager i Eflyt for Odense Kommune. Python-genimplementering af den tidligere Blue Prism-proces "BKF - flytteprocesser".

## Hvad gør robotten?

1. **Fremsøger flyttesager** i Eflyt inden for et rullende datointerval (4 dage tilbage til 2 dage frem) for tre sagstyper: *Simpel flytning*, *Særlig adresse* og *Boligselskab*
2. **Filtrerer** sager på korrekt flyttetype og lægger nye/ikke-fejlede sager i arbejdskøen med sagsnummer som reference
3. **Simpel flytning**: Henter sagsdetaljer og tæller beboere med/uden registreret fraflytningsadresse
   - Godkender sagen automatisk hvis alle beboere fraflytter
   - Ellers findes den beboer der har boet længst på adressen, og der sendes en logiværtserklæring til vedkommende – hvis der er plads nok på adressen
4. **Særlig adresse / Boligselskab**: Endnu ikke implementeret

## Forudsætninger

- Python ≥ 3.13
- [`uv`](https://docs.astral.sh/uv/) til pakkehåndtering
- Adgang til **Automation Server** (arbejdskø)
- Adgang til **Eflyt** (produktion)
- En **Odense SQL Server**-konto til tracking

## Installation

```sh
uv sync
```

## Konfiguration

Kopiér `.env.example` til `.env` og udfyld efter behov (Automation Server-variabler jf. `automation-server-client`-dokumentationen).

Credentials til Eflyt (`eFlyt`) og tracking (`Odense SQL Server`) hentes via `automation_server_client.Credential` og skal være oprettet på Automation Server-instansen.

## Kørsel

```sh
# Fyld arbejdskøen med nye flyttesager
uv run python main.py --queue

# Behandl arbejdskøen
uv run python main.py
```

### Argumenter

| Argument | Beskrivelse |
|---|---|
| `--queue` | Ryd og fyld arbejdskøen med nye sager, og afslut (kør ingen behandling) |

## Afhængigheder

| Pakke | Formål |
|---|---|
| `automation-server-client` | Arbejdskø-håndtering |
| `eflyt-client` | Integration med Eflyt |
| `odk-tools` | Aktivitetssporing |

## Persondatasikkerhed

Robotten behandler personoplysninger på vegne af Odense Kommune, herunder CPR-numre, navne og adresser fra Eflyt.

- Ingen personoplysninger må lægges i dette repository — hverken som testdata, i kode, i kommentarer, i commit-beskeder eller i issues. Brug altid fiktive/anonymiserede eksempler
- `.env` er ekskluderet via `.gitignore` og må aldrig committes
- Legitimationsoplysninger håndteres udelukkende via miljøvariabler (`.env`) og Automation Server Credentials — aldrig hardkodet
- Logning bør undgå at skrive personoplysninger til logfiler; log sagsnummer/reference frem for CPR/navn hvor muligt
- Ved fejlsøgning eller deling af data/output uden for produktionsmiljøet skal personoplysninger maskeres eller fjernes først

## Udvikling

Ved commits opdateres:

- `version` i `pyproject.toml` (semver)
- Denne README, hvis funktionalitet eller opsætning ændres
