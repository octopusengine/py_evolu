from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from py_evolu import evolu


DEBUG = True
DB_NAME = "test"
LOCAL_ONLY = False
RELAY = "wss://free.evoluhq.com"
SYNC_WAIT_SECONDS = 8

ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"
TEST_TXT = ROOT / "test.txt"
BACKUP_DB = ROOT / "test_backup.sqlite"


def line() -> None:
    print("-" * 72)


def show_json(label: str, value: object) -> None:
    print(f"\n{label}:")
    print(json.dumps(value, indent=2, ensure_ascii=False, default=str))


def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or default


def pause() -> None:
    input("\nPress Enter to continue...")


def current_stamp() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def read_env() -> dict[str, str]:
    if not ENV_FILE.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line_text = raw_line.strip()
        if not line_text or line_text.startswith("#") or "=" not in line_text:
            continue
        key, value = line_text.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def write_env_value(key: str, value: str) -> None:
    lines = []
    seen = False
    if ENV_FILE.exists():
        lines = ENV_FILE.read_text(encoding="utf-8").splitlines()

    next_lines = []
    for raw_line in lines:
        if raw_line.strip().startswith(f"{key}="):
            next_lines.append(f"{key}={value}")
            seen = True
        else:
            next_lines.append(raw_line)

    if not seen:
        next_lines.append(f"{key}={value}")

    ENV_FILE.write_text("\n".join(next_lines) + "\n", encoding="utf-8")


def evolu_key() -> str:
    return read_env().get("EVOLU_KEY", "")


def mask_secret(value: str | None) -> str:
    if not value:
        return "<not set>"
    parts = value.split()
    if len(parts) >= 4:
        return f"{parts[0]} {parts[1]} ... {parts[-2]} {parts[-1]}"
    return f"{value[:8]}...{value[-8:]}" if len(value) > 20 else "<set>"


def make_client() -> evolu:
    return evolu(
        name=DB_NAME,
        local_only=LOCAL_ONLY,
        relay=RELAY,
        debug=DEBUG,
        timeout=120,
        sync_wait_ms=SYNC_WAIT_SECONDS * 1000,
    )


def show_access(app: evolu) -> None:
    line()
    print("Evolu example")
    print(f"Relay:      {app.relay_url}")
    print(f"Access key: {ENV_FILE} -> EVOLU_KEY={mask_secret(evolu_key())}")
    print(f"DB file:    {app.db_path}")
    print(f"Text file:  {TEST_TXT}")
    print(f"Backup DB:  {BACKUP_DB}")
    print(f"Debug:      {DEBUG}")
    try:
        owner = app.owner()
        print(f"Owner ID:   {owner.get('ownerId')}")
        print("Mnemonic:   stored in the local Evolu DB; menu option 6 can show it")
    except Exception as exc:
        print(f"Owner state: not available yet ({exc})")
    line()


def save_text(app: evolu) -> None:
    text = ask("Text to save into test.txt and Evolu", f"test {current_stamp()}")
    TEST_TXT.write_text(text, encoding="utf-8")
    result = app.insert(text)
    show_json("Saved to Evolu", result)
    print(f"\nAlso saved to {TEST_TXT}")


def load_data(app: evolu) -> None:
    if TEST_TXT.exists():
        print(f"\ntest.txt:\n{TEST_TXT.read_text(encoding='utf-8')}")
    else:
        print("\ntest.txt does not exist yet.")
    show_json("Evolu data", app.list())


def synchronize(app: evolu) -> None:
    print(f"\nSynchronizing through relay {app.relay_url}")
    result = app.list(wait_for_sync=True)
    show_json("Data after sync wait", result)


def backup(app: evolu) -> None:
    result = app.export_backup(BACKUP_DB)
    show_json("Backup", result)


def restore_owner(app: evolu) -> None:
    print("\nRestore from mnemonic resets the local DB owner.")
    print("If data was already synced to the relay, run Synchronize after restore.")
    saved_key = evolu_key()
    if saved_key:
        use_saved = ask("Use EVOLU_KEY from .env? Type YES", "YES")
        mnemonic = saved_key if use_saved == "YES" else ask("Enter mnemonic")
    else:
        mnemonic = ask("Enter mnemonic")
    if not mnemonic:
        print("No mnemonic entered.")
        return
    result = app.restore(mnemonic)
    show_json("Restore", result)


def show_owner(app: evolu) -> None:
    owner = app.owner()
    visible = {**owner, "mnemonic": mask_secret(owner.get("mnemonic"))}
    show_json("Owner / relay access", visible)
    reveal = ask("Reveal full mnemonic? Type YES")
    if reveal == "YES":
        show_json("Full owner / relay access", owner)


def save_owner_key(app: evolu) -> None:
    owner = app.owner()
    mnemonic = owner.get("mnemonic")
    if not mnemonic:
        print("Owner has no mnemonic to save.")
        return
    write_env_value("EVOLU_KEY", str(mnemonic))
    print(f"Saved EVOLU_KEY to {ENV_FILE}")
    print(f"EVOLU_KEY={mask_secret(str(mnemonic))}")


def reset_db(app: evolu) -> None:
    confirm = ask("Really reset the local Evolu DB? Type YES")
    if confirm != "YES":
        print("Reset cancelled.")
        return
    show_json("Reset", app.reset())


def menu() -> None:
    app = make_client()
    while True:
        show_access(app)
        print("1. Load test.txt and Evolu data")
        print("2. Save text to test.txt and Evolu")
        print("3. Synchronize / wait for relay")
        print("4. Export Evolu DB backup")
        print("5. Restore owner from mnemonic")
        print("6. Show owner/mnemonic")
        print("7. Save current mnemonic to .env as EVOLU_KEY")
        print("8. Reset local DB")
        print("0. Exit")
        choice = ask("Choice")

        try:
            if choice == "1":
                load_data(app)
            elif choice == "2":
                save_text(app)
            elif choice == "3":
                synchronize(app)
            elif choice == "4":
                backup(app)
            elif choice == "5":
                restore_owner(app)
            elif choice == "6":
                show_owner(app)
            elif choice == "7":
                save_owner_key(app)
            elif choice == "8":
                reset_db(app)
            elif choice == "0":
                print("Bye.")
                return
            else:
                print("Unknown choice.")
        except Exception as exc:
            print("\nERROR:")
            print(exc)

        pause()


if __name__ == "__main__":
    menu()
