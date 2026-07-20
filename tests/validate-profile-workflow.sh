#!/usr/bin/env bash
set -euo pipefail

workflow=${WORKFLOW_FILE:-.github/workflows/main.yml}

ruby -e 'require "yaml"; YAML.parse_file(ARGV.fetch(0))' "$workflow"
test "$(grep -c 'target_branch: output' "$workflow")" -eq 1
test "$(grep -c 'if-no-files-found: error' "$workflow")" -eq 4
if grep -qE '^ +git push$' "$workflow"; then
  echo "workflow must not push generated files directly" >&2
  exit 1
fi
grep -q 'needs: \[generate-snake, generate-main-stats, generate-pins, generate-star-history\]' "$workflow"
grep -q 'name: snake-assets' "$workflow"
grep -q 'pattern: main-\*' "$workflow"
grep -q 'pattern: pin-\*' "$workflow"
grep -q 'name: star-history-assets' "$workflow"
grep -q 'repository: star-history/star-history' "$workflow"
grep -q 'ref: bcddc9d532b10bac7e0187a741288bf9cab17616' "$workflow"
grep -q 'star-history-token-test-repo.patch' "$workflow"
grep -q 'http://127.0.0.1:8080/svg' "$workflow"
grep -q 'path: dist/profile' "$workflow"
grep -q 'path: dist$' "$workflow"
grep -q 'group: profile-assets-' "$workflow"
grep -q 'cancel-in-progress: true' "$workflow"
grep -q 'bash tests/validate-output-assets.sh dist' "$workflow"
test "$(grep -c 'output/profile/' README.md)" -eq 6
test "$(grep -c 'hect0x7/output/github-contribution-grid-snake' README.md)" -eq 3
test -z "$(find profile -maxdepth 1 -name '*.svg' -print -quit 2>/dev/null)"
test ! -e .github/scripts/generate_star_history.py
