#!/usr/bin/env python3

import argparse
import json
import math
import os
import re
import sys
import time
from collections import defaultdict
from datetime import date, datetime, timezone
from html import escape
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_ROOT = "https://api.github.com"
USER_AGENT = "hect0x7-star-history-action"
COLORS = ("#0969da", "#cf222e", "#1a7f37", "#8250df", "#bc4c00", "#0550ae")


def parse_args():
    parser = argparse.ArgumentParser(description="Generate cached GitHub star history SVGs.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dark-output", type=Path, required=True)
    return parser.parse_args()


def github_request(path, token, accept="application/vnd.github+json"):
    headers = {
        "Accept": accept,
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2026-03-10",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(f"{API_ROOT}{path}", headers=headers)
    for attempt in range(3):
        try:
            with urlopen(request, timeout=30) as response:
                return json.load(response)
        except HTTPError as error:
            message = error.read().decode("utf-8", errors="replace")
            if error.code >= 500 and attempt < 2:
                time.sleep(2 ** attempt)
                continue
            if error.code in (401, 403):
                raise RuntimeError(
                    "GitHub rejected the token or exhausted its API quota. "
                    "Set the STAR_HISTORY_TOKEN repository secret to a fine-grained token "
                    f"that can read the configured repositories. Response: {message}"
                ) from error
            raise RuntimeError(f"GitHub API request failed ({error.code}): {message}") from error
        except URLError as error:
            if attempt < 2:
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"GitHub API request failed: {error.reason}") from error

    raise RuntimeError("GitHub API request failed after retries")


def load_repositories(path):
    repositories = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(repositories, list) or not repositories:
        raise ValueError("Repository config must be a non-empty JSON array")

    normalized = []
    for repository in repositories:
        if not isinstance(repository, str) or not re.fullmatch(r"[^/\s]+/[^/\s]+", repository):
            raise ValueError(f"Invalid repository name: {repository!r}")
        normalized.append(repository)
    return normalized


def load_cache(path):
    if not path.exists():
        return {"version": 1, "repositories": {}}

    cache = json.loads(path.read_text(encoding="utf-8"))
    if cache.get("version") != 1 or not isinstance(cache.get("repositories"), dict):
        raise ValueError("Unsupported star history cache format")
    return cache


def fetch_daily_history(repository, expected_count, token):
    daily_counts = defaultdict(int)
    page_count = max(1, math.ceil(expected_count / 100))

    for page in range(1, page_count + 1):
        stargazers = github_request(
            f"/repos/{repository}/stargazers?per_page=100&page={page}",
            token,
            accept="application/vnd.github.star+json",
        )
        if not isinstance(stargazers, list):
            raise RuntimeError(f"Unexpected stargazer response for {repository}")
        for stargazer in stargazers:
            starred_at = stargazer.get("starred_at")
            if starred_at:
                daily_counts[starred_at[:10]] += 1

    fetched_count = sum(daily_counts.values())
    if fetched_count != expected_count:
        raise RuntimeError(
            f"Fetched {fetched_count} stargazers for {repository}, "
            f"but GitHub reports {expected_count}. Refusing to replace the cache."
        )

    cumulative = 0
    history = []
    for day, count in sorted(daily_counts.items()):
        cumulative += count
        history.append([day, cumulative])
    return history


def update_cache(repositories, cache, token):
    cached_repositories = cache["repositories"]
    updated = {}

    for repository in repositories:
        metadata = github_request(f"/repos/{repository}", token)
        expected_count = metadata["stargazers_count"]
        cached = cached_repositories.get(repository)

        if cached and cached.get("stargazers_count") == expected_count and cached.get("history"):
            print(f"Using cached history for {repository} ({expected_count} stars)")
            updated[repository] = cached
            continue

        print(f"Refreshing history for {repository} ({expected_count} stars)")
        updated[repository] = {
            "stargazers_count": expected_count,
            "history": fetch_daily_history(repository, expected_count, token),
        }

    cache["repositories"] = updated
    return cache


def parse_day(value):
    return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc).date()


def nice_maximum(value):
    if value <= 0:
        return 1
    exponent = 10 ** math.floor(math.log10(value))
    fraction = value / exponent
    for step in (1, 2, 5, 10):
        if fraction <= step:
            return step * exponent
    return 10 * exponent


def format_number(value):
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}m".rstrip("0").rstrip(".")
    if value >= 1_000:
        return f"{value / 1_000:.1f}k".rstrip("0").rstrip(".")
    return str(value)


def interpolate_ticks(start, end, count):
    if start == end:
        return [start]
    span = (end - start).days
    return [start.fromordinal(start.toordinal() + round(span * index / (count - 1))) for index in range(count)]


def render_svg(repositories, cache, dark=False):
    width = 900
    height = 520
    margin_left = 72
    margin_right = 28
    margin_top = 92
    margin_bottom = 64
    chart_width = width - margin_left - margin_right
    chart_height = height - margin_top - margin_bottom

    background = "#0d1117" if dark else "#ffffff"
    foreground = "#f0f6fc" if dark else "#1f2328"
    muted = "#8b949e" if dark else "#656d76"
    grid = "#30363d" if dark else "#d8dee4"
    border = "#30363d" if dark else "#d0d7de"

    histories = []
    all_days = []
    maximum = 0
    for repository in repositories:
        history = [(parse_day(day), count) for day, count in cache["repositories"][repository]["history"]]
        histories.append((repository, history))
        if history:
            all_days.extend((history[0][0], history[-1][0]))
            maximum = max(maximum, history[-1][1])

    if not all_days:
        today = date.today()
        all_days = [today, today]

    start_day = min(all_days)
    end_day = max(all_days)
    if start_day == end_day:
        end_day = date.fromordinal(start_day.toordinal() + 1)
    day_span = max(1, (end_day - start_day).days)
    y_max = nice_maximum(maximum)

    def x_position(day):
        return margin_left + ((day - start_day).days / day_span) * chart_width

    def y_position(count):
        return margin_top + chart_height - (count / y_max) * chart_height

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">GitHub Star History</title>',
        '<desc id="desc">Cumulative GitHub stars over time for the configured repositories.</desc>',
        f'<rect width="{width}" height="{height}" rx="12" fill="{background}" stroke="{border}"/>',
        f'<text x="{margin_left}" y="38" fill="{foreground}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="22" font-weight="600">Star History</text>',
    ]

    legend_x = margin_left
    for index, (repository, history) in enumerate(histories):
        color = COLORS[index % len(COLORS)]
        label = repository.split("/", 1)[1]
        count = history[-1][1] if history else 0
        parts.append(f'<circle cx="{legend_x + 5}" cy="65" r="5" fill="{color}"/>')
        parts.append(
            f'<text x="{legend_x + 17}" y="70" fill="{foreground}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="13">'
            f'{escape(label)} <tspan fill="{muted}">{count:,}</tspan></text>'
        )
        legend_x += max(180, len(label) * 8 + 74)

    for index in range(6):
        value = round(y_max * index / 5)
        y = y_position(value)
        parts.append(f'<line x1="{margin_left}" y1="{y:.2f}" x2="{width - margin_right}" y2="{y:.2f}" stroke="{grid}" stroke-width="1"/>')
        parts.append(
            f'<text x="{margin_left - 12}" y="{y + 4:.2f}" text-anchor="end" fill="{muted}" '
            f'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="12">{format_number(value)}</text>'
        )

    x_ticks = interpolate_ticks(start_day, end_day, 6)
    for index, tick in enumerate(x_ticks):
        x = x_position(tick)
        anchor = "start" if index == 0 else "end" if index == len(x_ticks) - 1 else "middle"
        parts.append(f'<line x1="{x:.2f}" y1="{margin_top}" x2="{x:.2f}" y2="{margin_top + chart_height}" stroke="{grid}" stroke-width="1"/>')
        parts.append(
            f'<text x="{x:.2f}" y="{height - 30}" text-anchor="{anchor}" fill="{muted}" '
            f'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="12">{tick.strftime("%b %Y")}</text>'
        )

    for index, (_, history) in enumerate(histories):
        if not history:
            continue
        color = COLORS[index % len(COLORS)]
        points = [(x_position(day), y_position(count)) for day, count in history]
        if len(points) == 1:
            points.append((points[0][0] + 0.01, points[0][1]))
        path = " ".join(
            ("M" if point_index == 0 else "L") + f" {x:.2f} {y:.2f}"
            for point_index, (x, y) in enumerate(points)
        )
        parts.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>')
        last_x, last_y = points[-1]
        parts.append(f'<circle cx="{last_x:.2f}" cy="{last_y:.2f}" r="4" fill="{background}" stroke="{color}" stroke-width="3"/>')

    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def write_if_changed(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.write_text(content, encoding="utf-8", newline="\n")
    return True


def main():
    args = parse_args()
    repositories = load_repositories(args.config)
    cache = load_cache(args.cache)
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("STAR_HISTORY_TOKEN")
    if not token:
        raise RuntimeError(
            "Missing GitHub token. Set the STAR_HISTORY_TOKEN repository secret "
            "to a token that can read every configured repository."
        )

    cache = update_cache(repositories, cache, token)
    cache_content = json.dumps(cache, ensure_ascii=False, indent=2) + "\n"
    changed = [
        write_if_changed(args.cache, cache_content),
        write_if_changed(args.output, render_svg(repositories, cache)),
        write_if_changed(args.dark_output, render_svg(repositories, cache, dark=True)),
    ]
    print("Updated star history assets" if any(changed) else "Star history assets are current")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, KeyError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
