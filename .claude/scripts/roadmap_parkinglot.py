#!/usr/bin/env python3
"""
roadmap_parkinglot.py — der Within-BL-Kompass (Micro-Bruder von roadmap_status.py, BL-418).

Beantwortet: WO stehen wir INNERHALB eines Backlog-Items?
  1. Pipeline-Stufen-Status   — Intake -> A -> arc42 -> IDF -> SDF -> Post (DONE/AKTIV/OFFEN).
  2. PL-Item-Tabelle          — granularer K-Score, Stage, depends_on, Klassifikation, Status.
  3. Sub-Batch-Sicht          — AUTORITATIV (Manifest BERATER_OUTPUTS_IDF, wenn IDF lief)
                                ODER PROJEKTION (topologische PL-Gruppierung, vor IDF) — LAUT markiert.
  4. Orchestrator-Kette       — /_A -> /_IDF -> /_SDF -> /_I(sub-batch a,b,c) -> /_SDF_post, mit Position.
  5. Fortschritt %            — K-GEWICHTET (Sigma K_done / Sigma K_total) + Count-% + per-Stage.
  6. Naechster Befehl         — prozess-korrekt (reuse roadmap_status.next_command_for_bl).

READ-ONLY. Spiegelt den aktuellen Wissensstand: vor IDF = Projektion (simulierter Orchestrator),
nach IDF = autoritativ. Re-implementiert kein Routing als Magie.

CLI: py -3 roadmap_parkinglot.py --bl-folder {pfad} --bl-id BL-XXX
"""
from __future__ import annotations

import argparse
import glob
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:                       # pragma: no cover
    yaml = None

try:                                      # Macro-Mechanik wiederverwenden (Konsistenz, INV-AO-CALLER)
    from roadmap_status import next_command_for_bl
except Exception:                         # pragma: no cover
    next_command_for_bl = None

_PL_ID = re.compile(r"BL-\d+\S*")


# ───────────────────────── Lese-Helfer ─────────────────────────
def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _frontmatter(text: str) -> dict:
    m = re.match(r"^---\n(.*?)\n---", text or "", re.S)
    if not m or yaml is None:
        return {}
    try:
        d = yaml.safe_load(m.group(1))
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _first_md(folder: Path, sub: str) -> Path | None:
    hits = sorted(glob.glob(str(folder / sub / "*.md")))
    return Path(hits[0]) if hits else None


def _num(v, default: float = 0.0) -> float:
    try:
        return float(re.findall(r"[-+]?\d*\.?\d+", str(v))[0])
    except (IndexError, TypeError, ValueError):
        return default


# ───────────────────────── PL_Master ─────────────────────────
def parse_pl(folder: Path) -> dict:
    """6_PL/*.md -> {present, items_total, items_done, items:[{id, source_aks, k_score, srs,
    classification, status, dependencies, done_in_batch, title}]}."""
    f = _first_md(folder, "6_PL")
    if not f:
        return {"present": False, "items": [], "items_total": 0, "items_done": 0}
    text = _read(f)
    fm = _frontmatter(text)
    items = []
    for block in re.split(r"\n###\s+", text)[1:]:
        lines = block.splitlines()
        bid = lines[0].strip()
        if not _PL_ID.match(bid):
            continue
        d = {"id": bid}
        for ln in lines[1:]:
            mm = re.match(r"\s*-\s*\*\*([^:]+):\*\*\s*(.*)", ln)
            if mm:
                d[mm.group(1).strip().lower().replace(" ", "_")] = mm.group(2).strip()
        items.append(d)
    done = sum(1 for i in items if i.get("status", "").lower() == "done")
    return {"present": True, "items": items,
            "items_total": fm.get("items_total", len(items)),
            "items_done": fm.get("items_done", done),
            "aggregate_k_score": fm.get("aggregate_k_score")}


# ───────────────────────── K-Score ─────────────────────────
def parse_kscore(folder: Path) -> dict:
    f = _first_md(folder, "4_K-Score")
    if not f:
        return {"present": False, "ak_details": {}}
    fm = _frontmatter(_read(f))
    return {"present": True, "k_score": fm.get("k_score"), "k_label": fm.get("k_label"),
            "k_aufwand": fm.get("k_aufwand"), "k_kopplung": fm.get("k_kopplung"),
            "k_fragilitaet": fm.get("k_fragilitaet"), "ak_details": fm.get("ak_details") or {}}


# ───────────────────────── Manifest ─────────────────────────
def parse_manifest(folder: Path) -> dict:
    text = _read(folder / "_manifest.md")
    if not text:
        return {}
    out: dict = {}
    parts = re.split(r"\n##\s+([A-Za-z_][A-Za-z0-9_]*)\s*\n", "\n" + text)
    for i in range(1, len(parts) - 1, 2):
        out[parts[i].strip()] = _parse_section(parts[i + 1])
    return out


def _parse_section(body: str) -> dict:
    """yaml-fenced Block bevorzugt; sonst bare 'key: value'-Zeilen (top-level)."""
    m = re.search(r"```ya?ml\n(.*?)```", body, re.S)
    if m and yaml is not None:
        try:
            d = yaml.safe_load(m.group(1))
            if isinstance(d, dict):
                return d
        except Exception:
            pass
    d: dict = {}
    for ln in body.splitlines():
        if ln.lstrip().startswith("#"):
            continue
        mm = re.match(r"\s*([a-zA-Z_][\w]*):\s*(.*)", ln)
        if mm:
            d[mm.group(1)] = mm.group(2).strip()
    # gezielte Nested-Extraktion (DF_BATCH_STATE batch_modes/completed_sub_batches, falls nicht yaml)
    if not isinstance(d.get("batch_modes"), dict):
        bm = {}
        for mm in re.finditer(r"\b(batch_\w+):\s*(M\d)\b", body):
            bm[mm.group(1)] = mm.group(2)
        if bm:
            d["batch_modes"] = bm
    csb = re.search(r"completed_sub_batches:\s*\[([^\]]*)\]", body)
    if csb:
        d["completed_sub_batches"] = [x.strip() for x in csb.group(1).split(",") if x.strip()]
    bs = re.search(r"batch_status:\s*(\w+)", body)
    if bs:
        d["batch_status"] = bs.group(1)
    return d


# ───────────────────────── Stufen-Erkennung ─────────────────────────
def detect_stages(folder: Path, mani: dict) -> list[dict]:
    a = mani.get("A_PIPELINE_STATE", {})
    idf = mani.get("BERATER_OUTPUTS_IDF", {}) or mani.get("IDF_PIPELINE_STATE", {})
    df = mani.get("DF_BATCH_STATE", {})
    post = mani.get("POST_STATE", {})
    has_model = (folder / "2_Model").is_dir() and bool(glob.glob(str(folder / "2_Model" / "*.md")))
    has_spec = (folder / "3_Spec").is_dir() and bool(glob.glob(str(folder / "3_Spec" / "*.md")))
    a_done = str(a.get("phase", "")).upper() in {"COMPLETED", "DONE"} or (has_model and has_spec)
    arc42 = (folder / "arc42").is_dir() and bool(glob.glob(str(folder / "arc42" / "*.md")))
    idf_done = bool((idf.get("batchPlan") or {}).get("sub_batches")) or \
               str(idf.get("idf_status", "")).upper() in {"BATCH_PLAN_READY", "DONE", "IDF_DONE"}
    completed = df.get("completed_sub_batches") or []
    sdf_done = bool(completed) or str(df.get("batch_status", "")).upper() == "DONE"
    post_done = bool(post) or str(df.get("batch_status", "")).upper() == "DONE"
    return [
        {"stufe": "Intake",     "done": True,     "note": f"BL angelegt ({folder.name[:24]}…)"},
        {"stufe": "A-Pipeline", "done": a_done,   "note": _a_note(a, has_model, has_spec)},
        {"stufe": "arc42",      "done": arc42,    "note": "Sichten gerendert" if arc42 else "—"},
        {"stufe": "IDF",        "done": idf_done, "note": _idf_note(idf)},
        {"stufe": "SDF (Code)", "done": sdf_done, "note": (f"{len(completed)} Batch(es) gebaut" if sdf_done else "wartet auf IDF + Go")},
        {"stufe": "Post",       "done": post_done, "note": ("recalibrate/modelSync/statusTransition" if post_done else "—")},
    ]


def _a_note(a: dict, has_model: bool, has_spec: bool) -> str:
    if a:
        k = a.get("k_score"); rt = a.get("routing_target")
        return f"REIF, K={k}, routing={rt}" if k else "A-Artefakte vorhanden"
    return "Model+Spec da" if (has_model and has_spec) else "—"


def _idf_note(idf: dict) -> str:
    sb = (idf.get("batchPlan") or {}).get("sub_batches") or {}
    if sb:
        return f"{len(sb)} Sub-Batches geplant"
    return "noch nicht gelaufen (Projektion unten)"


# ───────────────────────── Sub-Batch-Sicht ─────────────────────────
def subbatches(mani: dict, pl: dict) -> dict:
    """authoritativ (IDF lief) ODER projektion (topologisch). Gibt {mode, batches:[{id,items,stage,modus,k}]}."""
    idf = mani.get("BERATER_OUTPUTS_IDF", {})
    df = mani.get("DF_BATCH_STATE", {})
    sb = (idf.get("batchPlan") or {}).get("sub_batches") or {}
    if sb:
        stages = (idf.get("stagePlanner") or {}).get("batch_stages") or df.get("batch_stages") or {}
        modes = df.get("batch_modes") or {}
        completed = set(df.get("completed_sub_batches") or [])
        out = []
        for bid, b in sb.items():
            agg = b.get("aggregates", {})
            out.append({"id": bid, "items": b.get("items", []),
                        "stage": stages.get(bid, "—"), "modus": modes.get(bid, "—"),
                        "k": agg.get("k_score_avg", "—"), "done": bid in completed,
                        "label": b.get("label", "")})
        return {"mode": "autoritativ", "batches": out}
    # PROJEKTION: topologische Schichten nach dependencies
    return {"mode": "projektion", "batches": _project_batches(pl)}


def _project_batches(pl: dict) -> list[dict]:
    items = pl.get("items", [])
    by_id = {i["id"]: i for i in items}

    def deps_of(it):
        raw = it.get("dependencies", "") or ""
        toks = re.findall(r"AK-\w+-PL-\d+", raw)                  # Kurz-Referenzen (AK-..-PL-..)
        return [d for d in by_id if d != it["id"] and any(t in d for t in toks)]

    placed: dict[str, int] = {}
    # Fixpunkt-Schichtung
    for _ in range(len(items) + 1):
        changed = False
        for it in items:
            if it["id"] in placed:
                continue
            ds = deps_of(it)
            if all(d in placed for d in ds):
                placed[it["id"]] = (max((placed[d] for d in ds), default=0) + 1) if ds else 1
                changed = True
        if not changed:
            break
    for it in items:                       # Zyklen/unaufloesbar -> letzte Schicht
        placed.setdefault(it["id"], max(placed.values(), default=0) + 1)
    layers: dict[int, list] = {}
    for it in items:
        layers.setdefault(placed[it["id"]], []).append(it)
    out = []
    for lvl in sorted(layers):
        grp = layers[lvl]
        out.append({"id": f"batch_{lvl} (proj.)",
                    "items": [i["id"] for i in grp],
                    "stage": "—", "modus": "—",
                    "k": round(sum(_num(i.get("k_score")) for i in grp) / max(len(grp), 1), 1),
                    "done": all(i.get("status", "").lower() == "done" for i in grp),
                    "label": ", ".join(i.get("source_aks", "?") for i in grp)})
    return out


# ───────────────────────── Fortschritt ─────────────────────────
def progress(pl: dict) -> dict:
    items = pl.get("items", [])
    if not items:
        return {"count_pct": 0.0, "k_pct": 0.0, "done": 0, "total": 0}
    done_items = [i for i in items if i.get("status", "").lower() == "done"]
    k_total = sum(_num(i.get("k_score")) for i in items)
    k_done = sum(_num(i.get("k_score")) for i in done_items)
    return {"count_pct": round(100 * len(done_items) / len(items), 1),
            "k_pct": round(100 * k_done / k_total, 1) if k_total else 0.0,
            "done": len(done_items), "total": len(items),
            "k_done": round(k_done, 1), "k_total": round(k_total, 1)}


# ───────────────────────── Render ─────────────────────────
def _bar(pct: float, width: int = 20) -> str:
    fill = int(round(pct / 100 * width))
    return "█" * fill + "░" * (width - fill)


def _mark(done: bool, active: bool = False) -> str:
    return "[x]" if done else ("[~]" if active else "[ ]")


def render(bl_id: str, folder: Path, mani: dict, pl: dict, ks: dict) -> str:
    stages = detect_stages(folder, mani)
    sb = subbatches(mani, pl)
    prog = progress(pl)
    ak = ks.get("ak_details", {})
    L: list[str] = []
    L.append(f"# /_roadmap_parkingLot — Within-BL-Kompass · {bl_id}")
    L.append("")

    # 1 Pipeline-Stufen
    L.append("## 1 · Pipeline-Stufen")
    L.append("| Stufe | Status | Zustand |")
    L.append("|---|---|---|")
    active_marked = False
    for s in stages:
        active = (not s["done"]) and (not active_marked)
        if active:
            active_marked = True
        L.append(f"| {s['stufe']} | {_mark(s['done'], active)} | {s['note']} |")
    L.append("")

    # 2 PL-Items
    L.append("## 2 · Parking-Lot-Items")
    if pl.get("present"):
        # Stage je Item aus Sub-Batch-Zuordnung (falls autoritativ)
        item_stage = {}
        if sb["mode"] == "autoritativ":
            for b in sb["batches"]:
                for it in b["items"]:
                    item_stage[it] = b["stage"]
        L.append("| PL-Item | AK | granular-K | Stage | Klass. | Status | depends_on |")
        L.append("|---|---|---|---|---|---|---|")
        for it in pl["items"]:
            aks = it.get("source_aks", "?")
            kak = _ak_k(aks, ak, it.get("k_score", "—"))
            cls = "code" if "code" in it.get("classification", "").lower() else (
                  "md" if "markdown" in it.get("classification", "").lower() else
                  ("split" if "gespalt" in it.get("classification", "").lower() or "GESPALT" in it.get("classification","") else "—"))
            st = item_stage.get(it["id"], "—")
            dep = _short_deps(it.get("dependencies", ""))
            L.append(f"| {it['id'].replace(bl_id+'-','')} | {aks} | {kak} | {st} | {cls} | {it.get('status','—')} | {dep} |")
    else:
        L.append("_(noch kein PL_Master — A-Pipeline Phase 5c nicht gelaufen)_")
    L.append("")

    # 3 Sub-Batches
    tag = "AUTORITATIV (aus IDF-Manifest)" if sb["mode"] == "autoritativ" else \
          "PROJEKTION (simulierter Orchestrator — NICHT autoritativ; verbindlich erst nach IDF 7/7.5/7.6 + SDF C3)"
    L.append(f"## 3 · Sub-Batches — {tag}")
    if sb["batches"]:
        L.append("| Batch | Items | Stage | Modus | K | Status |")
        L.append("|---|---|---|---|---|---|")
        for b in sb["batches"]:
            items = ", ".join(x.replace(bl_id + "-", "") for x in b["items"])
            L.append(f"| {b['id']} | {items} | {b['stage']} | {b['modus']} | {b['k']} | {'done' if b['done'] else '—'} |")
    else:
        L.append("_(keine PL-Items)_")
    L.append("")

    # 4 Orchestrator-Kette
    L.append("## 4 · Orchestrator-Kette (Position)")
    L.append(_chain(stages))
    L.append("")

    # 5 Fortschritt
    L.append("## 5 · Fortschritt (K-gewichtet)")
    L.append(f"- **K-gewichtet:** {_bar(prog['k_pct'])} **{prog['k_pct']}%**  (Σ K_done {prog.get('k_done','?')} / Σ K_total {prog.get('k_total','?')})")
    L.append(f"- **Count:** {prog['count_pct']}%  ({prog['done']}/{prog['total']} PL-Items)")
    L.append("")

    # 6 Naechster Befehl
    L.append("## 6 · Nächster Befehl (Prozess)")
    L.append(_next_cmd(bl_id, mani, stages))
    return "\n".join(L)


def _ak_k(aks: str, ak_details: dict, fallback) -> str:
    key = (aks or "").split(",")[0].strip().split(" ")[0]
    d = ak_details.get(key) if isinstance(ak_details, dict) else None
    if isinstance(d, dict) and d.get("k_score_pro_ak") is not None:
        return str(d["k_score_pro_ak"])
    return str(fallback)


def _short_deps(raw: str) -> str:
    ids = re.findall(r"AK-\d+(?:-PL-\d+)?", raw or "")
    return ", ".join(dict.fromkeys(ids)) if ids else "—"


def _chain(stages: list[dict]) -> str:
    sd = {s["stufe"]: s for s in stages}
    def m(name):
        s = sd.get(name, {})
        active = (not s.get("done")) and all(x.get("done") for x in stages[:stages.index(s)]) if s in stages else False
        return _mark(s.get("done", False), active)
    a = sd.get("A-Pipeline", {}); idf = sd.get("IDF", {}); sdf = sd.get("SDF (Code)", {}); post = sd.get("Post", {})
    def mk(s):
        return _mark(s.get("done", False))
    parts = [
        f"/_A_orchestrate {mk(a)}",
        f"/_IDF_orchestrate {mk(idf)}",
        f"/_SDF_orchestrate {mk(sdf)}",
        f"/_I_orchestrate (sub-batch a,b,c) {mk(sdf)}",
        f"/_SDF_orchestrate_post {mk(post)}",
    ]
    return "    " + "  →  ".join(parts)


def _next_cmd(bl_id: str, mani: dict, stages: list[dict]) -> str:
    sd = {s["stufe"]: s["done"] for s in stages}
    if next_command_for_bl is None:
        return f"  (roadmap_status nicht importierbar)"
    a_done = sd.get("A-Pipeline", False)
    idf_done = sd.get("IDF", False)
    sdf_done = sd.get("SDF (Code)", False)
    post_done = sd.get("Post", False)
    if post_done:
        return "  ✅ BL DONE — nächste Roadmap-BL (siehe /_roadmap_backlog)."
    if sdf_done:
        return f"  /_SDF_orchestrate_post {bl_id}  (Post: recalibrate/statusTransition/modelSync)"
    if idf_done:
        return f"  /_SDF_orchestrate {bl_id}  (pro Batch: C3 → /_I_orchestrate M{{N}})"
    if a_done:
        return f"  /_IDF_orchestrate {bl_id}  (Dekomposition: PL-Items → Sub-Batches)"
    return f"  /_A_orchestrate {bl_id}  (Wissensbasis: Model·Spec·K-Score·Gap·PL)"


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="roadmap_parkinglot", description="/_roadmap_parkingLot Within-BL-Kompass (read-only, BL-418)")
    p.add_argument("--bl-folder", type=Path, required=True, help="resolved BL-Vault-Ordner (resolve_bl_path)")
    p.add_argument("--bl-id", required=True)
    args = p.parse_args(argv)

    folder = args.bl_folder
    mani = parse_manifest(folder)
    pl = parse_pl(folder)
    ks = parse_kscore(folder)
    out = render(args.bl_id, folder, mani, pl, ks)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        print(out)
    except (UnicodeEncodeError, AttributeError):
        sys.stdout.buffer.write(out.encode("utf-8", "replace") + b"\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
