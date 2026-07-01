"""
BL-444 batch_2 RED-Worker: Content-Tests fuer _SDF_orchestrate_post.md

Diese Tests pruefen, ob der TERMINATE-Zweig in _SDF_orchestrate_post.md die
atomare Closure-Sequenz EXPLIZIT verdrahtet (AK-1/AK-2/AK-6).

Aktueller Zustand (SOLL red sein):
- Z876-887: reiner Kommentar-Pseudocode (should_chain_bdf), KEIN advance_current
- Z966-1013: Lane/Goal Redirect ruft _lane_orchestrate (BL-442 AK-4, ungebaut),
              KEIN next_bl_for_lane, kein guard_lane_closure_stop-Verweis
- Keine atomare Closure-Sequenz dokumentiert (kein "atomare Closure-Sequenz" Marker,
  kein "BL-444" Closure-Block-Marker)

GREEN-Worker muss folgende Strings/Marker in _SDF_orchestrate_post.md einfuegen:

  1. "advance_current"          -- AK-1/AK-3: Queue-Pointer-Advance (Pflicht im Closure-Block)
                                   Konkret: `plan = advance_current(my_lane, BL_ID, plan)`
                                   und `from lane_plan import ... advance_current ...`

  2. "next_bl_for_lane"         -- AK-2: Lane-aware next-BL-Bestimmung
                                   Konkret: `next_bl = next_bl_for_lane(my_lane, plan, done_set)`
                                   im TERMINATE/Closure-Block

  3. "guard_lane_closure_stop"  -- AK-6: Stop-Hook-Backstop-Verweis
                                   Konkret: Kommentar oder Verweis der Form
                                   "guard_lane_closure_stop.py" im Datei-Body

  4. "atomare Closure-Sequenz"  -- INV-CLOSURE-2: Dokumentation dass merge_seam + current-advance
     ODER "BL-444" im Closure-  -- + redirect-chain als atomarer Block laufen
     Kontext                       Konkret: entweder Marker-Kommentar
                                   "# [AK-1 BL-444: AKTIVER Closure-Block" oder
                                   Text "atomare Closure-Sequenz"

Datei-Pfad der zu pruefenden Datei:
  .claude/commands/_SDF_orchestrate_post.md
  (relativ zu OmniCommand-wtA Worktree)
"""
import os
import pathlib
import pytest

# Pfad zur Ziel-Datei (absolut, relativ zum Repo-Root aufgeloest)
_REPO_ROOT = pathlib.Path(__file__).parent.parent.parent  # OmniCommand-wtA
_TARGET = _REPO_ROOT / ".claude" / "commands" / "_SDF_orchestrate_post.md"


@pytest.fixture(scope="module")
def post_md_content() -> str:
    """Liest _SDF_orchestrate_post.md einmal fuer alle Tests."""
    assert _TARGET.exists(), (
        f"Ziel-Datei nicht gefunden: {_TARGET}\n"
        "Bitte pruefen ob der Worktree-Pfad korrekt ist."
    )
    return _TARGET.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Test 1: advance_current muss im Closure-Block referenziert sein (AK-1/AK-3)
# ---------------------------------------------------------------------------

def test_closure_block_references_advance_current(post_md_content: str) -> None:
    """AK-1/AK-3: Der TERMINATE-Closure-Block MUSS 'advance_current' aufrufen.

    GREEN-Marker: Der String 'advance_current' muss in der Datei vorkommen.
    Erwartete Form (aus Spec AK-1 SOLL-Pseudocode):
      plan = advance_current(my_lane, BL_ID, plan)
    UND/ODER:
      from lane_plan import ... advance_current ...

    Aktuell (RED): nur 'should_chain_bdf' Kommentar-Pseudocode, kein advance_current.
    """
    assert "advance_current" in post_md_content, (
        "FEHLT: 'advance_current' nicht in _SDF_orchestrate_post.md gefunden.\n"
        "AK-1/AK-3: Der Closure-Block muss 'advance_current(my_lane, BL_ID, plan)' aufrufen.\n"
        "GREEN-Worker: Ersetze den Kommentar-Pseudocode Z876-887 durch den aktiven Closure-Block "
        "aus BL-444_Spec.md AK-1 SOLL-Pseudocode (inkl. 'from lane_plan import ... advance_current')."
    )


# ---------------------------------------------------------------------------
# Test 2: next_bl_for_lane muss in der TERMINATE/Closure-Sektion sein (AK-2)
# ---------------------------------------------------------------------------

def test_closure_block_references_next_bl_for_lane(post_md_content: str) -> None:
    """AK-2: Der Closure-Block MUSS 'next_bl_for_lane' als Quelle des naechsten BL nutzen.

    GREEN-Marker: Der String 'next_bl_for_lane' muss in der Datei vorkommen.
    Erwartete Form (aus Spec AK-1 SOLL-Pseudocode):
      from lane_plan import next_bl_for_lane
      next_bl = next_bl_for_lane(my_lane, plan, done_set)

    Aktuell (RED): Der LANE/GOAL REDIRECT (Z966-1013) ruft '_lane_orchestrate'
    statt next_bl_for_lane zu nutzen — 'next_bl_for_lane' fehlt komplett.
    """
    assert "next_bl_for_lane" in post_md_content, (
        "FEHLT: 'next_bl_for_lane' nicht in _SDF_orchestrate_post.md gefunden.\n"
        "AK-2: Der Closure-Block muss 'next_bl_for_lane(my_lane, plan, done_set)' aufrufen\n"
        "statt den globalen BDF-Pick oder _lane_orchestrate zu nutzen.\n"
        "GREEN-Worker: Ersetze Z966-1013 Lane/Goal-Redirect durch den aktiven Closure-Block\n"
        "aus BL-444_Spec.md AK-1 SOLL-Pseudocode (Schritt 3: 'from lane_plan import next_bl_for_lane')."
    )


# ---------------------------------------------------------------------------
# Test 3: guard_lane_closure_stop muss als Stop-Hook-Backstop referenziert sein (AK-6)
# ---------------------------------------------------------------------------

def test_closure_block_references_guard_lane_closure_stop(post_md_content: str) -> None:
    """AK-6: Die Datei MUSS 'guard_lane_closure_stop' referenzieren (Stop-Hook-Backstop).

    GREEN-Marker: Der String 'guard_lane_closure_stop' muss in der Datei vorkommen.
    Erwartete Form (Kommentar oder Invarianten-Block):
      # GUARD: guard_lane_closure_stop.py (INV-CLOSURE-1, BL-444) ...
    ODER im INVARIANTEN-Block als Enforcement-Hinweis.

    Aktuell (RED): Nur 'guard_autochain_stop.py' (RE-BATCH) ist referenziert.
    'guard_lane_closure_stop' fehlt komplett — AK-6-Guard nicht gebaut/verdrahtet.
    """
    assert "guard_lane_closure_stop" in post_md_content, (
        "FEHLT: 'guard_lane_closure_stop' nicht in _SDF_orchestrate_post.md gefunden.\n"
        "AK-6: guard_lane_closure_stop.py ist der Stop-Hook-Backstop (analog guard_autochain_stop).\n"
        "Er blockiert Turn-Ende wenn INV-CLOSURE-1 verletzt ist (TERMINATE + lane + next_bl + kein Chain).\n"
        "GREEN-Worker: Fuege Verweis auf guard_lane_closure_stop.py im Closure-Block oder\n"
        "INVARIANTEN-Abschnitt ein (z.B. '# GUARD: guard_lane_closure_stop.py (INV-CLOSURE-1, BL-444)')."
    )


# ---------------------------------------------------------------------------
# Test 4: Atomare Closure-Sequenz muss als zusammenhaengender Block dokumentiert sein
# ---------------------------------------------------------------------------

def test_closure_sequence_atomic_documented(post_md_content: str) -> None:
    """INV-CLOSURE-2: Die 3 Closure-Schritte muessen als atomare Sequenz dokumentiert sein.

    GREEN-Marker: Mindestens EINER der folgenden Strings muss vorkommen:
      a) "atomare Closure-Sequenz"  -- explizites Atomaritaets-Marker
      b) "[AK-1 BL-444"            -- BL-444-Closure-Block-Kommentar aus Spec-SOLL-Pseudocode
      c) "BL-444: AKTIVER"         -- AKTIVER Closure-Block Marker (aus Spec AK-1 Zitat)

    Erwartete Form (aus Spec AK-1 SOLL-Pseudocode Z71):
      # [AK-1 BL-444: AKTIVER Closure-Block — nicht mehr Kommentar-Pseudocode]

    Aktuell (RED): Nur Kommentar-Pseudocode (should_chain_bdf) aus BL-442.
    Kein 'BL-444'-Marker, kein 'atomare Closure-Sequenz'-Marker vorhanden.

    INV-CLOSURE-2: merge_seam + current-advance + next-bl-chain sind ATOMAR.
    Kein Teilzustand erlaubt. Dokumentation der Atomaritaet ist Pflicht.
    """
    markers = [
        "atomare Closure-Sequenz",
        "[AK-1 BL-444",
        "BL-444: AKTIVER",
    ]
    found = any(marker in post_md_content for marker in markers)
    assert found, (
        "FEHLT: Kein Atomaritaets-Marker fuer den Closure-Block in _SDF_orchestrate_post.md.\n"
        f"Gesuchte Marker (mind. 1 muss vorhanden sein): {markers}\n"
        "INV-CLOSURE-2: merge_seam + current-advance + redirect-chain sind ATOMAR.\n"
        "GREEN-Worker: Fuege Marker-Kommentar ein, z.B.:\n"
        "  '# [AK-1 BL-444: AKTIVER Closure-Block — nicht mehr Kommentar-Pseudocode]'\n"
        "ODER dokumentiere 'atomare Closure-Sequenz' im Block-Header."
    )


# ---------------------------------------------------------------------------
# Ausfuehren: py -3 -m pytest .claude/scripts/test_bl444_closure_wiring.py -q
# ---------------------------------------------------------------------------
