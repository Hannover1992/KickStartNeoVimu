"""
test_wikilink_materializer.py — RED-Worker BL-450 batch_1 Stage 1

Tests: K-WM-1..7 (Link-Format, Idempotenz, Content-Loss-Schutz, Non-Destruktivitaet)

Ziel-Modul: wikilink_materializer.py (EXISTIERT NOCH NICHT -> alle Tests MUESSEN fehlschlagen)
Konvention: pytest, test_-Prefix (NC-6), Fixtures via tmp_path (Stufe 1 Laserpointer)

BL-450 Blueprint Kap. 6 (K-WM-1..7), Kap. 4.2
Konstanten: WIKILINK_SECTION_HEADER, WIKILINK_TEMPLATE (OQ-2-Mitigation, Kap. 4.2)
"""
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# K-WM-1: build_wikilink — erzeugt WIKILINK_TEMPLATE-konformen Link
# ---------------------------------------------------------------------------

def test_wm1_build_wikilink_uses_wikilink_template(tmp_path):
    """K-WM-1: build_wikilink() erzeugt Link der dem WIKILINK_TEMPLATE entspricht."""
    from wikilink_materializer import build_wikilink, WIKILINK_TEMPLATE  # type: ignore[import]

    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    dst_dir = vault_root / "BL-TEST" / "2_Model" / "truths"
    dst_dir.mkdir(parents=True)
    dst_path = dst_dir / "atom-002.md"
    dst_path.touch()

    link = build_wikilink(dst_atom_path=dst_path, vault_root=vault_root, label="Atom 002")

    # Muss [[...]] enthalten
    assert "[[" in link and "]]" in link, f"build_wikilink Ergebnis ist kein [[wikilink]]: {link!r}"
    # Muss den relativen Vault-Pfad enthalten (kein absoluter Pfad)
    rel = str(dst_path.relative_to(vault_root))
    assert rel.replace("\\", "/") in link.replace("\\", "/"), (
        f"Relativer Vault-Pfad fehlt im Link: {link!r}"
    )
    # Label muss vorkommen
    assert "Atom 002" in link, f"Label fehlt im generierten Link: {link!r}"


# ---------------------------------------------------------------------------
# K-WM-2: has_wikilink_section — erkennt vorhandenen WIKILINK_SECTION_HEADER
# ---------------------------------------------------------------------------

def test_wm2_has_wikilink_section_detects_existing_header():
    """K-WM-2: has_wikilink_section() gibt True zurueck wenn WIKILINK_SECTION_HEADER im Body."""
    from wikilink_materializer import has_wikilink_section, WIKILINK_SECTION_HEADER  # type: ignore[import]

    body_with_section = f"# Atom\n\nEtwas Text.\n\n{WIKILINK_SECTION_HEADER}\n- Verwandt: [[link|Label]]\n"
    body_without_section = "# Atom\n\nNur Text, keine Kanten-Sektion.\n"

    assert has_wikilink_section(body_with_section) is True
    assert has_wikilink_section(body_without_section) is False


# ---------------------------------------------------------------------------
# K-WM-3: get_existing_wikilinks — extrahiert korrekte Ziel-Links aus Body
# ---------------------------------------------------------------------------

def test_wm3_get_existing_wikilinks_extracts_link_targets():
    """K-WM-3: get_existing_wikilinks() extrahiert alle [[link]]-Ziele aus dem Kanten-Block."""
    from wikilink_materializer import get_existing_wikilinks, WIKILINK_SECTION_HEADER  # type: ignore[import]

    body = (
        "# Atom\n\nEtwas Text.\n\n"
        f"{WIKILINK_SECTION_HEADER}\n"
        "- Verwandt: [[BL-100/2_Model/truths/atom-A.md|Label A]]\n"
        "- Verwandt: [[BL-200/2_Model/truths/atom-B.md|Label B]]\n"
    )

    links = get_existing_wikilinks(body)

    assert "BL-100/2_Model/truths/atom-A.md" in links
    assert "BL-200/2_Model/truths/atom-B.md" in links
    assert len(links) == 2


# ---------------------------------------------------------------------------
# K-WM-4: append_wikilinks — schreibt 0 Links wenn alle bereits vorhanden
# ---------------------------------------------------------------------------

def test_wm4_append_wikilinks_returns_zero_when_all_links_present(tmp_path):
    """K-WM-4: append_wikilinks() schreibt 0 neue Links wenn alle Links bereits im Kanten-Block."""
    from wikilink_materializer import append_wikilinks, WIKILINK_SECTION_HEADER  # type: ignore[import]

    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    dst_dir = vault_root / "BL-DST" / "2_Model" / "truths"
    dst_dir.mkdir(parents=True)
    dst_path = dst_dir / "atom-dst.md"
    dst_path.touch()

    # Atom mit bereits vorhandener Sektion und Link
    rel = "BL-DST/2_Model/truths/atom-dst.md"
    existing_body = (
        "# Atom\n\nText.\n\n"
        f"{WIKILINK_SECTION_HEADER}\n"
        f"- Verwandt: [[{rel}|Dst Label]]\n"
    )
    atom_path = tmp_path / "atom-src.md"
    atom_path.write_text(f"---\nid: NS.src\n---\n{existing_body}", encoding="utf-8")

    edges = [{"rel": "relates_to", "ziel": "NS.atom-dst", "dst_path": str(dst_path)}]
    written = append_wikilinks(atom_path=atom_path, edges=edges, vault_root=vault_root)

    assert written == 0, f"Doppel-Write-Schutz verletzt: {written} Links geschrieben statt 0"


# ---------------------------------------------------------------------------
# K-WM-5: append_wikilinks — haengt Links unter WIKILINK_SECTION_HEADER an
# ---------------------------------------------------------------------------

def test_wm5_append_wikilinks_appends_under_section_header(tmp_path):
    """K-WM-5: append_wikilinks() schreibt neuen Link unter WIKILINK_SECTION_HEADER im Atom-Body."""
    from wikilink_materializer import append_wikilinks, WIKILINK_SECTION_HEADER  # type: ignore[import]

    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    dst_dir = vault_root / "BL-DST" / "2_Model" / "truths"
    dst_dir.mkdir(parents=True)
    dst_path = dst_dir / "atom-dst.md"
    dst_path.touch()

    # Atom ohne Kanten-Sektion
    atom_path = tmp_path / "atom-src.md"
    original_body = "# Atom Src\n\nEtwas Inhalt.\n"
    atom_path.write_text(f"---\nid: NS.src\n---\n{original_body}", encoding="utf-8")

    edges = [{"rel": "relates_to", "ziel": "NS.atom-dst", "dst_path": str(dst_path)}]
    written = append_wikilinks(atom_path=atom_path, edges=edges, vault_root=vault_root)

    assert written == 1
    result_content = atom_path.read_text(encoding="utf-8")
    assert WIKILINK_SECTION_HEADER in result_content, (
        f"WIKILINK_SECTION_HEADER fehlt im Ergebnis-Content"
    )
    assert "[[" in result_content and "]]" in result_content, (
        "Kein [[wikilink]] im Ergebnis-Content gefunden"
    )


# ---------------------------------------------------------------------------
# K-WM-6: Body-Content oberhalb des Kanten-Blocks bleibt unveraendert (Non-Destruktivitaet)
# ---------------------------------------------------------------------------

def test_wm6_append_wikilinks_preserves_existing_body_content(tmp_path):
    """K-WM-6: append_wikilinks() veraendert Body-Content oberhalb des Kanten-Blocks NICHT (NFR N5)."""
    from wikilink_materializer import append_wikilinks  # type: ignore[import]

    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    dst_dir = vault_root / "BL-DST" / "2_Model" / "truths"
    dst_dir.mkdir(parents=True)
    dst_path = dst_dir / "atom-new.md"
    dst_path.touch()

    original_body = (
        "# Wichtiger Atom-Titel\n\n"
        "Erster Absatz mit wichtigem Inhalt.\n\n"
        "## Abschnitt\n\n"
        "Weiterer Inhalt der NICHT veraendert werden darf.\n"
    )
    atom_path = tmp_path / "atom-src.md"
    atom_path.write_text(f"---\nid: NS.src\n---\n{original_body}", encoding="utf-8")

    edges = [{"rel": "relates_to", "ziel": "NS.atom-new", "dst_path": str(dst_path)}]
    append_wikilinks(atom_path=atom_path, edges=edges, vault_root=vault_root)

    result_content = atom_path.read_text(encoding="utf-8")
    # Original-Body-Text muss vollstaendig erhalten bleiben
    assert "Erster Absatz mit wichtigem Inhalt." in result_content, (
        "Content-Loss: Erster Absatz fehlt nach append_wikilinks"
    )
    assert "Weiterer Inhalt der NICHT veraendert werden darf." in result_content, (
        "Content-Loss: Zweiter Absatz fehlt nach append_wikilinks"
    )
    assert "Wichtiger Atom-Titel" in result_content, (
        "Content-Loss: Titel fehlt nach append_wikilinks"
    )


# ---------------------------------------------------------------------------
# K-WM-7: main() mit --vault missing_path -> exit code 2
# ---------------------------------------------------------------------------

def test_wm7_main_with_missing_vault_exits_2(tmp_path):
    """K-WM-7: main() gibt exit-Code 2 zurueck wenn --vault auf nicht-existierenden Pfad zeigt."""
    from wikilink_materializer import main  # type: ignore[import]

    missing = str(tmp_path / "no-such-vault")
    result = main(["--vault", missing])

    assert result == 2, f"Erwartet exit 2 fuer fehlendem Vault-Pfad, bekam {result}"
