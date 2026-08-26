"""Build the two SVG charts shown in the repository README."""

from __future__ import annotations

import csv
from pathlib import Path
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "processed"
ASSETS = ROOT / "assets"

NAVY = "#0B2545"
BLUE = "#2E74B5"
GREEN = "#0B7A53"
RED = "#B42318"
GRAY = "#667085"
GRID = "#E4E7EC"


def read_csv(name: str) -> list[dict[str, str]]:
    with (PROCESSED / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def money(value: float) -> str:
    amount = f"${abs(value) / 1000:,.1f}K"
    return amount if value >= 0 else f"({amount})"


def svg_text(x: float, y: float, text: str, **attrs: object) -> str:
    options = {"x": x, "y": y, "font-family": "Arial, sans-serif", **attrs}
    rendered = " ".join(f'{key.replace("_", "-")}="{value}"' for key, value in options.items())
    return f"<text {rendered}>{escape(text)}</text>"


def brand_chart() -> str:
    rows = sorted(read_csv("brand_profitability.csv"), key=lambda r: float(r["contribution_margin"]))
    width, height = 980, 500
    left, top, plot_width, bar_height, gap = 180, 110, 690, 72, 30
    maximum = max(float(row["contribution_margin"]) for row in rows)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Q2 contribution margin by brand</title>',
        '<desc id="desc">Peak Fuel contributed 22.0 thousand dollars, GlowTheory 20.5 thousand, and PawHaus 8.7 thousand.</desc>',
        '<rect width="100%" height="100%" fill="white"/>',
        svg_text(40, 52, "Q2 contribution margin by brand", fill=NAVY, font_size=26, font_weight="700"),
        svg_text(40, 80, "Contribution margin and margin rate", fill=GRAY, font_size=15),
    ]
    for index, row in enumerate(rows):
        y = top + index * (bar_height + gap)
        value = float(row["contribution_margin"])
        rate = float(row["contribution_margin_pct"])
        bar_width = value / maximum * plot_width
        parts.extend([
            svg_text(left - 18, y + 43, row["brand"], fill=NAVY, font_size=17, text_anchor="end"),
            f'<rect x="{left}" y="{y}" width="{bar_width:.1f}" height="{bar_height}" rx="3" fill="{BLUE}"/>',
            svg_text(left + 16, y + 44, f"{rate:.1%} margin", fill="white", font_size=15, font_weight="700"),
            svg_text(left + bar_width + 14, y + 44, money(value), fill=NAVY, font_size=17, font_weight="700"),
        ])
    parts.append("</svg>")
    return "\n".join(parts)


def platform_cost_chart() -> str:
    wanted = {
        "Contribution margin": "Contribution",
        "Advertising cost": "Ad spend",
        "FBA storage fee": "Storage",
        "Subscription fee": "Subscription",
        "Adjustments / other income": "Adjustments",
        "Result after platform costs": "Final result",
    }
    rows = [row for row in read_csv("profit_bridge.csv") if row["line_item"] in wanted]
    width, height = 1080, 560
    left, top, plot_width, plot_height = 90, 125, 920, 320
    baseline = top + plot_height * 0.55
    max_abs = max(abs(float(row["signed_amount"])) for row in rows)
    slot = plot_width / len(rows)
    bar_width = 86
    scale = (plot_height * 0.48) / max_abs
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Contribution margin and platform costs</title>',
    '<desc id="desc">Contribution margin was positive 51.2 thousand dollars. Advertising, storage, subscription, and adjustments resulted in a 5.5 thousand dollar loss after platform costs.</desc>',
        '<rect width="100%" height="100%" fill="white"/>',
        svg_text(40, 50, "Contribution margin is positive; platform costs make the quarter negative", fill=NAVY, font_size=24, font_weight="700"),
        svg_text(40, 80, "Platform costs cannot be reliably assigned to SKU from the supplied file", fill=GRAY, font_size=15),
        f'<line x1="{left}" y1="{baseline:.1f}" x2="{left + plot_width}" y2="{baseline:.1f}" stroke="{GRID}" stroke-width="2"/>',
    ]
    for index, row in enumerate(rows):
        label = wanted[row["line_item"]]
        value = float(row["signed_amount"])
        x = left + slot * index + (slot - bar_width) / 2
        bar_height = max(abs(value) * scale, 2)
        y = baseline - bar_height if value >= 0 else baseline
        color = GREEN if value >= 0 else RED
        value_y = y - 10 if value >= 0 else y + bar_height + 22
        parts.extend([
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width}" height="{bar_height:.1f}" rx="3" fill="{color}"/>',
            svg_text(x + bar_width / 2, value_y, money(value), fill=NAVY, font_size=14, font_weight="700", text_anchor="middle"),
            svg_text(x + bar_width / 2, height - 24, label, fill=NAVY, font_size=13, text_anchor="middle"),
        ])
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    (ASSETS / "brand-contribution-margin.svg").write_text(brand_chart(), encoding="utf-8")
    (ASSETS / "contribution-margin-and-platform-costs.svg").write_text(platform_cost_chart(), encoding="utf-8")


if __name__ == "__main__":
    main()
