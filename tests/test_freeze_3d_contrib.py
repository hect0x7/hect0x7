import unittest
import xml.etree.ElementTree as ET

from scripts.freeze_3d_contrib import freeze_rainbow_svg

SAMPLE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
  <style>
    .fill-bg { fill: #00000f; }
    .rb-l1-top{animation:rb-l1-top 10s linear infinite;}
    @keyframes rb-l1-top{0.00%{fill:rgb(100, 0, 0)}50.00%{fill:rgb(0, 100, 0)}100.00%{fill:rgb(100, 0, 0)}}
  </style>
  <text x="1260" y="20" text-anchor="end" class="fill-weak">2025-11-23 / 2026-11-25</text>
  <g transform="translate(10 20)">
    <animateTransform attributeName="transform" type="translate" values="10 30;10 20" dur="3s" repeatCount="1"/>
    <rect width="18" height="2.6" class="rb-l1-top" style="animation-delay:-5.000s">
      <animate attributeName="height" values="2.6;12.5" dur="3s" repeatCount="1"/>
    </rect>
    <rect width="18" height="2.6" class="rb-l1-top" style="animation-delay:-2.500s"/>
  </g>
</svg>"""


class Freeze3DContribTests(unittest.TestCase):
    def test_freeze_removes_animations_and_preserves_colors_and_heights(self) -> None:
        frozen = freeze_rainbow_svg(SAMPLE_SVG)
        self.assertNotIn("<animate", frozen)
        self.assertNotIn("@keyframes", frozen)
        self.assertNotIn("animation-delay", frozen)
        self.assertNotIn("rb-l1-top", frozen)
        self.assertNotIn("2025-11-23 / 2026-11-25", frozen)

        root = ET.fromstring(frozen)
        ns = {"svg": "http://www.w3.org/2000/svg"}
        g = root.find(".//svg:g", ns)
        self.assertIsNotNone(g)
        self.assertEqual(g.attrib["transform"], "translate(10 20)")

        rects = root.findall(".//svg:rect", ns)
        self.assertEqual(len(rects), 2)
        self.assertEqual(rects[0].attrib["height"], "12.5")
        self.assertEqual(rects[0].attrib["fill"], "rgb(0,100,0)")
        self.assertEqual(rects[1].attrib["fill"], "rgb(50,50,0)")


if __name__ == "__main__":
    unittest.main()
