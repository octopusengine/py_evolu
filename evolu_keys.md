# Evolu Owner Keys and Encryption

This note explains what Evolu derives from a BIP39 mnemonic, what is public, what must stay secret, and how synchronized data is encrypted before it is sent to a relay.

The examples here are based on the current local `@evolu/common` implementation used by this project.

## Short Version

Evolu uses a BIP39 mnemonic as the root secret for an owner.

From that mnemonic, Evolu derives:

- `ownerId`: a public/pseudonymous owner identifier
- `encryptionKey`: a secret symmetric key used to encrypt data changes
- `writeKey`: a secret write authorization key used by the relay/storage layer

The relay can see which owner is syncing and when changes happen, but it should not be able to read the application data without the owner encryption key.

## Key Derivation

The mnemonic is first converted to entropy. That entropy becomes the owner secret.

```text
OwnerSecret = BIP39 mnemonic entropy

ownerId       = SLIP-21(secret, ["Evolu", "OwnerIdBytes"])[0:16]
encryptionKey = SLIP-21(secret, ["Evolu", "OwnerEncryptionKey"])
writeKey      = SLIP-21(secret, ["Evolu", "OwnerWriteKey"])[0:16]
```

In other words:

- The mnemonic is the root secret.
- `ownerId` is derived from the root secret, but it is not itself secret.
- `encryptionKey` is derived from the root secret and must stay secret.
- `writeKey` is derived from the root secret and must stay secret.

## Is ownerId a Public Key?

No. `ownerId` is not a public key in the usual asymmetric cryptography sense.

It is a public, pseudonymous identifier derived from the owner secret. Evolu can expose it to the relay, and this project uses it in the owner-specific WebSocket transport.

Knowing only `ownerId` should not be enough to:

- decrypt data
- restore the owner
- authorize writes
- derive the mnemonic
- derive the encryption key
- derive the write key

The sensitive value is the mnemonic, because it can recreate the whole owner identity.

## What Must Stay Secret

Keep these private:

- BIP39 mnemonic
- `.env` value `EVOLU_KEY`
- `OwnerEncryptionKey`
- `OwnerWriteKey`
- any exported backup that contains private owner material or readable local data

The mnemonic is the most important secret. If someone has the mnemonic, they can recreate the owner and derive the same `ownerId`, `encryptionKey`, and `writeKey`.

## What Can Be Visible

Usually safe to show:

- `ownerId`
- relay URL
- local database file path
- number of synchronized rows

But even public metadata can reveal patterns. A relay can still observe that a given `ownerId` exists and when it syncs.

## How Evolu Encrypts Synced Data

Evolu encrypts database changes before they are stored by or synchronized through the relay.

The general flow is:

```text
local database change
  -> CRDT message
  -> padding
  -> XChaCha20-Poly1305 encryption
  -> encrypted relay message
```

The encryption uses:

- algorithm: `XChaCha20-Poly1305`
- key: `OwnerEncryptionKey`
- nonce: random 24-byte nonce
- payload: encoded database change / CRDT message

Before encryption, Evolu also pads the encoded change. Padding helps reduce the amount of information leaked through message length.

The relay stores encrypted messages. It can route and synchronize them, but it should not be able to inspect the actual table names, row values, or text content.

## Write Authorization vs Encryption

Evolu separates two concerns:

- `encryptionKey` protects data confidentiality
- `writeKey` authorizes writes for the owner

That means writing and reading are not the same capability.

Someone with the encryption key may be able to read encrypted data, but that does not automatically mean they can write to the relay.

Someone with the write key may be able to authorize writes, but that does not automatically mean they can decrypt existing data.

Someone with the mnemonic can derive both.

## Local Database vs Relay Data

The encryption described above protects synchronized relay data.

In this Python test project, the local SQLite database files such as `test.db`, `test_relay1.db`, or `test_relay2.db` are local application storage. They should be treated as local private data.

Do not assume that the local test database file is encrypted just because relay synchronization is encrypted.

For practical testing:

- `.env` protects the mnemonic from being hard-coded in Python files.
- `.gitignore` should exclude `.env`, local `.db` files, local `.sqlite` files, and test text files.
- Relay synchronization should be considered encrypted transport/storage of Evolu changes.
- Local files should still be protected by the machine, filesystem, backup policy, or additional application-level encryption if needed.

## What Happens in This Project

This project stores the mnemonic in `.env`:

```text
EVOLU_KEY="word1 word2 ... word12"
```

The Python wrapper loads that mnemonic and passes it to the Evolu TypeScript sidecar.

The sidecar restores or creates the Evolu owner, derives the same owner identity, and then uses that owner when reading, writing, syncing, backing up, or restoring data.

For example, if the mnemonic is the same, Evolu should derive the same:

- `ownerId`
- `encryptionKey`
- `writeKey`

That is why restoring from mnemonic gives access to the same synchronized owner data.

## Relay Visibility

A relay can generally see:

- relay connection
- `ownerId`
- timestamps or sync timing
- encrypted message sizes
- encrypted blobs

A relay should not see:

- mnemonic
- encryption key
- write key
- plaintext row values
- plaintext todo titles
- plaintext text content stored through Evolu changes

So, for the current test scenario, a relay may know that owner `WBV3nZEN46-y2Om4IkbTow` is syncing, but it should not be able to read `"test prvni"` or `"test 22"` unless it also has the owner encryption key or mnemonic.

## Practical Rule

Treat the mnemonic as the real master key.

```text
mnemonic -> ownerId + encryptionKey + writeKey
```

If you lose the mnemonic, you may lose the ability to restore the owner.

If someone else gets the mnemonic, they can become the same owner.

