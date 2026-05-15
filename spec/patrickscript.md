<!-- @scry.entry
id: spec.patrickscript~3f9d99a8
kind: spec
status: active
weight: 1.0
tags:
  - "scope:language"
  - "topic:patrickscript"
  - "topic:spec"
  - "topic:esolang"
  - "patrickscript"
  - "spec"
  - "stack-machine"
  - "unary-encoding"
  - "turing-complete"
summary: >
  PatrickScript v1.0.0 — a Turing-complete stack-based language with exactly
  two lexical tokens: the word `patrick` and a single space. Word arity (count
  of consecutive `patrick` tokens) selects the opcode family; gap width (count
  of consecutive spaces) encodes the immediate argument. The machine has a value
  stack, integer-addressed memory, and byte-width I/O. Designed and owned by the
  patrick-script-worker track. Also: PatrickScript, two-token language, unary
  encoding, opcode-by-count, gap-encodes-arg, stack machine, esolang, Turing
  complete, reference spec, v1.0.0.
rationale: >
  Without this spec, no implementation is correct by definition. Every design
  decision about PatrickScript lives here. An implementation written without
  reading this will diverge; a future wake designing a second implementation
  will have to re-derive semantics from scratch.
applies: >
  implementing a PatrickScript interpreter, writing PatrickScript programs,
  adding new instructions, evaluating Turing completeness, building a conformance
  corpus, evaluating the language design
seeded_questions:
  - "What are the two tokens in PatrickScript?"
  - "How does PatrickScript encode instructions?"
  - "What is the PatrickScript instruction set?"
  - "Is PatrickScript Turing complete?"
  - "How does PatrickScript handle I/O?"
  - "PatrickScript memory model"
  - "PatrickScript stack machine semantics"
  - "How to write a PatrickScript program"
  - "PatrickScript grammar word gap arity"
@scry.entry.end -->

# PatrickScript Language Specification

**Version**: 1.0.0
**Status**: active
**Authored by**: patrick-script-worker track, 2026-05-15

---

## 1. Overview

PatrickScript is a Turing-complete, stack-based programming language whose
entire design — computational model, grammar, semantics, tooling — was
authored by an LLM. The only human-fixed inputs are:

- **The name**: PatrickScript
- **The two lexical tokens**: `patrick` (the literal string) and ` ` (a
  single space, U+0020)

Every other property of the language is a decision made by the
`patrick-script-worker` track. No design question is deferred to the
originator.

PatrickScript programs are sequences of these two tokens. Structure is
encoded in the *count* of consecutive identical tokens: how many
`patrick`s in a row, and how many spaces in a row. These counts carry
all meaning.

---

## 2. Lexical Model

A PatrickScript source file is a sequence of bytes drawn exclusively from
two token types:

| Token | Representation | Unicode |
|-------|---------------|---------|
| WORD  | The string `patrick` | 7 ASCII bytes |
| SP    | A single space character | U+0020 |

No other bytes are legal in a PatrickScript source. Specifically:
- Newlines, tabs, carriage returns, and all other whitespace are illegal.
- Any byte sequence other than `patrick` or ` ` is illegal.
- An empty file (zero bytes) is a valid program (it halts immediately).

### 2.1 Tokens vs. Characters

The unit of tokenization is not the character but the token as defined
above. The string `patrick` is a single WORD token, not seven character
tokens. The string `patrick` is illegal (not a WORD token and not a SP
token).

---

## 3. Syntactic Structure

Tokens are organized into two syntactic constructs:

**Word**: a maximal contiguous run of WORD tokens. The **arity** of a
word is its length in WORD tokens.

**Gap**: a maximal contiguous run of SP tokens. The **width** of a gap
is its length in SP tokens.

A PatrickScript program is a sequence of zero or more **instructions**.
Each instruction is a (word, gap) pair: a word followed by a gap. The
final instruction in a program may omit its trailing gap; when it does,
the gap is treated as having width 1.

### Formal Grammar

```
program     ::= instruction* trailing?
instruction ::= word gap
trailing    ::= word
word        ::= 'patrick'+
gap         ::= ' '+
```

Since words and gaps are each maximal runs of their respective token,
they alternate strictly: no two words are adjacent (they would fuse into
one word), and no two gaps are adjacent (they would fuse into one gap).

### 3.1 Instruction Encoding

Each instruction encodes:

- **Opcode**: selected by (word_arity, gap_arg) together, where
  `gap_arg = gap_width - 1`. The gap always has width ≥ 1 (by grammar),
  so `gap_arg ≥ 0`. For a trailing word with no gap, `gap_arg = 0`.
- **Argument**: the `gap_arg` value doubles as the numeric immediate
  argument for instructions that take one (e.g., PUSH, JUMP).

---

## 4. Machine Model

A PatrickScript machine has the following state:

- **Value stack** (S): a LIFO stack of arbitrary integers (positive,
  negative, or zero). Initially empty.
- **Memory** (M): a map from integer addresses to integer values.
  `M[addr]` is 0 for any address not yet written. The address space is
  unbounded in both directions.
- **Instruction pointer** (IP): a zero-based index into the instruction
  sequence. Starts at 0.
- **Program**: the compiled list of (arity, gap_arg) pairs, indexed
  0..N-1.
- **I/O**: standard input and standard output, byte-oriented.

Execution proceeds by fetching the instruction at IP, executing it,
advancing IP, and repeating until HALT or an error condition.

---

## 5. Instruction Set

### Notation

Stack effects use the convention `before → after`, where items are
listed left-to-right with the top of stack at the right. For example,
`a b → a+b` means: before execution, b is on top with a below it;
after execution, their sum is on top.

`n` denotes the `gap_arg` value of the current instruction (the
immediate integer argument).

### 5.1 Stack Manipulation

| Arity | gap_arg | Mnemonic | Stack effect | Description |
|-------|---------|----------|-------------|-------------|
| 1 | n | PUSH | → n | Push the integer n onto the stack |
| 2 | 0 | POP | a → | Discard the top of the stack |
| 2 | 1 | DUP | a → a a | Duplicate the top of the stack |
| 2 | 2 | SWAP | a b → b a | Swap the top two elements |
| 2 | 3 | ROT | a b c → b c a | Rotate: move third element to top |

### 5.2 Arithmetic

All arithmetic pops two values unless noted. The operand order is: pop b
(top), pop a (below), compute and push result.

| Arity | gap_arg | Mnemonic | Stack effect | Description |
|-------|---------|----------|-------------|-------------|
| 3 | 0 | ADD | a b → a+b | Integer addition |
| 3 | 1 | SUB | a b → a-b | Integer subtraction (a minus b) |
| 3 | 2 | MUL | a b → a*b | Integer multiplication |
| 3 | 3 | DIV | a b → a÷b | Integer division (floor), b divides a |
| 3 | 4 | MOD | a b → a mod b | Integer remainder (sign follows a) |
| 3 | 5 | NEG | a → -a | Negate (unary; pops one, not two) |

**Division and modulo**: `a` is the dividend (below in stack), `b` is
the divisor (top of stack). `DIV` computes `floor(a / b)`. `MOD`
computes `a - b * floor(a / b)`. Division by zero is a runtime error.

### 5.3 Comparison

| Arity | gap_arg | Mnemonic | Stack effect | Description |
|-------|---------|----------|-------------|-------------|
| 4 | 0 | EQ | a b → (a==b) | 1 if equal, 0 otherwise |
| 4 | 1 | LT | a b → (a<b) | 1 if a < b, 0 otherwise |
| 4 | 2 | GT | a b → (a>b) | 1 if a > b, 0 otherwise |
| 4 | 3 | AND | a b → a&b | Bitwise AND |
| 4 | 4 | OR | a b → a\|b | Bitwise OR |
| 4 | 5 | XOR | a b → a^b | Bitwise XOR |
| 4 | 6 | NOT | a → ~a | Bitwise NOT (ones' complement) |

Comparison operand order: pop b (top), pop a (below), push result.

### 5.4 Control Flow

| Arity | gap_arg | Mnemonic | Stack effect | Description |
|-------|---------|----------|-------------|-------------|
| 5 | n | JUMP | — | Set IP to n (unconditional) |
| 6 | n | JUMPZ | a → | Pop a; if a == 0, set IP to n |
| 7 | n | JUMPNZ | a → | Pop a; if a != 0, set IP to n |

JUMP and JUMPZ set the IP to the instruction at 0-based index n. After
a jump, execution continues from the new IP (no automatic increment for
that step). If n is out of bounds, it is a runtime error.

JUMPZ and JUMPNZ always pop the condition value, whether or not the
branch is taken.

### 5.5 Input / Output

| Arity | gap_arg | Mnemonic | Stack effect | Description |
|-------|---------|----------|-------------|-------------|
| 8 | 0 | INCHAR | → c | Read one byte from stdin; push its value (0–255). Push -1 on EOF. |
| 8 | 1 | OUTCHAR | c → | Pop c; write `c mod 256` as one byte to stdout |
| 8 | 2 | INNUM | → n | Read one decimal integer from stdin (leading whitespace ignored); push n. Push -1 on EOF or parse error. |
| 8 | 3 | OUTNUM | n → | Pop n; write the decimal representation of n to stdout, followed by a newline |

### 5.6 Memory

| Arity | gap_arg | Mnemonic | Stack effect | Description |
|-------|---------|----------|-------------|-------------|
| 9 | 0 | LOAD | addr → val | Pop addr; push M[addr] |
| 9 | 1 | STORE | val addr → | Pop addr; pop val; set M[addr] = val |

### 5.7 Halt

| Arity | gap_arg | Mnemonic | Stack effect | Description |
|-------|---------|----------|-------------|-------------|
| 10 | any | HALT | — | Terminate the program with exit code 0 |

### 5.8 Reserved and Illegal Instructions

Arities 11 and above are reserved for future versions. An instruction
with arity ≥ 11 is a runtime error in v1.0.0.

There is no instruction with arity 0 (a zero-length word is not
grammatically possible).

---

## 6. Error Conditions

The following conditions are runtime errors. A conforming interpreter
MUST terminate with a non-zero exit code and SHOULD emit a diagnostic
message to stderr.

| Condition | Example |
|-----------|---------|
| Stack underflow | POP on empty stack |
| Division by zero | DIV or MOD with 0 on top |
| Jump out of bounds | JUMP n where n ≥ program length |
| Illegal instruction | word arity ≥ 11 |
| Illegal gap_arg for opcode | gap_arg outside defined range for a given arity |

For arity 2, gap_arg values 4 and above are illegal.
For arity 3, gap_arg values 6 and above are illegal.
For arity 4, gap_arg values 7 and above are illegal.
For arities 5, 6, 7, any gap_arg is legal (it is the target or unused).
For arity 8, gap_arg values 4 and above are illegal.
For arity 9, gap_arg values 2 and above are illegal.
For arity 10 (HALT), all gap_arg values are legal.

**Lexical errors** (illegal characters in source) are parse-time errors
and MUST cause the interpreter to exit with a non-zero exit code before
any execution.

---

## 7. Encoding Reference

An instruction is written as:

```
('patrick' × arity) (' ' × (gap_arg + 1))
```

except the last instruction in a program, which may omit trailing spaces
(treated as gap_arg = 0).

### 7.1 Encoding Examples

Within a word, `patrick` tokens are concatenated with no separating characters.
A word of arity n is the string `patrick` repeated n times. The gap follows
immediately after the last `patrick` of the word.

Below, `p` stands for `patrick` (7 characters) and `·` for a space:

| Instruction | Arity | gap_arg | Source (p=`patrick`, ·=space) |
|-------------|-------|---------|-------------------------------|
| PUSH 0 | 1 | 0 | `p·` |
| PUSH 5 | 1 | 5 | `p······` |
| POP | 2 | 0 | `pp·` |
| DUP | 2 | 1 | `pp··` |
| SWAP | 2 | 2 | `pp···` |
| ADD | 3 | 0 | `ppp·` |
| SUB | 3 | 1 | `ppp··` |
| EQ | 4 | 0 | `pppp·` |
| JUMP 0 | 5 | 0 | `ppppp·` |
| JUMPZ 3 | 6 | 3 | `pppppp····` |
| INCHAR | 8 | 0 | `pppppppp·` |
| OUTCHAR | 8 | 1 | `pppppppp··` |
| LOAD | 9 | 0 | `ppppppppp·` |
| HALT | 10 | 0 | `pppppppppp` |

A concrete example: OUTCHAR followed by HALT is the byte sequence
`patrickpatrickpatrickpatrickpatrickpatrickpatrickpatrick  patrickpatrickpatrickpatrickpatrickpatrickpatrickpatrickpatrickpatrick`
(8 patricks, 2 spaces, 10 patricks).

---

## 8. Turing Completeness

PatrickScript is Turing complete. A proof sketch:

PatrickScript can simulate a Turing machine by using its integer memory
as the TM tape (negative and positive addresses give a bidirectional
infinite tape), the stack to hold the tape head position and current
state, and the control flow instructions (JUMP, JUMPZ, JUMPNZ) to
implement state transitions.

More directly: PatrickScript has:
- **Unbounded memory** (LOAD/STORE on integer addresses)
- **Arbitrary integer arithmetic** (ADD, SUB, MUL, etc.)
- **Conditional branching** (JUMPZ, JUMPNZ)
- **Loops** (JUMP backwards creates loops, JUMPZ exits them)

This is sufficient to compute any computable function. PatrickScript can
simulate a Brainfuck interpreter, and Brainfuck is known Turing complete.

---

## 9. Program Examples

### 9.1 Hello World (first character)

Output ASCII 72 ('H') and halt. Using `p` for `patrick` and `·` for space:

```
p········································································pppppppp··pppppppppp
```

Decoded:
- `PUSH 71` — arity=1, gap_arg=71: `p` followed by 72 spaces
- `OUTCHAR` — arity=8, gap_arg=1: `pppppppp` followed by 2 spaces
- `HALT` — arity=10, gap_arg=0: `pppppppppp` with no trailing spaces

Note: PUSH 71 requires 72 spaces after one `patrick` token. PatrickScript
programs for non-trivial ASCII output are verbose by design. This is
intentional: the verbosity is a property of the encoding, not an
implementation choice.

### 9.2 Infinite counter

Print 0, 1, 2, ... indefinitely:

```
Instruction 0: PUSH 0        (arity=1, gap_arg=0) — push initial value
Instruction 1: DUP           (arity=2, gap_arg=1) — duplicate for print
Instruction 2: OUTNUM        (arity=8, gap_arg=3) — print number
Instruction 3: PUSH 1        (arity=1, gap_arg=1) — push increment
Instruction 4: ADD           (arity=3, gap_arg=0) — counter + 1
Instruction 5: JUMP 1        (arity=5, gap_arg=1) — loop back to DUP
```

### 9.3 Echo (copy stdin to stdout)

Read characters until EOF, writing each:

```
Instruction 0: INCHAR        (arity=8, gap_arg=0) — read byte or -1
Instruction 1: DUP           (arity=2, gap_arg=1) — dup to check for EOF
Instruction 2: PUSH 1        (arity=1, gap_arg=1) — push 1
Instruction 3: ADD           (arity=3, gap_arg=0) — eof+1; 0 if was -1
Instruction 4: JUMPZ 7       (arity=6, gap_arg=7) — if EOF, jump to HALT
Instruction 5: OUTCHAR       (arity=8, gap_arg=1) — write byte
Instruction 6: JUMP 0        (arity=5, gap_arg=0) — loop
Instruction 7: POP           (arity=2, gap_arg=0) — discard sentinel -1
Instruction 8: HALT          (arity=10, gap_arg=0) — done
```

---

## 10. Versioning

This specification is v1.0.0. Future versions add instructions via
currently-reserved arities (11+) or extend the gap_arg space for
existing arities. A v1.0.0-conformant interpreter MUST treat reserved
arities as runtime errors.

Version is declared in the spec document title, not in the source
language (PatrickScript has no pragma syntax).

---

## 11. Formal Summary

- **Tokens**: WORD (`patrick`) and SP (U+0020)
- **Words**: maximal WORD runs; arity = count
- **Gaps**: maximal SP runs; width ≥ 1; gap_arg = width - 1
- **Instructions**: (word, gap) pairs; last gap optional (treated as width 1)
- **Machine**: stack + memory + IP + I/O
- **Completeness**: Turing complete
- **Designed by**: patrick-script-worker (LLM), 2026-05-15
- **Fixed by originator**: name PatrickScript; tokens `patrick` and ` `
