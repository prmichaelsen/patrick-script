#!/usr/bin/env bash
# PatrickScript disassembler test runner
# Usage: bash corpus/run-disasm-tests.sh
# Runs --disassemble on all .ps files in corpus/disasm/ and checks output.
set -euo pipefail

INTERP="$(dirname "$0")/../src/patrickscript/ps.py"
DISASM_DIR="$(dirname "$0")/disasm"
PASS=0
FAIL=0

for ps_file in "$DISASM_DIR"/*.ps; do
    name="$(basename "$ps_file" .ps)"
    expected_file="$DISASM_DIR/$name.expected"
    desc_file="$DISASM_DIR/$name.desc"

    desc="$(cat "$desc_file" 2>/dev/null || echo '(no description)')"

    actual="$(python3 "$INTERP" --disassemble "$ps_file" 2>/dev/null || true)"
    expected="$(cat "$expected_file")"

    if [[ "$actual" == "$expected" ]]; then
        echo "PASS  $name"
        PASS=$((PASS + 1))
    else
        echo "FAIL  $name  ($desc)"
        echo "  expected: $(echo "$expected" | head -3)"
        echo "  actual:   $(echo "$actual"   | head -3)"
        FAIL=$((FAIL + 1))
    fi
done

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
