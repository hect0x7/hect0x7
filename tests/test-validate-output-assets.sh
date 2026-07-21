#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "$0")/.." && pwd)
fixture=$(mktemp -d)
trap 'rm -rf "$fixture"' EXIT

files=(
  github-contribution-grid-snake.svg
  github-contribution-grid-snake-dark.svg
  profile/stats-light.svg
  profile/stats-dark.svg
  profile/top-langs-light.svg
  profile/top-langs-dark.svg
  profile/pin-JMComic-Crawler-Python.svg
  profile/pin-JMComic-Crawler-Python-dark.svg
  profile/pin-jmcomic-ai.svg
  profile/pin-jmcomic-ai-dark.svg
  profile/pin-jm-view-server.svg
  profile/pin-jm-view-server-dark.svg
  profile/pin-plugin-jm-server.svg
  profile/pin-plugin-jm-server-dark.svg
  profile/pin-JMComic-APK.svg
  profile/pin-JMComic-APK-dark.svg
  profile/star-history.svg
  profile/star-history-dark.svg
  profile/star-history-JMComic-Crawler-Python.svg
  profile/star-history-JMComic-Crawler-Python-dark.svg
)

for file in "${files[@]}"; do
  mkdir -p "$fixture/$(dirname "$file")"
  printf 'svg' > "$fixture/$file"
done

cp "$repo_root/.github/output-README.md" "$fixture/README.md"

bash "$repo_root/tests/validate-output-assets.sh" "$fixture"

rm "$fixture/README.md"
if bash "$repo_root/tests/validate-output-assets.sh" "$fixture" >/dev/null 2>&1; then
  echo "validator accepted a missing README" >&2
  exit 1
fi
cp "$repo_root/.github/output-README.md" "$fixture/README.md"

rm "$fixture/profile/stats-light.svg"
if bash "$repo_root/tests/validate-output-assets.sh" "$fixture" >/dev/null 2>&1; then
  echo "validator accepted a missing asset" >&2
  exit 1
fi

printf 'svg' > "$fixture/profile/stats-light.svg"
printf 'svg' > "$fixture/profile/unexpected.svg"
if bash "$repo_root/tests/validate-output-assets.sh" "$fixture" >/dev/null 2>&1; then
  echo "validator accepted an unexpected asset" >&2
  exit 1
fi
