# py_evolu

Simple Python experiment with [Evolu](https://github.com/evoluhq/evolu).

Evolu does not currently have an official Python client, so this project uses a
small TypeScript sidecar with the official Evolu packages. Python calls the
sidecar and works with local SQLite data, owner/mnemonic restore, backup export,
and relay sync.

## What is here

- `py_evolu.py` - small Python wrapper, class `evolu`
- `evolu_example.py` - interactive menu example
- `src/evolu_cli.ts` - internal Evolu sidecar

The example uses:

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

## Run

```powershell
python evolu_example.py
```

The menu can:

1. Load `test.txt` and Evolu data
2. Save text to `test.txt` and Evolu
3. Synchronize through the relay
4. Export a database backup
5. Restore owner access from mnemonic
6. Show owner/mnemonic
7. Reset local DB

## Notes

This is an experiment, not a production Python Evolu client. The real Evolu
logic still runs through official TypeScript packages.
