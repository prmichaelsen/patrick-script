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
  (.ps and .psa); three .ps surfaces (semantic tokens, inlay hints,
  hover); TextMate grammar for .psa. Shared TypeScript interpreter at
  ../site/js/ps-interpreter.ts is bundled in via esbuild, no fork.
  Also: VS Code extension PatrickScript, vsce package, inlay hints,
  semantic tokens, .ps highlighting, .psa highlighting, disassembler.
rationale: >
  Without this, the extension's surfaces and build/publish flow are
  undiscoverable from the marketplace page; future wakes also lose the
  rationale for inlay-hints-over-CodeLens.
applies: publishing the extension, modifying any of its providers, debugging .ps highlighting, updating the marketplace page
seeded_questions:
  - "How do I install the PatrickScript VS Code extension?"
  - "Why does the extension use inlay hints instead of CodeLens?"
  - "Where is the .ps interpreter the extension uses?"
  - "How do I rebuild and publish the PatrickScript VS Code extension?"
@scry.entry.end -->

# PatrickScript for VS Code

Syntax highlighting and inline disassembly for
[PatrickScript](https://patrickscript.com) — the two-token language
whose entire source is the literal word `patrick` and the space.

## What it does

### `.ps` files (the language itself)

- **Length-based coloring (semantic tokens)**. Each `patrick` run is
  colored by its arity, so the opcode family is visible at a glance
  — pushes look different from arithmetic, which looks different
  from control flow.
- **Decoded inlay hints**. The instruction's index and mnemonic float
  inline above each word-run (`0: PUSH 5`, `1: ADD`, `12: JUMP 4`,
  ...). The hint comes from the same TypeScript interpreter that
  powers [patrickscript.com/play](https://patrickscript.com/play) —
  there is no separate disassembler.
- **Hover disassembly**. Hover any `patrick` to see the mnemonic,
  description, arity, and gap_arg.

### `.psa` files (the assembly form)

- Comments (`; ...`)
- Labels (`name:`)
- Mnemonics with operands (`PUSH 5`, `JUMP fac_base`)
- Bare mnemonics (`ADD`, `DUP`, ...)

## Why inlay hints, not CodeLens

The original concept called for a CodeLens overlay above each word
group. CodeLens anchors to lines; `.ps` programs are typically a
single line of `patrick`-runs. CodeLens would pile every hint at
line 0 and become useless.

Inlay hints live *between tokens*, which is the structure `.ps`
actually has. Same information, correct primitive.

## Settings

- `patrickscript.inlayHints.enabled` (default `true`) — global on/off.
- `patrickscript.inlayHints.showOperand` (default `true`) — show
  `PUSH 5` (true) or `PUSH` (false).

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

## License

MIT — same as the rest of the
[patrick-script](https://github.com/patrickscript/patrick-script) project.
