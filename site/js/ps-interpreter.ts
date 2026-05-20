// <!-- @scry.entry
// id: code.patrickscript-interpreter-ts~ceda823a
// kind: code
// status: active
// weight: 0.9
// tags:
//   - "topic:patrickscript"
//   - "patrickscript"
//   - "topic:interpreter"
//   - "interpreter"
//   - "topic:typescript"
//   - "typescript"
//   - "topic:stepper"
//   - "stepper"
//   - "scope:patrick-script"
//   - "patrick-script"
// summary: >
//   PatrickScript v1.3.0 TypeScript interpreter — a 1:1 port of the
//   Python reference at src/patrickscript/ps.py, restructured around a
//   stepper-friendly API: parse() → instructions; new Interpreter(src,
//   stdin) → machine; step() advances one opcode and returns a state
//   snapshot; run() executes to halt or step limit; reset() reinitializes.
//   Pure module — no DOM, no Node imports — usable by both the browser
//   stepper UI (site/js/play.ts) and the VS Code extension's CodeLens
//   disassembler. Conformance: every corpus/*.ps program produces
//   byte-equal stdout against the Python reference (site/js/conformance.ts).
//   Also: ps-interpreter.ts, PatrickScript TS, JavaScript interpreter,
//   browser interpreter, step machine, MachineState, visualgo, reusable
//   interpreter, disassembler, opcode visualization.
// rationale: >
//   The visualizer at patrickscript.com/play and the VS Code CodeLens
//   extension both need a JS-side interpreter that exposes per-step
//   state. Without this module each surface would re-implement the
//   semantics and silently diverge from the Python reference.
// applies: building the visual stepper, building the VS Code extension, disassembling .ps files in the browser, running PatrickScript in JS, verifying TS/Python conformance
// seeded_questions:
//   - "Where is the PatrickScript TypeScript interpreter?"
//   - "How do I step a PatrickScript program in JS?"
//   - "PatrickScript browser interpreter"
//   - "MachineState shape PatrickScript"
//   - "Disassemble PatrickScript in JavaScript"
// @scry.entry.end -->

/**
 * PatrickScript v1.3.0 — TypeScript reference port.
 *
 * Two-token alphabet: the literal word "patrick" and a single space " ".
 * A run of N "patrick" words = arity N. The run of spaces after it = gap;
 * gap_arg = max(gap_width - 1, 0). Trailing word with no gap → gap_arg=0.
 *
 * Instruction set is documented in MNEMONICS below and in the canonical
 * spec at spec/patrickscript.md. Behavior is identical to the Python
 * reference at src/patrickscript/ps.py except where noted (see "JS notes").
 */

export const WORD_TOKEN = "patrick";
export const WORD_LEN = WORD_TOKEN.length;

export interface Instr {
  arity: number;
  gapArg: number;
}

export interface MnemonicEntry {
  /** Resolved mnemonic, e.g. "PUSH 5" or "ADD". */
  mnemonic: string;
  /** Short description of the opcode's effect. */
  description: string;
  /** Family name without operand (e.g. "PUSH" for PUSH 5). */
  family: string;
}

/** A snapshot of the machine after a step. Cloned-by-construction so the
 *  UI can keep prior snapshots for animation diffs. */
export interface MachineState {
  /** Index of the next instruction to execute (after the most recent step). */
  ip: number;
  /** Stack contents, deepest first; the rightmost element is the top. */
  stack: number[];
  /** Sparse memory; only keys with non-default values are present. */
  memory: Record<number, number>;
  /** Bytes remaining on stdin. */
  stdin: number[];
  /** Bytes emitted to stdout so far. */
  stdout: number[];
  /** "running" | "halted" | "error". */
  status: "running" | "halted" | "error";
  /** Error message if status === "error". */
  error?: string;
  /** The instruction just executed (or null on initial state). */
  lastExecuted: {
    idx: number;
    arity: number;
    gapArg: number;
    mnemonic: string;
  } | null;
  /** Total steps taken since last reset. */
  steps: number;
}

// ---------------------------------------------------------------------------
// Parsing
// ---------------------------------------------------------------------------

export class ParseError extends Error {
  position: number;
  constructor(position: number, message: string) {
    super(message);
    this.position = position;
    this.name = "ParseError";
  }
}

/** Parse PatrickScript source into a flat instruction list. */
export function parse(source: string): Instr[] {
  if (!source) return [];

  const instructions: Instr[] = [];
  const n = source.length;
  let i = 0;

  while (i < n) {
    if (source.substr(i, WORD_LEN) !== WORD_TOKEN) {
      throw new ParseError(
        i,
        `unexpected token near '${source.substr(Math.max(0, i - 10), 20).replace(/\n/g, "\\n")}'`,
      );
    }
    let arity = 0;
    while (i < n && source.substr(i, WORD_LEN) === WORD_TOKEN) {
      arity += 1;
      i += WORD_LEN;
    }
    let gapWidth = 0;
    while (i < n && source.charAt(i) === " ") {
      gapWidth += 1;
      i += 1;
    }
    if (i < n && source.charAt(i) !== "p") {
      throw new ParseError(
        i,
        `unexpected token near '${source.substr(Math.max(0, i - 10), 20).replace(/\n/g, "\\n")}'`,
      );
    }
    const gapArg = Math.max(gapWidth - 1, 0);
    instructions.push({ arity, gapArg });
  }

  return instructions;
}

// ---------------------------------------------------------------------------
// Disassembly
// ---------------------------------------------------------------------------

interface MnemonicTableEntry {
  family: string;
  template: string; // "PUSH n" or "ADD"; "n" is the operand placeholder
  description: string;
  hasOperand: boolean;
}

/** (arity, gap_arg) → entry. When gap_arg is the wildcard "*", the family
 *  takes an operand (PUSH n, JUMP n, etc.). */
const MNEMONICS: Record<string, MnemonicTableEntry> = {
  "1,*": { family: "PUSH", template: "PUSH n", description: "push immediate n", hasOperand: true },
  "2,0": { family: "POP", template: "POP", description: "discard top", hasOperand: false },
  "2,1": { family: "DUP", template: "DUP", description: "duplicate top", hasOperand: false },
  "2,2": { family: "SWAP", template: "SWAP", description: "swap top two", hasOperand: false },
  "2,3": { family: "ROT", template: "ROT", description: "rotate top three", hasOperand: false },
  "3,0": { family: "ADD", template: "ADD", description: "a b → a+b", hasOperand: false },
  "3,1": { family: "SUB", template: "SUB", description: "a b → a-b", hasOperand: false },
  "3,2": { family: "MUL", template: "MUL", description: "a b → a*b", hasOperand: false },
  "3,3": { family: "DIV", template: "DIV", description: "a b → floor(a/b)", hasOperand: false },
  "3,4": { family: "MOD", template: "MOD", description: "a b → a mod b", hasOperand: false },
  "3,5": { family: "NEG", template: "NEG", description: "a → -a", hasOperand: false },
  "4,0": { family: "EQ", template: "EQ", description: "a b → (a==b)", hasOperand: false },
  "4,1": { family: "LT", template: "LT", description: "a b → (a<b)", hasOperand: false },
  "4,2": { family: "GT", template: "GT", description: "a b → (a>b)", hasOperand: false },
  "4,3": { family: "AND", template: "AND", description: "a b → a&b", hasOperand: false },
  "4,4": { family: "OR", template: "OR", description: "a b → a|b", hasOperand: false },
  "4,5": { family: "XOR", template: "XOR", description: "a b → a^b", hasOperand: false },
  "4,6": { family: "NOT", template: "NOT", description: "a → ~a", hasOperand: false },
  "5,*": { family: "JUMP", template: "JUMP n", description: "jump to instruction n", hasOperand: true },
  "6,*": { family: "JUMPZ", template: "JUMPZ n", description: "if top==0, jump to n", hasOperand: true },
  "7,*": { family: "JUMPNZ", template: "JUMPNZ n", description: "if top!=0, jump to n", hasOperand: true },
  "8,0": { family: "INCHAR", template: "INCHAR", description: "read byte → stack", hasOperand: false },
  "8,1": { family: "OUTCHAR", template: "OUTCHAR", description: "pop → write byte", hasOperand: false },
  "8,2": { family: "INNUM", template: "INNUM", description: "read int → stack", hasOperand: false },
  "8,3": { family: "OUTNUM", template: "OUTNUM", description: "pop → write int+newline", hasOperand: false },
  "9,0": { family: "LOAD", template: "LOAD", description: "pop addr → push mem[addr]", hasOperand: false },
  "9,1": { family: "STORE", template: "STORE", description: "pop val addr → mem[addr]=val", hasOperand: false },
  "10,*": { family: "HALT", template: "HALT", description: "terminate", hasOperand: false },
  "11,*": { family: "CALL", template: "CALL n", description: "push return addr; jump to n", hasOperand: true },
  "12,*": { family: "RET", template: "RET", description: "pop return addr; jump there", hasOperand: false },
  "13,*": { family: "PUSHN", template: "PUSHN n", description: "push -n (negative immediate)", hasOperand: true },
  "14,*": { family: "PICK", template: "PICK n", description: "copy n-th element from top", hasOperand: true },
};

/** Resolve one instruction to a mnemonic. */
export function mnemonicOf(instr: Instr): MnemonicEntry {
  const specific = `${instr.arity},${instr.gapArg}`;
  const family = `${instr.arity},*`;
  const entry = MNEMONICS[specific] ?? MNEMONICS[family];
  if (!entry) {
    return {
      mnemonic: `???`,
      description: `arity=${instr.arity} gap_arg=${instr.gapArg}`,
      family: "???",
    };
  }
  const mnemonic = entry.hasOperand
    ? entry.template.replace("n", String(instr.gapArg))
    : entry.template;
  return { mnemonic, description: entry.description, family: entry.family };
}

/** Disassemble a parsed instruction list into one-line strings. */
export function disassemble(instructions: Instr[]): string[] {
  return instructions.map((instr, idx) => {
    const { mnemonic, description } = mnemonicOf(instr);
    return `${String(idx).padStart(4)}  ${mnemonic.padEnd(16)}  ; ${description}`;
  });
}

// ---------------------------------------------------------------------------
// Execution — Interpreter (stepper-friendly)
// ---------------------------------------------------------------------------

/**
 * Stack-machine interpreter with a per-step state snapshot.
 *
 * JS notes:
 *   - Integers are represented as JS `number` (IEEE-754 doubles). For values
 *     within ±2^53 this matches Python's unbounded ints; outside that range
 *     precision loss is possible. The PatrickScript corpus stays in 32-bit
 *     range so this is a non-issue in practice.
 *   - Bitwise ops (AND/OR/XOR/NOT) coerce to 32-bit signed in JS via `& | ^ ~`.
 *     This matches Python's two's-complement semantics for small ints.
 *   - DIV/MOD use Python-style floor semantics (Math.floor(a/b)) so negative
 *     results match the Python reference.
 */
export class Interpreter {
  private instructions: Instr[] = [];
  private stack: number[] = [];
  private memory: Map<number, number> = new Map();
  private stdinBuf: number[] = [];
  private stdoutBuf: number[] = [];
  private ip = 0;
  private steps = 0;
  private status: "running" | "halted" | "error" = "running";
  private err: string | undefined;
  private lastExecuted: MachineState["lastExecuted"] = null;

  constructor(source: string, stdin: string | number[] | Uint8Array = "") {
    this.reset(source, stdin);
  }

  reset(source: string, stdin: string | number[] | Uint8Array = ""): void {
    this.instructions = parse(source);
    this.stack = [];
    this.memory = new Map();
    this.stdinBuf = toByteArray(stdin);
    this.stdoutBuf = [];
    this.ip = 0;
    this.steps = 0;
    this.status = this.instructions.length === 0 ? "halted" : "running";
    this.err = undefined;
    this.lastExecuted = null;
  }

  /** Public view of the parsed instructions. */
  program(): readonly Instr[] {
    return this.instructions;
  }

  /** Current machine state. Returns a defensive copy. */
  state(): MachineState {
    return {
      ip: this.ip,
      stack: [...this.stack],
      memory: Object.fromEntries(this.memory),
      stdin: [...this.stdinBuf],
      stdout: [...this.stdoutBuf],
      status: this.status,
      error: this.err,
      lastExecuted: this.lastExecuted,
      steps: this.steps,
    };
  }

  /** Convenience: stdout as a UTF-8-ish string (replacement for non-UTF). */
  stdoutText(): string {
    return new TextDecoder("utf-8", { fatal: false }).decode(
      new Uint8Array(this.stdoutBuf),
    );
  }

  /** Execute up to `maxSteps` instructions (default: Infinity). Returns the
   *  final state. Stops on HALT, error, or end-of-program. */
  run(maxSteps: number = Infinity): MachineState {
    let remaining = maxSteps;
    while (this.status === "running" && remaining > 0) {
      this.step();
      remaining -= 1;
    }
    return this.state();
  }

  /** Execute exactly one instruction. Returns the resulting state.
   *  No-op if status !== "running". */
  step(): MachineState {
    if (this.status !== "running") return this.state();

    if (this.ip >= this.instructions.length) {
      this.status = "halted";
      return this.state();
    }

    const idx = this.ip;
    const { arity, gapArg } = this.instructions[idx];
    this.ip += 1; // advance before execution; jumps may override
    this.steps += 1;

    try {
      this.execOne(arity, gapArg);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      this.status = "error";
      this.err = msg;
    }

    const mnemonic = mnemonicOf({ arity, gapArg }).mnemonic;
    this.lastExecuted = { idx, arity, gapArg, mnemonic };

    if (this.status === "running" && this.ip >= this.instructions.length) {
      this.status = "halted";
    }

    return this.state();
  }

  // ---- internal dispatch ----------------------------------------------------

  private pop(): number {
    if (this.stack.length === 0) throw new Error("stack underflow");
    return this.stack.pop()!;
  }

  private execOne(arity: number, gapArg: number): void {
    const progLen = this.instructions.length;

    switch (arity) {
      case 1: // PUSH n
        this.stack.push(gapArg);
        return;

      case 2: // stack manipulation
        if (gapArg === 0) { this.pop(); return; }
        if (gapArg === 1) { const a = this.pop(); this.stack.push(a, a); return; }
        if (gapArg === 2) { const b = this.pop(), a = this.pop(); this.stack.push(b, a); return; }
        if (gapArg === 3) {
          const c = this.pop(), b = this.pop(), a = this.pop();
          this.stack.push(b, c, a); return;
        }
        throw new Error(`illegal gap_arg ${gapArg} for arity 2 at instruction ${this.ip - 1}`);

      case 3: // arithmetic
        if (gapArg === 5) { const a = this.pop(); this.stack.push(-a); return; }
        if (gapArg <= 4) {
          const b = this.pop(), a = this.pop();
          if (gapArg === 0) { this.stack.push(a + b); return; }
          if (gapArg === 1) { this.stack.push(a - b); return; }
          if (gapArg === 2) { this.stack.push(a * b); return; }
          if (gapArg === 3) {
            if (b === 0) throw new Error("division by zero (DIV)");
            this.stack.push(Math.floor(a / b));
            return;
          }
          if (gapArg === 4) {
            if (b === 0) throw new Error("division by zero (MOD)");
            this.stack.push(a - b * Math.floor(a / b));
            return;
          }
        }
        throw new Error(`illegal gap_arg ${gapArg} for arity 3 at instruction ${this.ip - 1}`);

      case 4: // comparison/bitwise
        if (gapArg === 6) { const a = this.pop(); this.stack.push(~a); return; }
        if (gapArg <= 5) {
          const b = this.pop(), a = this.pop();
          if (gapArg === 0) { this.stack.push(a === b ? 1 : 0); return; }
          if (gapArg === 1) { this.stack.push(a < b ? 1 : 0); return; }
          if (gapArg === 2) { this.stack.push(a > b ? 1 : 0); return; }
          if (gapArg === 3) { this.stack.push(a & b); return; }
          if (gapArg === 4) { this.stack.push(a | b); return; }
          if (gapArg === 5) { this.stack.push(a ^ b); return; }
        }
        throw new Error(`illegal gap_arg ${gapArg} for arity 4 at instruction ${this.ip - 1}`);

      case 5: { // JUMP
        const target = gapArg;
        if (target >= progLen) {
          throw new Error(`JUMP target ${target} out of bounds (program length ${progLen})`);
        }
        this.ip = target;
        return;
      }

      case 6: { // JUMPZ
        const cond = this.pop();
        const target = gapArg;
        if (cond === 0) {
          if (target >= progLen) {
            throw new Error(`JUMPZ target ${target} out of bounds (program length ${progLen})`);
          }
          this.ip = target;
        }
        return;
      }

      case 7: { // JUMPNZ
        const cond = this.pop();
        const target = gapArg;
        if (cond !== 0) {
          if (target >= progLen) {
            throw new Error(`JUMPNZ target ${target} out of bounds (program length ${progLen})`);
          }
          this.ip = target;
        }
        return;
      }

      case 8: // I/O
        if (gapArg === 0) {
          // INCHAR — read 1 byte; -1 on EOF
          const ch = this.stdinBuf.shift();
          this.stack.push(ch === undefined ? -1 : ch);
          return;
        }
        if (gapArg === 1) {
          // OUTCHAR — pop, write byte (low 8 bits)
          const c = this.pop();
          this.stdoutBuf.push(((c % 256) + 256) % 256);
          return;
        }
        if (gapArg === 2) {
          // INNUM — read line, parse as int, -1 on bad parse/EOF
          if (this.stdinBuf.length === 0) { this.stack.push(-1); return; }
          let line = "";
          while (this.stdinBuf.length > 0) {
            const b = this.stdinBuf.shift()!;
            if (b === 0x0a) break; // '\n'
            line += String.fromCharCode(b);
          }
          const stripped = line.trim();
          const n = Number.parseInt(stripped, 10);
          if (Number.isNaN(n) || !/^-?\d+$/.test(stripped)) {
            this.stack.push(-1);
          } else {
            this.stack.push(n);
          }
          return;
        }
        if (gapArg === 3) {
          // OUTNUM — pop, write int + newline
          const n = this.pop();
          for (const c of String(n)) this.stdoutBuf.push(c.charCodeAt(0));
          this.stdoutBuf.push(0x0a);
          return;
        }
        throw new Error(`illegal gap_arg ${gapArg} for arity 8 at instruction ${this.ip - 1}`);

      case 9: // memory
        if (gapArg === 0) {
          const addr = this.pop();
          this.stack.push(this.memory.get(addr) ?? 0);
          return;
        }
        if (gapArg === 1) {
          const addr = this.pop();
          const val = this.pop();
          this.memory.set(addr, val);
          return;
        }
        throw new Error(`illegal gap_arg ${gapArg} for arity 9 at instruction ${this.ip - 1}`);

      case 10: // HALT
        this.status = "halted";
        return;

      case 11: { // CALL
        const target = gapArg;
        if (target >= progLen) {
          throw new Error(`CALL target ${target} out of bounds (program length ${progLen})`);
        }
        this.stack.push(this.ip); // return address (already advanced)
        this.ip = target;
        return;
      }

      case 12: { // RET
        const retAddr = this.pop();
        if (retAddr < 0 || retAddr > progLen) {
          throw new Error(`RET target ${retAddr} out of bounds (program length ${progLen})`);
        }
        this.ip = retAddr;
        return;
      }

      case 13: // PUSHN n → push -n
        this.stack.push(-gapArg);
        return;

      case 14: { // PICK n
        const depth = this.stack.length;
        if (gapArg >= depth) {
          throw new Error(`PICK ${gapArg}: stack underflow (depth=${depth})`);
        }
        this.stack.push(this.stack[depth - 1 - gapArg]);
        return;
      }

      default:
        throw new Error(
          `illegal instruction arity ${arity} at instruction ${this.ip - 1} ` +
          `(arities 15+ are reserved)`,
        );
    }
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function toByteArray(input: string | number[] | Uint8Array): number[] {
  if (typeof input === "string") {
    const bytes = new TextEncoder().encode(input);
    return Array.from(bytes);
  }
  if (input instanceof Uint8Array) return Array.from(input);
  return [...input];
}
