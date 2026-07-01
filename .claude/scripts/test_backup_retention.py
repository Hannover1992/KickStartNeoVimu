#!/usr/bin/env python3
"""
test_backup_retention.py — GOLD-RED fuer backup_retention.py (BL-338 PL-338-4).

ZWECK (Gold-Contract B): Heiler legen Backups (.bak_*, _manifest_history,
_manifest_pre_*, RECOVERY) und niemand prunt -> Heiler-als-Bloat-Produzent
(486-Empirie: 12 Backup-Leichen / 4.5MB). backup_retention.py liefert eine
Backup-Registry + Retention-Policy (keep_n juengste pro family, MD5-Dupe-Prune,
TTL-Ablauf).

GREEN-API (backup_retention.py, __file__-relativ / cwd-invariant):
  - register_backup(registry_path, family, backup_path, erzeugt_von, ttl, md5)
        -> schreibt Eintrag {family, path, erzeugt_von, ttl, md5, ts} (JSON/JSONL).
  - prune_backups(registry_path, family, keep_n=2, dry_run=False)
        -> behaelt die keep_n JUENGSTEN pro family; vom Rest: MD5-Duplikate -> prune,
           Rest -> Archiv/prune nach TTL. lossless-vor-Prune (MD5-Verify).
           Returns {kept, pruned, dupes_removed}.
  - find_backups(root, glob_pattern) -> Liste unregistrierter Backup-Dateien
        (Naming: .bak* / _manifest_history / _manifest_pre_* / RECOVERY).

Greenfield-Import `import backup_retention as br` ist RED bis das Modul existiert.
"""
from __future__ import annotations

import hashlib
import sys
import time
from pathlib import Path

import pytest

_SCRIPT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(_SCRIPT_DIR))

# Greenfield-Import -> RED bis backup_retention.py existiert (GREEN-Phase).
import backup_retention as br


# ── Helfer ───────────────────────────────────────────────────────────────────

def _md5_file(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def _make_backup(dirpath: Path, name: str, content: str) -> Path:
    dirpath.mkdir(parents=True, exist_ok=True)
    p = dirpath / name
    p.write_text(content, encoding="utf-8")
    return p


def _register(registry: Path, backup: Path, family: str, ttl: str = "30d",
              erzeugt_von: str = "manifest_slim", ts: str | None = None) -> None:
    """Duenner Wrapper um register_backup; ts optional fuer determinierte Ordnung."""
    kwargs = dict(family=family, backup_path=str(backup), erzeugt_von=erzeugt_von,
                  ttl=ttl, md5=_md5_file(backup))
    if ts is not None:
        kwargs["ts"] = ts
    br.register_backup(registry, **kwargs)


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_register_and_read_back_entry(tmp_path):
    """register_backup schreibt einen Eintrag mit allen Pflichtfeldern; read-back."""
    registry = tmp_path / "backup_registry.jsonl"
    bak = _make_backup(tmp_path, "_manifest.bak_2026-06-13_pre_split.md", "state-A")
    md5 = _md5_file(bak)
    br.register_backup(registry, family="manifest", backup_path=str(bak),
                       erzeugt_von="manifest_slim", ttl="30d", md5=md5)
    entries = br.read_registry(registry)
    assert len(entries) == 1
    e = entries[0]
    assert e["family"] == "manifest"
    assert e["path"] == str(bak)
    assert e["erzeugt_von"] == "manifest_slim"
    assert e["ttl"] == "30d"
    assert e["md5"] == md5
    assert "ts" in e and e["ts"]


def test_prune_keeps_keep_n_youngest_per_family(tmp_path):
    """prune_backups behaelt die keep_n JUENGSTEN pro family, prunt die aelteren."""
    registry = tmp_path / "reg.jsonl"
    paths = []
    for i in range(5):
        b = _make_backup(tmp_path, f"_manifest.bak_{i}.md", f"distinct-content-{i}")
        _register(registry, b, "manifest", ts=f"2026-06-13T10:0{i}:00")
        paths.append(b)
    res = br.prune_backups(registry, "manifest", keep_n=2)
    # die 2 juengsten (i=3,4) bleiben, 3 aeltere gepruned
    assert res["kept"] == 2
    assert res["pruned"] == 3
    assert paths[4].exists() and paths[3].exists()
    assert not paths[0].exists()


def test_prune_md5_dupe_detection(tmp_path):
    """2 inhaltsgleiche Backups (gleiche MD5) -> das Duplikat wird gepruned."""
    registry = tmp_path / "reg.jsonl"
    a = _make_backup(tmp_path, "_manifest.bak_old.md", "IDENTICAL")
    b = _make_backup(tmp_path, "_manifest.bak_new.md", "IDENTICAL")
    _register(registry, a, "manifest", ts="2026-06-13T10:00:00")
    _register(registry, b, "manifest", ts="2026-06-13T10:05:00")
    res = br.prune_backups(registry, "manifest", keep_n=1)
    assert res["dupes_removed"] >= 1
    # genau eine der beiden inhaltsgleichen Dateien ueberlebt
    assert a.exists() != b.exists()


def test_prune_dry_run_deletes_nothing(tmp_path):
    """prune dry_run=True -> kein Delete (Dateien bleiben, Registry unveraendert)."""
    registry = tmp_path / "reg.jsonl"
    paths = []
    for i in range(4):
        b = _make_backup(tmp_path, f"_manifest.bak_{i}.md", f"content-{i}")
        _register(registry, b, "manifest", ts=f"2026-06-13T10:0{i}:00")
        paths.append(b)
    before = registry.read_text(encoding="utf-8")
    res = br.prune_backups(registry, "manifest", keep_n=1, dry_run=True)
    assert all(p.exists() for p in paths)
    assert registry.read_text(encoding="utf-8") == before
    # dry_run berichtet trotzdem was gepruned WUERDE
    assert res["pruned"] >= 1


def test_prune_ttl_respect_fresh_vs_expired(tmp_path):
    """TTL-Respekt: abgelaufene Backups jenseits keep_n -> prune; frische -> behalten."""
    registry = tmp_path / "reg.jsonl"
    fresh = _make_backup(tmp_path, "_manifest.bak_fresh.md", "fresh-content")
    expired = _make_backup(tmp_path, "_manifest.bak_expired.md", "expired-content")
    # frisch: jetzt; abgelaufen: lange her + kurze TTL
    now_ts = time.strftime("%Y-%m-%dT%H:%M:%S")
    _register(registry, fresh, "manifest", ttl="30d", ts=now_ts)
    _register(registry, expired, "manifest", ttl="1d", ts="2020-01-01T00:00:00")
    res = br.prune_backups(registry, "manifest", keep_n=1)
    # frisch ueberlebt (juengster + nicht abgelaufen), abgelaufener wird gepruned
    assert fresh.exists()
    assert not expired.exists()
    assert res["pruned"] >= 1


def test_find_backups_matches_naming_ignores_non_backups(tmp_path):
    """find_backups matcht das Backup-Naming-Glob, ignoriert Nicht-Backups."""
    _make_backup(tmp_path, "_manifest.bak_2026-06-13_pre_split.md", "x")
    _make_backup(tmp_path, "_manifest_history_2026-06-10.md", "x")
    _make_backup(tmp_path, "_manifest_pre_migration.md", "x")
    _make_backup(tmp_path, "RECOVERY_2026-06-01.md", "x")
    _make_backup(tmp_path, "_manifest.md", "x")          # KEIN Backup
    _make_backup(tmp_path, "spec.md", "x")               # KEIN Backup
    found = br.find_backups(tmp_path)
    names = {Path(f).name for f in found}
    assert "_manifest.bak_2026-06-13_pre_split.md" in names
    assert "_manifest_history_2026-06-10.md" in names
    assert "_manifest_pre_migration.md" in names
    assert "RECOVERY_2026-06-01.md" in names
    assert "_manifest.md" not in names
    assert "spec.md" not in names


def test_prune_lossless_md5_verify_before_delete(tmp_path):
    """lossless-vor-Prune: ein zu prunender Eintrag, dessen Datei vom registrierten
    MD5 ABWEICHT (out-of-band geaendert), wird NICHT blind geloescht (Safety)."""
    registry = tmp_path / "reg.jsonl"
    keep = _make_backup(tmp_path, "_manifest.bak_keep.md", "keep-content")
    tampered = _make_backup(tmp_path, "_manifest.bak_tampered.md", "orig-content")
    _register(registry, keep, "manifest", ts="2026-06-13T10:05:00")
    _register(registry, tampered, "manifest", ts="2026-06-13T10:00:00")
    # out-of-band Aenderung NACH der Registrierung -> MD5-Mismatch
    tampered.write_text("MUTATED-AFTER-REGISTER", encoding="utf-8")
    res = br.prune_backups(registry, "manifest", keep_n=1)
    # der manipulierte Backup wird wegen MD5-Mismatch NICHT geloescht (lossless-Schutz)
    assert tampered.exists()
    assert "md5_mismatch" in res or res.get("skipped_mismatch", 0) >= 1
