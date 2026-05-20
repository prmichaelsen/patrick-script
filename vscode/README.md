<!-- @scry.entry
id: doc.patrickscript-vscode-readme~0ff76864
kind: internal
status: active
weight: 0.4
tags:
  - "topic:patrickscript"
  - "patrickscript"
  - "topic:vscode-extension"
  - "vscode-extension"
  - "topic:tooling"
  - "tooling"
summary: >
  README for the PatrickScript VS Code extension. Two file types
  (.ps and .psa); three .ps surfaces (semantic tokens, CodeLens,
  hover); TextMate grammar for .psa. Shared TypeScript interpreter at
  ../site/js/ps-interpreter.ts is bundled in via esbuild, no fork.
  Also: VS Code extension PatrickScript, vsce package, CodeLens
  overlay, semantic tokens, .ps highlighting, .psa highlighting,
  disassembler.
rationale: >
  Without this, the extension's surfaces and build/publish flow are
  undiscoverable from the marketplace page; future wakes also lose
  the design rationale for range-anchored CodeLens on single-line .ps.
applies: publishing the extension, modifying any of its providers, debugging .ps highlighting, updating the marketplace page
seeded_questions:
  - "How do I install the PatrickScript VS Code extension?"
  - "How does CodeLens render on single-line .ps files?"
  - "Where is the .ps interpreter the extension uses?"
  - "How do I rebuild and publish the PatrickScript VS Code extension?"
@scry.entry.end -->

# PatrickScript for VS Code

Syntax highlighting and inline disassembly for
[PatrickScript](https://patrickscript.com) — the two-token language
whose entire source is the literal word `patrick` and the space.

## What it does

### `.ps` files (the language itself)

- **Per-arity coloring (semantic tokens)**. Each `patrick` run is
  colored by its arity, so the opcode family is visible at a glance
  — pushes look different from arithmetic, which looks different
  from control flow. Themes can paint each arity bucket distinctly
  via the `psPush`, `psStack`, `psArith`, ..., `psReserved` token
  types declared in the manifest.
- **Decoded CodeLens overlay**. The instruction's index and mnemonic
  float above each word-run (`0: PUSH 5`, `1: ADD`, `12: JUMP 4`,
  ...). The label comes from the same TypeScript interpreter that
  powers [patrickscript.com/play](https://patrickscript.com/play) —
  there is no separate disassembler.
- **Hover disassembly**. Hover any `patrick` to see the mnemonic,
  description, arity, and gap_arg.

### `.psa` files (the assembly form)

- Comments (`; ...`)
- Labels (`name:`)
- Mnemonics with operands (`PUSH 5`, `JUMP fac_base`)
- Bare mnemonics (`ADD`, `DUP`, ...)

## How CodeLens works on single-line `.ps`

VS Code anchors each CodeLens to a *range* (not to a whole line) —
multiple CodeLenses on the same line stack horizontally in the
gutter above that line, each labeled with the mnemonic of the
instruction it covers. `.ps` programs are typically a single line
of `patrick`-runs, so the entire decoded program reads top-to-bottom
above that line as a column of `0: PUSH 5`, `1: ADD`, ... labels —
exactly the "instruction stream above the source" effect the
directive called for.

## Settings

- `patrickscript.semanticTokens.enabled` (default `true`) — global
  on/off for per-arity coloring.
- `patrickscript.codeLens.enabled` (default `true`) — global on/off
  for the decoded-instruction overlay.
- `patrickscript.codeLens.showIndex` (default `true`) — show
  `0: PUSH 5` (true) or `PUSH 5` (false).
- `patrickscript.hover.enabled` (default `true`) — global on/off
  for the disassembly hover popup.

## Building from source

The shared interpreter lives at
`../site/js/ps-interpreter.ts` and is bundled into
`dist/extension.js` via [esbuild](https://esbuild.github.io/) — no
fork, no parallel implementation.

```
npm install
npm run build              # esbuild → dist/extension.js
npm run package            # vsce package → patrickscript-vscode-*.vsix
```

## Publishing

```
npm run publish            # VS Code Marketplace (needs vsce publisher token)
npm run publish:ovsx       # Open VSX Registry (needs ovsx token)
```

Publisher tokens are an originator responsibility (Marketplace
account creation, PAT issuance).

## About — LLM authorship

**PatrickScript** is a programming language designed entirely by a
large language model (Claude). The two-token alphabet (`patrick` +
space) is the only constraint the human author fixed; every other
property — the stack-machine semantics, the per-arity opcode
families, the assembly form, the unary-encoding scheme — emerged
from LLM design choices, then was implemented and refined through
subsequent LLM-driven development.

**This VS Code extension** was likewise authored by an LLM — the
TextMate grammars, the per-arity semantic-token provider, the
range-anchored CodeLens disassembler, and the hover provider all
came from Claude.

Read more at [patrickscript.com](https://patrickscript.com).

## License

MIT — same as the rest of the
[patrick-script](https://github.com/prmichaelsen/patrick-script) project.
