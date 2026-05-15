#!/usr/bin/env python3
# <!-- @scry.entry
# id: code.patrickscript-assembler~686c3d51
# kind: code
# status: active
# weight: 0.9
# tags:
#   - "topic:patrickscript"
#   - "topic:assembler"
#   - "patrickscript"
#   - "assembler"
#   - "psa"
#   - "mnemonic"
#   - "two-pass"
#   - "label-resolution"
# summary: >
#   PatrickScript assembler (psa.py). Accepts mnemonic notation with labels
#   and emits valid .ps source. Two-pass: first pass records label→instruction
#   index, second pass encodes each instruction as repeated 'patrick' tokens
#   plus spaces. Input format: one instruction per line, semicolons introduce
#   comments, labels end with colon. Supports all v1.0.0 mnemonics. Also:
#   psa.py, PatrickScript assembler, assembly language, PUSH ADD JUMP JUMPZ
#   JUMPNZ HALT labels, mnemonic-to-source, two-pass assembler.
# rationale: >
#   Writing raw PatrickScript source is impractical — counting 'patrick' tokens
#   by hand for PUSH 42 means writing 1 patrick and 43 spaces. Without the
#   assembler, corpus tests and example programs cannot be written or read by
#   humans. The assembler is the human interface to PatrickScript.
# applies: >
#   writing PatrickScript programs, adding corpus tests, authoring examples,
#   learning the PatrickScript instruction set, debugging PatrickScript behavior
# seeded_questions:
#   - "How do I write a PatrickScript program with labels?"
#   - "PatrickScript assembler usage"
#   - "How do I compile .psa to .ps?"
#   - "PatrickScript mnemonic notation"
#   - "psa.py assembler format"
# @scry.entry.end -->
"""
PatrickScript assembler.

Reads a .psa (assembly) file and emits .ps (PatrickScript source) to stdout.

Assembly format:
    MNEMONIC [ARG]    ; optional comment
    label:            ; defines a label (target for JUMP/JUMPZ/JUMPNZ)

Labels are resolved on a second pass. Jump targets may be either a label
name or a bare integer (0-based instruction index).

All v1.0.0 mnemonics are supported:
    PUSH n   POP   DUP   SWAP   ROT
    ADD  SUB  MUL  DIV  MOD  NEG
    EQ   LT   GT   AND  OR   XOR  NOT
    JUMP target   JUMPZ target   JUMPNZ target
    INCHAR  OUTCHAR  INNUM  OUTNUM
    LOAD  STORE
    HALT

Usage:
    python psa.py <program.psa>           # emit .ps to stdout
    python psa.py --disassemble <out.ps>  # disassemble back (delegates to ps.py)

Exit codes:
    0  — success
    1  — assembly error
"""

import sys
import os

WORD = "patrick"

# Mnemonic → (arity, gap_arg_or_None)
# None gap_arg means the instruction takes a numeric argument
MNEMONIC_TABLE: dict[str, tuple[int, int | None]] = {
    "PUSH":    (1,  None),
    "POP":     (2,  0),
    "DUP":     (2,  1),
    "SWAP":    (2,  2),
    "ROT":     (2,  3),
    "ADD":     (3,  0),
    "SUB":     (3,  1),
    "MUL":     (3,  2),
    "DIV":     (3,  3),
    "MOD":     (3,  4),
    "NEG":     (3,  5),
    "EQ":      (4,  0),
    "LT":      (4,  1),
    "GT":      (4,  2),
    "AND":     (4,  3),
    "OR":      (4,  4),
    "XOR":     (4,  5),
    "NOT":     (4,  6),
    "JUMP":    (5,  None),
    "JUMPZ":   (6,  None),
    "JUMPNZ":  (7,  None),
    "INCHAR":  (8,  0),
    "OUTCHAR": (8,  1),
    "INNUM":   (8,  2),
    "OUTNUM":  (8,  3),
    "LOAD":    (9,  0),
    "STORE":   (9,  1),
    "HALT":    (10, 0),
}

# Mnemonics that take a numeric/label argument
TAKES_ARG = {"PUSH", "JUMP", "JUMPZ", "JUMPNZ"}


def _asm_error(line_no: int, line: str, msg: str) -> None:
    print(
        f"psa: assembly error at line {line_no}: {msg}\n"
        f"     {line.rstrip()}",
        file=sys.stderr,
    )
    sys.exit(1)


def assemble(source: str) -> str:
    """
    Two-pass assembler. Returns the .ps source string.
    """
    lines = source.splitlines()

    # -----------------------------------------------------------------------
    # Pass 1: collect labels and build (mnemonic, raw_arg, line_no) list
    # -----------------------------------------------------------------------
    # Each element of `instructions` is (mnemonic_upper, raw_arg_str_or_None, line_no)
    instructions: list[tuple[str, str | None, int]] = []
    labels: dict[str, int] = {}  # label → instruction index

    for line_no, line in enumerate(lines, start=1):
        # Strip comment
        if ";" in line:
            line = line[: line.index(";")]
        line = line.strip()
        if not line:
            continue

        # Label definition
        if line.endswith(":"):
            label = line[:-1].strip()
            if not label.isidentifier():
                _asm_error(line_no, lines[line_no - 1], f"invalid label '{label}'")
            if label in labels:
                _asm_error(line_no, lines[line_no - 1],
                           f"duplicate label '{label}'")
            labels[label] = len(instructions)
            continue

        # Instruction
        parts = line.split()
        mnemonic = parts[0].upper()
        if mnemonic not in MNEMONIC_TABLE:
            _asm_error(line_no, lines[line_no - 1],
                       f"unknown mnemonic '{mnemonic}'")

        if mnemonic in TAKES_ARG:
            if len(parts) < 2:
                _asm_error(line_no, lines[line_no - 1],
                           f"'{mnemonic}' requires an argument")
            raw_arg: str | None = parts[1]
        else:
            if len(parts) > 1:
                _asm_error(line_no, lines[line_no - 1],
                           f"'{mnemonic}' takes no argument but got '{parts[1]}'")
            raw_arg = None

        instructions.append((mnemonic, raw_arg, line_no))

    if not instructions:
        return ""  # empty program is valid

    # -----------------------------------------------------------------------
    # Pass 2: resolve labels and emit .ps source
    # -----------------------------------------------------------------------
    prog_len = len(instructions)
    parts_out: list[str] = []

    for idx, (mnemonic, raw_arg, line_no) in enumerate(instructions):
        arity, fixed_gap_arg = MNEMONIC_TABLE[mnemonic]
        line_text = lines[line_no - 1]

        # Resolve argument
        if fixed_gap_arg is not None:
            gap_arg = fixed_gap_arg
        else:
            # Must resolve raw_arg to an integer
            assert raw_arg is not None
            # Try label first, then integer
            if raw_arg in labels:
                gap_arg = labels[raw_arg]
            else:
                try:
                    gap_arg = int(raw_arg)
                except ValueError:
                    _asm_error(line_no, line_text,
                               f"unresolved label or invalid integer '{raw_arg}'")

            # Validate non-negative
            if gap_arg < 0:
                _asm_error(line_no, line_text,
                           f"argument {gap_arg} is negative (not allowed)")

        # Encode instruction: WORD * arity + ' ' * (gap_arg + 1)
        # The spec allows the final instruction to omit its trailing gap (treated
        # as gap_arg=0), but we always emit it so that non-zero gap_args on the
        # last instruction are not silently zeroed.
        word_part = WORD * arity
        gap_part = " " * (gap_arg + 1)

        parts_out.append(word_part + gap_part)

    return "".join(parts_out)


def main() -> None:
    args = sys.argv[1:]

    if not args:
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    if args[0] == "--help" or args[0] == "-h":
        print(__doc__)
        sys.exit(0)

    path = args[0]
    try:
        with open(path, "r") as f:
            source = f.read()
    except OSError as e:
        print(f"psa: cannot open '{path}': {e}", file=sys.stderr)
        sys.exit(1)

    output = assemble(source)
    sys.stdout.write(output)


if __name__ == "__main__":
    main()
