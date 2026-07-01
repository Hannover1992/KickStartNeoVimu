"""
test_wikilink_materialize_pass.py — RED-Worker BL-450 AC-2

Tests: main() als echter idempotenter Materialisierungs-Pass.
Aktuell: main() ist ein STUB (zaehlt nur atoms_with_sections, schreibt NIE).
-> Alle 4 Tests MUESSEN fehlschlagen (RED).

Ziel-Semantik (GREEN-Impl):
  main(["--vault", str(vault), "--dry-run"])  -> wuerde_schreiben > 0
  main(["--vault", str(vault)])               -> Atom-Body enthaelt [[ziel]] fuer jede edges:-Zeile
  Zweiter main()-Aufruf                       -> KEINE Duplikate (idempotent)
  Bestehender Body-Text                       -> unveraendert (non-destructive)
  edges: als String-Liste                     -> kein Crash, sinnvolle Materialisierung

edges:-Frontmatter-Format (aus truth_schema.py / BL-450 Wissen):
  edges:
    - rel: relates_to
      ziel: "NS-B.W2"
  ODER String-Liste:
  edges:
    - "NS-B.W7"
"""
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Hilfsfunktion: Atom-Datei mit YAML-Frontmatter erzeugen
# ---------------------------------------------------------------------------

def _make_atom(directory: Path, name: str, frontmatter: str, body: str = "") -> Path:
    """Schreibt eine Atom-.md-Datei mit YAML-Frontmatter und Body."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    content = f"---\n{frontmatter}---\n{body}"
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Test 1: main() materialisiert [[wikilinks]] in Atom-Body aus edges:-Frontmatter
# ---------------------------------------------------------------------------

def test_main_materializes_body_wikilinks(tmp_path):
    """AC-2: main() liest edges:-Frontmatter und schreibt [[ziel]]-Links in Atom-Body.

    AKTUELL STUB -> schreibt nichts -> RED.
    """
    from wikilink_materializer import main, WIKILINK_SECTION_HEADER  # type: ignore[import]

    vault = tmp_path / "vault"
    vault.mkdir()

    # Ziel-Atome anlegen (damit dst_path aufgeloest werden kann)
    dst_dir = vault / "NS-B" / "truths"
    dst_dir.mkdir(parents=True)
    dst_a = dst_dir / "W2.md"
    dst_b = dst_dir / "W7.md"
    dst_c = dst_dir / "W9.md"
    dst_a.write_text("---\nid: NS-B.W2\n---\n", encoding="utf-8")
    dst_b.write_text("---\nid: NS-B.W7\n---\n", encoding="utf-8")
    dst_c.write_text("---\nid: NS-B.W9\n---\n", encoding="utf-8")

    # Quell-Atom mit 3 edges:-Eintraegen (dict-Form, kanonisch)
    src_dir = vault / "NS-A" / "truths"
    src_atom = _make_atom(
        src_dir,
        "W-Gesamt.md",
        frontmatter=(
            "type: truth\n"
            "id: NS-A.W-Gesamt\n"
            "local_id: W-Gesamt\n"
            "edges:\n"
            f"  - rel: relates_to\n"
            f"    ziel: NS-B.W2\n"
            f"    dst_path: {str(dst_a).replace(chr(92), '/')}\n"
            f"  - rel: relates_to\n"
            f"    ziel: NS-B.W7\n"
            f"    dst_path: {str(dst_b).replace(chr(92), '/')}\n"
            f"  - rel: relates_to\n"
            f"    ziel: NS-B.W9\n"
            f"    dst_path: {str(dst_c).replace(chr(92), '/')}\n"
        ),
        body="# W-Gesamt\n\nQuelle fuer alle W-Wahrheiten.\n",
    )

    # --- Dry-run muss > 0 wuerde-schreiben melden ---
    # (Stub gibt 0 aus, weil er atoms_with_sections zaehlt, nicht edges -> TEST-SIGNAL implizit
    # durch den fehlenden [[..]] im Body nach dem echten Write-Lauf unten.)

    # --- Write-Lauf: main() ohne --dry-run ---
    exit_code = main(["--vault", str(vault)])
    assert exit_code == 0, f"main() endete mit exit_code={exit_code}"

    result = src_atom.read_text(encoding="utf-8")

    # AC-2: Obsidian-sichtbare [[wikilinks]] muessen im Body stehen
    assert "[[" in result and "]]" in result, (
        "Kein [[wikilink]] im Body materialisiert — main() ist noch STUB (AC-2 unerfuellt)"
    )
    assert WIKILINK_SECTION_HEADER in result, (
        f"WIKILINK_SECTION_HEADER '{WIKILINK_SECTION_HEADER}' fehlt im Body nach main()"
    )

    # Alle 3 Ziel-IDs oder deren Pfad-Fragmente muessen irgendwie referenziert sein
    # (flexible: entweder [[NS-B.W2]] oder [[NS-B/truths/W2.md|...]])
    for ziel_hint in ("W2", "W7", "W9"):
        assert ziel_hint in result, (
            f"Kante zu {ziel_hint} fehlt im materialisierten Body"
        )


# ---------------------------------------------------------------------------
# Test 2: Idempotenz — zweiter main()-Lauf erzeugt KEINE Duplikate
# ---------------------------------------------------------------------------

def test_idempotent_rerun(tmp_path):
    """AC-2 Idempotenz: zweiter main()-Lauf fuegt keine Duplikate hinzu.

    AKTUELL STUB -> schreibt beim ersten Lauf schon nichts -> Idempotenz-Test
    faellt durch weil erster Lauf nichts materialisiert hat (keine [[Links]] vorhanden).
    RED aus anderem Grund als Test 1, aber RED bleibt.
    """
    from wikilink_materializer import main, WIKILINK_SECTION_HEADER  # type: ignore[import]

    vault = tmp_path / "vault"
    vault.mkdir()

    dst_dir = vault / "NS-B" / "truths"
    dst_dir.mkdir(parents=True)
    dst_path = dst_dir / "W5.md"
    dst_path.write_text("---\nid: NS-B.W5\n---\n", encoding="utf-8")

    src_dir = vault / "NS-A" / "truths"
    src_atom = _make_atom(
        src_dir,
        "W-Quelle.md",
        frontmatter=(
            "type: truth\n"
            "id: NS-A.W-Quelle\n"
            "local_id: W-Quelle\n"
            "edges:\n"
            f"  - rel: relates_to\n"
            f"    ziel: NS-B.W5\n"
            f"    dst_path: {str(dst_path).replace(chr(92), '/')}\n"
        ),
        body="# W-Quelle\n\nEin Atom.\n",
    )

    # Erster Write-Lauf
    main(["--vault", str(vault)])
    content_after_first = src_atom.read_text(encoding="utf-8")

    # Vorbedingung fuer Idempotenz-Pruefung: erster Lauf muss etwas geschrieben haben
    assert "[[" in content_after_first, (
        "Erster main()-Lauf hat keine [[Links]] geschrieben — STUB noch aktiv (RED)"
    )

    # Zweiter Write-Lauf
    main(["--vault", str(vault)])
    content_after_second = src_atom.read_text(encoding="utf-8")

    # Datei darf sich beim zweiten Lauf nicht veraendern
    assert content_after_first == content_after_second, (
        "Idempotenz verletzt: zweiter main()-Lauf veraenderte Atom-Inhalt (Duplikate?)"
    )

    # Konkret: nur 1 Vorkommen des Abschnitts-Headers
    assert content_after_second.count(WIKILINK_SECTION_HEADER) == 1, (
        f"WIKILINK_SECTION_HEADER erscheint {content_after_second.count(WIKILINK_SECTION_HEADER)}x "
        f"— Duplikat-Sektion nach zweitem Lauf"
    )


# ---------------------------------------------------------------------------
# Test 3: Bestehender Body-Text bleibt unveraendert (non-destructive)
# ---------------------------------------------------------------------------

def test_non_destructive_body(tmp_path):
    """AC-2 Non-Destruktivitaet: main() veraendert Body-Text oberhalb des wikilink-Abschnitts nicht.

    AKTUELL STUB -> schreibt nichts -> Body bleibt unveraendert -> scheinbar GRUEN,
    ABER der Test prueft AUCH ob [[Links]] vorhanden sind (AC-2), was beim Stub fehlt -> RED.
    """
    from wikilink_materializer import main, WIKILINK_SECTION_HEADER  # type: ignore[import]

    vault = tmp_path / "vault"
    vault.mkdir()

    dst_dir = vault / "NS-B" / "truths"
    dst_dir.mkdir(parents=True)
    dst_path = dst_dir / "W3.md"
    dst_path.write_text("---\nid: NS-B.W3\n---\n", encoding="utf-8")

    original_body = (
        "# Wichtiger Titel\n\n"
        "Erster Absatz mit kritischem Inhalt — darf NICHT verloren gehen.\n\n"
        "## Unterabschnitt\n\n"
        "Weiterer Inhalt mit Details.\n"
    )
    src_dir = vault / "NS-A" / "truths"
    src_atom = _make_atom(
        src_dir,
        "W-NonDestruct.md",
        frontmatter=(
            "type: truth\n"
            "id: NS-A.W-NonDestruct\n"
            "local_id: W-NonDestruct\n"
            "edges:\n"
            f"  - rel: relates_to\n"
            f"    ziel: NS-B.W3\n"
            f"    dst_path: {str(dst_path).replace(chr(92), '/')}\n"
        ),
        body=original_body,
    )

    exit_code = main(["--vault", str(vault)])
    assert exit_code == 0

    result = src_atom.read_text(encoding="utf-8")

    # Body-Erhalt pruefen
    assert "Wichtiger Titel" in result, "Titel verloren gegangen (Content-Loss)"
    assert "Erster Absatz mit kritischem Inhalt" in result, (
        "Erster Absatz verloren gegangen (Content-Loss)"
    )
    assert "Weiterer Inhalt mit Details" in result, (
        "Zweiter Absatz verloren gegangen (Content-Loss)"
    )

    # UND: AC-2 muss erfuellt sein (STUB faellt hier durch)
    assert "[[" in result and "]]" in result, (
        "main() STUB: kein [[wikilink]] materialisiert obwohl edges: vorhanden (AC-2 unerfuellt)"
    )
    assert WIKILINK_SECTION_HEADER in result, (
        f"'{WIKILINK_SECTION_HEADER}' fehlt — Wikilink-Abschnitt nicht angelegt"
    )


# ---------------------------------------------------------------------------
# Test 4: String-Form edges: toleriert — kein Crash, sinnvolle Ausgabe
# ---------------------------------------------------------------------------

def test_string_edges_tolerated(tmp_path):
    """AC-2 Robustheit: edges: als String-Liste (["NS-B.W7"]) -> kein Crash.

    main() soll mit String-Eintraegen umgehen koennen (tolerate, ggf. skipping).
    AKTUELL STUB -> schreibt nichts -> kein Crash aber auch keine [[Links]] -> RED
    wegen fehlender AC-2-Materialisierung (nicht wegen Crash).
    """
    from wikilink_materializer import main  # type: ignore[import]

    vault = tmp_path / "vault"
    vault.mkdir()

    src_dir = vault / "NS-A" / "truths"
    src_atom = _make_atom(
        src_dir,
        "W-StringEdge.md",
        frontmatter=(
            "type: truth\n"
            "id: NS-A.W-StringEdge\n"
            "local_id: W-StringEdge\n"
            "edges:\n"
            "  - NS-B.W7\n"      # String-Form (kein dict, kein dst_path)
            "  - '[[NS-B.W9]]'\n"  # Wikilink-String-Form
        ),
        body="# W-String-Edges\n\nAtom mit String-Form edges.\n",
    )

    # Darf NICHT mit Exception oder exit_code != 0 enden
    try:
        exit_code = main(["--vault", str(vault)])
    except Exception as exc:
        pytest.fail(
            f"main() raised Exception bei String-Form edges: {type(exc).__name__}: {exc}"
        )

    assert exit_code == 0, (
        f"main() gab exit_code={exit_code} zurueck bei String-Form edges (erwartet 0)"
    )

    # Beim Stub: kein [[..]] -> das ist der eigentliche RED-Signal fuer String-Form-Handling
    # (Fuer GREEN: mind. die String-Ziele sollten sinnvoll materialisiert ODER uebersprungen
    #  werden ohne Crash — main() entscheidet welche String-Edges verfolgbar sind.)
    result = src_atom.read_text(encoding="utf-8")
    # Keine harten Assertions auf [[..]] hier — String-Edges duerfen geskippt werden
    # wenn kein dst_path auflösbar. Der Test stellt nur sicher: KEIN CRASH.
    # (Fuer vollstaendige AC-2-Pruefung: Test 1 mit dict-Edges ist massgeblich.)
    assert isinstance(result, str), "Atom-Datei ist nach main() nicht mehr lesbar"


# ---------------------------------------------------------------------------
# Test 5: Real-Shape edges (rel+ziel, KEIN dst_path) — main() materialisiert [[links]]
# BL-450 AC-2 Luecke: _extract_edges filtert edges ohne dst_path -> 0 edges -> RED
# ---------------------------------------------------------------------------

def test_main_materializes_ziel_only_edges(tmp_path):
    """AC-2 Real-Shape: edges mit AUSSCHLIESSLICH rel+ziel (kein dst_path).

    Dies ist das echte Format aus keyword_edge_writer / Live-Vault:
      edges:
        - rel: relates_to
          ziel: _meta_truths.W7

    AKTUELL: _extract_edges prueft `edge.get("dst_path")` und ueberspringt Eintraege
    ohne dieses Feld -> 0 edges extrahiert -> atoms_written=0 -> RED.

    ERWARTUNG (GREEN): main() materialisiert [[..]] fuer ziel-Eintraege,
    z.B. [[W7]] oder [[_meta_truths.W7]] gemaess build_wikilink-Konvention.
    """
    from wikilink_materializer import main, WIKILINK_SECTION_HEADER  # type: ignore[import]

    vault = tmp_path / "vault"
    vault.mkdir()

    # Quell-Atom mit REAL-Shape edges (nur rel+ziel, kein dst_path)
    src_dir = vault / "NS-A" / "truths"
    src_atom = _make_atom(
        src_dir,
        "W-RealShape.md",
        frontmatter=(
            "type: truth\n"
            "id: NS-A.W-RealShape\n"
            "local_id: W-RealShape\n"
            "edges:\n"
            "  - rel: relates_to\n"
            "    ziel: _meta_truths.W7\n"
        ),
        body="# W-RealShape\n\nAtom mit real-shape edges (nur rel+ziel).\n",
    )

    # Write-Lauf
    exit_code = main(["--vault", str(vault)])
    assert exit_code == 0, f"main() endete mit exit_code={exit_code}"

    result = src_atom.read_text(encoding="utf-8")

    # AC-2: [[wikilink]] muss im Body stehen — ziel "_meta_truths.W7" oder Fragment "W7"
    assert "[[" in result and "]]" in result, (
        "main() materialisierte KEINEN [[wikilink]] fuer real-shape edge (rel+ziel ohne dst_path). "
        "Ursache: _extract_edges filtert edges ohne dst_path -> 0 edges -> RED (AC-2 Luecke)."
    )
    assert WIKILINK_SECTION_HEADER in result, (
        f"'{WIKILINK_SECTION_HEADER}' fehlt — Wikilink-Abschnitt nicht angelegt fuer ziel-only edge"
    )
    # Ziel-Fragment muss referenziert sein
    assert "W7" in result, (
        "Ziel '_meta_truths.W7' (Fragment 'W7') fehlt im materialisierten Body"
    )


# ---------------------------------------------------------------------------
# Test 6: Real-Shape dry-run zaehlt ziel-only edges als would-write > 0
# BL-450 AC-2 Luecke: dry-run zaehlt ebenfalls nur dst_path-edges -> 0 -> RED
# ---------------------------------------------------------------------------

def test_dry_run_counts_ziel_edges(tmp_path):
    """AC-2 Real-Shape dry-run: edges mit nur rel+ziel sollen als would-write > 0 gezaehlt werden.

    AKTUELL: dry-run-Pfad in main() ruft ebenfalls edge.get("dst_path") -> 0 would_write
    fuer ziel-only edges -> atoms_written=0 edges_written=0 -> RED.

    ERWARTUNG (GREEN): would_write >= 1 pro ziel-only edge, Ausgabe enthaelt
    edges_written > 0 (oder atoms_written > 0).

    Pruefung: stdout-Ausgabe parsen (atoms_written= / edges_written=) ODER
    separater Zaehler-Mechanismus. Hier: Datei bleibt unveraendert (dry-run),
    aber wir pruefen dass der Lauf > 0 melden wuerde — via stdout-Capture.
    """
    import io
    import contextlib
    from wikilink_materializer import main  # type: ignore[import]

    vault = tmp_path / "vault"
    vault.mkdir()

    # Quell-Atom mit REAL-Shape edges (nur rel+ziel, kein dst_path)
    src_dir = vault / "NS-A" / "truths"
    src_atom = _make_atom(
        src_dir,
        "W-DryRunReal.md",
        frontmatter=(
            "type: truth\n"
            "id: NS-A.W-DryRunReal\n"
            "local_id: W-DryRunReal\n"
            "edges:\n"
            "  - rel: relates_to\n"
            "    ziel: _meta_truths.W7\n"
        ),
        body="# W-DryRunReal\n\nAtom fuer dry-run real-shape test.\n",
    )

    # stdout capturen um atoms_written / edges_written auszulesen
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exit_code = main(["--vault", str(vault), "--dry-run"])
    output = buf.getvalue()

    assert exit_code == 0, f"main(--dry-run) endete mit exit_code={exit_code}"

    # Datei darf im dry-run NICHT veraendert worden sein
    result = src_atom.read_text(encoding="utf-8")
    assert "[[" not in result, (
        "dry-run hat Atom veraendert (kein Write erwartet im dry-run-Modus)"
    )

    # KERN-ASSERTION: atoms_written und/oder edges_written muss > 0 sein
    # AKTUELL: _extract_edges filtert ziel-only edges -> 0 -> RED
    assert "atoms_written=0" not in output or "edges_written=0" not in output, (
        f"dry-run meldete atoms_written=0 und edges_written=0 fuer real-shape ziel-only edge. "
        f"Ursache: _extract_edges filtert edges ohne dst_path. Output: {output!r} -> RED (AC-2 Luecke)."
    )
    # Positiv-Form: mindestens eines muss > 0 sein
    import re as _re
    aw_match = _re.search(r"atoms_written=(\d+)", output)
    ew_match = _re.search(r"edges_written=(\d+)", output)
    atoms_w = int(aw_match.group(1)) if aw_match else 0
    edges_w = int(ew_match.group(1)) if ew_match else 0
    assert atoms_w > 0 or edges_w > 0, (
        f"dry-run zaehlt atoms_written={atoms_w} edges_written={edges_w} fuer ziel-only edge "
        f"(erwartet > 0). Vollstaendige Ausgabe: {output!r} -> RED (BL-450 AC-2 Luecke)."
    )
