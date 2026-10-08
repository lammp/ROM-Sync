#!/usr/bin/env python3
"""Measure WCAG contrast over a stylesheet's declared tokens and its literals.

Why this exists: the interface's accessibility claims were, until October 2026,
unmeasured. A ratio is arithmetic, not an opinion, so it belongs in a tool that
anyone can rerun rather than in a sentence somebody wrote once.

Usage:
    python _tools/contrast.py <stylesheet.css> [--pairs pairs.txt] [--strict]

With no --pairs it reports the declared custom properties, every colour literal
in the rule bodies, and which literals merely restate a token. With --pairs it
measures each foreground/background pair and, for a failure, computes the
nearest correction by lightness.

pairs.txt columns, tab separated; a line whose first non-space
character is '#' is a comment, so a hex value is never mistaken for one:
    label <TAB> foreground <TAB> background <TAB> target

Foreground and background accept a hex colour or a '--token' name resolved from
the stylesheet. Target is 4.5 for text or 3.0 for non-text and large text.

Exit code 1 with --strict when any pair fails.
"""
from __future__ import annotations

import argparse
import colorsys
import re
import sys
from pathlib import Path

HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
DECL = re.compile(r"(--[a-z0-9-]+)\s*:\s*([^;}]+)")


def parse_hex(value: str) -> tuple[int, int, int]:
    h = value.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) not in (6, 8):
        raise ValueError(f"not a hex colour: {value!r}")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _channel(c: int) -> float:
    s = c / 255
    return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4


def luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = (_channel(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(fg: str, bg: str) -> float:
    a, b = luminance(parse_hex(fg)), luminance(parse_hex(bg))
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def nudge(colour: str, against: str, target: float) -> str | None:
    """Walk lightness away from the background until the target is met."""
    r, g, b = parse_hex(colour)
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    lighten = luminance(parse_hex(against)) < 0.18
    for step in range(0, 1001):
        nl = min(1.0, l + step / 1000) if lighten else max(0.0, l - step / 1000)
        rr, gg, bb = colorsys.hls_to_rgb(h, nl, s)
        cand = "#%02x%02x%02x" % (round(rr * 255), round(gg * 255), round(bb * 255))
        if ratio(cand, against) >= target:
            return cand
    return None


def read_tokens(css: str) -> dict[str, str]:
    root = re.search(r":root\s*\{(.*?)\}", css, re.S)
    body = root.group(1) if root else css
    return {m.group(1): m.group(2).strip() for m in DECL.finditer(body)}


def read_literals(css: str, tokens: dict[str, str]) -> tuple[dict[str, int], list[str]]:
    body = re.sub(r":root\s*\{.*?\}", "", css, flags=re.S)
    counts: dict[str, int] = {}
    for m in HEX.finditer(body):
        v = m.group(0).lower()
        counts[v] = counts.get(v, 0) + 1
    named = {v.lower() for v in tokens.values() if v.startswith("#")}
    restated = sorted(v for v in counts if v in named)
    return counts, restated


def resolve(value: str, tokens: dict[str, str], label: str) -> str:
    """A token name resolves against the stylesheet; anything else is a literal."""
    v = value.strip()
    if not v.startswith("--"):
        return v
    if v not in tokens:
        raise SystemExit(
            f"pair {label!r} names {v}, which the stylesheet does not declare. "
            f"Declared: {', '.join(sorted(tokens)) or 'none'}"
        )
    return tokens[v]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stylesheet", type=Path)
    ap.add_argument("--pairs", type=Path)
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    css = args.stylesheet.read_text(encoding="utf-8")
    tokens = read_tokens(css)
    counts, restated = read_literals(css, tokens)

    print(f"{args.stylesheet}: {len(tokens)} declared tokens, "
          f"{len(counts)} distinct literals over {sum(counts.values())} occurrences, "
          f"{css.count('var(--')} var() references")
    print()
    print("declared tokens")
    for k, v in tokens.items():
        print(f"  {k:28} {v}")
    print()
    if restated:
        print("literals that restate a declared token (no design intent, fix in place)")
        for v in restated:
            owner = next(k for k, t in tokens.items() if t.lower() == v)
            print(f"  {v}  x{counts[v]}  is {owner}")
        print()
    untokenised = sorted(v for v in counts if v not in restated)
    print(f"untokenised colours ({len(untokenised)})")
    for v in untokenised:
        print(f"  {v}  x{counts[v]}")

    if not args.pairs:
        return 0

    print()
    print(f"{'pair':34} {'fg':9} {'bg':9} {'ratio':>6} {'need':>5}  verdict  correction")
    print("-" * 100)
    failures = 0
    for line in args.pairs.read_text(encoding="utf-8").splitlines():
        # only a leading '#' is a comment: '#ffffff' is a value
        if line.lstrip().startswith("#"):
            continue
        line = line.strip()
        if not line:
            continue
        label, fg_raw, bg_raw, target_raw = (c.strip() for c in line.split("\t"))
        fg = resolve(fg_raw, tokens, label)
        bg = resolve(bg_raw, tokens, label)
        target = float(target_raw)
        r = ratio(fg, bg)
        ok = r >= target
        if not ok:
            failures += 1
        fix = "" if ok else (nudge(fg, bg, target) or "no solution at this hue")
        print(f"{label:34} {fg:9} {bg:9} {r:6.2f} {target:5.1f}  "
              f"{'PASS' if ok else 'FAIL':7}  {fix}")
    print("-" * 100)
    print(f"{failures} failing pair(s)")
    return 1 if failures and args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
