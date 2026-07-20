#!/usr/bin/env python3
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.generate_used_by import LOCALES, README_FILES, THEMES


REQUIRED_REPOSITORY_COUNT = 9
SAFE_SLUG = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?$")


def fail(message):
    raise SystemExit(message)


def expected_svg_files(config):
    repositories = config.get("repositories")
    if not isinstance(repositories, list) or len(repositories) != REQUIRED_REPOSITORY_COUNT:
        fail(f"expected {REQUIRED_REPOSITORY_COUNT} configured repositories")
    slugs = [item.get("slug") for item in repositories if isinstance(item, dict)]
    if len(slugs) != REQUIRED_REPOSITORY_COUNT or any(
        not isinstance(slug, str) or not SAFE_SLUG.fullmatch(slug) for slug in slugs
    ):
        fail("repository slugs must be non-empty and path-safe")
    if len(slugs) != len(set(slugs)):
        fail("repository slugs must be unique")
    cards = {
        f"cards/{locale}/{slug}-{theme}.svg"
        for locale in LOCALES
        for slug in slugs
        for theme in THEMES
    }
    summaries = {
        f"summary/{locale}-{theme}.svg"
        for locale in LOCALES
        for theme in THEMES
    }
    showcases = {
        f"showcase/{locale}-{theme}.svg"
        for locale in LOCALES
        for theme in THEMES
    }
    return cards | summaries | showcases


def validate_output(output, config, readme_dir):
    output = Path(output)
    readme_dir = Path(readme_dir)
    expected = expected_svg_files(config)
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    required_manifest = {
        "locales": list(LOCALES),
        "themes": list(THEMES),
        "repository_count": REQUIRED_REPOSITORY_COUNT,
        "public_dependents": config.get("public_dependents"),
        "svg_count": len(expected),
        "files": sorted(expected),
    }
    for key, value in required_manifest.items():
        if manifest.get(key) != value:
            fail(f"invalid manifest field {key}")
    manifest_repositories = manifest.get("repositories")
    if not isinstance(manifest_repositories, list) or {
        item.get("slug") for item in manifest_repositories if isinstance(item, dict)
    } != {item["slug"] for item in config["repositories"]}:
        fail("manifest repository list does not match configuration")
    actual = {path.relative_to(output).as_posix() for path in output.rglob("*.svg")}
    if expected != actual:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        fail(f"SVG contract mismatch; missing={missing}, extra={extra}")
    expected_readmes = set(README_FILES.values())
    actual_readmes = {path.name for path in readme_dir.glob("README*.md") if path.is_file()}
    if expected_readmes != actual_readmes:
        fail(
            f"README contract mismatch; missing={sorted(expected_readmes - actual_readmes)}, "
            f"extra={sorted(actual_readmes - expected_readmes)}"
        )
    locale_by_readme = {filename: locale for locale, filename in README_FILES.items()}
    for filename in expected_readmes:
        content = (readme_dir / filename).read_text(encoding="utf-8")
        locale = locale_by_readme[filename]
        if (
            content.count("<picture>") != 1
            or "<table>" in content
            or f"showcase/{locale}-light.svg" not in content
            or f"showcase/{locale}-dark.svg" not in content
        ):
            fail(f"invalid composite showcase reference: {filename}")
    for relative in sorted(actual):
        path = output / relative
        if path.stat().st_size == 0:
            fail(f"empty SVG: {relative}")
        ET.parse(path)
    return len(actual)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=".github/used-by-repositories.json")
    parser.add_argument("--output", default="dist")
    parser.add_argument("--readme-dir", default="dist")
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    count = validate_output(args.output, config, args.readme_dir)
    print(f"validated {count} SVG files")


if __name__ == "__main__":
    main()
