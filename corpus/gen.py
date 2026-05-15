#!/usr/bin/env python3
# <!-- @scry.entry
# id: code.patrickscript-corpus-gen~c776ef9c
# kind: code
# status: active
# weight: 0.7
# tags:
#   - "topic:patrickscript"
#   - "topic:corpus"
#   - "patrickscript"
#   - "corpus"
#   - "test-generator"
#   - "gen.py"
# summary: >
#   PatrickScript corpus test generator. Encodes (arity, gap_arg) instruction
#   tuples into .ps source; writes .ps, .stdin, .expected, .desc for each test.
#   Covers: jump, jumpz, jumpnz, countdown loop, innum, outchar, inchar,
#   load-store, div-by-zero, stack-underflow, factorial. Also: gen.py,
#   corpus generator, PatrickScript test suite, ps_encode.
# rationale: >
#   Without this, the encoding logic for new corpus tests must be computed by
#   hand. A bug in the encoding (e.g. trailing newline) will silently produce
#   parse errors. This script is the authoritative generator for new tests.
# applies: >
#   adding new PatrickScript corpus tests, regenerating .ps files from
#   instruction lists, debugging corpus test failures
# seeded_questions:
#   - "How are PatrickScript corpus tests generated?"
#   - "PatrickScript corpus generator"
#   - "gen.py corpus test"
#   - "How do I add a new PatrickScript test?"
# @scry.entry.end -->
"""
Generate PatrickScript corpus test files from instruction lists.
Run from project root: python3 corpus/gen.py
"""
import os

CORPUS = os.path.dirname(os.path.abspath(__file__))


def ps_encode(instructions):
    """
    Encode a list of (arity, gap_arg) tuples into PatrickScript source.
    The last instruction has no trailing spaces.
    """
    parts = []
    for i, (arity, gap_arg) in enumerate(instructions):
        word = "patrick" * arity
        is_last = (i == len(instructions) - 1)
        if is_last:
            parts.append(word)
        else:
            parts.append(word + " " * (gap_arg + 1))
    return "".join(parts)


def write_test(name, instructions, stdin_content="", expected_content="", desc=""):
    ps = ps_encode(instructions)
    base = os.path.join(CORPUS, name)
    with open(base + ".ps", "w") as f:
        f.write(ps)
    with open(base + ".stdin", "w") as f:
        f.write(stdin_content)
    with open(base + ".expected", "w") as f:
        f.write(expected_content)
    with open(base + ".desc", "w") as f:
        f.write(desc + "\n")
    print(f"  wrote {name}.{{ps,stdin,expected,desc}}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

# jump: unconditional JUMP skips dead code
# 0: PUSH 42
# 1: JUMP 3       (skip idx 2)
# 2: PUSH 0       (dead — never reached)
# 3: OUTNUM
# 4: HALT
write_test(
    "jump",
    [(1, 42), (5, 3), (1, 0), (8, 3), (10, 0)],
    stdin_content="",
    expected_content="42\n",
    desc="JUMP skips dead PUSH 0; OUTNUM prints 42, HALT",
)

# jumpz: JUMPZ fires when top == 0
# 0: PUSH 0
# 1: JUMPZ 3      (0 == 0 → jump to idx 3)
# 2: PUSH 99      (skipped)
# 3: PUSH 42
# 4: OUTNUM       (prints 42)
# 5: HALT
write_test(
    "jumpz",
    [(1, 0), (6, 3), (1, 99), (1, 42), (8, 3), (10, 0)],
    stdin_content="",
    expected_content="42\n",
    desc="JUMPZ fires when top == 0; skips PUSH 99; prints 42",
)

# jumpnz: JUMPNZ fires when top != 0
# 0: PUSH 5
# 1: JUMPNZ 3     (5 != 0 → jump to idx 3)
# 2: PUSH 0       (skipped)
# 3: PUSH 42
# 4: OUTNUM
# 5: HALT
write_test(
    "jumpnz",
    [(1, 5), (7, 3), (1, 0), (1, 42), (8, 3), (10, 0)],
    stdin_content="",
    expected_content="42\n",
    desc="JUMPNZ fires when top != 0; skips PUSH 0; prints 42",
)

# countdown: loop using JUMPNZ, counts 3 → 2 → 1
# 0:  PUSH 3
# 1:  DUP
# 2:  OUTNUM
# 3:  PUSH 1
# 4:  SUB
# 5:  DUP
# 6:  JUMPNZ 1    (loop back to DUP if counter != 0)
# 7:  POP
# 8:  HALT
write_test(
    "countdown",
    [(1, 3), (2, 1), (8, 3), (1, 1), (3, 1), (2, 1), (7, 1), (2, 0), (10, 0)],
    stdin_content="",
    expected_content="3\n2\n1\n",
    desc="JUMPNZ loop: counts down from 3 to 1 using DUP/SUB; prints 3, 2, 1",
)

# innum: read a number and echo it
# 0: INNUM
# 1: OUTNUM
# 2: HALT
write_test(
    "innum",
    [(8, 2), (8, 3), (10, 0)],
    stdin_content="17\n",
    expected_content="17\n",
    desc="INNUM reads integer from stdin; OUTNUM prints it back → 17",
)

# outchar: push ASCII 72 ('H') and OUTCHAR
# 0: PUSH 72
# 1: OUTCHAR
# 2: HALT
write_test(
    "outchar",
    [(1, 72), (8, 1), (10, 0)],
    stdin_content="",
    expected_content="H",
    desc="PUSH 72 ('H') then OUTCHAR → writes byte 'H' to stdout",
)

# inchar: read one byte and echo it with OUTCHAR
# 0: INCHAR
# 1: OUTCHAR
# 2: HALT
write_test(
    "inchar",
    [(8, 0), (8, 1), (10, 0)],
    stdin_content="A",
    expected_content="A",
    desc="INCHAR reads one byte ('A') from stdin; OUTCHAR writes it back",
)

# load-store: store 42 at address 7, load it, print it
# 0: PUSH 42
# 1: PUSH 7
# 2: STORE
# 3: PUSH 7
# 4: LOAD
# 5: OUTNUM
# 6: HALT
write_test(
    "load-store",
    [(1, 42), (1, 7), (9, 1), (1, 7), (9, 0), (8, 3), (10, 0)],
    stdin_content="",
    expected_content="42\n",
    desc="STORE 42 at mem[7]; LOAD from mem[7]; OUTNUM prints 42",
)

# div-by-zero: PUSH 5, PUSH 0, DIV → runtime error, stdout empty
# 0: PUSH 5
# 1: PUSH 0
# 2: DIV
# 3: OUTNUM      (never reached)
# 4: HALT
write_test(
    "div-by-zero",
    [(1, 5), (1, 0), (3, 3), (8, 3), (10, 0)],
    stdin_content="",
    expected_content="",
    desc="DIV by zero triggers runtime error (exit 1); stdout is empty",
)

# stack-underflow: pop twice from a stack with one element → error on second pop
# 0: PUSH 1
# 1: POP
# 2: POP         (underflow)
# 3: HALT
write_test(
    "stack-underflow",
    [(1, 1), (2, 0), (2, 0), (10, 0)],
    stdin_content="",
    expected_content="",
    desc="Second POP on empty stack triggers runtime error; stdout is empty",
)

# factorial: compute 5! = 120 using a memory-backed accumulator loop
# mem[0] = result (initialized to 1)
# counter on stack
# 0:  PUSH 1
# 1:  PUSH 0
# 2:  STORE          mem[0] = 1
# 3:  PUSH 5         counter = 5
# --- loop (idx 4) ---
# 4:  DUP            copy counter
# 5:  PUSH 0
# 6:  LOAD           push mem[0]
# 7:  MUL            counter * result
# 8:  PUSH 0
# 9:  STORE          mem[0] = new result
# 10: PUSH 1
# 11: SUB            counter - 1
# 12: DUP            copy for test
# 13: JUMPNZ 4       if counter != 0, loop
# 14: POP            drop the 0
# 15: PUSH 0
# 16: LOAD           push mem[0] = 120
# 17: OUTNUM         prints 120
# 18: HALT
write_test(
    "factorial",
    [
        (1, 1), (1, 0), (9, 1),   # 0-2: result=1 in mem[0]
        (1, 5),                    # 3: counter=5
        (2, 1),                    # 4: DUP
        (1, 0), (9, 0),           # 5-6: PUSH 0, LOAD
        (3, 2),                    # 7: MUL
        (1, 0), (9, 1),           # 8-9: PUSH 0, STORE
        (1, 1), (3, 1),           # 10-11: PUSH 1, SUB
        (2, 1), (7, 4),           # 12-13: DUP, JUMPNZ 4
        (2, 0),                    # 14: POP
        (1, 0), (9, 0),           # 15-16: PUSH 0, LOAD
        (8, 3), (10, 0),          # 17-18: OUTNUM, HALT
    ],
    stdin_content="",
    expected_content="120\n",
    desc="5! = 120 via memory-backed accumulator loop; demonstrates STORE/LOAD/MUL/JUMPNZ",
)

print("\nAll corpus files generated.")
