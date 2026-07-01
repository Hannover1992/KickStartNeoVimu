"""BL-442 AK-1: SDF-post -> BDF aktiver Redirect-Entscheider (GAP-1).

RED-Tests (Test-Autor != GREEN-Implementierer). should_chain_bdf entscheidet, ob _SDF_orchestrate_post
bei TERMINATE aktiv Skill(_BDF_orchestrate) chainen soll (statt nur passivem df_status=DONE-Signal).
Regel: redirect NUR wenn queue/parking-lot durch UND Lane/Goal-Modus (kein eigener BDF-Loop laeuft)
UND nicht no_chain. Bei big_dark_factory-Modus (BDF-Loop aktiv) NICHT (Doppel-Antrieb vermeiden).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import sdf_post_bdf_redirect as r  # noqa: E402


def test_redirect_when_lane_goal_done():
    # Lane/Goal-Modus, alles durch, kein no_chain, kein aktiver BDF-Loop -> redirect
    assert r.should_chain_bdf(mode="lane", all_items_done=True, no_chain=False, bdf_loop_active=False) is True


def test_no_redirect_when_not_done():
    assert r.should_chain_bdf(mode="lane", all_items_done=False, no_chain=False, bdf_loop_active=False) is False


def test_no_redirect_when_bdf_loop_active():
    # big_dark_factory: BDF treibt selbst -> kein aktiver Re-Chain (Doppel-Antrieb)
    assert r.should_chain_bdf(mode="big_dark_factory", all_items_done=True, no_chain=False, bdf_loop_active=True) is False


def test_no_redirect_when_no_chain():
    assert r.should_chain_bdf(mode="lane", all_items_done=True, no_chain=True, bdf_loop_active=False) is False


def test_target_command_is_bdf_orchestrate():
    assert r.redirect_target() == "_BDF_orchestrate"
