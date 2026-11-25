#!/usr/bin/env python3
"""Freeze animated github-profile-3d-contrib rainbow SVG into a zero-animation static SVG."""

from __future__ import annotations

import argparse
import re
import xml.etree.ElementTree as ET
from pathlib import Path

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)

ANIMATION_RULE_RE = re.compile(
    r"\.(rb-l\d+-(?:top|left|right))\s*\{\s*animation:\s*([^\s;]+)\s+([0-9.]+)s[^}]*\}"
)
KEYFRAMES_RE = re.compile(
    r"@keyframes\s+(rb-l\d+-(?:top|left|right))\s*\{((?:[^{}]*\{[^{}]*\})*[^{}]*)\}"
)
STOP_RE = re.compile(
    r"([0-9.]+)%\s*\{\s*fill\s*:\s*rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)\s*;?\s*\}"
)
DELAY_RE = re.compile(r"animation-delay\s*:\s*([+-]?[0-9.]+)\s*s")
DATE_RANGE_RE = re.compile(r"^\s*\d{4}-\d{2}-\d{2}\s*/\s*\d{4}-\d{2}-\d{2}\s*$")


def _parse_rainbow_keyframes(css: str) -> tuple[dict[str, float], dict[str, list[tuple[float, tuple[int, int, int]]]]]:
    durations: dict[str, float] = {}
    for cls_name, _anim_name, dur_s in ANIMATION_RULE_RE.findall(css):
        durations[cls_name] = float(dur_s)

    keyframes: dict[str, list[tuple[float, tuple[int, int, int]]]] = {}
    for name, body in KEYFRAMES_RE.findall(css):
        stops: list[tuple[float, tuple[int, int, int]]] = []
        for pct_s, r_s, g_s, b_s in STOP_RE.findall(body):
            stops.append((float(pct_s) / 100.0, (int(r_s), int(g_s), int(b_s))))
        if stops:
            stops.sort(key=lambda item: item[0])
            keyframes[name] = stops
    return durations, keyframes


def _interpolate_rgb(stops: list[tuple[float, tuple[int, int, int]]], phase: float) -> str:
    p = phase % 1.0
    for idx in range(len(stops) - 1):
        p0, c0 = stops[idx]
        p1, c1 = stops[idx + 1]
        if p0 <= p <= p1:
            span = p1 - p0
            t = 0.0 if span <= 0 else (p - p0) / span
            r = round(c0[0] + (c1[0] - c0[0]) * t)
            g = round(c0[1] + (c1[1] - c0[1]) * t)
            b = round(c0[2] + (c1[2] - c0[2]) * t)
            return f"rgb({r},{g},{b})"
    c = stops[-1][1]
    return f"rgb({c[0]},{c[1]},{c[2]})"


def _strip_rainbow_css(css: str) -> str:
    cleaned = ANIMATION_RULE_RE.sub("", css)
    cleaned = KEYFRAMES_RE.sub("", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned


def _local_tag(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def freeze_rainbow_svg(svg_text: str) -> str:
    root = ET.fromstring(svg_text)

    durations: dict[str, float] = {}
    keyframes: dict[str, list[tuple[float, tuple[int, int, int]]]] = {}

    for elem in root.iter():
        if _local_tag(elem.tag) == "style" and elem.text:
            d, k = _parse_rainbow_keyframes(elem.text)
            durations.update(d)
            keyframes.update(k)
            elem.text = _strip_rainbow_css(elem.text)

    for parent in root.iter():
        # Apply final value of SMIL animations if present, then remove SMIL nodes.
        to_remove = []
        for child in list(parent):
            tag = _local_tag(child.tag)
            if tag == "text" and DATE_RANGE_RE.match("".join(child.itertext())):
                to_remove.append(child)
                continue
            if tag in ("animate", "animateTransform", "animateMotion", "set"):
                attr_name = child.attrib.get("attributeName")
                values = child.attrib.get("values")
                if attr_name and values:
                    final_val = values.split(";")[-1].strip()
                    if tag == "animateTransform":
                        t_type = child.attrib.get("type", "")
                        if t_type and not final_val.startswith(t_type):
                            parent.attrib[attr_name] = f"{t_type}({final_val})"
                        else:
                            parent.attrib[attr_name] = final_val
                    else:
                        parent.attrib[attr_name] = final_val
                to_remove.append(child)
        for child in to_remove:
            parent.remove(child)

        # Freeze rainbow class + animation-delay into static fill.
        cls = parent.attrib.get("class", "")
        classes = cls.split()
        rb_cls = next((c for c in classes if c in keyframes), None)
        if rb_cls:
            style_attr = parent.attrib.get("style", "")
            delay_m = DELAY_RE.search(style_attr)
            delay_s = float(delay_m.group(1)) if delay_m else 0.0
            dur_s = durations.get(rb_cls, 10.0)
            phase = ((-delay_s) % dur_s) / dur_s if dur_s > 0 else 0.0
            parent.attrib["fill"] = _interpolate_rgb(keyframes[rb_cls], phase)

            remaining_classes = [c for c in classes if c != rb_cls]
            if remaining_classes:
                parent.attrib["class"] = " ".join(remaining_classes)
            else:
                parent.attrib.pop("class", None)

            new_style = DELAY_RE.sub("", style_attr).strip(" ;")
            if new_style:
                parent.attrib["style"] = new_style
            else:
                parent.attrib.pop("style", None)

    result = ET.tostring(root, encoding="unicode")
    ET.fromstring(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze animated 3D contrib rainbow SVG to static SVG.")
    parser.add_argument("--input", required=True, help="Source animated SVG path")
    parser.add_argument("--output", required=True, help="Destination static SVG path")
    args = parser.parse_args()

    src = Path(args.input).read_text(encoding="utf-8")
    frozen = freeze_rainbow_svg(src)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(frozen, encoding="utf-8")
    print(f"Froze 3D rainbow SVG: {len(src)} -> {len(frozen)} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
