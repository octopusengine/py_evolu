# py_evolu

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab.svg)
![Node.js](https://img.shields.io/badge/Node.js-22%2B-339933.svg)
![TypeScript](https://img.shields.io/badge/TypeScript-sidecar-3178c6.svg)
![Evolu](https://img.shields.io/badge/Evolu-local--first-2f855a.svg)

Simple Python experiment with [Evolu](https://github.com/evoluhq/evolu).

Evolu does not currently have an official Python client, so this project uses a
small TypeScript sidecar with the official Evolu packages. Python calls the
sidecar and works with local SQLite data, owner/mnemonic restore, backup export,
and relay sync.

## What is here

- `py_evolu.py` - small Python wrapper, class `evolu`
- `evolu_example.py` - interactive menu example
- `evolu_app.py` - PyQt6 desktop example
- `evolu_ui.py` - PyQt6 UI layer used by `evolu_app.py`
- `src/evolu_cli.ts` - internal Evolu sidecar

The example uses:

- access key file: `.env`
- relay 1 database: `test_relay1.db`
- relay 2 database: `test_relay2.db`
- relay 1 text file: `test_relay1.txt`
- relay 2 text file: `test_relay2.txt`
- relay 1: `wss://free.evoluhq.com`
- relay 2: `wss://evolu.petrkr.net`

## Requirements

- Python 3.10+
- PyQt6, for the desktop GUI
- Node.js 22+
- npm

On Windows, the current Evolu packages need a recent Node version. If your
global Node is older, update Node first.

## Install

```powershell
cd py_evolu
npm install
```

If `better-sqlite3` has trouble after changing Node versions, rebuild it:

```powershell
npm rebuild better-sqlite3
```

## Access key

The Evolu owner mnemonic can be stored in `.env`:

```env
EVOLU_KEY=your-evolu-mnemonic-here
```

You can copy `.env.example` to `.env`, or use menu option 7 to save the current
owner mnemonic. The real `.env` file is ignored by Git.

## Run

```powershell
python evolu_example.py
```

Run the PyQt6 desktop app:

```powershell
python -m pip install PyQt6
python evolu_app.py
```

For a more detailed explanation of the local-first flow, relay sync, mnemonic
restore, and every menu action, see [evolu_example.md](evolu_example.md).

For the Python sandbox wrapper concept, what still runs through TypeScript, and
setup notes for Windows and Linux, see [EVOLU_LIB.md](EVOLU_LIB.md).

For owner key derivation, `ownerId`, `encryptionKey`, `writeKey`, and relay
encryption notes, see [evolu_keys.md](evolu_keys.md).

The menu can:

1. Load `test.txt` and Evolu data
2. Save text to `test.txt` and Evolu
3. Synchronize through the relay
4. Export a database backup
5. Restore owner access from mnemonic
6. Show owner/mnemonic
7. Save current mnemonic to `.env` as `EVOLU_KEY`
8. Reset local DB
9. Switch active relay profile
10. Write sample values to both relay profiles

## Notes

This is an experiment, not a production Python Evolu client. The real Evolu
logic still runs through official TypeScript packages.

---

[agama-point/agama_linky_sandbox](https://github.com/agama-point/agama_linky_sandbox)

`agama_linky_sandbox` is a local testing and learning sandbox for [hynek-jina/linky](https://github.com/hynek-jina/linky), focused on key derivation, local tooling, and small protocol experiments around Linky's Nostr, Cashu, and Evolu integrations.

🔗 [agama-point/py_nostr](https://github.com/agama-point/py_nostr)

`py_nostr` is a small experimental Python wrapper around `pynostr` for working with Nostr keys, events, relays, publishing, user metadata, and direct messages. It is useful for local protocol experiments, but scripts that publish events or send DMs perform real Nostr actions when configured with a private key.

🔗 [agama-point/py_cashu](https://github.com/agama-point/py_cashu)

`py_cashu` is an educational Python project for exploring Cashu ecash flows: mints, Lightning invoices, blind signatures, proofs, bearer tokens, wallet seed material, and token transfers. It is a console and desktop experiment for understanding the protocol, not a production wallet.

🔗 [octopusengine/py_evolu](https://github.com/octopusengine/py_evolu)

`py_evolu` is a Python experiment around Evolu local-first data, owner mnemonics, SQLite storage, backup export, restore, and relay sync. Because Evolu has no official Python client, it uses a small TypeScript sidecar with the official Evolu packages.

---

## References

- [Evolu website](https://www.evolu.dev/)
- [Evolu GitHub](https://github.com/evoluhq/evolu)
