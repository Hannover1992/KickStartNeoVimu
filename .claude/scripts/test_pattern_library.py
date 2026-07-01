#!/usr/bin/env python3
"""Tests fuer pattern_library.py (DCSRE-486 Pattern-Capture-Leak-Fix). Gegen tmp_path, nie Live-DCS."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pattern_library as pl

SCRIPT = Path(__file__).parent / "pattern_library.py"


def _seed_layer(vault: Path, layer="BE-DOMAIN", existing=None):
    d = vault / "Libraries" / "PatternLibrary" / "_project" / layer
    d.mkdir(parents=True, exist_ok=True)
    for pid_name in (existing or []):
        (d / f"{pid_name}.md").write_text("---\nid: x\n---\n", encoding="utf-8")
    return d


# ── next_id ──
def test_next_id_empty(tmp_path):
    _seed_layer(tmp_path)
    assert pl.next_id("BE-DOMAIN", vault_root=tmp_path) == "PT-DOM-001"


def test_next_id_increment(tmp_path):
    _seed_layer(tmp_path, existing=["PT-DOM-001_A", "PT-DOM-002_B", "PT-DOM-010_C"])
    assert pl.next_id("BE-DOMAIN", vault_root=tmp_path) == "PT-DOM-011"


def test_next_id_fe_layer(tmp_path):
    # FE-Layer behaelt seinen Namen im Short-Code
    _seed_layer(tmp_path, layer="FE-FORM")
    assert pl.next_id("FE-FORM", vault_root=tmp_path) == "PT-FE-FORM-001"


# ── add_arch (einstufige Materialisierung — der Leak-Fix) ──
def test_add_arch_materializes_file_and_index(tmp_path):
    _seed_layer(tmp_path)
    pid, fpath, dedup = pl.add_arch(
        "BE-DOMAIN", "Enum singular Display", description="Enums singular mit Display",
        tags=["enum", "convention"], sources=["Foo.cs"],
        pattern="- Regel X", beispiel="```cs\nenum A{}\n```", abgrenzung="- nicht Y",
        vault_root=tmp_path, story="DCSRE-1944",
    )
    assert pid == "PT-DOM-001"
    assert fpath.exists()
    content = fpath.read_text(encoding="utf-8")
    assert "id: PT-DOM-001" in content and "## Pattern" in content and "- Regel X" in content
    assert "added_via: /_pattern_add (DCSRE-1944)" in content
    # Index-Zeile materialisiert (nicht nur Kandidat)
    idx = (tmp_path / "Libraries/PatternLibrary/_project/BE-DOMAIN/_index.md").read_text(encoding="utf-8")
    assert "PT-DOM-001" in idx and "Enums singular mit Display" in idx


def test_add_arch_auto_increment(tmp_path):
    _seed_layer(tmp_path)
    p1, _, _ = pl.add_arch("BE-DOMAIN", "Erstes", vault_root=tmp_path)
    p2, _, _ = pl.add_arch("BE-DOMAIN", "Zweites", vault_root=tmp_path)
    assert p1 == "PT-DOM-001" and p2 == "PT-DOM-002"


def test_add_arch_dedup_warn(tmp_path):
    _seed_layer(tmp_path, existing=["PT-DOM-001_Enum_Singular_Display"])
    _pid, _fp, dedup = pl.add_arch("BE-DOMAIN", "Enum Singular Display", vault_root=tmp_path)
    assert dedup is not None and "Enum_Singular" in dedup


# ── add_semantic ──
def test_add_semantic_terms_append(tmp_path):
    f, entry = pl.add_semantic("BE-DOMAIN", "ZEVSP", "Cross-System-ID-Suffix",
                               target="terms", vault_root=tmp_path)
    assert f.name == "domain-terms.md"
    txt = f.read_text(encoding="utf-8")
    assert "**ZEVSP**" in txt and "Cross-System-ID-Suffix" in txt


def test_add_semantic_glossary(tmp_path):
    f, _ = pl.add_semantic("BE-DOMAIN", "QDVS", "Qualitaetsdarstellung", target="glossary", vault_root=tmp_path)
    assert f.name == "domain-glossary.md" and "_global" in str(f)


# ── find (Consult) ──
def test_find_patterns(tmp_path):
    _seed_layer(tmp_path)
    pl.add_arch("BE-DOMAIN", "Enum singular", description="Enums singular mit Display", vault_root=tmp_path)
    hits = pl.find_patterns("enum", vault_root=tmp_path)
    assert any("PT-DOM-001" in h for h in hits)


# ── CLI Smoke ──
def test_cli_add_arch(tmp_path):
    _seed_layer(tmp_path)
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "add", "--arch", "--layer", "BE-DOMAIN",
         "--name", "CLI Test", "--description", "via cli", "--vault-root", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert "PT-DOM-001" in r.stdout
    assert (tmp_path / "Libraries/PatternLibrary/_project/BE-DOMAIN/PT-DOM-001.md").exists()


# ══ Counter / Lifecycle (BL-237 AK-COUNTER-0/SCHEMA-0/MIG-0/V1) ══
def _seed_arch_pattern(tmp_path, layer="BE-DOMAIN", name="Test Pattern"):
    pid, path, _ = pl.add_arch(layer, name, description="d", vault_root=tmp_path)
    return pid, path


def test_add_arch_writes_counter_frontmatter(tmp_path):
    # AK-SCHEMA-0: volles Counter-Frontmatter ab Geburt
    _pid, path = _seed_arch_pattern(tmp_path)
    c = pl.read_counter(path)
    assert c["usage_count"] == 0 and c["broken_count"] == 0
    assert c["status"] == "experimental" and c["scope"] == "arch"
    assert c["boundary_notes"] == [] and c["variants"] == []


def test_lifecycle_pfad1_usage_increment_additiv(tmp_path):
    pid, path = _seed_arch_pattern(tmp_path)
    assert pl.lifecycle(pid, 1, scope="arch", vault_root=tmp_path)["usage_count"] == 1
    assert pl.lifecycle(pid, 1, scope="arch", vault_root=tmp_path)["usage_count"] == 2
    assert pl.read_counter(path)["usage_count"] == 2


def test_lifecycle_pfad1_status_upgrade_thresholds(tmp_path):
    # AK-VOCAB-0 Schwellen 5/10
    pid, path = _seed_arch_pattern(tmp_path)
    for _ in range(4):
        pl.lifecycle(pid, 1, scope="arch", vault_root=tmp_path)
    assert pl.read_counter(path)["status"] == "experimental"           # bei 4
    assert pl.lifecycle(pid, 1, scope="arch", vault_root=tmp_path)["status"] == "active"   # usage=5
    for _ in range(4):
        pl.lifecycle(pid, 1, scope="arch", vault_root=tmp_path)
    assert pl.read_counter(path)["status"] == "active"                 # bei 9
    assert pl.lifecycle(pid, 1, scope="arch", vault_root=tmp_path)["status"] == "PROVEN"   # usage=10


def test_lifecycle_pfad2_broken_and_boundary_append(tmp_path):
    pid, path = _seed_arch_pattern(tmp_path)
    r = pl.lifecycle(pid, 2, scope="arch", vault_root=tmp_path, broken_context="Foo.cs", broken_reason="passt nicht")
    assert r["broken_count"] == 1 and r["auto_deprecated"] is False
    c = pl.read_counter(path)
    assert len(c["boundary_notes"]) == 1 and "passt nicht" in c["boundary_notes"][0]
    assert len(c["broken_locations"]) == 1 and c["broken_locations"][0]["file"] == "Foo.cs"


def test_lifecycle_pfad2_auto_deprecate_at_3(tmp_path):
    # AK-VOCAB-0 Schwelle 3
    pid, path = _seed_arch_pattern(tmp_path)
    pl.lifecycle(pid, 2, scope="arch", vault_root=tmp_path, broken_context="a", broken_reason="r")
    pl.lifecycle(pid, 2, scope="arch", vault_root=tmp_path, broken_context="b", broken_reason="r")
    assert pl.read_counter(path)["status"] != "deprecated"             # bei 2 noch nicht
    assert pl.lifecycle(pid, 2, scope="arch", vault_root=tmp_path, broken_context="c", broken_reason="r")["auto_deprecated"] is True
    assert pl.read_counter(path)["status"] == "deprecated"


def test_maturity_derived(tmp_path):
    pid, path = _seed_arch_pattern(tmp_path)
    pl.lifecycle(pid, 1, scope="arch", vault_root=tmp_path)
    pl.lifecycle(pid, 1, scope="arch", vault_root=tmp_path)
    pl.lifecycle(pid, 2, scope="arch", vault_root=tmp_path, broken_context="x", broken_reason="y")
    assert pl.maturity(pl.read_counter(path)) == 1   # usage 2 - broken 1


def test_lifecycle_pfad5_no_mutation(tmp_path):
    pid, path = _seed_arch_pattern(tmp_path)
    before = path.read_text(encoding="utf-8")
    assert pl.lifecycle(pid, 5, scope="arch", vault_root=tmp_path)["no_pattern_found"] is True
    assert path.read_text(encoding="utf-8") == before


def test_read_counter_graceful_default_on_legacy(tmp_path):
    # AK-MIG-0: Pattern ohne Counter-Felder -> Default 0 (kein Crash, kein Ranking-Regress-Crash)
    d = tmp_path / "Libraries" / "PatternLibrary" / "_project" / "BE-DOMAIN"
    d.mkdir(parents=True)
    legacy = d / "PT-DOM-099_legacy.md"
    legacy.write_text("---\nid: PT-DOM-099\nlayer: BE-DOMAIN\nname: Legacy\n---\n# Legacy\n", encoding="utf-8")
    c = pl.read_counter(legacy)
    assert c["usage_count"] == 0 and c["status"] == "experimental"


def test_migrate_backfills_legacy_idempotent(tmp_path):
    d = tmp_path / "Libraries" / "PatternLibrary" / "_project" / "BE-DOMAIN"
    d.mkdir(parents=True)
    (d / "PT-DOM-099_legacy.md").write_text("---\nid: PT-DOM-099\nlayer: BE-DOMAIN\nname: L\n---\n# L\n", encoding="utf-8")
    assert pl.migrate(scope="arch", vault_root=tmp_path) == 1
    assert pl.read_counter(d / "PT-DOM-099_legacy.md")["usage_count"] == 0
    assert pl.migrate(scope="arch", vault_root=tmp_path) == 0   # idempotent


def test_migrate_preserves_existing_counter(tmp_path):
    # APPEND-ohne-Ueberschreiben: bestehender usage_count bleibt
    pid, path = _seed_arch_pattern(tmp_path)
    pl.lifecycle(pid, 1, scope="arch", vault_root=tmp_path)
    pl.migrate(scope="arch", vault_root=tmp_path)
    assert pl.read_counter(path)["usage_count"] == 1


def test_thresholds_match_vocab(tmp_path):
    # AK-VOCAB-0 / C-2: kanonische Schwellen 5/10/3
    assert (pl.THRESH_ACTIVE, pl.THRESH_PROVEN, pl.THRESH_DEPRECATE) == (5, 10, 3)


def test_cli_lifecycle_pfad1(tmp_path):
    pid, _path = _seed_arch_pattern(tmp_path)
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "lifecycle", pid, "--pfad", "1", "--scope", "arch",
         "--vault-root", str(tmp_path)], capture_output=True, text=True)
    out = json.loads(r.stdout)
    assert out["usage_count"] == 1 and out["pfad"] == 1


# ══ rank_by_maturity (BL-237 AK-CTX-V2 — usage-getriebenes Ranked-find) ══
# SC-Vertrag ERGEBNIS2 Impl-Vertrag #2 + Blueprint batch_C2/S1 K-1/K-2/B-1/B-2/B-3.
# Konsumiert die maturity()-Primitive (P0, 22/22) read-only — Counter-Kern unberuehrt (DoD-21).
# Vokabular strikt code-konform (W-CNT-7): NUR usage_count/broken_count/maturity().

def _ranked_ids(entries, top_n=5):
    return [e["id"] for e in pl.rank_by_maturity(entries, top_n=top_n)]


def test_rank_by_maturity_desc_mixed_counter():
    # K-2: gemischte Counter -> maturity() DESC. A:usage10/broken1=9, B:usage3/broken0=3, C:usage0=0.
    entries = [
        {"id": "C", "usage_count": 0, "broken_count": 0, "confidence": "low"},
        {"id": "A", "usage_count": 10, "broken_count": 1, "confidence": "low"},
        {"id": "B", "usage_count": 3, "broken_count": 0, "confidence": "low"},
    ]
    assert _ranked_ids(entries) == ["A", "B", "C"]


def test_rank_by_maturity_cold_start_regress_equals_confidence():
    # K-1 (Kanarienvogel): usage=0 fuer ALLE -> maturity gleich -> confidence-Tie-Break greift.
    # Reihenfolge MUSS bit-identisch zum heutigen confidence-DESC-Ranking sein.
    entries = [
        {"id": "low", "usage_count": 0, "broken_count": 0, "confidence": "low"},
        {"id": "high", "usage_count": 0, "broken_count": 0, "confidence": "high"},
        {"id": "med", "usage_count": 0, "broken_count": 0, "confidence": "medium"},
    ]
    # Heutiges confidence-DESC-Ranking: high, med, low.
    confidence_ranking = sorted(
        entries, key=lambda e: {"high": 3, "medium": 2, "low": 1}[e["confidence"]], reverse=True
    )
    assert _ranked_ids(entries) == [e["id"] for e in confidence_ranking] == ["high", "med", "low"]


def test_rank_by_maturity_tie_break_stability():
    # B-2: gleiche maturity (alle usage=2/broken=0 -> m=2), unterschiedliche confidence
    # -> confidence DESC entscheidet deterministisch (keine Eingabe-Reihenfolge-Abhaengigkeit).
    entries = [
        {"id": "a", "usage_count": 2, "broken_count": 0, "confidence": "low"},
        {"id": "c", "usage_count": 2, "broken_count": 0, "confidence": "high"},
        {"id": "b", "usage_count": 2, "broken_count": 0, "confidence": "medium"},
    ]
    assert _ranked_ids(entries) == ["c", "b", "a"]


def test_rank_by_maturity_preserves_generic_global():
    # B-1 (INV-B1-4 / INV-SL-1): _generic/_global bleiben IMMER erhalten, unabhaengig vom Rang,
    # und werden vom Top-N-Cut NIE herausgefiltert.
    entries = [{"id": f"P{i}", "usage_count": 100, "broken_count": 0, "confidence": "high"} for i in range(6)]
    entries.append({"id": "G1", "layer": "_generic", "usage_count": 0, "broken_count": 0, "confidence": "low"})
    entries.append({"id": "GL", "scope": "_global", "usage_count": 0, "broken_count": 0, "confidence": "low"})
    out_ids = _ranked_ids(entries, top_n=5)
    assert "G1" in out_ids and "GL" in out_ids   # trotz usage=0 und 6 hoeher-reifen Konkurrenten


def test_rank_by_maturity_top_n_cut_on_sorted_list():
    # B-3: Top-N-Cut wendet auf die NEU (maturity) sortierte Liste an, nicht auf die confidence-Liste.
    # 7 Nicht-preserved Kandidaten, top_n=5 -> genau 5; die 5 hoechst-reifen bleiben.
    entries = [{"id": f"P{i}", "usage_count": i, "broken_count": 0, "confidence": "low"} for i in range(7)]
    out_ids = _ranked_ids(entries, top_n=5)
    assert len(out_ids) == 5
    assert out_ids == ["P6", "P5", "P4", "P3", "P2"]   # maturity DESC, P1/P0 abgeschnitten


def test_rank_by_maturity_vocabulary_only_usage_broken():
    # K-3 (Vokabular-Disziplin, W-CNT-7): rank_by_maturity ehrt usage_count/broken_count.
    # Phantom-Felder (confirm_count/maturity_score) duerfen die Reihenfolge NICHT beeinflussen.
    entries = [
        {"id": "real", "usage_count": 5, "broken_count": 0, "confidence": "low"},
        {"id": "phantom", "confirm_count": 99, "maturity_score": 99, "confidence": "low"},
    ]
    # 'real' (maturity=5) vor 'phantom' (maturity=0, Phantom-Felder ignoriert).
    assert _ranked_ids(entries) == ["real", "phantom"]


# ══════════════════════════════════════════════════════════════════════════
# ══ BL-237 batch_C3a — Counter-Feed-Kette (LOGFMT/R6a/R6b-Drain/R4/R2/AK-3) ══
# ══════════════════════════════════════════════════════════════════════════
# TDD-Recovery (I_VERIFY_STATE_batch_C3a verify_round=1 BLOCKED -> Tests materialisiert).
# Asserting-Tests fuer die im Sub-Blueprint vorgezeichnete Gold-Formel (K-1..K-4 + B-1..B-4)
# gegen den bereits code-grounden Impl-Stand (pattern_library.py:475-683). Reine tmp_path-Tests.

def _seed_pattern(tmp_path, layer="BE-DOMAIN", name="C3a Probe"):
    """Materialisiert EIN echtes drainbares Pattern (usage_count:0/status:experimental ab Geburt)."""
    _seed_layer(tmp_path, layer=layer)
    pid, fpath, _ = pl.add_arch(layer, name, description="C3a feed probe", vault_root=tmp_path)
    return pid, fpath


# ── GT-C3a-01 · AK-CTX-LOGFMT — strukturierter Parse + B-3 rueckwaerts-tolerant ──
def test_logfmt_parse_structured():
    line = pl.format_usage_line("VERIFIED", "PT-DOM-001", scope="arch",
                                commit_sha="abc123", file_anchor="Foo.cs:42",
                                fac_id="FAC-9", note="ok")
    rec = pl.parse_usage_line(line)
    assert rec is not None and rec["structured"] is True
    assert rec["signal"] == "VERIFIED" and rec["pattern_id"] == "PT-DOM-001"
    assert rec["commit_sha"] == "abc123" and rec["file_anchor"] == "Foo.cs:42"
    assert rec["fac_id"] == "FAC-9" and rec["scope"] == "arch"


def test_logfmt_backward_tolerant():
    # B-3: alte freie 5-Spalten-Zeile / Header / Leerzeile werfen KEINE Exception -> None (Skip).
    assert pl.parse_usage_line("2026-01-01 | VERIFIED | PT-OLD-1 | arch | freie zeile") is None
    assert pl.parse_usage_line("# pattern-usage log header") is None
    assert pl.parse_usage_line("") is None
    assert pl.parse_usage_line(None) is None
    # Pipe im Feldwert bricht die Spalten-Konvention NICHT (escaped zu '/').
    rt = pl.parse_usage_line(pl.format_usage_line("VERIFIED", "PT-X", note="a|b|c"))
    assert rt["note"] == "a/b/c"


# ── GT-C3a-02 · AK-CTX-R6a — vault-resolved (B-1) + lock-gated (B-2) ──
def test_r6a_vault_resolved(tmp_path):
    # B-1: Log landet VAULT-resolved unter .claude/wissen/, NICHT worktree-lokal.
    p = pl.append_usage("VERIFIED", "PT-DOM-001", vault_root=tmp_path)
    expected = tmp_path / pl.USAGE_LOG_RELPATH
    assert p == expected and p.exists()
    content = p.read_text(encoding="utf-8")
    assert pl.LOG_MARKER in content and "PT-DOM-001" in content
    # Append haengt an, ueberschreibt nicht.
    pl.append_usage("CONFORMANCE_PASS", "PT-DOM-002", vault_root=tmp_path)
    lines = [l for l in p.read_text(encoding="utf-8").splitlines() if l.startswith(pl.LOG_MARKER)]
    assert len(lines) == 2


def test_r6a_lock_gated(tmp_path, monkeypatch):
    # B-2: WENN factory_lock importierbar, umschliesst acquire/release den APPEND (Spy).
    calls = []

    class _FakeLock:
        @staticmethod
        def acquire(scope=None, worker_id=None, purpose=None, vault_root=None):
            calls.append(("acquire", scope))
            return True

        @staticmethod
        def release(worker_id, vault_root=None):
            calls.append(("release", worker_id))
            return True

    monkeypatch.setitem(sys.modules, "factory_lock", _FakeLock)
    pl.append_usage("VERIFIED", "PT-DOM-001", vault_root=tmp_path, lock_scope="pattern-usage")
    assert ("acquire", "pattern-usage") in calls
    assert any(c[0] == "release" for c in calls)
    # Reihenfolge: acquire VOR release (APPEND dazwischen).
    assert [c[0] for c in calls if c[0] in ("acquire", "release")][:2] == ["acquire", "release"]


# ── GT-C3a-03 · AK-CTX-R6b — Drain idempotent (K-1, BLOCKER) ──
def test_r6b_drain_idempotent(tmp_path):
    # K-1: zweimal drainen == einmal usage++ (processed-Cursor verhindert Doppel-Zaehlen).
    pid, fpath = _seed_pattern(tmp_path)
    pl.append_usage("VERIFIED", pid, vault_root=tmp_path)

    r1 = pl.drain_usage_log(vault_root=tmp_path)
    # usage_pp = Anzahl gezaehlter Signale (NICHT physische Zeilen; ein evtl. fuehrender
    # Newline-Prefix zaehlt als geskippte Zeile, bewegt den Counter aber nicht).
    assert r1["usage_pp"] == 1
    assert pl.read_counter(fpath)["usage_count"] == 1

    r2 = pl.drain_usage_log(vault_root=tmp_path)        # zweiter Lauf: 0 neue Signale
    assert r2["usage_pp"] == 0 and r2["processed_now"] == 0
    assert pl.read_counter(fpath)["usage_count"] == 1   # KEIN Doppel-Zaehlen
    assert r2["cursor_after"] == r1["cursor_after"]     # Cursor stabil


def test_r6b_drain_only_new_lines(tmp_path):
    # K-1 Erweiterung: ein NEUES Signal nach dem ersten Drain wird beim zweiten Drain genau 1x gezaehlt.
    pid, fpath = _seed_pattern(tmp_path)
    pl.append_usage("VERIFIED", pid, vault_root=tmp_path)
    pl.drain_usage_log(vault_root=tmp_path)
    pl.append_usage("CONFORMANCE_PASS", pid, vault_root=tmp_path)
    r = pl.drain_usage_log(vault_root=tmp_path)
    assert r["usage_pp"] == 1 and r["processed_now"] == 1   # genau 1 neue Zeile nach erstem Drain
    assert pl.read_counter(fpath)["usage_count"] == 2


# ── GT-C3a-04 · AK-CTX-R4 — Anti-False-Positive-Gate (K-2, BLOCKER) + auto-deprecate@3 (B-4) ──
def test_r4_anti_false_positive(tmp_path):
    # K-2: unabhaengiger Edit OHNE commit_sha/file_anchor-Match loest NIE pfad-2 (kein broken++).
    pid, fpath = _seed_pattern(tmp_path)
    applied_sha, applied_anchor = "deadbeef", "Foo.cs:10"

    # Fremder Commit, andere Datei -> Gate blockt.
    res_unrelated = pl.detect_and_emit_revert(
        pid, {"commit_sha": "ffff", "file_anchor": "Bar.cs:99"},
        applied_commit_sha=applied_sha, applied_file_anchor=applied_anchor, vault_root=tmp_path)
    assert res_unrelated["gated"] is True and res_unrelated["emitted"] is False
    pl.drain_usage_log(vault_root=tmp_path)
    assert pl.read_counter(fpath)["broken_count"] == 0   # KEIN False-Positive broken++

    # Echter Revert (BEIDE Anker matchen) -> Signal emittiert -> Drain macht broken++.
    res_real = pl.detect_and_emit_revert(
        pid, {"reverted_commit_sha": applied_sha, "file_anchor": applied_anchor},
        applied_commit_sha=applied_sha, applied_file_anchor=applied_anchor, vault_root=tmp_path)
    assert res_real["gated"] is False and res_real["emitted"] is True
    pl.drain_usage_log(vault_root=tmp_path)
    assert pl.read_counter(fpath)["broken_count"] == 1

    # Gate ohne angewandte Anker (leer) -> konservativ False.
    assert pl.is_revert_of_application({"commit_sha": "x", "file_anchor": "y"}, "", "") is False


def test_r4_auto_deprecate_irreversible_at_threshold(tmp_path):
    # B-4: 3x echter Revert -> auto-deprecate@3 (THRESH_DEPRECATE) bleibt erreicht (Sink-Irreversibilitaet).
    pid, fpath = _seed_pattern(tmp_path)
    sha, anchor = "cafe", "Mod.cs:1"
    for _ in range(pl.THRESH_DEPRECATE):
        pl.detect_and_emit_revert(
            pid, {"reverted_commit_sha": sha, "file_anchor": anchor},
            applied_commit_sha=sha, applied_file_anchor=anchor, vault_root=tmp_path)
        pl.drain_usage_log(vault_root=tmp_path)
    c = pl.read_counter(fpath)
    assert c["broken_count"] >= pl.THRESH_DEPRECATE
    assert c["status"] == "deprecated"


# ── GT-C3a-05 · AK-CTX-R2 — Asymmetrie: "kein finding" NIE usage++ (K-4) ──
def test_r2_asymmetry_no_signal_no_increment(tmp_path):
    # K-4: ein Drain ueber einen Log OHNE CONFORMANCE_PASS/VERIFIED bewegt usage_count NICHT.
    pid, fpath = _seed_pattern(tmp_path)
    # Nur ein KEIN_PATTERN-Info-Signal (legacy/no-finding) -> wird beim Drain geskippt.
    pl.append_usage("KEIN_PATTERN", pid, vault_root=tmp_path, note="no finding")
    r = pl.drain_usage_log(vault_root=tmp_path)
    assert r["usage_pp"] == 0 and r["broken_pp"] == 0 and r["skipped"] >= 1
    assert pl.read_counter(fpath)["usage_count"] == 0   # Asymmetrie: kein finding -> NIE usage++

    # Demgegenueber: ein echtes CONFORMANCE_PASS bewegt den Counter (Positiv-Kontrolle).
    pl.append_usage("CONFORMANCE_PASS", pid, vault_root=tmp_path)
    pl.drain_usage_log(vault_root=tmp_path)
    assert pl.read_counter(fpath)["usage_count"] == 1


# ── GT-C3a-06 · AK-3 — POST-B (b): Drain produziert genau 1x usage++ via R6b ──
def test_ak3_postb_drain_exactly_once(tmp_path):
    # AK-3 (b): ein CONFORMANCE_PASS-Signal -> nach Drain genau 1x usage++ (idempotenter R6b-Sink).
    pid, fpath = _seed_pattern(tmp_path)
    pl.append_usage("CONFORMANCE_PASS", pid, scope="arch", vault_root=tmp_path,
                    commit_sha="c1", file_anchor="A.cs:1")
    pl.drain_usage_log(vault_root=tmp_path)
    pl.drain_usage_log(vault_root=tmp_path)   # erneuter POST-B-Lauf
    assert pl.read_counter(fpath)["usage_count"] == 1   # genau 1x, kein Doppel-Zaehlen


# ════════════════════════════════════════════════════════════════════════════════════════
# batch_C3b (SEMFORMAT / R5 / AK-4 / AK-5) — SemanticLibrary-Symmetrie + 2 Berater-Achsen.
# TDD-Recovery (FanIn in-step, analog batch_C3a): additive Tests GEGEN den bestehenden Impl-Stand
# (pattern_library.py add_semantic*/migrate_semantic/lifecycle scope=semantic + _PT_berater_*.md
# Cmd-Vertraege). KEINE Aenderung der Schreib-Seite — Reuse-not-rebuild (DoD-21).
# Gold-Formel sub-1.md §Gold: K-1 R5-Symmetrie up+down, K-2 S1-Audit-Disziplin, K-3 arch-Regression,
# K-4 forensic-boundary_note==pfad-2-Vokabular + B-1..B-3 Boundary + AK-4/AK-5 Vertrags-Selbsttest.
# ════════════════════════════════════════════════════════════════════════════════════════

COMMANDS_DIR = Path(__file__).resolve().parents[1] / "commands"


def _seed_sem_pattern(tmp_path, layer="BE-DOMAIN", name="ZEVSP", target="terms"):
    """SEMFORMAT-Helfer: legt EINEN Semantic-Eintrag als per-Term-Frontmatter-Datei an (B-1)."""
    sid, fpath, created = pl.add_semantic_file(layer, name, description="Cross-System-ID-Suffix",
                                               target=target, vault_root=tmp_path)
    return sid, fpath, created


# ── Block 1 · SEMFORMAT (Py, Wurzel) — B-1 / B-2 / B-3 ──
def test_semformat_writes_frontmatter_file(tmp_path):
    # B-1: add_semantic legt eine per-Term-.md-Datei mit vollem Counter-Frontmatter an
    # (NICHT mehr nur Bullet). Spiegelt add_arch / _COUNTER_DEFAULTS (AK-SCHEMA-0).
    sid, fpath, created = _seed_sem_pattern(tmp_path)
    assert created is True and fpath.exists() and fpath.suffix == ".md"
    txt = fpath.read_text(encoding="utf-8")
    assert f"id: {sid}" in txt and "scope: semantic" in txt and "name: ZEVSP" in txt
    # Voller Counter ab Geburt (gespiegelt von add_arch):
    for fld in ("status: experimental", "usage_count: 0", "broken_count: 0",
                "boundary_notes: []", "broken_locations: []", "variants: []"):
        assert fld in txt


def test_semformat_findable_by_find_pattern_file(tmp_path):
    # B-1 KRITISCH (F1->F2-Brueckenschluss): die neu geschriebene Datei ist via
    # _find_pattern_file(scope="semantic") auffindbar — sonst ist R5 mechanisch blockiert.
    sid, fpath, _ = _seed_sem_pattern(tmp_path)
    found = pl._find_pattern_file(sid, scope="semantic", vault_root=tmp_path)
    assert found is not None and found == fpath


def test_semformat_defaults(tmp_path):
    # B-1: read_counter der neuen Datei liefert Cold-Start-Defaults.
    sid, fpath, _ = _seed_sem_pattern(tmp_path)
    c = pl.read_counter(fpath)
    assert c["usage_count"] == 0 and c["broken_count"] == 0
    assert c["status"] == "experimental" and c["scope"] == "semantic"
    assert c["boundary_notes"] == [] and c["variants"] == []


def test_semformat_glossary_layout(tmp_path):
    # B-1: glossary-target landet korrekt unter _global/ (eigenes Layout, AK-MIG-0-konform).
    sid, fpath, created = pl.add_semantic_file("BE-DOMAIN", "QDVS", description="Qualitaetsdarstellung",
                                               target="glossary", vault_root=tmp_path)
    assert created is True and "_global" in str(fpath) and fpath.exists()
    # Counter-Frontmatter ab Geburt auch fuer glossary:
    assert pl.read_counter(fpath)["status"] == "experimental" and pl.read_counter(fpath)["usage_count"] == 0
    # BOUNDARY-FINDING (FanIn batch_C3b, surfaced): _find_pattern_file globt _project/*/ + _generic/ +
    # _project/ — aber NICHT _global/{pid}*.md. => glossary-Eintraege sind heute NICHT lifecycle-findbar
    # (lifecycle(scope=semantic) auf SL-GLOSS-* -> pattern_not_found). Die DOKUMENTIERTE Gold-Achse
    # (add_semantic default target=terms + Migration terms/naming) landet unter _project/<layer>/ und IST
    # findbar (s. test_semformat_findable_by_find_pattern_file). Glossary-Lifecycle = surfaced boundary
    # fuer modelMaintain/qualityGate (1-Zeilen-Glob-Erweiterung _global/{pid}*.md), NICHT in batch_C3b-Gold.
    assert pl._find_pattern_file(sid, scope="semantic", vault_root=tmp_path) is None  # dokumentiertes IST


def test_semformat_migration_lossless(tmp_path):
    # B-2: jeder Bestands-Bullet -> GENAU 1 per-Term-Datei (Name+Description erhalten); idempotent
    # (2. Lauf -> 0 Duplikate); Alt-Aggregat-Datei bleibt als Lese-Index liegen (kein Datenverlust).
    layer = "BE-DOMAIN"
    agg = pl._layer_dir("semantic", layer, vault_root=tmp_path) / "domain-terms.md"
    agg.parent.mkdir(parents=True, exist_ok=True)
    agg.write_text("# Domain Terms\n\n- **ZEVSP** — Cross-System-ID-Suffix\n"
                   "- **QDVS** — Qualitaetsdarstellung\n", encoding="utf-8")

    n1 = pl.migrate_semantic(layer=layer, vault_root=tmp_path)
    assert n1 == 2                                   # 2 Bullets -> 2 per-Term-Dateien
    f_zevsp = pl._sem_file_for_name(layer, "ZEVSP", target="terms", vault_root=tmp_path)
    assert f_zevsp is not None
    body = f_zevsp.read_text(encoding="utf-8")
    assert "name: ZEVSP" in body and "Cross-System-ID-Suffix" in body  # verlustfrei
    assert pl.read_counter(f_zevsp)["usage_count"] == 0                 # Cold-Start
    assert agg.exists()                                                # Alt-Aggregat bleibt liegen

    n2 = pl.migrate_semantic(layer=layer, vault_root=tmp_path)
    assert n2 == 0                                                      # idempotent: keine Duplikate


def test_semformat_vault_resolved(tmp_path):
    # B-3: add_semantic_file(... vault_root=tmp) landet unter resolve_vault_root(override), NICHT im CWD.
    _sid, fpath, _ = _seed_sem_pattern(tmp_path)
    assert str(fpath).startswith(str(tmp_path))
    assert "Libraries" in str(fpath) and "SemanticLibrary" in str(fpath)


# ── Block 2 · R5 (Py, depends_on SEMFORMAT) — KANARIENVOEGEL K-1 / K-2 / K-3 ──
def test_r5_lifecycle_semantic_up(tmp_path):
    # K-1 (up): lifecycle(scope="semantic") hebt usage_count 0->1 (NICHT pattern_not_found)
    # und promotet experimental->active @5 — gleicher Kern wie arch, NUR via scope-Parameter.
    sid, fpath, _ = _seed_sem_pattern(tmp_path)
    r1 = pl.lifecycle(sid, 1, scope="semantic", vault_root=tmp_path)
    assert r1.get("error") is None and r1["usage_count"] == 1
    assert pl.read_counter(fpath)["usage_count"] == 1
    for _ in range(pl.THRESH_ACTIVE - 1):
        pl.lifecycle(sid, 1, scope="semantic", vault_root=tmp_path)
    assert pl.read_counter(fpath)["status"] == "active"   # promote @5 (symmetrisch zu arch)


def test_r5_lifecycle_semantic_down(tmp_path):
    # K-1 (down): lifecycle(scope="semantic", pfad=2) hebt broken_count + schreibt boundary_notes/
    # broken_locations; auto-deprecate @3. BEIDE Pfade existieren -> kein downgrade-only-Klon (F3).
    sid, fpath, _ = _seed_sem_pattern(tmp_path)
    r = pl.lifecycle(sid, 2, scope="semantic", vault_root=tmp_path,
                     broken_context="Foo.py:10", broken_reason="anti-pattern")
    assert r.get("error") is None and r["broken_count"] == 1
    c = pl.read_counter(fpath)
    assert "broken in Foo.py:10: anti-pattern" in c["boundary_notes"]
    assert c["broken_locations"][0]["file"] == "Foo.py:10"
    for _ in range(pl.THRESH_DEPRECATE - 1):
        pl.lifecycle(sid, 2, scope="semantic", vault_root=tmp_path,
                     broken_context="Foo.py:10", broken_reason="anti-pattern")
    assert pl.read_counter(fpath)["status"] == "deprecated"   # auto-deprecate @3 symmetrisch


def test_r5_s1_audit_discipline(tmp_path):
    # K-2 (S1-Audit-Disziplin, C-6/F10): der Counter incrementiert NUR durch einen expliziten
    # pfad-1-Lifecycle-Call (echtes positives Signal) — das blosse Anlegen/Finden eines Eintrags
    # (Match/Erwaehnung) bewegt usage_count NICHT. Test beweist: kein impliziter Auto-Increment.
    sid, fpath, _ = _seed_sem_pattern(tmp_path)
    assert pl.read_counter(fpath)["usage_count"] == 0            # Geburt: 0
    pl._find_pattern_file(sid, scope="semantic", vault_root=tmp_path)   # blosser Match
    pl.read_counter(fpath)                                       # blosses Lesen
    assert pl.read_counter(fpath)["usage_count"] == 0           # KEIN Increment ohne echtes Signal
    pl.lifecycle(sid, 1, scope="semantic", vault_root=tmp_path)  # echtes positives Signal
    assert pl.read_counter(fpath)["usage_count"] == 1           # erst JETZT ++


def test_arch_regression_38_green(tmp_path):
    # K-3 (arch-Regression / scope-Isolation): der arch-Pfad bleibt UNANGETASTET von SEMFORMAT/R5.
    # Ein semantic-lifecycle beruehrt NICHT die arch-Library; ein arch-Pattern bleibt bit-stabil.
    sid_arch, fpath_arch = _seed_arch_pattern(tmp_path)
    before = fpath_arch.read_text(encoding="utf-8")
    # semantic-Operationen daneben:
    sid_sem, _, _ = _seed_sem_pattern(tmp_path)
    pl.lifecycle(sid_sem, 1, scope="semantic", vault_root=tmp_path)
    pl.lifecycle(sid_sem, 2, scope="semantic", vault_root=tmp_path,
                 broken_context="x", broken_reason="y")
    # arch-Pattern unveraendert (kein Cross-scope-Leak):
    assert fpath_arch.read_text(encoding="utf-8") == before
    assert pl.read_counter(fpath_arch)["usage_count"] == 0
    # arch-lifecycle wirkt weiter normal (scope-parametrisch, getrennte Libraries):
    pl.lifecycle(sid_arch, 1, scope="arch", vault_root=tmp_path)
    assert pl.read_counter(fpath_arch)["usage_count"] == 1
    assert pl._find_pattern_file(sid_arch, scope="semantic", vault_root=tmp_path) is None


# ── Block 3 · AK-4 classify (Cmd-Vertrag-Selbsttest, parallel zu Block 1/2) ──
def _read_cmd(name):
    return (COMMANDS_DIR / name).read_text(encoding="utf-8")


def test_ak4_classify_three_orthogonal_axes(tmp_path):
    # AK-4 (Vertrag, INV-CLS-2): _PT_berater_classify.md belegt 3 orthogonale Achsen
    # (semantisch|architektonisch|FACHLICH), FACHLICH eigenstaendig (geht NICHT in semantisch unter).
    t = _read_cmd("_PT_berater_classify.md")
    assert "status: active" in t                       # untracked-Draft -> active (committed)
    assert "INV-CLS-2" in t and "orthogonal" in t.lower()
    for axis in ("semantisch", "architektonisch", "FACHLICH"):
        assert axis in t
    # Kern-Fall (AK-4): FACHLICH geht NICHT in semantisch unter.
    assert "geht NICHT in semantisch unter" in t or "FACHLICH geht NICHT" in t


def test_ak4_classify_tie_break_deterministic(tmp_path):
    # AK-4 (Tie-Break, INV-CLS-3 / DoD-8): deterministische Prioritaet
    # architektonisch > factoring > fachlich > semantisch + Doku-Pflicht (tie_break_log).
    # (BL-257 schob factoring als 4. Achse zwischen architektonisch und fachlich ein;
    #  Test auf die kanonische 4-Achsen-Prioritaet des Docs nachgezogen, BL-303-Adjudikation.)
    t = _read_cmd("_PT_berater_classify.md")
    assert "INV-CLS-3" in t and "tie_break_log" in t
    assert "architektonisch > factoring > fachlich > semantisch" in t


# ── Block 4 · AK-5 timeAxis/contradiction/forensic (Cmd-Vertrag) — KANARIENVOGEL K-4 ──
def test_forensic_boundary_note_pfad2_verbatim(tmp_path):
    # K-4 KRITISCH (F4 / INV-FOR-3): forensic boundary_note mappt VERBATIM auf das pfad-2-Vokabular
    # f"broken in {ctx}: {reason}" (pattern_library.py:Z602) + broken_locations {file,reason,date} (Z604).
    # Beweis 1 (Cmd-Vertrag): der Draft formuliert das exakte Format.
    t = _read_cmd("_PT_berater_forensic.md")
    assert "INV-FOR-3" in t
    assert 'f"broken in {broken_context}: {broken_reason}"' in t
    # Beweis 2 (Code-Grounding): der Live-lifecycle-pfad-2 produziert GENAU diesen String.
    sid, fpath, _ = _seed_sem_pattern(tmp_path)
    pl.lifecycle(sid, 2, scope="semantic", vault_root=tmp_path,
                 broken_context="Mod.py:7", broken_reason="misuse")
    note = pl.read_counter(fpath)["boundary_notes"][0]
    assert note == "broken in Mod.py:7: misuse"        # forensic-String == lifecycle-String (kein Uebersetzungs-Bedarf)


def test_ak5_forensic_exactly_three_hypotheses(tmp_path):
    # AK-5 (INV-FOR-2): GENAU 3 Hypothesen (pattern_wrong/misused/misdescribed) + konservativer
    # Tie-Break (misused>misdescribed>wrong, kein vorschnelles broken++).
    t = _read_cmd("_PT_berater_forensic.md")
    assert "INV-FOR-2" in t
    for h in ("pattern_wrong", "pattern_misused", "pattern_misdescribed"):
        assert h in t
    assert "misused > misdescribed > wrong" in t or "misused>misdescribed>wrong" in t


def test_ak5_timeaxis_contradiction_spine(tmp_path):
    # AK-5 (Stage-3->4->6-Spine): timeAxis (reverts_raw) + contradiction (items) verdrahtet;
    # forensic liest beide. F8 PL_DRIFT/HOLD als batch_C5-Constraint dokumentiert (NICHT vorgezogen).
    ta = _read_cmd("_PT_berater_timeAxis.md")
    co = _read_cmd("_PT_berater_contradiction.md")
    fo = _read_cmd("_PT_berater_forensic.md")
    assert "status: active" in ta and "status: active" in co
    assert "reverts_raw" in ta and "reverts_raw" in fo        # timeAxis liefert, forensic konsumiert
    assert "contradiction" in fo                              # forensic liest das DASS


# ════════════════════════════════════════════════════════════════════════════════════════
# ══ BL-237 batch_C4 — Domain-Achse + FactoringLibrary (4-kind add) + Conformance 4-rule_source ══
# ════════════════════════════════════════════════════════════════════════════════════════
# SC-FULL Z5 OBSERVE5 (F1-F12) + sub-1.md Gold-Definition KONSUMIERT (NICHT re-analysiert).
# Block 0 DOMAIN-GATE (Vertrag) -> Block 1 F1 (Py, Enabler, K-1/K-2/K-3 + B-1/B-3) ->
# Block 2 AK-7 (Py-Bootstrap B-2 + Cmd-Consult NON-BLOCKING) -> Block 3 F8 (4-rule_source + K-4) ->
# Block 4 F4 (resolution_status-Trippel B-4). Reuse-not-rebuild (DoD-21): add_arch/next_id/
# _find_pattern_file/_SCOPE_LIB NUR genutzt. K-2 (scope=arch verhaltensgleich) ist der haerteste Stopp.

# ── Block 0 · DOMAIN-GATE (Design-Notiz, Vertrag) ──
def test_domain_gate_design_note_verdict_fixed(tmp_path):
    # A-DOMAIN-GATE (Vertrag, F6): Die Design-Notiz fixiert das vor-entschiedene Verdikt —
    # Domain = eigene DomainLibrary (spiegelnd), NICHT auf A-Pipeline routen (C-1); ableitbar
    # aus W-AXIS-1/2/3 + GOAL/SOA-2. Die Notiz lebt als Code-Kommentar im pattern_library.py.
    src = (Path(__file__).parent / "pattern_library.py").read_text(encoding="utf-8")
    assert "DOMAIN-GATE" in src
    assert "DomainLibrary" in src and "FactoringLibrary" in src
    # Kern-Verdikt: NICHT auf A-Pipeline routen (C-1).
    assert "NICHT" in src and "A-Pipeline" in src
    assert "W-AXIS-1" in src and "W-AXIS-2" in src and "W-AXIS-3" in src and "GOAL" in src


def test_domain_gate_no_a_pipeline_routing_in_scope_lib(tmp_path):
    # DOMAIN-GATE (F6, C-1): 0 A-Pipeline-Routing fuer Domain — _SCOPE_LIB mappt domain auf
    # eine eigene Library, KEIN A-Pipeline-Delegations-Pfad im Counter-Kern.
    assert pl._SCOPE_LIB["domain"] == "DomainLibrary"
    assert pl._SCOPE_LIB["factoring"] == "FactoringLibrary"
    # Es gibt KEINE Routing-Funktion, die domain an eine A-Pipeline delegiert.
    assert not any("a_pipeline" in n.lower() or "route_domain" in n.lower() for n in dir(pl))


# ── Block 1 · F1 (Py, Enabler) — KANARIENVOEGEL K-1 / K-2 / K-3 ──
def test_add_arch_scope_domain_writes_DOM_id_full_counter_fm(tmp_path):
    # A-F1 (kritisch): add_arch(scope="domain") legt DOM-Datei unter DomainLibrary an mit vollem
    # Counter-FM (usage_count==0, broken_count==0, status==experimental, _COUNTER_DEFAULTS).
    pid, fpath, _ = pl.add_arch("BE-DOMAIN", "Domain Term Rule", description="Fachliche Regel",
                                scope="domain", vault_root=tmp_path)
    assert pid == "DOM-DOM-001"
    assert fpath.exists()
    assert "Libraries/DomainLibrary/_project/BE-DOMAIN".replace("/", os.sep) in str(fpath) \
        or "Libraries/DomainLibrary/_project/BE-DOMAIN" in str(fpath).replace(os.sep, "/")
    c = pl.read_counter(fpath)
    assert c["usage_count"] == 0 and c["broken_count"] == 0 and c["status"] == "experimental"
    assert c["scope"] == "domain"
    content = fpath.read_text(encoding="utf-8")
    for field in ("boundary_notes: []", "broken_locations: []", "derived_from: null", "variants: []"):
        assert field in content


def test_add_arch_scope_factoring_writes_FAC_id(tmp_path):
    # A-F1 (analog factoring): add_arch(scope="factoring") -> FAC-Datei unter FactoringLibrary.
    pid, fpath, _ = pl.add_arch("BE-CORE", "Extract Method", scope="factoring", vault_root=tmp_path)
    assert pid == "FAC-CORE-001"
    assert "FactoringLibrary" in str(fpath).replace(os.sep, "/")
    assert pl.read_counter(fpath)["scope"] == "factoring"


def test_find_pattern_file_scope_domain_factoring_finds_birth_file(tmp_path):
    # B-1 (kritisch, Brueckenschluss): _find_pattern_file(scope) findet die add_arch-Geburts-Datei
    # (sonst ist der Counter fuer die neue Library mechanisch blind).
    dpid, _, _ = pl.add_arch("BE-DOMAIN", "Domain X", scope="domain", vault_root=tmp_path)
    fpid, _, _ = pl.add_arch("BE-CORE", "Factor Y", scope="factoring", vault_root=tmp_path)
    assert pl._find_pattern_file(dpid, scope="domain", vault_root=tmp_path) is not None
    assert pl._find_pattern_file(fpid, scope="factoring", vault_root=tmp_path) is not None
    # lifecycle(scope=domain) findet die Geburts-Datei und zaehlt hoch (mechanisch nicht-blind).
    res = pl.lifecycle(dpid, 1, scope="domain", vault_root=tmp_path)
    assert res.get("usage_count") == 1


def test_next_id_scope_deterministic_no_pt_leak(tmp_path):
    # K-3 (kritisch): next_id(scope) vergibt deterministisch DOM-/FAC-Prefixe, KEIN PT-Leak,
    # kollisionsfrei (2 Aufrufe -> NNN+1).
    assert pl.next_id("BE-DOMAIN", vault_root=tmp_path, scope="domain") == "DOM-DOM-001"
    assert pl.next_id("BE-CORE", vault_root=tmp_path, scope="factoring") == "FAC-CORE-001"
    p1, _, _ = pl.add_arch("BE-DOMAIN", "A", scope="domain", vault_root=tmp_path)
    p2, _, _ = pl.add_arch("BE-DOMAIN", "B", scope="domain", vault_root=tmp_path)
    assert p1 == "DOM-DOM-001" and p2 == "DOM-DOM-002"
    # KEIN PT-Prefix in der DomainLibrary.
    dlib = tmp_path / "Libraries" / "DomainLibrary" / "_project" / "BE-DOMAIN"
    assert not any(f.name.startswith("PT-") for f in dlib.glob("*.md"))


def test_add_arch_scope_arch_default_unchanged(tmp_path):
    # K-2 (harter Regressions-Stopp): add_arch/next_id OHNE scope-Arg (Default scope=arch) sind
    # verhaltensgleich — PT-Prefix, PatternLibrary, bit-identisch zum alten Pfad.
    _seed_layer(tmp_path)
    assert pl.next_id("BE-DOMAIN", vault_root=tmp_path) == "PT-DOM-001"      # default scope=arch
    pid, fpath, _ = pl.add_arch("BE-DOMAIN", "Arch Default", vault_root=tmp_path)
    assert pid == "PT-DOM-001"
    assert "PatternLibrary" in str(fpath).replace(os.sep, "/")
    assert pl.read_counter(fpath)["scope"] == "arch"


def test_add_arch_scope_single_path_no_clone(tmp_path):
    # K-1: die 4-kind-add laeuft ueber EINE parametrisierte Funktion (add_arch) — KEIN zweiter
    # numerierter add-Pfad pro scope, KEIN _add_numbered-Extrakt mit losen Aufrufern (F2/F4/DoD-21).
    import inspect
    src = inspect.getsource(pl)
    # KEINE geklonten add_domain/add_factoring-Funktionen.
    assert "def add_domain(" not in src and "def add_factoring(" not in src
    # add_arch traegt den scope-Parameter (EINE Funktion fuer alle numerierten scopes).
    assert "scope" in inspect.signature(pl.add_arch).parameters
    assert "scope" in inspect.signature(pl.next_id).parameters
    # Verhaltens-Beweis: dieselbe Funktion bedient arch+domain+factoring.
    a, _, _ = pl.add_arch("BE-DOMAIN", "A1", vault_root=tmp_path)                       # arch
    d, _, _ = pl.add_arch("BE-DOMAIN", "D1", scope="domain", vault_root=tmp_path)       # domain
    f, _, _ = pl.add_arch("BE-DOMAIN", "F1", scope="factoring", vault_root=tmp_path)    # factoring
    assert a.startswith("PT-") and d.startswith("DOM-") and f.startswith("FAC-")


def test_add_arch_scope_vault_resolved(tmp_path):
    # B-3: add_arch(scope=domain, vault_root=tmp) landet unter resolve_vault_root/Libraries/DomainLibrary/,
    # NICHT im CWD/worktree-lokal.
    _, fpath, _ = pl.add_arch("BE-DOMAIN", "VaultRes", scope="domain", vault_root=tmp_path)
    expected = tmp_path / "Libraries" / "DomainLibrary"
    assert str(expected) in str(fpath)


# ── Block 2 · AK-7 (Py-Bootstrap + Cmd-Consult NON-BLOCKING) ──
def test_ak7_bootstrap_domain_factoring_index_and_seed(tmp_path):
    # B-2 / A-AK7: bootstrap legt DomainLibrary + FactoringLibrary im Repo an mit _index.md + >=1 Seed.
    res = pl.bootstrap_domain_factoring(vault_root=tmp_path)
    for scope, lib in (("domain", "DomainLibrary"), ("factoring", "FactoringLibrary")):
        info = res[scope]
        assert info["created"] is True
        assert Path(info["seed_path"]).exists()                       # >=1 Seed materialisiert
        idx = tmp_path / "Libraries" / lib / "_project" / "BE-DOMAIN" / "_index.md"
        assert idx.exists()                                           # _index.md angelegt
        assert info["seed_id"].startswith("DOM-" if scope == "domain" else "FAC-")


def test_ak7_bootstrap_idempotent(tmp_path):
    # B-2: ein 2. Bootstrap-Lauf erzeugt KEINE Duplikate (created=False, kein zweiter Seed).
    pl.bootstrap_library("domain", vault_root=tmp_path)
    second = pl.bootstrap_library("domain", vault_root=tmp_path)
    assert second["created"] is False
    seeds = list((tmp_path / "Libraries" / "DomainLibrary" / "_project" / "BE-DOMAIN").glob("DOM-*.md"))
    assert len(seeds) == 1                                            # genau EIN Seed (idempotent)


def test_ak7_consult_non_blocking_in_refactor_and_architect(tmp_path):
    # A-AK7 (Vertrag): _TDD_refactorCode.md + _I_cleanCodeArchitect.md tragen einen
    # DomainLibrary/FactoringLibrary-Consult-Schritt MIT expliziter NON-BLOCKING-Klausel.
    rc = _read_cmd("_TDD_refactorCode.md")
    ar = _read_cmd("_I_cleanCodeArchitect.md")
    for t in (rc, ar):
        assert "DomainLibrary" in t and "FactoringLibrary" in t
        assert "NON-BLOCKING" in t
        assert "greenfield" in t.lower()
    # refactorCode: greenfield-leer bricht NICHT ab (B.5-Abort nur fuer pattern+semantic).
    assert "NON-BLOCKING-KLAUSEL" in rc            # explizite Klausel vorhanden
    assert "Greenfield bricht Refactor nie" in rc  # Kern-Constraint woertlich
    assert "matched_domain" in rc and "matched_factoring" in rc


# ── Block 3 · F8 Conformance 4-rule_source (Cmd-Grounding) — KANARIENVOGEL K-4 ──
def test_f8_conformance_four_rule_source(tmp_path):
    # A-F8 (Vertrag): die Union-Liste listet domain/factoring-Reads + 2 source-Tags -> 4 rule_source;
    # ARCH-10/29 rule_source-PFLICHT bleibt erfuellt.
    t = _read_cmd("_PostBatch_PatternConformance.md")
    assert "DomainLibrary" in t and "FactoringLibrary" in t
    for tag in ('source: "pattern"', 'source: "semantic"', 'source: "domain"', 'source: "factoring"'):
        assert tag in t
    # 4-rule_source explizit als Vertrags-Anker.
    assert '"pattern" | "semantic" | "domain" | "factoring"' in t


def test_f8_domain_rule_severity_info_not_blocker(tmp_path):
    # K-4 (kritisch, Anti-Overclaim): Domain-/Factoring-Regel-Default = severity:INFO (non-blocking),
    # NICHT BLOCKER -> kein faelschlicher Stage-Stopp (F9, vorhandene INFO-Klasse).
    t = _read_cmd("_PostBatch_PatternConformance.md")
    assert 'domain_default_severity   = "INFO"' in t or 'domain_default_severity = "INFO"' in t
    assert 'factoring_default_severity = "INFO"' in t
    assert "Anti-Overclaim" in t
    # INFO bleibt non-blocking (die vorhandene INFO->ignoriert-Klasse).
    assert "INFO" in t and "ignoriert" in t


# ── Block 4 · F4 glossary-CONFLICT resolution_status-Trippel ──
def test_f4_glossary_conflict_resolution_status_triple(tmp_path):
    # B-4: domain-glossary CONFLICT-Work-Item-Schema enthaelt resolution_status ∈ {open,resolved,by_design}.
    assert pl.RESOLUTION_STATUS == ("open", "resolved", "by_design")
    item = pl.make_glossary_conflict_item("ZEVSP", "term ueberlappt 2 Domains",
                                          resolution_status="open",
                                          source_a="DomainA", source_b="DomainB")
    assert item["resolution_status"] == "open"
    assert item["type"] == "glossary_conflict" and item["scope"] == "domain"
    assert item["term"] == "ZEVSP"
    # ungueltiger Status -> ValueError (Trippel ist verbindlich).
    import pytest
    with pytest.raises(ValueError):
        pl.make_glossary_conflict_item("X", "c", resolution_status="ignored")


def test_f4_by_design_not_filtered_as_noise(tmp_path):
    # B-4 (F10): ein resolution_status=by_design-Item wird NICHT als Noise verworfen — es bleibt
    # im Item-Bestand erhalten (nur nicht 'actionable'/open).
    items = [
        pl.make_glossary_conflict_item("T1", "c1", resolution_status="open"),
        pl.make_glossary_conflict_item("T2", "c2", resolution_status="by_design"),
        pl.make_glossary_conflict_item("T3", "c3", resolution_status="resolved"),
    ]
    actionable = pl.filter_actionable_conflicts(items)
    # Nur 'open' ist actionable.
    assert len(actionable) == 1 and actionable[0]["term"] == "T1"
    # by_design ist NICHT geloescht — der volle Bestand traegt es weiter (kein Noise-Drop).
    by_design = [it for it in items if it["resolution_status"] == "by_design"]
    assert len(by_design) == 1 and by_design[0]["term"] == "T2"


# ════════════════════════════════════════════════════════════════════════════════════════
# BL-237 batch_C5 (P4 Querschnitt) — FanIn-TDD-Recovery (analog C3a/C3b/C4-Recovery, additiv).
# SC-OBSERVE6 (F1-F12, sc_verdict=OBSERVE_DONE_PENDING_MODELMAINTAIN) + S1/sub-1.md (5 Exit-Kriterien,
# K-1..K-4) als verbindlicher Blueprint-Input KONSUMIERT, NICHT re-analysiert. Schreib-Seite UNVERAENDERT
# (Code war code-complete, nur Test-Luecke). 53/69-Guard-Baseline regressionsfrei (K-4).
# ════════════════════════════════════════════════════════════════════════════════════════


# ── Block 5 · GT-C5-01 · AK-CTX-WORTHINESS-EXTRACT (F1, §4.1) — KANARIENVOGEL K-1 ──
def test_is_pattern_worthy_callable_and_signal_parity(tmp_path):
    # K-1 (Termination-P1): is_pattern_worthy() ist aufrufbar -> bool und die 5 Signal-Klassen
    # sind 1:1 die Heuristik aus _PT_promoteFromPL:176-206 (Single-Source, Extract-not-reimplement).
    # (a) Aufrufbar + bool-Vertrag.
    assert callable(pl.is_pattern_worthy) and callable(pl.worthiness_reasons)
    assert pl.is_pattern_worthy("nichtssagender Freitext ohne Signal") is False
    assert pl.is_pattern_worthy("Eine wiederverwendbare Architektur-Konvention") is True
    # (b) is_pattern_worthy == (worthiness_reasons != []) — die Disjunktion (>=1 Klasse feuert).
    for cand in ("Pattern X", "nothing here", {"text": "Validator Constraint"}, ""):
        assert pl.is_pattern_worthy(cand) == (len(pl.worthiness_reasons(cand)) > 0)
    # (c) Signal-Parity — jede der 5 Klassen feuert isoliert mit ihrem Quell-Keyword (Parity-Anker K-1).
    assert pl.worthiness_reasons("Architektur") == ["arch-keyword"]
    assert pl.worthiness_reasons("Cross-Cutting") == ["cross-cutting"]
    assert pl.worthiness_reasons("Validator") == ["validation-pattern"]
    assert pl.worthiness_reasons("StyleCop SA1") == ["compiler-rule"]
    # has-concrete-example via Datei-Referenz ODER Code-Block (keine Keyword-Klasse).
    assert pl.worthiness_reasons("siehe Foo.cs") == ["has-concrete-example"]
    assert pl.worthiness_reasons("```\ncode\n```") == ["has-concrete-example"]
    # (d) candidate-tolerant (str | dict mit .text/.content) — Konsument _PT_berater_materialize reicht Shapes.
    assert pl.is_pattern_worthy({"content": "generische Konvention"}) is True
    assert pl.is_pattern_worthy({"text": "blah"}) is False


def test_worthiness_wire_promote_and_materialize_call_single_source(tmp_path):
    # K-1 (Vertrag, INV-MAT-5 AUFGELOEST): _PT_promoteFromPL ruft is_pattern_worthy()/worthiness_reasons()
    # statt Inline-Reimpl; _PT_berater_materialize ruft es ECHT (kein worthiness_pending-Fallback-Pass).
    promote = _read_cmd("_PT_promoteFromPL.md")
    materialize = _read_cmd("_PT_berater_materialize.md")
    # promote: Inline-Reimpl ENTFERNT -> Single-Source-Aufruf.
    assert "worthiness_reasons" in promote or "is_pattern_worthy" in promote
    assert "Single-Source" in promote or "KEIN Inline-Reimpl" in promote
    # materialize: echter Aufruf + INV-MAT-5 als aufgeloest markiert (worthiness_pending=false).
    assert "is_pattern_worthy" in materialize
    assert "INV-MAT-5" in materialize
    assert "worthiness_pending: false" in materialize or "worthiness_pending:false" in materialize


# ── Block 6 · GT-C5-02 · AK-10 Stage-7 Verdrahtungs-Verifikation (F4) — quiescenz-gated B-2 ──
def test_stage7_single_pass_quiescence_gated(tmp_path):
    # B-2 (AK-10, INV-PTO-2): die Stage-7-Materialisierungs-Primitiven sind verdrahtet + einstufig:
    #   resolve_vault_root(override) + add_arch einstufig (kein Kandidat-Zwischenschritt, kein
    #   leeres-Verzeichnis-Dedup) + manifest_quiescence-Gate als Library-API VOR Write aufrufbar.
    import importlib
    mq = importlib.import_module("manifest_quiescence")
    # (a) Quiescenz-Gate ist als API aufrufbar (require_quiescent + is_manifest_quiescent + evaluate).
    assert callable(mq.is_manifest_quiescent) and callable(mq.require_quiescent)
    assert callable(mq.evaluate_quiescence)
    # (b) resolve_vault_root override-Pfad (W-486-2): override gewinnt deterministisch, kein globaler resolve_bl_path-Touch.
    assert pl.resolve_vault_root(override=tmp_path) == tmp_path
    # (c) add_arch EINSTUFIG: ein einziger Aufruf materialisiert Datei + Index-Zeile (kein 2-Pass-Kandidat).
    _seed_layer(tmp_path)
    pid, fpath, dedup = pl.add_arch("BE-DOMAIN", "Stage7 Wire", description="einstufig",
                                    vault_root=tmp_path, story="BL-237")
    assert fpath.exists()                                  # Datei direkt da (1 Pass)
    idx = (tmp_path / "Libraries/PatternLibrary/_project/BE-DOMAIN/_index.md")
    assert idx.exists() and pid in idx.read_text(encoding="utf-8")   # Index-Zeile im selben Pass
    # (d) Quiescenz-Gate GREEN auf einem ruhenden (frisch-geschriebenen, kein Fremd-Lock) Manifest:
    #     evaluate_quiescence ohne Fremd-Lock + stabile mtime -> quiescent True (Gate laesst Write zu).
    res = mq.evaluate_quiescence(lock_info=None, mtime_before=100.0, mtime_after=100.0)
    assert res is True or (isinstance(res, tuple) and res[0] is True)


def test_stage7_orchestrate_quiescence_gate_contract(tmp_path):
    # B-2 (Vertrag, AK-10): _PT_orchestrate gatet Stage 7 (Library-Write) auf manifest_quiescence GREEN
    # (INV-PTO-2) und ueberspringt NUR Stage 7 bei BUSY — Stages 1-6/8 laufen read-only weiter.
    t = _read_cmd("_PT_orchestrate.md")
    assert "INV-PTO-2" in t and "Quiescenz" in t
    assert "manifest_quiescence" in t
    assert "Stage 7" in t and ("read-only" in t or "READ-ONLY" in t)


# ── Block 7 · GT-C5-03 · AK-8 Index-Counter-Spalten (F3) B-1 + /_pattern_status SCHREIBT=∅ K-2 ──
def test_append_index_row_counter_columns(tmp_path):
    # B-1 (AK-8, F3): die _index.md-Zeile traegt jetzt usage_count/broken_count/status als eigene
    # Spalten (vorher nur ID|Datei|Kurzbeschreibung). Geburts-Default 0/0/experimental (_COUNTER_DEFAULTS).
    _seed_layer(tmp_path)
    pid, fpath, _ = pl.add_arch("BE-DOMAIN", "Counter Spalten", description="AK-8 Sichtbarkeit",
                                vault_root=tmp_path, story="BL-237")
    idx_txt = (tmp_path / "Libraries/PatternLibrary/_project/BE-DOMAIN/_index.md").read_text(encoding="utf-8")
    # Header traegt die 3 neuen Spalten zusaetzlich zu den unveraenderten ersten 3 (additiv, K-4).
    assert "usage_count" in idx_txt and "broken_count" in idx_txt and "status" in idx_txt
    assert "| ID | Datei | Kurzbeschreibung |" in idx_txt   # erste 3 Spalten unveraendert (Index-Leser tolerant)
    # Daten-Zeile traegt die Geburts-Defaults (0/0/experimental) als Counter-Werte.
    data_row = [l for l in idx_txt.splitlines() if pid in l and "|" in l][0]
    cells = [c.strip() for c in data_row.strip("|").split("|")]
    # | ID | [Datei](Datei) | Beschreibung | usage_count | broken_count | status |
    assert cells[0] == pid
    assert cells[3] == "0" and cells[4] == "0" and cells[5] == "experimental"


def test_pattern_status_readonly_contract_writes_nothing(tmp_path):
    # K-2 (KANARIENVOGEL): /_pattern_status ist STRIKT READ-ONLY (PT-CMD-014, INV-PS-1) —
    # SCHREIBT=∅, KEIN --fix, KEIN Library-Mutate, KEIN zweiter Live-Aggregat-Call. Cmd-Vertrags-Selbsttest.
    t = _read_cmd("_pattern_status.md")
    assert "PT-CMD-014" in t and "INV-PS-1" in t
    assert "READ-ONLY" in t and "DIAGNOSE" in t
    # SCHREIBT=∅ / 0 Schreiboperationen explizit.
    assert "0 Schreiboperationen" in t
    assert "KEIN --fix" in t or "kein `--fix`" in t or "kein --fix" in t.lower()
    # Datenquelle = .report-Slot + Frontmatter-Counter (kein eigener Counter-Kern -> Reuse, DoD-21).
    assert ".report" in t
    assert "rank_by_maturity" in t or "read_counter" in t   # Reuse der pattern_library-Primitiven
    # Mutiert die PatternLibrary NIE.
    assert "Mutiert die PatternLibrary NIE" in t or "mutiert" in t.lower()


# ════════════════════════════════════════════════════════════════════════════
# ══ BL-307 batch_PL1 · RED (TDD) — Index-Schema-Drift-Emitter + Validator + Summary ══
# ════════════════════════════════════════════════════════════════════════════
# WURZEL (Befund 1, AK-1): _append_index_row haengt seine 6-Spalten-Counter-Zeile IMMER an,
# OHNE das Bestands-Header-Schema des Ziel-_index.md zu pruefen (Z255-262). Seed-Indizes tragen
# ein FREMDES 7-Spalten-Schema (| ID | Name | Status | Confidence | Zyklus | Cool | Random |).
# Folge: die neue 6-Spalten-Zeile sitzt unter dem 7-Spalten-Header = column-shift, semantisch korrupt
# (live FE-FORM: 9/13 Zeilen verschoben). Kanon = 6-Spalten-Counter (BL-237 baut darauf).
# Diese Tests sind RED bis PL-307-1/-4/-5 GREEN sind.

# Kanonischer 6-Spalten-Header (BL-237-Counter-Schema) — die Wahrheit, auf die migriert wird.
_CANON_IDX_HEADER = "| ID | Datei | Kurzbeschreibung | usage_count | broken_count | status |"
# Fremdes 7-Spalten-Seed-Schema (Befund 1 case_study: /_PT_arch_init 2026-05-02 + FE-Batch).
_FOREIGN_IDX_HEADER = "| ID | Name | Status | Confidence | Zyklus | Cool | Random |"
_FOREIGN_IDX_SEP = "|----|------|--------|------------|--------|------|--------|"


def _seed_foreign_index(layer_dir: Path, summary: str | None = None, rows=None):
    """Schreibt ein _index.md mit dem FREMDEN 7-Spalten-Seed-Schema (+ optional Summary-Zeile).

    Spiegelt die Live-FE-FORM-Drift: Header = 7 Spalten, Bestands-Zeilen = 7 Zellen.
    """
    idx = layer_dir / "_index.md"
    head = "# BE-DOMAIN Pattern Library\n\n"
    if summary:
        head += summary + "\n\n"
    body = [_FOREIGN_IDX_HEADER, _FOREIGN_IDX_SEP]
    for r in (rows or [
        "| PT-DOM-900 | Bestands Eins | active | 0.9 | 12 | x | r1 |",
        "| PT-DOM-901 | Bestands Zwei | proven | 0.7 |  8 | y | r2 |",
    ]):
        body.append(r)
    idx.write_text(head + "\n".join(body) + "\n", encoding="utf-8")
    return idx


def _idx_data_rows(idx_txt: str):
    """Tabellen-Daten-Zeilen (ohne Header/Separator) als Zellen-Listen."""
    out = []
    for l in idx_txt.splitlines():
        s = l.strip()
        if not s.startswith("|"):
            continue
        if "ID" in s and ("Kurzbeschreibung" in s or "Name" in s):
            continue  # Header
        if set(s.replace("|", "").strip()) <= set("-: "):
            continue  # Separator
        out.append([c.strip() for c in s.strip("|").split("|")])
    return out


# ── PL-307-1 (AK-1) · Emitter-Schema-Detection: Fremd-Header -> migriere-auf-Kanon, dann append ──
def test_append_index_row_migrates_foreign_header_to_canon(tmp_path):
    # RED: _append_index_row erkennt heute das Fremd-Schema NICHT — die neue Zeile sitzt unter dem
    # 7-Spalten-Header (Z255-262). GREEN: bei Fremd-Header wird der Index idempotent auf den
    # 6-Spalten-Kanon migriert (Header ersetzt), DANN die neue Counter-Zeile angehaengt.
    ld = _seed_layer(tmp_path)
    _seed_foreign_index(ld)
    pl._append_index_row("arch", "BE-DOMAIN", "PT-DOM-902", "PT-DOM-902_neu.md",
                         "Neue Drift-Zeile", story=None, vault_root=tmp_path)
    idx_txt = (ld / "_index.md").read_text(encoding="utf-8")
    # Header ist jetzt der Kanon — KEIN Fremd-Header mehr.
    assert _CANON_IDX_HEADER in idx_txt
    assert _FOREIGN_IDX_HEADER not in idx_txt
    # GENAU EIN Tabellen-Header (kein doppelter Append unter Fremd-Tabelle).
    assert idx_txt.count("| ID |") == 1


def test_append_index_row_new_row_schema_aligned_under_foreign(tmp_path):
    # RED: die neue Zeile traegt 6 Counter-Zellen, der Bestands-Header 7 Spalten -> column-shift.
    # GREEN: nach Migration sind ALLE Daten-Zeilen 6 Zellen, die neue Zeile schema-aligned
    # (ID / [Datei](Datei) / Beschreibung / usage_count / broken_count / status).
    ld = _seed_layer(tmp_path)
    _seed_foreign_index(ld)
    pl._append_index_row("arch", "BE-DOMAIN", "PT-DOM-902", "PT-DOM-902_neu.md",
                         "Neue Drift-Zeile", story=None, vault_root=tmp_path)
    idx_txt = (ld / "_index.md").read_text(encoding="utf-8")
    rows = _idx_data_rows(idx_txt)
    # Jede Daten-Zeile hat genau 6 Zellen (Kanon) — keine column-shifted 7er-Zeile mehr.
    assert all(len(r) == 6 for r in rows), f"column-shift: {[len(r) for r in rows]}"
    new = [r for r in rows if r and r[0] == "PT-DOM-902"][0]
    assert new[2] == "Neue Drift-Zeile"        # Kurzbeschreibung in der RICHTIGEN Spalte
    assert new[3] == "0" and new[4] == "0" and new[5] == "experimental"  # Counter-Defaults


def test_append_index_row_foreign_migration_lossless_and_idempotent(tmp_path):
    # RED: Bestands-Zeilen gehen heute beim blinden Append verloren/verschoben. GREEN: die
    # 2 Bestands-IDs ueberleben die Migration (lossless gemappt) + ein 2. Append re-migriert NICHT
    # (idempotent: Header bleibt Kanon, kein erneutes Header-Umschreiben).
    ld = _seed_layer(tmp_path)
    _seed_foreign_index(ld)
    pl._append_index_row("arch", "BE-DOMAIN", "PT-DOM-902", "PT-DOM-902_a.md",
                         "A", story=None, vault_root=tmp_path)
    after_first = (ld / "_index.md").read_text(encoding="utf-8")
    assert "PT-DOM-900" in after_first and "PT-DOM-901" in after_first  # lossless
    pl._append_index_row("arch", "BE-DOMAIN", "PT-DOM-903", "PT-DOM-903_b.md",
                         "B", story=None, vault_root=tmp_path)
    after_second = (ld / "_index.md").read_text(encoding="utf-8")
    assert after_second.count("| ID |") == 1   # immer noch genau ein Kanon-Header (idempotent)
    rows = _idx_data_rows(after_second)
    ids = {r[0] for r in rows if r}
    assert {"PT-DOM-900", "PT-DOM-901", "PT-DOM-902", "PT-DOM-903"} <= ids


# ── PL-307-4 (AK-4) · validate_index_schema: read-only Schema-Sanity (findings, schreibt NICHTS) ──
def test_validate_index_schema_flags_foreign_and_shifted(tmp_path):
    # RED: validate_index_schema existiert noch nicht (greenfield). GREEN: read-only Funktion
    # liefert findings — foreign_header (Header != Kanon) + column_shifted_row (Zellen != 6).
    ld = _seed_layer(tmp_path)
    idx = _seed_foreign_index(ld)
    findings = pl.validate_index_schema(idx)
    kinds = {f["kind"] for f in findings}
    assert "foreign_header" in kinds
    assert "column_shifted_row" in kinds


def test_validate_index_schema_clean_on_canon(tmp_path):
    # GREEN-Pfad: ein frisch von _append_index_row (Neuanlage = Kanon) erzeugter Index ist sauber
    # -> KEINE Schema-findings. (RED bis die Funktion existiert.)
    ld = _seed_layer(tmp_path)
    pl.add_arch("BE-DOMAIN", "Sauber", description="kanonisch geboren", vault_root=tmp_path)
    findings = pl.validate_index_schema(ld / "_index.md")
    assert [f for f in findings if f["kind"] in ("foreign_header", "column_shifted_row")] == []


def test_validate_index_schema_readonly_contract_writes_nothing(tmp_path):
    # K-2-Vorbild (test_pattern_status_readonly_contract): validate_index_schema MUTIERT NICHTS.
    # MD5 vor==nach (read-only). RED bis die Funktion existiert.
    import hashlib
    ld = _seed_layer(tmp_path)
    idx = _seed_foreign_index(ld)
    before = hashlib.md5(idx.read_bytes()).hexdigest()
    pl.validate_index_schema(idx)
    after = hashlib.md5(idx.read_bytes()).hexdigest()
    assert before == after


# ── PL-307-5 (AK-5) · Stale Bootstrap-Summary: Append haelt Summary-Zaehler aktuell ODER markiert pit ──
def test_append_index_row_refreshes_or_marks_stale_summary(tmp_path):
    # Befund 1 (case_study): Seed-Index traegt eine Summary-Zeile ("Patterns: 3+1") die bei 13 Zeilen
    # STALE ist. RED: _append_index_row pflegt sie heute nicht. GREEN (minimaler Vertrag): nach Append
    # spiegelt die Summary die wahre Zeilen-Zahl ODER ist als point-in-time/stale markiert — NIE eine
    # falsche feste Zahl unter der wahren Zeilen-Menge.
    ld = _seed_layer(tmp_path)
    # Fremd-Index mit 2 Bestands-Zeilen + bewusst falscher Summary (behauptet 99 Patterns).
    _seed_foreign_index(ld, summary="Patterns: 99")
    pl._append_index_row("arch", "BE-DOMAIN", "PT-DOM-902", "PT-DOM-902_s.md",
                         "Summary-Probe", story=None, vault_root=tmp_path)
    idx_txt = (ld / "_index.md").read_text(encoding="utf-8")
    data_rows = _idx_data_rows(idx_txt)
    true_count = len(data_rows)  # wahre Zeilen-Zahl nach Append (Migration + neue Zeile)
    # Die falsche feste "99" darf NICHT mehr als Klartext-Wahrheit dastehen, wenn sie != true_count ist:
    has_stale_marker = ("point-in-time" in idx_txt.lower()
                        or "stale" in idx_txt.lower()
                        or "pit" in idx_txt.lower())
    summary_refreshed = f"Patterns: {true_count}" in idx_txt
    assert (summary_refreshed or has_stale_marker) and "Patterns: 99" not in idx_txt


# ══════════════════════════════════════════════════════════════════════════
# ══ BL-307 batch_PL2 · RED — Backfill fm-loser Pattern-Files + Layer-Index-Migration ══
# ══════════════════════════════════════════════════════════════════════════
# Gegen tmp_path-Fixtures (KEIN Live-Library-IO). Quiescenz/Live-Apply ist deploy-gate, NICHT
# Test-Belang. Beide Contracts sind additiv: bestehende Asserts unberuehrt, pattern_library.py GREEN.

# ── PL-307-3 (BE-CORE-FM-Backfill) · fm-LOSE Pattern-Files frontmatter-en (heute migrate-Z1014-Skip) ──
def _seed_fm_less_core_file(layer_dir: Path, pid="PT-CORE-007", title="Frontmatterloses Core-Pattern",
                            body_extra="\n## Pattern\n\n- Eine tragende Regel.\n\n## Beispiel\n\n```\nx\n```\n"):
    """Schreibt ein Pattern-File OHNE YAML-Frontmatter (nur Markdown-Body, beginnend mit ``# {pid} — Titel``).

    Spiegelt die BE-CORE-Drift: Bestands-Files ohne Frontmatter, die migrate() heute am
    ``fm is None -> continue`` (Z1014) skippt. Die ID steckt im Dateinamen + in der H1-Zeile.
    """
    f = layer_dir / f"{pid}_{title.split()[0].lower()}.md"
    f.write_text(f"# {pid} — {title}\n{body_extra}", encoding="utf-8")
    return f


def test_backfill_fm_less_writes_frontmatter_lossless(tmp_path):
    # RED: migrate() skippt fm-lose Files (Z1014 `fm is None -> continue`) -> Frontmatter bleibt aus.
    # GREEN: ein Backfill-Modus (backfill_missing_fm) verarbeitet sie: schreibt additiv YAML-Frontmatter
    #   (id aus Dateiname/H1, layer aus Pfad, status=experimental default), Body UNVERAENDERT (lossless).
    ld = _seed_layer(tmp_path)
    f = _seed_fm_less_core_file(ld, pid="PT-CORE-007")
    body_before = f.read_text(encoding="utf-8")
    assert pl.backfill_missing_fm(scope="arch", vault_root=tmp_path) == 1
    txt = f.read_text(encoding="utf-8")
    # Frontmatter ist jetzt DA (id/layer/status), per read_counter konsumierbar (kein Crash).
    assert txt.startswith("---")
    fm, body = pl._split_fm(txt)
    assert fm is not None
    assert pl._fm_get(fm, "id") == "PT-CORE-007"
    assert pl._fm_get(fm, "layer") == "BE-DOMAIN"
    assert pl._fm_get(fm, "status") == "experimental"
    # Body LOSSLESS: der originale Markdown-Body (inkl. H1 + Pattern-Section) bleibt unangetastet.
    assert "# PT-CORE-007 — Frontmatterloses Core-Pattern" in body
    assert "## Pattern" in body and "Eine tragende Regel." in body
    assert body.rstrip("\n") in body_before.rstrip("\n")


def test_backfill_fm_less_idempotent(tmp_path):
    # RED bis backfill_missing_fm existiert. GREEN: 2. Lauf ist no-op (Frontmatter schon da -> 0).
    ld = _seed_layer(tmp_path)
    _seed_fm_less_core_file(ld, pid="PT-CORE-008")
    assert pl.backfill_missing_fm(scope="arch", vault_root=tmp_path) == 1
    assert pl.backfill_missing_fm(scope="arch", vault_root=tmp_path) == 0   # idempotent


def test_backfill_fm_less_dry_run_writes_nothing(tmp_path):
    # RED bis backfill_missing_fm existiert. GREEN: dry_run=True meldet die Treffer, MUTIERT aber NICHTS.
    import hashlib
    ld = _seed_layer(tmp_path)
    f = _seed_fm_less_core_file(ld, pid="PT-CORE-009")
    before = hashlib.md5(f.read_bytes()).hexdigest()
    n = pl.backfill_missing_fm(scope="arch", vault_root=tmp_path, dry_run=True)
    after = hashlib.md5(f.read_bytes()).hexdigest()
    assert n == 1                       # haette 1 File backfilled
    assert before == after              # aber NICHTS geschrieben (dry-run)


def test_backfill_fm_less_skips_files_with_fm(tmp_path):
    # GREEN-Pfad-Abgrenzung: ein Pattern MIT Frontmatter (add_arch-geboren) wird NICHT erneut
    # angefasst (kein Doppel-FM). RED bis backfill_missing_fm existiert.
    ld = _seed_layer(tmp_path)
    pl.add_arch("BE-DOMAIN", "Hat schon FM", description="d", vault_root=tmp_path)
    # Nur die fm-lose Datei zaehlt als Backfill-Treffer; die fm-volle wird uebersprungen.
    _seed_fm_less_core_file(ld, pid="PT-CORE-010")
    assert pl.backfill_missing_fm(scope="arch", vault_root=tmp_path) == 1


def test_cli_backfill_fm_subcommand(tmp_path):
    # RED: greenfield CLI-Subcommand (z.B. `backfill-fm`). GREEN: CLI ruft backfill_missing_fm.
    ld = _seed_layer(tmp_path)
    _seed_fm_less_core_file(ld, pid="PT-CORE-011")
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "backfill-fm", "--scope", "arch",
         "--vault-root", str(tmp_path)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    f = next(ld.glob("PT-CORE-011*.md"))
    fm, _ = pl._split_fm(f.read_text(encoding="utf-8"))
    assert fm is not None and pl._fm_get(fm, "id") == "PT-CORE-011"


# ── PL-307-2 (Layer-Index-Migration) · Standalone drifted-Index -> Kanon-6-Spalten (idempotent) ──
def test_migrate_index_standalone_foreign_to_canon(tmp_path):
    # RED: greenfield Standalone-Migration (migrate_index existiert noch nicht). GREEN: ein drifteter
    # Layer-Index (7-Spalten-Fremd-Header + verschobene Zeilen) wird auf den Kanon-6-Spalten gebracht —
    # OHNE dass ein Pattern-Add ihn triggert (im Gegensatz zur _append_index_row-In-Place-Migration).
    ld = _seed_layer(tmp_path)
    idx = _seed_foreign_index(ld)
    pl.migrate_index(idx, dry_run=False)
    idx_txt = idx.read_text(encoding="utf-8")
    assert _CANON_IDX_HEADER in idx_txt
    assert _FOREIGN_IDX_HEADER not in idx_txt
    assert idx_txt.count("| ID |") == 1                      # genau ein Kanon-Header
    rows = _idx_data_rows(idx_txt)
    assert all(len(r) == 6 for r in rows), f"column-shift: {[len(r) for r in rows]}"


def test_migrate_index_lossless_ids_and_descriptions(tmp_path):
    # RED bis migrate_index existiert. GREEN: die Bestands-IDs + tragende Beschreibung ueberleben
    # die Migration verlustfrei (Fremd-Zeile -> _migrate_foreign_row-Mapping, reuse batch_PL1).
    ld = _seed_layer(tmp_path)
    idx = _seed_foreign_index(ld)
    pl.migrate_index(idx, dry_run=False)
    rows = _idx_data_rows(idx.read_text(encoding="utf-8"))
    by_id = {r[0]: r for r in rows if r}
    assert {"PT-DOM-900", "PT-DOM-901"} <= set(by_id)        # IDs lossless
    assert by_id["PT-DOM-900"][2] == "Bestands Eins"          # Beschreibung in RICHTIGER Spalte


def test_migrate_index_dry_run_is_default_and_writes_nothing(tmp_path):
    # RED bis migrate_index existiert. GREEN: dry-run ist DEFAULT (kein Arg -> kein Schreiben).
    import hashlib
    ld = _seed_layer(tmp_path)
    idx = _seed_foreign_index(ld)
    before = hashlib.md5(idx.read_bytes()).hexdigest()
    pl.migrate_index(idx)                                    # dry_run default True -> no-op
    after = hashlib.md5(idx.read_bytes()).hexdigest()
    assert before == after


def test_migrate_index_idempotent_on_canon(tmp_path):
    # RED bis migrate_index existiert. GREEN: ein bereits-Kanon-Index wird nicht re-migriert
    # (idempotent: 2. apply-Lauf laesst Header + Zeilen unveraendert).
    import hashlib
    ld = _seed_layer(tmp_path)
    idx = _seed_foreign_index(ld)
    pl.migrate_index(idx, dry_run=False)                     # 1. Lauf migriert
    digest_1 = hashlib.md5(idx.read_bytes()).hexdigest()
    pl.migrate_index(idx, dry_run=False)                     # 2. Lauf -> no-op
    digest_2 = hashlib.md5(idx.read_bytes()).hexdigest()
    assert digest_1 == digest_2


def test_migrate_index_backup_on_apply(tmp_path):
    # RED bis migrate_index existiert. GREEN: ein apply-Lauf legt ein Backup an (Vorbild
    # reconcile_backlog_index) — der Original-Inhalt ist nach der Migration noch wiederherstellbar.
    ld = _seed_layer(tmp_path)
    idx = _seed_foreign_index(ld)
    original = idx.read_text(encoding="utf-8")
    pl.migrate_index(idx, dry_run=False)
    backups = list(ld.glob("_index*.bak*")) + list(ld.glob("*_index.md.bak*")) \
        + list(ld.glob("_index.md.*.bak"))
    assert backups, f"kein Backup angelegt: {[p.name for p in ld.iterdir()]}"
    assert any(_FOREIGN_IDX_HEADER in b.read_text(encoding="utf-8") for b in backups), \
        "Backup traegt nicht den Original-Fremd-Header"
    assert original  # Original-Snapshot existierte


def test_cli_migrate_index_subcommand(tmp_path):
    # RED: greenfield CLI-Subcommand (z.B. `migrate-index`). GREEN: CLI ruft migrate_index;
    # dry-run-default heisst: erst mit --apply (oder Aequivalent) wird geschrieben.
    ld = _seed_layer(tmp_path)
    idx = _seed_foreign_index(ld)
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "migrate-index", "--index", str(idx),
         "--apply", "--vault-root", str(tmp_path)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    idx_txt = idx.read_text(encoding="utf-8")
    assert _CANON_IDX_HEADER in idx_txt and _FOREIGN_IDX_HEADER not in idx_txt


def test_resolve_vault_root_override_wins(tmp_path):
    # BL-374 AK-3/AK-1: explizites override gewinnt (tier-1)
    assert pl.resolve_vault_root(override=str(tmp_path)) == Path(str(tmp_path))


def test_resolve_vault_root_no_override_delegates_to_canonical(monkeypatch, tmp_path):
    # BL-374 AK-1: ohne override delegiert an kanonische resolve_vault_root.py (SSoT) —
    # CLAUDE_VAULT_ROOT (Stufe 1 der kanonischen Kette) schlaegt durch.
    monkeypatch.setenv("CLAUDE_VAULT_ROOT", str(tmp_path))
    assert pl.resolve_vault_root() == Path(str(tmp_path))


def test_resolve_vault_root_no_hardcoded_omnicommand_fallback(monkeypatch, tmp_path):
    # BL-374 AK-1: der hardcoded 'Documents/OmniCommand'-Fallback ist WEG. Ohne env/.vault_root/
    # routing-Match liefert die kanonische Kette ihre cwd-Heuristik (~/Documents/{cwd_name}),
    # NICHT den OmniCommand-Pfad. (RED auf altem Code: der gab den hardcoded OmniCommand-Pfad.)
    monkeypatch.delenv("CLAUDE_VAULT_ROOT", raising=False)
    monkeypatch.delenv("OBSIDIAN_VAULT_PATH", raising=False)
    monkeypatch.chdir(tmp_path)
    result = str(pl.resolve_vault_root()).replace("\\", "/")
    assert result != "C:/Users/Administrator/Documents/OmniCommand"


# ════════════════════════════════════════════════════════════════════════════════════════
# BL-258 batch_1 — Novelty-Exploration-Gegengewicht (rank_by_maturity novelty_slots)
# RED-Tests: novelty_slots-Param + _is_novelty existieren noch NICHT in pattern_library.py.
# Neue Klasse TestNoveltyExploration; bestehende Tests (K-1..K-3/B-1..B-3) unveraendert.
# ════════════════════════════════════════════════════════════════════════════════════════

class TestNoveltyExploration:
    """BL-258 AK-S1/S2/S3/CTX-1 — Novelty-Exploration-Gegengewicht fuer rank_by_maturity."""

    # ── AK-CTX-1: Backwards-Compat (soll GRUEN sein — Default=0 == altes Verhalten) ────

    def test_novelty_default_equals_old_behavior(self):
        # AK-CTX-1: novelty_slots=0 (explizit) und kein novelty_slots-Arg (Default)
        # muessen fuer jede Eingabe bit-identische Ergebnisse liefern.
        # Beweis: novelty_slots=0 ist der neue Default — kein Caller-Change noetig.
        entries = [
            {"id": "A", "usage_count": 10, "broken_count": 1, "confidence": "high"},
            {"id": "B", "usage_count": 3, "broken_count": 0, "confidence": "medium"},
            {"id": "C", "usage_count": 0, "broken_count": 0, "confidence": "low"},
            {"id": "D", "usage_count": 5, "broken_count": 2, "confidence": "high"},
        ]
        result_default = pl.rank_by_maturity(entries, top_n=3)
        result_explicit_zero = pl.rank_by_maturity(entries, top_n=3, novelty_slots=0)
        assert [e["id"] for e in result_default] == [e["id"] for e in result_explicit_zero]

    # ── AK-S1: Novelty-Boost — usage=0-Pattern erscheint mit novelty_slots>0 im Top-N ─

    def test_novelty_boost_lifts_usage0_into_top_n(self):
        # AK-S1: mit novelty_slots=2 werden 2 junge (usage=0/broken=0) Patterns
        # in Top-N aufgenommen, die ohne novelty_slots durch den maturity-Cut verdraengt
        # wuerden (weil 5 reifere Konkurrenten existieren).
        # Ohne novelty_slots wuerden N0_a/N0_b (maturity=0) aus top_n=5 fliegen
        # (P0..P4 belegen alle Slots mit maturity 4..0).
        mature_entries = [
            {"id": f"P{i}", "usage_count": i + 1, "broken_count": 0, "confidence": "low"}
            for i in range(5)  # P0=usage1, P1=usage2, ..., P4=usage5 (maturity 1..5)
        ]
        novelty_entries = [
            {"id": "N0_a", "usage_count": 0, "broken_count": 0, "confidence": "low"},
            {"id": "N0_b", "usage_count": 0, "broken_count": 0, "confidence": "low"},
        ]
        entries = mature_entries + novelty_entries

        # Ohne novelty_slots: N0_a und N0_b landen NICHT in top_n=5 (5 reifere Konkurrenten)
        result_no_novelty = [e["id"] for e in pl.rank_by_maturity(entries, top_n=5)]
        assert "N0_a" not in result_no_novelty and "N0_b" not in result_no_novelty

        # Mit novelty_slots=2: BEIDE jungen Patterns erscheinen im Top-N
        result_with_novelty = [e["id"] for e in pl.rank_by_maturity(entries, top_n=5, novelty_slots=2)]
        assert "N0_a" in result_with_novelty or "N0_b" in result_with_novelty
        # Mindestens 1 Novelty-Pattern im Top-N (2 Slots reserviert)
        novelty_count = sum(1 for pid in result_with_novelty if pid in ("N0_a", "N0_b"))
        assert novelty_count >= 1

    # ── AK-S2: Konfidenz-vs-Reife — Eligibility-Praedikat _is_novelty ───────────────────

    def test_konfidenz_reife_usage0_eligible_broken_not(self):
        # AK-S2: usage=0/broken=0 ist novelty-eligible (ungetestet/neu).
        # usage=0/broken>0 ist NICHT eligible (abgelehnt/broken — Konfidenz-Achse).
        # Beweis via _is_novelty Helper — muss existieren und das Praedikat korrekt ausdruecken.
        assert pl._is_novelty({"usage_count": 0, "broken_count": 0}) is True
        assert pl._is_novelty({"usage_count": 0, "broken_count": 1}) is False
        assert pl._is_novelty({"usage_count": 0, "broken_count": 3}) is False
        # usage>0 ist nicht novelty (bereits erprobt)
        assert pl._is_novelty({"usage_count": 1, "broken_count": 0}) is False

    def test_konfidenz_reife_broken_pattern_excluded_from_novelty_slot(self):
        # AK-S2 (Integration): ein Pattern mit usage=0/broken=1 (abgelehnt) bekommt
        # KEINEN Novelty-Slot, auch wenn novelty_slots>0.
        entries = [
            {"id": f"M{i}", "usage_count": i + 5, "broken_count": 0, "confidence": "low"}
            for i in range(4)  # 4 reife Patterns (maturity 5..8)
        ]
        entries += [
            {"id": "BROKEN_NEW", "usage_count": 0, "broken_count": 1, "confidence": "low"},
            {"id": "CLEAN_NEW", "usage_count": 0, "broken_count": 0, "confidence": "low"},
        ]
        # Mit novelty_slots=1: CLEAN_NEW (usage=0/broken=0) bekommt den Slot,
        # BROKEN_NEW (usage=0/broken=1) NICHT.
        result = [e["id"] for e in pl.rank_by_maturity(entries, top_n=5, novelty_slots=1)]
        assert "CLEAN_NEW" in result
        assert "BROKEN_NEW" not in result

    # ── AK-S3: Diversitaets-Cut — gemischtes Top-N + Auffuellung bei fehlenden Kandidaten ─

    def test_diversity_cut_mixes_mature_and_novelty(self):
        # AK-S3: Top-N mit novelty_slots=m enthaelt sowohl k=top_n-m reife als auch
        # m junge Patterns. len(result) == top_n (kein Leer-Slot, volle Fuehlung).
        entries = [
            {"id": f"MAT{i}", "usage_count": i + 1, "broken_count": 0, "confidence": "low"}
            for i in range(6)  # 6 reife Patterns
        ]
        entries += [
            {"id": "NOV1", "usage_count": 0, "broken_count": 0, "confidence": "low"},
            {"id": "NOV2", "usage_count": 0, "broken_count": 0, "confidence": "low"},
        ]
        result = pl.rank_by_maturity(entries, top_n=5, novelty_slots=2)
        result_ids = [e["id"] for e in result]

        # Top-N-Groesse bleibt 5 (kein Leer-Slot)
        assert len(result_ids) == 5

        # Mindestens 1 reifes Pattern (k=3 Slots fuer Reife)
        mature_in_result = [pid for pid in result_ids if pid.startswith("MAT")]
        assert len(mature_in_result) >= 1

        # Mindestens 1 Novelty-Pattern (m=2 Slots)
        novelty_in_result = [pid for pid in result_ids if pid in ("NOV1", "NOV2")]
        assert len(novelty_in_result) >= 1

    def test_diversity_cut_fills_when_no_novelty_candidates(self):
        # AK-S3: keine Novelty-eligible Patterns vorhanden (alle usage>0 oder broken>0)
        # -> Novelty-Slots mit naechst-reifen aufgefuellt.
        # Kein Leer-Slot; Top-N-Groesse bleibt erhalten.
        entries = [
            {"id": f"M{i}", "usage_count": i + 1, "broken_count": 0, "confidence": "low"}
            for i in range(7)  # alle usage>0 -> keine Novelty-Kandidaten
        ]
        result = pl.rank_by_maturity(entries, top_n=5, novelty_slots=2)
        # Kein Novelty-Kandidat -> Auffuellung mit Reifen -> 5 Eintraege
        assert len(result) == 5
        result_ids = [e["id"] for e in result]
        # Die 5 reifsten (M6..M2, maturity 7..3) sind im Ergebnis
        assert all(pid in result_ids for pid in ("M6", "M5", "M4", "M3", "M2"))
