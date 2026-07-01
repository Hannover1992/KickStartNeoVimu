#!/usr/bin/env python3
"""
BL-195 AK-2: Race-Condition-Test-Patterns (Windows-kompatibel).

Worker-Functions sind Module-Level fuer Windows-multiprocessing spawn-Mode.
"""

import multiprocessing
import os
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path


def _race_worker(worker_id, barrier, queue, fn_module, fn_name, fn_args):
    """Module-Level Worker fuer trigger_race. Importiert fn dynamisch."""
    try:
        import importlib
        mod = importlib.import_module(fn_module)
        fn = getattr(mod, fn_name)
        barrier.wait(timeout=10)
        result = fn(worker_id, *fn_args)
        queue.put((worker_id, "ok", result))
    except Exception as e:
        queue.put((worker_id, "fail", str(e)))


def trigger_race(n_workers, work_fn, args=()):
    """Spawn N processes that all do `work_fn(args)` at exactly the same time.

    work_fn MUSS Module-Level sein (Windows spawn-mode requirement).
    """
    fn_module = work_fn.__module__
    fn_name = work_fn.__name__

    barrier = multiprocessing.Barrier(n_workers)
    queue = multiprocessing.Queue()

    processes = []
    for i in range(n_workers):
        p = multiprocessing.Process(
            target=_race_worker,
            args=(i, barrier, queue, fn_module, fn_name, args)
        )
        p.start()
        processes.append(p)

    results = []
    for _ in range(n_workers):
        results.append(queue.get(timeout=30))

    for p in processes:
        p.join(timeout=5)

    results.sort(key=lambda r: r[0])
    return results


def _heartbeat_worker(process_id, counts, stop_event, fn_module, fn_name, fn_arg, interval):
    """Module-Level Heartbeat-Worker."""
    import importlib
    mod = importlib.import_module(fn_module)
    fn = getattr(mod, fn_name)
    while not stop_event.is_set():
        try:
            fn(process_id, fn_arg)
            counts[process_id] += 1
        except Exception:
            pass
        time.sleep(interval)


def heartbeat_stress(heartbeat_fn, fn_arg, duration_sec=10, n_processes=3, interval_sec=1.0):
    """N Heartbeat-Daemons parallel.

    heartbeat_fn MUSS Module-Level + Signatur (process_id, fn_arg).
    """
    fn_module = heartbeat_fn.__module__
    fn_name = heartbeat_fn.__name__

    counts = multiprocessing.Array("i", n_processes)
    stop_event = multiprocessing.Event()

    processes = []
    for i in range(n_processes):
        p = multiprocessing.Process(
            target=_heartbeat_worker,
            args=(i, counts, stop_event, fn_module, fn_name, fn_arg, interval_sec)
        )
        p.start()
        processes.append(p)

    time.sleep(duration_sec)
    stop_event.set()
    for p in processes:
        p.join(timeout=5)

    return list(counts)


@contextmanager
def temp_vault(n_worktrees=1, prefix="bl195_vault"):
    """Context-Manager: erzeugt temp Vault-Struktur + n Worktree-Subdirs."""
    tmp = tempfile.mkdtemp(prefix=prefix)
    vault_root = Path(tmp) / "vault"
    vault_root.mkdir(parents=True, exist_ok=True)
    worktrees = []
    for i in range(n_worktrees):
        wt = Path(tmp) / f"worktree_{i}"
        wt.mkdir(parents=True, exist_ok=True)
        worktrees.append(wt)
    try:
        yield {"vault_root": vault_root, "worktrees": worktrees, "tmp_base": Path(tmp)}
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
