# Evolu Python Sandbox Wrapper

This project is a sandbox wrapper around Evolu for Python experiments.

It is not an official Evolu Python client and it is not meant to replace the
official TypeScript implementation. The goal is to make Evolu easier to try
from Python code, Python scripts, and a simple PyQt desktop app, while still
using the real Evolu packages for the parts that currently only exist in the
TypeScript ecosystem.

## Why Python

Python makes the experiment more accessible for people who want to work with:

- small local scripts
- desktop tools
- data inspection
- simple automation
- teaching and demos

The Python layer keeps the API close to normal Python usage:

```python
from py_evolu import evolu

client = evolu(name="test_relay1", relay="wss://free.evoluhq.com")
client.insert("hello from Python")
rows = client.list(wait_for_sync=True)
print(rows)
```

That makes Evolu approachable without asking every user to write a full
TypeScript app first.

## What Still Runs In TypeScript

Evolu itself still runs through official TypeScript packages:

- `@evolu/common`
- `@evolu/nodejs`

The TypeScript sidecar is `src/evolu_cli.ts`. Python starts this sidecar as a
subprocess and reads JSON from stdout.

The sidecar is responsible for:

- creating the Evolu instance
- defining the schema used by this experiment
- opening and using the local SQLite database
- deriving and restoring the Evolu app owner
- returning `ownerId` and mnemonic information
- inserting, updating, deleting, and listing rows
- exporting the local Evolu database
- resetting/restoring the app owner
- connecting to an Evolu relay over WebSocket
- waiting briefly so sync can send or receive changes

The Python file `py_evolu.py` is responsible for:

- exposing a small Python class named `evolu`
- building the sidecar command line
- choosing the database/profile name
- choosing local-only mode or relay mode
- passing relay URLs and wait times
- parsing sidecar JSON responses
- providing convenient methods such as `insert`, `list`, `restore`, and
  `export_backup`

The current call path is:

```text
Python code
  -> py_evolu.py
  -> node + tsx
  -> src/evolu_cli.ts
  -> official Evolu packages
  -> local SQLite database and optional relay sync
```

## Project Files

- `py_evolu.py` - Python wrapper class
- `src/evolu_cli.ts` - TypeScript Evolu sidecar
- `evolu_example.py` - interactive Python CLI demo
- `evolu_app.py` - PyQt6 desktop app entry point
- `evolu_ui.py` - PyQt6 desktop UI
- `.env` - optional local Evolu mnemonic as `EVOLU_KEY`

## Install On Windows

Requirements:

- Python 3.10+
- Node.js 22+
- npm
- PyQt6, only for the desktop app

Clone or unpack the project, then install Node dependencies:

```powershell
cd D:\data_codex\py_evolu
npm install
```

Install PyQt6 if you want to run the desktop app:

```powershell
python -m pip install PyQt6
```

Run the CLI example:

```powershell
python evolu_example.py
```

Run the desktop app:

```powershell
python evolu_app.py
```

Run TypeScript checks:

```powershell
npm run typecheck
```

Run sidecar smoke tests:

```powershell
npm run smoke:local
npm run smoke:sync
```

If `better-sqlite3` fails after changing Node versions, rebuild it:

```powershell
npm rebuild better-sqlite3
```

## Install On Linux

Requirements:

- Python 3.10+
- Node.js 22+
- npm
- build tools for native Node packages
- PyQt6, only for the desktop app

Example on Debian/Ubuntu:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip build-essential
```

Install a recent Node.js 22 release with your preferred method. For example,
with `nvm`:

```bash
nvm install 22
nvm use 22
```

Create and activate a Python virtual environment:

```bash
cd /path/to/py_evolu
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

Install optional desktop dependencies:

```bash
python -m pip install PyQt6
```

Install Node dependencies:

```bash
npm install
```

Run the CLI example:

```bash
python evolu_example.py
```

Run the desktop app:

```bash
python evolu_app.py
```

Run checks:

```bash
npm run typecheck
npm run smoke:local
npm run smoke:sync
```

If a native SQLite dependency was built for another Node version, rebuild it:

```bash
npm rebuild better-sqlite3
```

## Access Key

The Evolu owner mnemonic can be stored in `.env`:

```env
EVOLU_KEY="your mnemonic words here"
```

The real `.env` file is ignored by Git. Do not publish it. Anyone with the
mnemonic can restore the owner and access synced data for that owner.

## Relay Mode And Local-Only Mode

Local-only mode uses only the local SQLite database:

```python
client = evolu(name="local-test", local_only=True)
```

Relay mode also connects to an Evolu relay:

```python
client = evolu(name="relay-test", relay="wss://free.evoluhq.com")
```

The default relay in this project is:

```text
wss://free.evoluhq.com
```

The demo also uses:

```text
wss://evolu.petrkr.net
```

## Current Limits

This wrapper is intentionally small. It currently exposes only the demo schema
and a small set of commands. It is good for experiments, accessibility, and
learning, but it is not a complete Python implementation of Evolu.

The important limitation is that owner handling, encryption, local-first storage,
and relay sync are still done by the official TypeScript packages. A pure Python
Evolu library would need to port those parts carefully.
