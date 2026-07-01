"""
t_script.py — /_T_script: fuehrt NUR die Tests EINER Stage aus (stage1..stage6).

User-Anforderung 2026-06-04: „eine einfache Moeglichkeit, wirklich NUR diese Tests
auszufuehren" — nicht die ganze Suite, sondern gezielt stage-N (Unit=1, Integration=3,
E2E=6). Loest `.claude/meta/implementation/stage_{N}.md` → `testbefehl` und faehrt
GENAU das. Setup/Teardown (Docker/Healthchecks) nur auf Wunsch (--setup/--teardown).

Das Test-Ziel pro Stage ist PROJEKT-CONFIG (der `testbefehl` in stage_{N}.md) — fuer ein
FE-Projekt z.B. der scoped Cypress-Lauf, fuer BE `dotnet test --filter ...`. t_script.py
ist projekt-agnostisch: es faehrt, was im stage_{N}.md steht.

DER MIX (User 2026-06-04): „nur die Tests, die fuer uns in der gesetzten Stage relevant sind".
= Stage-testbefehl-Template (HOW) X testSearch-relevante Tests (WHICH). Der stage_{N}.md-
`testbefehl` traegt einen Platzhalter (`<FQN>`/`<TestName>` .NET, `<SPEC>` Cypress/FE); die
relevanten Tests (= `coverage_map.covering_tests` aus dem I_orchestrate/IDF-testSearch) werden
hineinsubstituiert -> GENAU diese Tests laufen, nicht die ganze Suite. Tests via --tests=/
--tests-file= (dorthin schreibt der testSearch seine covering_tests).

USAGE (terminal, „nebenbei"):
    py .claude/scripts/t_script.py 3                       # ganze stage-3 testbefehl
    py .claude/scripts/t_script.py 3 --tests=MyTest1,MyTest2   # NUR diese relevanten Tests (Mix)
    py .claude/scripts/t_script.py 6 --tests-file=relevant.txt --setup --teardown  # FE-E2E + Infra
    py .claude/scripts/t_script.py 1 3 --dry-run          # mehrere Stages, nur Plan zeigen
Flags: --tests=A,B  --tests-file=F  --setup  --teardown  --dry-run  --meta-dir=DIR
Exit: 0 = alle gruen/Plan ok, 1 = Test-FAIL/Stage fehlt, 2 = Usage-Fehler.
"""

import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def resolve_stage_arg(arg):
    """'3' / 'stage3' / '--stage=6' -> int 1..6, sonst None."""
    m = re.search(r"([1-9])", str(arg))
    if not m:
        return None
    n = int(m.group(1))
    return n if 1 <= n <= 6 else None


def _extract_commands(block, section):
    """Liest die `commands:`-Liste unter `{section}:` (z.B. setup/teardown) aus dem
    Frontmatter-Block. Robust gegen `commands: []` (leer) + nachfolgende Subkeys."""
    lines = block.splitlines()
    out, in_section, in_commands = [], False, False
    for ln in lines:
        if re.match(r"^" + section + r":\s*$", ln):
            in_section, in_commands = True, False
            continue
        if in_section:
            if re.match(r"^\S", ln):       # Dedent auf Top-Level-Key -> Sektion zu Ende
                break
            if re.match(r"^\s+commands:\s*$", ln):
                in_commands = True
                continue
            if in_commands:
                m = re.match(r'^\s+-\s*"?(.*?)"?\s*$', ln)
                if m:
                    out.append(m.group(1).strip())
                elif re.match(r"^\s+\S+:", ln):  # naechster Subkey -> commands-Liste zu Ende
                    in_commands = False
    return out


def _parse_testbefehl(block):
    """testbefehl-Wert sauber extrahieren: gequotet (mit inneren \\\" + trailing
    YAML-Kommentar ' #...') ODER ungequotet. Der nachgestellte ' # ...'-Kommentar
    wird abgeschnitten (sonst landet er im Befehl)."""
    m = re.search(r'^testbefehl:\s*"(.*)"\s*(?:#.*)?$', block, re.M)  # gequotet
    if not m:
        m = re.search(r"^testbefehl:\s*([^\"\s#][^#]*?)\s*(?:#.*)?$", block, re.M)  # ungequotet
    if not m:
        return None
    # In den Stage-Files steht der Reminder-Kommentar oft INNERHALB der Quotes
    # (z.B. '...<TestName>\"  # IMMER Einzel-Test ... NIEMALS alle!'). Der gehoert NICHT
    # zum Befehl (Shell wuerde '#' eh als Kommentar werten) -> trailing ' #...' abschneiden.
    return re.sub(r"\s+#.*$", "", m.group(1)).strip()


def parse_stage(content):
    """stage_{N}.md-Frontmatter -> {name, testbefehl, setup_commands, teardown_commands}."""
    parts = content.split("---", 2)
    block = parts[1] if len(parts) >= 3 else content
    nm = re.search(r"^name:\s*(.+?)\s*$", block, re.M)
    return {
        "name": nm.group(1).strip() if nm else None,
        "testbefehl": _parse_testbefehl(block),
        "setup_commands": _extract_commands(block, "setup"),
        "teardown_commands": _extract_commands(block, "teardown"),
    }


def _meta_from_slices(handle):
    """Baue die meta-Struktur aus einem Vault-StageHandle (execute/setup/teardown-Slices).

    BL-392 AK-CONSUMER-REWRITE / W-SLICE-2: jeder Concern liegt in seinem eigenen
    Slice. testbefehl kommt aus dem execute-Slice, setup/teardown-Commands aus den
    gleichnamigen Slices, der Stage-Name aus _index. Spiegelt das parse_stage-dict
    (selbe Keys), nur aus den getrennten Slices statt aus einem Monolith-Block.
    """
    index_view = handle.slice_view("_index") or {}
    execute_view = handle.slice_view("execute") or {}
    setup_view = handle.slice_view("setup") or {}
    teardown_view = handle.slice_view("teardown") or {}

    def _commands(view):
        cmds = view.get("commands") if isinstance(view, dict) else None
        return [str(c) for c in cmds] if isinstance(cmds, (list, tuple)) else []

    name = index_view.get("name")
    testbefehl = execute_view.get("testbefehl")
    return {
        "name": str(name).strip() if name is not None else None,
        "testbefehl": str(testbefehl).strip() if testbefehl is not None else None,
        "setup_commands": _commands(setup_view),
        "teardown_commands": _commands(teardown_view),
    }


def load_stage_meta(n, meta_dir):
    """Loese die Stage-Meta VIA resolve_vault_stage (BL-392 AK-CONSUMER-REWRITE).

    Dual-Read (behavior-preserving): Vault-Slice-Satz wenn migriert, sonst der
    Legacy-Monolith. KEIN direkter `.claude/meta/implementation/stage_N.md`-Read mehr.

    - Vault-Slice-Satz vorhanden -> meta aus execute/setup/teardown-Slices.
    - Legacy-Fallback -> der Monolith-ROHTEXT (handle.legacy_path) wird mit dem
      bestehenden parse_stage-Regex gelesen, BYTE-IDENTISCH zum heutigen Verhalten
      (inkl. In-Quote-Kommentar-Abschnitt). `meta_dir` wird als legacy_meta_dir
      durchgereicht, sodass das heutige explizite --meta-dir-Verhalten erhalten bleibt.
    - Stage nicht aufloesbar -> None (Caller meldet "nicht gefunden", wie heute).
    """
    import resolve_vault_stage as rvs

    handle = rvs.resolve_stage(n, legacy_meta_dir=meta_dir)
    if handle is None:
        return None
    if handle.is_legacy:
        # Roh-Text-Parser auf GENAU die Legacy-Datei -> heutiges Verhalten unveraendert.
        with open(handle.legacy_path, encoding="utf-8", errors="replace") as fh:
            return parse_stage(fh.read())
    return _meta_from_slices(handle)


# Platzhalter im stage-testbefehl-Template, in die die relevanten Tests substituiert werden.
# .NET: <FQN>/<TestName> (dotnet --filter), Cypress/FE: <SPEC>, generisch <TEST>.
_PLACEHOLDERS = ["<FQN>", "<TestName>", "<SPEC>", "<TEST>"]


def has_placeholder(testbefehl):
    return any(p in (testbefehl or "") for p in _PLACEHOLDERS)


def build_test_commands(testbefehl, tests, join=False, sep=","):
    """Der MIX (User 2026-06-04): Stage-testbefehl-Template (HOW) x testSearch-relevante
    Tests (WHICH, aus coverage_map.covering_tests). Wenn `tests` gegeben UND das Template
    einen Platzhalter (<FQN>/<TestName>/<SPEC>) hat:
      - default: GENAU 1 Befehl pro relevantem Test (gut fuer .NET --filter).
      - join=True: 1 Befehl mit sep-verbundener Liste (gut fuer Cypress `--spec a,b`).
    Sonst der testbefehl unveraendert."""
    if not tests:
        return [testbefehl]
    ph = next((p for p in _PLACEHOLDERS if p in (testbefehl or "")), None)
    if not ph:
        return [testbefehl]  # kein Platzhalter -> nicht substituierbar (Caller warnt)
    if join:
        return [testbefehl.replace(ph, sep.join(tests))]
    return [testbefehl.replace(ph, t) for t in tests]


def load_tests(kv):
    """Relevante Tests aus --tests=A,B,C UND/ODER --tests-file=path (1 pro Zeile,
    # = Kommentar). Das ist die testSearch-Seite des Mix (covering_tests des I_orchestrate)."""
    tests = []
    if kv.get("tests"):
        tests += [t.strip() for t in kv["tests"].split(",") if t.strip()]
    if kv.get("tests-file"):
        try:
            with open(kv["tests-file"], encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    s = line.strip()
                    if s and not s.startswith("#"):
                        tests.append(s)
        except OSError:
            pass
    return tests


def build_plan(meta, with_setup, with_teardown, tests=None, join=False):
    """Run-Plan: [setup...] (opt) + Test-Befehl(e) + [teardown...] (opt). Default = nur Test.
    Bei `tests`: der Test-Schritt expandiert zu GENAU den relevanten Tests (Mix; join=1 Befehl)."""
    plan = []
    if with_setup:
        plan += [("setup", c) for c in meta["setup_commands"]]
    if meta.get("testbefehl"):
        for cmd in build_test_commands(meta["testbefehl"], tests or [], join=join):
            plan.append(("test", cmd))
    if with_teardown:
        plan += [("teardown", c) for c in meta["teardown_commands"]]
    return plan


def main(argv):
    flags = {a for a in argv if a.startswith("--") and "=" not in a}
    kv = dict(a[2:].split("=", 1) for a in argv if a.startswith("--") and "=" in a)
    stages = [s for s in (resolve_stage_arg(a) for a in argv if not a.startswith("--")) if s]
    if not stages:
        print("usage: t_script.py <stage 1-6> [<stage>...] [--tests=A,B] [--tests-file=F] "
              "[--join] [--setup] [--teardown] [--dry-run] [--meta-dir=DIR]")
        return 2

    meta_dir = kv.get("meta-dir", os.path.join(".claude", "meta", "implementation"))
    with_setup = "--setup" in flags
    with_teardown = "--teardown" in flags
    dry = "--dry-run" in flags
    join = "--join" in flags   # Cypress: 1 Lauf mit komma-verbundenen Specs (statt 1 Lauf je Spec)
    tests = load_tests(kv)     # testSearch-Seite des Mix (relevante covering_tests)
    overall = 0

    for n in stages:
        # BL-392 AK-CONSUMER-REWRITE: Stage-Resolution via resolve_vault_stage
        # (Dual-Read: Vault-Slice-Satz wenn migriert, sonst Legacy-Monolith im
        # --meta-dir). KEIN direkter stage_N.md-Read mehr.
        meta = load_stage_meta(n, meta_dir)
        if meta is None:
            print("[T_SCRIPT] stage_{}.md nicht gefunden (weder Vault-Slice noch Legacy-Monolith in {})".format(n, meta_dir))
            overall = 1
            continue
        if not meta["testbefehl"]:
            print("[T_SCRIPT] stage {} hat kein testbefehl-Feld (Vault-execute-Slice bzw. Legacy-Monolith in {})".format(n, meta_dir))
            overall = 1
            continue

        if tests and not has_placeholder(meta["testbefehl"]):
            print("[T_SCRIPT] [WARN] stage {}: --tests gegeben, aber testbefehl hat keinen "
                  "<FQN>/<TestName>/<SPEC>-Platzhalter -> nicht substituierbar; ganzer stage-testbefehl laeuft.".format(n))
        if not tests and has_placeholder(meta["testbefehl"]):
            # z.B. Cypress `--spec <SPEC>`: ohne --tests gaebe es einen nackten Platzhalter-Lauf -> skip.
            print("[T_SCRIPT] [WARN] stage {}: testbefehl hat einen <...>-Platzhalter aber keine --tests "
                  "-> uebersprungen (gib --tests=<spec/test>).".format(n))
            overall = 1
            continue
        plan = build_plan(meta, with_setup, with_teardown, tests, join=join)
        label = " | {} relevante Tests (Mix)".format(len(tests)) if tests and has_placeholder(meta["testbefehl"]) else ""
        print("=== Stage {} ({}){} ===".format(n, meta.get("name") or "", label))
        for kind, cmd in plan:
            print("  [{}] {}".format(kind, cmd))
        if dry:
            print("  (dry-run: nichts ausgefuehrt)")
            continue

        for kind, cmd in plan:
            rc = subprocess.call(cmd, shell=True)
            if rc != 0:
                print("[T_SCRIPT] {} FAIL (exit {}): {}".format(kind, rc, cmd))
                overall = 1
                if kind == "test":
                    break  # Test rot -> Rest dieser Stage abbrechen (Teardown ggf. separat fahren)
    return overall


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
