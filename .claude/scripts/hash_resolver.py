#!/usr/bin/env python3
"""
OmniCommand Hash Resolver (BL-113a C1).

CLI: python3 hash_resolver.py --name <NAME> --ebene <L1|L2|L3> [--hash-length N]

stdout: {normalize(name)}${h1}[_{h2}[_{h3}]].md

Exit-Codes:
    0 success
    1 detached HEAD (AK-9a)
    2 kein git-Repo / unknown ebene (AK-10a)
    3 missing --name
    4 invalid --hash-length

AK-Mapping:
    AK-1a  Deterministischer 3-stufiger Hash (L1/L2/L3, Separator "_", "$"-Trenner)
    AK-2a  normalize_branch idempotent (non-alphanumeric -> "-", lowercase)
    AK-6a  main-Branch erhaelt regulaeren 4-char-Hash (kein Sonderfall)
    AK-7a  OMNI_HASH_OVERRIDE Hash-WERT-Override (ADR-B, I3), gated via
           --allow-override ODER CLAUDE_TEST_MODE=true, mit stderr-WARN
    AK-9a  Detached HEAD -> exit 1 + stderr (strict fail-loud)
    AK-10a kein git-Repo -> exit 2 + stderr (strict fail-loud)
    ADR-A  hashlib.sha256, [:n] Hex
    ADR-B  OMNI_HASH_OVERRIDE nur mit --allow-override oder CLAUDE_TEST_MODE, IMMER geloggt
    ADR-G  Separator "_" zwischen Hash-Ebenen, "$" zwischen Name und Hash
    ADR-J  hash_length optional via ENV/Config, Default 4
"""

import argparse
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False


def normalize_branch(name: str) -> str:
    """Non-alphanumeric -> "-", lowercase, strip leading/trailing dashes. Idempotent."""
    return re.sub(r'[^a-z0-9-]', '-', name.lower()).strip('-')


def _hash(text: str, n: int = 4) -> str:
    """SHA256[:n] lowercase hex (ADR-A)."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:n]


def _git(args):
    """Run git command; return stdout stripped or empty string on failure."""
    try:
        result = subprocess.run(
            ['git'] + args, capture_output=True, text=True, check=False
        )
        if result.returncode != 0:
            return ''
        return result.stdout.strip()
    except (FileNotFoundError, OSError):
        return ''


def _is_git_repo() -> bool:
    """True when cwd is inside a git working tree (AK-10a)."""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--is-inside-work-tree'],
            capture_output=True, text=True, check=False,
        )
        return result.returncode == 0 and result.stdout.strip() == 'true'
    except (FileNotFoundError, OSError):
        return False


def _is_detached_head() -> bool:
    """True when HEAD is detached (git symbolic-ref HEAD exits non-zero)."""
    try:
        result = subprocess.run(
            ['git', 'symbolic-ref', 'HEAD'],
            capture_output=True, text=True, check=False,
        )
        return result.returncode != 0
    except (FileNotFoundError, OSError):
        return True


def _get_override() -> str:
    """Return OMNI_HASH_OVERRIDE value when permitted; '' otherwise. Emits
    stderr WARN per ADR-B regardless of outcome when ENV is set."""
    override = os.environ.get('OMNI_HASH_OVERRIDE')
    if not override:
        return ''
    allow_flag = os.environ.get('_OMNI_ALLOW_OVERRIDE') == '1'
    test_mode = os.environ.get('CLAUDE_TEST_MODE') == 'true'
    if allow_flag or test_mode:
        sys.stderr.write(
            '[WARN] hash override active via OMNI_HASH_OVERRIDE\n'
        )
        return override
    sys.stderr.write(
        '[WARN] OMNI_HASH_OVERRIDE ignored (use --allow-override in test mode)\n'
    )
    return ''


def _get_hash_length() -> int:
    """Resolve hash length: ENV TEST_HASH_LENGTH > config/project.yaml > 4 (ADR-J)."""
    env_val = os.environ.get('TEST_HASH_LENGTH')
    if env_val:
        return int(env_val)
    cfg = Path('config/project.yaml')
    if _HAS_YAML and cfg.exists():
        try:
            with cfg.open('r', encoding='utf-8') as fh:
                data = yaml.safe_load(fh) or {}
            if isinstance(data, dict) and 'hash_length' in data:
                return int(data['hash_length'])
        except (yaml.YAMLError, OSError, ValueError):
            pass
    return 4


def _get_target_ref() -> str:
    """L1 reference: ENV MANIFEST_TARGET > git remote origin > 'local'."""
    env_val = os.environ.get('MANIFEST_TARGET')
    if env_val:
        return env_val
    remote = _git(['remote', 'get-url', 'origin'])
    return remote or 'local'


def _get_feature_ref(name: str) -> str:
    """L2 reference: ENV MANIFEST_FEATURE > provided name."""
    return os.environ.get('MANIFEST_FEATURE') or name


def _get_worktree_ref() -> str:
    """L3 reference: ENV MANIFEST_WORKTREE (CI-Escape) > current branch.

    Strict fail-loud when no ENV is present: AK-10a (not a git repo -> exit 2),
    AK-9a (detached HEAD -> exit 1)."""
    env_val = os.environ.get('MANIFEST_WORKTREE')
    if env_val:
        return env_val
    if not _is_git_repo():
        sys.stderr.write('[ERROR] Not a git repository (AK-10a)\n')
        sys.exit(2)
    if _is_detached_head():
        sys.stderr.write(
            '[ERROR] Detached HEAD state - use MANIFEST_WORKTREE env to override (AK-9a)\n'
        )
        sys.exit(1)
    branch = _git(['rev-parse', '--abbrev-ref', 'HEAD'])
    return branch or 'local'


def resolve(name: str, ebene: str, hash_length: int) -> str:
    """Build {normalize(name)}${h1}[_{h2}[_{h3}]].md per ebene (ADR-G).

    If OMNI_HASH_OVERRIDE is active (ADR-B, I3, AK-7a), it replaces the
    entire hash-block (everything between '$' and '.md'); per-ebene
    sub-hashes are NOT computed in that case."""
    normalized = normalize_branch(name)
    override = _get_override()
    if override:
        return f'{normalized}${override}.md'
    h1 = _hash(normalize_branch(_get_target_ref()), hash_length)
    if ebene == 'L1':
        return f'{normalized}${h1}.md'
    h2 = _hash(normalize_branch(_get_feature_ref(name)), hash_length)
    if ebene == 'L2':
        return f'{normalized}${h1}_{h2}.md'
    h3 = _hash(normalize_branch(_get_worktree_ref()), hash_length)
    if ebene == 'L3':
        return f'{normalized}${h1}_{h2}_{h3}.md'
    print(f'Unknown ebene: {ebene}', file=sys.stderr)
    sys.exit(2)


def main():
    parser = argparse.ArgumentParser(description='OmniCommand Hash Resolver (BL-113a)')
    parser.add_argument('--name', required=False)
    parser.add_argument('--ebene', required=False)
    parser.add_argument('--hash-length', type=int, required=False)
    parser.add_argument(
        '--allow-override', action='store_true',
        help='Permit OMNI_HASH_OVERRIDE to replace the hash block (ADR-B, AK-7a).',
    )
    args = parser.parse_args()

    if args.allow_override:
        os.environ['_OMNI_ALLOW_OVERRIDE'] = '1'

    if not args.name:
        print('Missing --name', file=sys.stderr)
        sys.exit(3)
    if args.ebene not in ('L1', 'L2', 'L3'):
        print(f'Unknown ebene: {args.ebene}', file=sys.stderr)
        sys.exit(2)

    if args.hash_length is not None:
        if args.hash_length < 1 or args.hash_length > 64:
            print(f'Invalid --hash-length: {args.hash_length}', file=sys.stderr)
            sys.exit(4)
        hash_length = args.hash_length
    else:
        hash_length = _get_hash_length()

    print(resolve(args.name, args.ebene, hash_length))


if __name__ == '__main__':
    main()
