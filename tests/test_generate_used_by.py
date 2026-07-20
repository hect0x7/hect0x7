import json
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import scripts.generate_used_by as generator
from scripts.generate_used_by import (
    LOCALES,
    THEMES,
    build_repositories,
    format_date,
    generate_assets,
    render_card,
    render_readme,
    render_summary,
)
from scripts.validate_used_by_output import validate_output


def repository(index=0):
    return {
        "owner": f"owner{index}",
        "repo": f"repo{index}",
        "slug": f"owner{index}--repo{index}",
        "descriptions": {
            "zh-CN": f"中文描述 {index}",
            "en": f"English description {index}",
            "ja": f"日本語の説明 {index}",
            "ko": f"한국어 설명 {index}",
        },
        "stargazers_count": 1234 - index,
        "forks_count": 86 - index,
        "pushed_at": "2026-07-20T08:30:00Z",
        "html_url": f"https://github.com/owner{index}/repo{index}",
    }


class CardRenderingTest(unittest.TestCase):
    def test_light_and_dark_use_distinct_metric_palettes_and_vector_icons(self):
        light = render_card(repository(), "zh-CN", "light")
        dark = render_card(repository(), "zh-CN", "dark")

        self.assertIn("#ff8500", light)
        self.assertIn("#0969da", light)
        self.assertIn("#ffb000", dark)
        self.assertIn("#58a6ff", dark)
        self.assertIn('data-icon="star"', light)
        self.assertIn('data-icon="fork"', light)
        self.assertIn('data-icon="activity"', light)
        self.assertIn('data-icon="activity" transform="translate(194 107)"', light)
        self.assertIn('stroke-width="1.7"', light)
        self.assertEqual(1, light.count("<rect"))
        self.assertNotIn(">Stars<", light)
        self.assertNotIn(">Forks<", light)
        self.assertNotIn("⑂", light)

    def test_card_uses_compact_three_column_width(self):
        card = render_card(repository(), "zh-CN", "light")

        self.assertIn('width="280" height="136"', card)
        self.assertIn('viewBox="0 0 280 136"', card)

    def test_compact_card_truncates_long_repository_name(self):
        item = repository()
        item["owner"] = "ClovertaTheTrilobita"
        item["repo"] = "SanYeCao-Nonebot-with-a-very-long-suffix"

        card = render_card(item, "en", "light")
        root = ET.fromstring(card)
        title = next(node for node in root.findall("{http://www.w3.org/2000/svg}text") if node.get("class") == "title")

        self.assertTrue(title.text.endswith("…"))
        self.assertNotIn("SanYeCao-Nonebot-with-a-very-long-suffix", title.text)
        self.assertIn("SanYeCao-Nonebot-with-a-very-long-suffix", root.get("aria-label"))

    def test_compact_card_leaves_room_for_wide_latin_title_glyphs(self):
        item = repository()
        item["owner"] = "GEMILUXVII"
        item["repo"] = "astrbot_plugin_jm_cosmos"

        card = render_card(item, "en", "light")
        root = ET.fromstring(card)
        title = next(node for node in root.findall("{http://www.w3.org/2000/svg}text") if node.get("class") == "title")

        self.assertEqual("GEMILUXVII / astrbot_plugin_jm_…", title.text)

    def test_card_localizes_description_and_absolute_date(self):
        expected_dates = {
            "zh-CN": "2026-07-20",
            "en": "Jul 20, 2026",
            "ja": "2026年7月20日",
            "ko": "2026년 7월 20일",
        }

        for locale, expected_date in expected_dates.items():
            with self.subTest(locale=locale):
                card = render_card(repository(), locale, "light")
                self.assertIn(repository()["descriptions"][locale], card)
                self.assertIn(expected_date, card)
                self.assertEqual(expected_date, format_date("2026-07-20T08:30:00Z", locale))

    def test_card_escapes_repository_text(self):
        item = repository()
        item["descriptions"]["en"] = "A <safe> & useful project"
        card = render_card(item, "en", "light")
        self.assertIn("A &lt;safe&gt; &amp; useful project", card)


class ReadmeRenderingTest(unittest.TestCase):
    def test_chinese_readme_references_one_composite_showcase(self):
        readme = render_readme([repository(i) for i in range(9)], "zh-CN", 109)

        self.assertIn("使用 jmcomic 的项目", readme)
        self.assertNotIn("> **自动生成**", readme)
        self.assertNotIn("<table>", readme)
        self.assertEqual(1, readme.count("<picture>"))
        self.assertIn("showcase/zh-CN-dark.svg", readme)
        self.assertIn("showcase/zh-CN-light.svg", readme)
        self.assertIn("README-en.md", readme)
        self.assertIn("README-jp.md", readme)
        self.assertIn("README-kr.md", readme)

    def test_all_readmes_use_localized_showcases(self):
        repositories = [repository(i) for i in range(9)]
        expected = {
            "zh-CN": "使用 jmcomic 的项目",
            "en": "Projects using jmcomic",
            "ja": "jmcomic を使用しているプロジェクト",
            "ko": "jmcomic을 사용하는 프로젝트",
        }
        for locale, heading in expected.items():
            with self.subTest(locale=locale):
                readme = render_readme(repositories, locale, 109)
                self.assertIn(heading, readme)
                self.assertIn(f"showcase/{locale}-dark.svg", readme)
                self.assertIn(f"showcase/{locale}-light.svg", readme)

    def test_summary_embeds_large_localized_notice_and_exact_public_count(self):
        expected_notices = {
            "zh-CN": "根据 GitHub 公开数据自动整理，用于展示社区中的相关项目。",
            "en": "Automatically organized from public GitHub data to showcase related projects in the community.",
            "ja": "GitHub の公開データをもとに自動整理し、コミュニティの関連プロジェクトを紹介しています。",
            "ko": "GitHub 공개 데이터를 바탕으로 자동 정리하여 커뮤니티의 관련 프로젝트를 소개합니다.",
        }
        for locale, notice in expected_notices.items():
            with self.subTest(locale=locale):
                summary = render_summary(109, 9, locale, "light")
                self.assertIn('width="860" height="140"', summary)
                self.assertIn(notice, summary)
                self.assertIn("#ff8500", summary)
                self.assertIn(">109<", summary)
                self.assertNotIn("约 109", summary)

    def test_showcase_embeds_summary_and_nine_cards_in_three_columns(self):
        self.assertTrue(hasattr(generator, "render_showcase"), "render_showcase is missing")
        showcase = generator.render_showcase([repository(i) for i in range(9)], 109, "zh-CN", "light")
        root = ET.fromstring(showcase)
        nested = root.findall("{http://www.w3.org/2000/svg}svg")

        self.assertEqual("860", root.get("width"))
        self.assertEqual("584", root.get("height"))
        self.assertEqual(10, len(nested))
        self.assertEqual(("0", "0"), (nested[0].get("x"), nested[0].get("y")))
        self.assertEqual(("0", "152"), (nested[1].get("x"), nested[1].get("y")))
        self.assertEqual(("290", "152"), (nested[2].get("x"), nested[2].get("y")))
        self.assertEqual(("580", "152"), (nested[3].get("x"), nested[3].get("y")))
        self.assertEqual(("0", "440"), (nested[7].get("x"), nested[7].get("y")))
        self.assertEqual(("580", "440"), (nested[9].get("x"), nested[9].get("y")))
        self.assertIn("使用 jmcomic 的项目", showcase)
        self.assertIn("owner8 / repo8", showcase)


class AssetGenerationTest(unittest.TestCase):
    def test_generates_exact_manifest_for_9_repositories(self):
        repositories = [repository(i) for i in range(9)]
        with tempfile.TemporaryDirectory() as output_dir, tempfile.TemporaryDirectory() as readme_dir:
            manifest = generate_assets(repositories, 109, Path(output_dir), Path(readme_dir))

            self.assertEqual(LOCALES, tuple(manifest["locales"]))
            self.assertEqual(THEMES, tuple(manifest["themes"]))
            self.assertEqual(88, manifest["svg_count"])
            self.assertEqual(88, len(list(Path(output_dir).rglob("*.svg"))))
            self.assertEqual(8, len(list((Path(output_dir) / "showcase").glob("*.svg"))))
            self.assertEqual(4, len(list(Path(readme_dir).glob("README*.md"))))
            saved = json.loads((Path(output_dir) / "manifest.json").read_text())
            self.assertEqual(manifest, saved)

    def test_validator_rejects_a_missing_svg(self):
        repositories = [repository(i) for i in range(9)]
        with tempfile.TemporaryDirectory() as output_dir, tempfile.TemporaryDirectory() as readme_dir:
            output = Path(output_dir)
            readmes = Path(readme_dir)
            generate_assets(repositories, 109, output, readmes)
            config = {"public_dependents": 109, "repositories": repositories}
            self.assertEqual(88, validate_output(output, config, readmes))
            next(output.rglob("*.svg")).unlink()
            with self.assertRaises(SystemExit):
                validate_output(output, config, readmes)

    def test_validator_rejects_a_self_consistent_incomplete_manifest(self):
        repositories = [repository(i) for i in range(9)]
        with tempfile.TemporaryDirectory() as output_dir, tempfile.TemporaryDirectory() as readme_dir:
            output = Path(output_dir)
            readmes = Path(readme_dir)
            generate_assets(repositories, 109, output, readmes)
            config = {"public_dependents": 109, "repositories": repositories}
            manifest_path = output / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["files"] = manifest["files"][:1]
            manifest["svg_count"] = 1
            manifest_path.write_text(json.dumps(manifest))

            with self.assertRaises(SystemExit):
                validate_output(output, config, readmes)

    def test_validator_rejects_missing_readme_and_unsafe_or_duplicate_slugs(self):
        repositories = [repository(i) for i in range(9)]
        with tempfile.TemporaryDirectory() as output_dir, tempfile.TemporaryDirectory() as readme_dir:
            output = Path(output_dir)
            readmes = Path(readme_dir)
            generate_assets(repositories, 109, output, readmes)
            config = {"public_dependents": 109, "repositories": repositories}
            (readmes / "README-kr.md").unlink()
            with self.assertRaises(SystemExit):
                validate_output(output, config, readmes)

    def test_validator_cli_runs_from_repository_root(self):
        repositories = [repository(i) for i in range(9)]
        with tempfile.TemporaryDirectory() as output_dir, tempfile.TemporaryDirectory() as readme_dir, tempfile.TemporaryDirectory() as config_dir:
            output = Path(output_dir)
            readmes = Path(readme_dir)
            config = {"public_dependents": 109, "repositories": repositories}
            config_file = Path(config_dir) / "config.json"
            config_file.write_text(json.dumps(config), encoding="utf-8")
            generate_assets(repositories, 109, output, readmes)

            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/validate_used_by_output.py",
                    "--config",
                    str(config_file),
                    "--output",
                    output_dir,
                    "--readme-dir",
                    readme_dir,
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn("validated 88 SVG files", result.stdout)

            config["repositories"][1]["slug"] = config["repositories"][0]["slug"]
            with self.assertRaises(SystemExit):
                validate_output(output, config, readmes)

            config["repositories"][1]["slug"] = "../unsafe"
            with self.assertRaises(SystemExit):
                validate_output(output, config, readmes)

    def test_repository_config_has_no_custom_descriptions(self):
        config = json.loads(Path(".github/used-by-repositories.json").read_text())
        self.assertEqual(9, len(config["repositories"]))
        for item in config["repositories"]:
            self.assertNotIn("descriptions", item)

    def test_build_repositories_uses_original_api_description_for_every_locale(self):
        config = {
            "repositories": [{
                "owner": "owner0",
                "repo": "repo0",
                "slug": "owner0--repo0",
                "descriptions": {locale: "Custom generated copy" for locale in LOCALES},
            }]
        }
        metadata = [{
            "full_name": "owner0/repo0",
            "description": "Original repository description",
            "stargazers_count": 12,
            "forks_count": 3,
            "pushed_at": "2026-07-20T08:30:00Z",
            "html_url": "https://github.com/owner0/repo0",
        }]

        built = build_repositories(config, metadata=metadata)

        self.assertEqual(
            {locale: "Original repository description" for locale in LOCALES},
            built[0]["descriptions"],
        )

    def test_workflow_uses_local_generator_and_publishes_only_used_by(self):
        workflow = Path(".github/workflows/used_by.yml").read_text()
        self.assertIn("python scripts/generate_used_by.py", workflow)
        self.assertIn("python scripts/validate_used_by_output.py", workflow)
        self.assertIn("--readme-dir dist", workflow)
        self.assertIn("HEAD:used-by", workflow)
        self.assertNotIn("github-readme-stats-action", workflow)
        self.assertNotIn("schedule:", workflow)
        self.assertNotIn("workflow_dispatch:", workflow)


if __name__ == "__main__":
    unittest.main()
