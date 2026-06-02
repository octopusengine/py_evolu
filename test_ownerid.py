from __future__ import annotations

from pathlib import Path

from py_evolu import evolu


ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"
DB_NAME = "test_ownerid"
RELAY = "wss://free.evoluhq.com"


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


def mask_mnemonic(mnemonic: str) -> str:
    words = mnemonic.split()
    if len(words) >= 4:
        return f"{words[0]} {words[1]} ... {words[-2]} {words[-1]}"
    return "<set>"


def main() -> int:
    mnemonic = read_env().get("EVOLU_KEY", "")
    if not mnemonic:
        raise RuntimeError(f"EVOLU_KEY is missing in {ENV_FILE}")

    app = evolu(
        name=DB_NAME,
        relay=RELAY,
        debug=False,
        timeout=120,
        sync_wait_ms=0,
    )

    print(f"Loaded EVOLU_KEY from: {ENV_FILE}")
    print(f"Mnemonic: {mask_mnemonic(mnemonic)}")

    restored = app.restore(mnemonic)
    print(f"Restore result: {restored.get('ok')} ({restored.get('restored')})")

    owner = app.owner()
    print()
    print("Owner:")
    print(f"ownerId:  {owner.get('ownerId')}")
    print(f"name:     {owner.get('name')}")
    print(f"relay:    {RELAY}")
    print(f"mnemonic: {mask_mnemonic(str(owner.get('mnemonic') or ''))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
