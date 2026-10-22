// Adapt Next's flags and optionally launch an isolated local API + scheduler.
import { spawn, spawnSync } from "node:child_process";
import path from "node:path";
import { existsSync } from "node:fs";
const input = process.argv.slice(2);
let port = process.env.PORT || "3000";
for (let i = 0; i < input.length; i++)
  if (input[i] === "--port") port = input[i + 1];
const children = [];
const supervised = input.includes("--strictPort");
if (input.includes("--with-backend")) {
  const cwd = path.resolve("../backend");
  const runtimePython =
    "/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python3";
  const python =
    process.env.CODEX_PRIMARY_RUNTIME_PYTHON ||
    (supervised && existsSync(runtimePython) ? runtimePython : "python3");
  const env = {
    ...process.env,
    APP_ENV: "development",
    COOKIE_SECURE: "false",
    PUBLIC_URL: supervised
      ? `http://terminal.local:${port}`
      : `http://localhost:${port}`,
    DATABASE_URL:
      process.env.DATABASE_URL || "sqlite:////tmp/hackamatch-preview.db",
  };
  const migration = spawnSync(python, ["-m", "alembic", "upgrade", "head"], {
    cwd,
    env,
    stdio: "inherit",
  });
  if (migration.status !== 0) {
    console.error(
      "Backend migration did not start or failed:",
      migration.error?.code || migration.status,
    );
    process.exit(migration.status || 1);
  }
  for (const args of [
    [
      "-m",
      "uvicorn",
      "app.main:app",
      "--host",
      "127.0.0.1",
      "--port",
      "8000",
      "--no-access-log",
    ],
    ["-m", "app.worker"],
  ])
    children.push(spawn(python, args, { cwd, env, stdio: "inherit" }));
}
const web = spawn(
  process.execPath,
  [
    "node_modules/next/dist/bin/next",
    "dev",
    "--hostname",
    "0.0.0.0",
    "--port",
    port,
  ],
  { stdio: "inherit" },
);
children.push(web);
for (const signal of ["SIGINT", "SIGTERM"])
  process.on(signal, () => {
    for (const child of children) child.kill(signal);
  });
web.on("exit", (code) => {
  for (const child of children) if (child !== web) child.kill("SIGTERM");
  process.exit(code ?? 0);
});
