#!/usr/bin/env python3
"""Render the Thai per-fold results figure for the Experiment Results slide.

Reads the accepted figure_period_performance.csv, keeps only the four OOF
periods (2022H1-2023H2), recomputes each percent deviance reduction of the
selected HGB model against the segment_mean_k365 baseline from the stored
mean deviances, reconciles it with the stored relative_deviance_reduction,
and plots it as-is (no refit). Outputs a PNG, an SVG with editable text, and
a metadata JSON recording the source hash, every input deviance, and every
plotted percentage.

The caller is expected to set a writable MPLCONFIGDIR before running.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from render_thai_calibration import (  # noqa: E402  (also selects the Agg backend)
    DPI,
    FIG_SIZE_IN,
    FOOTER_GREY,
    GRID_GREY,
    NAVY,
    SPINE_GREY,
    TEXT_GREY,
    configure_style,
    locate_thai_font,
    png_size,
    register_font,
    sha256_file,
)

import matplotlib  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ft2font import FT2Font  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = (
    REPO_ROOT / "output" / "spatial-model-results" / "v3-evaluation-017-002" / "figure_period_performance.csv"
)
DEFAULT_OUTPUT_DIR = REPO_ROOT / "output" / "presentation-th"

EXPECTED_HEADER = [
    "unit",
    "scope",
    "group",
    "baseline_mean_deviance",
    "selected_mean_deviance",
    "relative_deviance_reduction",
]
UNITS = ["daily", "6h"]
PLOT_SCOPE = "oof"
PERIODS = ["2022H1", "2022H2", "2023H1", "2023H2"]
# Method names per the accepted evaluation (reconciliation.csv); the CSV itself has no method column.
SELECTED_METHOD = "HGB (selected)"
BASELINE_METHOD = "segment_mean_k365"
GAIN_TOLERANCE = 1e-12
Y_HEADROOM = 1.22

DARK_TEAL = "#0B6E70"
BLUE = "#2563EB"
UNIT_COLORS = {"daily": DARK_TEAL, "6h": BLUE}

TITLE = "HGB ให้ผลดีกว่า Baseline ครบทั้ง 4 รอบ"
SUBTITLE = "ผล OOF ปี 2022–2023 • เปรียบเทียบแยกรายวันและช่วงละ 6 ชั่วโมง"
PANEL_TITLES = {"daily": "รายวัน", "6h": "ช่วงละ 6 ชั่วโมง"}
PERIOD_LABELS = {
    "2022H1": "ต้นปี\n2022",
    "2022H2": "ปลายปี\n2022",
    "2023H1": "ต้นปี\n2023",
    "2023H2": "ปลายปี\n2023",
}
Y_LABEL = "ลด Poisson deviance จาก Baseline (%)"
FOOTER = "แท่งสูง = ลดความคลาดเคลื่อนได้มาก • เป็นผลรายรอบ ไม่ใช่เปอร์เซ็นต์ความแม่นยำ"

ALL_TEXT = [TITLE, SUBTITLE, Y_LABEL, FOOTER]
ALL_TEXT += list(PANEL_TITLES.values()) + list(PERIOD_LABELS.values())


class DataError(ValueError):
    pass


# ---------------------------------------------------------------- data


def _parse_float(raw: str, field: str, row_number: int) -> float:
    try:
        value = float(raw)
    except ValueError as exc:
        raise DataError(f"row {row_number}: {field}={raw!r} is not numeric") from exc
    if not math.isfinite(value):
        raise DataError(f"row {row_number}: {field}={raw!r} is not finite")
    return value


def load_rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader, None)
        if header != EXPECTED_HEADER:
            raise DataError(f"unexpected header: {header}")
        rows = []
        for row_number, record in enumerate(reader, start=2):
            if not record:
                continue
            if len(record) != len(EXPECTED_HEADER):
                raise DataError(f"row {row_number}: expected {len(EXPECTED_HEADER)} fields, got {len(record)}")
            raw = dict(zip(EXPECTED_HEADER, record))
            row = {
                "csv_row_number": row_number,
                "csv_text": {field: raw[field] for field in EXPECTED_HEADER[3:]},
                "unit": raw["unit"],
                "scope": raw["scope"],
                "group": raw["group"],
            }
            for field in EXPECTED_HEADER[3:]:
                row[field] = _parse_float(raw[field], field, row_number)
            rows.append(row)
    return rows


def select_and_reconcile(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Return (plotted points in UNITS x PERIODS order, excluded rows)."""
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        key = (row["unit"], row["scope"], row["group"])
        if key in seen:
            raise DataError(f"row {row['csv_row_number']}: duplicate unit/scope/group {key}")
        seen.add(key)

    by_key: dict[tuple[str, str], dict] = {}
    excluded = []
    for row in rows:
        num = row["csv_row_number"]
        if row["unit"] not in UNITS:
            raise DataError(f"row {num}: unexpected unit {row['unit']!r}")
        if row["scope"] != PLOT_SCOPE:
            excluded.append(
                {"csv_row_number": num, "unit": row["unit"], "scope": row["scope"], "group": row["group"],
                 "reason": "not OOF (diagnostic / 2024+ rows are not plotted)"}
            )
            continue
        if row["group"] not in PERIODS:
            raise DataError(f"row {num}: unexpected OOF group {row['group']!r} (expected {PERIODS})")
        by_key[(row["unit"], row["group"])] = row

    expected = [(unit, period) for unit in UNITS for period in PERIODS]
    missing = [key for key in expected if key not in by_key]
    if missing:
        raise DataError(f"missing unit/period groups: {missing}")
    if len(by_key) != 8:
        raise DataError(f"expected 8 unit/period groups, found {len(by_key)}")

    points = []
    for unit, period in expected:
        row = by_key[(unit, period)]
        num = row["csv_row_number"]
        baseline = row["baseline_mean_deviance"]
        selected = row["selected_mean_deviance"]
        if baseline <= 0 or selected <= 0:
            raise DataError(f"row {num}: deviances must be positive")
        gain = (baseline - selected) / baseline
        stored = row["relative_deviance_reduction"]
        diff = abs(gain - stored)
        if diff > GAIN_TOLERANCE:
            raise DataError(
                f"row {num}: recomputed reduction {gain!r} differs from stored {stored!r} by {diff:.3e}"
            )
        if gain <= 0:
            # The title claims HGB beats Baseline in every round; refuse to render otherwise.
            raise DataError(f"row {num}: {unit}/{period} reduction {gain!r} is not positive")
        percent = gain * 100.0
        points.append(
            {
                "csv_row_number": num,
                "unit": unit,
                "scope": row["scope"],
                "period": period,
                "period_label_th": PERIOD_LABELS[period].replace("\n", " "),
                "baseline_mean_deviance": baseline,
                "selected_mean_deviance": selected,
                "baseline_mean_deviance_csv_text": row["csv_text"]["baseline_mean_deviance"],
                "selected_mean_deviance_csv_text": row["csv_text"]["selected_mean_deviance"],
                "stored_relative_deviance_reduction": stored,
                "recomputed_relative_deviance_reduction": gain,
                "reconciliation_abs_diff": diff,
                "plotted_percent": percent,
                "annotation": f"{percent:+.2f}%",
            }
        )
    return points, excluded


def check_font_covers(path: Path) -> None:
    needed = {ord(ch) for text in ALL_TEXT for ch in text if 0x0E00 <= ord(ch) <= 0x0E7F}
    missing = needed - set(FT2Font(str(path)).get_charmap())
    if missing:
        raise SystemExit(f"font {path} lacks Thai glyphs: {sorted(chr(c) for c in missing)}")


# ---------------------------------------------------------------- plotting


def draw_figure(points: list[dict]):
    fig = plt.figure(figsize=FIG_SIZE_IN, dpi=DPI)

    fig.text(0.5, 0.955, TITLE, ha="center", va="top", fontsize=32, fontweight="bold", color=NAVY)
    fig.text(0.5, 0.875, SUBTITLE, ha="center", va="top", fontsize=19, color=TEXT_GREY)

    bottom, height = 0.20, 0.55
    width, gap, left0 = 0.37, 0.12, 0.085
    axes = {
        "daily": fig.add_axes([left0, bottom, width, height]),
        "6h": fig.add_axes([left0 + width + gap, bottom, width, height]),
    }

    for unit, ax in axes.items():
        series = [p for p in points if p["unit"] == unit]
        xs = list(range(len(series)))
        heights = [p["plotted_percent"] for p in series]
        bars = ax.bar(xs, heights, width=0.62, color=UNIT_COLORS[unit], zorder=3)
        drawn = [float(patch.get_height()) for patch in bars.patches]
        if drawn != heights:
            raise RuntimeError(f"{unit}: drawn bar heights differ from computed percentages")
        for patch, point in zip(bars.patches, series):
            point["drawn_bar_height"] = float(patch.get_height())
            ax.annotate(
                point["annotation"],
                xy=(patch.get_x() + patch.get_width() / 2, patch.get_height()),
                xytext=(0, 8),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=19,
                fontweight="bold",
                color=NAVY,
            )

        ax.set_ylim(0, max(heights) * Y_HEADROOM)
        ax.set_xlim(-0.6, len(series) - 0.4)
        ax.set_xticks(xs)
        ax.set_xticklabels([PERIOD_LABELS[p["period"]] for p in series], linespacing=1.3)
        ax.set_title(PANEL_TITLES[unit], fontsize=24, fontweight="bold", color=UNIT_COLORS[unit], pad=16)
        ax.set_ylabel(Y_LABEL, fontsize=16, color=TEXT_GREY, labelpad=10)
        ax.yaxis.set_major_formatter(lambda v, _pos: f"{v:g}")
        ax.tick_params(axis="x", labelsize=17, colors=TEXT_GREY, length=0, pad=10)
        ax.tick_params(axis="y", labelsize=15, colors=TEXT_GREY, length=5)
        ax.grid(True, axis="y", color=GRID_GREY, linewidth=0.9)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(SPINE_GREY)

    fig.text(0.5, 0.035, FOOTER, ha="center", va="center", fontsize=16, color=FOOTER_GREY)
    return fig, axes


def check_text_layout(fig, axes: dict) -> list[str]:
    """Return problems: text outside the canvas or bar annotations outside their panel."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    fig_box = fig.bbox
    problems = []
    texts = list(fig.texts)
    for ax in fig.axes:
        texts += [ax.title, ax.xaxis.label, ax.yaxis.label] + list(ax.texts)
        texts += [t.label1 for t in ax.xaxis.get_major_ticks() if t.label1.get_visible()]
        texts += [t.label1 for t in ax.yaxis.get_major_ticks() if t.label1.get_visible()]
    for text in texts:
        if not text.get_text():
            continue
        box = text.get_window_extent(renderer)
        if box.x0 < fig_box.x0 or box.y0 < fig_box.y0 or box.x1 > fig_box.x1 or box.y1 > fig_box.y1:
            problems.append(f"outside figure: {text.get_text()!r}")
    for unit, ax in axes.items():
        ax_box = ax.get_window_extent(renderer)
        title_box = ax.title.get_window_extent(renderer)
        for text in ax.texts:
            box = text.get_window_extent(renderer)
            if box.y1 > ax_box.y1 or box.x0 < ax_box.x0 or box.x1 > ax_box.x1:
                problems.append(f"{unit} annotation outside panel: {text.get_text()!r}")
            if box.overlaps(title_box):
                problems.append(f"{unit} annotation overlaps title: {text.get_text()!r}")
    return problems


# ---------------------------------------------------------------- main


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)

    input_path = args.input.resolve()
    if not input_path.is_file():
        raise SystemExit(f"input not found: {input_path}")

    csv_sha256 = sha256_file(input_path)
    try:
        rows = load_rows(input_path)
        points, excluded = select_and_reconcile(rows)
    except DataError as exc:
        raise SystemExit(f"invalid period performance data: {exc}") from exc

    regular_font, bold_font = locate_thai_font()
    check_font_covers(regular_font)
    family = register_font(regular_font, bold_font)
    configure_style(family, svg_editable=True)

    fig, axes = draw_figure(points)
    if len(points) != 8 or any("drawn_bar_height" not in p for p in points):
        raise RuntimeError("expected exactly 8 drawn bars")
    problems = check_text_layout(fig, axes)
    if problems:
        raise RuntimeError(f"text layout problems: {problems}")
    y_limits = {unit: [float(v) for v in ax.get_ylim()] for unit, ax in axes.items()}

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    png_path = output_dir / "fold_results_th.png"
    svg_path = output_dir / "fold_results_th.svg"
    metadata_path = output_dir / "fold_results_th_metadata.json"

    fig.savefig(png_path, dpi=DPI, format="png")
    fig.savefig(svg_path, format="svg")
    plt.close(fig)
    width_px, height_px = png_size(png_path)

    metadata = {
        "source_csv": str(input_path.relative_to(REPO_ROOT) if input_path.is_relative_to(REPO_ROOT) else input_path),
        "source_csv_sha256": csv_sha256,
        "source_row_count": len(rows),
        "plotted_group_count": len(points),
        "scope_plotted": PLOT_SCOPE,
        "periods_plotted": PERIODS,
        "methods": {"selected": SELECTED_METHOD, "baseline": BASELINE_METHOD},
        "metric": "percent reduction in mean Poisson deviance vs baseline = 100 * (baseline - selected) / baseline",
        "data_transformations": "none beyond the percent formula above (no refit, no pooling)",
        "reconciliation": {
            "stored_column": "relative_deviance_reduction",
            "tolerance_abs": GAIN_TOLERANCE,
            "all_within_tolerance": all(p["reconciliation_abs_diff"] <= GAIN_TOLERANCE for p in points),
            "max_abs_diff": max(p["reconciliation_abs_diff"] for p in points),
        },
        "plotted_points": points,
        "excluded_rows": excluded,
        "axes": {
            "y_starts_at_zero": True,
            "y_limits_percent": y_limits,
            "y_headroom_factor": Y_HEADROOM,
            "shared_y": False,
        },
        "font": {
            "family": family,
            "regular_path": str(regular_font),
            "bold_path": str(bold_font) if bold_font else None,
        },
        "outputs": {
            "png": {"path": png_path.name, "width_px": width_px, "height_px": height_px,
                    "sha256": sha256_file(png_path)},
            "svg": {"path": svg_path.name, "text_editable": True, "sha256": sha256_file(svg_path)},
        },
        "matplotlib_version": matplotlib.__version__,
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"wrote {png_path} ({width_px}x{height_px})")
    print(f"wrote {svg_path}")
    print(f"wrote {metadata_path}")
    print(f"font: {family} ({regular_font})")
    for point in points:
        print(f"  {point['unit']:>5} {point['period']}: {point['annotation']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
