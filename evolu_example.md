# Evolu Example Notes

This file explains what the interactive `evolu_example.py` script does and how
the pieces fit together.

## Short Concept

Evolu is a local-first data platform. The app writes to a local SQLite database
first, so the data is available on the local machine even before any network
sync happens. Synchronization is a separate step handled through an Evolu relay.

In this Python experiment, Python is not talking to Evolu directly. Python calls
a small TypeScript sidecar (`src/evolu_cli.ts`), and that sidecar uses the
official Evolu TypeScript packages.

The basic flow is:

```text
Python menu
  -> py_evolu.py wrapper
  -> TypeScript Evolu sidecar
  -> local SQLite database
  -> Evolu relay, when sync is enabled
```

## Local-First

Local-first means the local database is the primary working database. In this
example, Evolu stores data in:

```text
test.db
```

The menu can read and write data without treating the relay as the main
database. The relay is used for backup/synchronization, not as the place where
the application logic primarily lives.

## Relay And Client

The client is this local project running on your PC. The relay is the remote
sync endpoint:

```text
wss://free.evoluhq.com
```

The relay receives encrypted changes and helps another restored client/device
get them back. The relay should not need to understand your application data.
It coordinates encrypted data synchronization by owner.

## Key, Owner, And Mnemonic

Evolu identifies data ownership through an `Owner`.

The important values are:

- `ownerId`: public identifier of the owner
- `encryptionKey`: key used to encrypt/decrypt data
- `writeKey`: key proving write access
- `mnemonic`: human-readable recovery phrase

The mnemonic is a BIP39-style seed phrase. Evolu derives owner keys from the
owner secret/mnemonic. In this example, `EVOLU_KEY` stores that mnemonic:

```env
EVOLU_KEY="visit fever ... awake error witness"
```

This example does not use a Nostr key. The mnemonic is similar in spirit to a
portable private identity/recovery secret, but it is Evolu's owner mnemonic, not
a Nostr `nsec` key.

Keep `EVOLU_KEY` private. Anyone who has it can restore the owner and access the
synced encrypted data for that owner.

## Backup And Synchronization

There are two backup-like concepts here:

1. SQLite export backup

   Menu option 4 exports the local database file to:

   ```text
   test_backup.sqlite
   ```

   This is a local file backup.

2. Relay synchronization

   Menu option 3 keeps the client connected for a short time and reads data
   after waiting for the relay. When writes are made, the wrapper also waits a
   few seconds so the sidecar has time to send changes through the WebSocket
   relay.

Restore from mnemonic does not restore from `test_backup.sqlite`. It resets the
local Evolu owner from the mnemonic. If the data was already synchronized to the
relay, running sync/list after restore lets the local DB receive the synced data
again.

## Menu Actions

### 1. Load `test.txt` and Evolu data

This reads two things:

- `test.txt`, if it exists
- current rows from the local Evolu database

It does not force a relay sync unless the local Evolu sidecar happens to receive
updates while opening the database. It is mainly a local read.

### 2. Save text to `test.txt` and Evolu

This asks for a text value and writes it to:

```text
test.txt
```

Then it inserts the same text into Evolu as a todo-like row. Evolu writes the
change to `test.db` first. If relay sync is enabled, the wrapper waits for a
short period so the sidecar can send the encrypted change to the relay.

### 3. Synchronize / wait for relay

This opens the Evolu sidecar and performs a list operation with a sync wait.

The purpose is to give the WebSocket relay connection time to:

- send pending local changes
- receive remote/synced changes for the owner
- apply those changes to the local database

After the wait, the script prints the Evolu rows it sees locally.

### 4. Export Evolu DB backup

This calls Evolu's database export and writes:

```text
test_backup.sqlite
```

This is a local SQLite backup/export. It is useful for inspecting or preserving
the current local database state, but it is different from mnemonic restore.

### 5. Restore owner from mnemonic

This resets the local Evolu owner using a mnemonic.

If `.env` contains `EVOLU_KEY`, the script offers to use it automatically:

```env
EVOLU_KEY="visit fever ... awake error witness"
```

After restore, the local DB can initially look empty because restore only
recreates access to the owner. Run option 3, or use a waiting list operation, to
give the relay time to send the synchronized data back.

### 6. Show owner/mnemonic

This prints owner information.

By default, the mnemonic is masked:

```json
{
  "ownerId": "WBV3nZEN46-y2Om4IkbTow",
  "mnemonic": "visit fever ... error witness",
  "name": "test",
  "localOnly": false
}
```

The script can reveal the full mnemonic only after asking for confirmation.

### 7. Save current mnemonic to `.env` as `EVOLU_KEY`

This reads the current owner mnemonic from Evolu and writes it to:

```text
.env
```

The result is:

```env
EVOLU_KEY="your mnemonic words here"
```

The `.env` file is ignored by Git via `.gitignore`, because it contains secret
owner access.

### 8. Reset local DB

This resets the local Evolu app owner and local data for the current DB name.

It does not delete relay data by itself. If you still have the mnemonic and the
data was synchronized, you can restore the owner and synchronize again.

### 0. Exit

Stops the Python menu. No additional sync is performed unless the previous menu
action did it.

## Example Owner Output

When choosing option 6, debug mode shows the exact sidecar command:

```text
RUN: node.exe ... src/evolu_cli.ts owner --name test --relay wss://free.evoluhq.com
```

The sidecar returns JSON like:

```json
{
  "ownerId": "WBV3nZEN46-y2Om4IkbTow",
  "mnemonic": "visit fever ... awake error witness",
  "name": "test",
  "localOnly": false
}
```

In the visible menu output, the mnemonic is masked unless you explicitly reveal
it.

## References

- [Evolu documentation](https://www.evolu.dev/docs)
- [Evolu Owner API](https://www.evolu.dev/docs/api-reference/common/local-first/interfaces/Owner)
- [Evolu installation / restore notes](https://www.evolu.dev/docs/installation)
- [Mnemonic type](https://www.evolu.dev/docs/api-reference/common/Type/variables/Mnemonic)
