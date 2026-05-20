// <!-- @scry.entry
// id: code.patrickscript-vscode-extension~0dfac2b2
// kind: internal
// status: active
// weight: 0.8
// tags:
//   - "topic:patrickscript"
//   - "patrickscript"
//   - "topic:vscode-extension"
//   - "vscode-extension"
//   - "topic:semantic-tokens"
//   - "semantic-tokens"
//   - "topic:codelens"
//   - "codelens"
//   - "scope:patrick-script"
//   - "patrick-script"
// summary: >
//   PatrickScript VS Code extension entry point. Registers three .ps
//   providers — semantic tokens (per-arity coloring via psPush/psStack/
//   …/psReserved IDs declared in package.json), CodeLens (decoded mnemonic
//   anchored above each word-run), hover (mnemonic + description + arity/
//   gap_arg) — all backed by the canonical TypeScript interpreter at
//   ../site/js/ps-interpreter.ts (esbuild bundles it in; no fork). .psa
//   is handled by the TextMate grammar at
//   syntaxes/patrickscript-assembly.tmLanguage.json. Soft parser
//   (locateInstructions) keeps highlighting/CodeLens live on malformed input.
//   Also: extension.ts, activate, registerDocumentSemanticTokensProvider,
//   registerCodeLensProvider, registerHoverProvider, locateInstructions,
//   safeLocate, PsSemanticTokensProvider, PsCodeLensProvider,
//   PsHoverProvider, single-line .ps, arity to token type mapping.
// rationale: >
//   Without this marker, the extension's surfaces and arity→token-type
//   mapping are invisible to scry meaning-search; a future wake editing
//   the providers would re-derive both.
// applies: editing the VS Code extension, debugging .ps highlighting, debugging .ps CodeLens, modifying the soft parser, registering new providers, mapping arity to semantic token type
// seeded_questions:
//   - "Where is the PatrickScript VS Code extension's entry point?"
//   - "Which semantic-token type does arity N map to?"
//   - "How does the extension reuse the shared TypeScript interpreter?"
//   - "How does the extension cope with malformed .ps input?"
//   - "PatrickScript CodeLens provider"
// @scry.entry.end -->

// PatrickScript VS Code extension.
//
// Three .ps surfaces over the canonical TypeScript interpreter at
// ../../site/js/ps-interpreter.ts (no fork — esbuild bundles the shared
// module into dist/extension.js at build time):
//
//   1. Semantic tokens — color each `patrick` run by arity, with each
//      arity bucket getting its own VS Code token type (psPush, psStack,
//      psArith, …) so a theme can paint them distinctly.
//   2. CodeLens       — decoded mnemonic anchored above each instruction
//                       ("0: PUSH 5", "1: ADD", "12: JUMP 4", ...).
//   3. Hover          — full mnemonic + description + arity/gap_arg.
//
// .psa is handled by the TextMate grammar in syntaxes/.

import * as vscode from "vscode";
import {
  parse,
  mnemonicOf,
  ParseError,
  WORD_TOKEN,
  WORD_LEN,
  type Instr,
} from "../../site/js/ps-interpreter";

// ---------------------------------------------------------------------------
// Shared parsing — produce per-instruction source ranges.
// ---------------------------------------------------------------------------

interface LocatedInstr {
  instr: Instr;
  /** byte offset of the first `patrick` in this instruction's word-run */
  start: number;
  /** byte offset one past the last `patrick` (end of word-run) */
  wordEnd: number;
  /** byte offset one past the gap (start of next instruction or EOF) */
  end: number;
}

function locateInstructions(source: string): LocatedInstr[] {
  const out: LocatedInstr[] = [];
  const n = source.length;
  let i = 0;
  while (i < n) {
    if (source.substr(i, WORD_LEN) !== WORD_TOKEN) {
      // skip a single character so we don't loop forever on bad input;
      // the canonical parser would throw here, but the extension stays soft.
      i += 1;
      continue;
    }
    const start = i;
    let arity = 0;
    while (i < n && source.substr(i, WORD_LEN) === WORD_TOKEN) {
      arity += 1;
      i += WORD_LEN;
    }
    const wordEnd = i;
    let gapWidth = 0;
    while (i < n && source.charAt(i) === " ") {
      gapWidth += 1;
      i += 1;
    }
    const gapArg = Math.max(gapWidth - 1, 0);
    out.push({ instr: { arity, gapArg }, start, wordEnd, end: i });
  }
  return out;
}

/** Try to parse; on ParseError fall back to soft locator so highlighting and
 *  hints still appear up to the bad byte. */
function safeLocate(doc: vscode.TextDocument): LocatedInstr[] {
  const text = doc.getText();
  try {
    parse(text); // throws on malformed input; we just use this as validation
  } catch {
    /* fall through to soft locator */
  }
  return locateInstructions(text);
}

// ---------------------------------------------------------------------------
// Semantic tokens — per-arity coloring.
// ---------------------------------------------------------------------------

/** Index matches the order in package.json's `semanticTokenTypes`. */
const SEMANTIC_TYPES = [
  "psPush",     // arity 1
  "psStack",    // arity 2
  "psArith",    // arity 3
  "psCmp",      // arity 4
  "psJump",     // arity 5
  "psJumpz",    // arity 6
  "psJumpnz",   // arity 7
  "psIo",       // arity 8
  "psMem",      // arity 9
  "psHalt",     // arity 10
  "psCall",     // arity 11
  "psRet",      // arity 12
  "psPushn",    // arity 13
  "psPick",     // arity 14
  "psReserved", // arity >= 15
];

const SEMANTIC_LEGEND = new vscode.SemanticTokensLegend(SEMANTIC_TYPES, []);

function arityToTokenIndex(arity: number): number {
  if (arity < 1) return SEMANTIC_TYPES.length - 1; // reserved/invalid
  if (arity >= 15) return SEMANTIC_TYPES.length - 1; // reserved
  return arity - 1;
}

class PsSemanticTokensProvider
  implements vscode.DocumentSemanticTokensProvider
{
  provideDocumentSemanticTokens(
    document: vscode.TextDocument,
  ): vscode.ProviderResult<vscode.SemanticTokens> {
    const cfg = vscode.workspace.getConfiguration("patrickscript.semanticTokens");
    if (cfg.get<boolean>("enabled", true) !== true) {
      return new vscode.SemanticTokens(new Uint32Array(0));
    }
    const builder = new vscode.SemanticTokensBuilder(SEMANTIC_LEGEND);
    const located = safeLocate(document);
    for (const li of located) {
      const range = new vscode.Range(
        document.positionAt(li.start),
        document.positionAt(li.wordEnd),
      );
      const typeIdx = arityToTokenIndex(li.instr.arity);
      if (range.start.line === range.end.line) {
        builder.push(
          range.start.line,
          range.start.character,
          range.end.character - range.start.character,
          typeIdx,
          0,
        );
      } else {
        for (let ln = range.start.line; ln <= range.end.line; ln++) {
          const lineRange = document.lineAt(ln).range;
          const startCh = ln === range.start.line ? range.start.character : 0;
          const endCh =
            ln === range.end.line ? range.end.character : lineRange.end.character;
          if (endCh > startCh) {
            builder.push(ln, startCh, endCh - startCh, typeIdx, 0);
          }
        }
      }
    }
    return builder.build();
  }
}

// ---------------------------------------------------------------------------
// CodeLens — decoded mnemonic anchored at each instruction's word-run.
// ---------------------------------------------------------------------------

class PsCodeLensProvider implements vscode.CodeLensProvider {
  provideCodeLenses(
    document: vscode.TextDocument,
  ): vscode.ProviderResult<vscode.CodeLens[]> {
    const cfg = vscode.workspace.getConfiguration("patrickscript.codeLens");
    if (cfg.get<boolean>("enabled", true) !== true) return [];
    const showIndex = cfg.get<boolean>("showIndex", true);

    const located = safeLocate(document);
    const lenses: vscode.CodeLens[] = [];
    located.forEach((li, idx) => {
      const { mnemonic, description } = mnemonicOf(li.instr);
      const range = new vscode.Range(
        document.positionAt(li.start),
        document.positionAt(li.wordEnd),
      );
      const label = showIndex ? `${idx}: ${mnemonic}` : mnemonic;
      lenses.push(
        new vscode.CodeLens(range, {
          title: label,
          tooltip: description,
          command: "", // non-actionable label
        }),
      );
    });
    return lenses;
  }
}

// ---------------------------------------------------------------------------
// Hover — opcode + operand + stack effect under the cursor.
// ---------------------------------------------------------------------------

class PsHoverProvider implements vscode.HoverProvider {
  provideHover(
    document: vscode.TextDocument,
    position: vscode.Position,
  ): vscode.ProviderResult<vscode.Hover> {
    const cfg = vscode.workspace.getConfiguration("patrickscript.hover");
    if (cfg.get<boolean>("enabled", true) !== true) return undefined;
    const offset = document.offsetAt(position);
    const located = safeLocate(document);
    const li = located.find((x) => offset >= x.start && offset < x.end);
    if (!li) return undefined;
    const idx = located.indexOf(li);
    const { mnemonic, description } = mnemonicOf(li.instr);
    const md = new vscode.MarkdownString();
    md.appendMarkdown(`### \`${mnemonic}\`  _(instr ${idx})_\n\n`);
    md.appendMarkdown(`${description}\n\n`);
    md.appendMarkdown(
      `- **arity** \`${li.instr.arity}\` (word-run length)\n` +
        `- **gap_arg** \`${li.instr.gapArg}\` (gap_width - 1, clamped at 0)\n`,
    );
    md.appendMarkdown(
      `\nSpec: [patrickscript.com/spec](https://patrickscript.com/spec)`,
    );
    md.isTrusted = false;
    const range = new vscode.Range(
      document.positionAt(li.start),
      document.positionAt(li.wordEnd),
    );
    return new vscode.Hover(md, range);
  }
}

// ---------------------------------------------------------------------------
// Activate.
// ---------------------------------------------------------------------------

export function activate(context: vscode.ExtensionContext) {
  const selector: vscode.DocumentSelector = { language: "patrickscript" };

  context.subscriptions.push(
    vscode.languages.registerDocumentSemanticTokensProvider(
      selector,
      new PsSemanticTokensProvider(),
      SEMANTIC_LEGEND,
    ),
    vscode.languages.registerCodeLensProvider(
      selector,
      new PsCodeLensProvider(),
    ),
    vscode.languages.registerHoverProvider(selector, new PsHoverProvider()),
  );
}

export function deactivate(): void {
  /* nothing to clean up */
}
