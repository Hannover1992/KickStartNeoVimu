---
type: utility
status: active
version: 1.0.0
created: 2026-05-17
op: ReverseLookup
phase: Post-Pipeline
tier: haiku
depends_on:
  - propagate_provenance.py (BL-160 SB-3)
  - validate_source_provenance.py (BL-160 SB-4)
related:
  - _backlog
  - _w_user_story_extended
backlog_origin: BL-160
ak_refs: [AK-4]
---

# /_origin — Reverse-Lookup Coherenz-Kette

**Status:** v1.0 (BL-160 AK-4 2026-05-17)
**Actor:** PROVENANCE-NAVIGATOR
**Zweck:** Reverse-Lookup von beliebigem Artefakt bis Original-URL. Antwortet "Wo kommt das eigentlich her?" in 5 Jahren noch.

---

## Vertrag

```
+===========================================================================+
|  COMMAND: /_origin {target} [--confirm] [--max-hops=10]                  |
+===========================================================================+
|                                                                           |
|  KERN-PROBLEM:                                                            |
|    Code-Zeile, AK-Block, oder Spec-Abschnitt existiert — aber woher      |
|    kommt er urspruenglich? Ohne Coherenz-Kette reisst Traceability       |
|    nach jeder Pipeline-Stufe ab. In 5 Jahren ist Confluence-PageId       |
|    406159586 nicht mehr im Code sichtbar.                                 |
|                                                                           |
|  KERN-PRINZIP (Reverse-Traversal):                                        |
|    Skill liest Frontmatter `provenance_chain` + `derived_from` und       |
|    traversiert rueckwaerts Layer fuer Layer bis Layer=0 (Original-URL).  |
|    Mechanisch — kein LLM-Reasoning noetig. Tier=haiku reicht.            |
|                                                                           |
|  LIEST (Input):                                                           |
|    1. {target}          — Vault-Pfad, Code-Ref, AK-Ref, oder BL-ID       |
|    2. Frontmatter jedes traversierten Vault-Docs                         |
|                                                                           |
|  SCHREIBT (Output):                                                       |
|    1. Terminal: Markdown-Tabelle aller Hops bis Original-URL             |
|    2. (optional) Browser-Oeffnen bei --confirm + Layer-0-URL gefunden    |
|                                                                           |
|  INVARIANTEN:                                                             |
|    INV-ORIGIN-1: Traversal stoppt SPAETESTENS bei max-hops               |
|    INV-ORIGIN-2: Cycle-Detection — besuchte Pfade in Set, abort          |
|    INV-ORIGIN-3: Output ist Markdown-Tabelle (Pipe-Format)               |
|    INV-ORIGIN-4: --confirm oeffnet NUR Layer=0 role=original URL         |
|    INV-ORIGIN-5: Haiku-Worker reicht — keine LLM-Reasoning-Tiefe        |
+===========================================================================+
```

---

## Aufruf

| Parameter | Typ | Pflicht | Default | Beschreibung |
|---|---|---|---|---|
| `{target}` | string | ja | — | Artefakt-Referenz (siehe Target-Formate) |
| `--confirm` | flag | nein | false | Oeffnet Original-URL im Browser (nur bei Layer=0 gefunden) |
| `--max-hops` | int | nein | 10 | Maximale Traversal-Tiefe, Schutz vor langen Ketten |

---

## Target-Formate

| Format | Beispiel | Resolution |
|---|---|---|
| Vault-Pfad | `Backlog/BL-160-source-provenance-system.md` | direkt als Vault-Doc lesen |
| Code-Ref | `Code:./src/Service.cs:42` | grep XML-Doc-Comment nach BL-Ref, dann Vault-Doc |
| AK-Ref | `AK:BL-160:AK-3` | Liest Spec.md der BL-ID, sucht AK-3-Block, liest dessen provenance |
| BL-ID | `BL-160` | Liest BL-Item root-Markdown direkt |

---

## Workflow

```
1. Target-Resolution: {target} -> initial_doc_path
   - Vault-Pfad:  direkt verwenden
   - Code-Ref:    parse "Code:{path}:{line}", grep XML-Doc-Comment fuer BL-ID,
                  dann Vault-Doc aus BL-ID ableiten
   - AK-Ref:      parse "AK:{BL-ID}:{AK-N}", locate Spec.md unter
                  Backlog/{slug}/3_Spec/, lese provenance_chain
   - BL-ID:       glob "Backlog/{BL-ID}-*/" fuer slug, lade root .md

2. Frontmatter lesen: initial_doc.frontmatter.provenance_chain

3. Layer-Tabelle aufbauen (Startpunkt = aktueller Layer):
   hops = 0
   visited = Set()
   current = initial_doc_path

   WHILE hops < max_hops:
     IF current IN visited:
       EXIT 2 mit Cycle-Error (Cycle-Path drucken)
     visited.add(current)

     fm = read_frontmatter(current)
     append Tabellen-Zeile: Hop | Layer | Role | Artefakt | Timestamp | Source

     IF fm.layer == 0 OR fm.role == 'original':
       BREAK  # Original gefunden

     IF fm.derived_from ist leer:
       WARN "derived_from fehlt bei {current}, Kette bricht hier ab"
       BREAK

     current = fm.derived_from[0]  # primary parent
     hops += 1

4. Tabelle ausgeben (Markdown Pipe-Format)

5. IF --confirm AND letzter Layer hat role='original' AND source ist URL:
     Windows:  os.startfile(source_url)
     Linux:    subprocess.run(['xdg-open', source_url])
```

---

## Output-Format (Tabelle)

Beispiel fuer `Code:./src/SourceProvenanceService.cs:42`:

```
Hop | Layer | Role       | Artefakt                                                      | Timestamp  | Source
----+-------+------------+---------------------------------------------------------------+------------+------------------------------------
0   | 5     | code       | src/SourceProvenanceService.cs:42                             | 2026-05-17 | XML-Doc -> blueprint.md
1   | 4     | blueprint  | Backlog/BL-160-source-provenance-system/Implementation/blueprint.md | 2026-05-16 | Model.md + Spec.md
2   | 3     | model      | Backlog/BL-160-source-provenance-system/2_Model/BL-160_Model.md | 2026-05-15 | Spec.md
3   | 3     | spec       | Backlog/BL-160-source-provenance-system/3_Spec/BL-160_Spec.md | 2026-05-15 | Crumbs/findings_master.md
4   | 2     | finding    | Backlog/BL-160-source-provenance-system/Crumbs/findings_master.md | 2026-05-14 | _pileOfMud_snapshot/BL-160_RAW_2026-05-14.md
5   | 1     | snapshot   | Backlog/BL-160-source-provenance-system/Sources/_pileOfMud_snapshot/BL-160_RAW_2026-05-14.md | 2026-05-14 | pileOfMud/BL-160_RAW_2026-05-14.md
6   | 0     | original   | https://confluence.kluger.net/pages/viewpage.action?pageId=406159586 | 2026-05-08 | (Original)

Total: 7 Hops, Original-URL: https://confluence.kluger.net/pages/viewpage.action?pageId=406159586
Tipp: --confirm oeffnet Original-URL direkt im Browser.
```

---

## Implementation (Dispatch)

```python
# Pseudocode — Worker liest Frontmatter inline via Python-Subprocess
import sys, os, subprocess, yaml, re
from pathlib import Path

VAULT_ROOT = Path(os.environ.get("VAULT_ROOT", "."))

def resolve_target(target: str) -> Path | None:
    if target.startswith("Code:"):
        # Code:./src/Service.cs:42
        parts = target[5:].rsplit(":", 1)
        code_path = Path(parts[0])
        line = int(parts[1]) if len(parts) > 1 else None
        bl_id = grep_bl_id_from_xmldoc(code_path, line)
        return locate_bl_vault_doc(bl_id) if bl_id else None

    elif target.startswith("AK:"):
        # AK:BL-160:AK-3
        _, bl_id, ak_n = target.split(":", 2)
        slug = find_slug_for_bl_id(bl_id)
        return VAULT_ROOT / f"Backlog/{slug}/3_Spec/{bl_id}_Spec.md"

    elif re.match(r"^BL-\d+$", target):
        slug = find_slug_for_bl_id(target)
        return VAULT_ROOT / f"Backlog/{slug}/{target}.md" if slug else None

    else:
        # Direkt als Vault-Pfad
        p = VAULT_ROOT / target
        return p if p.exists() else None

def read_frontmatter(doc_path: Path) -> dict:
    content = doc_path.read_text(encoding="utf-8")
    if content.startswith("---"):
        end = content.index("---", 3)
        return yaml.safe_load(content[3:end]) or {}
    return {}

def reverse_lookup(target: str, max_hops: int = 10) -> list[dict]:
    initial = resolve_target(target)
    if initial is None:
        print(f"ERROR: target '{target}' nicht aufloesbar — siehe Format-Tabelle")
        sys.exit(2)

    rows = []
    visited = set()
    current = initial
    hop = 0

    while hop < max_hops:
        key = str(current)
        if key in visited:
            print(f"ERROR: Cycle erkannt bei {current}")
            print(f"Cycle-Path: {' -> '.join(list(visited)[-3:] + [key])}")
            sys.exit(2)
        visited.add(key)

        fm = read_frontmatter(current)
        if not fm:
            print(f"WARN: Kein Frontmatter bei {current}, Kette bricht hier ab")
            rows.append({"hop": hop, "layer": "?", "role": "unknown",
                         "artefakt": str(current), "timestamp": "?", "source": "MISSING"})
            break

        rows.append({
            "hop": hop,
            "layer": fm.get("layer", "?"),
            "role": fm.get("role", "?"),
            "artefakt": str(current),
            "timestamp": fm.get("created", "?"),
            "source": fm.get("source_provenance", {}).get("source_url", "?"),
        })

        layer = fm.get("layer", -1)
        if layer == 0 or fm.get("role") == "original":
            break  # Original erreicht

        derived_from = fm.get("derived_from", [])
        if not derived_from:
            print(f"WARN: derived_from leer bei {current}, kein Original gefunden")
            break

        current = VAULT_ROOT / derived_from[0]
        hop += 1
    else:
        print(f"WARN: max-hops={max_hops} erreicht, Tabelle bis hierhin")

    return rows

# Spawn via Worker
# Agent(general-haiku, description="Provenance-Traversal fuer /_origin",
#   prompt=f"Fuehre reverse_lookup('{target}', max_hops={max_hops}) aus.
#            Gib Ergebnis als Markdown-Pipe-Tabelle aus.")
```

---

## Fehlerbehandlung

| Fehler | Exit | Aktion |
|---|---|---|
| target nicht aufloesbar | 2 | Hinweis auf Format-Tabelle ausgeben |
| Frontmatter fehlt | WARN | Stop bei diesem Layer, Tabelle bis hierhin ausgeben |
| `derived_from` leer | WARN | Stop, kein Original gefunden — Kette unvollstaendig |
| Cycle erkannt | 2 | Cycle-Path drucken, abbrechen |
| max-hops erreicht | WARN | Tabelle bis hierhin ausgeben |
| --confirm ohne Layer=0 | INFO | Hinweis: Original-URL nicht gefunden, kein Browser-Oeffnen |

---

## INVARIANTEN

| ID | Invariante |
|---|---|
| INV-ORIGIN-1 | Traversal stoppt SPAETESTENS bei `max-hops` — kein infinite-loop moeglich |
| INV-ORIGIN-2 | Cycle-Detection: besuchte Pfade in Set; bei Re-Visit sofort EXIT 2 mit Cycle-Path |
| INV-ORIGIN-3 | Output ist Markdown-Tabelle (Pipe-Format), kompatibel mit Obsidian-Rendering + Terminal |
| INV-ORIGIN-4 | `--confirm` oeffnet NUR Layer=0 + role=original URL, nie einen Vault-Doc |
| INV-ORIGIN-5 | Tier=haiku reicht — kein LLM-Reasoning, nur Frontmatter-Traversal |

---

## Verwandte Commands

| Command | Erzeugt Layer |
|---|---|
| `/_w_user_story_extended {URL}` | Layer 0 -> 1 (Original-URL -> pileOfMud) |
| `/_backlog mode=intake` | Layer 1 -> 2 (pileOfMud -> Vault-Snapshot) |
| `/_A_orchestrate findingsExtraction` | Layer 2 -> 3 (Snapshot -> Findings) |
| `/_spec` | Layer 3 -> 3 (Findings -> Spec) |
| `/_model` | Layer 3 -> 3 (Spec -> Model) |
| `/_I_blueprintArchitect` | Layer 3 -> 4 (Model+Spec -> Blueprint) |
| `/_I_codeSystem` | Layer 4 -> 5 (Blueprint -> Code) |
| `propagate_provenance.py reverse` | Backend-Skript fuer Traversal (SB-3 AK-6) |
