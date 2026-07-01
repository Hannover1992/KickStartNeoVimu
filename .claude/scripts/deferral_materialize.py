#!/usr/bin/env python3
"""deferral_materialize.py — BL-323 AK-1 (Stage-Defer Emit) + AK-4 (AK/Gate-Defer Generalisierung).

Defer-Materialisierungs-Helper: beim Defer MATERIALISIERT die Engine ein getrenntes,
re-surfacing Folge-PL-Item statt eines Prosa-Markers. machine-not-context — die Engine
emittiert das PL-Item, nicht der Lead per Hand.

Spiegel: _IDF_berater_bottleneckTrigger SCHRITT 4 (Queue-Writer, der die DEFERRED-PLs
aus dem Loop herausschreibt + PL-Status setzt). SELBE Funktion fuer Stage-Defer (kind="stage")
UND AK/Gate-Defer (kind="ak", AK-4) — generalisiert ueber das `kind`-Feld.

Contract:
- materialize_deferral(defer_ctx) -> pl_item  (rein, deterministisch, idempotente id)
- write_deferral_pl(pl_item, pl_master_path) -> None  (append-if-not-present by id)
"""
import hashlib

# Pflichtfelder fuer JEDEN defer_ctx (kind-unabhaengig).
_REQUIRED_BASE = ("kind", "bl_id", "defer_reason", "defer_trigger", "verify")


def _stable_hash(*parts):
    """Stabiler 8-stelliger Hash ueber den Prozess hinweg (KEIN Python-hash()).

    hashlib.sha1 ist deterministisch zwischen Prozessen — Python's eingebautes
    hash() ist es wegen PYTHONHASHSEED NICHT, daher ungeeignet fuer idempotente ids.
    """
    payload = "\x1f".join("" if p is None else str(p) for p in parts)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:8]


def materialize_deferral(defer_ctx):
    """Materialisiert ein valides, re-surfacing Folge-PL-Item aus einem Defer-Context.

    Rein + deterministisch: gleicher defer_ctx -> identische id (T3-Idempotenz).
    Validierung: fehlende Pflichtfelder -> ValueError mit klarer Meldung (T5).
    """
    if not isinstance(defer_ctx, dict):
        raise ValueError(
            f"defer_ctx muss ein dict sein, war {type(defer_ctx).__name__}"
        )

    # Basis-Pflichtfelder
    for field in _REQUIRED_BASE:
        if not defer_ctx.get(field):
            raise ValueError(
                f"defer_ctx Pflichtfeld fehlt oder leer: {field!r} "
                f"(noetig: {', '.join(_REQUIRED_BASE)} + kind-spezifisch)"
            )

    kind = defer_ctx["kind"]
    bl_id = defer_ctx["bl_id"]

    # kind-spezifische Pflichtfelder + Discriminator-Felder
    if kind == "stage":
        if not defer_ctx.get("batch"):
            raise ValueError(
                "defer_ctx Pflichtfeld fehlt oder leer: 'batch' (noetig fuer kind='stage')"
            )
        if not defer_ctx.get("deferred_stages"):
            raise ValueError(
                "defer_ctx Pflichtfeld fehlt oder leer: 'deferred_stages' "
                "(noetig fuer kind='stage')"
            )
        typ = "deferred-stage"
        batch = defer_ctx["batch"]
        deferred_stages = defer_ctx["deferred_stages"]
        scope_label = batch
        # id-Diskriminator: kind + batch + deferred_stages
        disc = _stable_hash(kind, batch, deferred_stages)
        item_key = batch
        title = (
            f"Deferred Stages {deferred_stages} fuer {batch}: "
            f"{defer_ctx['defer_reason']}, Trigger: {defer_ctx['defer_trigger']}"
        )
    elif kind == "ak":
        if not defer_ctx.get("deferred_ak"):
            raise ValueError(
                "defer_ctx Pflichtfeld fehlt oder leer: 'deferred_ak' "
                "(noetig fuer kind='ak')"
            )
        typ = "deferred-ak"
        deferred_ak = defer_ctx["deferred_ak"]
        scope_label = deferred_ak
        # id-Diskriminator: kind + deferred_ak
        disc = _stable_hash(kind, deferred_ak)
        item_key = deferred_ak
        title = (
            f"Deferred {deferred_ak}: "
            f"{defer_ctx['defer_reason']}, Trigger: {defer_ctx['defer_trigger']}"
        )
    else:
        raise ValueError(
            f"defer_ctx.kind unbekannt: {kind!r} (erlaubt: 'stage' | 'ak')"
        )

    pl_id = f"{bl_id}-DEFER-{item_key}-{disc}"

    pl_item = {
        "id": pl_id,
        "typ": typ,
        "title": title,
        "defer_reason": defer_ctx["defer_reason"],
        "defer_trigger": defer_ctx["defer_trigger"],
        "verify": defer_ctx["verify"],
        "status": "deferred",
        "re_surface": True,
        "resurface_trigger": defer_ctx["defer_trigger"],
    }
    if kind == "stage":
        pl_item["deferred_stages"] = deferred_stages
    else:
        pl_item["deferred_ak"] = deferred_ak

    return pl_item


def write_deferral_pl(pl_item, pl_master_path):
    """Haengt eine Index-Zeile fuer das PL-Item an den PL-Master an — idempotent.

    append-if-not-present by id: steht die id schon im Master-Text, wird KEIN zweiter
    Eintrag geschrieben (T4-Dedup). Spiegel des bottleneckTrigger-Queue-Writers, der
    DEFERRED-PLs ohne Doppelung herausschreibt.
    """
    pl_id = pl_item["id"]
    with open(pl_master_path, "r", encoding="utf-8") as f:
        text = f.read()

    if pl_id in text:
        # Bereits vorhanden -> kein Doppel-Eintrag.
        return

    # Die id darf in der Zeile nur EINMAL vorkommen — der Dedup-Check zaehlt rohe
    # Substring-Vorkommen (T4: text.count(pl_id) == 1). Daher KEIN zusaetzlicher
    # "{pl_id}.md"-Dateiverweis (sonst id 2x im Master).
    title = pl_item.get("title", "")
    line = f"- [ ] **{pl_id}** [HOCH] {title}"

    sep = "" if text.endswith("\n") or text == "" else "\n"
    with open(pl_master_path, "a", encoding="utf-8") as f:
        f.write(f"{sep}{line}\n")
