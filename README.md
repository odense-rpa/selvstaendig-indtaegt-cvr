# Selvstændig Indkomst — CVR-kontrol

Kontrollerer borgere på ydelse med selvstændig indkomst op mod CVR-registeret for at identificere, om de er registreret som deltagere i virksomheder inden for Odense Kommune.

## Hvad gør robotten?

1. Indlæser en liste over borgere (CPR-numre) fra en Excel-fil (`documents/Borgere.xlsx`), der skal placeres manuelt inden kørsel.
2. Tilføjer borgere til en arbejdskø i Automation Server, hvis de ikke allerede er i køen.
3. For hver borger i køen forespørges SQL-tabellen `cvr_aktuelle_fad` for CVR-tilknytninger baseret på CPR-nummer.
4. Borgere uden CVR-nummer rapporteres i gruppen **Intet CVRnr**.
5. Borgere med CVR-nummer rapporteres i gruppen **Borgere med CVRnr** med CVR-nummer og antal tilknytninger.
6. Aktivitet spores via Tracker mod Odense SQL Server.

## Forudsætninger

- Python ≥ 3.13
- [`uv`](https://docs.astral.sh/uv/) til pakkehåndtering
- Adgang til **Automation Server** (arbejdskø og credentials)
- Adgang til **Odense SQL Server** med tabellen `cvr_aktuelle_fad`

## Installation

```sh
uv sync
```

## Konfiguration

Credentials registreres i Automation Server:
- `Odense SQL Server` — indeholder `server`- og `database`-felter og bruges til både databaseforbindelsen og tracking.

Miljøvariabler:

| Variabel | Beskrivelse |
|---|---|
| `ATS_URL` | URL til Automation Server API (f.eks. `http://localhost/api`) |
| `ATS_TOKEN` | Bearer token til autentificering mod Automation Server |
| `ATS_WORKQUEUE_OVERRIDE` | Valgfri override af arbejdskø-ID |

## Kørsel

Placer Excel-filen med borgerlisten i `documents/Borgere.xlsx` inden kørsel.

```sh
uv run python main.py --queue   # Fyld arbejdskøen
uv run python main.py           # Behandl arbejdskøen
```

## Afhængigheder

| Pakke | Formål |
|---|---|
| `automation-server-client` | Klient til Automation Server — håndterer arbejdskø, credentials og work items |
| `odk-tools` | Odense-specifikke hjælpeværktøjer til tracking og rapportering |
| `openpyxl` | Læser Excel-filen med borgerlisten |
| `pymssql` | Forbindelse til Microsoft SQL Server for CVR-opslag |
| `ruff` | Python linter/formatter |

## GDPR og sikkerhed

Processen behandler CPR-numre på borgere, der modtager ydelse med selvstændig indkomst, samt CVR-oplysninger og navne (`Navn_FAD`) hentet fra SQL-databasen. Oplysningerne forlader ikke SQL-serveren eller Automation Server — de fremgår af rapporter i Automation Server, som kun er tilgængelige for brugere med adgang hertil.
