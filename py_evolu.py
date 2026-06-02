from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DEFAULT_RELAY = "wss://free.evoluhq.com"
BUNDLED_NODE = Path(
    r"C:\Users\Yenda\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
)
TSX_CLI = ROOT / "node_modules" / "tsx" / "dist" / "cli.mjs"
EVOLU_CLI = ROOT / "src" / "evolu_cli.ts"


class evolu:
    def __init__(
        self,
        name: str = "py-evolu-main",
        *,
        local_only: bool = False,
        relay: str | None = None,
        debug: bool = False,
        timeout: int = 45,
        sync_wait_ms: int = 8000,
    ) -> None:
        self.name = name
        self.local_only = local_only
        self.relay = relay
        self.debug = debug
        self.timeout = timeout
        self.sync_wait_ms = sync_wait_ms

    @property
    def relay_url(self) -> str:
        return "local-only / no relay" if self.local_only else self.relay or DEFAULT_RELAY

    @property
    def db_path(self) -> Path:
        return ROOT / f"{self.name}.db"

    def owner(self) -> dict[str, Any]:
        return self._run("owner")

    def insert(self, title: str, *, completed: bool = False) -> dict[str, Any]:
        args = ["insert", "--title", title]
        if completed:
            args.append("--completed")
        self._add_sync_wait(args)
        return self._run(*args)

    def update(
        self,
        todo_id: str,
        *,
        title: str | None = None,
        completed: bool | None = None,
    ) -> dict[str, Any]:
        args = ["update", "--id", todo_id]
        if title is not None:
            args.extend(["--title", title])
        if completed is True:
            args.append("--completed")
        if completed is False:
            args.append("--open")
        self._add_sync_wait(args)
        return self._run(*args)

    def delete(self, todo_id: str) -> dict[str, Any]:
        args = ["delete", "--id", todo_id]
        self._add_sync_wait(args)
        return self._run(*args)

    def list(self, *, wait_for_sync: bool = False) -> dict[str, Any]:
        args = ["list"]
        if wait_for_sync:
            self._add_sync_wait(args)
        return self._run(*args)

    def export_backup(self, path: str | Path) -> dict[str, Any]:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return self._run("export", "--out", str(path))

    def reset(self) -> dict[str, Any]:
        return self._run("reset")

    def restore(self, mnemonic: str) -> dict[str, Any]:
        return self._run("restore", "--mnemonic", mnemonic)

    def wait(self, seconds: float, reason: str = "waiting") -> None:
        self._debug(f"{reason}: {seconds:.1f}s")
        time.sleep(seconds)

    def _run(self, *args: str) -> dict[str, Any]:
        node = str(BUNDLED_NODE) if BUNDLED_NODE.exists() else "node"
        cmd = [node, str(TSX_CLI), str(EVOLU_CLI), *args, "--name", self.name]
        if self.local_only:
            cmd.append("--local-only")
        if self.relay:
            cmd.extend(["--relay", self.relay])
        env = os.environ.copy()
        if BUNDLED_NODE.exists():
            node_bin = str(BUNDLED_NODE.parent)
            old_path = env.get("Path") or env.get("PATH") or ""
            env["Path"] = f"{node_bin}{os.pathsep}{old_path}"
            env["PATH"] = env["Path"]

        self._debug(f"RUN: {' '.join(cmd)}")
        started = time.perf_counter()
        completed = subprocess.run(
            cmd,
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            timeout=self.timeout,
            check=False,
        )
        elapsed = time.perf_counter() - started

        self._debug(f"exit={completed.returncode} elapsed={elapsed:.2f}s")
        if completed.stdout.strip():
            self._debug(f"stdout:\n{completed.stdout.rstrip()}")
        if completed.stderr.strip():
            self._debug(f"stderr:\n{completed.stderr.rstrip()}")

        if completed.returncode != 0:
            raise RuntimeError(
                "Evolu sidecar failed\n"
                f"command: {' '.join(cmd)}\n"
                f"stdout:\n{completed.stdout}\n"
                f"stderr:\n{completed.stderr}"
            )

        text = completed.stdout.strip()
        json_start = text.find("{")
        if json_start < 0:
            raise RuntimeError(f"Evolu sidecar did not return JSON:\n{text}")
        return json.loads(text[json_start:])

    def _debug(self, message: str) -> None:
        if not self.debug:
            return
        stamp = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        print(f"[{stamp}] {message}", flush=True)

    def _add_sync_wait(self, args: list[str]) -> None:
        if not self.local_only and self.sync_wait_ms > 0:
            args.extend(["--wait", str(self.sync_wait_ms)])


Evolu = evolu
