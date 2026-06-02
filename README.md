# py_evolu

Simple Python experiment with [Evolu](https://github.com/evoluhq/evolu).

GitHub: [octopusengine/py_evolu](https://github.com/octopusengine/py_evolu)

Evolu does not currently have an official Python client, so this project uses a
small TypeScript sidecar with the official Evolu packages. Python calls the
sidecar and works with local SQLite data, owner/mnemonic restore, backup export,
and relay sync.

## What is here

- `py_evolu.py` - small Python wrapper, class `evolu`
- `evolu_example.py` - interactive menu example
- `src/evolu_cli.ts` - internal Evolu sidecar

The example uses:

- access key file: `.env`
- local database: `test.db`
- text file: `test.txt`
- backup file: `test_backup.sqlite`
- default relay: `wss://free.evoluhq.com`

## Requirements

- Python 3.10+
- Node.js 22+
- npm

On Windows, the current Evolu packages need a recent Node version. If your
global Node is older, update Node first.

## Install

```powershell
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

For a more detailed explanation of the local-first flow, relay sync, mnemonic
restore, and every menu action, see [evolu_example.md](evolu_example.md).

The menu can:

1. Load `test.txt` and Evolu data
2. Save text to `test.txt` and Evolu
3. Synchronize through the relay
4. Export a database backup
5. Restore owner access from mnemonic
6. Show owner/mnemonic
7. Save current mnemonic to `.env` as `EVOLU_KEY`
8. Reset local DB

## Notes

This is an experiment, not a production Python Evolu client. The real Evolu
logic still runs through official TypeScript packages.

---

## Links

- [Evolu website](https://www.evolu.dev/)
- [Evolu GitHub](https://github.com/evoluhq/evolu)
