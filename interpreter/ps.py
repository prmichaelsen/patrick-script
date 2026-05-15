#!/usr/bin/env python3
# <!-- @scry.entry
# id: code.patrickscript-interpreter~771620e2
# kind: code
# status: active
# weight: 0.9
# tags:
#   - "topic:patrickscript"
#   - "topic:interpreter"
#   - "patrickscript"
#   - "interpreter"
#   - "stack-machine"
#   - "python"
#   - "reference-implementation"
# summary: >
#   PatrickScript v1.1.0 reference interpreter in Python. Parses word/gap token
#   pairs, executes stack machine semantics: PUSH, POP, DUP, SWAP, ROT, arithmetic
#   (ADD/SUB/MUL/DIV/MOD/NEG), comparison/bitwise (EQ/LT/GT/AND/OR/XOR/NOT),
#   control flow (JUMP/JUMPZ/JUMPNZ/CALL/RET), I/O (INCHAR/OUTCHAR/INNUM/OUTNUM),
#   memory (LOAD/STORE), HALT. Also: ps.py, PatrickScript interpreter, reference
#   implementation, conformance, stack machine, unary encoding, v1.1.0, CALL, RET,
#   subroutines.
# rationale: >
#   Without this file a future wake has no way to test PatrickScript programs.
#   This is the canonical arbiter of language semantics when the spec is ambiguous.
# applies: >
#   running PatrickScript programs, debugging PatrickScript behavior, extending
#   the instruction set, verifying conformance
# seeded_questions:
#   - "How do I run a PatrickScript program?"
#   - "PatrickScript interpreter command line"
#   - "PatrickScript disassemble"
#   - "reference implementation PatrickScript"
# @scry.entry.end -->
"""
PatrickScript v1.1.0 reference interpreter.

Usage:
    python ps.py <program.ps>
    python ps.py --disassemble <program.ps>

Exit codes:
    0  — HALT or empty program
    1  — runtime error (stack underflow, division by zero, etc.)
    2  — parse error (illegal characters in source)
"""

import sys
import math

WORD_TOKEN = "patrick"
WORD_LEN = len(WORD_TOKEN)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse(source: str) -> list[tuple[int, int]]:
    """
    Parse PatrickScript source into a list of (arity, gap_arg) instructions.

    Raises SystemExit(2) on lexical error.
    """
    if not source:
        return []

    instructions = []
    i = 0
    n = len(source)

    while i < n:
        # Expect a WORD run
        if source[i:i + WORD_LEN] != WORD_TOKEN:
            _parse_error(i, source)

        # Count consecutive WORD tokens
        arity = 0
        while i < n and source[i:i + WORD_LEN] == WORD_TOKEN:
            arity += 1
            i += WORD_LEN

        # Count following SP tokens (the gap)
        gap_width = 0
        while i < n and source[i] == " ":
            gap_width += 1
            i += 1

        # Check no illegal characters followed the gap
        # (handled by outer loop: if source[i] is not 'p' of 'patrick',
        #  the next iteration will catch it)
        if i < n and source[i] != "p":
            _parse_error(i, source)

        # gap_arg: 0 if no gap (trailing word), else gap_width - 1
        gap_arg = max(gap_width - 1, 0)
        instructions.append((arity, gap_arg))

    return instructions


def _parse_error(pos: int, source: str) -> None:
    context = source[max(0, pos - 10):pos + 10].replace("\n", "\\n")
    print(
        f"PatrickScript parse error at position {pos}: "
        f"unexpected token near '{context}'",
        file=sys.stderr,
    )
    sys.exit(2)


# ---------------------------------------------------------------------------
# Disassembly
# ---------------------------------------------------------------------------

MNEMONICS = {
    # (arity, gap_arg): (mnemonic, description)
    (1, None): ("PUSH n", "push immediate n"),
    (2, 0): ("POP", "discard top"),
    (2, 1): ("DUP", "duplicate top"),
    (2, 2): ("SWAP", "swap top two"),
    (2, 3): ("ROT", "rotate top three"),
    (3, 0): ("ADD", "a b → a+b"),
    (3, 1): ("SUB", "a b → a-b"),
    (3, 2): ("MUL", "a b → a*b"),
    (3, 3): ("DIV", "a b → floor(a/b)"),
    (3, 4): ("MOD", "a b → a mod b"),
    (3, 5): ("NEG", "a → -a"),
    (4, 0): ("EQ", "a b → (a==b)"),
    (4, 1): ("LT", "a b → (a<b)"),
    (4, 2): ("GT", "a b → (a>b)"),
    (4, 3): ("AND", "a b → a&b"),
    (4, 4): ("OR", "a b → a|b"),
    (4, 5): ("XOR", "a b → a^b"),
    (4, 6): ("NOT", "a → ~a"),
    (5, None): ("JUMP n", "jump to instruction n"),
    (6, None): ("JUMPZ n", "if top==0, jump to n"),
    (7, None): ("JUMPNZ n", "if top!=0, jump to n"),
    (8, 0): ("INCHAR", "read byte → stack"),
    (8, 1): ("OUTCHAR", "pop → write byte"),
    (8, 2): ("INNUM", "read int → stack"),
    (8, 3): ("OUTNUM", "pop → write int+newline"),
    (9, 0): ("LOAD", "pop addr → push mem[addr]"),
    (9, 1): ("STORE", "pop val addr → mem[addr]=val"),
    (10, None): ("HALT", "terminate"),
    (11, None): ("CALL n", "push return addr; jump to n"),
    (12, None): ("RET", "pop return addr; jump there"),
}


def disassemble(instructions: list[tuple[int, int]]) -> None:
    for idx, (arity, gap_arg) in enumerate(instructions):
        key_specific = (arity, gap_arg)
        key_family = (arity, None)
        if key_specific in MNEMONICS:
            mnem, desc = MNEMONICS[key_specific]
        elif key_family in MNEMONICS:
            mnem_tmpl, desc = MNEMONICS[key_family]
            mnem = mnem_tmpl.replace("n", str(gap_arg))
        else:
            mnem = f"???"
            desc = f"arity={arity} gap_arg={gap_arg}"
        print(f"{idx:4d}  {mnem:<16}  ; {desc}")


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

class RuntimeError_(Exception):
    pass


def _runtime_error(msg: str) -> None:
    print(f"PatrickScript runtime error: {msg}", file=sys.stderr)
    sys.exit(1)


def execute(instructions: list[tuple[int, int]]) -> None:
    stack: list[int] = []
    memory: dict[int, int] = {}
    ip = 0
    prog_len = len(instructions)

    def pop() -> int:
        if not stack:
            _runtime_error("stack underflow")
        return stack.pop()

    def peek() -> int:
        if not stack:
            _runtime_error("stack underflow on peek")
        return stack[-1]

    while ip < prog_len:
        arity, gap_arg = instructions[ip]
        ip += 1  # advance before execution (jumps may override)

        # --- Arity 1: PUSH ---
        if arity == 1:
            stack.append(gap_arg)

        # --- Arity 2: Stack manipulation ---
        elif arity == 2:
            if gap_arg == 0:   # POP
                pop()
            elif gap_arg == 1: # DUP
                a = pop(); stack.extend([a, a])
            elif gap_arg == 2: # SWAP
                b, a = pop(), pop(); stack.extend([b, a])
            elif gap_arg == 3: # ROT
                c, b, a = pop(), pop(), pop(); stack.extend([b, c, a])
            else:
                _runtime_error(
                    f"illegal gap_arg {gap_arg} for arity 2 at instruction {ip-1}"
                )

        # --- Arity 3: Arithmetic ---
        elif arity == 3:
            if gap_arg == 5:   # NEG (unary)
                a = pop(); stack.append(-a)
            elif gap_arg <= 4:
                b, a = pop(), pop()
                if gap_arg == 0: stack.append(a + b)
                elif gap_arg == 1: stack.append(a - b)
                elif gap_arg == 2: stack.append(a * b)
                elif gap_arg == 3:
                    if b == 0:
                        _runtime_error("division by zero (DIV)")
                    stack.append(math.floor(a / b))
                elif gap_arg == 4:
                    if b == 0:
                        _runtime_error("division by zero (MOD)")
                    stack.append(a - b * math.floor(a / b))
            else:
                _runtime_error(
                    f"illegal gap_arg {gap_arg} for arity 3 at instruction {ip-1}"
                )

        # --- Arity 4: Comparison / Bitwise ---
        elif arity == 4:
            if gap_arg == 6:   # NOT (unary)
                a = pop(); stack.append(~a)
            elif gap_arg <= 5:
                b, a = pop(), pop()
                if gap_arg == 0: stack.append(1 if a == b else 0)
                elif gap_arg == 1: stack.append(1 if a < b else 0)
                elif gap_arg == 2: stack.append(1 if a > b else 0)
                elif gap_arg == 3: stack.append(a & b)
                elif gap_arg == 4: stack.append(a | b)
                elif gap_arg == 5: stack.append(a ^ b)
            else:
                _runtime_error(
                    f"illegal gap_arg {gap_arg} for arity 4 at instruction {ip-1}"
                )

        # --- Arity 5: JUMP ---
        elif arity == 5:
            target = gap_arg
            if target >= prog_len:
                _runtime_error(
                    f"JUMP target {target} out of bounds (program length {prog_len})"
                )
            ip = target

        # --- Arity 6: JUMPZ ---
        elif arity == 6:
            cond = pop()
            target = gap_arg
            if cond == 0:
                if target >= prog_len:
                    _runtime_error(
                        f"JUMPZ target {target} out of bounds (program length {prog_len})"
                    )
                ip = target

        # --- Arity 7: JUMPNZ ---
        elif arity == 7:
            cond = pop()
            target = gap_arg
            if cond != 0:
                if target >= prog_len:
                    _runtime_error(
                        f"JUMPNZ target {target} out of bounds (program length {prog_len})"
                    )
                ip = target

        # --- Arity 8: I/O ---
        elif arity == 8:
            if gap_arg == 0:   # INCHAR
                ch = sys.stdin.buffer.read(1)
                stack.append(ord(ch) if ch else -1)
            elif gap_arg == 1: # OUTCHAR
                c = pop()
                sys.stdout.buffer.write(bytes([c % 256]))
                sys.stdout.buffer.flush()
            elif gap_arg == 2: # INNUM
                line = sys.stdin.readline().strip()
                try:
                    stack.append(int(line))
                except (ValueError, EOFError):
                    stack.append(-1)
            elif gap_arg == 3: # OUTNUM
                n = pop()
                sys.stdout.buffer.write((str(n) + '\n').encode())
                sys.stdout.buffer.flush()
            else:
                _runtime_error(
                    f"illegal gap_arg {gap_arg} for arity 8 at instruction {ip-1}"
                )

        # --- Arity 9: Memory ---
        elif arity == 9:
            if gap_arg == 0:   # LOAD
                addr = pop()
                stack.append(memory.get(addr, 0))
            elif gap_arg == 1: # STORE
                addr = pop()
                val = pop()
                memory[addr] = val
            else:
                _runtime_error(
                    f"illegal gap_arg {gap_arg} for arity 9 at instruction {ip-1}"
                )

        # --- Arity 10: HALT ---
        elif arity == 10:
            sys.exit(0)

        # --- Arity 11: CALL ---
        elif arity == 11:
            target = gap_arg
            if target >= prog_len:
                _runtime_error(
                    f"CALL target {target} out of bounds (program length {prog_len})"
                )
            stack.append(ip)  # push return address (ip already advanced)
            ip = target

        # --- Arity 12: RET ---
        elif arity == 12:
            ret_addr = pop()
            if ret_addr < 0 or ret_addr > prog_len:
                _runtime_error(
                    f"RET target {ret_addr} out of bounds (program length {prog_len})"
                )
            ip = ret_addr

        # --- Illegal ---
        else:
            _runtime_error(
                f"illegal instruction arity {arity} at instruction {ip-1} "
                f"(arities 13+ are reserved)"
            )

    # Fell off end of program — implicit halt
    sys.exit(0)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    args = sys.argv[1:]

    if not args:
        print(__doc__, file=sys.stderr)
        sys.exit(2)

    disasm_mode = False
    if args[0] == "--disassemble":
        disasm_mode = True
        args = args[1:]

    if not args:
        print("error: no input file", file=sys.stderr)
        sys.exit(2)

    path = args[0]
    try:
        with open(path, "r") as f:
            source = f.read()
    except OSError as e:
        print(f"error: cannot open '{path}': {e}", file=sys.stderr)
        sys.exit(2)

    instructions = parse(source)

    if disasm_mode:
        disassemble(instructions)
        return

    execute(instructions)


if __name__ == "__main__":
    main()
