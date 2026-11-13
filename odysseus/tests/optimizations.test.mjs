// Node wrapper for the Python optimization tests.
//
// The optimization module is Python (the repo's backend language), but
// pytest is not installed in this environment, so the suite is plain
// stdlib `unittest`. This file runs it through Node's built-in test
// runner so `npm run test:optimizations` is the single entry point.
// No model, no network, no weights — mocks only.
import { test } from "node:test";
import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import path from "node:path";
import { fileURLToPath } from "node:url";

const execFileAsync = promisify(execFile);
const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

test("python optimization suite passes (stdlib unittest, mocks only)", async () => {
  const { stdout, stderr } = await execFileAsync(
    "python3",
    ["tests/test_optimizations.py"],
    { cwd: repoRoot, timeout: 120_000 },
  );
  const output = `${stdout}\n${stderr}`;
  assert.match(output, /OK\b/, `expected unittest OK, got:\n${output}`);
  assert.doesNotMatch(output, /FAILED|ERROR:/);
});
