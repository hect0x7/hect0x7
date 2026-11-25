#!/usr/bin/env python3
"""Generate dark and light Bento profile cards from live GitHub user metrics."""

from __future__ import annotations

import argparse
import json
import os
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from html import escape
from pathlib import Path

API_BASE = "https://api.github.com"

SKILL_SPECS = (
    (
        "Python",
        "c1",
        '<path d="M5 6.5C5 4.8 6.2 4 8 4h1.5C11 4 12 4.9 12 6.3V8H7.2C5.8 8 5 8.8 5 10.2V11H4.2C3 11 2.2 10 2.2 8.4V7.6C2.2 6.4 3 5.5 4.2 5.5H5" stroke="COLOR" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M13 11.5c0 1.7-1.2 2.5-3 2.5H8.5C7 14 6 13.1 6 11.7V10h4.8c1.4 0 2.2-.8 2.2-2.2V7h.8c1.2 0 2 1 2 2.6v.8c0 1.2-.8 2.1-2 2.1H13" stroke="COLOR" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>',
        True,
    ),
    (
        "Full-Stack",
        "c2",
        '<path d="M9 3.5 15 6.5 9 9.5 3 6.5 9 3.5Z" stroke="COLOR" stroke-width="1.45" stroke-linejoin="round"/><path d="M3 9.8 9 12.8 15 9.8" stroke="COLOR" stroke-width="1.45" stroke-linecap="round" stroke-linejoin="round"/><path d="M3 12.8 9 15.8 15 12.8" stroke="COLOR" stroke-width="1.45" stroke-linecap="round" stroke-linejoin="round"/>',
        False,
    ),
    (
        "AI",
        "c3",
        '<path d="M9 2.8 10.7 7.3 15.2 9 10.7 10.7 9 15.2 7.3 10.7 2.8 9 7.3 7.3 9 2.8Z" stroke="COLOR" stroke-width="1.45" stroke-linejoin="round"/>',
        False,
    ),
    (
        "Databases",
        "c5",
        '<ellipse cx="9" cy="5" rx="5.2" ry="2" stroke="COLOR" stroke-width="1.45"/><path d="M3.8 5v4c0 1.1 2.3 2 5.2 2s5.2-.9 5.2-2V5" stroke="COLOR" stroke-width="1.45"/><path d="M3.8 9v4c0 1.1 2.3 2 5.2 2s5.2-.9 5.2-2V9" stroke="COLOR" stroke-width="1.45"/>',
        False,
    ),
    (
        "Networking",
        "c4",
        '<circle cx="9" cy="9" r="6" stroke="COLOR" stroke-width="1.45"/><path d="M3.3 9h11.4M9 3c1.8 1.6 2.7 3.6 2.7 6S10.8 13.4 9 15C7.2 13.4 6.3 11.4 6.3 9S7.2 4.6 9 3Z" stroke="COLOR" stroke-width="1.35"/>',
        False,
    ),
    (
        "Reverse Eng.",
        "c6",
        '<path d="M6.2 5.5 3 9l3.2 3.5M11.8 5.5 15 9l-3.2 3.5M10.2 4.2 7.8 13.8" stroke="COLOR" stroke-width="1.45" stroke-linecap="round" stroke-linejoin="round"/>',
        False,
    ),
    (
        "Web Scraping",
        "c7",
        '<circle cx="9" cy="9" r="2.2" stroke="COLOR" stroke-width="1.45"/><path d="M9 3v3.8M9 11.2V15M3 9h3.8M11.2 9H15M4.8 4.8l2.6 2.6M10.6 10.6l2.6 2.6M13.2 4.8l-2.6 2.6M7.4 10.6l-2.6 2.6" stroke="COLOR" stroke-width="1.35" stroke-linecap="round"/>',
        False,
    ),
    (
        "Automation",
        "c8",
        '<path d="M10.2 2.8 4.5 10h4.2l-.9 5.2 5.7-7.2H9.3l.9-5.2Z" stroke="COLOR" stroke-width="1.45" stroke-linejoin="round"/>',
        False,
    ),
)


@dataclass(frozen=True)
class ProfileMetrics:
    username: str
    total_stars: int
    followers: int
    public_repos: int


def format_compact_count(value: int, *, plus: bool = False) -> str:
    if value < 0:
        raise ValueError(f"count must be non-negative, got {value}")
    if value < 1000:
        return str(value)
    tenths = value // 100
    whole, frac = divmod(tenths, 10)
    suffix = "k+" if plus else "k"
    return f"{whole}.{frac}{suffix}"


def _api_get_json(url: str, token: str | None) -> object:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "hect0x7-profile-card-generator",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_profile_metrics(username: str, token: str | None = None) -> ProfileMetrics:
    user_data = _api_get_json(f"{API_BASE}/users/{username}", token)
    if not isinstance(user_data, dict):
        raise RuntimeError(f"Unexpected user payload for {username}")

    total_stars = 0
    page = 1
    while True:
        repos_url = f"{API_BASE}/users/{username}/repos?per_page=100&type=owner&page={page}"
        repos = _api_get_json(repos_url, token)
        if not isinstance(repos, list):
            raise RuntimeError(f"Unexpected repos payload on page {page} for {username}")
        if not repos:
            break
        for repo in repos:
            total_stars += int(repo["stargazers_count"])
        if len(repos) < 100:
            break
        page += 1

    return ProfileMetrics(
        username=username,
        total_stars=total_stars,
        followers=int(user_data["followers"]),
        public_repos=int(user_data["public_repos"]),
    )


def _theme_palette(theme: str) -> dict[str, str]:
    if theme == "dark":
        return {
            "sfx": "D",
            "outer_bg": "#0d1117",
            "tile_bg": "#151624",
            "tile_hi": "#1a182e",
            "tile_bd": "#2b2948",
            "sub_bg": "#141522",
            "sub_hi": "#1d1933",
            "icon_bg": "#1e1e36",
            "icon_bd": "#323056",
            "fg": "#f0f6fc",
            "sub": "#c9d1d9",
            "muted": "#8b949e",
            "c1": "#fe428e",
            "c2": "#a9fef7",
            "c3": "#f8d847",
            "c4": "#7ee787",
            "c5": "#58a6ff",
            "c6": "#d2a8ff",
            "c7": "#ffa657",
            "c8": "#79c0ff",
        }
    if theme == "light":
        return {
            "sfx": "L",
            "outer_bg": "#ffffff",
            "tile_bg": "#f6f8fa",
            "tile_hi": "#f0f6fc",
            "tile_bd": "#d0d7de",
            "sub_bg": "#f6f8fa",
            "sub_hi": "#eef5fc",
            "icon_bg": "#ffffff",
            "icon_bd": "#d8dee4",
            "fg": "#1f2328",
            "sub": "#3b434b",
            "muted": "#57606a",
            "c1": "#0969da",
            "c2": "#0f766e",
            "c3": "#8250df",
            "c4": "#1a7f37",
            "c5": "#0550ae",
            "c6": "#8250df",
            "c7": "#bc4c00",
            "c8": "#0969da",
        }
    raise ValueError(f"Unsupported theme: {theme}")


def render_profile_card(metrics: ProfileMetrics, theme: str) -> str:
    p = _theme_palette(theme)
    sfx = p["sfx"]
    stars_label = format_compact_count(metrics.total_stars, plus=True)
    followers_label = format_compact_count(metrics.followers)
    repos_label = format_compact_count(metrics.public_repos)

    tiles = []
    for idx, (label, color_key, icon_paths, is_hi) in enumerate(SKILL_SPECS):
        col = idx % 4
        row = idx // 4
        x = 468 + col * 110
        y = row * 88
        col_hex = p[color_key]
        bg = p["sub_hi"] if is_hi else p["sub_bg"]
        bd = col_hex if is_hi else p["tile_bd"]
        bd_op = "0.75" if is_hi else "1"
        tcol = col_hex if is_hi else p["fg"]
        tiles.append(
            f'''  <g transform="translate({x}, {y})">
    <rect x="0.5" y="0.5" width="101" height="77" rx="11" fill="{bg}" stroke="{bd}" stroke-opacity="{bd_op}"/>
    <rect x="33" y="11" width="36" height="36" rx="9" fill="{p['icon_bg']}" stroke="{p['icon_bd']}"/>
    <g transform="translate(41, 19) scale(1.12)">{icon_paths.replace("COLOR", col_hex)}</g>
    <text x="51" y="64" text-anchor="middle" class="sans" font-size="12" font-weight="600" fill="{tcol}">{escape(label)}</text>
  </g>'''
        )

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="166" viewBox="0 0 900 166" fill="none" role="img" aria-label="{escape(metrics.username)} GitHub Profile Card">
  <defs>
    <linearGradient id="hybGrad{sfx}" x1="0" y1="0" x2="456" y2="0" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="{p['c1']}"/>
      <stop offset="55%" stop-color="{p['c3']}"/>
      <stop offset="100%" stop-color="{p['c2']}"/>
    </linearGradient>
    <clipPath id="hybClip{sfx}"><rect x="0.5" y="0.5" width="455" height="105" rx="12"/></clipPath>
  </defs>
  <style>
    .sans {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; }}
    .mono {{ font-family: 'JetBrains Mono', 'Fira Code', 'SFMono-Regular', Consolas, monospace; }}
  </style>
  <rect width="900" height="166" fill="{p['outer_bg']}"/>

  <!-- Left Top: Intro Card (456 x 106) -->
  <g clip-path="url(#hybClip{sfx})">
    <rect x="0" y="0" width="456" height="106" fill="{p['tile_hi']}"/>
    <rect x="0" y="0" width="456" height="2.5" fill="url(#hybGrad{sfx})"/>
    <text x="20" y="34" class="sans" font-size="22" font-weight="800" fill="{p['fg']}" letter-spacing="-0.4">Hello, I'm {escape(metrics.username)} 👋</text>
    <text x="20" y="63" class="sans" font-size="13" fill="{p['sub']}">Love writing <tspan fill="{p['c1']}" font-weight="700">Python</tspan> &amp; pursuing <tspan fill="{p['c2']}" font-weight="600">excellent system design</tspan>.</text>
    <text x="20" y="86" class="sans" font-size="12.5" fill="{p['muted']}">Building interesting open-source tools whenever I'm free.</text>
  </g>
  <rect x="0.5" y="0.5" width="455" height="105" rx="12" fill="none" stroke="{p['tile_bd']}"/>

  <!-- Left Bottom: 3-Column KPI Bar (456 x 50) -->
  <rect x="0.5" y="116.5" width="455" height="49" rx="12" fill="{p['tile_bg']}" stroke="{p['tile_bd']}"/>
  <text x="76" y="138" text-anchor="middle" class="mono" font-size="16" font-weight="800" fill="{p['c1']}">{escape(stars_label)}</text>
  <text x="76" y="154" text-anchor="middle" class="mono" font-size="9" fill="{p['muted']}" letter-spacing="0.6">TOTAL STARS</text>

  <line x1="152" y1="127" x2="152" y2="155" stroke="{p['tile_bd']}"/>
  <text x="228" y="138" text-anchor="middle" class="mono" font-size="16" font-weight="800" fill="{p['c3']}">{escape(followers_label)}</text>
  <text x="228" y="154" text-anchor="middle" class="mono" font-size="9" fill="{p['muted']}" letter-spacing="0.6">FOLLOWERS</text>

  <line x1="304" y1="127" x2="304" y2="155" stroke="{p['tile_bd']}"/>
  <text x="380" y="138" text-anchor="middle" class="mono" font-size="16" font-weight="800" fill="{p['c2']}">{escape(repos_label)}</text>
  <text x="380" y="154" text-anchor="middle" class="mono" font-size="9" fill="{p['muted']}" letter-spacing="0.6">PUBLIC REPOS</text>

  <!-- Right: 4x2 Mini Bento Skill Tiles -->
{chr(10).join(tiles)}
</svg>
'''
    ET.fromstring(svg)
    return svg


def write_profile_cards(metrics: ProfileMetrics, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for theme in ("light", "dark"):
        svg = render_profile_card(metrics, theme)
        (output_dir / f"profile-card-{theme}.svg").write_text(svg, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate light/dark GitHub profile Bento cards.")
    parser.add_argument("--username", required=True, help="GitHub username")
    parser.add_argument("--output-dir", default="profile-card", help="Directory for output SVGs")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN") or None
    metrics = fetch_profile_metrics(args.username, token=token)
    write_profile_cards(metrics, Path(args.output_dir))
    print(
        f"Generated profile cards for {metrics.username}: "
        f"stars={metrics.total_stars}, followers={metrics.followers}, repos={metrics.public_repos}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
