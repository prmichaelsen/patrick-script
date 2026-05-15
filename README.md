# PatrickScript

A programming language with exactly two lexical tokens: the literal word
`patrick` and a single space (` `).

PatrickScript's entire specification — computational model, grammar, semantics,
tooling — is designed and authored by an LLM. The only human-fixed inputs are
the name and the two tokens. Everything else is the agent's to decide.

The language is owned by the `patrick-script-worker` track in the `reflection`
substrate. The specification, reference implementation, and conformance corpus
live in this repository.

Status: v1.0.0 — spec, reference interpreter, and 22-test conformance corpus
complete. Turing complete via JUMP/JUMPZ/JUMPNZ + unbounded memory.

## Running programs

```
./patrickscript <program.ps>
./patrickscript --disassemble <program.ps>
```

Or directly via the interpreter:

```
python3 interpreter/ps.py <program.ps>
```

## Running the conformance corpus

```
bash corpus/run-tests.sh
```

All 33 tests should pass.

## Writing programs with the assembler

Writing raw PatrickScript is impractical (PUSH 42 requires one `patrick`
token and 43 spaces). Use the assembler (`interpreter/psa.py`) for
human-readable input:

```
python3 interpreter/psa.py program.psa > program.ps
./patrickscript program.ps
```

Assembly format: one mnemonic per line, labels end with `:`, comments
start with `;`. See `examples/` for complete programs.

## Examples

`examples/` contains:
- `counter.psa` — infinite counter (0, 1, 2, ...)
- `echo.psa` — copy stdin to stdout byte by byte
- `fibonacci.psa` — first 10 Fibonacci numbers
- `fizzbuzz.psa` — FizzBuzz 1..15; showcases MOD, JUMPZ, OUTCHAR+OUTNUM mixing

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
