// <!-- @scry.entry
// id: code.patrickscript-conformance-ts~7d72dc16
// kind: code
// status: active
// weight: 0.85
// tags:
//   - "topic:patrickscript"
//   - "patrickscript"
//   - "topic:conformance"
//   - "conformance"
//   - "topic:test-harness"
//   - "test-harness"
//   - "scope:patrick-script"
//   - "patrick-script"
//   - "typescript"
// summary: >
//   Node-only conformance harness for the TypeScript PatrickScript
//   interpreter. Walks corpus/*.ps, runs each through the TS interpreter
//   with corpus/<name>.stdin as input, and compares stdout to
//   corpus/<name>.expected byte-for-byte. Mirrors corpus/run-tests.sh
//   (which exercises the Python reference) so byte-equal corpus output
//   across both implementations is the conformance claim. Run via
//   `npx tsx site/js/conformance.ts` from the patrick-script project root.
//   Also: conformance.ts, PatrickScript TS test harness, byte-equal
//   conformance, parity test, ps.py vs ps-interpreter.ts, corpus runner.
// rationale: >
//   The TS interpreter is only credible if it produces byte-identical
//   stdout to the Python reference for every corpus program. This script
//   is the mechanical claim of that property; CI runs it on every change.
// applies: validating the TypeScript interpreter, running the full corpus through TS, debugging TS/Python divergence, gating CI on conformance
// seeded_questions:
//   - "How do I verify the PatrickScript TS interpreter matches the Python reference?"
//   - "PatrickScript TS conformance harness"
//   - "Run corpus through the JS interpreter"
//   - "npx tsx conformance"
// @scry.entry.end -->

/**
 * Conformance harness: TS interpreter vs corpus/*.expected.
 *
 * Usage:
 *   npx tsx site/js/conformance.ts                # run all
 *   npx tsx site/js/conformance.ts add fizzbuzz   # filter by name
 *   npx tsx site/js/conformance.ts --verbose      # show diffs on FAIL
 *
 * Exit code: 0 if all PASS, 1 otherwise.
 */

import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, dirname, basename, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { Interpreter, ParseError } from "./ps-interpreter.ts";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const PROJECT_ROOT = resolve(__dirname, "..", "..");
const CORPUS = join(PROJECT_ROOT, "corpus");

interface Args {
  filters: string[];
  verbose: boolean;
}

function parseArgs(argv: string[]): Args {
  const filters: string[] = [];
  let verbose = false;
  for (const a of argv) {
    if (a === "--verbose" || a === "-v") verbose = true;
    else if (!a.startsWith("-")) filters.push(a);
  }
  return { filters, verbose };
}

function listCorpusPrograms(): string[] {
  return readdirSync(CORPUS)
    .filter((f) => f.endsWith(".ps"))
    .map((f) => f.slice(0, -3))
    .sort();
}

function readIfExists(path: string): string {
  try {
    return readFileSync(path, "utf8");
  } catch {
    return "";
  }
}

function bytesToVisible(bytes: number[]): string {
  return bytes
    .map((b) => {
      if (b === 0x0a) return "\\n";
      if (b === 0x09) return "\\t";
      if (b < 0x20 || b > 0x7e) return `\\x${b.toString(16).padStart(2, "0")}`;
      return String.fromCharCode(b);
    })
    .join("");
}

function runOne(name: string): {
  pass: boolean;
  expected: string;
  actual: string;
  error?: string;
} {
  const psPath = join(CORPUS, `${name}.ps`);
  const stdinPath = join(CORPUS, `${name}.stdin`);
  const expectedPath = join(CORPUS, `${name}.expected`);

  const source = readFileSync(psPath, "utf8");
  let stdin = "";
  try {
    if (statSync(stdinPath).size > 0) stdin = readFileSync(stdinPath, "utf8");
  } catch { /* no stdin file */ }
  const expected = readIfExists(expectedPath);

  let actual = "";
  let error: string | undefined;
  try {
    const interp = new Interpreter(source, stdin);
    interp.run();
    const state = interp.state();
    actual = interp.stdoutText();
    if (state.status === "error") error = state.error;
  } catch (e) {
    if (e instanceof ParseError) {
      error = `parse error: ${e.message}`;
    } else {
      error = e instanceof Error ? e.message : String(e);
    }
  }

  // The Python harness compares stdout only — strip a trailing newline from
  // `expected` because `cat <file>` and bash command substitution `$(...)`
  // collapse the final newline. We replicate that semantic: trim ONE trailing
  // newline from both sides if present.
  const norm = (s: string) => (s.endsWith("\n") ? s.slice(0, -1) : s);
  const pass = norm(actual) === norm(expected);
  return { pass, expected, actual, error };
}

function main(): void {
  const { filters, verbose } = parseArgs(process.argv.slice(2));
  let names = listCorpusPrograms();
  if (filters.length > 0) {
    names = names.filter((n) => filters.some((f) => n.includes(f)));
  }

  let pass = 0;
  let fail = 0;
  const failures: Array<{ name: string; expected: string; actual: string; error?: string }> = [];

  for (const name of names) {
    const result = runOne(name);
    if (result.pass) {
      console.log(`PASS  ${name}`);
      pass += 1;
    } else {
      console.log(`FAIL  ${name}`);
      fail += 1;
      failures.push({ name, ...result });
    }
  }

  console.log("");
  console.log(`Results: ${pass} passed, ${fail} failed`);

  if (verbose && failures.length > 0) {
    console.log("");
    console.log("--- failures ---");
    for (const f of failures) {
      console.log(`\n${f.name}`);
      console.log(`  expected: ${bytesToVisible(Array.from(new TextEncoder().encode(f.expected)))}`);
      console.log(`  actual:   ${bytesToVisible(Array.from(new TextEncoder().encode(f.actual)))}`);
      if (f.error) console.log(`  error:    ${f.error}`);
    }
  }

  process.exit(fail === 0 ? 0 : 1);
}

main();
