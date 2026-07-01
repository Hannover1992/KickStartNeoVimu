"""
test_orchestrator_phase_registration.py — BL-362 Phase-Registrierungs-Completeness (RED zuerst).

Fängt die 7.7-Drift-Klasse strukturell: eine Phase mit Resume-Einstiegspunkt
(`IF resume_phase IN [..., "X"]:`) MUSS in der `resolve_resume_phase`-Whitelist UND
der Resume-Tabelle registriert sein — sonst startet ein Resume nach Crash from-scratch
(stiller Bug). Statisch, deterministisch, kein Live-Pipeline-Risiko.

Selbst-Validierung: läuft gegen die ECHTE _IDF_orchestrate.md und beweist, dass die
2026-06-15 registrierten Phasen TEST_SEARCH + PARALLEL_SUITABILITY jetzt vollständig sind.

Run aus Repo-Root:  py -3 -m pytest .claude/scripts/test_orchestrator_phase_registration.py -v
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import orchestrator_phase_registration as opr

COMMANDS = Path(__file__).parent.parent / "commands"
MODULE_PATH = str(Path(__file__).parent / "orchestrator_phase_registration.py")


# ─── resume_guard_phases: das X aus jedem `resume_phase IN [..., "X"]` ────────────
def test_resume_guard_phases_extracts_last_token():
    md = '''
IF resume_phase IN [null, "INIT"]:
  ...
IF resume_phase IN [null,..., "METRIC_PLAN"]:
  ...
IF resume_phase IN [null, ..., "TEST_SEARCH"]:
  ...
'''
    assert opr.resume_guard_phases(md) == {"INIT", "METRIC_PLAN", "TEST_SEARCH"}


# ─── whitelist_phases: Tokens aus dem resolve_resume_phase-Subroutine-Body ────────
def test_whitelist_phases_from_subroutine():
    md = '''
SUBROUTINE: resolve_resume_phase(idf_status):
  IF idf_status IN [null, "IDLE"]: RETURN null
  IF idf_status IN ["INIT","METRIC_PLAN","TEST_SEARCH"]:
    RETURN idf_status
  RETURN null
```
'''
    assert opr.whitelist_phases(md) == {"IDLE", "INIT", "METRIC_PLAN", "TEST_SEARCH"}


# ─── check_orchestrator: Gap erkannt / Vollständig sauber ────────────────────────
def test_check_detects_whitelist_gap():
    # FOO hat einen Resume-Guard, fehlt aber in der Whitelist UND Resume-Tabelle -> 7.7-Klasse
    md = '''
IF resume_phase IN [null, ..., "FOO"]:
  Skill(...)

SUBROUTINE: resolve_resume_phase(idf_status):
  IF idf_status IN [null, "IDLE"]: RETURN null
  IF idf_status IN ["INIT","BAR"]:
    RETURN idf_status
```

| `INIT` | Springe zu Phase 1 |
| `BAR` | Springe zu Phase 2 |
'''
    violations = opr.check_orchestrator(md)
    assert any("FOO" in v for v in violations)


def test_check_clean_when_registered():
    md = '''
IF resume_phase IN [null, ..., "INIT"]:
  Skill(...)
IF resume_phase IN [null, ..., "BAR"]:
  Skill(...)

SUBROUTINE: resolve_resume_phase(idf_status):
  IF idf_status IN [null, "IDLE"]: RETURN null
  IF idf_status IN ["INIT","BAR"]:
    RETURN idf_status
```

| `INIT` | Springe zu Phase 1 |
| `BAR` | Springe zu Phase 2 |
'''
    assert opr.check_orchestrator(md) == []


def test_check_detects_resume_table_gap():
    # BAZ in Whitelist + Guard, aber NICHT in Resume-Tabelle
    md = '''
IF resume_phase IN [null, ..., "BAZ"]:
  Skill(...)

SUBROUTINE: resolve_resume_phase(idf_status):
  IF idf_status IN [null, "IDLE"]: RETURN null
  IF idf_status IN ["BAZ"]:
    RETURN idf_status
```

| `INIT` | Springe zu Phase 1 |
'''
    violations = opr.check_orchestrator(md)
    assert any("BAZ" in v and "Resume-Tabelle" in v for v in violations)


# ─── SELBST-VALIDIERUNG: die ECHTE _IDF_orchestrate.md ist jetzt sauber ───────────
def test_real_idf_orchestrate_is_complete():
    idf = COMMANDS / "_IDF_orchestrate.md"
    assert idf.is_file(), f"nicht gefunden: {idf}"
    md = idf.read_text(encoding="utf-8")
    guards = opr.resume_guard_phases(md)
    # die 2026-06-15 registrierten Phasen MÜSSEN als Resume-Guards existieren ...
    assert "TEST_SEARCH" in guards
    assert "PARALLEL_SUITABILITY" in guards
    # ... und der Checker MUSS 0 Violations melden (Registrierung vollständig)
    violations = opr.check_orchestrator(md)
    assert violations == [], f"_IDF_orchestrate Registrierungs-Drift: {violations}"


# ─── CLI: Drift → exit 1 + DRIFT-Report; sauber → exit 0 ──────────────────────────
def test_cli_reports_drift_and_exits_nonzero(tmp_path):
    f = tmp_path / "orch.md"
    f.write_text(
        'IF resume_phase IN [null, ..., "FOO"]:\n  Skill(x)\n'
        'SUBROUTINE: resolve_resume_phase(idf_status):\n'
        '  IF idf_status IN ["INIT"]:\n    RETURN idf_status\n```\n'
        '| `INIT` | Springe zu Phase 1 |\n',
        encoding="utf-8")
    proc = subprocess.run([sys.executable, MODULE_PATH, str(f)],
                          capture_output=True, text=True)
    assert proc.returncode == 1, proc.stdout
    assert "DRIFT" in proc.stdout and "FOO" in proc.stdout


def test_cli_real_idf_orchestrate_exits_zero():
    proc = subprocess.run([sys.executable, MODULE_PATH, str(COMMANDS / "_IDF_orchestrate.md")],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout
    assert "[OK]" in proc.stdout


# ═══════════════════════════════════════════════════════════════════════════════
# INCREMENT-2: Resume-Mechanismus-Klassifikation (SDF/A/BDF generalisieren)
# ═══════════════════════════════════════════════════════════════════════════════
# Increment-1 meldete SDF/A/BDF still [N/A] (kein whitelist-Resume). Increment-2 macht
# den Checker mechanismus-bewusst. Marker gemessen 2026-06-15 gegen die echten
# Orchestratoren (messen-statt-glauben), darum sind die Assertions empirisch verankert.

# ─── detect_mechanisms: jedes Muster aus seinem Struktur-Marker ───────────────────
def test_detect_whitelist_mechanism():
    md = 'SUBROUTINE: resolve_resume_phase(idf_status):\n  IF idf_status IN ["INIT"]: RETURN idf_status\n'
    assert opr.detect_mechanisms(md) == {"whitelist"}


def test_detect_state_dispatch_mechanism():
    md = 'IF DF_BATCH_STATE existiert AND batch_status == "STARTED":\n  -> SCHRITT 1\n'
    assert opr.detect_mechanisms(md) == {"state_dispatch"}


def test_detect_factory_state_mechanism_eq_and_in():
    md = ('IF BDF_PIPELINE_STATE.bdf_status == "TEST_RUNNING":\n  ...\n'
          'IF BDF_PIPELINE_STATE.bdf_status IN ["SCANNING", "ITEM_DONE"]:\n  ...\n')
    assert opr.detect_mechanisms(md) == {"factory_state"}


def test_detect_idempotent_berater_mechanism():
    md = "**Resume:** Berater sind individuell idempotent (lesen eigenen Output)."
    assert opr.detect_mechanisms(md) == {"idempotent_berater"}


# ─── handled_states: robuste Dispatch-State-Extraktion (== und IN) ────────────────
def test_handled_states_state_dispatch():
    md = ('IF batch_status == "STARTED":\n ...\nELIF batch_status == "READY":\n ...\n'
          'ELIF batch_status == "DONE":\n ...\n')
    assert opr.handled_states(md) == {"STARTED", "READY", "DONE"}


def test_handled_states_factory_in_list():
    md = 'IF bdf_status IN ["SCANNING", "BATCH_PLANNING", "ITEM_RUNNING", "ITEM_DONE"]:\n ...\n'
    assert opr.handled_states(md) == {"SCANNING", "BATCH_PLANNING", "ITEM_RUNNING", "ITEM_DONE"}


# ─── Severity-Split: unclassified = WARN (exit 0), NICHT harte DRIFT ──────────────
# Der generische --resume-Marker ist zu breit fuer harte DRIFT (7 echte Orchestratoren
# mit legitimem state-Resume wuerden sonst False-DRIFT flaggen). Schwaches Signal -> warnings.
def test_classify_unclassified_is_warning_not_violation():
    md = "## RESUME\nBei --resume macht der Orchestrator etwas Undokumentiertes.\n"
    rep = opr.classify_and_check(md)
    assert rep["mechanisms"] == ["unclassified"]
    assert rep["violations"] == []                                  # KEINE harte DRIFT
    assert any("unklassifiziert" in w for w in rep["warnings"])     # nur WARN


# ─── HARTE DRIFT: resume_phase-Guards vorhanden, aber resolve_resume_phase fehlt ──
def test_classify_broken_whitelist_is_hard_violation():
    # whitelist-Intent (Guards) ohne Dispatch-Surface = Guards zeigen ins Leere.
    md = 'IF resume_phase IN [null, ..., "FOO"]:\n  Skill(x)\n# (Dispatch-Subroutine fehlt komplett)\n'
    rep = opr.classify_and_check(md)
    assert rep["mechanisms"] == ["whitelist_broken"]
    assert any("broken" in v and "FOO" in v for v in rep["violations"])
    assert rep["warnings"] == []


def test_classify_none_when_no_resume_markers():
    md = "# Ein Skill ohne jegliches Resume-Konzept.\nSkill(foo)\n"
    rep = opr.classify_and_check(md)
    assert rep["mechanisms"] == ["none"]
    assert rep["violations"] == []


# ─── Generalisierung NICHT IDF-hardcoded: whitelist-Check greift auf JEDEN Orch ───
def test_whitelist_check_applies_to_non_idf_orchestrator():
    # Hypothetischer Nicht-IDF-Orchestrator der whitelist-Resume ADOPTIERT, mit Gap:
    md = ('# _XYZ_orchestrate (hypothetisch)\n'
          'IF resume_phase IN [null, ..., "NEWPHASE"]:\n  Skill(x)\n'
          'SUBROUTINE: resolve_resume_phase(status):\n  IF status IN ["INIT"]: RETURN status\n```\n'
          '| `INIT` | Springe zu Phase 1 |\n')
    rep = opr.classify_and_check(md)
    assert "whitelist" in rep["mechanisms"]
    assert any("NEWPHASE" in v for v in rep["violations"])  # Gap auto-gefangen, nicht nur fuer IDF


# ─── SELBST-VALIDIERUNG: die 4 ECHTEN Orchestratoren, je 1 Mechanismus, 0 Violations ─
def test_real_idf_classified_whitelist_clean():
    md = (COMMANDS / "_IDF_orchestrate.md").read_text(encoding="utf-8")
    rep = opr.classify_and_check(md)
    assert rep["mechanisms"] == ["whitelist"]
    assert rep["violations"] == [], rep["violations"]


def test_real_sdf_classified_state_dispatch():
    md = (COMMANDS / "_SDF_orchestrate.md").read_text(encoding="utf-8")
    rep = opr.classify_and_check(md)
    assert rep["mechanisms"] == ["state_dispatch"]
    # SDF Phase-0 LITE-RESUME-GUARD dispatcht auf diese batch_status-Werte:
    assert {"STARTED", "READY", "DONE"} <= set(rep["handled_states"])
    assert rep["violations"] == [], rep["violations"]


def test_real_a_classified_idempotent_berater():
    md = (COMMANDS / "_A_orchestrate.md").read_text(encoding="utf-8")
    rep = opr.classify_and_check(md)
    assert rep["mechanisms"] == ["idempotent_berater"]
    assert rep["violations"] == [], rep["violations"]


def test_real_bdf_classified_factory_state():
    md = (COMMANDS / "_BDF_orchestrate.md").read_text(encoding="utf-8")
    rep = opr.classify_and_check(md)
    assert rep["mechanisms"] == ["factory_state"]
    # BDF Resume-Detection dispatcht auf den bdf_status-Enum (Auszug):
    assert {"TEST_RUNNING", "SCANNING", "EMPTY", "DONE", "ABORTED"} <= set(rep["handled_states"])
    assert rep["violations"] == [], rep["violations"]


# ─── CLI: alle 4 echten Orchestratoren → exit 0, SDF/A/BDF als [CLASSIFIED] ────────
def test_cli_all_four_real_orchestrators_exit_zero():
    files = [str(COMMANDS / n) for n in
             ("_IDF_orchestrate.md", "_SDF_orchestrate.md", "_A_orchestrate.md", "_BDF_orchestrate.md")]
    proc = subprocess.run([sys.executable, MODULE_PATH, *files], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout
    assert "[OK]" in proc.stdout          # IDF whitelist
    assert "[CLASSIFIED]" in proc.stdout  # SDF/A/BDF nicht mehr still [N/A]
    assert "state_dispatch" in proc.stdout and "factory_state" in proc.stdout


# ─── CLI ueber ALLE Orchestratoren: 0 harte DRIFT (unclassified = WARN, exit 0) ───
# Verankert den Severity-Split gegen die echte Engine: das Wiren in den Sanity-Audit
# darf NICHT RED-on-first-run sein. Unbekannte-Mechanismus-Orchestratoren -> [WARN].
def test_cli_all_orchestrators_no_hard_drift():
    files = [str(p) for p in sorted(COMMANDS.glob("_*orchestrate.md"))]
    assert len(files) >= 20, f"erwartete viele Orchestratoren, fand {len(files)}"
    proc = subprocess.run([sys.executable, MODULE_PATH, *files], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout          # KEINE harte DRIFT auf der echten Engine
    assert "[WARN]" in proc.stdout                    # die unklassifizierten als WARN gesurfaced
    assert "[DRIFT]" not in proc.stdout               # aber NICHTS hart-rot
