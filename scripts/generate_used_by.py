#!/usr/bin/env python3
import argparse
import json
import os
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

if __package__:
    from .collect_used_by import collect_dependents, fetch_all_metadata
else:
    from collect_used_by import collect_dependents, fetch_all_metadata


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
        "stars": "Star 总数",
        "forks": "Fork 总数",
        "top": "Top {count}",
        "notice_label": "自动生成",
        "updated": "更新时间",
        "active": "近30天活跃数",
        "summary_notice": "根据 GitHub 公开数据自动整理，用于展示社区中的相关项目。",
    },
    "en": {
        "heading": "Projects using jmcomic",
        "public": "Public dependents",
        "showing": "Showing",
        "stars": "Total stars",
        "forks": "Total forks",
        "top": "Top {count}",
        "notice_label": "Automated",
        "updated": "Updated",
        "active": "Active in 30 days",
        "summary_notice": "Automatically organized from public GitHub data to showcase related projects in the community.",
    },
    "ja": {
        "heading": "jmcomic を使用しているプロジェクト",
        "public": "公開依存リポジトリ",
        "showing": "表示中",
        "stars": "Star 合計",
        "forks": "Fork 合計",
        "top": "上位 {count} 件",
        "notice_label": "自動生成",
        "updated": "更新日時",
        "active": "過去30日の活動",
        "summary_notice": "GitHub の公開データをもとに自動整理し、コミュニティの関連プロジェクトを紹介しています。",
    },
    "ko": {
        "heading": "jmcomic을 사용하는 프로젝트",
        "public": "공개 종속 저장소",
        "showing": "현재 표시",
        "stars": "Star 합계",
        "forks": "Fork 합계",
        "top": "상위 {count}개",
        "notice_label": "자동 생성",
        "updated": "업데이트",
        "active": "최근 30일 활동",
        "summary_notice": "GitHub 공개 데이터를 바탕으로 자동 정리하여 커뮤니티의 관련 프로젝트를 소개합니다.",
    },
}

SUMMARY_PALETTES = {
    "light": {
        "card": "#ffffff", "border": "#d8dee4", "accent": "#ff8500",
        "title": "#24292f", "notice_bg": "#fff1df", "notice_label": "#b84f00",
        "text": "#57606a",
        "public_bg": "#f5f0ff", "public_border": "#d8c4ff", "public_text": "#6639ba",
        "top_bg": "#edfff4", "top_border": "#9be9b7", "top_text": "#168244",
        "stars_bg": "#fff4e5", "stars_border": "#ffc46b", "stars_text": "#c45d00",
        "forks_bg": "#edf6ff", "forks_border": "#9ecbff", "forks_text": "#0969da",
    },
    "dark": {
        "card": "#161b22", "border": "#30363d", "accent": "#ffb000",
        "title": "#f0f6fc", "notice_bg": "#3d2b00", "notice_label": "#ffb000",
        "text": "#9da7b1",
        "public_bg": "#2d2048", "public_border": "#6e40c9", "public_text": "#d2a8ff",
        "top_bg": "#123621", "top_border": "#238636", "top_text": "#56d364",
        "stars_bg": "#3d2b00", "stars_border": "#9e6a03", "stars_text": "#ffb000",
        "forks_bg": "#102c4c", "forks_border": "#1f6feb", "forks_text": "#58a6ff",
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


def count_active_repositories(dependents, updated_at):
    cutoff = updated_at - timedelta(days=30)
    return sum(cutoff <= datetime.fromisoformat(item["pushed_at"].replace("Z", "+00:00")) <= updated_at
               for item in dependents)


def render_summary(public_dependents, shown_count, total_stars, total_forks, locale, theme,
                   updated_at=None, active_count=None):
    colors = SUMMARY_PALETTES[theme]
    copy = COPY[locale]
    updated_at = updated_at or datetime.now(timezone.utc)
    updated_time = updated_at.astimezone(timezone(timedelta(hours=8)))
    heading = escape(copy["heading"])
    notice_label = escape(copy["notice_label"])
    notice = escape(copy["summary_notice"])
    notice_nodes = "".join(
        f'<text x="46" y="{76 + index * 15}" font-size="10.5" fill="{colors["text"]}">{escape(line)}</text>'
        for index, line in enumerate(wrap_text(copy["summary_notice"], width=66, lines=2))
    )
    extra_colors = {
        "light": (("#eef2ff", "#c7d2fe", "#4f46b8"), ("#fff1f3", "#fecdd6", "#be4264")),
        "dark": (("#202442", "#454c86", "#a5b4fc"), ("#38202d", "#794052", "#f3a6bc")),
    }
    metrics = [
        (copy["public"], str(public_dependents), "public"),
        (copy["showing"], copy["top"].format(count=shown_count), "top"),
        (copy["active"], str(active_count) if active_count is not None else "—", "active"),
        (copy["stars"], str(total_stars), "stars"),
        (copy["forks"], str(total_forks), "forks"),
        (copy["updated"], f"{updated_time:%Y-%m-%d}", "updated"),
    ]
    # Keep the original four metrics in place; prepend the new column.
    metrics = [metrics[index] for index in (2, 0, 1, 5, 3, 4)]
    metric_nodes = []
    for index, (label, value, key) in enumerate(metrics):
        if key in ("active", "updated"):
            bg, border, text = extra_colors[theme][0 if key == "active" else 1]
        else:
            bg, border, text = (colors[f"{key}_{part}"] for part in ("bg", "border", "text"))
        x, y = 468 + index % 3 * 126, 24 + index // 3 * 52
        size = 14 if key == "updated" else 16
        detail = f' data-updated-at="{updated_at.isoformat()}"' if key == "updated" else ""
        tooltip = "UTC+8" if key == "updated" else f"{label}: {value}"
        if key == "active":
            tooltip = f"{label}: {value} / {public_dependents}"
        metric_nodes.append(f'''<g transform="translate({x} {y})"{detail}>
    <title>{escape(tooltip)}</title>
    <rect width="116" height="42" rx="7" fill="{bg}" stroke="{border}"/>
    <text x="10" y="17" font-size="9.5" fill="{text}">{escape(label)}</text>
    <text x="10" y="35" font-size="{size}" font-weight="700" fill="{text}">{escape(value)}</text>
  </g>''')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="860" height="140" viewBox="0 0 860 140" role="img" aria-label="{heading}">
  <desc>{notice}</desc>
  <style>text {{ font-family:{font_family()}; }}</style>
  <rect x="4" y="4" width="852" height="132" rx="8" fill="{colors['card']}" stroke="{colors['border']}"/>
  <rect x="22" y="24" width="5" height="92" rx="2.5" fill="{colors['accent']}"/>
  <text x="46" y="49" font-size="22" font-weight="700" fill="{colors['title']}">{heading}</text>
  {notice_nodes}
  <rect x="46" y="101" width="68" height="21" rx="5" fill="{colors['notice_bg']}"/>
  <text x="57" y="116" font-size="12" font-weight="700" fill="{colors['notice_label']}">{notice_label}</text>
  {''.join(metric_nodes)}
</svg>'''


def render_showcase(repositories, public_dependents, locale, theme, updated_at=None, active_count=None):
    updated_at = updated_at or datetime.now(timezone.utc)
    total_stars = sum(repository["stargazers_count"] for repository in repositories)
    total_forks = sum(repository["forks_count"] for repository in repositories)
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
    summary = ET.fromstring(
        render_summary(public_dependents, len(repositories), total_stars, total_forks, locale, theme, updated_at,
                       active_count)
    )
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


def generate_assets(repositories, public_dependents, output_dir, readme_dir, dependents=None):
    updated_at = datetime.now(timezone.utc)
    active_count = None
    if dependents is not None:
        names = [item["full_name"].lower() for item in dependents]
        if len(names) != public_dependents or len(set(names)) != len(names):
            raise ValueError("full dependents snapshot must match the public count")
        active_count = count_active_repositories(dependents, updated_at)
    output_dir.mkdir(parents=True, exist_ok=True)
    readme_dir.mkdir(parents=True, exist_ok=True)
    repositories = sorted(repositories, key=lambda item: item["stargazers_count"], reverse=True)
    total_stars = sum(repository["stargazers_count"] for repository in repositories)
    total_forks = sum(repository["forks_count"] for repository in repositories)
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
                render_summary(
                    public_dependents, len(repositories), total_stars, total_forks, locale, theme, updated_at,
                    active_count
                ),
                encoding="utf-8",
            )
            expected_files.append(relative.as_posix())
        showcase_dir = output_dir / "showcase"
        showcase_dir.mkdir(parents=True, exist_ok=True)
        for theme in THEMES:
            relative = Path("showcase") / f"{locale}-{theme}.svg"
            (output_dir / relative).write_text(
                render_showcase(repositories, public_dependents, locale, theme, updated_at, active_count), encoding="utf-8"
            )
            expected_files.append(relative.as_posix())
        (readme_dir / README_FILES[locale]).write_text(
            render_readme(repositories, locale, public_dependents), encoding="utf-8"
        )
    manifest = {
        "updated_at": updated_at.isoformat(),
        "active_repositories_30d": active_count,
        "locales": list(LOCALES),
        "themes": list(THEMES),
        "repository_count": len(repositories),
        "public_dependents": public_dependents,
        "total_stars": total_stars,
        "total_forks": total_forks,
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


def build_repositories(metadata):
    ranked = sorted(metadata, key=lambda item: (-item["stargazers_count"], item["full_name"].lower()))
    output = []
    for api in ranked[:9]:
        owner, repo = api["full_name"].split("/")
        description = api.get("description") or api["full_name"]
        output.append({
            "owner": owner,
            "repo": repo,
            "slug": f"{owner}--{repo}",
            "descriptions": {locale: description for locale in LOCALES},
            "stargazers_count": api["stargazers_count"],
            "forks_count": api["forks_count"],
            "pushed_at": api["pushed_at"],
            "html_url": api["html_url"],
        })
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="dist")
    parser.add_argument("--readme-dir", default="generated-readmes")
    args = parser.parse_args()
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    names = collect_dependents()
    dependents = fetch_all_metadata(names, fetch_repository, token)
    repositories = build_repositories(dependents)
    generate_assets(repositories, len(dependents), Path(args.output), Path(args.readme_dir), dependents)


if __name__ == "__main__":
    main()
