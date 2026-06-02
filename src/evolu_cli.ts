import {
  createConsole,
  createEvolu,
  createOwnerWebSocketTransport,
  createRandom,
  createRandomBytes,
  createTime,
  createWebSocket,
  id,
  NonEmptyString1000,
  nullOr,
  SimpleName,
  SqliteBoolean,
  sqliteFalse,
  sqliteTrue,
  type AppOwner,
  type OwnerId,
} from "@evolu/common";
import { createDbWorkerForPlatform } from "@evolu/common/local-first";
import { createBetterSqliteDriver } from "@evolu/nodejs";
import BetterSQLite from "better-sqlite3";
import { writeFile } from "node:fs/promises";

const TodoId = id("Todo");

const Schema = {
  todo: {
    id: TodoId,
    title: NonEmptyString1000,
    isCompleted: nullOr(SqliteBoolean),
  },
};

type CliOptions = {
  name: string;
  localOnly: boolean;
  relay?: string;
  enableLogging: boolean;
  externalAppOwner?: AppOwner;
  transportOwnerId?: OwnerId;
};

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const makeDeps = (enableLogging: boolean) => {
  const sharedConsole = createConsole({ enableLogging });
  const createPlatformDeps = () => ({
    console: sharedConsole,
    createSqliteDriver: createBetterSqliteDriver,
    createWebSocket,
    randomBytes: createRandomBytes(),
    random: createRandom(),
    time: createTime(),
  });

  return {
    console: sharedConsole,
    createDbWorker: () => createDbWorkerForPlatform(createPlatformDeps()),
    randomBytes: createRandomBytes(),
    time: createTime(),
    reloadApp: () => undefined,
  };
};

const makeEvolu = (options: CliOptions) => {
  const transports = options.localOnly
    ? []
    : options.transportOwnerId
      ? [
          createOwnerWebSocketTransport({
            url: options.relay ?? "wss://free.evoluhq.com",
            ownerId: options.transportOwnerId,
          }),
        ]
      : [{ type: "WebSocket" as const, url: options.relay ?? "wss://free.evoluhq.com" }];

  return createEvolu(makeDeps(options.enableLogging))(Schema, {
    name: SimpleName.orThrow(options.name),
    transports,
    enableLogging: options.enableLogging,
    ...(options.externalAppOwner ? { externalAppOwner: options.externalAppOwner } : {}),
  });
};

const getStoredAppOwner = (name: string): AppOwner | undefined => {
  try {
    const db = new BetterSQLite(`${name}.db`, { readonly: true, fileMustExist: true });
    const row = db
      .prepare(
        `
          select
            appOwnerId,
            appOwnerEncryptionKey,
            appOwnerWriteKey,
            appOwnerMnemonic
          from evolu_config
          limit 1
        `,
      )
      .get() as
      | {
          appOwnerId: string;
          appOwnerEncryptionKey: Uint8Array;
          appOwnerWriteKey: Uint8Array;
          appOwnerMnemonic: string | null;
        }
      | undefined;
    db.close();
    if (!row) return undefined;
    return {
      type: "AppOwner",
      id: row.appOwnerId as AppOwner["id"],
      encryptionKey: row.appOwnerEncryptionKey as AppOwner["encryptionKey"],
      writeKey: row.appOwnerWriteKey as AppOwner["writeKey"],
      mnemonic: row.appOwnerMnemonic ? (row.appOwnerMnemonic as NonNullable<AppOwner["mnemonic"]>) : null,
    };
  } catch {
    return undefined;
  }
};

const withStoredOwnerTransport = (options: CliOptions): CliOptions => {
  if (options.localOnly || options.externalAppOwner) return options;
  const owner = getStoredAppOwner(options.name);
  if (!owner) return options;
  return { ...options, externalAppOwner: owner, transportOwnerId: owner.id };
};

const allTodosQuery = (evolu: ReturnType<typeof makeEvolu>) =>
  evolu.createQuery((db) =>
    db
      .selectFrom("todo")
      .select(["id", "title", "isCompleted", "createdAt", "updatedAt", "isDeleted"])
      .orderBy("createdAt"),
  );

const output = (value: unknown) => {
  process.stdout.write(`${JSON.stringify(value, null, 2)}\n`);
};

const serializeError = (error: unknown): unknown => {
  if (error instanceof Error) {
    return { name: error.name, message: error.message, stack: error.stack };
  }
  return error;
};

const fail = (message: string, details?: unknown): never => {
  process.stderr.write(`${message}${details ? `\n${JSON.stringify(details, null, 2)}` : ""}\n`);
  process.exit(1);
  throw new Error(message);
};

const parseArgs = (argv: string[]) => {
  const [command = "help", ...rest] = argv;
  const flags: Record<string, string | boolean> = {};

  for (let i = 0; i < rest.length; i += 1) {
    const arg = rest[i];
    if (!arg.startsWith("--")) fail(`Unexpected argument: ${arg}`);
    const key = arg.slice(2);
    const next = rest[i + 1];
    if (next == null || next.startsWith("--")) {
      flags[key] = true;
    } else {
      flags[key] = next;
      i += 1;
    }
  }

  const options: CliOptions = {
    name: String(flags.name ?? "py-evolu"),
    localOnly: Boolean(flags["local-only"]),
    enableLogging: Boolean(flags.verbose),
    ...(typeof flags.relay === "string" ? { relay: flags.relay } : {}),
  };

  return { command, flags, options };
};

const withTimeout = async <T>(promise: Promise<T>, ms: number, label: string) => {
  let timeout: ReturnType<typeof setTimeout> | undefined;
  const timeoutPromise = new Promise<never>((_, reject) => {
    timeout = setTimeout(() => reject(new Error(`${label} timed out after ${ms}ms`)), ms);
  });
  try {
    return await Promise.race([promise, timeoutPromise]);
  } finally {
    if (timeout) clearTimeout(timeout);
  }
};

const waitForMutation = async <T>(
  mutate: (onComplete: () => void) => { ok: true; value: T } | { ok: false; error: unknown },
) => {
  let resolveComplete!: () => void;
  const completed = new Promise<void>((resolve) => {
    resolveComplete = resolve;
  });
  const result = mutate(resolveComplete);
  if (result.ok === true) {
    await withTimeout(completed, 15000, "mutation completion");
    return result.value;
  }
  fail("Mutation validation failed.", result.error);
};

const waitForSyncSettle = async (options: CliOptions, flags: Record<string, string | boolean>) => {
  if (options.localOnly) return;
  await sleep(Number(flags.wait ?? 3000));
};

const listTodos = async (evolu: ReturnType<typeof makeEvolu>) => {
  const rows = await evolu.loadQuery(allTodosQuery(evolu));
  return rows.map((row) => ({
    ...row,
    isCompleted: row.isCompleted === sqliteTrue,
    isDeleted: row.isDeleted === sqliteTrue,
  }));
};

const dispose = (evolu: ReturnType<typeof makeEvolu>) => {
  void evolu;
};

const waitForOwner = async (evolu: ReturnType<typeof makeEvolu>, label = "appOwner"): Promise<AppOwner> => {
  const error = evolu.getError();
  if (error) fail(`${label} failed before wait.`, serializeError(error));

  let unsubscribe: (() => void) | undefined;
  const ownerOrError = new Promise<Awaited<typeof evolu.appOwner>>((resolve, reject) => {
    unsubscribe = evolu.subscribeError(() => {
      const nextError = evolu.getError();
      if (nextError) reject(nextError);
    });
    evolu.appOwner.then(resolve, reject);
  });

  try {
    return await withTimeout(ownerOrError, 15000, label);
  } catch (error_) {
    return fail(`${label} failed.`, serializeError(error_));
  } finally {
    unsubscribe?.();
  }
};

const run = async () => {
  const { command, flags, options } = parseArgs(process.argv.slice(2));

  if (command === "help") {
    output({
      commands: ["owner", "insert", "update", "delete", "list", "export", "reset", "restore", "smoke-local", "smoke-sync"],
      commonFlags: ["--name <db-name>", "--local-only", "--relay <ws-url>", "--verbose"],
    });
    return;
  }

  if (command === "smoke-local") {
    const evolu = makeEvolu({ ...options, name: `${options.name}-local-smoke`, localOnly: true });
    try {
      const owner = await waitForOwner(evolu, "local smoke owner");
      const inserted = await waitForMutation((onComplete) =>
        evolu.insert(
          "todo",
          { title: `local smoke ${new Date().toISOString()}`, isCompleted: sqliteFalse },
          { onComplete },
        ),
      );
      const todos = await listTodos(evolu);
      output({ ok: true, mode: "local", ownerId: owner.id, inserted, count: todos.length, todos });
    } finally {
      dispose(evolu);
    }
    return;
  }

  if (command === "smoke-sync") {
    const baseName = String(flags.name ?? `py-evolu-sync-${Date.now()}`);
    const bootstrap = makeEvolu({ ...options, name: `${baseName}-owner`, localOnly: true });
    const firstOwner = await waitForOwner(bootstrap, "sync bootstrap owner");
    const syncedOptions = {
      ...options,
      localOnly: false,
      externalAppOwner: firstOwner,
      transportOwnerId: firstOwner.id,
    };
    const first = makeEvolu({ ...syncedOptions, name: `${baseName}-a` });
    const second = makeEvolu({ ...syncedOptions, name: `${baseName}-b` });

    try {
      await waitForOwner(first, "first sync owner");
      await waitForOwner(second, "second sync owner");
      await waitForMutation((onComplete) =>
        first.insert(
          "todo",
          { title: `sync smoke ${new Date().toISOString()}`, isCompleted: sqliteFalse },
          { onComplete },
        ),
      );

      await sleep(Number(flags.wait ?? 5000));
      const secondTodos = await listTodos(second);
      output({
        ok: secondTodos.length > 0,
        mode: "sync",
        ownerId: firstOwner.id,
        restoredTo: `${baseName}-b`,
        count: secondTodos.length,
        todos: secondTodos,
      });
    } finally {
      dispose(bootstrap);
      dispose(first);
      dispose(second);
    }
    return;
  }

  const commandOptions = command === "reset" || command === "restore" ? options : withStoredOwnerTransport(options);
  const evolu = makeEvolu(commandOptions);
  try {
    if (command === "owner") {
      const owner = await waitForOwner(evolu, "owner command appOwner");
      output({ ownerId: owner.id, mnemonic: owner.mnemonic ?? null, name: commandOptions.name, localOnly: commandOptions.localOnly });
      return;
    }

    if (command === "insert") {
      await waitForOwner(evolu, "insert command appOwner");
      const title = String(flags.title ?? "");
      if (!title) fail("--title is required.");
      const inserted = await waitForMutation((onComplete) =>
        evolu.insert(
          "todo",
          {
            title,
            isCompleted: flags.completed ? sqliteTrue : sqliteFalse,
          },
          { onComplete },
        ),
      );
      await waitForSyncSettle(commandOptions, flags);
      output({ ok: true, inserted, todos: await listTodos(evolu) });
      return;
    }

    if (command === "update") {
      await waitForOwner(evolu, "update command appOwner");
      const todoId = String(flags.id ?? "");
      if (!todoId) fail("--id is required.");
      const update = {
        id: todoId as typeof TodoId.Type,
        ...(typeof flags.title === "string" ? { title: flags.title } : {}),
        ...(flags.completed ? { isCompleted: sqliteTrue } : {}),
        ...(flags.open ? { isCompleted: sqliteFalse } : {}),
      };
      const updated = await waitForMutation((onComplete) => evolu.update("todo", update, { onComplete }));
      await waitForSyncSettle(commandOptions, flags);
      output({ ok: true, updated, todos: await listTodos(evolu) });
      return;
    }

    if (command === "delete") {
      await waitForOwner(evolu, "delete command appOwner");
      const todoId = String(flags.id ?? "");
      if (!todoId) fail("--id is required.");
      const deleted = await waitForMutation((onComplete) =>
        evolu.update("todo", { id: todoId as typeof TodoId.Type, isDeleted: sqliteTrue }, { onComplete }),
      );
      await waitForSyncSettle(commandOptions, flags);
      output({ ok: true, deleted, todos: await listTodos(evolu) });
      return;
    }

    if (command === "list") {
      await waitForOwner(evolu, "list command appOwner");
      if (!commandOptions.localOnly && flags.wait) {
        await sleep(Number(flags.wait));
      }
      output({ ok: true, todos: await listTodos(evolu) });
      return;
    }

    if (command === "export") {
      await waitForOwner(evolu, "export command appOwner");
      const out = String(flags.out ?? `${options.name}.sqlite`);
      const db = await evolu.exportDatabase();
      await writeFile(out, db);
      output({ ok: true, out, bytes: db.byteLength });
      return;
    }

    if (command === "reset") {
      await waitForOwner(evolu, "reset command appOwner");
      await evolu.resetAppOwner({ reload: false });
      output({ ok: true, reset: options.name });
      return;
    }

    if (command === "restore") {
      await waitForOwner(evolu, "restore command appOwner");
      const mnemonic = String(flags.mnemonic ?? "");
      if (!mnemonic) fail("--mnemonic is required.");
      await evolu.restoreAppOwner(mnemonic as never, { reload: false });
      output({ ok: true, restored: options.name, todos: await listTodos(evolu) });
      return;
    }

    fail(`Unknown command: ${command}`);
  } finally {
    dispose(evolu);
  }
};

run()
  .then(() => {
    process.exit(0);
  })
  .catch((error: unknown) => {
    fail("Unhandled error.", serializeError(error));
  });
