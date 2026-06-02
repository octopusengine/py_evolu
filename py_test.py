from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from py_evolu import evolu


DEBUG = True
DB_NAME = "py-evolu-main"
LOCAL_ONLY = False
RESET_AT_START = True
RESTORE_AFTER_BACKUP = True
SYNC_WAIT_SECONDS = 8


ROOT = Path(__file__).resolve().parent
BACKUP_FILE = ROOT / "backup" / f"{DB_NAME}.sqlite"


def title(text: str) -> None:
    print("\n" + "=" * 88)
    print(text)
    print("=" * 88)


def dump(label: str, value: object) -> None:
    print(f"\n{label}:")
    print(json.dumps(value, indent=2, ensure_ascii=False, default=str))


def main() -> int:
    app = evolu(
        name=DB_NAME,
        local_only=LOCAL_ONLY,
        debug=DEBUG,
        timeout=120,
        sync_wait_ms=SYNC_WAIT_SECONDS * 1000,
    )

    title("1. Owner / connection")
    if RESET_AT_START:
        dump("reset", app.reset())
    owner = app.owner()
    dump("owner", {**owner, "mnemonic": "<hidden>" if owner.get("mnemonic") else None})
    mnemonic = owner.get("mnemonic")
    if not mnemonic:
        raise RuntimeError("Mnemonic is missing; restore test cannot continue.")

    title("2. Insert")
    inserted = app.insert(f"Python Evolu test {datetime.now(timezone.utc).isoformat()}")
    dump("inserted", inserted)
    todo_id = inserted["inserted"]["id"]

    title("3. List after insert")
    dump("todos", app.list())

    title("4. Update")
    updated = app.update(todo_id, title="Python Evolu test updated", completed=True)
    dump("updated", updated)

    title("5. Export backup")
    backup = app.export_backup(BACKUP_FILE)
    dump("backup", backup)

    if not LOCAL_ONLY:
        title("6. Wait for sync")
        app.wait(SYNC_WAIT_SECONDS, "giving relay time to receive local changes")

    if RESTORE_AFTER_BACKUP:
        title("7. Restore same owner into the same DB")
        restored = app.restore(mnemonic)
        dump("restored", restored)
        if not LOCAL_ONLY:
            app.wait(SYNC_WAIT_SECONDS, "giving relay time to send data back after restore")

    title("8. Final list")
    final_rows = app.list(wait_for_sync=not LOCAL_ONLY)
    dump("final todos", final_rows)

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
