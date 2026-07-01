#!/usr/bin/env python3
"""stage_slice_migrate.py — BL-392 batch_3 (AK-MIGRATION): read-only/dry-run Monolith->8-Slice-Migrator.

Schwester von stage_slice_schema.py (batch_1, Validator) + resolve_vault_stage.py
(batch_2, Resolver). Dieses Modul ist der MIGRATIONS-MECHANISMUS: es zerlegt einen
monolithischen `stage_N.md` (1 Datei, alle YAML-Bloecke in einem Frontmatter) in die
8 atomaren Slices (`stage_slice_schema.CANONICAL_SLICES`) — dieselbe Atomisierungs-
Doktrin wie die Truth-Migration (BL-309), jetzt aufs Stage-Doc.

KERN-GARANTIE — VERLUSTFREI (Round-Trip, der DoD-Kern wie die Truth-Migration):
  Die Feld-Verteilung ist TOTAL: JEDES Frontmatter-Feld der IST-stage_N.md landet in
  GENAU EINEM Slice (kein Concern verloren, kein Concern doppelt). Bekannte Felder
  folgen CONCERN_FIELD_MAP (Spiegel der resolve_vault_stage-Legacy-View-Verteilung,
  damit Resolver + Migrator nie auseinanderlaufen); jedes UNGEMAPPTE Feld faellt
  deterministisch in den `_index`-Identitaets-Slice (Catch-All) — so kann kein Feld
  still verschwinden (staerker als eine feste Liste). Die Round-Trip-Eigenschaft ist
  test-erzwungen (test_stage_slice_migrate.py).

skip-SENTINEL (W-SLICE-3, explizit > implizit):
  Hat eine Stage einen Concern implizit-leer gelassen (z.B. stage_1: `setup.commands: []`,
  `health_check: null`), ergaenzt der Migrator das EXPLIZITE `skip: true` im jeweiligen
  Slice — der Monolith-Wert bleibt erhalten (Round-Trip), das skip macht "bewusst nicht
  da" maschinell unterscheidbar von "vergessen" (stage_slice_schema-konform).

stage_3 MECHANISMUS-KORREKTUR (W-DOM-2, der zweite Ur-Defekt — PL-2-Inhalt):
  Die IST-stage_3.md beschreibt einen FIKTIVEN `docker-compose ... up/down`-Mechanismus
  (die `docker-compose.integration.yml` existiert im Projekt NICHT). Der Migrator ersetzt
  fuer die Integration-Stage die setup/teardown/health_check-Slices durch den ECHTEN
  Mechanismus (STAGE3_MECHANISM_CORRECTION, Korrektur-Sicherung aus dem BL-392-Body):
  FluentDocker pro Test-Instanz / ContainerIntegrationTestBase / DockerSemaphore(4) /
  RunInitialMigrations() zur Laufzeit / in-process WebApplicationTestFactory / Health-Gate
  "Docker-Daemon erreichbar" (`docker version`). Merksatz: Code -> recompile. Image -> rmi + rebuild.
  Das ist projekt-spezifischer Slice-INHALT (PL-2), als benannte Korrektur-Konstante
  gefuehrt — die GENERISCHE Split-Mechanik (PL-1) bleibt davon unberuehrt.

LIVE CUTOVER (quiescenz-gated OWNER-Schritt, [[feedback_no_concurrent_manifest_edit]], BL-419):
  `cutover_to_vault(...)` plant bei `dry_run=True` (Default) nur die Zielpfade (kein Write).
  Bei `dry_run=False` schreibt es die 8 Slices in den LIVE-DCS-Vault
  (`{VAULT}/Stage/stage_N_<name>/`) UNTER dem Factory-Global-Lock (D-W5): der Lock wird VOR
  jeglichem Slice-Write erworben (Single-Writer) und im `finally` (auch bei Exception)
  owner-gated freigegeben. Scheitert der Lock-Erwerb, wird NICHTS geschrieben und das
  Scheitern signalisiert. Das spiegelt PHASE-B der Truth-Migration — der Write erfordert
  verifizierte Quiescenz/Lock auf dem LIVE-Vault.

read-only: dieses Modul liest Monolith-Text (als String uebergeben) und mutiert
keinen Vault/State. projekt-agnostisch bis auf die benannte stage_3-Korrektur-Konstante
(PL-2-Inhalt, klar als solche markiert).

Exit codes (CLI, dry-run-Vorschau):
  0 = Migration konform (Round-Trip verlustfrei + Schema-PASS)
  2 = Defekt (Schema-BLOCK auf dem migrierten Satz)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

import yaml

# Factory-Global-Lock-Fassade (D-W5, BL-419 AK-QUIESCENZ) — NUR konsumieren, nicht aendern.
import factory_lock

# Single source der 8 Slices + des Schemas (batch_1) — Migrator + Validator laufen nie auseinander.
from stage_slice_schema import CANONICAL_SLICES, validate_slice_dict

# ---------------------------------------------------------------------------
# Feld -> Slice-Verteilung (TOTAL, Catch-All -> _index)
# ---------------------------------------------------------------------------
#
# Spiegel der resolve_vault_stage-Legacy-View-Verteilung (_LEGACY_SCALAR_FIELDS +
# _LEGACY_NESTED_SLICES), erweitert um die real in den 6 Monolithen vorkommenden
# Zusatzfelder (das_gold/status/ueberlappung_strategie/feature_override/...), damit
# die Verteilung TOTAL ist. Reihenfolge = Lese-Reihenfolge je Slice.
#
# WICHTIG (verlustfrei): die geschachtelten Concerns setup/teardown/health_check
# liegen im Monolith bereits unter EINEM gleichnamigen Key (value = nested dict);
# der jeweilige Slice fuehrt also den Monolith-Key 1:1 (kein Auspacken -> kein
# Verlust, kein Re-Key). Skalar-Felder werden aus dem Top-Level uebernommen.

CONCERN_FIELD_MAP: dict[str, tuple[str, ...]] = {
    "_index": (
        # Identitaet + Catch-All. Alle Felder, die nicht klar einem Lifecycle-/
        # Deklarations-Concern gehoeren, landen hier (Identitaets-Anker).
        "stufe",
        "name",
        "fokus",
        "blueprint_perspektive",
        "kanarienvogel_zone",
        "kanarienvogel_bootstrap",
        "feature_override",
        "status",
        "das_gold",
    ),
    "execute": (
        "testbefehl",
        "test_projekte",
        "testpfad",
        "fanout",
        "mocks_erlaubt",
        "testtyp",
    ),
    # Geschachtelte Lifecycle-Slices: im Monolith liegt der Concern als nested dict
    # unter EINEM gleichnamigen Key; der Slice-Frontmatter IST dieses Sub-dict
    # AUSGEPACKT (Spiegel resolve_vault_stage._legacy_slice_view: setup-Slice-View =
    # mono["setup"] direkt, mit commands/timeout_min/... auf Top-Level). Daher hier
    # KEINE Top-Level-Skalar-Felder, sondern Sonderbehandlung in slice_dict_frontmatter.
    "setup": (),
    "teardown": (),
    "health_check": (),
    "resources": (
        "infrastruktur",
        "ressourcen_constraints",
        "max_container_parallel",
        "container_isolation",
        "flaky_risiko",
        "db_zustand_setup_pflicht",
        "parallelitaet_max",      # stage_5/6: top-level (ausserhalb ressourcen_constraints)
        "ueberlappung_strategie",  # stage_2-spezifisch
    ),
    "concurrency_class": (
        "concurrency_class",
        "concurrency_depends_on",
        "concurrency_rationale",
    ),
    "exit_criteria": ("exit_criteria",),
}

# Das _index ist der Catch-All-Slice fuer ungemappte Felder (Identitaets-Anker).
CATCH_ALL_SLICE = "_index"

# Concern-Lead-Feld je geschachteltem Lifecycle-Slice (fuer die skip-Erkennung).
_NESTED_LEAD = {"setup": "commands", "teardown": "commands", "health_check": "command"}


# ---------------------------------------------------------------------------
# stage_3 Mechanismus-Korrektur (PL-2-Inhalt — projekt-spezifischer Slice-Text)
# ---------------------------------------------------------------------------
#
# Der ECHTE Integration-Mechanismus aus der BL-392-Korrektur-Sicherung. ERSETZT die
# fiktiven docker-compose-Strings in setup/teardown/health_check der Integration-Stage.
# Das ist projekt-spezifischer Vault-INHALT (PL-2), klar als benannte Korrektur gefuehrt;
# die generische Split-Mechanik (PL-1) bleibt unberuehrt.

STAGE3_MECHANISM_CORRECTION: dict[str, dict] = {
    "setup": {
        "mechanismus": "FluentDocker pro Test-Instanz (ContainerIntegrationTestBase, Ports ab 9001, DockerSemaphore(4))",
        "commands": [
            "dotnet build <TestProjekt>   # Fall 1 (C#-Code): In-Process-Host laedt neue DLLs",
        ],
        "migration": "RunInitialMigrations() zur LAUFZEIT -> neue Migration automatisch, kein Image-Rebuild noetig",
        "sut": "WebApplicationTestFactory IN-PROCESS (kein eigener Backend-Container)",
        "image_rebuild_hinweis": "Fall 2 (Image-Inhalt: DIC-MockServer / Database.Dockerfile / init.sql): docker rmi <image> + rebuild (sonst STALE Image)",
        "merksatz": "Code -> recompile. Image -> rmi + rebuild.",
        "timeout_min": 5,
        "idempotent": True,
    },
    "teardown": {
        "mechanismus": "Cleanup via Dispose / CleanupExistingContainers (PRO Test-Instanz, FluentDocker) — KEIN globales Compose-Down",
        "commands": [
            "ContainerIntegrationTestBase.Dispose()   # per-Instanz Container-Cleanup",
        ],
        "always_run": True,
        "timeout_min": 2,
    },
    "health_check": {
        "command": "docker version   # Health-Gate: nur 'Docker-Daemon erreichbar', KEIN fester Port",
        "gate": "Docker-Daemon erreichbar",
        "retries": 5,
        "interval_sec": 4,
    },
    # MERGE-Overlay (nicht voll-ersetzend): nur die concurrency_rationale-Prosa traegt
    # die docker-compose-Fiktion (geteilter compose / Port 5433) -> auf den echten
    # Mechanismus (per-Instanz FluentDocker + DockerSemaphore(4)-Budget) umschreiben.
    # `concurrency_class`/`concurrency_depends_on` (echte Werte) bleiben unberuehrt.
    "concurrency_class": {
        "concurrency_rationale": (
            "container_isolation=true + DockerSemaphore(4) -> mehrere Batches parallel MOEGLICH, "
            "aber nur unter Container-Budget; KEIN geteilter compose-Stack (per-Instanz FluentDocker, "
            "Ports ab 9001, Cleanup via Dispose). Scheduler koordiniert: parallel bis Cap, sonst Defer."
        ),
    },
}

# Concerns, deren Korrektur die bestehenden Slice-Felder MERGT (nur die genannten Keys
# ueberschreiben) statt den Slice voll zu ersetzen. Die Lifecycle-Slices werden voll
# ersetzt (ihre Fiktion steckt in denselben Keys commands/command); concurrency_class
# wird nur teil-ueberschrieben (echte class/depends_on bleiben).
_MERGE_OVERLAY_CONCERNS = ("concurrency_class",)

# Erkennungs-Heuristik fuer die Integration-Stage (projekt-agnostisch): die Stage
# beschreibt den docker-compose-Fiktiv-Mechanismus UND ist testtyp=integration.
# So bleibt die Korrektur auf genau den defekten Slice-Satz beschraenkt, ohne eine
# Stage-Nummer hartzucodieren.
_DOCKER_COMPOSE_MARKER = "docker-compose"


# ---------------------------------------------------------------------------
# Frontmatter-Parsing (Spiegel stage_slice_schema/tdd_stages_ready)
# ---------------------------------------------------------------------------


def _parse_frontmatter_text(text: str) -> dict:
    """Lies das YAML-Frontmatter (zwischen den ersten zwei '---') aus einem Monolith-Text.

    Leerer/fehlender Frontmatter-Block -> {} (fail-safe). utf-8-tolerant (der Aufrufer
    liest die Datei mit errors='replace').
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fm_lines: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        fm_lines.append(line)
    try:
        data = yaml.safe_load("\n".join(fm_lines))
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def monolith_fields(monolith_text: str) -> dict:
    """Die geparsten Frontmatter-Felder des Monolithen (Round-Trip-Referenz)."""
    return _parse_frontmatter_text(monolith_text)


# ---------------------------------------------------------------------------
# Slice-Selektion (Feld -> Slice), TOTAL via Catch-All
# ---------------------------------------------------------------------------


def _slice_for_field(field_name: str) -> str:
    """Der Slice, in den ein Monolith-Feld gehoert. Ungemappt -> Catch-All (_index)."""
    for slice_name, fields in CONCERN_FIELD_MAP.items():
        if field_name in fields:
            return slice_name
    return CATCH_ALL_SLICE


def _is_implicitly_empty_nested(concern: str, value: object) -> bool:
    """True gdw. ein geschachtelter Lifecycle-Concern implizit-leer ist (skip-Bedarf).

    Implizit-leer = der Monolith liess den Concern faktisch weg, ohne explizites skip:
      - health_check: null (Top-Level None) ODER {command: null/leer}.
      - setup/teardown: {commands: []} (leere Befehlsliste) ODER {} ODER None.
    Ein gefuellter Concern (echte commands / echtes command) ist NICHT leer.
    """
    if value is None:
        return True
    if not isinstance(value, dict):
        return False
    if not value:
        return True
    lead = _NESTED_LEAD[concern]
    lead_val = value.get(lead)
    if lead_val is None:
        return True
    if isinstance(lead_val, (list, str)) and len(lead_val) == 0:
        return True
    return False


def _normalize_resources_for_schema(resources_fm: dict) -> None:
    """Ergaenze `infrastruktur: none` explizit, wenn der Monolith keines trug (in-place).

    Nicht-Infra-Stages (stage_1/2) haben kein `infrastruktur`-Feld -> der Monolith meinte
    implizit none (tdd_stages_ready-Default). Die Migration macht das EXPLIZIT, damit der
    resources-Deklarations-Slice schema-konform ist (Concern-Lead vorhanden, W-SLICE-3).
    Vorhandenes `infrastruktur` (stage_3/4/6) bleibt unberuehrt.
    """
    if "infrastruktur" not in resources_fm:
        resources_fm["infrastruktur"] = "none"


def _normalize_exit_criteria_for_schema(exit_fm: dict) -> None:
    """Leite das Schema-Concern-Lead `qg` aus der exit_criteria-Liste ab (in-place).

    Der Monolith fuehrt `exit_criteria` als Liste von 1-Key-dicts
    (`[{blueprint_qg: pass}, {stufen_tests_gruen: ja}, ...]`). Das Schema (batch_1)
    erwartet das Concern-Lead `qg`. Die Original-Liste bleibt 1:1 (Round-Trip); `qg`
    wird aus dem `blueprint_qg`-Eintrag der Liste gespiegelt (faithful surface, kein
    Werteverlust). Fehlt ein blueprint_qg-Eintrag, faellt `qg` auf "pass" (Abnahme-Default).
    """
    if "qg" in exit_fm:
        return
    criteria = exit_fm.get("exit_criteria")
    qg_value = "pass"
    if isinstance(criteria, list):
        for entry in criteria:
            if isinstance(entry, dict) and "blueprint_qg" in entry:
                qg_value = entry["blueprint_qg"]
                break
    exit_fm["qg"] = qg_value


# ---------------------------------------------------------------------------
# _index-Anreicherung (BL-392 batch_4 / AK-INDEX): slice_map + maintainability-Slot
# ---------------------------------------------------------------------------
#
# Der migrierte `_index`-Slice traegt zusaetzlich (Spiegel von stage_index_schema,
# batch_4): die `slice_map` (concern -> Slice-Dateiname; bewusst weggelassener Concern
# -> `skip`, W-SLICE-3) + den reservierten `maintainability`-Slot. maintainability-
# FORMAT ist OFFEN (W-AK-MAINT, Spec Sec 5): Boolean? Sub-Stage (`stage_3.1`)? — die
# Migration ERFINDET es NICHT, sondern reserviert den Slot als None (PRAESENZ genuegt
# dem Schema). Die Map wird aus den PRODUZIERTEN Slice-dicts abgeleitet (ein Slice mit
# nur einem skip/none-Sentinel zaehlt als bewusst weggelassen -> "skip" in der Map).

# Reservierter maintainability-Slot — None = Slot da, Wert offen (W-AK-MAINT).
INDEX_MAINTAINABILITY_DEFAULT: object = None


def _produced_slice_is_skip(slice_name: str, fm: dict) -> bool:
    """True gdw. ein produziertes Slice-dict NUR ein skip/none-Sentinel traegt (bewusst weggelassen).

    Genutzt fuer die slice_map-Ableitung: ein Lifecycle-Slice, der bei der Migration zum
    expliziten skip normalisiert wurde (implizit-leer im Monolith), wird in der Map als
    `skip` gefuehrt — nicht als Datei-Eintrag (explizit > implizit, W-SLICE-3).
    """
    if not isinstance(fm, dict) or not fm:
        return False
    for sentinel in ("skip", "none"):
        if fm.get(sentinel) in (True, "skip", "none", "true"):
            # Nur als skip werten, wenn der Slice keine echten Concern-Daten traegt.
            real_keys = {k for k in fm if k not in ("skip", "none")}
            return not real_keys
    return False


def _index_slice_map_from_slices(slices: dict[str, dict]) -> dict[str, str]:
    """Leite die `slice_map` (concern -> Dateiname | 'skip') aus den produzierten Slice-dicts ab.

    Jeder kanonische Slice bekommt seinen Dateinamen `{slice}.md`; ein Slice, der nur ein
    skip/none-Sentinel traegt (implizit-leerer Concern, zum skip normalisiert), wird als
    `skip` gefuehrt. So ist die Map per Konstruktion konsistent mit dem spaeteren Cutover-
    Verzeichnis (stage_index_schema.check_index_slice_map gibt consistent=True), denn der
    Cutover schreibt fuer skip-Concerns weiterhin eine Datei — der skip-Eintrag in der Map
    bleibt aber valide (skip-aware Konsistenz erlaubt Datei ODER skip-Markierung).
    """
    smap: dict[str, str] = {}
    for name in CANONICAL_SLICES:
        if _produced_slice_is_skip(name, slices.get(name, {})):
            smap[name] = "skip"
        else:
            smap[name] = f"{name}.md"
    return smap


def _enrich_index_slice(slices: dict[str, dict]) -> None:
    """Ergaenze den `_index`-Slice (in-place) um slice_map + maintainability-Slot (AK-INDEX).

    Additiv + verlustfrei: weder ueberschreibt es vorhandene Monolith-Felder im _index
    (stufe/name/...), noch erfindet es einen maintainability-WERT (Slot=None, W-AK-MAINT
    offen). Setzt slice_map/maintainability nur, wenn nicht schon vorhanden.
    """
    index_fm = slices["_index"]
    index_fm.setdefault("maintainability", INDEX_MAINTAINABILITY_DEFAULT)
    index_fm.setdefault("slice_map", _index_slice_map_from_slices(slices))


# ---------------------------------------------------------------------------
# Kern: Monolith -> 8 Slice-Frontmatter-dicts (verlustfrei + skip + stage_3-Korrektur)
# ---------------------------------------------------------------------------


def slice_dict_frontmatter(
    monolith_text: str,
    corrections: Optional[dict[str, dict]] = None,
) -> dict[str, dict]:
    """Zerlege den Monolith in die 8 Slice-Frontmatter-dicts (concern -> fm-dict).

    Verlustfreie TOTAL-Verteilung: jedes Monolith-Feld landet in genau einem Slice
    (CONCERN_FIELD_MAP; ungemappt -> _index-Catch-All). Geschachtelte Lifecycle-
    Concerns (setup/teardown/health_check) werden AUSGEPACKT: der Slice-Frontmatter
    IST das innere Sub-dict (commands/timeout_min/... auf Top-Level — Spiegel von
    resolve_vault_stage._legacy_slice_view, damit Resolver + Migrator deckungsgleich
    sind). Der Round-Trip re-wrappt sie unter ihren Concern-Key zurueck.

    skip-Sentinel (W-SLICE-3): ein implizit-leerer Lifecycle-Concern (z.B.
    `health_check: null`, `setup.commands: []`) bekommt zusaetzlich `skip: true` —
    das macht "bewusst nicht da" explizit unterscheidbar von "vergessen".

    stage_3-Korrektur: ist `corrections` gesetzt (default: Auto-Detect der docker-compose-
    Fiktiv-Integration-Stage), ERSETZEN die Korrektur-dicts die betroffenen Lifecycle-
    Slices durch den echten Mechanismus.
    """
    mono = _parse_frontmatter_text(monolith_text)

    # Auto-Detect: docker-compose-Fiktion in einer Integration-Stage -> stage_3-Korrektur.
    if corrections is None and _needs_stage3_correction(monolith_text, mono):
        corrections = STAGE3_MECHANISM_CORRECTION

    slices: dict[str, dict] = {name: {} for name in CANONICAL_SLICES}

    # Skalar-/Listen-Felder: Top-Level-Verteilung ueber CONCERN_FIELD_MAP (Catch-All _index).
    # Die geschachtelten Lifecycle-Concerns (setup/teardown/health_check) sind in der Map
    # leer -> sie werden hier NICHT verteilt, sondern unten ausgepackt.
    nested = set(_NESTED_LEAD)  # {"setup", "teardown", "health_check"}
    for field_name, value in mono.items():
        if field_name in nested:
            continue  # Sonderbehandlung (Auspacken) unten.
        slice_name = _slice_for_field(field_name)
        slices[slice_name][field_name] = value

    # Geschachtelte Lifecycle-Concerns AUSPACKEN: der Slice-Frontmatter IST das innere
    # Sub-dict (Spiegel resolve_vault_stage._legacy_slice_view) — commands/timeout_min/...
    # auf Top-Level. Implizit-leerer Concern -> explizites skip-Sentinel (W-SLICE-3).
    for concern in ("setup", "teardown", "health_check"):
        nested_val = mono.get(concern, None)
        if isinstance(nested_val, dict):
            slices[concern] = dict(nested_val)
        # health_check: null im Monolith -> leerer Slice (kommt unten ein skip).
        if _is_implicitly_empty_nested(concern, nested_val):
            slices[concern]["skip"] = True

    # Schema-Normalisierung (additiv, verlustfrei): die migrierten Slices muessen die
    # Concern-Lead-Felder tragen, die stage_slice_schema (batch_1) prueft. Der Monolith
    # liess sie z.T. implizit/anders-benannt — die Migration macht sie EXPLIZIT:
    #   - resources: kein `infrastruktur`-Key im Monolith (Nicht-Infra-Stage stage_1/2)
    #     -> `infrastruktur: none` explizit setzen (Spiegel der tdd_stages_ready-none-
    #     Default-Semantik; das Original bleibt unberuehrt, hier wird nur ergaenzt).
    #   - exit_criteria: der Monolith fuehrt eine LISTE unter `exit_criteria`; das Schema
    #     erwartet das Concern-Lead `qg`. Die Liste bleibt 1:1 erhalten (Round-Trip) +
    #     `qg` wird aus dem `blueprint_qg`-Eintrag der Liste abgeleitet (faithful surface).
    _normalize_resources_for_schema(slices["resources"])
    _normalize_exit_criteria_for_schema(slices["exit_criteria"])

    # stage_3-Mechanismus-Korrektur: Lifecycle-Slices voll ersetzen (Fiktion steckt in
    # denselben Keys), concurrency_class nur MERGE-ueberschreiben (echte class/depends_on
    # bleiben, nur die docker-compose-Rationale-Prosa wird ersetzt).
    if corrections:
        for concern, corrected_fm in corrections.items():
            if concern not in slices:
                continue
            if concern in _MERGE_OVERLAY_CONCERNS:
                slices[concern].update(dict(corrected_fm))
            else:
                slices[concern] = dict(corrected_fm)

    # _index-Anreicherung (BL-392 batch_4 / AK-INDEX): slice_map (concern -> Datei|skip)
    # + reservierter maintainability-Slot (None, Format OFFEN W-AK-MAINT). Additiv, NACH
    # der Korrektur (die slice_map spiegelt den finalen Slice-Satz, inkl. skip-normalisiert).
    _enrich_index_slice(slices)

    return slices


def _needs_stage3_correction(monolith_text: str, mono: dict) -> bool:
    """True gdw. der Monolith der docker-compose-Fiktiv-Integration-Stage entspricht.

    Projekt-agnostische Heuristik (KEINE Stage-Nummer hartcodiert): testtyp==integration
    UND der Text traegt den docker-compose-Marker (der Fiktiv-Defekt W-DOM-2). So wird
    GENAU die defekte Integration-Stage korrigiert, nicht die anderen docker-Stages
    (die einen anderen, hier nicht in Scope stehenden Mechanismus haben).
    """
    if str(mono.get("testtyp", "")).strip().lower() != "integration":
        return False
    return _DOCKER_COMPOSE_MARKER in monolith_text.lower()


# ---------------------------------------------------------------------------
# Kern: Monolith -> 8 Slice-MARKDOWN-Texte (Frontmatter + knappe Prosa)
# ---------------------------------------------------------------------------


def split_monolith_to_slices(
    monolith_text: str,
    corrections: Optional[dict[str, dict]] = None,
) -> dict[str, str]:
    """Zerlege einen Monolith-stage_N.md in {concern: slice_markdown_text}.

    Pro Slice ein BOM-freier, LF-normierter Markdown-String: YAML-Frontmatter
    (das Slice-fm aus slice_dict_frontmatter) + eine knappe Prosa-Ueberschrift.
    read-only/dry-run: schreibt NICHTS, liefert nur die Texte.
    """
    fm_dict = slice_dict_frontmatter(monolith_text, corrections=corrections)
    out: dict[str, str] = {}
    for name in CANONICAL_SLICES:
        out[name] = _render_slice_markdown(name, fm_dict[name])
    return out


def _render_slice_markdown(slice_name: str, fm: dict) -> str:
    """Rendere einen Slice als Markdown (Frontmatter + Prosa-Stub), BOM-frei/LF.

    Ein leeres fm wird als `{}`-Frontmatter (eine '--- / --- '-Klammer) gerendert; das
    bleibt schema-sichtbar (Empty-Slice -> der Validator faengt es, kein stiller Pass).
    """
    if fm:
        body = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True, default_flow_style=False)
    else:
        body = ""
    text = "---\n" + body + "---\n\n# " + slice_name + "\n"
    # LF-Normierung + BOM-Schutz (yaml liefert bereits LF; defensiv).
    return text.replace("\r\n", "\n").replace("\r", "\n").lstrip("﻿")


# ---------------------------------------------------------------------------
# LIVE CUTOVER — quiescenz-gated Owner-Write (Factory-Global-Lock, D-W5, BL-419)
# ---------------------------------------------------------------------------


def _resolve_target_dir(slices: dict[str, str], target_dir: Optional[Path]) -> Path:
    """Bestimme das Ziel-Verzeichnis fuer den Cutover.

    Expliziter `target_dir`-Override gewinnt (tmp-Steuerbarkeit, DoD-3c). Ohne Override
    wird der Pfad deterministisch aus (stufe, name) des `_index`-Slice abgeleitet:
    `{resolve_vault_root()}/Stage/stage_{N}_<name>/` (SSoT-Root, DoD-2d/3b).
    """
    if target_dir is not None:
        return Path(target_dir)
    # SSoT: resolve_vault_root (env CLAUDE_VAULT_ROOT primaer) ueber den Resolver.
    import resolve_vault_stage as rvs

    n, name = _stage_n_name_from_slices(slices)
    return rvs.resolve_vault_root() / "Stage" / f"stage_{n}_{name}"


def _stage_n_name_from_slices(slices: dict[str, str]) -> tuple[int, str]:
    """Lies (stufe, name) aus dem `_index`-Slice-Frontmatter (fuer die dirname-Ableitung)."""
    index_fm = _parse_frontmatter_text(slices.get(CATCH_ALL_SLICE, ""))
    return int(index_fm.get("stufe")), str(index_fm.get("name"))


def cutover_to_vault(
    slices: dict[str, str],
    target_dir: Optional[Path],
    dry_run: bool = True,
) -> dict[str, Path]:
    """Cutover der 8 Slices in einen Stage-Verzeichnis-Pfad (dry-run-Plan ODER LIVE-Write).

    `dry_run=True` (Default): schreibt NICHTS, liefert nur die geplanten Zielpfade
    (concern -> {dir}/{concern}.md) zur Transparenz.

    `dry_run=False` (quiescenz-gated OWNER-Pfad, BL-419): schreibt die Slices in den
    LIVE-Vault UNTER dem Factory-Global-Lock (D-W5):
      - acquire VOR jeglichem Slice-Write (Single-Writer, DoD-1a). Scheitert acquire
        (False/timeout), wird NICHTS geschrieben + ein RuntimeError signalisiert (DoD-1c).
      - mkdir + 8 {concern}.md byte-identisch (utf-8/LF/BOM-frei, DoD-2a/b); genau-1-Dir
        pro Nummer, Re-Run idempotent (DoD-2c).
      - release owner-gated (derselbe worker_id) im `finally` — auch bei Exception (DoD-1b/d).
    Rueckgabe == die dry_run-Plan-Map (Planung == Realitaet, DoD-2e).

    target_dir=None -> Ableitung `{resolve_vault_root()}/Stage/stage_{N}_<name>/` (DoD-2d/3b);
    expliziter target_dir gewinnt (DoD-3c).
    """
    resolved_dir = _resolve_target_dir(slices, target_dir)
    planned = {name: resolved_dir / f"{name}.md" for name in slices}
    if dry_run:
        return planned

    # Lock-Vault-Root: ohne target_dir-Override liegt der Lock unter demselben SSoT-Vault
    # wie der Write ({root}/Stage/stage_N_<name>/ -> root). Mit Override gilt der env-Root,
    # damit der Factory-Global-Lock nicht in einen stale Default-Pfad faellt.
    lock_vault_root = _lock_vault_root(resolved_dir, target_dir)

    # Lock-Verzeichnis muss existieren, bevor factory_lock den Lock-File atomar schreibt
    # (frischer Vault-Root: {root}/ gibt es ggf. noch nicht).
    if lock_vault_root is not None:
        try:
            Path(lock_vault_root).mkdir(parents=True, exist_ok=True)
        except OSError:
            pass

    worker_id = f"cutover-{os.getpid()}"
    acquired = factory_lock.acquire(worker_id=worker_id, vault_root=lock_vault_root)
    if not acquired:
        raise RuntimeError(
            f"cutover_to_vault: Factory-Global-Lock-Erwerb fehlgeschlagen (worker_id={worker_id}); "
            "KEIN Slice-Write (quiescenz-gated Single-Writer, DoD-1c)."
        )
    try:
        resolved_dir.mkdir(parents=True, exist_ok=True)
        for name in slices:
            (resolved_dir / f"{name}.md").write_text(slices[name], encoding="utf-8", newline="\n")
    finally:
        factory_lock.release(worker_id, vault_root=lock_vault_root)
    return planned


def _lock_vault_root(resolved_dir: Path, target_dir: Optional[Path]) -> Optional[Path]:
    """Der Vault-Root, unter dem der Factory-Global-Lock liegen soll.

    Ohne target_dir-Override ist es der SSoT-Vault-Root ({root}/Stage/stage_N_<name>/ ->
    der Grosselter-Pfad). Mit Override versuchen wir denselben SSoT-Root (resolve_vault_root),
    fallen aber fail-safe auf None (factory_lock-Default) zurueck, wenn keiner aufloesbar ist.
    """
    if target_dir is None:
        # resolved_dir == {root}/Stage/stage_N_<name>  -> root = parent.parent
        return resolved_dir.parent.parent
    try:
        import resolve_vault_stage as rvs

        return rvs.resolve_vault_root()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# CLI (dry-run-Vorschau: Migration eines Monolithen, Schema-Check, kein Write)
# ---------------------------------------------------------------------------


def main(argv: Optional[list[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Monolith->8-Slice-Migrator (BL-392 AK-MIGRATION, read-only/dry-run, KEIN Vault-Write)."
    )
    parser.add_argument("monolith", help="Pfad zu einer monolithischen stage_N.md (read-only)")
    parser.add_argument(
        "--show",
        metavar="SLICE",
        default=None,
        help=f"Einen Slice-Text ausgeben ({'/'.join(CANONICAL_SLICES)})",
    )
    args = parser.parse_args(argv)

    path = Path(args.monolith)
    if not path.exists():
        print(f"NOT_FOUND: {path}", file=sys.stderr)
        return 2
    text = path.read_text(encoding="utf-8", errors="replace")

    fm_dict = slice_dict_frontmatter(text)
    res = validate_slice_dict(fm_dict)

    if args.show is not None:
        out = split_monolith_to_slices(text)
        if args.show not in out:
            print(f"NOT_A_SLICE: {args.show}", file=sys.stderr)
            return 2
        print(out[args.show])
        return 0 if res.valid else 2

    if res.valid:
        print(f"MIGRATE: PASS ({path.name} -> 8 Slices, Schema konform, verlustfrei dry-run)")
        return 0
    print(f"MIGRATE: BLOCK ({path.name})")
    for name in res.missing_slices:
        print(f"  [MISSING] {name}")
    for err in res.errors:
        print(f"  [BLOCK] {err.slice} — {err.message}")
    return 2


if __name__ == "__main__":
    # Windows-stdout default cp1252 -> Umlaute crashen. utf-8 erzwingen, fail-safe.
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    sys.exit(main(sys.argv[1:]))
