import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from scripts.generate_profile_card import (
    ProfileMetrics,
    format_compact_count,
    render_profile_card,
    write_profile_cards,
)


class GenerateProfileCardTests(unittest.TestCase):
    def test_format_compact_count(self) -> None:
        self.assertEqual(format_compact_count(0), "0")
        self.assertEqual(format_compact_count(24), "24")
        self.assertEqual(format_compact_count(637), "637")
        self.assertEqual(format_compact_count(999, plus=True), "999")
        self.assertEqual(format_compact_count(1000, plus=True), "1.0k+")
        self.assertEqual(format_compact_count(15580, plus=True), "15.5k+")
        self.assertEqual(format_compact_count(15600, plus=False), "15.6k")

    def test_render_profile_card_valid_svg_and_content(self) -> None:
        metrics = ProfileMetrics(
            username="hect0x7",
            total_stars=15620,
            followers=637,
            public_repos=24,
        )
        for theme in ("light", "dark"):
            svg = render_profile_card(metrics, theme)
            root = ET.fromstring(svg)
            self.assertTrue(root.tag.endswith("svg"))
            self.assertIn("Hello, I'm hect0x7", svg)
            self.assertIn("Open-source maker focused on", svg)
            self.assertIn("Building projects I enjoy using, and sharing them openly.", svg)
            self.assertIn("15.6k+", svg)
            self.assertIn("637", svg)
            self.assertIn("24", svg)
            for skill in (
                "Product",
                "System Design",
                "AI Agents",
                "Full-Stack",
                "Data &amp; DB",
                "Networking",
                "Reverse Eng.",
                "Automation",
            ):
                self.assertIn(skill, svg)
            self.assertNotIn("Rust", svg)
            self.assertNotIn("Python", svg)
            self.assertNotIn("Reach me", svg)

    def test_write_profile_cards(self) -> None:
        metrics = ProfileMetrics("hect0x7", 15590, 640, 24)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            write_profile_cards(metrics, out)
            for name in ("profile-card-light.svg", "profile-card-dark.svg"):
                content = (out / name).read_text(encoding="utf-8")
                ET.fromstring(content)
                self.assertIn("15.5k+", content)


if __name__ == "__main__":
    unittest.main()
