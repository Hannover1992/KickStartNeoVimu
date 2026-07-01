"""Lock-Stealing-Simulator: manipuliert heartbeat.txt timestamps.

Test-Pattern: simuliere stale lock ohne tatsaechlich auf 5min zu warten.
Ermoeglicht Unit-Tests fuer PC-Stale-Detection-Logik.

Usage (CLI):
  lock_steal_simulator.py force-stale <lock_dir> [age_s]
  lock_steal_simulator.py restore-fresh <lock_dir>
"""
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path


def force_stale(lock_dir: Path, age_seconds: int = 600) -> datetime:
    """
    Setzt heartbeat.txt auf einen Timestamp der age_seconds in der Vergangenheit liegt.
    Simuliert stale Worker ohne tatsaechlich zu warten.

    Args:
        lock_dir:    Pfad zum BL-Lock-Verzeichnis (z.B. .locks/BL-179.lock/)
        age_seconds: Wie alt der Timestamp erscheinen soll (default: 600s = 10min)

    Returns:
        Der geschriebene stale Timestamp.

    Raises:
        FileNotFoundError: wenn heartbeat.txt nicht existiert.
    """
    heartbeat = lock_dir / "heartbeat.txt"
    if not heartbeat.exists():
        raise FileNotFoundError(f"No heartbeat in {lock_dir}")
    stale_ts = datetime.now(timezone.utc) - timedelta(seconds=age_seconds)
    heartbeat.write_text(stale_ts.isoformat() + "\n", encoding="utf-8")
    return stale_ts


def restore_fresh(lock_dir: Path) -> datetime:
    """
    Setzt heartbeat.txt auf den aktuellen Timestamp zurueck.
    Simuliert einen lebendigen Worker der gerade seinen Heartbeat gesendet hat.

    Args:
        lock_dir: Pfad zum BL-Lock-Verzeichnis.

    Returns:
        Der geschriebene frische Timestamp.

    Raises:
        FileNotFoundError: wenn heartbeat.txt nicht existiert.
    """
    heartbeat = lock_dir / "heartbeat.txt"
    if not heartbeat.exists():
        raise FileNotFoundError(f"No heartbeat in {lock_dir}")
    fresh_ts = datetime.now(timezone.utc)
    heartbeat.write_text(fresh_ts.isoformat() + "\n", encoding="utf-8")
    return fresh_ts


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            "Usage: lock_steal_simulator.py {force-stale|restore-fresh} <lock_dir> [age_s]",
            file=sys.stderr,
        )
        sys.exit(2)
    cmd, path = sys.argv[1], Path(sys.argv[2])
    if cmd == "force-stale":
        age = int(sys.argv[3]) if len(sys.argv) > 3 else 600
        ts = force_stale(path, age)
        print(f"force-stale -> {ts.isoformat()}")
    elif cmd == "restore-fresh":
        ts = restore_fresh(path)
        print(f"restore-fresh -> {ts.isoformat()}")
    else:
        print(f"Unknown cmd: {cmd}", file=sys.stderr)
        sys.exit(2)
