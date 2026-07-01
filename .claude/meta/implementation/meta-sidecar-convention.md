# meta-sidecar-convention.md — Meta-Sidecar-Runtime-Konvention (BL-372)

**Status:** Engine-Kanon (projekt-AGNOSTISCH). Via `/_redeploy --infra` (PROCESS_FILES) in alle Projekte gespreizt — ueberall identisch.
**Zweck:** Trennt den projekt-AGNOSTISCHEN Command (Engine) vom projekt-SPEZIFISCHEN Inhalt (Vault) als RUNTIME-Lade-Konvention.
**Quelle:** BL-372 (A-Pipeline 2026-06-16, REIF). Schwester: BL-302 (domain-keyed). Generalisiert [[feedback_command_layer_purity]] (BL-NEW-58) von Deploy-Zeit zu Runtime.

---

## Die Konvention in einem Satz

Jeder Command VERSUCHT beim Lauf IMMER, seinen projekt-spezifischen Meta-Sidecar
`{vault_root}/_meta/commands/{commandName}_Meta.md` zu laden. Existiert er → projekt-Metadaten greifen.
Fehlt er → generischer Placeholder, der Command laeuft generisch weiter (kein Crash). So bleibt das
Command-File selbst projekt-AGNOSTISCH (0 projekt-spezifischer Inhalt) und ist trotzdem pro Projekt
anreicherbar.

---

## 1. Pfad-Kanon (AK-1)

- **Kanon:** `{vault_root}/_meta/commands/{commandName}_Meta.md`. Genau EIN Sidecar pro Command, 1:1
  Namens-Mapping zum Command-File (`_goal_backlog` → `_goal_backlog_Meta.md`).
- **Heimat = VAULT** (projekt-spezifisch, T9), NICHT das Engine-Repo.
- **`vault_root`-Aufloesung MEHRSTUFIG** (NICHT `.vault_root`-only): env `CLAUDE_VAULT_ROOT` →
  `.claude/.vault_root` (walk-up) → Default; via `resolve_vault_root()` (`.claude/scripts/resolve_vault_meta.py`).

## 2. Der gemeinsame `_meta/`-Wurzelkanon (AK-8 — BL-302-Koordination)

- `{vault_root}/_meta/` ist der GEMEINSAME Vault-Meta-Wurzelkanon fuer ZWEI Granularitaeten:
  - **command-keyed:** `_meta/commands/{name}_Meta.md` (BL-372)
  - **domain-keyed:** `_meta/{domain}/…` (BL-302)
- **WARUM `_meta/` (mit Unterstrich) statt `meta/`:** `meta/` (ohne `_`) kollidiert namentlich mit der
  DEPLOYTEN Engine-`.claude/meta/`-Semantik (Schicht-1: `meta/a, meta/sdf, meta/sc, meta/pr`). `_meta/` ist
  BL-302-konform + kollisionsfrei.
- **BL-372 DEFINIERT** diesen Kanon; **BL-302 (DRAFT) ERBT ihn** — Cross-Ref, KEINE Block-Dependency.
  Bei BL-302-Bau: Konsistenz-Check gegen diesen Kanon (kein divergentes `DCS\Template\`-Layout).

## 3. Always-Try-Load (AK-2)

- Jeder Command VERSUCHT IMMER **bedingungslos** den Sidecar zu laden — NICHT "falls vorhanden pruefen und
  dann skippen". Eine fehlende Datei ist **KEIN Fehler** (kein if-exists-skip, kein Crash).
- Markdown-Skill-Commands: eine PROMPT-Konvention im Command-Doc ("lies
  `{vault_root}/_meta/commands/{name}_Meta.md`, falls vorhanden"). Script-Commands: optional via
  `resolve_command_sidecar()` (§9).
- Exakt das `resolve_meta`-Verhalten: erster Treffer gewinnt, am Ende `return None`.

## 4. Placeholder / Hello-World-Fallback (AK-3)

- Sidecar fehlt → generischer Placeholder/Default greift, Command laeuft generisch weiter (kein Crash).
- Bei Markdown-Commands ist der Fallback eine PROMPT-Konvention ("WENN kein Sidecar, fahre generisch fort"),
  NICHT zwingend ein Code-Return-Wert. `resolve_command_sidecar()` liefert `None`; die `None`-Behandlung als
  generischer Lauf IST die Konvention im Command-Doc (SA-2, [[feedback_markdown_engine_bootstrap]]).

## 5. Runtime-Purity — HARTE Regel (AK-4)

- Das Command-File darf **KEINEN projekt-spezifischen Inhalt** mehr tragen. Projekt-Spezifisches
  (Roadmaps, Routing-Maps, projekt-Templates) wandert in den Sidecar.
- Generalisiert die 3-Schichten-Purity ([[feedback_command_layer_purity]], BL-NEW-58) von einer
  DEPLOY-ZEIT-Regel zu einer RUNTIME-Lade-Konvention.
- **★ Framing:** das ist eine SCHUTZ-Konvention ("DAMIT projekt-Inhalt NIE in den agnostischen Command
  leckt"), KEIN Reparatur-Patch fuer ein existierendes Leck. Stand 2026-06-16: die OmniCommand-230-Roadmap
  ist z.B. NICHT in `/_goal_backlog.md` (grep `BL-230|Gate-A|C2-RUN` = 0) → ARCHITEKT-2-PRAEVENTION.

## 6. Redeploy-Sicherheit (AK-5)

- Sidecars liegen unter `{vault_root}/_meta/` = ein vom `/_redeploy` NIE-angefasster Vault-Pfad
  (PROJEKT-INSTANZ-SPEZIFISCH, analog `wissen/ models/ analysis/`).
- `_meta/` ist EXPLIZIT in `_redeploy.md` Schicht-3 ("NIEMALS angefasst") eingetragen — die Unversehrtheit
  ist damit DEKLARIERT, nicht impliziert. Redeploy spreizt nur den agnostischen Command; der Sidecar bleibt
  pro Projekt erhalten.

## 7. Default-Stub-Deploy (AK-6)

- **Stub-if-absent:** ein STRIKT LEERER Placeholder-`_Meta.md`-Stub wird pro Command-Sidecar-Slot deployt —
  ABER nur-wenn-absent, idempotent (exakt das `pileOfMud/.gitignore`-Muster: "NUR die Huelle, NIE der Inhalt").
- Garantiert: ein bereits angereicherter Sidecar wird NIE ueberschrieben (**Kopplung AK-6↔AK-5**). Der Stub
  enthaelt NUR einen Placeholder-Header, NIE projekt-Inhalt → keine Contamination, Reinheit gewahrt.
- Die per-Command-Stub-Liste folgt dem AK-7-Sweep (welche Commands brauchen ueberhaupt einen Sidecar).

## 8. Command-Sweep — Methode + Filter (AK-7)

- **Methode (empirisch):** grep je Command-Doc nach projekt-spezifischem INHALT (BL-IDs, Projekt-Namen,
  Roadmap-Marker, hardcodierte Pfade/Routing).
- **★ Filter-Regel (Inhalt-vs-State — DIE Unterscheidung):** Sidecar NUR fuer projekt-spezifische
  META-**INHALTE** (Roadmaps, Routing-Maps, Templates — die ein Mensch/Projekt SCHREIBT und der Command LIEST).
  NICHT fuer generierbaren **STATE** (Indizes, Manifeste, Aggregate — die aus anderen Wahrheits-Dateien
  GENERIERT werden; die brauchen einen Generator, keinen Sidecar — z.B. BL-306-Index = generierte Sicht).
- **Kandidaten-Anker (zu VERIFIZIEREN, nicht bestaetigt):** `/_goal_backlog` (proaktiv: Roadmap KOENNTE
  dorthin), `/_help`-Routing, vault-routing-naher Inhalt.
- Die Sweep-DURCHFUEHRUNG (Kandidaten-Liste fuellen) ist Discovery-Arbeit (PL/IDF), NICHT Teil dieser Konvention.

## 9. Der Resolver-Adapter (AK-9)

- `resolve_command_sidecar(command_name)` in `.claude/scripts/resolve_vault_meta.py`: duenner Adapter auf
  `resolve_vault_root()` → `{vault_root}/_meta/commands/{name}_Meta.md` → `return Path if exists else None`.
- **OPTIONAL** — fuer Commands, die einen aufgeloesten Pfad-String brauchen. Der KERN ist die
  Markdown-Konvention (§3/§4), nicht dieser Helfer.

---

## Forward-Verify (AK-5/AK-6, DoD-11)

Das Redeploy-Verhalten (Sidecar bleibt beim Redeploy unangetastet; Stub-if-absent idempotent) ist NUR LIVE
beim naechsten `/_redeploy` beweisbar ([[feedback_forward_verification_pattern]]). Dormant Companion-
Verifikation beim naechsten Live-Redeploy: `_meta/`-Pfade NACHWEISBAR nicht ueberschrieben, Stub nur-wenn-absent.

## Verwandt

[[feedback_command_layer_purity]] (Deploy-Zeit-Basis) · BL-302 (domain-keyed `_meta/`) ·
`resolve_vault_meta.py` (Resolver-Fundament) · [[feedback_markdown_engine_bootstrap]] (Konvention > Code) ·
BL-306 (generierte Sicht, KEIN Sidecar-Konsument) · [[manifest-write-discipline]] (Engine-Kanon-Doc-Muster).
