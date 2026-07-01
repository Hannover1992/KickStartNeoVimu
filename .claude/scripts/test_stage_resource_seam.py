"""
test_stage_resource_seam.py — Tests fuer BL-392 batch_5 (AK-RES-SEAM).

Die NAHT zwischen den atomisierten Stage-Slices (resolve_vault_stage.StageHandle /
die resources.md- + concurrency_class.md-Slices, batch_2/3) und der vorhandenen
ressourcen-zentrischen FREE/LOCKED-Registry (stage_resource_registry, BL-247).

stage_resource_seam ist der PRODUCER (W-RES-2): es DEKLARIERT die Ressourcen einer
Stage aus den Slices (resource_ids + divisibility + concurrency_class + depends_on).
Es GOVERNT NICHT — kein acquire/release/lock. Die Governance (Locks) ist der CONSUMER
BL-368/BL-247 (stage_resource_registry). Diese Tests pinnen genau diese Trennung +
die freier-String-Round-Trip-DoD (W-RES-2 adjudiziert).

read-only: die Naht mutiert weder Vault noch State und nimmt KEIN Lock.

Lauf (beide cwds, BL-336-Lehre):
  py -3 -m pytest .claude/scripts/test_stage_resource_seam.py     (repo-root)
  py -3 -m pytest test_stage_resource_seam.py                     (scripts-cwd)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

import stage_resource_registry as reg  # die FERTIGE FREE/LOCKED-Registry (read-only genutzt)
from stage_resource_seam import stage_resources


# ---------------------------------------------------------------------------
# Slice-Fixtures: resources.md-Slice (Deklaration) + concurrency_class.md-Slice
# ---------------------------------------------------------------------------
#
# Die Naht liest aus zwei Slices:
#   - resources.md-Slice: die Ressourcen-Deklaration (resource_ids + Teilbarkeit).
#   - concurrency_class.md-Slice: concurrency_class + concurrency_depends_on.
# Format der resource_ids = FREIE Strings (heutiges concurrency_depends_on-Format),
# inkl. ':'-Eintrag (z.B. "container_budget:max_container_parallel").

# Eine realistische Integration-Stage (Spiegel der IST-stage_3.md, gekuerzt):
_CONCURRENCY_SLICE = {
    "concurrency_class": "DEPENDS",
    "concurrency_depends_on": [
        "docker_integration_stack",
        "container_budget:max_container_parallel",  # ':' = der Round-Trip-Stresstest
    ],
    "concurrency_rationale": "container_isolation=true -> parallel bis Cap, sonst Defer.",
}

_RESOURCES_SLICE = {
    "infrastruktur": "docker",
    # Ressourcen-Deklaration mit Teilbarkeit (teilbar/unteilbar). Freier-String-Format.
    "resources": [
        {"id": "docker_integration_stack", "divisibility": "unteilbar"},
        {"id": "container_budget:max_container_parallel", "divisibility": "teilbar"},
    ],
}


# ---------------------------------------------------------------------------
# 1. divisibility-Map: teilbar/unteilbar -> {id: teilbar|unteilbar}
# ---------------------------------------------------------------------------


def test_divisibility_map_from_resources_slice() -> None:
    """Der resources-Slice mit teilbar/unteilbar -> divisibility-Map pro resource_id."""
    decl = stage_resources(_RESOURCES_SLICE, _CONCURRENCY_SLICE)
    assert decl["divisibility"]["docker_integration_stack"] == "unteilbar"
    assert decl["divisibility"]["container_budget:max_container_parallel"] == "teilbar"


def test_resource_ids_collected() -> None:
    """resource_ids enthaelt die deklarierten Ressourcen (freie Strings, inkl. ':')."""
    decl = stage_resources(_RESOURCES_SLICE, _CONCURRENCY_SLICE)
    assert "docker_integration_stack" in decl["resource_ids"]
    assert "container_budget:max_container_parallel" in decl["resource_ids"]


def test_concurrency_class_and_depends_on_extracted() -> None:
    """concurrency_class + depends_on (freie Strings) kommen aus dem concurrency-Slice."""
    decl = stage_resources(_RESOURCES_SLICE, _CONCURRENCY_SLICE)
    assert decl["concurrency_class"] == "DEPENDS"
    assert decl["depends_on"] == [
        "docker_integration_stack",
        "container_budget:max_container_parallel",
    ]


# ---------------------------------------------------------------------------
# 2. Freier-String-Round-Trip (W-RES-2): via registry render/_fs_unsafe == Original
# ---------------------------------------------------------------------------


def test_free_string_roundtrip_via_registry() -> None:
    """Was die Naht uebergibt, kommt aus der Registry als ORIGINAL-String zurueck (':' reversibel)."""
    decl = stage_resources(_RESOURCES_SLICE, _CONCURRENCY_SLICE)
    for rid in decl["resource_ids"]:
        # Die Registry enkodiert den resource_id FS-safe (Lock-Key) und rekonstruiert
        # ihn via _fs_unsafe (genau das, was render()/lookup_free() tun, um den
        # Original-resource_id zu liefern). Round-Trip muss verlustfrei sein.
        key = reg._fs_safe(rid)
        back = reg._fs_unsafe(key)
        assert back == rid, f"Round-Trip-Verlust: {rid!r} -> {key!r} -> {back!r}"


def test_colon_resource_id_roundtrip_explicit() -> None:
    """Der ':'-Eintrag round-trippt verlustfrei (':' -> ~3a -> ':')."""
    rid = "container_budget:max_container_parallel"
    decl = stage_resources(_RESOURCES_SLICE, _CONCURRENCY_SLICE)
    assert rid in decl["resource_ids"]
    assert reg._fs_unsafe(reg._fs_safe(rid)) == rid


def test_roundtrip_via_registry_render(tmp_path: Path) -> None:
    """End-to-end: render() schreibt die .md mit dem ORIGINAL-resource_id (inkl. ':')."""
    decl = stage_resources(_RESOURCES_SLICE, _CONCURRENCY_SLICE)
    # render() ist read-only ggue. .locks (kein Lock); es spiegelt nur den Zustand.
    out_path = reg.render(decl["resource_ids"], vault_root=tmp_path)
    rendered = out_path.read_text(encoding="utf-8")
    # Der Original-String (mit ':') steht so in der gerenderten .md (kein FS-Key-Leak).
    assert "container_budget:max_container_parallel" in rendered
    assert "docker_integration_stack" in rendered


# ---------------------------------------------------------------------------
# 3. Producer-only (W-RES-2): die Naht ruft KEIN acquire/release/lock
# ---------------------------------------------------------------------------


def test_seam_takes_no_lock(tmp_path: Path) -> None:
    """Die Naht deklariert nur — sie nimmt KEIN Lock (kein .locks/-Eintrag entsteht).

    Strukturell: die Naht ist eine reine in-memory-Deklaration ohne Vault-Handle —
    sie KANN gar nichts in ein .locks/ schreiben. Snapshot eines frischen Dir bleibt
    leer (Producer-only: kein acquire/release auf der Registry).
    """
    locks_before = _locks_snapshot(tmp_path)
    stage_resources(_RESOURCES_SLICE, _CONCURRENCY_SLICE)
    locks_after = _locks_snapshot(tmp_path)
    assert locks_before == locks_after == set(), "Die Naht darf KEIN Lock/acquire ausloesen (Producer-only)."


def test_seam_source_has_no_acquire_calls() -> None:
    """Falsifikation: der Naht-Quelltext ruft KEIN acquire/release/acquire_all/lock (Governance=BL-368)."""
    import stage_resource_seam as mod

    src = Path(mod.__file__).read_text(encoding="utf-8")
    # Strukturelle Falsifikation: kein Governance-Call (acquire/release/lock).
    for forbidden in ("acquire(", "release(", "acquire_all(", "acquire_region(", ".acquire_bl("):
        assert forbidden not in src, f"Producer-only verletzt: Naht ruft {forbidden}"


def test_seam_is_read_only_no_state_mutation(tmp_path: Path) -> None:
    """read-only: ein stage_resources-Aufruf legt NICHTS auf der Platte an.

    Die Naht bekommt nur in-memory Slice-dicts (kein Pfad) und kann daher per
    Konstruktion nichts schreiben — das frische tmp_path bleibt leer.
    """
    before = set(p.name for p in tmp_path.rglob("*"))
    stage_resources(_RESOURCES_SLICE, _CONCURRENCY_SLICE)
    after = set(p.name for p in tmp_path.rglob("*"))
    assert before == after == set(), "stage_resources mutiert nichts (read-only Deklaration)."


# ---------------------------------------------------------------------------
# 4. Leere / skip resources -> leere Deklaration (kein Crash)
# ---------------------------------------------------------------------------


def test_empty_resources_yields_empty_declaration() -> None:
    """Leerer resources-Slice -> leere Deklaration (kein Crash)."""
    decl = stage_resources({}, {})
    assert decl["resource_ids"] == []
    assert decl["divisibility"] == {}
    assert decl["depends_on"] == []
    assert decl["concurrency_class"] is None


def test_skip_resources_yields_empty_declaration() -> None:
    """resources-Slice mit skip-Sentinel -> leere Ressourcen-Deklaration (W-SLICE-3)."""
    decl = stage_resources({"skip": True}, {"skip": True})
    assert decl["resource_ids"] == []
    assert decl["divisibility"] == {}


def test_none_slices_no_crash() -> None:
    """None-Slices (Slice fehlt ganz) -> leere Deklaration, kein Crash (fail-safe)."""
    decl = stage_resources(None, None)
    assert decl["resource_ids"] == []
    assert decl["depends_on"] == []


def test_resources_slice_without_explicit_list_uses_depends_on() -> None:
    """Kein expliziter resources-List, aber depends_on da -> depends_on bilden die resource_ids.

    Heutiges Format traegt die Ressourcen-Beziehung NUR im concurrency_depends_on (freie
    Strings). Fehlt eine separate resources-Liste, leitet die Naht die resource_ids aus
    depends_on ab (divisibility dann unbekannt -> Default), damit kein Concern verloren geht.
    """
    decl = stage_resources({"infrastruktur": "docker"}, _CONCURRENCY_SLICE)
    assert "docker_integration_stack" in decl["resource_ids"]
    assert "container_budget:max_container_parallel" in decl["resource_ids"]


# ---------------------------------------------------------------------------
# 5. Eingabe-Flexibilitaet: StageHandle ODER resources-Slice-dict
# ---------------------------------------------------------------------------


def test_accepts_stage_handle(tmp_path, monkeypatch) -> None:
    """stage_resources akzeptiert auch einen StageHandle (slice_view liefert die Slices)."""
    import os
    import yaml
    from resolve_vault_stage import resolve_stage

    # Lege einen Vault-Slice-Satz an (resources + concurrency_class tragen die Deklaration).
    vault = tmp_path / "vault"
    slice_set = {
        "_index": {"stufe": 3, "name": "integration"},
        "execute": {"testbefehl": "dotnet test", "testtyp": "integration"},
        "setup": {"commands": ["up"]},
        "teardown": {"commands": ["down"]},
        "health_check": {"command": "docker version"},
        "resources": _RESOURCES_SLICE,
        "concurrency_class": _CONCURRENCY_SLICE,
        "exit_criteria": {"qg": "pass"},
    }
    stage_dir = vault / "Stage" / "stage_3_integration"
    stage_dir.mkdir(parents=True, exist_ok=True)
    for name, fm in slice_set.items():
        text = "---\n" + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True) + "---\n\n# " + name + "\n"
        (stage_dir / f"{name}.md").write_text(text, encoding="utf-8")

    monkeypatch.setenv("CLAUDE_VAULT_ROOT", str(vault))
    handle = resolve_stage(3)
    assert handle is not None

    decl = stage_resources(handle)
    assert "docker_integration_stack" in decl["resource_ids"]
    assert decl["divisibility"]["container_budget:max_container_parallel"] == "teilbar"
    assert decl["concurrency_class"] == "DEPENDS"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _locks_snapshot(vault_root: Path) -> set:
    """Schnappschuss aller .locks/-Eintraege unter vault_root (leer wenn keine)."""
    locks_root = vault_root / ".locks"
    if not locks_root.exists():
        return set()
    return set(str(p.relative_to(locks_root)) for p in locks_root.rglob("*"))
