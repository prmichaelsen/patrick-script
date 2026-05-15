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
  PatrickScript v1.3.0 — a Turing-complete stack-based language with exactly
  two lexical tokens: the word `patrick` and a single space. Word arity (count
  of consecutive `patrick` tokens) selects the opcode family; gap width (count
  of consecutive spaces) encodes the immediate argument. The machine has a value
  stack, integer-addressed memory, byte-width I/O, subroutine support via
  CALL/RET (v1.1.0), single-instruction negative literal PUSHN (v1.2.0), and
  stack copy PICK (v1.3.0). Designed and owned by the patrick-script-worker track.
  Also: PatrickScript, two-token language, unary encoding, opcode-by-count,
  gap-encodes-arg, stack machine, esolang, Turing complete, reference spec,
  v1.3.0, CALL, RET, subroutines, PUSHN, negative literal, PICK, stack copy.
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

**Version**: 1.3.0
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

| Token | Representation           | Unicode       |
| ----- | ------------------------ | ------------- |
| WORD  | The string `patrick`     | 7 ASCII bytes |
| SP    | A single space character | U+0020        |

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

| Arity | gap_arg | Mnemonic | Stack effect  | Description                       |
| ----- | ------- | -------- | ------------- | --------------------------------- |
| 1     | n       | PUSH     | → n           | Push the integer n onto the stack |
| 2     | 0       | POP      | a →           | Discard the top of the stack      |
| 2     | 1       | DUP      | a → a a       | Duplicate the top of the stack    |
| 2     | 2       | SWAP     | a b → b a     | Swap the top two elements         |
| 2     | 3       | ROT      | a b c → b c a | Rotate: move third element to top |

### 5.2 Arithmetic

All arithmetic pops two values unless noted. The operand order is: pop b
(top), pop a (below), compute and push result.

| Arity | gap_arg | Mnemonic | Stack effect  | Description                           |
| ----- | ------- | -------- | ------------- | ------------------------------------- |
| 3     | 0       | ADD      | a b → a+b     | Integer addition                      |
| 3     | 1       | SUB      | a b → a-b     | Integer subtraction (a minus b)       |
| 3     | 2       | MUL      | a b → a*b     | Integer multiplication                |
| 3     | 3       | DIV      | a b → a÷b     | Integer division (floor), b divides a |
| 3     | 4       | MOD      | a b → a mod b | Integer remainder (sign follows a)    |
| 3     | 5       | NEG      | a → -a        | Negate (unary; pops one, not two)     |

**Negative integer literals**: PUSH encodes its argument as `gap_arg`,
which is always ≥ 0. There is no literal syntax for negative integers.
To push −n, push n then negate: `PUSH n` followed by `NEG`. The result
is −n on the stack. The assembler supports this directly via two lines.

**Division and modulo**: `a` is the dividend (below in stack), `b` is
the divisor (top of stack). `DIV` computes `floor(a / b)`. `MOD`
computes `a - b * floor(a / b)`. Division by zero is a runtime error.

### 5.3 Comparison

| Arity | gap_arg | Mnemonic | Stack effect | Description                    |
| ----- | ------- | -------- | ------------ | ------------------------------ |
| 4     | 0       | EQ       | a b → (a==b) | 1 if equal, 0 otherwise        |
| 4     | 1       | LT       | a b → (a<b)  | 1 if a < b, 0 otherwise        |
| 4     | 2       | GT       | a b → (a>b)  | 1 if a > b, 0 otherwise        |
| 4     | 3       | AND      | a b → a&b    | Bitwise AND                    |
| 4     | 4       | OR       | a b → a\|b   | Bitwise OR                     |
| 4     | 5       | XOR      | a b → a^b    | Bitwise XOR                    |
| 4     | 6       | NOT      | a → ~a       | Bitwise NOT (ones' complement) |

Comparison operand order: pop b (top), pop a (below), push result.

### 5.4 Control Flow

| Arity | gap_arg | Mnemonic | Stack effect | Description                   |
| ----- | ------- | -------- | ------------ | ----------------------------- |
| 5     | n       | JUMP     | —            | Set IP to n (unconditional)   |
| 6     | n       | JUMPZ    | a →          | Pop a; if a == 0, set IP to n |
| 7     | n       | JUMPNZ   | a →          | Pop a; if a != 0, set IP to n |

JUMP and JUMPZ set the IP to the instruction at 0-based index n. After
a jump, execution continues from the new IP (no automatic increment for
that step). If n is out of bounds, it is a runtime error.

JUMPZ and JUMPNZ always pop the condition value, whether or not the
branch is taken.

### 5.5 Input / Output

| Arity | gap_arg | Mnemonic | Stack effect | Description                                                                                              |
| ----- | ------- | -------- | ------------ | -------------------------------------------------------------------------------------------------------- |
| 8     | 0       | INCHAR   | → c          | Read one byte from stdin; push its value (0–255). Push -1 on EOF.                                        |
| 8     | 1       | OUTCHAR  | c →          | Pop c; write `c mod 256` as one byte to stdout                                                           |
| 8     | 2       | INNUM    | → n          | Read one decimal integer from stdin (leading whitespace ignored); push n. Push -1 on EOF or parse error. |
| 8     | 3       | OUTNUM   | n →          | Pop n; write the decimal representation of n to stdout, followed by a newline                            |

### 5.6 Memory

| Arity | gap_arg | Mnemonic | Stack effect | Description                          |
| ----- | ------- | -------- | ------------ | ------------------------------------ |
| 9     | 0       | LOAD     | addr → val   | Pop addr; push M[addr]               |
| 9     | 1       | STORE    | val addr →   | Pop addr; pop val; set M[addr] = val |

### 5.7 Halt

| Arity | gap_arg | Mnemonic | Stack effect | Description                            |
| ----- | ------- | -------- | ------------ | -------------------------------------- |
| 10    | any     | HALT     | —            | Terminate the program with exit code 0 |

### 5.8 Subroutines (v1.1.0)

| Arity | gap_arg | Mnemonic | Stack effect     | Description                            |
| ----- | ------- | -------- | ---------------- | -------------------------------------- |
| 11    | n       | CALL     | → ret            | Push (IP+1); jump to instruction n     |
| 12    | any     | RET      | ret →            | Pop ret; jump to instruction ret       |

**CALL n** saves the return address (the index of the instruction
immediately following CALL) by pushing it onto the value stack, then
sets IP to n. Execution continues from instruction n.

**RET** pops the top of the value stack as a return address and sets IP
to it. If the stack is empty when RET executes, it is a stack underflow
error. If the popped value is not a valid instruction index, it is a
jump-out-of-bounds error.

The gap_arg of CALL is the jump target (like JUMP). The gap_arg of RET
is ignored (like HALT).

Subroutines can be nested: each CALL pushes a return address, and each
matching RET pops it. Recursive calls are legal but may exhaust stack
space in practice.

### 5.9 Negative Push (v1.2.0)

| Arity | gap_arg | Mnemonic | Stack effect | Description                            |
| ----- | ------- | -------- | ------------ | -------------------------------------- |
| 13    | n       | PUSHN    | → -n         | Push the integer −n onto the stack     |

**PUSHN n** pushes the negation of its immediate argument. The argument
n is encoded as gap_arg (≥ 0), so the pushed value is −n (≤ 0). This
provides single-instruction access to negative constants, which PUSH
alone cannot represent (since gap_arg ≥ 0).

Examples: `PUSHN 5` pushes −5. `PUSHN 0` pushes 0 (same as `PUSH 0`).

The two-instruction idiom `PUSH n / NEG` remains valid and equivalent.
PUSHN is a convenience instruction, not a new capability.

### 5.10 Stack Copy (v1.3.0)

| Arity | gap_arg | Mnemonic | Stack effect                  | Description                             |
| ----- | ------- | -------- | ----------------------------- | --------------------------------------- |
| 14    | n       | PICK     | a[n]..a[1] a[0] → ... a[0] a[n] | Copy the element n positions from top |

**PICK n** copies the element at depth n (0-indexed from the top of the
stack) and pushes it onto the top. The original element is not removed.

- `PICK 0` duplicates the top element (equivalent to DUP).
- `PICK 1` copies the second element from the top.
- `PICK n` where n ≥ stack depth is a stack underflow runtime error.

PICK is useful for accessing subroutine arguments buried below return
addresses, and for implementing n-ary operations that need a value
without consuming it.

Examples:
- Stack `[1 2 3]` (3 on top): `PICK 0` → `[1 2 3 3]`
- Stack `[1 2 3]`: `PICK 2` → `[1 2 3 1]`

### 5.11 Reserved and Illegal Instructions

Arities 15 and above are reserved for future versions. An instruction
with arity ≥ 15 is a runtime error in v1.3.0.

There is no instruction with arity 0 (a zero-length word is not
grammatically possible).

---

## 6. Error Conditions

The following conditions are runtime errors. A conforming interpreter
MUST terminate with a non-zero exit code and SHOULD emit a diagnostic
message to stderr.

| Condition                  | Example                                         |
| -------------------------- | ----------------------------------------------- |
| Stack underflow            | POP on empty stack; PICK n where n ≥ depth      |
| Division by zero           | DIV or MOD with 0 on top                        |
| Jump out of bounds         | JUMP n where n ≥ program length                 |
| Illegal instruction        | word arity ≥ 15                                 |
| Illegal gap_arg for opcode | gap_arg outside defined range for a given arity |

For arity 2, gap_arg values 4 and above are illegal.
For arity 3, gap_arg values 6 and above are illegal.
For arity 4, gap_arg values 7 and above are illegal.
For arities 5, 6, 7, any gap_arg is legal (it is the target or unused).
For arity 8, gap_arg values 4 and above are illegal.
For arity 9, gap_arg values 2 and above are illegal.
For arity 10 (HALT), all gap_arg values are legal.
For arity 11 (CALL), any gap_arg is legal (it is the target address).
For arity 12 (RET), all gap_arg values are legal (the gap_arg is ignored).
For arity 13 (PUSHN), any gap_arg is legal (it is the value to negate).
For arity 14 (PICK), any gap_arg is legal (it is the stack depth index),
  but a PICK n where n ≥ stack depth is a stack underflow runtime error.

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
| ----------- | ----- | ------- | ----------------------------- |
| PUSH 0      | 1     | 0       | `p·`                          |
| PUSH 5      | 1     | 5       | `p······`                     |
| POP         | 2     | 0       | `pp·`                         |
| DUP         | 2     | 1       | `pp··`                        |
| SWAP        | 2     | 2       | `pp···`                       |
| ADD         | 3     | 0       | `ppp·`                        |
| SUB         | 3     | 1       | `ppp··`                       |
| EQ          | 4     | 0       | `pppp·`                       |
| JUMP 0      | 5     | 0       | `ppppp·`                      |
| JUMPZ 3     | 6     | 3       | `pppppp····`                  |
| INCHAR      | 8     | 0       | `pppppppp·`                   |
| OUTCHAR     | 8     | 1       | `pppppppp··`                  |
| LOAD        | 9     | 0       | `ppppppppp·`                  |
| HALT        | 10    | 0       | `pppppppppp`                  |
| CALL 3      | 11    | 3       | `ppppppppppp····`             |
| RET         | 12    | 0       | `pppppppppppp·`               |
| PUSHN 5     | 13    | 5       | `ppppppppppppp······`         |
| PICK 2      | 14    | 2       | `pppppppppppppp···`           |

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

### 9.4 FizzBuzz (1 to 15)

The canonical Turing-completeness demonstration. Uses memory (STORE/LOAD) to
hold the loop counter and a printed-flag, MOD for divisibility tests,
JUMPZ/JUMPNZ for branching, OUTCHAR for string output, and OUTNUM for
integer output. The source `examples/fizzbuzz.psa` is 70 instructions; the
compiled `.ps` form is 3,361 bytes.

**Design sketch** (register map: mem[0] = n, mem[1] = printed_flag):

```
; --- Init ---
PUSH 1; PUSH 0; STORE        ;; mem[0] = 1

main_loop:
  PUSH 0; LOAD               ;; n
  PUSH 15; GT; JUMPNZ done   ;; n > 15 → halt

  PUSH 0; PUSH 1; STORE      ;; printed_flag = 0

  ; Fizz check
  PUSH 0; LOAD; PUSH 3; MOD
  JUMPNZ check_buzz          ;; n%3 != 0 → skip
  OUTCHAR 'F','i','z','z'
  PUSH 1; PUSH 1; STORE      ;; printed_flag = 1

check_buzz:
  PUSH 0; LOAD; PUSH 5; MOD
  JUMPNZ check_num           ;; n%5 != 0 → skip
  OUTCHAR 'B','u','z','z'
  PUSH 1; PUSH 1; STORE      ;; printed_flag = 1

check_num:
  PUSH 1; LOAD; JUMPNZ print_nl ;; printed_flag != 0 → newline only
  PUSH 0; LOAD; OUTNUM           ;; otherwise print n (OUTNUM adds \n)
  JUMP next_iter

print_nl:
  PUSH 10; OUTCHAR           ;; '\n'

next_iter:
  PUSH 0; LOAD; PUSH 1; ADD
  PUSH 0; STORE              ;; n = n + 1
  JUMP main_loop

done:
  HALT
```

Output for 1..15:
```
1
2
Fizz
4
Buzz
Fizz
7
8
Fizz
Buzz
11
Fizz
13
14
FizzBuzz
```

### 9.5 Factorial (n!) — iterative



Computes n! for an integer read from stdin. Uses STORE/LOAD for an
accumulator register, MUL for iteration. The source `corpus/factorial.psa`
computes 5! = 120.

**Design sketch** (register map: mem[0] = accumulator):

```
PUSH 1; PUSH 0; STORE    ;; mem[0] = 1 (acc)
INNUM                    ;; read n
loop:
  DUP; JUMPZ done        ;; n == 0 → done
  DUP
  PUSH 0; LOAD           ;; acc
  MUL
  PUSH 0; STORE          ;; acc = acc * n
  PUSH 1; SUB            ;; n = n - 1
  JUMP loop
done:
  POP
  PUSH 0; LOAD; OUTNUM   ;; print acc
  HALT
```

### 9.6 Subroutine Calling Convention

CALL pushes the return address on top of the value stack before jumping.
This means on subroutine entry, the return address sits above any
arguments the caller pushed — the opposite of most conventional calling
conventions where the return address is at a known frame offset.

The idiomatic pattern is **SWAP to expose arguments, SWAP back to
restore**. For a single-argument subroutine:

```
; Caller:
PUSH arg
CALL sub           ;; stack on entry to sub: [..., arg, ret_addr]

; Subroutine body:
sub:
  SWAP             ;; [..., ret_addr, arg]   — expose argument
  < ... work on arg ... >
  SWAP             ;; [..., result, ret_addr] — restore call frame
  RET              ;; returns; result is now on top for caller
```

For zero-argument subroutines (output-only, side-effect routines), the
return address is already on top and no SWAP is needed:

```
; Caller:
CALL print_greeting

; Subroutine:
print_greeting:
  PUSH 72; OUTCHAR   ;; 'H'
  PUSH 105; OUTCHAR  ;; 'i'
  PUSH 10; OUTCHAR   ;; '\n'
  RET
```

For multi-argument subroutines, the convention extends via multiple
SWAPs or ROT:

```
; Two-argument sub (a, b → result):
; Caller pushes a then b, then CALL.
; Entry stack: [..., a, b, ret_addr]

sub2:
  ROT              ;; [..., b, ret_addr, a]  — surface first arg
  SWAP             ;; [..., b, a, ret_addr]  — expose both args below ret
  < ... work on a and b ... >   ;; stack: [..., result, ret_addr]
  RET
```

**Recursive subroutines** work naturally: each CALL pushes a new return
address above the current frame's values. The recursive factorial in
`corpus/factorial-recursive.psa` demonstrates this pattern — each
recursive level pushes its `n` and then CALL pushes the return address;
SWAP is used at subroutine entry to reorder them for computation.

**Key invariant**: at each RET, the return address must be on top of the
stack with the result(s) below it. Violations (wrong stack depth, wrong
top-of-stack) cause jump-out-of-bounds or return to a garbage address.
The assembler's label system makes CALL targets readable, but the stack
discipline at RET is the programmer's responsibility.

### 9.7 Zero-Argument Subroutine Reuse

A zero-argument subroutine is the simplest reusable unit: no arguments
to SWAP around, no result to thread through the stack frame. Because the
return address arrives on top, the subroutine executes, then RETs
without any frame-management overhead.

```
print_hello:
  .string "Hi\n"   ;; output-only side effect
  RET               ;; return address already on top
```

The same subroutine can be called any number of times:

```
CALL print_hello   ;; first call
CALL print_hello   ;; second call — same body, new return address
HALT
```

Each CALL pushes a fresh return address, so independent invocations
share the body code but maintain separate return continuations. There
is no state to reset between calls; zero-argument subroutines are
naturally reentrant in a single-threaded sequential program.

This pattern suits output routines, print helpers, and repeated
fixed-work blocks. The `corpus/call-string.psa` test demonstrates
it: `.string "Hi\n"` + `RET`, called twice.

---

## 10. Versioning

### v1.0.0 (2026-05-15)

Initial release. Stack machine with 10 arities: PUSH (1), stack ops (2),
arithmetic (3), comparison/bitwise (4), JUMP/JUMPZ/JUMPNZ (5–7), I/O
(8), memory (9), HALT (10). Arities 11+ reserved.

### v1.1.0 (2026-05-15)

Adds subroutine support: CALL (arity 11) and RET (arity 12). Arities 13+
remain reserved. A v1.1.0-conformant interpreter executes CALL and RET
as specified in section 5.8; it treats arities ≥ 13 as runtime errors.
A v1.0.0-only interpreter that encounters arity 11 or 12 is permitted to
treat them as runtime errors (reserved instruction).

### v1.2.0 (2026-05-15)

Adds PUSHN (arity 13, gap_arg = n): pushes −n onto the stack. Provides
single-instruction negative literal encoding. The two-instruction idiom
`PUSH n / NEG` remains valid and equivalent; PUSHN is a convenience
instruction. A v1.2.0-conformant interpreter executes PUSHN as specified
in section 5.9; it treats arities ≥ 14 as runtime errors.

Arities 14+ remain reserved in v1.2.0.

### v1.3.0 (2026-05-15)

Adds PICK (arity 14, gap_arg = n): copies the element at depth n from
the top of the stack (0 = top). Provides direct access to buried stack
values without destructive reordering. A v1.3.0-conformant interpreter
executes PICK as specified in section 5.10; it treats arities ≥ 15 as
runtime errors. A v1.2.0-only interpreter that encounters arity 14 is
permitted to treat it as a runtime error.

Arities 15+ remain reserved.

Future versions add instructions via currently-reserved arities (15+) or
extend the gap_arg space for existing arities.

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
