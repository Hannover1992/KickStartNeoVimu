"""
test_truth_gc_health.py — BL-399 batch_2 (M3) RED-Tests

AK-HEALTH-INTEGRATION + AK-SAFETY-GATE: truth_gc als Health-Dimension eingehaengt +
Safety-Class-Gate (NIE auto fuer GC-Member).

RED-Phase: die Integration existiert NOCH NICHT in health_orchestrate.py -> Tests schlagen
FEHL bis GREEN-Worker die Aenderungen implementiert. Insbesondere:
  - health_registry.yaml fehlen die 5 GC-Member (truth_dup/truth_stale/truth_orphan/
    truth_format_drift/truth_view_bloat)
  - generate_health_report haengt truth_gc.scan NOCH NICHT ein
  - detected_drifts-Erweiterung fuer GC-Dimension fehlt

Isolation: KEIN echter Vault-IO. tmp_path fuer Registry + Truth-Korpus.
Monkeypatch: health_orchestrate.find_health_registry_yaml + resolve_vault_root.
Muster 1:1 analog test_health_orchestrate.py (G-pinning, tmp-Korpus, _pin_registry).
"""
import textwrap
import json
from pathlib import Path

import pytest
import health_orchestrate as ho


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures + Helfer
# ──────────────────────────────────────────────────────────────────────────────

# Die 5 GC-Member die nach AK-HEALTH-INTEGRATION in health_registry.yaml stehen MUESSEN.
# drift_typ-Mapping: 1:1 aus Spec T-HI-3.
GC_MEMBER_SPECS = {
    "truth_dup":          "truth_duplicate",
    "truth_stale":        "truth_stale",
    "truth_orphan":       "truth_orphan",
    "truth_format_drift": "truth_format_drift",
    "truth_view_bloat":   "truth_view_bloat",
}

# GC-Member safety_class darf NIE auto sein (AK-SAFETY-GATE T-SG-1).
_FORBIDDEN_GC_AUTO = {"auto"}
_ALLOWED_GC_SAFETY = {"lock", "hil"}

# Minimale Registry mit den 5 GC-Membern (nur fuer Health-Integration-Tests ohne echtes YAML).
GC_REGISTRY_YAML = textwrap.dedent("""\
    health_members:
      truth_dup:
        drift_typ: truth_duplicate
        detector: "truth_gc.py duplicates --dry-run"
        healer: null
        safety_class: lock
        status: wired
      truth_stale:
        drift_typ: truth_stale
        detector: "truth_gc.py stale --dry-run"
        healer: null
        safety_class: hil
        status: wired
      truth_orphan:
        drift_typ: truth_orphan
        detector: "truth_gc.py orphaned --dry-run"
        healer: null
        safety_class: hil
        status: wired
      truth_format_drift:
        drift_typ: truth_format_drift
        detector: "truth_gc.py format_regression --dry-run"
        healer: null
        safety_class: lock
        status: wired
      truth_view_bloat:
        drift_typ: truth_view_bloat
        detector: "truth_gc.py accumulation --dry-run"
        healer: null
        safety_class: hil
        status: wired
""")

# Registry mit GC-Membern + einem standard-Member (kein blanket-all Test).
GC_REGISTRY_PLUS_STANDARD = textwrap.dedent("""\
    health_members:
      stamping_heiler:
        drift_typ: missing_format_version
        detector: "resolve_format_version.read_format_version (ist==0)"
        healer: "resolve_format_version.stamp_format_version_lines (+ write-back)"
        safety_class: auto
        status: wired
      truth_dup:
        drift_typ: truth_duplicate
        detector: "truth_gc.py duplicates --dry-run"
        healer: null
        safety_class: lock
        status: wired
      truth_stale:
        drift_typ: truth_stale
        detector: "truth_gc.py stale --dry-run"
        healer: null
        safety_class: hil
        status: wired
      truth_orphan:
        drift_typ: truth_orphan
        detector: "truth_gc.py orphaned --dry-run"
        healer: null
        safety_class: hil
        status: wired
      truth_format_drift:
        drift_typ: truth_format_drift
        detector: "truth_gc.py format_regression --dry-run"
        healer: null
        safety_class: lock
        status: wired
      truth_view_bloat:
        drift_typ: truth_view_bloat
        detector: "truth_gc.py accumulation --dry-run"
        healer: null
        safety_class: hil
        status: wired
""")


def _write_gc_registry(tmp_path: Path, text: str = GC_REGISTRY_YAML) -> Path:
    reg = tmp_path / "health_registry.yaml"
    reg.write_text(text, encoding="utf-8")
    return reg


def _pin_registry(monkeypatch, reg_path):
    """Loader auf Test-Registry pinnen (kein Vault-IO). reg_path=None -> Datei fehlt."""
    monkeypatch.setattr(ho, "find_health_registry_yaml", lambda: reg_path)


def _build_truth_corpus_with_duplicate(tmp_path: Path) -> Path:
    """tmp-Truth-Korpus: BL-Ordner mit truths/, zwei Atome mit gleichem content_hash (-> duplicates)."""
    bl_root = tmp_path / "BL-fake-dup"
    truths_dir = bl_root / "truths"
    truths_dir.mkdir(parents=True)

    dup_fm = textwrap.dedent("""\
        ---
        local_id: T-dup-1
        type: truth
        content_hash: AABBCC001122
        status: active
        truth_grade: A
        referenced_by: []
        edges: []
        ---
        # Duplizierter Truth
        Inhalt fuer Duplikat-Test.
    """)
    (truths_dir / "T-dup-1.md").write_text(dup_fm, encoding="utf-8")
    (truths_dir / "T-dup-2.md").write_text(
        dup_fm.replace("T-dup-1", "T-dup-2"), encoding="utf-8"
    )
    return bl_root


def _build_truth_corpus_with_orphan(tmp_path: Path) -> Path:
    """tmp-Truth-Korpus: Atom ohne referenced_by UND ohne edges (-> orphaned)."""
    bl_root = tmp_path / "BL-fake-orphan"
    truths_dir = bl_root / "truths"
    truths_dir.mkdir(parents=True)

    orphan_fm = textwrap.dedent("""\
        ---
        local_id: T-orphan-1
        type: truth
        content_hash: DEADBEEF0000
        status: active
        truth_grade: B
        referenced_by: []
        edges: []
        ---
        # Verwaister Truth
        Kein eingehender noch ausgehender Verweis.
    """)
    (truths_dir / "T-orphan-1.md").write_text(orphan_fm, encoding="utf-8")

    # Zweiter Atom MIT referenced_by (soll NICHT orphaned sein — Kontroll-Truth).
    ref_fm = textwrap.dedent("""\
        ---
        local_id: T-ref-1
        type: truth
        content_hash: CAFEBABE1111
        status: active
        truth_grade: A
        referenced_by:
          - BL-001
        edges: []
        ---
        # Referenzierter Truth
        Wird von BL-001 referenziert.
    """)
    (truths_dir / "T-ref-1.md").write_text(ref_fm, encoding="utf-8")
    return bl_root


def _build_truth_corpus_with_referenced_orphan(tmp_path: Path) -> Path:
    """tmp-Truth-Korpus: Atom ohne referenced_by UND ohne edges (-> orphaned) +
    Atom MIT referenced_by (-> INV-MIG-12: darf NICHT archiviert werden)."""
    bl_root = tmp_path / "BL-fake-inv-mig"
    truths_dir = bl_root / "truths"
    truths_dir.mkdir(parents=True)

    orphan_fm = textwrap.dedent("""\
        ---
        local_id: T-isolated-1
        type: truth
        content_hash: ISOLATEDAABB
        status: active
        truth_grade: C
        referenced_by: []
        edges: []
        ---
        # Isolierter Truth (kein Verweis — orphaned)
    """)
    (truths_dir / "T-isolated-1.md").write_text(orphan_fm, encoding="utf-8")

    referenced_fm = textwrap.dedent("""\
        ---
        local_id: T-referenced-2
        type: truth
        content_hash: REFERENCED22
        status: contradicted
        truth_grade: B
        referenced_by:
          - BL-010
          - BL-020
        edges: []
        ---
        # Referenzierter contradicted Truth
        Darf NICHT still archiviert werden (INV-MIG-12).
    """)
    (truths_dir / "T-referenced-2.md").write_text(referenced_fm, encoding="utf-8")
    return bl_root


def _build_fake_vault(tmp_path: Path, monkeypatch, registry_yaml: str = GC_REGISTRY_PLUS_STANDARD) -> Path:
    """tmp-Vault mit ungepintem Manifest + GC-Registry; resolve_vault_root + Registry gepinnt."""
    vault = tmp_path / "vault"
    vault.mkdir()
    reg = vault / "health_registry.yaml"
    reg.write_text(registry_yaml, encoding="utf-8")
    _pin_registry(monkeypatch, reg)
    monkeypatch.setattr(ho, "resolve_vault_root", lambda: vault, raising=False)
    # Ungestempeltes Manifest (Gen-0, kein format_version -> missing_format_version Drift).
    manifest = vault / "_manifest.md"
    manifest.write_text("---\ntype: manifest\nbacklog_counter: 1\n---\n\n# body\n", encoding="utf-8")
    return vault


# ──────────────────────────────────────────────────────────────────────────────
# AK-HEALTH-INTEGRATION Tests (T-HI-1 .. T-HI-5)
# ──────────────────────────────────────────────────────────────────────────────

class TestAkHealthIntegration:
    """AK-HEALTH-INTEGRATION: truth_gc.scan eingehaengt, 5 GC-drift_typen in detected_drifts,
    drift-typ-gematcht (kein blanket-all), report-only Default unangetastet."""

    def test_hi1_dup_befund_erzeugt_truth_dup_member(self, tmp_path, monkeypatch):
        """T-HI-1: tmp-Korpus mit Dup-Befund -> heal_recommendations enthaelt member='truth_dup',
        drift='truth_duplicate'.

        RED-Erwartung: generate_health_report haengt truth_gc.scan NICHT ein -> kein GC-drift
        in detected_drifts -> 'truth_dup' fehlt in heal_recommendations -> AssertionError.
        """
        vault = _build_fake_vault(tmp_path, monkeypatch, GC_REGISTRY_PLUS_STANDARD)
        # GC-Corpus: Duplikat-Truth-Paar (gleicher content_hash -> GC findet duplicates).
        gc_root = _build_truth_corpus_with_duplicate(tmp_path)

        # Nach Integration: generate_health_report MUSS gc_roots-Parameter akzeptieren
        # ODER auto-discovery via Vault-Struktur. Wir testen den erwarteten Integrations-API:
        # generate_health_report(vault_root, gc_roots=[gc_root]).
        report = ho.generate_health_report(vault, gc_roots=[gc_root])

        recs = report.get("heal_recommendations", [])
        members_in_recs = {r.get("member") for r in recs}
        drifts_in_recs = {r.get("drift") for r in recs}

        assert "truth_dup" in members_in_recs, (
            f"T-HI-1: 'truth_dup'-Member muss bei Dup-Befund in heal_recommendations erscheinen. "
            f"Gefunden: {members_in_recs}"
        )
        assert "truth_duplicate" in drifts_in_recs, (
            f"T-HI-1: drift='truth_duplicate' muss in heal_recommendations erscheinen. "
            f"Gefunden: {drifts_in_recs}"
        )

    def test_hi2_drift_typ_gematcht_nicht_blanket_all(self, tmp_path, monkeypatch):
        """T-HI-2: ein einzelner orphaned-Befund loest GENAU truth_orphan aus, NICHT alle 5 GC-Member.

        BL-338-Prinzip: kein blanket-all — nur der drift-typ-passende Member erscheint.
        RED-Erwartung: ohne Integration keine GC-drifts -> keine truth_*-Member -> aber
        wenn Integration da waere: muesste selektiv sein. Test prueft BEIDE Seiten:
        (1) orphan-Befund loest truth_orphan aus, (2) truth_dup/stale/format/bloat erscheinen NICHT.
        """
        vault = _build_fake_vault(tmp_path, monkeypatch, GC_REGISTRY_PLUS_STANDARD)
        gc_root = _build_truth_corpus_with_orphan(tmp_path)

        report = ho.generate_health_report(vault, gc_roots=[gc_root])

        recs = report.get("heal_recommendations", [])
        gc_members_in_recs = {r.get("member") for r in recs
                              if r.get("member", "").startswith("truth_")}

        # GENAU truth_orphan soll erscheinen (orphaned-Atom vorhanden).
        assert "truth_orphan" in gc_members_in_recs, (
            f"T-HI-2: orphaned-Befund muss 'truth_orphan' auslösen. "
            f"GC-Members in recs: {gc_members_in_recs}"
        )
        # kein blanket-all: truth_dup, truth_stale, truth_format_drift, truth_view_bloat
        # sollen NICHT erscheinen (kein passender Befund im Korpus).
        unexpected = gc_members_in_recs - {"truth_orphan"}
        assert not unexpected, (
            f"T-HI-2: BL-338 verletzt — blanket-all statt drift-typ-gematcht: "
            f"unerwartete GC-Member {unexpected} ohne passenden Befund"
        )

    def test_hi3_5_gc_member_in_real_registry(self):
        """T-HI-3: die echte health_registry.yaml enthaelt alle 5 GC-Member mit korrektem drift_typ.

        Laedt die echte Registry (kein tmp, kein pin) und prueft die 5 GC-Member-Namen + drift_typ.
        RED-Erwartung: die 5 Member fehlen in der aktuellen health_registry.yaml -> fehlschlagen.
        """
        members = ho.load_health_registry()
        for member_name, expected_drift_typ in GC_MEMBER_SPECS.items():
            assert member_name in members, (
                f"T-HI-3: GC-Member '{member_name}' fehlt in health_registry.yaml "
                f"(erwartet drift_typ='{expected_drift_typ}')"
            )
            entry = members[member_name]
            actual_drift = entry.get("drift_typ")
            assert actual_drift == expected_drift_typ, (
                f"T-HI-3: Member '{member_name}' hat drift_typ='{actual_drift}', "
                f"erwartet '{expected_drift_typ}'"
            )

    def test_hi4_report_only_kein_gc_heal(self, tmp_path, monkeypatch):
        """T-HI-4: plan_heal(report, 'report-only') -> [] auch wenn GC-Drifts vorhanden.

        INV-HEALTH-1: report-only Default ist strukturell unangetastet (keine Auto-Heal-Action).
        RED-Erwartung: ohne Integration schlaegt generate_health_report(gc_roots=...) fehl.
        """
        vault = _build_fake_vault(tmp_path, monkeypatch, GC_REGISTRY_YAML)
        gc_root = _build_truth_corpus_with_duplicate(tmp_path)

        report = ho.generate_health_report(vault, gc_roots=[gc_root])
        plan = ho.plan_heal(report, mode="report-only")

        assert plan == [], (
            f"T-HI-4: plan_heal('report-only') muss [] liefern auch mit GC-Drifts, war {plan}"
        )

    def test_hi5_gc_member_detector_form(self, tmp_path, monkeypatch):
        """T-HI-5: jeder GC-Member detector-String enthaelt 'truth_gc' und '--dry-run'.

        Spec-Anforderung: detector-Form 'truth_gc.py <subcommand> --dry-run'.
        RED-Erwartung: die GC-Member fehlen in der echten Registry -> fehlschlagen.
        """
        real_members = ho.load_health_registry()
        for member_name in GC_MEMBER_SPECS:
            assert member_name in real_members, (
                f"T-HI-5: GC-Member '{member_name}' fehlt in health_registry.yaml"
            )
            detector = real_members[member_name].get("detector") or ""
            assert "truth_gc" in detector, (
                f"T-HI-5: Member '{member_name}' detector='{detector}' enthaelt nicht 'truth_gc'"
            )
            assert "--dry-run" in detector, (
                f"T-HI-5: Member '{member_name}' detector='{detector}' enthaelt nicht '--dry-run'"
            )


# ──────────────────────────────────────────────────────────────────────────────
# AK-SAFETY-GATE Tests (T-SG-1 .. T-SG-4)
# ──────────────────────────────────────────────────────────────────────────────

class TestAkSafetyGate:
    """AK-SAFETY-GATE: GC-Member NIE auto; plan_heal gated; truth_gc read-only; INV-MIG-12."""

    def test_sg1_gc_member_nie_auto_in_real_registry(self):
        """T-SG-1: jeder der 5 GC-Member hat safety_class in {lock, hil}, KEINER hat 'auto'.

        Auto = destruktiv-faehig; Truth-GC-Member heilen Truth-Atome -> immer Mensch-Freigabe
        oder vault_lock. Auto ist VERBOTEN.
        RED-Erwartung: GC-Member fehlen in echter Registry -> fehlschlagen.
        """
        real_members = ho.load_health_registry()
        for member_name in GC_MEMBER_SPECS:
            assert member_name in real_members, (
                f"T-SG-1: GC-Member '{member_name}' fehlt in health_registry.yaml"
            )
            sc = real_members[member_name].get("safety_class")
            assert sc in _ALLOWED_GC_SAFETY, (
                f"T-SG-1: GC-Member '{member_name}' hat safety_class='{sc}' — "
                f"GC-Member duerfen NIE 'auto' haben (erlaubt: {_ALLOWED_GC_SAFETY})"
            )

    def test_sg1_gc_member_nie_auto_in_tmp_registry(self, tmp_path, monkeypatch):
        """T-SG-1 (tmp): GC-Registry-Fixture konsistent — alle 5 GC-Member lock/hil.

        Validiert die eigene Fixture: der GREEN-Worker muss diese Klassifizierung einhalten.
        Dieser Test ist GRUEN-SOFORT (Fixture-Self-Check) — beabsichtigt. Er validiert
        die Spec-Anforderung strukturell auch bei fehlendem echtem Registry-File.
        """
        reg = _write_gc_registry(tmp_path, GC_REGISTRY_YAML)
        _pin_registry(monkeypatch, reg)
        members = ho.load_health_registry()
        for member_name in GC_MEMBER_SPECS:
            assert member_name in members, (
                f"T-SG-1-tmp: GC-Member '{member_name}' fehlt in Fixture-Registry"
            )
            sc = members[member_name].get("safety_class")
            assert sc in _ALLOWED_GC_SAFETY, (
                f"T-SG-1-tmp: Fixture GC-Member '{member_name}' hat safety_class='{sc}' — "
                f"GC-Member duerfen NIE 'auto' haben"
            )

    def test_sg2_plan_heal_gc_gating_synthetisch(self):
        """T-SG-2: plan_heal('heal') gated lock-GC-Member -> needs_lock=True, hil -> needs_freigabe=True.

        SYNTHETISCH (kein Vault-IO): handgebauter Report mit GC-Member-Recommendations.
        Prueft das Gating direkt ohne Integration. Dieser Test ist design-GRUEN (plan_heal
        existiert und gatet bereits korrekt nach safety_class) — er dokumentiert die Gate-
        Semantik fuer GC-Member explizit und bleibt stabil wenn Integration kommt.
        """
        report = {
            "per_artifact": {},
            "heal_recommendations": [
                {"member": "truth_dup", "drift": "truth_duplicate", "safety_class": "lock"},
                {"member": "truth_orphan", "drift": "truth_orphan", "safety_class": "hil"},
                {"member": "truth_stale", "drift": "truth_stale", "safety_class": "hil"},
            ],
        }
        plan = ho.plan_heal(report, mode="heal")
        assert plan, f"T-SG-2: heal-Plan muss Eintraege liefern, war leer"

        for eintrag in plan:
            sc = eintrag.get("safety_class")
            member = eintrag.get("member")
            # Kein auto-execute fuer GC-Member (keiner sollte execute==True haben).
            assert eintrag.get("execute") is not True, (
                f"T-SG-2: GC-Member '{member}' (safety_class='{sc}') darf NICHT auto-execute. "
                f"Eintrag: {eintrag}"
            )
            if sc == "lock":
                assert eintrag.get("needs_lock") is True, (
                    f"T-SG-2: lock-GC-Member '{member}' muss needs_lock=True tragen: {eintrag}"
                )
            elif sc == "hil":
                assert eintrag.get("needs_freigabe") is True, (
                    f"T-SG-2: hil-GC-Member '{member}' muss needs_freigabe=True tragen: {eintrag}"
                )

    def test_sg2_plan_heal_gc_gating_mit_integration(self, tmp_path, monkeypatch):
        """T-SG-2 (Integration): plan_heal('heal') mit GC-Drifts aus echtem scan -> GC-Member gated.

        RED-Erwartung: generate_health_report haengt truth_gc NICHT ein -> kein GC-drift
        in Report -> truth_*-Member nicht in heal_recommendations -> Test schlaegt fehl
        (keine GC-Member zum Gaten gefunden).
        """
        vault = _build_fake_vault(tmp_path, monkeypatch, GC_REGISTRY_YAML)
        gc_root = _build_truth_corpus_with_duplicate(tmp_path)

        report = ho.generate_health_report(vault, gc_roots=[gc_root])
        plan = ho.plan_heal(report, mode="heal")

        gc_plan_entries = [e for e in plan if e.get("member", "").startswith("truth_")]
        assert gc_plan_entries, (
            f"T-SG-2-int: plan_heal(heal) mit GC-Dup-Befund muss mind. einen truth_*-Eintrag liefern. "
            f"Gesamt-Plan: {plan}"
        )
        for eintrag in gc_plan_entries:
            sc = eintrag.get("safety_class")
            member = eintrag.get("member")
            assert sc in _ALLOWED_GC_SAFETY, (
                f"T-SG-2-int: GC-Plan-Eintrag '{member}' safety_class='{sc}' — "
                f"muss lock/hil sein, nie auto"
            )
            assert eintrag.get("execute") is not True, (
                f"T-SG-2-int: GC-Member '{member}' darf NICHT auto-execute: {eintrag}"
            )

    def test_sg3_truth_gc_ist_read_only(self, tmp_path):
        """T-SG-3: truth_gc.scan() veraendert KEINE Datei (read-only-Roundtrip).

        Erstellt tmp-Korpus, merkt Hashes aller Dateien, ruft scan() auf, prueft Byte-Identitaet.
        Dieser Test sollte GRUEN sein (truth_gc wurde in batch_1 bereits read-only gebaut) —
        er dient als Nicht-Regress-Guard: GREEN-Worker darf truth_gc NICHT mit Write-Logik
        veraendern.
        """
        import hashlib
        import truth_gc

        gc_root = _build_truth_corpus_with_orphan(tmp_path)
        truths_dir = gc_root / "truths"

        # Vor-Hashes aller Truth-Dateien.
        def file_hashes(directory: Path) -> dict:
            return {
                p.name: hashlib.md5(p.read_bytes()).hexdigest()
                for p in sorted(directory.glob("*.md"))
                if p.is_file()
            }

        before = file_hashes(truths_dir)
        assert before, "T-SG-3: Fixture muss mind. eine Truth-Datei enthalten"

        # scan() ausfuehren.
        _report = truth_gc.scan([gc_root])

        after = file_hashes(truths_dir)
        assert before == after, (
            f"T-SG-3: truth_gc.scan() veraenderte Dateien — NICHT read-only! "
            f"Vorher: {list(before.keys())} | Nachher: {list(after.keys())}"
        )

    def test_sg4_inv_mig12_orphaned_befund_schema(self, tmp_path):
        """T-SG-4 (INV-MIG-12): orphaned-Befund-Eintrag traegt Vorbedingung referenced_by leer.

        truth_gc._scan_orphaned definiert 'orphaned' als: referenced_by leer UND edges leer.
        Ein Truth MIT referenced_by darf NICHT in orphaned erscheinen (referenz-blindes
        Archivieren verboten — INV-MIG-12).
        Dieser Test validiert die GC-Sonde-Semantik direkt (kein Health-Integration-IO).
        Wird GRUEN wenn truth_gc.py korrekt implementiert (batch_1 bereits fertig) — Guard
        gegen Regression durch batch_2-Aenderungen.
        """
        import truth_gc

        gc_root = _build_truth_corpus_with_referenced_orphan(tmp_path)
        report = truth_gc.scan([gc_root])

        orphaned = report.get("orphaned", [])
        orphaned_ids = {e.get("local_id") for e in orphaned}

        # T-isolated-1 hat referenced_by=[] und edges=[] -> MUSS in orphaned erscheinen.
        assert "T-isolated-1" in orphaned_ids, (
            f"T-SG-4: T-isolated-1 (keine Refs, keine Edges) muss orphaned sein. "
            f"orphaned_ids={orphaned_ids}"
        )
        # T-referenced-2 hat referenced_by=[BL-010, BL-020] -> darf NICHT orphaned sein (INV-MIG-12).
        assert "T-referenced-2" not in orphaned_ids, (
            f"T-SG-4: INV-MIG-12 verletzt — T-referenced-2 mit referenced_by=[BL-010, BL-020] "
            f"darf NICHT orphaned sein (referenz-blindes Archivieren verboten!). "
            f"orphaned_ids={orphaned_ids}"
        )

    def test_sg4_inv_mig12_schema_hat_referenced_by_feld(self, tmp_path):
        """T-SG-4b (INV-MIG-12): orphaned-Befund-dict traegt 'reason' mit Vorbedingungs-Nennung.

        Der Befund-Schema (aus _befund()) muss die Vorbedingung 'referenced_by leer' im
        reason-String nachweisbar machen, damit die gated Heilung referenz-bewusst arbeiten kann.
        """
        import truth_gc

        gc_root = _build_truth_corpus_with_orphan(tmp_path)
        report = truth_gc.scan([gc_root])

        orphaned = report.get("orphaned", [])
        assert orphaned, "T-SG-4b: Fixture muss mind. einen orphaned Befund liefern"

        for befund in orphaned:
            reason = befund.get("reason", "")
            assert "referenced_by" in reason or "no referenced_by" in reason, (
                f"T-SG-4b: orphaned-Befund-reason '{reason}' nennt 'referenced_by' nicht — "
                f"INV-MIG-12-Vorbedingung nicht im Befund-Schema nachweisbar. befund={befund}"
            )


# ──────────────────────────────────────────────────────────────────────────────
# Integrations-API-Pruefung (Schnittstellen-Vertrag fuer GREEN-Worker)
# ──────────────────────────────────────────────────────────────────────────────

class TestIntegrationApiContract:
    """Prueft den erwarteten Integrations-API-Vertrag fuer den GREEN-Worker.

    Diese Tests definieren WIE generate_health_report die GC-Dimension einhaengt —
    das ist die API-Spec die GREEN implementieren muss. Alle schlagen RED fehl
    (generate_health_report akzeptiert noch kein gc_roots-Argument).
    """

    def test_generate_health_report_akzeptiert_gc_roots_param(self, tmp_path, monkeypatch):
        """generate_health_report(vault, gc_roots=[...]) akzeptiert gc_roots als keyword-Arg.

        RED: TypeError weil gc_roots-Parameter fehlt in der aktuellen Signatur.
        GREEN-Erwartung: Signatur wird zu generate_health_report(vault_root, gc_roots=None).
        """
        vault = _build_fake_vault(tmp_path, monkeypatch)
        gc_root = _build_truth_corpus_with_orphan(tmp_path)

        # Darf KEINEN TypeError werfen; gc_roots=[] (leer) == wie ohne GC.
        report = ho.generate_health_report(vault, gc_roots=[])
        assert isinstance(report, dict), "generate_health_report muss dict liefern"

    def test_generate_health_report_gc_roots_leer_unveraendert(self, tmp_path, monkeypatch):
        """generate_health_report(vault, gc_roots=[]) verhalt sich wie bisher (kein GC-Befund).

        Rueckwaertskompatibilitaet: kein gc_roots -> keine GC-drifts, bestehender
        format_version-Scan unveraendert (DoD-6).
        """
        vault = _build_fake_vault(tmp_path, monkeypatch)

        report_ohne_gc = ho.generate_health_report(vault)
        report_mit_leer = ho.generate_health_report(vault, gc_roots=[])

        # Beide Reports sollten keine GC-Member in heal_recommendations enthalten.
        for report in (report_ohne_gc, report_mit_leer):
            recs = report.get("heal_recommendations", [])
            gc_recs = [r for r in recs if r.get("member", "").startswith("truth_")]
            assert not gc_recs, (
                f"generate_health_report ohne GC-Befund darf keine truth_*-Empfehlungen liefern: {gc_recs}"
            )

    def test_report_detected_drifts_enthaelt_gc_drifts(self, tmp_path, monkeypatch):
        """After Integration: detected_drifts im Report enthaelt GC-drift_typen wenn Befunde da.

        RED: generate_health_report kennt gc_roots noch nicht -> kein GC-drift in detected_drifts.
        GREEN: per_artifact oder ein gc_summary-Feld enthaelt die GC-dimension-drifts.
        """
        vault = _build_fake_vault(tmp_path, monkeypatch, GC_REGISTRY_PLUS_STANDARD)
        gc_root = _build_truth_corpus_with_duplicate(tmp_path)

        report = ho.generate_health_report(vault, gc_roots=[gc_root])

        # Nach Integration: der Report muss GC-drifts sichtbar machen.
        # Mindestens: heal_recommendations enthaelt truth_dup-Entry.
        recs = report.get("heal_recommendations", [])
        gc_drift_typs = {r.get("drift") for r in recs if r.get("member", "").startswith("truth_")}

        assert "truth_duplicate" in gc_drift_typs, (
            f"test_report_detected_drifts: 'truth_duplicate' drift fehlt in Report nach Integration. "
            f"GC-drifts in recs: {gc_drift_typs}"
        )
