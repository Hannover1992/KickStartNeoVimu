#!/usr/bin/env python3
"""write_surface.py — Zwei-Surface-Diskriminator + Code-Write-cwd-relativ-Resolver
(BL-317 sub_batch_5, AK-7, two-surface-resolution).

MECHANISMUS-PRIMITIV, kein Pipeline-Umbau. Stellt zwei reine Funktionen bereit:

  classify_write_surface(path, vault_root) -> "vault" | "code"
      Der (a)/(b)-Diskriminator. EXAKT der guard_vault_write_lock-Test (Reuse):
      vault gdw os.path.normcase(abspath(path)) mit normcase(abspath(vault_root))
      beginnt — entlang der os.sep-Grenze (gegen Praefix-Kollision wie
      OmniCommandX vs OmniCommand). Sonst "code".

  resolve_code_write(path, worktree_cwd, surface=None) -> path
      Surface=code  : relativer Pfad wird gegen worktree_cwd aufgeloest (sodass er
                      im Worktree statt im Main-Tree landet); abs-Pfade bleiben abs.
      Surface=vault : Pfad UNVERAENDERT abs zurueck (G0-Domaene, BL-334-Lock).

Spike-Befund (BL-317): isolation:'worktree' isoliert nur den git-Kontext, NICHT
abs-Datei-Writes. Damit Code-Writes worktree-isoliert sind, muessen sie cwd/
worktree-relativ aufgeloest werden; Vault-State-Writes bleiben abs + G0.

  Scope G3 deckt NUR (a) Code-Writes.  (b) Vault-Writes = BL-334/G0 (vault_lock).

DORMANT-FORWARD (NICHT in SB-5 verdrahtet): die LIVE-Durchsetzung, dass ALLE
Build-Worker-Code-Writes durch resolve_code_write gehen, ist eine Verhaltens-
aenderung an der Pipeline und ein Multi-Worktree-Effekt (N>=2). Bei N=1 (heute)
existiert nur 1 Tree, also kein Isolations-Durchbruch akut. write_surface.py
liefert das MECHANISMUS-Primitiv; die Pipeline-weite Durchsetzung ist dormant
und an die BL-230-Wellen-Phase forward-delegiert. KEIN bestehender Resolver
(resolve_bl_path / resolve_vault_root / current_context) wird hier veraendert.

Konsistenz (AK-7, kein Drift): die Surface-Entscheidung wird ueber denselben
Normalisierer (_norm) wie guard_vault_write_lock.py getroffen. Wenn der Guard
importierbar ist, wird SEIN _norm direkt wiederverwendet (Single-Source); sonst
greift ein bit-identischer lokaler Fallback.
"""

import os

VAULT = "vault"
CODE = "code"


def _norm(p):
    """Absolut + case-insensitive (Windows) normalisiert, fuer Praefix-Match.

    Wiederverwendung des guard_vault_write_lock-Normalisierers (Single-Source,
    kein Drift). Bit-identischer lokaler Fallback falls der Guard nicht
    importierbar ist (z.B. isolierter Test-Pfad)."""
    try:
        import guard_vault_write_lock as _guard
        return _guard._norm(p)
    except Exception:
        return os.path.normcase(os.path.abspath(str(p)))


def classify_write_surface(path, vault_root):
    """Zwei-Surface-Diskriminator: "vault" gdw `path` unter `vault_root` liegt,
    sonst "code". EXAKT der guard_vault_write_lock-Match (Z133-140): normcase+
    abspath, Praefix entlang os.sep-Grenze (gegen Kollision OmniCommandX).

    vault_root None/leer -> "code" (kein aufloesbarer Vault -> behandle als Code,
    konservativ; die G0-Lock-Domaene gilt nur bei aufloesbarem vault_root)."""
    if not vault_root:
        return CODE
    target_norm = _norm(path)
    vault_norm = _norm(vault_root)
    if target_norm == vault_norm or target_norm.startswith(vault_norm + os.sep):
        return VAULT
    return CODE


def resolve_code_write(path, worktree_cwd, surface=None):
    """Loest einen Code-Write-Pfad relativ zum Worktree-cwd auf.

    surface=None  -> intern nicht klassifiziert; behandelt wie "code" (reiner
                     cwd-Resolver). Aufrufer kann surface explizit setzen.
    surface="vault" -> Pfad UNVERAENDERT zurueck (G0-Domaene, BL-334): Vault-
                     State-Writes bleiben abs, kein cwd-Rebase.
    surface="code"  -> os.path.join(worktree_cwd, path): ein RELATIVER Pfad
                     landet unter worktree_cwd (Worktree-Isolation der
                     Code-Writes); ein bereits ABSOLUTER Pfad bleibt absolut
                     (os.path.join verwirft worktree_cwd bei abs-Komponente).

    HINWEIS: gibt den Pfad NICHT normalisiert zurueck (nur fuer Surface=code
    via os.path.join zusammengesetzt) — der Aufrufer behaelt seine Pfad-Form.
    Reine Funktion, keine Filesystem-Effekte."""
    if surface == VAULT:
        # G0-Domaene (BL-334): abs Vault-Pfad bleibt unveraendert.
        return path
    # surface in (None, "code"): cwd-relativer Code-Resolver.
    # os.path.join ist abs-aware: bei abs `path` wird worktree_cwd verworfen.
    return os.path.join(worktree_cwd, path)
