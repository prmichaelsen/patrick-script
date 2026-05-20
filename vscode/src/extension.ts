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
//   - "topic:inlay-hints"
//   - "inlay-hints"
//   - "scope:patrick-script"
//   - "patrick-script"
// summary: >
//   PatrickScript VS Code extension entry point. Registers three .ps
//   providers — semantic tokens (length-based coloring by arity), inlay
//   hints (decoded mnemonic + index per word-run), hover (mnemonic +
//   description + arity/gap_arg) — all backed by the canonical TypeScript
//   interpreter at ../site/js/ps-interpreter.ts (esbuild bundles it in;
//   no fork). .psa is handled by the TextMate grammar at
//   syntaxes/patrickscript-assembly.tmLanguage.json. Soft parser
//   (locateInstructions) keeps highlighting/hints live on malformed input.
//   Also: extension.ts, activate, registerDocumentSemanticTokensProvider,
//   registerInlayHintsProvider, registerHoverProvider, locateInstructions,
//   safeLocate, PsSemanticTokensProvider, PsInlayHintsProvider,
//   PsHoverProvider, CodeLens-vs-inlay decision, .ps single-line.
// rationale: >
//   Without this marker, the extension's surfaces and the
//   CodeLens→inlay-hints design pivot are invisible to scry meaning-search;
//   a future wake editing the providers would re-derive both.
// applies: editing the VS Code extension, debugging .ps highlighting, debugging .ps inlay hints, modifying the soft parser, registering new providers, deciding between CodeLens and InlayHints in VS Code
// seeded_questions:
//   - "Where is the PatrickScript VS Code extension's entry point?"
//   - "Why does the extension use InlayHints instead of CodeLens?"
//   - "How does the extension reuse the shared TypeScript interpreter?"
//   - "How does the extension cope with malformed .ps input?"
//   - "PatrickScript semantic tokens provider"
// @scry.entry.end -->

// PatrickScript VS Code extension.
//
// Three .ps surfaces over the canonical TypeScript interpreter at
// ../../site/js/ps-interpreter.ts (no fork — esbuild bundles the shared
// module into dist/extension.js at build time):
//
//   1. Semantic tokens — color each `patrick` run by arity (opcode family).
//   2. Inlay hints     — decoded mnemonic floats inline above each
//                        word-group ("PUSH 5", "ADD", "JUMP 12", ...).
//   3. Hover           — full mnemonic + description + stack effect.
//
// (CodeLens was the original directive primitive, but .ps programs are
// typically single-line; CodeLens anchors to lines, which collapses every
// hint onto line 0. Inlay hints are the structurally correct VS Code
// primitive for inline overlays — they live between tokens, not above
// lines, which matches the .ps grain.)
//
// .psa is handled by the TextMate grammar in syntaxes/.

import * as vscode from "vscode";
import {
  parse,
  mnemonicOf,
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
// Semantic tokens — length-based coloring.
// ---------------------------------------------------------------------------

const SEMANTIC_TYPES = [
  "patrickscript.arity1",
  "patrickscript.arity2",
  "patrickscript.arity3",
  "patrickscript.arity4",
  "patrickscript.arity5",
  "patrickscript.arity6",
  "patrickscript.arity7",
  "patrickscript.arity8",
  "patrickscript.arity9",
  "patrickscript.arity10",
  "patrickscript.arity11",
  "patrickscript.arity12",
  "patrickscript.arity13",
  "patrickscript.arity14",
];

const SEMANTIC_LEGEND = new vscode.SemanticTokensLegend(SEMANTIC_TYPES, []);

class PsSemanticTokensProvider
  implements vscode.DocumentSemanticTokensProvider
{
  provideDocumentSemanticTokens(
    document: vscode.TextDocument,
  ): vscode.ProviderResult<vscode.SemanticTokens> {
    const builder = new vscode.SemanticTokensBuilder(SEMANTIC_LEGEND);
    const located = safeLocate(document);
    for (const li of located) {
      // Each `patrick` run gets one token per source line it touches.
      // .ps files are typically single-line, but be safe.
      const range = new vscode.Range(
        document.positionAt(li.start),
        document.positionAt(li.wordEnd),
      );
      const arityCapped = Math.min(Math.max(li.instr.arity, 1), 14);
      const typeIdx = arityCapped - 1;
      // Walk line-by-line if the range spans newlines.
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
// Inlay hints — decoded mnemonic immediately before each word-run.
// ---------------------------------------------------------------------------

class PsInlayHintsProvider implements vscode.InlayHintsProvider {
  provideInlayHints(
    document: vscode.TextDocument,
    range: vscode.Range,
  ): vscode.ProviderResult<vscode.InlayHint[]> {
    const cfg = vscode.workspace.getConfiguration("patrickscript.inlayHints");
    if (cfg.get<boolean>("enabled", true) !== true) return [];
    const showOperand = cfg.get<boolean>("showOperand", true);

    const located = safeLocate(document);
    const rangeStart = document.offsetAt(range.start);
    const rangeEnd = document.offsetAt(range.end);

    const hints: vscode.InlayHint[] = [];
    located.forEach((li, idx) => {
      if (li.end < rangeStart) return;
      if (li.start > rangeEnd) return;
      const { mnemonic, description, family } = mnemonicOf(li.instr);
      const label = showOperand ? `${idx}: ${mnemonic}` : `${idx}: ${family}`;
      const pos = document.positionAt(li.start);
      const hint = new vscode.InlayHint(
        pos,
        label,
        vscode.InlayHintKind.Type,
      );
      hint.paddingRight = true;
      hint.tooltip = new vscode.MarkdownString(
        `**${mnemonic}** — ${description}\n\n` +
          `_arity_ = ${li.instr.arity}, _gap_arg_ = ${li.instr.gapArg}`,
      );
      hints.push(hint);
    });
    return hints;
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
    const offset = document.offsetAt(position);
    const located = safeLocate(document);
    const li = located.find((x) => offset >= x.start && offset < x.end);
    if (!li) return undefined;
    const { mnemonic, description } = mnemonicOf(li.instr);
    const md = new vscode.MarkdownString();
    md.appendMarkdown(`### \`${mnemonic}\`\n\n`);
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
    vscode.languages.registerInlayHintsProvider(
      selector,
      new PsInlayHintsProvider(),
    ),
    vscode.languages.registerHoverProvider(selector, new PsHoverProvider()),
  );
}

export function deactivate(): void {
  /* nothing to clean up */
}
