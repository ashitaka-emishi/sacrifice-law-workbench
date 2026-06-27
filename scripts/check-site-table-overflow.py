#!/usr/bin/env python3
"""Check rendered Quarto tables stay inside the main content column."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PAGES = (
    "cases/lincoln/analysis/corpus-analysis.html",
    "publication/public-site-readiness.html",
)
VIEWPORTS = (
    (1366, 900),
    (390, 844),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify wide rendered-site tables scroll within main content "
            "instead of extending under the right page panel."
        )
    )
    parser.add_argument(
        "--site-dir",
        type=Path,
        default=ROOT / "_site",
        help="Rendered Quarto site directory. Run `quarto render` first.",
    )
    parser.add_argument(
        "pages",
        nargs="*",
        default=list(DEFAULT_PAGES),
        help="Rendered HTML pages, relative to --site-dir, to inspect.",
    )
    return parser.parse_args()


def table_measurements(page: Any) -> list[dict[str, Any]]:
    return page.evaluate(
        """() => {
          const main = document.querySelector("main.content");
          if (!main) {
            return [];
          }
          const mainRect = main.getBoundingClientRect();
          const margin = document.querySelector("#quarto-margin-sidebar");
          const marginRect = margin ? margin.getBoundingClientRect() : null;
          return [...main.querySelectorAll("table")].map((table, index) => {
            const rect = table.getBoundingClientRect();
            const style = getComputedStyle(table);
            return {
              index,
              tableRight: rect.right,
              tableWidth: rect.width,
              mainRight: mainRect.right,
              mainWidth: mainRect.width,
              marginLeft: marginRect ? marginRect.left : null,
              overflowX: style.overflowX,
              scrollWidth: table.scrollWidth,
              clientWidth: table.clientWidth,
            };
          });
        }"""
    )


def check_page(browser: Any, html_path: Path) -> list[str]:
    errors: list[str] = []
    for width, height in VIEWPORTS:
        page = browser.new_page(viewport={"width": width, "height": height})
        page.goto(html_path.as_uri(), wait_until="networkidle")
        measurements = table_measurements(page)
        page.close()
        if not measurements:
            errors.append(f"{html_path}: no rendered tables found at {width}x{height}")
            continue
        for table in measurements:
            label = f"{html_path}: table {table['index']} at {width}x{height}"
            if table["overflowX"] not in {"auto", "scroll"}:
                errors.append(f"{label}: overflow-x is `{table['overflowX']}`, expected auto/scroll")
            if table["tableRight"] > table["mainRight"] + 1:
                errors.append(
                    f"{label}: table right edge {table['tableRight']:.1f} exceeds "
                    f"main content right edge {table['mainRight']:.1f}"
                )
            margin_left = table["marginLeft"]
            margin_is_right_panel = margin_left is not None and margin_left > table["mainRight"] + 1
            if margin_is_right_panel and table["tableRight"] > margin_left + 1:
                errors.append(
                    f"{label}: table right edge {table['tableRight']:.1f} extends "
                    f"under right page panel at {margin_left:.1f}"
                )
            if table["scrollWidth"] > table["clientWidth"] and table["clientWidth"] > table["mainWidth"] + 1:
                errors.append(
                    f"{label}: scroll container width {table['clientWidth']:.1f} "
                    f"exceeds main content width {table['mainWidth']:.1f}"
                )
    return errors


def main() -> int:
    args = parse_args()
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "Playwright is required for the rendered-site table overflow check. "
            "Install it with `python3 -m pip install playwright` and "
            "`python3 -m playwright install chromium`.",
            file=sys.stderr,
        )
        return 2

    missing = [page for page in args.pages if not (args.site_dir / page).exists()]
    if missing:
        print(
            "Rendered page(s) missing; run `quarto render` first: "
            + ", ".join(str(args.site_dir / page) for page in missing),
            file=sys.stderr,
        )
        return 2

    errors: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        for page in args.pages:
            errors.extend(check_page(browser, args.site_dir / page))
        browser.close()

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Rendered-site table overflow check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
