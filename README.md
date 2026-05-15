# PatrickScript

A programming language with exactly two lexical tokens: the literal word
`patrick` and a single space (` `).

PatrickScript's entire specification — computational model, grammar, semantics,
tooling — is designed and authored by an LLM. The only human-fixed inputs are
the name and the two tokens. Everything else is the agent's to decide.

The language is owned by the `patrick-script-worker` track in the `reflection`
substrate. The specification, reference implementation, and conformance corpus
live in this repository.

Status: v1.1.0 — spec, reference interpreter, assembler, and 38-test
conformance corpus complete. Turing complete via JUMP/JUMPZ/JUMPNZ +
unbounded memory. v1.1.0 adds CALL/RET subroutines (arities 11–12).

## Running programs

```
./patrickscript <program.ps>
./patrickscript --disassemble <program.ps>
```

Or directly:

```
python3 interpreter/ps.py <program.ps>
```

## Running the conformance corpus

```
bash corpus/run-tests.sh
```

All 38 tests should pass.

## Writing programs with the assembler

Writing raw PatrickScript is impractical (PUSH 42 requires one `patrick`
token and 43 spaces). Use the assembler for human-readable input:

```
./psa program.psa > program.ps
./patrickscript program.ps
```

Or directly:

```
python3 interpreter/psa.py program.psa > program.ps
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
- `fizzbuzz.psa` — FizzBuzz 1..15 using CALL/RET subroutines + `.string` (v1.1.0)

To run an example:
```
python3 interpreter/psa.py examples/fibonacci.psa > /tmp/fib.ps
./patrickscript /tmp/fib.ps
```

## Documentation conventions

**Raw-legible tables**: every markdown table in every `*.md` documentation
file in this repo is formatted so the raw source is legible — column pipes
aligned vertically, separator rows padded to match. Pure presentation; content
is never changed to satisfy alignment. Apply this to any table you add or edit.
