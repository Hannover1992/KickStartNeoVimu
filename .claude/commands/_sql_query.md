---
status: v1.1
version: "1.1"
created: 2026-03-09
op: SqlQuery
type: satellite
---

# /_sql_query — Dev-DB Query (Auto-Discovery)

**Status:** v1.1
**Typ:** Satelliten-Command (DB-Abfrage)
**Actor:** DU (direkt, kein Team)
**Modus:** READONLY

---

## Vertrag

```
+==============================================================+
|  COMMAND: /_sql_query <SQL>                                  |
+==============================================================+
|                                                              |
|  SYNTAX:                                                     |
|    /_sql_query SELECT Id, Name FROM dbo.Foo WHERE Id = 'x'  |
|                                                              |
|  LIEST (Auto-Discovery, Reihenfolge):                       |
|    1. Sources/.env                                           |
|    2. Sources/docker-compose.yml                             |
|    3. docker-compose.yml (Root)                              |
|                                                              |
|  SCHREIBT: NICHTS                                           |
|                                                              |
+==============================================================+
```

---

## Schritt 1: Verbindungsdaten auto-discovern

Suche im aktuellen Projektverzeichnis nach Konfigurationsdateien.

**Kandidaten (in Reihenfolge):**
1. `Sources/.env`
2. `Sources/docker-compose.yml`
3. `docker-compose.yml`

Lies die erste gefundene Datei und extrahiere:

| Feld       | Suche nach                                      | Fallback      |
|------------|-------------------------------------------------|---------------|
| `SERVER`   | `SA_HOST`, `DB_HOST`, `localhost` + Port         | `localhost,5433` |
| `PORT`     | `SA_PORT`, `DB_PORT`, ports-Mapping (`XXXX:1433`)| `5433`        |
| `USER`     | `SA_USER`, `MSSQL_USER`, erster non-sa Account  | `dcsp`        |
| `PASSWORD` | `SA_PASSWORD`, `MSSQL_SA_PASSWORD`              | —             |
| `DATABASE` | `DB_NAME`, `DATABASE`, Service-Name             | `dcsp`        |

**Wichtig:** Verwende NIEMALS `sa` mit `-d <database>` — das schlägt fehl.
- Falls nur `sa`-Credentials gefunden: nutze `sa` OHNE `-d`-Flag, oder suche App-Account.
- Falls App-Account gefunden (z.B. `dcsp`): nutze App-Account + `-d <db>`.

---

## Schritt 2: SQL aus Argumenten

`$ARGUMENTS` enthält das vollständige SQL-Statement.

Falls leer → zeige Beispiele und STOP:
```
Verwendung: /_sql_query <SQL>

Beispiele:
  /_sql_query SELECT TOP 5 * FROM dbo.Versorgungsvertrag
  /_sql_query SELECT COUNT(*) FROM dbo.Pflegeeinrichtung
  /_sql_query SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'Foo'
```

---

## Schritt 3: sqlcmd ausführen

**Mit App-Account + Datenbank:**
```bash
sqlcmd -S "{SERVER},{PORT}" -U {USER} -P "{PASSWORD}" -d {DATABASE} -C -N -W -Q "{SQL}"
```

**Mit sa (nur ohne -d):**
```bash
sqlcmd -S "{SERVER},{PORT}" -U sa -P "{SA_PASSWORD}" -C -N -W -Q "{SQL}"
```

Flags:
- `-C` — TrustServerCertificate (Pflicht bei selbstsigniertem Zert)
- `-N` — Encrypt
- `-W` — Trailing Spaces entfernen (saubererer Output)

---

## Schritt 4: Ergebnis ausgeben

```
DB:    {SERVER}:{PORT}/{DATABASE}
Query: {SQL}
─────────────────────────────────────────
{ERGEBNIS}
─────────────────────────────────────────
{N} Zeile(n).
```

**Fehlerfall — DB nicht erreichbar:**
```
FEHLER: Verbindung fehlgeschlagen ({SERVER}:{PORT}).
→ Docker-Container läuft? Prüfe: docker ps
```

**Fehlerfall — SQL-Fehler:**
```
SQL-FEHLER: {Fehlermeldung}
```

---

**Version:** 1.1 — Auto-Discovery statt statischer Meta-Datei
