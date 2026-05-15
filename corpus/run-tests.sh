#!/usr/bin/env bash
# PatrickScript conformance test runner
# Usage: bash corpus/run-tests.sh
# Runs all .ps files in corpus/ against expected output.
set -euo pipefail

INTERP="$(dirname "$0")/../interpreter/ps.py"
CORPUS="$(dirname "$0")"
PASS=0
FAIL=0

for ps_file in "$CORPUS"/*.ps; do
    name="$(basename "$ps_file" .ps)"
    expected_file="$CORPUS/$name.expected"
    stdin_file="$CORPUS/$name.stdin"
    desc_file="$CORPUS/$name.desc"

    desc="$(cat "$desc_file" 2>/dev/null || echo '(no description)')"

    stdin_arg=""
    if [[ -f "$stdin_file" && -s "$stdin_file" ]]; then
        stdin_arg="< $stdin_file"
    fi

    actual="$(python3 "$INTERP" "$ps_file" < "$stdin_file" 2>/dev/null || true)"
    expected="$(cat "$expected_file")"

    if [[ "$actual" == "$expected" ]]; then
        echo "PASS  $name"
        PASS=$((PASS + 1))
    else
        echo "FAIL  $name"
        echo "      desc:     $desc"
        echo "      expected: $(printf '%q' "$expected")"
        echo "      actual:   $(printf '%q' "$actual")"
        FAIL=$((FAIL + 1))
    fi
done

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
