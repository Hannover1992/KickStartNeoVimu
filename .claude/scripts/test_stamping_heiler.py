"""
test_stamping_heiler.py — BL-343 / batch_PL2 / PL-343-3 (M3, Stage 1, Atomic)

RED-Test-Host fuer den Stamping-Heiler-Write-Back (stamp_manifest_writeback).
Das Primitiv existiert bereits in resolve_format_version.py
(stamp_format_version_lines / read_format_version / resolve_format_version) — was
FEHLT ist der manifest-write-back-WRAPPER: liest ein Manifest von Platte,
stempelt die format_version-Zeile additiv ins Top-Level-Frontmatter und schreibt
es lossless zurueck (idempotent, version=None-safe, dry_run-faehig).

Greenfield: stamping_heiler.py existiert NOCH NICHT -> `import stamping_heiler`
schlaegt fehl -> ImportError = RED fuer alle G1..G5. Bewusst KEIN try/except: der
Import-Fehler IST der RED-Beweis fuer den Wrapper-Ring.

Isolation: KEIN echtes Vault-IO. tmp_path fuer die Manifest-Datei,
resolve_format_version("manifest") wird per monkeypatch auf dem Modul gepinnt
(Writer=Follow, kein eigenes Versions-Literal). MD5 verifiziert die Lossless-
Garantie auf dem Nicht-Stempel-Rest.

Gold-Map (GOLD-Contract PL-343-3):
  G1 ungestempelt -> stamped=True, danach read_format_version==soll
  G2 idempotent: 2x stamp -> 2. Lauf was_already=True, Datei nach 2.==nach 1.
  G3 soll=None (Registry nicht aufloesbar) -> No-Op, kein Crash, Datei unveraendert
  G4 dry_run -> kein Write (Bytes unveraendert), Report stamped-wuerde
  G5 lossless: nicht-format_version-Zeilen (body + andere FM-Felder) byte-identisch
"""
import hashlib
import textwrap
from pathlib import Path

import pytest

# Re-Use des Primitivs (existiert) fuer die Gegen-Probe (read_format_version).
import resolve_format_version as rfv

# Greenfield-Modul: existiert noch nicht -> ImportError = RED fuer G1..G5.
# Bewusst KEIN try/except: der Import-Fehler IST der RED-Beweis fuer den Wrapper.
import stamping_heiler as sh


SOLL = 1  # resolve_format_version("manifest") in den Tests gepinnt.


UNGESTEMPELTES_MANIFEST = textwrap.dedent(
    """\
    ---
    type: manifest
    backlog_counter: 42
    backlog_last_update: "2026-06-13"
    ---

    # Manifest Body

    - BL-343: irgendwas
    """
)


def _write_manifest(tmp_path: Path, text: str = UNGESTEMPELTES_MANIFEST) -> Path:
    p = tmp_path / "manifest.md"
    p.write_text(text, encoding="utf-8")
    return p


def _pin_soll(monkeypatch, soll):
    """resolve_format_version('manifest') auf einen Test-Wert pinnen (kein Vault-IO).

    soll=None simuliert 'Registry nicht aufloesbar' (G3). Writer=Follow:
    der Heiler holt den Wert via diesem Call, kein eigenes Literal.
    """
    monkeypatch.setattr(sh, "resolve_format_version", lambda typ: soll, raising=False)


def _md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _non_stamp_lines(text: str) -> list[str]:
    """Alle Zeilen AUSSER der format_version-Stempel-Zeile (fuer Lossless-Vergleich)."""
    return [ln for ln in text.splitlines() if not ln.strip().startswith("format_version:")]


# ---------------------------------------------------------------------------
# G1 — ungestempelt -> stempelt -> read_format_version == soll
# ---------------------------------------------------------------------------

def test_ungestempelt_wird_gestempelt(tmp_path, monkeypatch):
    """G1: ist==0 + soll!=None -> stamped=True; danach Datei traegt soll."""
    _pin_soll(monkeypatch, SOLL)
    mpath = _write_manifest(tmp_path)

    rep = sh.stamp_manifest_writeback(str(mpath))

    assert rep["stamped"] is True, f"ungestempelt -> stamped=True erwartet, war {rep!r}"
    assert rep["was_already"] is False
    assert rep["version"] == SOLL

    # Gegen-Probe via Bestands-Primitiv: das Manifest traegt jetzt soll.
    fm = mpath.read_text(encoding="utf-8")
    assert rfv.read_format_version(fm) == SOLL, (
        f"nach Stamp muss read_format_version=={SOLL} sein, Datei:\n{fm}"
    )


# ---------------------------------------------------------------------------
# G2 — idempotent: zweiter Lauf aendert nichts (kein Doppel-Stempel)
# ---------------------------------------------------------------------------

def test_idempotent_kein_doppelstempel(tmp_path, monkeypatch):
    """G2: 2x stamp -> 2. Lauf was_already=True; Datei nach 2.==nach 1. (byte-identisch)."""
    _pin_soll(monkeypatch, SOLL)
    mpath = _write_manifest(tmp_path)

    sh.stamp_manifest_writeback(str(mpath))
    nach_1 = mpath.read_text(encoding="utf-8")

    rep2 = sh.stamp_manifest_writeback(str(mpath))
    nach_2 = mpath.read_text(encoding="utf-8")

    assert rep2["was_already"] is True, f"2. Lauf -> was_already=True erwartet, war {rep2!r}"
    assert rep2["stamped"] is False, "bereits gestempelt -> kein erneuter Stamp"
    assert nach_2 == nach_1, "zweiter Lauf darf die Datei NICHT veraendern (idempotent)"
    # Genau EINE format_version-Zeile (kein Doppel-Stempel).
    fv = [ln for ln in nach_2.splitlines() if ln.strip().startswith("format_version:")]
    assert len(fv) == 1, f"genau 1 format_version-Zeile erwartet, fand {fv}"


# ---------------------------------------------------------------------------
# G3 — soll=None (Registry nicht aufloesbar) -> No-Op, KEIN Crash
# ---------------------------------------------------------------------------

def test_soll_none_noop_kein_crash(tmp_path, monkeypatch):
    """G3: resolve gibt None -> No-Op (skipped_reason='no_soll'), Datei unveraendert, kein Crash."""
    _pin_soll(monkeypatch, None)
    mpath = _write_manifest(tmp_path)
    vorher = mpath.read_text(encoding="utf-8")

    # Darf NICHT werfen (Dual-Read-Resilienz, Symmetrie zu version=None-Weglass).
    rep = sh.stamp_manifest_writeback(str(mpath))

    assert rep["stamped"] is False, f"soll=None -> kein Stamp, war {rep!r}"
    assert rep.get("skipped_reason") == "no_soll", (
        f"soll=None -> skipped_reason='no_soll' erwartet, war {rep!r}"
    )
    assert mpath.read_text(encoding="utf-8") == vorher, "soll=None -> Datei byte-unveraendert"


# ---------------------------------------------------------------------------
# G4 — dry_run -> kein Write, Report wie-wuerde
# ---------------------------------------------------------------------------

def test_dry_run_kein_write(tmp_path, monkeypatch):
    """G4: dry_run=True -> Datei-Bytes unveraendert, Report meldet was-wuerde (stamped-wuerde)."""
    _pin_soll(monkeypatch, SOLL)
    mpath = _write_manifest(tmp_path)
    vorher = mpath.read_text(encoding="utf-8")

    rep = sh.stamp_manifest_writeback(str(mpath), dry_run=True)

    assert mpath.read_text(encoding="utf-8") == vorher, "dry_run darf NICHT schreiben"
    assert rep["stamped"] is True, (
        f"dry_run auf ungestempeltem Manifest -> stamped (was-wuerde)=True, war {rep!r}"
    )
    assert rep["was_already"] is False
    assert rep["version"] == SOLL


# ---------------------------------------------------------------------------
# G5 — lossless: Nicht-Stempel-Zeilen byte-identisch nach Stamp (MD5)
# ---------------------------------------------------------------------------

def test_lossless_nur_stempelzeile_neu(tmp_path, monkeypatch):
    """G5: nach Stamp sind alle Zeilen AUSSER der format_version-Zeile byte-identisch.

    MD5 auf dem Nicht-Stempel-Rest (body + andere FM-Felder) muss vorher==nachher sein.
    """
    _pin_soll(monkeypatch, SOLL)
    mpath = _write_manifest(tmp_path)
    vorher = mpath.read_text(encoding="utf-8")

    sh.stamp_manifest_writeback(str(mpath))
    nachher = mpath.read_text(encoding="utf-8")

    rest_vorher = "\n".join(_non_stamp_lines(vorher))
    rest_nachher = "\n".join(_non_stamp_lines(nachher))
    assert _md5(rest_nachher) == _md5(rest_vorher), (
        "Lossless verletzt: Nicht-format_version-Zeilen veraendert.\n"
        f"vorher:\n{rest_vorher}\nnachher:\n{rest_nachher}"
    )
    # Und der Stempel ist tatsaechlich dazugekommen (sonst waere Lossless trivial).
    assert rfv.read_format_version(nachher) == SOLL
