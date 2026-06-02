from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QApplication

from evolu_ui import MainWindow
from py_evolu import evolu


DEBUG = True
LOCAL_ONLY = False
SYNC_WAIT_SECONDS = 8

ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"


@dataclass(frozen=True)
class RelayProfile:
    label: str
    db_name: str
    relay: str
    text_file: Path
    backup_file: Path


RELAYS = [
    RelayProfile(
        label="relay1",
        db_name="test_relay1",
        relay="wss://free.evoluhq.com",
        text_file=ROOT / "test_relay1.txt",
        backup_file=ROOT / "test_relay1_backup.sqlite",
    ),
    RelayProfile(
        label="relay2",
        db_name="test_relay2",
        relay="wss://evolu.petrkr.net",
        text_file=ROOT / "test_relay2.txt",
        backup_file=ROOT / "test_relay2_backup.sqlite",
    ),
]


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def read_env() -> dict[str, str]:
    if not ENV_FILE.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def write_env_value(key: str, value: str) -> None:
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines() if ENV_FILE.exists() else []
    next_lines = []
    seen = False
    for line in lines:
        if line.strip().startswith(f"{key}="):
            next_lines.append(f'{key}="{value}"')
            seen = True
        else:
            next_lines.append(line)
    if not seen:
        next_lines.append(f'{key}="{value}"')
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


class EvoluWorker(QObject):
    log_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)
    data_signal = pyqtSignal(dict)
    profiles_signal = pyqtSignal(list)
    profile_index_signal = pyqtSignal(int)

    def __init__(self) -> None:
        super().__init__()
        self._profile_index = 0
        self._debug = DEBUG

    @pyqtSlot()
    def initialize(self) -> None:
        self.profiles_signal.emit(
            [
                {"label": profile.label, "relay": profile.relay, "db_name": profile.db_name}
                for profile in RELAYS
            ]
        )
        self.profile_index_signal.emit(self._profile_index)
        self._load_current(wait_for_sync=False)

    @pyqtSlot(bool)
    def set_debug(self, enabled: bool) -> None:
        self._debug = enabled
        self._log(f"Debug {'enabled' if enabled else 'disabled'}")

    @pyqtSlot(int)
    def set_profile(self, index: int) -> None:
        if not 0 <= index < len(RELAYS):
            return
        self._profile_index = index
        self._log(f"Switched to {self._profile().label}")
        self._load_current(wait_for_sync=False)

    @pyqtSlot(str, object)
    def run_action(self, action: str, payload: object) -> None:
        payload = payload if isinstance(payload, dict) else {}
        try:
            if action == "load":
                self._load_current(wait_for_sync=False)
            elif action == "save_text":
                text = str(payload.get("text") or f"test {now()}")
                self._save_text(text)
            elif action == "sync":
                self._load_current(wait_for_sync=True)
            elif action == "backup":
                self._backup()
            elif action == "restore_env":
                self._restore_from_env()
            elif action == "show_owner":
                self._show_owner()
            elif action == "save_key":
                self._save_key()
            elif action == "reset":
                self._reset()
            elif action == "sample_both":
                self._sample_both()
            else:
                self._log(f"Unknown action: {action}")
        except Exception as exc:
            self.status_signal.emit("Error")
            self._log(f"ERROR: {exc}")

    def _profile(self) -> RelayProfile:
        return RELAYS[self._profile_index]

    def _client(self, profile: RelayProfile | None = None) -> evolu:
        profile = profile or self._profile()
        return evolu(
            name=profile.db_name,
            local_only=LOCAL_ONLY,
            relay=profile.relay,
            debug=False,
            timeout=120,
            sync_wait_ms=SYNC_WAIT_SECONDS * 1000,
        )

    def _ensure_env_owner(self, app: evolu) -> None:
        key = evolu_key()
        if not key or app.db_path.exists():
            return
        self._log(f"Initializing {app.db_path.name} from EVOLU_KEY")
        self._log_json("restore", app.restore(key))

    def _base_state(self, profile: RelayProfile, app: evolu) -> dict[str, Any]:
        owner: dict[str, Any] = {}
        try:
            self._ensure_env_owner(app)
            owner = app.owner()
            owner = {**owner, "mnemonic": mask_secret(owner.get("mnemonic"))}
        except Exception as exc:
            owner = {"error": str(exc)}

        text_content = profile.text_file.read_text(encoding="utf-8") if profile.text_file.exists() else ""
        return {
            "profile": {"label": profile.label, "relay": profile.relay, "db_name": profile.db_name},
            "owner": owner,
            "db_path": str(app.db_path),
            "text_path": str(profile.text_file),
            "backup_path": str(profile.backup_file),
            "text_content": text_content,
            "rows": None,
        }

    def _load_current(self, *, wait_for_sync: bool) -> None:
        profile = self._profile()
        app = self._client(profile)
        self.status_signal.emit(f"Loading {profile.label}...")
        self._log(f"Load {profile.label}, relay={profile.relay}, wait_for_sync={wait_for_sync}")
        state = self._base_state(profile, app)
        result = app.list(wait_for_sync=wait_for_sync)
        state["rows"] = result.get("todos", [])
        self.data_signal.emit(state)
        self._log_json("rows", state["rows"])
        self.status_signal.emit("Ready")

    def _save_text(self, text: str) -> None:
        profile = self._profile()
        app = self._client(profile)
        self.status_signal.emit(f"Saving to {profile.label}...")
        self._ensure_env_owner(app)
        profile.text_file.write_text(text, encoding="utf-8")
        self._log(f"Save text to {profile.label}: {text!r}")
        self._log_json("insert", app.insert(text))
        self._load_current(wait_for_sync=False)

    def _backup(self) -> None:
        profile = self._profile()
        app = self._client(profile)
        self.status_signal.emit(f"Backing up {profile.label}...")
        self._ensure_env_owner(app)
        self._log_json("backup", app.export_backup(profile.backup_file))
        self.status_signal.emit("Ready")

    def _restore_from_env(self) -> None:
        key = evolu_key()
        if not key:
            raise RuntimeError("EVOLU_KEY is not set in .env")
        profile = self._profile()
        app = self._client(profile)
        self.status_signal.emit(f"Restoring {profile.label}...")
        self._log(f"Restore {profile.label} from EVOLU_KEY={mask_secret(key)}")
        self._log_json("restore", app.restore(key))
        self._load_current(wait_for_sync=True)

    def _show_owner(self) -> None:
        app = self._client()
        self._ensure_env_owner(app)
        owner = app.owner()
        visible = {**owner, "mnemonic": mask_secret(owner.get("mnemonic"))}
        self._log_json("owner", visible)
        state = self._base_state(self._profile(), app)
        state["rows"] = app.list().get("todos", [])
        self.data_signal.emit(state)

    def _save_key(self) -> None:
        app = self._client()
        self._ensure_env_owner(app)
        owner = app.owner()
        mnemonic = owner.get("mnemonic")
        if not mnemonic:
            raise RuntimeError("Owner has no mnemonic")
        write_env_value("EVOLU_KEY", str(mnemonic))
        self._log(f"Saved EVOLU_KEY={mask_secret(str(mnemonic))} to {ENV_FILE}")

    def _reset(self) -> None:
        profile = self._profile()
        app = self._client(profile)
        self.status_signal.emit(f"Resetting {profile.label}...")
        self._log_json("reset", app.reset())
        self._load_current(wait_for_sync=False)

    def _sample_both(self) -> None:
        self.status_signal.emit("Writing samples to both relays...")
        samples = [(RELAYS[0], "test prvni"), (RELAYS[1], "test 22")]
        for profile, text in samples:
            app = self._client(profile)
            self._ensure_env_owner(app)
            profile.text_file.write_text(text, encoding="utf-8")
            self._log(f"Sample save {text!r} -> {profile.label}")
            self._log_json("insert", app.insert(text))
        self._load_current(wait_for_sync=False)

    def _log_json(self, label: str, value: object) -> None:
        self._log(f"{label}:\n{json.dumps(value, indent=2, ensure_ascii=False, default=str)}")

    def _log(self, message: str) -> None:
        if not self._debug:
            return
        stamp = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        self.log_signal.emit(f"[{stamp}] {message}")


def main() -> int:
    app = QApplication(sys.argv)

    worker_thread = QThread()
    worker = EvoluWorker()
    worker.moveToThread(worker_thread)

    window = MainWindow()
    window.action_requested.connect(worker.run_action)
    window.profile_requested.connect(worker.set_profile)
    window.debug_changed.connect(worker.set_debug)
    worker.log_signal.connect(window.append_debug)
    worker.status_signal.connect(window.set_status)
    worker.data_signal.connect(window.update_view)
    worker.profiles_signal.connect(window.set_profiles)
    worker.profile_index_signal.connect(window.set_profile_index)
    worker_thread.started.connect(worker.initialize)

    app.aboutToQuit.connect(worker_thread.quit)
    worker_thread.finished.connect(worker.deleteLater)

    worker_thread.start()
    window.show()
    exit_code = app.exec()
    worker_thread.wait(3000)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
