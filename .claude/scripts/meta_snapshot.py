#!/usr/bin/env python3
"""meta_snapshot.py — Snapshot Vault-Meta → .claude/meta-cache/ (BL-193 AK-7).

Aufruf:
  python meta_snapshot.py             # snapshot kopieren
  python meta_snapshot.py --dry-run   # Datei-Count ohne Kopieren (exitcode 0)
  python meta_snapshot.py --validate  # SHA-256 Manifest pruefen (exitcode 0, WARN bei Mismatch)

Exitcodes:
  0 = Erfolg
  2 = Vault nicht erreichbar
"""
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


MANIFEST_NAME = ".snapshot_manifest.json"


def _resolve_vault_root() -> Path:
    v = os.environ.get("CLAUDE_VAULT_ROOT")
    if v:
        return Path(v)
    for parent in [Path.cwd(), *Path.cwd().parents]:
        vr = parent / ".claude" / ".vault_root"
        if vr.exists():
            return Path(vr.read_text(encoding="utf-8").strip())
    return Path("C:/Users/Administrator/Documents/OmniCommand")


def _resolve_project_typ() -> str:
    cwd_str = str(Path.cwd()).replace("\\", "/")
    if "CenCoCo" in cwd_str or "cencoco" in cwd_str.lower():
        return "CenCoCo"
    return "DCSRE"


def _cache_dir() -> Path:
    for parent in [Path.cwd(), *Path.cwd().parents]:
        if (parent / ".claude").exists():
            return parent / ".claude" / "meta-cache"
    return Path.cwd() / ".claude" / "meta-cache"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _collect_sources(vault: Path, typ: str) -> list[tuple[Path, Path]]:
    """Return list of (src, rel_cache_path) pairs."""
    pairs = []
    for prefix, cache_sub in [
        (vault / "Meta" / "Universal", Path("Universal")),
        (vault / "Meta" / "Typen" / typ, Path("Typen") / typ),
    ]:
        if prefix.exists():
            for src in prefix.rglob("*"):
                if src.is_file():
                    rel = src.relative_to(prefix)
                    pairs.append((src, cache_sub / rel))
    return pairs


def cmd_dry_run() -> int:
    vault = _resolve_vault_root()
    typ = _resolve_project_typ()
    if not vault.exists():
        print(f"[meta_snapshot] ERROR: Vault nicht erreichbar: {vault}", file=sys.stderr)
        return 2
    pairs = _collect_sources(vault, typ)
    print(f"[meta_snapshot] --dry-run: {len(pairs)} Dateien gefunden (kein Kopieren)")
    print(f"  Vault:  {vault}")
    print(f"  Typ:    {typ}")
    return 0


def cmd_snapshot() -> int:
    vault = _resolve_vault_root()
    if not vault.exists():
        print(f"[meta_snapshot] ERROR: Vault nicht erreichbar: {vault}", file=sys.stderr)
        return 2
    typ = _resolve_project_typ()
    pairs = _collect_sources(vault, typ)
    cache = _cache_dir()
    files_map: dict[str, str] = {}
    copied = 0
    for src, rel in pairs:
        dest = cache / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        files_map[str(rel).replace("\\", "/")] = _sha256(dest)
        copied += 1
    manifest = {
        "file_count": copied,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_vault_path": str(vault).replace("\\", "/"),
        "files": files_map,
    }
    manifest_path = cache / MANIFEST_NAME
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[meta_snapshot] Snapshot: {copied} Dateien -> {cache}")
    print(f"  Manifest: {manifest_path}")
    return 0


def cmd_validate() -> int:
    cache = _cache_dir()
    manifest_path = cache / MANIFEST_NAME
    if not manifest_path.exists():
        print(f"[meta_snapshot] WARN: Kein Manifest gefunden: {manifest_path}", file=sys.stderr)
        return 0
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    mismatches = []
    for rel_str, expected_hash in manifest.get("files", {}).items():
        dest = cache / rel_str
        if not dest.exists():
            mismatches.append(f"MISSING: {rel_str}")
            continue
        actual = _sha256(dest)
        if actual != expected_hash:
            mismatches.append(f"MISMATCH: {rel_str}")
    if mismatches:
        print(f"[meta_snapshot] WARN: {len(mismatches)} Hash-Abweichungen gefunden:")
        for m in mismatches:
            print(f"  {m}")
    else:
        print(f"[meta_snapshot] --validate: alle {len(manifest.get('files', {}))} Dateien konsistent")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--dry-run" in args:
        sys.exit(cmd_dry_run())
    elif "--validate" in args:
        sys.exit(cmd_validate())
    else:
        sys.exit(cmd_snapshot())
