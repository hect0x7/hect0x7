#!/usr/bin/env bash
set -euo pipefail

root=${1:-dist}
expected=(
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

for file in "${expected[@]}"; do
  if [[ ! -s "$root/$file" ]]; then
    echo "missing or empty output asset: $file" >&2
    exit 1
  fi
done

cmp -s "$root/profile/pin-jm-view-server.svg" "$root/profile/pin-plugin-jm-server.svg" || {
  echo "legacy light jm view card differs from canonical asset" >&2
  exit 1
}
cmp -s "$root/profile/pin-jm-view-server-dark.svg" "$root/profile/pin-plugin-jm-server-dark.svg" || {
  echo "legacy dark jm view card differs from canonical asset" >&2
  exit 1
}

if [[ ! -s "$root/README.md" ]]; then
  echo "missing or empty output README" >&2
  exit 1
fi

grep -q './profile/star-history.svg' "$root/README.md"
grep -q './profile/star-history-JMComic-Crawler-Python.svg' "$root/README.md"
grep -q 'used-by/showcase/zh-CN-light.svg' "$root/README.md"

actual_count=$(find "$root" -type f -name '*.svg' | wc -l | tr -d ' ')
if [[ "$actual_count" -ne "${#expected[@]}" ]]; then
  echo "expected ${#expected[@]} SVG assets, found $actual_count" >&2
  exit 1
fi
