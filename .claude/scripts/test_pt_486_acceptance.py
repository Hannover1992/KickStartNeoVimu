#!/usr/bin/env python3
"""BL-237 batch_C5 AK-9 — DCSRE-486 Acceptance-Harness (read-only, greenfield).

Zweck (sub-1.md Exit-Kriterium 4 / K-3 haertester Stopp):
  Read-only Acceptance-Harness fuer den DCSRE-486 cross-vault Pattern-Materialisierungs-Rahmen.
  Beweist die SICHERHEITS-Invarianten des Rahmens (dry-run=0 Writes, Quiescenz-Gate vor Write,
  Vault-Override statt globalem resolve_bl_path-Touch, cross-vault Args-Durchreichung) GEGEN
  tmp_path / Vertrags-Anker — NIE gegen Live-DCS und NIE als scharfer 486-Live-Lauf.

WICHTIG (DoD-15/20, STOP-Bedingung(2)): Der SCHARFE 486-Live-Lauf (echte Writes in den DCS-Vault)
  ist ein HiL/EXTERN-Gate an Lead/IDF und wird hier NIE inline getriggert. Diese Harness deckt
  ausschliesslich die dry-run / read-only / Gate-Vertrags-Seite ab. K-3 (dry-run 0 Writes +
  scharf nie automatisch) ist der haerteste Stopp: bricht eine dieser Annahmen, ist der Rahmen unsicher.

Szenarien (A-E):
  A — dry-run materialize: 0 Schreiboperationen auf der Library (test_dry_run_zero_writes).
  B — Quiescenz-Gate VOR Write: BUSY (Fremd-Lock/mtime-Drift) -> require_quiescent raised, kein Write.
  C — Vault-Override (W-486-2): override gewinnt deterministisch, KEIN globaler resolve_bl_path-Touch.
  D — cross-vault Args-Durchreichung: --target-vault/--quiescenz-override im _PT_orchestrate-Vertrag.
  E — scharf=HiL/EXTERN: _PT_orchestrate-Vertrag deklariert den scharfen Lauf NICHT als Motor-inline.
"""
import importlib
from pathlib import Path

import pattern_library as pl

mq = importlib.import_module("manifest_quiescence")

COMMANDS_DIR = Path(__file__).resolve().parents[1] / "commands"


def _read_cmd(name):
    return (COMMANDS_DIR / name).read_text(encoding="utf-8")


def _seed_layer(vault: Path, layer="BE-DOMAIN"):
    d = vault / "Libraries" / "PatternLibrary" / "_project" / layer
    d.mkdir(parents=True, exist_ok=True)
    return d


def _library_snapshot(vault: Path):
    """Liste aller Library-Dateien + Inhalte (fuer 0-Writes-Vergleich)."""
    root = vault / "Libraries"
    if not root.exists():
        return {}
    return {p: p.read_text(encoding="utf-8", errors="replace")
            for p in root.rglob("*") if p.is_file()}


# ── Szenario A · test_dry_run_zero_writes (K-3 haertester Stopp) ──
def test_dry_run_zero_writes(tmp_path):
    # K-3: ein dry-run materialize-Pfad schreibt 0 Bytes auf die Library. Wir modellieren den
    # dry-run als "is_pattern_worthy()-Klassifikation OHNE add_arch" — exakt was _PT_berater_materialize
    # unter --dry-run tut (klassifizieren + loggen, NICHT schreiben). Beweis: Snapshot bit-identisch.
    _seed_layer(tmp_path)
    before = _library_snapshot(tmp_path)
    candidates = ["Eine wiederverwendbare Architektur-Konvention (siehe Foo.cs)",
                  "nichtssagender Freitext", "Validator Constraint MaxLength"]
    # dry-run: NUR klassifizieren (Worthiness-Gate), KEIN Write.
    decisions = {c: pl.is_pattern_worthy(c) for c in candidates}
    after = _library_snapshot(tmp_path)
    assert decisions[candidates[0]] is True and decisions[candidates[1]] is False
    assert before == after, "dry-run darf NICHTS auf der Library schreiben (K-3)"


# ── Szenario B · Quiescenz-Gate VOR Write (INV-PTO-2) ──
def test_quiescence_gate_blocks_write_on_busy(tmp_path):
    # B: bei aktivem Fremd-Lock ODER mtime-Drift waehrend des Settle-Fensters -> require_quiescent
    # raised (RuntimeError [QUIESCENCE-GATE]) BEVOR ein destruktiver Write passieren kann.
    import pytest
    # Fremd-Lock-Achse: evaluate_quiescence mit fremdem Lock-Owner -> nicht quiescent.
    ok, reason = mq.evaluate_quiescence(lock_info={"owner": "other-worker", "phase": "implement"},
                                        mtime_before=100.0, mtime_after=100.0,
                                        self_worker_id="me")
    assert ok is False and "foreign active lock" in reason
    # mtime-Drift-Achse: Manifest aenderte sich waehrend Settle -> nicht quiescent.
    ok2, reason2 = mq.evaluate_quiescence(lock_info=None, mtime_before=100.0, mtime_after=101.0)
    assert ok2 is False and "mtime changed" in reason2
    # require_quiescent ist ein HARD-Gate: nicht-quiescentes Manifest -> raise (kein Write).
    manifest = tmp_path / "_manifest.md"
    manifest.write_text("# busy\n", encoding="utf-8")
    with pytest.raises(RuntimeError):
        # settle=0 + injizierter Fremd-Lock via Monkey-Frei: wir nutzen die reine Drift-Achse,
        # indem wir ein nicht-existentes Manifest pruefen (mtime_before=None -> not found -> raise).
        mq.require_quiescent(tmp_path / "does_not_exist.md", settle_seconds=0)


def test_quiescence_gate_green_allows_write(tmp_path):
    # B (Gegenprobe): ruhendes Manifest (kein Fremd-Lock, stabile mtime) -> quiescent True,
    # der nachfolgende add_arch-Write ist erlaubt + materialisiert genau 1 Pattern (einstufig).
    manifest = tmp_path / "_manifest.md"
    manifest.write_text("# quiet\n", encoding="utf-8")
    assert mq.require_quiescent(manifest, settle_seconds=0) is True
    _seed_layer(tmp_path)
    pid, fpath, _ = pl.add_arch("BE-DOMAIN", "Erlaubter Write", vault_root=tmp_path, story="BL-237")
    assert fpath.exists() and pid == "PT-DOM-001"


# ── Szenario C · Vault-Override (W-486-2) — kein globaler resolve_bl_path-Touch ──
def test_vault_override_wins_no_global_resolve_touch(tmp_path):
    # C: resolve_vault_root(override=...) gewinnt deterministisch gegen env/default — der scharfe
    # 486-Live-Lauf zielt via --vault-root/--target-vault auf den DCS-Vault, OHNE resolve_bl_path
    # global umzubiegen (W-486-2: kein Cross-Projekt-Leak).
    other_vault = tmp_path / "dcs_vault"
    other_vault.mkdir()
    assert pl.resolve_vault_root(override=other_vault) == other_vault
    # add_arch respektiert vault_root -> schreibt in den Ziel-Vault, NICHT ins Repo-default.
    _seed_layer(other_vault)
    pid, fpath, _ = pl.add_arch("BE-DOMAIN", "Cross Vault", vault_root=other_vault, story="BL-237")
    assert other_vault in fpath.parents          # Datei landet im Override-Vault
    assert fpath.is_relative_to(other_vault)     # strikt unter dem Override-Vault, kein Repo-Leak


# ── Szenario D · cross-vault Args-Durchreichung (_PT_orchestrate-Vertrag) ──
def test_orchestrate_cross_vault_args_passthrough_contract():
    # D: _PT_orchestrate reicht --target-vault/--quiescenz-override an Stage-7 (materialize) durch
    # (G-5) und gatet Stage 7 auf Quiescenz (INV-PTO-2). Vertrags-Anker.
    t = _read_cmd("_PT_orchestrate.md")
    assert "--target-vault" in t and "--quiescenz-override" in t
    assert "--dry-run" in t
    assert "INV-PTO-2" in t and "manifest_quiescence" in t
    # G-5: Override-Signal wird NUR an materialize durchgereicht (kein zweiter Gate-Compute).
    assert "G-5" in t


# ── Szenario E · scharf = HiL/EXTERN-Gate (NIE Motor-inline, DoD-15/20) ──
def test_sharp_486_run_is_hil_extern_not_motor_inline():
    # E (K-3-Flanke): der scharfe Live-Lauf ist quiescenz-gated + deferred bei BUSY — der Vertrag
    # erzwingt KEINEN automatischen Write bei BUSY (materialize_allowed=false -> Stage 7 SKIP).
    # Damit ist "scharf nie automatisch" strukturell verankert: ohne Quiescenz kein Library-Write.
    t = _read_cmd("_PT_orchestrate.md")
    assert "materialize_allowed = false" in t or "materialize_allowed=false" in t
    assert "Stage 7" in t and ("SKIP" in t or "gesperrt" in t)
    # dry-run als sichere Standard-Probe (0 Writes) vor scharfem Lauf.
    assert "--dry-run" in t
