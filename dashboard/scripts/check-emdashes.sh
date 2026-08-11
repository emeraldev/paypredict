#!/usr/bin/env bash
# Fail the build if any em-dash (U+2014) appears in user-visible copy or
# labels. Comments (//, /*, *, /**, {/*) are excluded — this rule is about
# what a customer sees, not what a developer scribbles beside their code.
#
# For empty-cell placeholders or "no value" glyphs, use an en-dash (–,
# U+2013) instead. For prose, use a period, comma, or colon.
set -eo pipefail

cd "$(dirname "$0")/.."

matches=$(
  grep -rn '—' src/ --include='*.ts' --include='*.tsx' 2>/dev/null \
    | grep -vE ':[[:space:]]*(//|\*|/\*|\{/\*)' \
    || true
)

if [ -n "$matches" ]; then
  echo "Found em-dashes ('—') in user-visible copy or labels."
  echo "Replace with a period, comma, colon, or en-dash ('–') as appropriate."
  echo
  echo "$matches"
  exit 1
fi

echo "No em-dashes in user-visible strings."
