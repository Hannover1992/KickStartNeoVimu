#!/usr/bin/env python3
"""resolve_vault_stage.py — BL-392 batch_2 (AK-GLOB): glob-faehiger Stage-Slice-Resolver.

Schwester-Resolver zu `resolve_vault_meta` (W-GLOB-2-Adjudikation, Option B):
`resolve_vault_meta.resolve_meta(rel_path)` bleibt strukturell SINGLE-FILE und
UNBERUEHRT (ein rel_path -> ein path.exists()-Treffer ueber sechs Tiers, kein glob).
Eine atomisierte Stage ist aber ein VERZEICHNIS aus den 8 kanonischen Slice-Dateien
(stage_slice_schema.CANONICAL_SLICES). Dieser Resolver kennt die kanonische Vault-
Stage-Heimat `{VAULT}/Stage/stage_N_<name>/` (Postfix-Glob, genau-1-Match je Nummer)
und liefert:

  - `resolve_stage(n) -> StageHandle | None` — den Slice-SATZ einer Stage
    (Verzeichnis + Map concern->Pfad ueber die 8 Slices).
  - `resolve_slice(n, slice_name) -> Path | None` — den EINZEL-Slice gezielt
    (single unit of work: TDD-Green ruft resolve_slice(3, "execute")).
  - `StageHandle` traegt: stage_dir, number, name, slice_paths + resolve_slice(name)
    + slice_view(name) (in-memory Frontmatter) + is_legacy.

DUAL-READ-FALLBACK (W-VAULT-1, Backward-Compat, KEIN atomarer Cut):
  Existiert KEIN Vault-Slice-Verzeichnis `{VAULT}/Stage/stage_N_*/` (Migration noch
  nicht gelaufen), faellt resolve_stage — analog resolve_vault_meta Tier-6-Legacy —
  auf den Legacy-Monolith `.claude/meta/implementation/stage_N.md` zurueck: es parst
  dessen Frontmatter und liefert einen StageHandle mit IN-MEMORY aus dem Monolith
  abgeleiteten Slice-Views (kein Schreiben, kein echtes Verzeichnis). So koexistieren
  migrierte (Vault-Slice) und nicht-migrierte (Legacy-Monolith) Stages waehrend der
  Umstellung. Vault gewinnt IMMER vor Legacy (Praezedenz).

VAULT-ROOT via SSoT: IMMER ueber resolve_vault_root() (kanonische ARCH-N8-SSoT),
nie ueber einen literalen Pfad (BL-374-Defekt-Klasse vermeiden).

read-only: dieser Resolver mutiert weder Vault noch State. fail-safe: fehlende
Stage + fehlender Legacy -> None (kein Crash).

Exit codes (CLI):
  0 = aufgeloest (Stage-Verzeichnis ODER Legacy-Fallback)
  2 = nicht gefunden
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Die 8 kanonischen Slices sind in stage_slice_schema (batch_1) definiert —
# single source, damit Resolver + Validator nie auseinanderlaufen.
from stage_slice_schema import CANONICAL_SLICES


# ---------------------------------------------------------------------------
# Vault-Root-SSoT (kein hardcoded Pfad — BL-374-Klasse)
# ---------------------------------------------------------------------------


def resolve_vault_root() -> Path:
    """Resolve den Vault-Root ueber die kanonische SSoT (ARCH-N8).

    Delegiert an resolve_vault_root.py (env CLAUDE_VAULT_ROOT primaer ->
    OBSIDIAN_VAULT_PATH -> .vault_root-pin -> vault-routing.json -> Heuristik).
    ImportError (SSoT fehlt) propagiert = fail-safe (lieber lauter Fehler als
    falsch-geratener Vault). Exakt das Muster aus resolve_vault_meta.resolve_vault_root.
    """
    import resolve_vault_root as rvr  # kanonische SSoT — kein hardcoded Default
    return Path(rvr.resolve_vault_root())


# ---------------------------------------------------------------------------
# Monolith -> 8-Slice-Feld-Verteilung (Dual-Read in-memory Views, W-VAULT-1)
# ---------------------------------------------------------------------------

# Pro Slice die Monolith-Frontmatter-Felder, die in diesen Slice gehoeren
# (verlustfreie Verteilung — Spiegel der AK-MIGRATION-Feld-Verteilung, hier nur
# fuer den IN-MEMORY-Legacy-View; das echte Schreiben ist batch_3+).
# "execute" und die anderen Lifecycle-Slices ziehen ihre Sub-dicts direkt aus dem
# Monolith (setup/teardown/health_check sind dort bereits geschachtelt).
_LEGACY_SCALAR_FIELDS = {
    "_index": ("stufe", "name", "fokus", "blueprint_perspektive", "kanarienvogel_zone"),
    "execute": (
        "testbefehl",
        "test_projekte",
        "testpfad",
        "fanout",
        "mocks_erlaubt",
        "testtyp",
    ),
    "resources": (
        "infrastruktur",
        "ressourcen_constraints",
        "max_container_parallel",
        "container_isolation",
        "flaky_risiko",
        "db_zustand_setup_pflicht",
    ),
    "concurrency_class": (
        "concurrency_class",
        "concurrency_depends_on",
        "concurrency_rationale",
    ),
    "exit_criteria": ("exit_criteria",),
}

# Diese Slices sind im Monolith bereits als geschachteltes dict vorhanden — der
# in-memory View IST dieses Sub-dict.
_LEGACY_NESTED_SLICES = ("setup", "teardown", "health_check")


def _legacy_slice_view(slice_name: str, monolith_fm: dict) -> Optional[dict]:
    """Leite den in-memory Frontmatter-View eines Slices aus dem Monolith ab.

    Verlustfreie 1:N-Verteilung: Skalar-Felder werden in den Concern-Slice kopiert,
    geschachtelte Sektionen (setup/teardown/health_check) direkt uebernommen.
    `exit_criteria` ist im Monolith eine Liste -> wird als {qg-Surrogat} unter dem
    eigenen Key gefuehrt, damit der Concern erhalten bleibt.
    """
    monolith_fm = monolith_fm or {}

    if slice_name in _LEGACY_NESTED_SLICES:
        value = monolith_fm.get(slice_name)
        # Fehlt die Sektion im Monolith -> leerer View (Stage hatte den Concern nicht).
        return value if isinstance(value, dict) else {}

    fields = _LEGACY_SCALAR_FIELDS.get(slice_name)
    if fields is None:
        return None
    view: dict = {}
    for f in fields:
        if f in monolith_fm:
            view[f] = monolith_fm[f]
    return view


# ---------------------------------------------------------------------------
# StageHandle
# ---------------------------------------------------------------------------


@dataclass
class StageHandle:
    """Aufgeloeste Stage: Verzeichnis + Slice-Pfade ODER in-memory Legacy-Views.

    - number:      Stage-Nummer.
    - name:        Postfix-Name (Vault: aus dem Verzeichnis; Legacy: aus dem
                   Monolith-`name`-Feld, sonst "").
    - stage_dir:   Path des Vault-Stage-Verzeichnisses, ODER None bei Legacy-Fallback.
    - slice_paths: Map concern -> Pfad ueber die 8 Slices (nur Vault; bei Legacy leer).
    - is_legacy:   True gdw. der Handle aus dem Legacy-Monolith stammt (in-memory).
    - legacy_path: Path des Legacy-Monolith `.claude/meta/implementation/stage_N.md`
                   (nur Legacy; None bei Vault). Damit ein Consumer, der heute den
                   Monolith-ROHTEXT mit eigenem Parser liest (t_script.parse_stage),
                   im Dual-Read-Fallback byte-identisch auf GENAU diese Datei
                   weiterlesen kann (Behavior-preserving, BL-392 AK-CONSUMER-REWRITE).
    - _legacy_fm:  das geparste Monolith-Frontmatter (nur Legacy; intern fuer slice_view).
    """

    number: int
    name: str
    stage_dir: Optional[Path] = None
    slice_paths: dict[str, Path] = field(default_factory=dict)
    is_legacy: bool = False
    legacy_path: Optional[Path] = None
    _legacy_fm: Optional[dict] = None

    def resolve_slice(self, slice_name: str) -> Optional[Path]:
        """Einzel-Slice-Pfad (single unit of work). None bei unbekanntem Slice ODER Legacy.

        Bei Legacy-Fallback gibt es keinen Datei-Pfad (in-memory) -> None; der
        Inhalt kommt dann ueber `slice_view`.
        """
        return self.slice_paths.get(slice_name)

    def slice_view(self, slice_name: str) -> Optional[dict]:
        """In-memory Frontmatter-View eines Slices.

        - Vault-Handle: liest das {slice}.md-Frontmatter von der Platte (read-only).
        - Legacy-Handle: leitet den View aus dem Monolith-Frontmatter ab.
        None gdw. der Slice nicht kanonisch ist ODER (Vault) die Datei fehlt.
        """
        if slice_name not in CANONICAL_SLICES:
            return None
        if self.is_legacy:
            return _legacy_slice_view(slice_name, self._legacy_fm or {})
        path = self.slice_paths.get(slice_name)
        if path is None or not path.exists():
            return None
        return _parse_frontmatter(path)


# ---------------------------------------------------------------------------
# Frontmatter-Parsing (Spiegel resolve_vault_meta/tdd_stages_ready)
# ---------------------------------------------------------------------------


def _parse_frontmatter(path: Path) -> Optional[dict]:
    """Lies das YAML-Frontmatter (zwischen den ersten zwei '---') aus path.

    None wenn die Datei fehlt ODER kein Frontmatter-Block da ist. utf-8 mit
    errors='replace' (robust gegen handgeschriebene Umlaute).
    """
    if not path.exists() or not path.is_file():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    fm_lines: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        fm_lines.append(line)
    import yaml

    try:
        data = yaml.safe_load("\n".join(fm_lines))
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


# ---------------------------------------------------------------------------
# Legacy-Monolith-Lokalisierung (Tier-6-Aequivalent, .claude/meta/implementation/)
# ---------------------------------------------------------------------------


def _resolve_legacy_monolith(n: int, legacy_meta_dir: Optional[Path] = None) -> Optional[Path]:
    """Finde `.claude/meta/implementation/stage_{n}.md` (cwd-Walkup ODER expliziter Dir).

    Default (legacy_meta_dir=None): exakt der resolve_vault_meta-Tier-6-Mechanismus —
    vom cwd nach oben laufen und das erste existierende
    .claude/meta/implementation/stage_N.md nehmen (der redeploy-populated Legacy-Pfad).
    Garantiert, dass ein nicht-migrierter Stage nicht stillschweigend verschwindet, bis
    die Vault-Migration (batch_3+) lief.

    legacy_meta_dir gesetzt (BL-392 AK-CONSUMER-REWRITE): ein Consumer mit einem
    expliziten Meta-Verzeichnis (t_script `--meta-dir`, tdd_stages_ready `--target-dir`)
    reicht es hier durch; der Dual-Read-Fallback liest `stage_{n}.md` aus GENAU diesem
    Verzeichnis (statt cwd-Walkup). So bleibt das heutige explizite-Dir-Verhalten der
    Consumer byte-identisch, nur via Resolver geroutet.
    """
    if legacy_meta_dir is not None:
        candidate = Path(legacy_meta_dir) / f"stage_{n}.md"
        return candidate if candidate.exists() else None
    rel = Path(".claude") / "meta" / "implementation" / f"stage_{n}.md"
    for parent in [Path.cwd(), *Path.cwd().parents]:
        candidate = parent / rel
        if candidate.exists():
            return candidate
    return None


# ---------------------------------------------------------------------------
# Glob-Resolution (der Kern — genau-1-Match je Nummer, W-GLOB-2)
# ---------------------------------------------------------------------------


def _glob_stage_dir(vault_root: Path, n: int) -> Optional[Path]:
    """Globt `{vault_root}/Stage/stage_{n}_*/` und liefert das EINE Match-Verzeichnis.

    genau-1-Match-Semantik:
      - 0 Treffer -> None (Caller faellt auf Legacy zurueck).
      - 1 Treffer -> dieses Verzeichnis.
      - >1 Treffer -> ValueError (Ambiguitaet, kein stiller Zufalls-Pick).
    fail-safe: existiert `{vault_root}/Stage/` nicht, -> None (kein Crash).
    """
    stage_root = vault_root / "Stage"
    if not stage_root.exists() or not stage_root.is_dir():
        return None
    matches = sorted(
        d for d in stage_root.glob(f"stage_{n}_*") if d.is_dir()
    )
    if not matches:
        return None
    if len(matches) > 1:
        names = ", ".join(d.name for d in matches)
        raise ValueError(
            f"Ambiguitaet: {len(matches)} Stage-Verzeichnisse fuer Nummer {n} "
            f"({names}). Genau-1-Match erwartet (BL-392 AK-GLOB)."
        )
    return matches[0]


def _stage_name_from_dir(stage_dir: Path, n: int) -> str:
    """Extrahiere den Postfix-Namen aus `stage_{n}_<name>` (sonst "")."""
    prefix = f"stage_{n}_"
    name = stage_dir.name
    return name[len(prefix):] if name.startswith(prefix) else ""


def _build_vault_handle(stage_dir: Path, n: int) -> StageHandle:
    """Baue einen Vault-StageHandle: slice_paths = Map concern -> {slice}.md-Pfad."""
    slice_paths = {name: stage_dir / f"{name}.md" for name in CANONICAL_SLICES}
    return StageHandle(
        number=n,
        name=_stage_name_from_dir(stage_dir, n),
        stage_dir=stage_dir,
        slice_paths=slice_paths,
        is_legacy=False,
    )


def _build_legacy_handle(monolith_path: Path, n: int) -> Optional[StageHandle]:
    """Baue einen in-memory Legacy-StageHandle aus dem Monolith-Frontmatter.

    legacy_path traegt den realen Monolith-Pfad, damit ein Consumer mit eigenem
    Roh-Text-Parser (t_script.parse_stage) im Fallback byte-identisch weiterliest.
    """
    fm = _parse_frontmatter(monolith_path)
    if fm is None:
        return None
    name = str(fm.get("name", "")) if fm.get("name") is not None else ""
    return StageHandle(
        number=n,
        name=name,
        stage_dir=None,         # in-memory: kein echtes Verzeichnis
        slice_paths={},         # Legacy: keine Datei-Pfade (Inhalt via slice_view)
        is_legacy=True,
        legacy_path=monolith_path,
        _legacy_fm=fm,
    )


# ---------------------------------------------------------------------------
# Oeffentliche API
# ---------------------------------------------------------------------------


def resolve_stage(
    n: int,
    vault_root: Optional[Path] = None,
    legacy_meta_dir: Optional[Path] = None,
) -> Optional[StageHandle]:
    """Loese die Stage `n` auf: Vault-Slice-Satz, sonst Legacy-Monolith, sonst None.

    1. Glob `{VAULT}/Stage/stage_{n}_*/` (genau-1-Match; >1 = ValueError).
       Treffer -> Vault-StageHandle (slice_paths ueber die 8 Slices).
    2. Kein Vault-Treffer -> Dual-Read-Fallback: `.claude/meta/implementation/
       stage_{n}.md` (cwd-Walkup; ODER aus `legacy_meta_dir`, falls gesetzt) ->
       in-memory Legacy-StageHandle (mit legacy_path).
    3. Weder noch -> None (fail-safe).

    read-only. Vault gewinnt IMMER vor Legacy (Praezedenz). `legacy_meta_dir`
    (BL-392 AK-CONSUMER-REWRITE) richtet den Dual-Read-Fallback auf ein explizites
    Consumer-Meta-Verzeichnis (t_script `--meta-dir` / tdd_stages_ready
    `--target-dir`); None = heutiges cwd-Walkup-Verhalten (unveraendert).
    """
    if vault_root is None:
        vault_root = resolve_vault_root()

    stage_dir = _glob_stage_dir(vault_root, n)  # kann ValueError werfen (Ambiguitaet)
    if stage_dir is not None:
        return _build_vault_handle(stage_dir, n)

    legacy = _resolve_legacy_monolith(n, legacy_meta_dir=legacy_meta_dir)
    if legacy is not None:
        return _build_legacy_handle(legacy, n)

    return None


def resolve_slice(
    n: int,
    slice_name: str,
    vault_root: Optional[Path] = None,
    legacy_meta_dir: Optional[Path] = None,
) -> Optional[Path]:
    """Einzel-Slice-Pfad fuer Stage `n` (single unit of work).

    None gdw. die Stage nicht aufloesbar ist, der Slice nicht kanonisch ist, ODER
    der Handle ein Legacy-Fallback ist (in-memory, kein Datei-Pfad — Inhalt via
    StageHandle.slice_view). Genau das, was ein TDD-Green-Worker braucht: NUR den
    einen execute.md-Pfad.
    """
    handle = resolve_stage(n, vault_root=vault_root, legacy_meta_dir=legacy_meta_dir)
    if handle is None:
        return None
    return handle.resolve_slice(slice_name)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: Optional[list[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Glob-faehiger Stage-Slice-Resolver (BL-392 AK-GLOB). "
                    "Resolved {VAULT}/Stage/stage_N_<name>/ ODER Legacy-Monolith-Fallback."
    )
    parser.add_argument("number", type=int, help="Stage-Nummer (1..N)")
    parser.add_argument(
        "--slice",
        metavar="SLICE_NAME",
        default=None,
        help=f"Einzel-Slice-Pfad statt des ganzen Satzes ({'/'.join(CANONICAL_SLICES)})",
    )
    args = parser.parse_args(argv)

    try:
        handle = resolve_stage(args.number)
    except ValueError as exc:
        print(f"AMBIGUOUS: {exc}", file=sys.stderr)
        return 2

    if handle is None:
        print(f"NOT_FOUND: keine Stage {args.number} (Vault-Slice ODER Legacy-Monolith)", file=sys.stderr)
        return 2

    if args.slice is not None:
        path = handle.resolve_slice(args.slice)
        if path is None:
            if handle.is_legacy:
                print(
                    f"LEGACY: Stage {args.number} via Legacy-Monolith (in-memory, kein "
                    f"Slice-Pfad). Inhalt nur via slice_view('{args.slice}').",
                    file=sys.stderr,
                )
            else:
                print(f"NOT_FOUND: Slice '{args.slice}' (nicht kanonisch?)", file=sys.stderr)
            return 2
        print(path)
        return 0

    # Ganzer Satz.
    if handle.is_legacy:
        print(f"LEGACY stage_{args.number} (in-memory aus .claude/meta/implementation/)")
    else:
        print(f"STAGE stage_{args.number}_{handle.name} -> {handle.stage_dir}")
        for name in CANONICAL_SLICES:
            print(f"  {name}: {handle.slice_paths[name]}")
    return 0


if __name__ == "__main__":
    # Windows-stdout default cp1252 -> Umlaute crashen. utf-8 erzwingen, fail-safe.
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    sys.exit(main(sys.argv[1:]))
