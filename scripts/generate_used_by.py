#!/usr/bin/env python3
import argparse
import json
import os
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from html import escape
from pathlib import Path


LOCALES = ("zh-CN", "en", "ja", "ko")
THEMES = ("light", "dark")
README_FILES = {
    "zh-CN": "README.md",
    "en": "README-en.md",
    "ja": "README-jp.md",
    "ko": "README-kr.md",
}
RAW_BASE = "https://raw.githubusercontent.com/hect0x7/hect0x7/used-by"
SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)

COPY = {
    "zh-CN": {
        "heading": "使用 jmcomic 的项目",
        "public": "公开依赖项目",
        "showing": "当前展示",
        "top": "Top {count}",
        "notice_label": "自动生成",
        "summary_notice": "根据 GitHub 公开数据自动整理，用于展示社区中的相关项目。",
    },
    "en": {
        "heading": "Projects using jmcomic",
        "public": "Public dependents",
        "showing": "Showing",
        "top": "Top {count}",
        "notice_label": "Automated",
        "summary_notice": "Automatically organized from public GitHub data to showcase related projects in the community.",
    },
    "ja": {
        "heading": "jmcomic を使用しているプロジェクト",
        "public": "公開依存リポジトリ",
        "showing": "表示中",
        "top": "上位 {count} 件",
        "notice_label": "自動生成",
        "summary_notice": "GitHub の公開データをもとに自動整理し、コミュニティの関連プロジェクトを紹介しています。",
    },
    "ko": {
        "heading": "jmcomic을 사용하는 프로젝트",
        "public": "공개 종속 저장소",
        "showing": "현재 표시",
        "top": "상위 {count}개",
        "notice_label": "자동 생성",
        "summary_notice": "GitHub 공개 데이터를 바탕으로 자동 정리하여 커뮤니티의 관련 프로젝트를 소개합니다.",
    },
}

SUMMARY_PALETTES = {
    "light": {
        "card": "#ffffff", "border": "#d8dee4", "accent": "#ff8500",
        "title": "#24292f", "notice_bg": "#fff1df", "notice_label": "#b84f00",
        "text": "#57606a", "metric_bg": "#f6f8fa", "metric_border": "#d0d7de",
        "metric_text": "#24292f", "top_bg": "#fff7ed", "top_border": "#ffbf78",
    },
    "dark": {
        "card": "#161b22", "border": "#30363d", "accent": "#ffb000",
        "title": "#f0f6fc", "notice_bg": "#3d2b00", "notice_label": "#ffb000",
        "text": "#9da7b1", "metric_bg": "#21262d", "metric_border": "#30363d",
        "metric_text": "#f0f6fc", "top_bg": "#292300", "top_border": "#806700",
    },
}

PALETTES = {
    "light": {
        "canvas": "#fffefe",
        "card": "#fffefe",
        "border": "#e4e2e2",
        "title": "#2f80ed",
        "text": "#434d58",
        "muted": "#6e7781",
        "divider": "#e4e2e2",
        "star": "#ff8500",
        "fork": "#0969da",
    },
    "dark": {
        "canvas": "#0d1117",
        "card": "#161b22",
        "border": "#30363d",
        "title": "#58a6ff",
        "text": "#c9d1d9",
        "muted": "#8b949e",
        "divider": "#30363d",
        "star": "#ffb000",
        "fork": "#58a6ff",
    },
}


def format_date(value, locale):
    date = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if locale == "zh-CN":
        return f"{date:%Y-%m-%d}"
    if locale == "en":
        months = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
        return f"{months[date.month - 1]} {date.day}, {date.year}"
    if locale == "ja":
        return f"{date.year}年{date.month}月{date.day}日"
    if locale == "ko":
        return f"{date.year}년 {date.month}월 {date.day}일"
    raise ValueError(f"unsupported locale: {locale}")


def compact_count(value):
    if value < 1000:
        return str(value)
    amount = value / 1000
    return f"{amount:.1f}".rstrip("0").rstrip(".") + "k"


def display_width(text):
    return sum(2 if unicodedata.east_asian_width(char) in "WFA" else 1 for char in text)


def truncate(text, width):
    result = []
    used = 0
    for char in text:
        char_width = 2 if unicodedata.east_asian_width(char) in "WFA" else 1
        if used + char_width > width - 1:
            return "".join(result).rstrip() + "…"
        result.append(char)
        used += char_width
    return "".join(result)


def wrap_text(text, width=58, lines=2):
    text = " ".join((text or "").split())
    if not text:
        return [""]
    output = []
    remaining = text
    while remaining and len(output) < lines:
        if display_width(remaining) <= width:
            output.append(remaining)
            remaining = ""
            break
        current = []
        used = 0
        last_space = -1
        for index, char in enumerate(remaining):
            char_width = 2 if unicodedata.east_asian_width(char) in "WFA" else 1
            if used + char_width > width:
                break
            current.append(char)
            used += char_width
            if char.isspace():
                last_space = index
        cut = last_space + 1 if last_space >= 0 else len(current)
        output.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()
    if remaining:
        output[-1] = truncate(output[-1] + " " + remaining, width)
    return output


def font_family():
    return "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans CJK SC','Noto Sans',sans-serif"


def render_card(repository, locale, theme):
    if locale not in LOCALES or theme not in THEMES:
        raise ValueError("unsupported locale or theme")
    colors = PALETTES[theme]
    full_name = f"{repository['owner']} / {repository['repo']}"
    name = escape(full_name)
    display_name = escape(truncate(full_name, 32))
    description = repository["descriptions"].get(locale) or repository["descriptions"]["en"]
    description_lines = [escape(line) for line in wrap_text(description, width=38)]
    date = escape(format_date(repository["pushed_at"], locale))
    date_width = sum(10 if unicodedata.east_asian_width(char) in "WFA" else 5.5 for char in date)
    date_icon_x = max(146, round(266 - date_width - 17))
    stars = compact_count(repository["stargazers_count"])
    forks = compact_count(repository["forks_count"])
    desc_nodes = "".join(
        f'<text x="14" y="{50 + index * 17}" class="description">{line}</text>'
        for index, line in enumerate(description_lines)
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="280" height="136" viewBox="0 0 280 136" role="img" aria-label="{name}">
  <style>
    text {{ font-family:{font_family()}; }}
    .title {{ font-size:15px;font-weight:600;fill:{colors['title']}; }}
    .description {{ font-size:12px;fill:{colors['text']}; }}
    .metric-value {{ font-size:11px;font-weight:600;fill:{colors['text']}; }}
    .updated {{ font-size:10px;fill:{colors['muted']};letter-spacing:.1px; }}
  </style>
  <rect x="4" y="4" width="272" height="128" rx="10" fill="{colors['card']}" stroke="{colors['border']}"/>
  <text x="14" y="29" class="title">{display_name}</text>
  {desc_nodes}
  <line x1="14" y1="91" x2="266" y2="91" stroke="{colors['divider']}"/>
  <g transform="translate(14 105)">
    <path data-icon="star" d="M8 .75l2.16 4.37 4.82.7-3.49 3.4.82 4.8L8 11.75l-4.31 2.27.82-4.8-3.49-3.4 4.82-.7L8 .75z" fill="{colors['star']}"/>
    <text x="22" y="12" class="metric-value">{stars}</text>
  </g>
  <g transform="translate(79 105)">
    <g data-icon="fork" fill="none" stroke="{colors['fork']}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
      <circle cx="4" cy="3" r="2"/><circle cx="12" cy="3" r="2"/><circle cx="8" cy="13" r="2"/>
      <path d="M4 5v1c0 2.2 1.8 4 4 4v1M12 5v1c0 2.2-1.8 4-4 4"/>
    </g>
    <text x="22" y="12" class="metric-value">{forks}</text>
  </g>
  <g data-icon="activity" transform="translate({date_icon_x} 107)" fill="none" stroke="{colors['muted']}" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="6" cy="6" r="5"/>
    <path d="M6 3v3l2 1.5"/>
  </g>
  <text x="266" y="117" text-anchor="end" class="updated">{date}</text>
</svg>'''


def render_summary(public_dependents, shown_count, locale, theme):
    colors = SUMMARY_PALETTES[theme]
    copy = COPY[locale]
    heading = escape(copy["heading"])
    notice_label = escape(copy["notice_label"])
    notice = escape(copy["summary_notice"])
    public_label = escape(copy["public"])
    showing_label = escape(copy["showing"])
    public_value = str(public_dependents)
    showing_value = escape(copy["top"].format(count=shown_count))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="860" height="140" viewBox="0 0 860 140" role="img" aria-label="{heading}">
  <style>text {{ font-family:{font_family()}; }}</style>
  <rect x="4" y="4" width="852" height="132" rx="8" fill="{colors['card']}" stroke="{colors['border']}"/>
  <rect x="22" y="24" width="5" height="92" rx="2.5" fill="{colors['accent']}"/>
  <text x="46" y="53" font-size="27" font-weight="700" fill="{colors['title']}">{heading}</text>
  <rect x="46" y="72" width="68" height="24" rx="5" fill="{colors['notice_bg']}"/>
  <text x="57" y="89" font-size="12" font-weight="700" fill="{colors['notice_label']}">{notice_label}</text>
  <text x="126" y="89" font-size="10.5" fill="{colors['text']}">{notice}</text>
  <g transform="translate(594 30)"><rect width="110" height="76" rx="7" fill="{colors['metric_bg']}" stroke="{colors['metric_border']}"/><text x="12" y="27" font-size="11" fill="{colors['text']}">{public_label}</text><text x="12" y="57" font-size="23" font-weight="700" fill="{colors['metric_text']}">{public_value}</text></g>
  <g transform="translate(716 30)"><rect width="120" height="76" rx="7" fill="{colors['top_bg']}" stroke="{colors['top_border']}"/><text x="12" y="27" font-size="11" fill="{colors['notice_label']}">{showing_label}</text><text x="12" y="57" font-size="23" font-weight="700" fill="{colors['accent']}">{showing_value}</text></g>
</svg>'''


def render_showcase(repositories, public_dependents, locale, theme):
    root = ET.Element(
        f"{{{SVG_NS}}}svg",
        {
            "width": "860",
            "height": "584",
            "viewBox": "0 0 860 584",
            "role": "img",
            "aria-label": COPY[locale]["heading"],
        },
    )
    summary = ET.fromstring(render_summary(public_dependents, len(repositories), locale, theme))
    summary.set("x", "0")
    summary.set("y", "0")
    root.append(summary)
    for index, repository in enumerate(repositories):
        card = ET.fromstring(render_card(repository, locale, theme))
        card.set("x", str((index % 3) * 290))
        card.set("y", str(152 + (index // 3) * 144))
        root.append(card)
    return ET.tostring(root, encoding="unicode")


def language_navigation(locale):
    labels = (("zh-CN", "简体中文"), ("en", "English"), ("ja", "日本語"), ("ko", "한국어"))
    parts = []
    for code, label in labels:
        parts.append(f"<strong>{label}</strong>" if code == locale else f'<a href="./{README_FILES[code]}">{label}</a>')
    return " •\n  ".join(parts)


def render_readme(repositories, locale, public_dependents):
    copy = COPY[locale]
    lines = [
        '<p align="center">',
        f"  {language_navigation(locale)}",
        "</p>",
        "",
        '<picture>',
        f'  <source media="(prefers-color-scheme: dark)" srcset="{RAW_BASE}/showcase/{locale}-dark.svg">',
        f'  <source media="(prefers-color-scheme: light)" srcset="{RAW_BASE}/showcase/{locale}-light.svg">',
        f'  <img width="100%" alt="{copy["heading"]}" src="{RAW_BASE}/showcase/{locale}-light.svg">',
        "</picture>",
    ]
    lines.append("")
    return "\n".join(lines)


def generate_assets(repositories, public_dependents, output_dir, readme_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    readme_dir.mkdir(parents=True, exist_ok=True)
    repositories = sorted(repositories, key=lambda item: item["stargazers_count"], reverse=True)
    expected_files = []
    for locale in LOCALES:
        card_dir = output_dir / "cards" / locale
        card_dir.mkdir(parents=True, exist_ok=True)
        for repository in repositories:
            for theme in THEMES:
                relative = Path("cards") / locale / f"{repository['slug']}-{theme}.svg"
                (output_dir / relative).write_text(render_card(repository, locale, theme), encoding="utf-8")
                expected_files.append(relative.as_posix())
        summary_dir = output_dir / "summary"
        summary_dir.mkdir(parents=True, exist_ok=True)
        for theme in THEMES:
            relative = Path("summary") / f"{locale}-{theme}.svg"
            (output_dir / relative).write_text(
                render_summary(public_dependents, len(repositories), locale, theme), encoding="utf-8"
            )
            expected_files.append(relative.as_posix())
        showcase_dir = output_dir / "showcase"
        showcase_dir.mkdir(parents=True, exist_ok=True)
        for theme in THEMES:
            relative = Path("showcase") / f"{locale}-{theme}.svg"
            (output_dir / relative).write_text(
                render_showcase(repositories, public_dependents, locale, theme), encoding="utf-8"
            )
            expected_files.append(relative.as_posix())
        (readme_dir / README_FILES[locale]).write_text(
            render_readme(repositories, locale, public_dependents), encoding="utf-8"
        )
    manifest = {
        "locales": list(LOCALES),
        "themes": list(THEMES),
        "repository_count": len(repositories),
        "public_dependents": public_dependents,
        "svg_count": len(expected_files),
        "files": sorted(expected_files),
        "repositories": [
            {
                "owner": item["owner"],
                "repo": item["repo"],
                "slug": item["slug"],
                "stars": item["stargazers_count"],
                "forks": item["forks_count"],
                "pushed_at": item["pushed_at"],
            }
            for item in repositories
        ],
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def fetch_repository(owner, repo, token=None):
    request = urllib.request.Request(
        f"https://api.github.com/repos/{owner}/{repo}",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "hect0x7-used-by-generator"},
    )
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def build_repositories(config, metadata=None, token=None):
    metadata_by_name = {
        item["full_name"].lower(): item for item in (metadata or [])
    }
    output = []
    for item in config["repositories"]:
        key = f"{item['owner']}/{item['repo']}".lower()
        api = metadata_by_name.get(key) or fetch_repository(item["owner"], item["repo"], token)
        description = api.get("description") or f"{item['owner']}/{item['repo']}"
        descriptions = {locale: description for locale in LOCALES}
        output.append({
            **item,
            "descriptions": descriptions,
            "stargazers_count": api["stargazers_count"],
            "forks_count": api["forks_count"],
            "pushed_at": api["pushed_at"],
            "html_url": api["html_url"],
        })
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=".github/used-by-repositories.json")
    parser.add_argument("--output", default="dist")
    parser.add_argument("--readme-dir", default="generated-readmes")
    parser.add_argument("--metadata")
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    metadata = json.loads(Path(args.metadata).read_text(encoding="utf-8")) if args.metadata else None
    repositories = build_repositories(config, metadata, os.environ.get("GITHUB_TOKEN"))
    generate_assets(repositories, config["public_dependents"], Path(args.output), Path(args.readme_dir))


if __name__ == "__main__":
    main()
