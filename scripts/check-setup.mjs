#!/usr/bin/env node
/**
 * Verifies the local toolchain matches what CivicLens's monorepo expects
 * before a new contributor runs `pnpm install` / `uv sync`. Intentionally
 * dependency-free (plain Node.js) so it works before any install step.
 */

import { execFileSync } from "node:child_process";

function run(command, args) {
  try {
    // shell: true is needed so this resolves .cmd/.ps1 shims on Windows
    // (e.g. pnpm) as well as plain executables on POSIX. The full command
    // line is built as one string (args are always our own hardcoded
    // literals, e.g. "--version" — never user input) so Node has nothing
    // to (mis)escape, avoiding the shell+args-array caveat entirely.
    const commandLine = [command, ...args].join(" ");
    return execFileSync(commandLine, [], { encoding: "utf8", shell: true }).trim();
  } catch {
    return null;
  }
}

function checkMinNodeMajor(versionString, minMajor) {
  const match = /^v?(\d+)\./.exec(versionString ?? "");
  return match ? Number(match[1]) >= minMajor : false;
}

const checks = [
  {
    name: "Node.js >= 20",
    result: checkMinNodeMajor(run("node", ["--version"]), 20),
    detail: run("node", ["--version"]),
  },
  {
    name: "pnpm available",
    result: run("pnpm", ["--version"]) !== null,
    detail: run("pnpm", ["--version"]),
  },
  {
    name: "Python >= 3.12",
    result: (() => {
      const version = run("python", ["--version"]);
      const match = /Python (\d+)\.(\d+)/.exec(version ?? "");
      return match ? Number(match[1]) === 3 && Number(match[2]) >= 12 : false;
    })(),
    detail: run("python", ["--version"]),
  },
  {
    name: "uv available",
    result: run("uv", ["--version"]) !== null,
    detail: run("uv", ["--version"]),
  },
];

let allPassed = true;
for (const check of checks) {
  const status = check.result ? "OK  " : "MISSING";
  if (!check.result) allPassed = false;
  console.log(`[${status}] ${check.name}${check.detail ? ` (${check.detail})` : ""}`);
}

if (!allPassed) {
  console.error("\nOne or more required tools are missing. See README.md 'Prerequisites'.");
  process.exit(1);
}

console.log("\nAll prerequisites found.");
