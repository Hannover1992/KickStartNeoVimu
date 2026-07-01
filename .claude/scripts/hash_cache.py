#!/usr/bin/env python3
"""
OmniCommand Hash Cache (BL-113a C4).

CLI:
    python3 hash_cache.py --get <NAME> --ebene <L1|L2|L3>
    python3 hash_cache.py --invalidate <NAME>
    python3 hash_cache.py --list

Python:
    from hash_cache import get_cached

AK-Mapping:
    AK-3a  Cache-Hit < 5ms (in-file YAML-Block, fcntl.LOCK_SH)
    AK-4a  Cache-Invalidierung: mtime-Mismatch -> Re-Read; Branch-Wechsel fuehrt
           ueber hash_resolver zu neuem L3-Pfad (neue Cache-Datei).
    AK-5a  Atomic-Write via fcntl.LOCK_EX, serialisiert parallele Writes.
"""

import argparse
import fcntl
import os
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent
ANALYSIS_DIR = ROOT_DIR / '.claude' / 'analysis'
LEGACY_PATH = ANALYSIS_DIR / '_session_params.md'
RESOLVER = SCRIPT_DIR / 'hash_resolver.py'

BEGIN = '# HASH_CACHE_BEGIN'
END = '# HASH_CACHE_END'

_MTIME_CACHE = {'path': None, 'mtime': None, 'data': None}


def _lock_shared(f): fcntl.flock(f.fileno(), fcntl.LOCK_SH)
def _lock_exclusive(f): fcntl.flock(f.fileno(), fcntl.LOCK_EX)
def _unlock(f): fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def _session_params_path() -> Path:
    try:
        result = subprocess.run(
            [sys.executable, str(RESOLVER), '--name', '_session_params', '--ebene', 'L3'],
            capture_output=True, text=True, check=True,
        )
        hashed = result.stdout.strip()
        candidate = ANALYSIS_DIR / hashed
        if candidate.exists():
            return candidate
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        pass
    return LEGACY_PATH


def _parse_block(text: str) -> dict:
    m = re.search(rf'{re.escape(BEGIN)}\n(.*?)\n{re.escape(END)}', text, re.DOTALL)
    if not m:
        return {}
    body = m.group(1)
    out = {}
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith('#') or line.endswith(':'):
            continue
        mm = re.match(r'^([A-Za-z0-9_\-.]+):\s*"([^"]*)"\s*$', line)
        if mm:
            out[mm.group(1)] = mm.group(2)
    return out


def _render_block(cache: dict) -> str:
    lines = [BEGIN, 'hash_values:']
    for k in sorted(cache.keys()):
        lines.append(f'  {k}: "{cache[k]}"')
    lines.append(END)
    return '\n'.join(lines)


def _read_cache() -> dict:
    path = _session_params_path()
    if not path.exists():
        return {}
    mtime = path.stat().st_mtime
    if _MTIME_CACHE['path'] == path and _MTIME_CACHE['mtime'] == mtime:
        return dict(_MTIME_CACHE['data'])
    with open(path, 'r', encoding='utf-8') as f:
        _lock_shared(f)
        try:
            text = f.read()
        finally:
            _unlock(f)
    data = _parse_block(text)
    _MTIME_CACHE.update(path=path, mtime=mtime, data=dict(data))
    return data


def _write_cache(cache: dict) -> None:
    path = _session_params_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text('# Session-Parameter\n', encoding='utf-8')
    with open(path, 'r+', encoding='utf-8') as f:
        _lock_exclusive(f)
        try:
            text = f.read()
            block = _render_block(cache)
            if BEGIN in text and END in text:
                new = re.sub(
                    rf'{re.escape(BEGIN)}\n.*?\n{re.escape(END)}',
                    block.replace('\\', r'\\'),
                    text, count=1, flags=re.DOTALL,
                )
            else:
                new = text.rstrip() + '\n\n' + block + '\n'
            f.seek(0)
            f.truncate()
            f.write(new)
            f.flush()
            os.fsync(f.fileno())
        finally:
            _unlock(f)
    _MTIME_CACHE.update(path=None, mtime=None, data=None)


def get_cached(name: str, ebene: str) -> str:
    key = f'{name}_{ebene}'
    cache = _read_cache()
    if key in cache:
        return cache[key]
    result = subprocess.run(
        [sys.executable, str(RESOLVER), '--name', name, '--ebene', ebene],
        capture_output=True, text=True, check=True,
    )
    value = result.stdout.strip()
    cache = _read_cache()
    cache[key] = value
    _write_cache(cache)
    return value


def invalidate(name: str) -> int:
    cache = _read_cache()
    prefix = f'{name}_'
    keys = [k for k in cache if k.startswith(prefix)]
    for k in keys:
        del cache[k]
    if keys:
        _write_cache(cache)
    return len(keys)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--get', metavar='NAME')
    p.add_argument('--ebene', choices=['L1', 'L2', 'L3'])
    p.add_argument('--invalidate', metavar='NAME')
    p.add_argument('--list', action='store_true')
    args = p.parse_args()

    if args.get:
        if not args.ebene:
            print('--get requires --ebene', file=sys.stderr)
            sys.exit(2)
        print(get_cached(args.get, args.ebene))
    elif args.invalidate:
        n = invalidate(args.invalidate)
        print(f'invalidated {n} entries for {args.invalidate}')
    elif args.list:
        cache = _read_cache()
        if not cache:
            print('(empty)')
        else:
            for k in sorted(cache):
                print(f'{k}: {cache[k]}')
    else:
        p.print_help()
        sys.exit(2)


if __name__ == '__main__':
    main()
