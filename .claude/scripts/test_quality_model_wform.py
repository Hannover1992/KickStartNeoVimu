"""
test_quality_model_wform.py — BL-243 AK-S3: Gold-Form-Validator fuer W{n}-Knoten.

Macht die Truth-Atomic-First-Konvention (BL-243 AK-S1, _model.md) ERZWINGBAR:
ein Model-W{n}-Knoten ist „gold", wenn er die kanonische atomare Form traegt
(### W-Heading + **text:** + **Status:** kanonisch + **source:** + **Quelle:** Wikilink +
**Edge zu:**) — NICHT Prosa/Flowchart-statt-Text. Vorbild: BL-161 quality_*-Familie.

On-disk-Form (verifiziert an BL-242 2_Model):
    ### W-DOM-1 · {atomarer Titel}
    - **text:** {einzeiliger Wahrheits-Satz}
    - **Typ:** ... · **Herkunft:** INTERN · **Status:** TENTATIV
    - **source:** `Crumbs:F-C11`
    - **Quelle:** `[[...]]`, ...
    - **Edge zu:** W-DOM-2, ...
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import quality_model_wform as qmw  # noqa: E402  (M3 RED: Modul existiert noch nicht)


GOLD_BLOCK = (
    "### W-DOM-1 · Die Liefer-Einheit\n"
    "- **text:** Der Read-Index besteht aus exakt 5 benannten Typen.\n"
    "- **Typ:** HYPOTHESE · **Herkunft:** INTERN · **Status:** TENTATIV\n"
    "- **source:** `Crumbs:F-C11`\n"
    "- **Quelle:** `[[Crumbs/x.md#F-C11]]`, `[[1_Task/Task.md#EK]]`\n"
    "- **Edge zu:** W-DOM-2, W-SCO-1\n"
)

MODEL_GOLD = (
    "---\nid: X\n---\n# Model\n\n" + GOLD_BLOCK + "\n"
    "### W-DOM-2 · Zweite Wahrheit\n"
    "- **text:** Drei der fuenf Indizes sind reine Frontmatter-Aggregate.\n"
    "- **Status:** BESTAETIGT\n"
    "- **source:** `Repo:x.py:71`\n"
    "- **Quelle:** `[[a.md#b]]`\n"
    "- **Edge zu:** W-DOM-1\n"
)

MODEL_MISSING_STATUS = (
    "# Model\n"
    "### W-VAL-1 · Ohne Status\n"
    "- **text:** Eine atomare Aussage ohne Status-Feld.\n"
    "- **source:** `Crumbs:F1`\n"
    "- **Quelle:** `[[a.md#b]]`\n"
    "- **Edge zu:** W-VAL-2\n"
)

MODEL_PROSE = (
    "# Model\n"
    "Die Anwendung W1 funktioniert so: (a) erst dies, (b) dann das — als Flowchart-Schritt.\n"
    "Kein einziger `### W`-Block, nur Prosa/Ablauf. (BL-243-Antipattern.)\n"
)


def test_parse_finds_w_blocks():
    blocks = qmw.parse_w_blocks(MODEL_GOLD)
    ids = [b["w_id"] for b in blocks]
    assert "W-DOM-1" in ids and "W-DOM-2" in ids
    assert len(blocks) == 2


def test_gold_block_passes():
    res = qmw.validate_model(MODEL_GOLD)
    assert res["total"] == 2
    assert res["gold_count"] == 2
    assert res["violations"] == []


def test_missing_status_flagged():
    res = qmw.validate_model(MODEL_MISSING_STATUS)
    assert res["gold_count"] == 0
    assert any("Status" in v["missing"] for v in res["violations"])


def test_non_canonical_status_flagged():
    m = (
        "### W-X-1 · T\n"
        "- **text:** Eine Aussage.\n"
        "- **Status:** irgendwas\n"
        "- **source:** `Crumbs:F`\n"
        "- **Quelle:** `[[a.md#b]]`\n"
        "- **Edge zu:** W-X-2\n"
    )
    res = qmw.validate_model(m)
    assert res["violations"][0]["status_canonical"] is False


def test_quelle_without_wikilink_flagged():
    m = (
        "### W-Y-1 · T\n"
        "- **text:** Aussage.\n"
        "- **Status:** OFFEN\n"
        "- **source:** `Crumbs:F`\n"
        "- **Quelle:** irgendein Text ohne Wikilink\n"
        "- **Edge zu:** W-Y-2\n"
    )
    res = qmw.validate_model(m)
    assert any("Quelle" in mm for v in res["violations"] for mm in v["missing"])


def test_prose_only_flagged():
    res = qmw.validate_model(MODEL_PROSE)
    assert res["prose_only"] is True
    assert res["total"] == 0


def test_cli_exit_codes(tmp_path):
    good = tmp_path / "good_Model.md"
    good.write_text(MODEL_GOLD, encoding="utf-8")
    bad = tmp_path / "bad_Model.md"
    bad.write_text(MODEL_MISSING_STATUS, encoding="utf-8")
    assert qmw.main([str(good)]) == 0
    assert qmw.main([str(bad)]) == 1
