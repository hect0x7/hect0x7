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
grep -Fq 'repo: [JMComic-Crawler-Python, jmcomic-ai, jm-view-server, JMComic-APK]' "$workflow"
grep -q 'name: star-history-assets' "$workflow"
grep -q 'repository: star-history/star-history' "$workflow"
grep -q 'ref: bcddc9d532b10bac7e0187a741288bf9cab17616' "$workflow"
grep -q 'star-history-token-test-repo.patch' "$workflow"
grep -q 'http://127.0.0.1:8080/svg' "$workflow"
grep -Fq 'STAR_HISTORY_TOKEN: ${{ secrets.STAR_HISTORY_TOKEN }}' "$workflow"
if grep -Fq 'STAR_HISTORY_TOKEN: ${{ secrets.GITHUB_TOKEN }}' "$workflow"; then
  echo "workflow must use the cross-repository Star History token" >&2
  exit 1
fi
grep -q 'jq -r '\''.single | join(",")'\'' .github/star-history-repositories.json' "$workflow"
grep -q 'jq -r '\''.ecosystem | join(",")'\'' .github/star-history-repositories.json' "$workflow"
grep -Fq "generate_chart '' star-history/star-history-JMComic-Crawler-Python.svg" "$workflow"
grep -Fq "generate_chart 'dark' star-history/star-history-JMComic-Crawler-Python-dark.svg" "$workflow"
grep -Fq "generate_chart '' star-history/star-history.svg" "$workflow"
grep -Fq "generate_chart 'dark' star-history/star-history-dark.svg" "$workflow"
grep -q 'path: dist/profile' "$workflow"
grep -q 'path: dist$' "$workflow"
grep -q 'group: profile-assets-' "$workflow"
grep -q 'cancel-in-progress: true' "$workflow"
grep -q 'bash tests/validate-output-assets.sh dist' "$workflow"
grep -q 'cp .github/output-README.md dist/README.md' "$workflow"
test "$(grep -c 'output/profile/' README.md)" -eq 6
test "$(grep -c 'hect0x7/output/github-contribution-grid-snake' README.md)" -eq 3
test -z "$(find profile -maxdepth 1 -name '*.svg' -print -quit 2>/dev/null)"
test ! -e .github/scripts/generate_star_history.py
test "$(jq -r '.single | length' .github/star-history-repositories.json)" -eq 1
test "$(jq -r '.ecosystem | length' .github/star-history-repositories.json)" -eq 4
test "$(jq -r '.single[0]' .github/star-history-repositories.json)" = 'hect0x7/JMComic-Crawler-Python'
test "$(jq -r '.ecosystem | unique | length' .github/star-history-repositories.json)" -eq 4
test "$(jq -r '.ecosystem | join(",")' .github/star-history-repositories.json)" = 'hect0x7/JMComic-Crawler-Python,hect0x7/JMComic-APK,hect0x7/jmcomic-ai,hect0x7/jm-view-server'
grep -q './profile/star-history-JMComic-Crawler-Python.svg' .github/output-README.md
grep -q './profile/star-history-JMComic-Crawler-Python-dark.svg' .github/output-README.md
grep -q './profile/star-history.svg' .github/output-README.md
grep -q './profile/star-history-dark.svg' .github/output-README.md
grep -q './profile/pin-jm-view-server.svg' .github/output-README.md
grep -q './profile/pin-jm-view-server-dark.svg' .github/output-README.md
