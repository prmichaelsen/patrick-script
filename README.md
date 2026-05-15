# PatrickScript

A programming language with exactly two lexical tokens: the literal word
`patrick` and a single space (` `).

PatrickScript's entire specification — computational model, grammar, semantics,
tooling — is designed and authored by an LLM. The only human-fixed inputs are
the name and the two tokens. Everything else is the agent's to decide.

The language is owned by the `patrick-script-worker` track in the `reflection`
substrate. The specification, reference implementation, and conformance corpus
live in this repository.

Status: v1.3.0 — spec, reference interpreter, assembler, and 50-test
conformance corpus (+ 12 disassembler round-trip tests) complete. Turing
complete via JUMP/JUMPZ/JUMPNZ + unbounded memory. v1.1.0 adds CALL/RET
subroutines (arities 11–12). v1.2.0 adds PUSHN single-instruction negative
literal (arity 13). v1.3.0 adds PICK stack-copy instruction (arity 14).

## Install (once published to PyPI)

```
pip install patrickscript
# or
uv add patrickscript
```

After install, `patrickscript` and `patrickscript-asm` are on PATH.

## Running programs

```
./patrickscript <program.ps>
./patrickscript --disassemble <program.ps>
```

Or directly:

```
python3 src/patrickscript/ps.py <program.ps>
```

## Running the conformance corpus

```
bash corpus/run-tests.sh
```

All 49 corpus tests and 12 disassembler round-trip tests should pass.

## Writing programs with the assembler

Writing raw PatrickScript is impractical (PUSH 42 requires one `patrick`
token and 43 spaces). Use the assembler for human-readable input:

```
./psa program.psa > program.ps
./patrickscript program.ps
```

Or directly:

```
python3 src/patrickscript/psa.py program.psa > program.ps
./patrickscript program.ps
```

Assembly format: one mnemonic per line, labels end with `:`, comments
start with `;`. String literals via `.string "text"` directive (emits
PUSH+OUTCHAR per character, supports `\n \t \\ \"`). See `examples/`
for complete programs.

## Examples

`examples/` contains:
- `hello-world.psa` — "Hello, World!" via `.string` directive (v1.1.0)
- `counter.psa` — infinite counter (0, 1, 2, ...)
- `echo.psa` — copy stdin to stdout byte by byte
- `fibonacci.psa` — first 10 Fibonacci numbers
- `factorial-recursive.psa` — recursive 5! using CALL/RET; shows nested recursion (v1.1.0)
- `fizzbuzz.psa` — FizzBuzz 1..15 using CALL/RET subroutines + `.string` (v1.1.0)
- `call-string.psa` — CALL/RET subroutine called twice; `.string` inside subroutine (v1.1.0)
- `square.psa` — compute n² using PICK 0 for non-destructive stack copy (v1.3.0)
- `pick-demo.psa` — PICK 2 copies a deep stack element; prints four characters (v1.3.0)
- `rot13.psa` — ROT13 cipher: rotate A-Z and a-z by 13, pass others through; its own inverse (v1.3.0)

To run an example:
```
python3 src/patrickscript/psa.py examples/fibonacci.psa > /tmp/fib.ps
./patrickscript /tmp/fib.ps
```

## Documentation conventions

**Raw-legible tables**: every markdown table in every `*.md` documentation
file in this repo is formatted so the raw source is legible — column pipes
aligned vertically, separator rows padded to match. Pure presentation; content
is never changed to satisfy alignment. Apply this to any table you add or edit.
