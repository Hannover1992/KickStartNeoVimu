"""test_bl256_materialization.py — BL-256 AK-S2/S3/S4 pytest-Assertions.

AK-S2: Bootstrap idempotent, DomainLibrary + FactoringLibrary angelegt.
AK-S3: Alle 4 Libraries/_index.md befuellt + lesbar (>= 1 Index-Zeile, 6-Spalten).
AK-S4: lifecycle(pfad=1) -> usage_count > 0, Status-Feld vorhanden.

Vault-Strategie:
- AK-S2 Idempotenz-Tests via tmp_path (kein Vault-Mutation-Seiteneffekt).
- AK-S3 Verifikation gegen ECHTEN Vault (nach Live-Bootstrap AK-S2-Deliverable).
- AK-S4 Maturity-Transition via tmp_path (isoliert + deterministisch).
"""
import json
import sys
from pathlib import Path

import pytest

# Pattern_library liegt im selben Verzeichnis wie diese Testdatei.
_SCRIPTS = Path(__file__).parent
sys.path.insert(0, str(_SCRIPTS))

import pattern_library as pl

REAL_VAULT = Path(r"C:\Users\hanno\Documents\Work\Wissen\Berechtigung\OmniCommand\OmniCommand")


# ── Hilfsfunktionen ──────────────────────────────────────────────────────────

def _count_data_rows(index_path: Path) -> int:
    """Zaehlt Daten-Zeilen (nicht Header, nicht Separator) in einer _index.md-Tabelle."""
    if not index_path.exists():
        return 0
    rows = 0
    for line in index_path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("|") and not set(s).issubset(set("| -:")):
            # Kein Separator (nur Pipes, Leerzeichen, Bindestriche, Doppelpunkte)
            # aber pruefen ob es kein reiner Header ist (enthaelt mindestens 1 alphanum)
            cells = [c.strip() for c in s.split("|") if c.strip()]
            # Header-Zeile enthaelt Worte wie "ID", "Datei" etc. — wir zaehlen NUR Zeilen
            # die NICHT den kanonischen Header darstellen
            if cells and cells[0] not in ("ID", "id"):
                rows += 1
    return rows


def _has_6col_data_row(index_path: Path) -> bool:
    """Prueft ob >= 1 Daten-Zeile mit exakt 6 Zellen (W-DOM-4 Schema) existiert."""
    if not index_path.exists():
        return False
    for line in index_path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.split("|") if c.strip()]
        # Separator-Zeilen (nur - und :) ueberspringen
        if all(set(c).issubset(set("-: ")) for c in cells):
            continue
        # Header-Zeile ("ID | Datei | ...") ueberspringen
        if cells and cells[0] in ("ID", "id"):
            continue
        if len(cells) == 6:
            return True
    return False


# ── AK-S2: Bootstrap-Tests (tmp_path — idempotent, kein echter Vault) ────────

class TestAkS2Bootstrap:
    """Bootstrap legt DomainLibrary + FactoringLibrary an (created=True),
    und ist idempotent (2. Lauf created=False, kein Doppel-Seed)."""

    def test_bootstrap_domain_creates_index(self, tmp_path):
        """Erster Bootstrap domain: _index.md wird angelegt."""
        result = pl.bootstrap_library("domain", vault_root=str(tmp_path))
        assert result["created"] is True
        assert result["scope"] == "domain"
        assert result["library"] == "DomainLibrary"
        idx = Path(result["index_path"])
        assert idx.exists(), f"_index.md fehlt: {idx}"

    def test_bootstrap_factoring_creates_index(self, tmp_path):
        """Erster Bootstrap factoring: _index.md wird angelegt."""
        result = pl.bootstrap_library("factoring", vault_root=str(tmp_path))
        assert result["created"] is True
        assert result["scope"] == "factoring"
        assert result["library"] == "FactoringLibrary"
        idx = Path(result["index_path"])
        assert idx.exists(), f"_index.md fehlt: {idx}"

    def test_bootstrap_domain_idempotent(self, tmp_path):
        """2. Bootstrap domain-Run: created=False, kein Doppel-Seed."""
        pl.bootstrap_library("domain", vault_root=str(tmp_path))
        result2 = pl.bootstrap_library("domain", vault_root=str(tmp_path))
        assert result2["created"] is False, "2. Run muss created=False liefern (Idempotenz)"

    def test_bootstrap_factoring_idempotent(self, tmp_path):
        """2. Bootstrap factoring-Run: created=False, kein Doppel-Seed."""
        pl.bootstrap_library("factoring", vault_root=str(tmp_path))
        result2 = pl.bootstrap_library("factoring", vault_root=str(tmp_path))
        assert result2["created"] is False, "2. Run muss created=False liefern (Idempotenz)"

    def test_bootstrap_domain_no_double_seed(self, tmp_path):
        """Kein Doppel-Seed nach 2 Runs: exakt 1 DOM-*.md im Layer-Dir."""
        pl.bootstrap_library("domain", vault_root=str(tmp_path))
        pl.bootstrap_library("domain", vault_root=str(tmp_path))
        ld = pl._layer_dir("domain", "BE-DOMAIN", str(tmp_path))
        seeds = sorted(ld.glob("DOM-*.md"))
        assert len(seeds) == 1, f"Erwartet 1 Seed, gefunden: {len(seeds)}"

    def test_bootstrap_domain_factoring_both(self, tmp_path):
        """bootstrap_domain_factoring() legt beide Libraries in einem Aufruf an."""
        res = pl.bootstrap_domain_factoring(vault_root=str(tmp_path))
        assert "domain" in res
        assert "factoring" in res
        assert res["domain"]["created"] is True
        assert res["factoring"]["created"] is True

    def test_bootstrap_both_idempotent(self, tmp_path):
        """bootstrap_domain_factoring() 2x: beide created=False."""
        pl.bootstrap_domain_factoring(vault_root=str(tmp_path))
        res2 = pl.bootstrap_domain_factoring(vault_root=str(tmp_path))
        assert res2["domain"]["created"] is False
        assert res2["factoring"]["created"] is False

    def test_bootstrap_invalid_scope_raises(self, tmp_path):
        """Scope != domain|factoring -> ValueError (W-VAL-1)."""
        with pytest.raises(ValueError):
            pl.bootstrap_library("arch", vault_root=str(tmp_path))

    def test_bootstrap_real_vault_domain_created(self):
        """AK-S2 Deliverable: ECHTER Vault — DomainLibrary existiert nach Bootstrap."""
        if not REAL_VAULT.exists():
            pytest.skip("Echter Vault nicht erreichbar")
        # Bootstrap ist idempotent — created kann True oder False sein (1. oder n. Run)
        result = pl.bootstrap_library("domain", vault_root=str(REAL_VAULT))
        # Deliverable-Assertion: Verzeichnis + _index.md existieren IMMER nach Bootstrap
        ld = pl._layer_dir("domain", "BE-DOMAIN", str(REAL_VAULT))
        assert ld.exists(), "DomainLibrary/_project/BE-DOMAIN/ fehlt"
        idx = ld / "_index.md"
        assert idx.exists(), "DomainLibrary/_project/BE-DOMAIN/_index.md fehlt"

    def test_bootstrap_real_vault_factoring_created(self):
        """AK-S2 Deliverable: ECHTER Vault — FactoringLibrary existiert nach Bootstrap."""
        if not REAL_VAULT.exists():
            pytest.skip("Echter Vault nicht erreichbar")
        pl.bootstrap_library("factoring", vault_root=str(REAL_VAULT))
        ld = pl._layer_dir("factoring", "BE-DOMAIN", str(REAL_VAULT))
        assert ld.exists(), "FactoringLibrary/_project/BE-DOMAIN/ fehlt"
        idx = ld / "_index.md"
        assert idx.exists(), "FactoringLibrary/_project/BE-DOMAIN/_index.md fehlt"


# ── AK-S3: Verifikation — ECHTER Vault — alle 4 _index.md befuellt ──────────

class TestAkS3Verification:
    """Alle 4 Libraries/{X}Library/_index.md existieren + lesbar + >= 1 Index-Zeile (6-Spalten)."""

    def _skip_if_no_vault(self):
        if not REAL_VAULT.exists():
            pytest.skip("Echter Vault nicht erreichbar")

    def test_pattern_library_index_exists_and_readable(self):
        """PatternLibrary hat mind. eine _index.md die lesbar ist."""
        self._skip_if_no_vault()
        # PatternLibrary hat mehrere _index.md (Root + COMMANDS-Layer)
        pl_root = REAL_VAULT / "Libraries" / "PatternLibrary"
        all_idx = list(pl_root.rglob("_index.md"))
        assert len(all_idx) > 0, "PatternLibrary: keine _index.md gefunden"
        for idx in all_idx:
            content = idx.read_text(encoding="utf-8")
            assert len(content) > 0, f"Leere _index.md: {idx}"

    def test_semantic_library_index_exists_and_readable(self):
        """SemanticLibrary hat _index.md die lesbar und befuellt ist."""
        self._skip_if_no_vault()
        sl_idx = REAL_VAULT / "Libraries" / "SemanticLibrary" / "_index.md"
        assert sl_idx.exists(), f"SemanticLibrary/_index.md fehlt: {sl_idx}"
        content = sl_idx.read_text(encoding="utf-8")
        assert len(content) > 0, "SemanticLibrary/_index.md ist leer"

    def test_domain_library_index_exists_and_readable(self):
        """DomainLibrary/_project/BE-DOMAIN/_index.md existiert + befuellt."""
        self._skip_if_no_vault()
        dl_idx = REAL_VAULT / "Libraries" / "DomainLibrary" / "_project" / "BE-DOMAIN" / "_index.md"
        assert dl_idx.exists(), f"DomainLibrary/_index.md fehlt: {dl_idx}"
        content = dl_idx.read_text(encoding="utf-8")
        assert len(content) > 0, "DomainLibrary/_index.md ist leer"

    def test_factoring_library_index_exists_and_readable(self):
        """FactoringLibrary/_project/BE-DOMAIN/_index.md existiert + befuellt."""
        self._skip_if_no_vault()
        fl_idx = REAL_VAULT / "Libraries" / "FactoringLibrary" / "_project" / "BE-DOMAIN" / "_index.md"
        assert fl_idx.exists(), f"FactoringLibrary/_index.md fehlt: {fl_idx}"
        content = fl_idx.read_text(encoding="utf-8")
        assert len(content) > 0, "FactoringLibrary/_index.md ist leer"

    def test_domain_library_has_6col_data_row(self):
        """DomainLibrary _index.md enthaelt >= 1 Daten-Zeile mit 6 Spalten (W-DOM-4)."""
        self._skip_if_no_vault()
        dl_idx = REAL_VAULT / "Libraries" / "DomainLibrary" / "_project" / "BE-DOMAIN" / "_index.md"
        assert _has_6col_data_row(dl_idx), f"Keine 6-Spalten-Daten-Zeile in {dl_idx}"

    def test_factoring_library_has_6col_data_row(self):
        """FactoringLibrary _index.md enthaelt >= 1 Daten-Zeile mit 6 Spalten (W-DOM-4)."""
        self._skip_if_no_vault()
        fl_idx = REAL_VAULT / "Libraries" / "FactoringLibrary" / "_project" / "BE-DOMAIN" / "_index.md"
        assert _has_6col_data_row(fl_idx), f"Keine 6-Spalten-Daten-Zeile in {fl_idx}"

    def test_domain_index_contains_seed_id(self):
        """DomainLibrary _index.md enthaelt den Bootstrap-Seed DOM-DOM-001."""
        self._skip_if_no_vault()
        dl_idx = REAL_VAULT / "Libraries" / "DomainLibrary" / "_project" / "BE-DOMAIN" / "_index.md"
        content = dl_idx.read_text(encoding="utf-8")
        assert "DOM-DOM-001" in content, "Seed-Pattern DOM-DOM-001 nicht im Index"

    def test_factoring_index_contains_seed_id(self):
        """FactoringLibrary _index.md enthaelt den Bootstrap-Seed FAC-DOM-001."""
        self._skip_if_no_vault()
        fl_idx = REAL_VAULT / "Libraries" / "FactoringLibrary" / "_project" / "BE-DOMAIN" / "_index.md"
        content = fl_idx.read_text(encoding="utf-8")
        assert "FAC-DOM-001" in content, "Seed-Pattern FAC-DOM-001 nicht im Index"

    def test_validate_index_schema_domain(self):
        """DomainLibrary _index.md hat kein Foreign-Schema (validate_index_schema liefert [])."""
        self._skip_if_no_vault()
        dl_idx = REAL_VAULT / "Libraries" / "DomainLibrary" / "_project" / "BE-DOMAIN" / "_index.md"
        findings = pl.validate_index_schema(dl_idx)
        schema_errors = [f for f in findings if f.get("kind") == "foreign_header"]
        assert schema_errors == [], f"Foreign-Header in DomainLibrary _index.md: {schema_errors}"


# ── AK-S4: Maturity-Tracking (tmp_path — isoliert + deterministisch) ─────────

class TestAkS4Maturity:
    """lifecycle(pfad=1) inkrementiert usage_count und kann Status-Transition ausloesen."""

    def _bootstrap_and_get_pid(self, tmp_path, scope="domain") -> tuple:
        """Hilfsfunktion: Bootstrap + liefere (pid, seed_path)."""
        result = pl.bootstrap_library(scope, vault_root=str(tmp_path))
        return result["seed_id"], Path(result["seed_path"])

    def test_lifecycle_increments_usage_count(self, tmp_path):
        """lifecycle pfad=1 -> usage_count steigt von 0 auf 1."""
        pid, fpath = self._bootstrap_and_get_pid(tmp_path)
        assert fpath.exists(), f"Seed-Datei fehlt: {fpath}"
        counter_before = pl.read_counter(fpath)
        assert counter_before["usage_count"] == 0

        result = pl.lifecycle(pid, pfad=1, scope="domain", vault_root=str(tmp_path))
        assert result.get("error") is None, f"lifecycle error: {result}"
        assert result["usage_count"] == 1
        assert result["maturity"] == 1

    def test_lifecycle_usage_count_monoton(self, tmp_path):
        """Mehrfache lifecycle pfad=1 Calls -> usage_count steigt monoton."""
        pid, fpath = self._bootstrap_and_get_pid(tmp_path)
        for expected in range(1, 4):
            res = pl.lifecycle(pid, pfad=1, scope="domain", vault_root=str(tmp_path))
            assert res["usage_count"] == expected, f"Erwartet {expected}, got {res['usage_count']}"

    def test_lifecycle_status_transition_to_active(self, tmp_path):
        """Nach 5 lifecycle pfad=1 Calls: Status wechselt experimental -> active (THRESH_ACTIVE=5)."""
        pid, fpath = self._bootstrap_and_get_pid(tmp_path)
        for _ in range(5):
            res = pl.lifecycle(pid, pfad=1, scope="domain", vault_root=str(tmp_path))
        assert res["usage_count"] == 5
        assert res["status"] == "active", f"Status nach 5 Calls erwartet 'active', got {res['status']!r}"

    def test_lifecycle_persists_to_file(self, tmp_path):
        """lifecycle schreibt usage_count zurueck in das Pattern-File (Frontmatter)."""
        pid, fpath = self._bootstrap_and_get_pid(tmp_path)
        pl.lifecycle(pid, pfad=1, scope="domain", vault_root=str(tmp_path))
        counter = pl.read_counter(fpath)
        assert counter["usage_count"] == 1, "usage_count nicht in Datei persistiert"

    def test_lifecycle_real_vault_dom_seed(self):
        """AK-S4 Real-Vault: DOM-DOM-001 hat usage_count > 0 (nach Live-lifecycle-Call)."""
        if not REAL_VAULT.exists():
            pytest.skip("Echter Vault nicht erreichbar")
        seed_path = (REAL_VAULT / "Libraries" / "DomainLibrary" / "_project" / "BE-DOMAIN"
                     / "DOM-DOM-001_DomainLibrary_Seed.md")
        assert seed_path.exists(), "DOM-DOM-001 Seed fehlt im echten Vault"
        counter = pl.read_counter(seed_path)
        # Nach AK-S4-Deliverable-Lauf (lifecycle wurde bereits ausgefuehrt) muss usage_count > 0
        assert counter["usage_count"] > 0, (
            f"usage_count={counter['usage_count']} — lifecycle wurde noch nicht ausgefuehrt "
            f"(AK-S4 Deliverable: py -3 pattern_library.py lifecycle DOM-DOM-001 --pfad 1 --scope domain)"
        )

    def test_lifecycle_factoring_seed(self, tmp_path):
        """lifecycle funktioniert auch fuer factoring-scope."""
        pid, fpath = self._bootstrap_and_get_pid(tmp_path, scope="factoring")
        result = pl.lifecycle(pid, pfad=1, scope="factoring", vault_root=str(tmp_path))
        assert result.get("error") is None, f"lifecycle error: {result}"
        assert result["usage_count"] == 1
