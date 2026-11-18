#!/usr/bin/env python3
"""Render the Thai grouped-bar comparison of the three model families vs Baseline.

One figure, two panels, both pooled OOF 2022-2023: left Poisson deviance,
right MAE (separate y scales, each from 0). Each panel has two unit groups
(daily, 6h) with four bars: Baseline (segment_mean_k365), Poisson Regression,
Random Forest and HGB Poisson (all ::routed_context). Values come from the
accepted figure_method_comparison.csv and are plotted exactly as stored; no
refit, retuning or recomputation. Rows are reconciled against
leaderboard_oof.csv and every source file is checked against its manifest hash.

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
import render_thai_calibration as rc  # noqa: E402  (Thai font + figure helpers; sets Agg backend)

import matplotlib  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from matplotlib.ticker import FixedLocator, FuncFormatter, MaxNLocator  # noqa: E402

REPO_ROOT = rc.REPO_ROOT
EVAL_DIR = REPO_ROOT / "output" / "spatial-model-results" / "v3-evaluation-017-002"
EVAL_MANIFEST = EVAL_DIR / "spatial_evaluation_manifest.json"
METHOD_CSV = EVAL_DIR / "figure_method_comparison.csv"
REPORT_DIR = REPO_ROOT / "backend" / "rerun-spatial-model-016-002" / "reports" / "v3" / "spatial_experiments"
EXP_MANIFEST = REPORT_DIR / "spatial_experiments_manifest.json"
LEADERBOARD_CSV = REPORT_DIR / "leaderboard_oof.csv"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "output" / "presentation-th" / "model-comparison"
OUTPUT_STEM = "grouped_models_oof_th"

SPLIT = "oof_2022_2023"
UNITS = ["daily", "6h"]
BASELINE = "segment_mean_k365"
HGB = "hgb_poisson_fixed::routed_context"
METHODS = [
    BASELINE,
    "poisson_a1e-05::routed_context",
    "rf_poisson_fixed::routed_context",
    HGB,
]
METRICS = {
    "deviance": {"column": "mean_poisson_deviance", "decimals": 6},
    "mae": {"column": "mae", "decimals": 6},
}
RECONCILE_COLUMNS = ["n", "mean_poisson_deviance", "mae"]

# 15 x 8.44 in at 200 dpi -> 3000 x 1688 px (16:9).
FIG_SIZE_IN = rc.FIG_SIZE_IN
DPI = rc.DPI
EXPECTED_PX = (3000, 1688)
VALUE_TEXT = "#1F2937"

METHOD_LABELS = {
    BASELINE: "Baseline",
    "poisson_a1e-05::routed_context": "Poisson Regression",
    "rf_poisson_fixed::routed_context": "Random Forest",
    HGB: "HGB Poisson",
}
METHOD_COLORS = {
    BASELINE: "#8A8A8A",
    "poisson_a1e-05::routed_context": "#7B3FA0",
    "rf_poisson_fixed::routed_context": "#0072B2",
    HGB: "#009E8F",
}
UNIT_LABELS = {"daily": "รายวัน", "6h": "ช่วงละ 6 ชั่วโมง"}
TITLE = "เปรียบเทียบผลทั้ง 3 โมเดลกับ Baseline"
SUBTITLE = "ผล OOF ปี 2022–2023 • ค่ายิ่งต่ำยิ่งดี"
PANEL_TITLES = {"deviance": "Poisson deviance", "mae": "MAE — ผิดเฉลี่ยกี่รายการ"}
Y_LABELS = {"deviance": "Poisson deviance เฉลี่ย", "mae": "MAE (รายการ)"}
FOOTER = "เปรียบเทียบภายในหน่วยเวลาเดียวกัน • HGB มี deviance ต่ำสุด แต่ Baseline มี MAE ต่ำกว่า"
# Footer claim, checked per unit before drawing: metric -> method that must be lowest.
FOOTER_CLAIM = {"deviance": HGB, "mae": BASELINE}

rc.ALL_TEXT = list(rc.ALL_TEXT) + [TITLE, SUBTITLE, FOOTER] + list(UNIT_LABELS.values()) \
    + list(PANEL_TITLES.values()) + list(Y_LABELS.values())

GROUP_X = {"daily": 0.0, "6h": 1.0}
BAR_WIDTH = 0.19
BAR_STEP = 0.205
X_LIMITS = (-0.55, 1.55)
LABEL_OFFSET_PT = 5
INITIAL_HEADROOM = 1.18
HEADROOM_STEP = 1.06
LABEL_TOP_FRACTION = 0.97


class DataError(ValueError):
    pass


def require(cond: bool, message: str) -> None:
    if not cond:
        raise DataError(message)


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT)) if path.is_relative_to(REPO_ROOT) else str(path)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- sources


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for row_number, row in enumerate(reader, start=2):
            row["_row"] = row_number
            rows.append(row)
    require(rows, f"{rel(path)} has no data rows")
    return rows


def require_columns(path: Path, rows: list[dict], columns: list[str]) -> None:
    missing = [c for c in columns if c not in rows[0]]
    require(not missing, f"{rel(path)} is missing columns {missing}")


def parse_metric(raw: str, label: str) -> float:
    try:
        value = float(raw)
    except ValueError as exc:
        raise DataError(f"{label}={raw!r} is not numeric") from exc
    require(math.isfinite(value) and value > 0, f"{label}={raw!r} must be finite and positive")
    return value


def check_hashes() -> dict:
    exp_manifest, eval_manifest = read_json(EXP_MANIFEST), read_json(EVAL_MANIFEST)
    require(eval_manifest.get("status") == "complete" and eval_manifest.get("failed_checks") == [],
            "evaluation manifest not complete/clean")
    require(exp_manifest.get("status") == "complete" and exp_manifest.get("failed_checks") == [],
            "experiments manifest not complete/clean")
    checks = {}
    for path, manifest_path, manifest in (
        (METHOD_CSV, EVAL_MANIFEST, eval_manifest),
        (LEADERBOARD_CSV, EXP_MANIFEST, exp_manifest),
    ):
        actual = rc.sha256_file(path)
        expected = manifest["report_files"].get(path.name)
        require(expected is not None, f"{path.name} not listed in {rel(manifest_path)} report_files")
        require(actual == expected, f"{path.name} sha256 {actual} differs from manifest {expected}")
        checks[rel(path)] = {"sha256": actual, "manifest": rel(manifest_path), "manifest_sha256": expected,
                             "matches_manifest": True}
    for path in (EVAL_MANIFEST, EXP_MANIFEST):
        checks[rel(path)] = {"sha256": rc.sha256_file(path), "manifest": None, "manifest_sha256": None,
                             "matches_manifest": None}
    return checks


def select_bars() -> list[dict]:
    rows = read_csv(METHOD_CSV)
    require_columns(METHOD_CSV, rows, ["unit", "method", "n"] + [s["column"] for s in METRICS.values()])
    keys = [(r["unit"], r["method"]) for r in rows]
    require(len(keys) == len(set(keys)), f"{rel(METHOD_CSV)} has duplicate unit/method rows")

    bars = []
    for unit in UNITS:
        for method in METHODS:
            found = [r for r in rows if r["unit"] == unit and r["method"] == method]
            require(len(found) == 1, f"{rel(METHOD_CSV)}: expected 1 row for {unit}/{method}, found {len(found)}")
            row = found[0]
            values = {}
            for metric, spec in METRICS.items():
                raw = row[spec["column"]]
                values[metric] = {"source_column": spec["column"], "source_text": raw,
                                  "value": parse_metric(raw, f"{rel(METHOD_CSV)} row {row['_row']} {spec['column']}")}
            bars.append({"split": SPLIT, "unit": unit, "method": method, "legend_label": METHOD_LABELS[method],
                         "source_file": rel(METHOD_CSV), "source_row_number": row["_row"], "n": int(row["n"]),
                         "values": values})
    rows_used = {(b["unit"], b["method"]) for b in bars}
    require(len(rows_used) == len(UNITS) * len(METHODS), f"expected 8 unique source rows, got {len(rows_used)}")
    for unit in UNITS:
        require(len({b["n"] for b in bars if b["unit"] == unit}) == 1, f"{unit}: methods have different n")
    return bars


def reconcile(bars: list[dict]) -> list[dict]:
    rows = read_csv(LEADERBOARD_CSV)
    require_columns(LEADERBOARD_CSV, rows, ["unit", "method"] + RECONCILE_COLUMNS)
    out = []
    for bar in bars:
        unit, method = bar["unit"], bar["method"]
        found = [r for r in rows if r["unit"] == unit and r["method"] == method]
        require(len(found) == 1, f"leaderboard_oof.csv: expected 1 row for {unit}/{method}, found {len(found)}")
        source = {"n": str(bar["n"])} | {s["column"]: bar["values"][m]["source_text"] for m, s in METRICS.items()}
        for column in RECONCILE_COLUMNS:
            a, b = float(source[column]), float(found[0][column])
            require(a == b, f"{unit}/{method} {column}: figure_method_comparison {a!r} != leaderboard {b!r}")
            out.append({"unit": unit, "method": method, "column": column,
                        "figure_method_comparison_row": bar["source_row_number"], "leaderboard_row": found[0]["_row"],
                        "figure_method_comparison_value": a, "leaderboard_value": b, "abs_diff": abs(a - b),
                        "exact_match": True})
    return out


def check_footer_claim(bars: list[dict]) -> dict:
    result = {}
    for metric, expected in FOOTER_CLAIM.items():
        for unit in UNITS:
            group = [b for b in bars if b["unit"] == unit]
            lowest = min(group, key=lambda b: b["values"][metric]["value"])
            require(lowest["method"] == expected,
                    f"footer claim fails: lowest {metric} for {unit} is {lowest['method']}, not {expected}")
            result[f"{unit}/{metric}"] = {"lowest_method": lowest["method"],
                                          "value": lowest["values"][metric]["value"]}
    return result


# ---------------------------------------------------------------- plotting


def bar_x(unit: str, method: str) -> float:
    return GROUP_X[unit] + (METHODS.index(method) - (len(METHODS) - 1) / 2) * BAR_STEP


def value_label(metric: str, value: float) -> str:
    return f"{value:.{METRICS[metric]['decimals']}f}"


def tick_formatter(ticks: list[float]) -> FuncFormatter:
    # Fewest decimals that still show every tick exactly (e.g. 0.0025 steps need 4).
    step = min(b - a for a, b in zip(ticks, ticks[1:]))
    decimals = next(d for d in range(12) if all(abs(round(t, d) - t) <= step * 1e-6 for t in ticks))
    return FuncFormatter(lambda v, _pos: "0" if v == 0 else f"{v:.{decimals}f}")


def fit_y_axis(fig, ax, value_texts: list, max_value: float) -> tuple[float, list[float]]:
    # Start from 0; grow headroom until every rotated label sits inside the panel.
    top = max_value * INITIAL_HEADROOM
    for _ in range(40):
        ax.set_ylim(0, top)
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        inv = ax.transData.inverted()
        highest = max(inv.transform((0, t.get_window_extent(renderer).y1))[1] for t in value_texts)
        if highest <= top * LABEL_TOP_FRACTION:
            break
        top *= HEADROOM_STEP
    else:
        raise RuntimeError("could not fit value labels inside the panel")
    ticks = [t for t in MaxNLocator(nbins=5, steps=[1, 2, 2.5, 5, 10]).tick_values(0, top) if 0 <= t <= top]
    ax.yaxis.set_major_locator(FixedLocator(ticks))
    ax.yaxis.set_major_formatter(tick_formatter(ticks))
    return top, ticks


def draw_figure(bars: list[dict]):
    fig = plt.figure(figsize=FIG_SIZE_IN, dpi=DPI)
    fig.text(0.5, 0.958, TITLE, ha="center", va="top", fontsize=28, fontweight="bold", color=rc.NAVY)
    fig.text(0.5, 0.893, SUBTITLE, ha="center", va="top", fontsize=17, color=rc.TEXT_GREY)

    bottom, height, width = 0.215, 0.535, 0.385
    axes = {
        "deviance": fig.add_axes([0.085, bottom, width, height]),
        "mae": fig.add_axes([0.585, bottom, width, height]),
    }
    drawn, value_texts, y_axes = [], [], {}
    for metric, ax in axes.items():
        texts = []
        for bar in bars:
            x = bar_x(bar["unit"], bar["method"])
            value = bar["values"][metric]["value"]
            container = ax.bar([x], [value], width=BAR_WIDTH, color=METHOD_COLORS[bar["method"]],
                               edgecolor="white", linewidth=1.0, zorder=3)
            height_drawn = float(container.patches[0].get_height())
            if height_drawn != value:
                raise RuntimeError(f"{metric}/{bar['unit']}/{bar['method']}: drawn height differs from source value")
            label = value_label(metric, value)
            texts.append(ax.annotate(
                label, (x, value), xytext=(0, LABEL_OFFSET_PT), textcoords="offset points", rotation=90,
                ha="center", va="bottom", fontsize=12.5, color=VALUE_TEXT, annotation_clip=False))
            drawn.append({**bar, "metric": metric, "x": x, "plotted_height": height_drawn, "label_text": label})

        ax.set_xlim(*X_LIMITS)
        ax.set_xticks([GROUP_X[u] for u in UNITS])
        ax.set_xticklabels([UNIT_LABELS[u] for u in UNITS])
        ax.tick_params(axis="x", length=0, labelsize=17, colors=rc.NAVY, pad=10)
        ax.tick_params(axis="y", labelsize=13, colors=rc.TEXT_GREY, length=4)
        ax.grid(True, axis="y", color=rc.GRID_GREY, linewidth=0.8)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.spines["left"].set_color(rc.SPINE_GREY)
        ax.spines["bottom"].set_color(rc.SPINE_GREY)
        ax.set_ylabel(Y_LABELS[metric], fontsize=15, color=rc.TEXT_GREY, labelpad=12)
        ax.text(0.5, 1.045, PANEL_TITLES[metric], transform=ax.transAxes, ha="center", va="bottom",
                fontsize=21, fontweight="bold", color=rc.NAVY)

        max_value = max(d["plotted_height"] for d in drawn if d["metric"] == metric)
        top, ticks = fit_y_axis(fig, ax, texts, max_value)
        y_axes[metric] = {"y_min": 0.0, "y_max": top, "max_bar_value": max_value, "y_ticks": ticks}
        value_texts += texts

    handles = [Patch(facecolor=METHOD_COLORS[m], edgecolor="none", label=METHOD_LABELS[m]) for m in METHODS]
    fig.legend(handles=handles, loc="center", bbox_to_anchor=(0.5, 0.092), ncol=4, frameon=False, fontsize=16,
               handlelength=1.6, handleheight=1.0, columnspacing=2.6)
    fig.text(0.5, 0.032, FOOTER, ha="center", va="center", fontsize=13, color=rc.FOOTER_GREY)
    return fig, drawn, {"y_axes": y_axes, "value_texts": value_texts, "axes": axes}


def check_layout(fig, layout: dict) -> None:
    clipped = rc.check_text_inside_figure(fig)
    require(not clipped, f"text extends outside the figure: {clipped}")
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    labels = layout["value_texts"]
    boxes = [t.get_window_extent(renderer) for t in labels]
    for t, box in zip(labels, boxes):
        ax_box = t.axes.get_window_extent(renderer)
        require(box.y1 <= ax_box.y1 and box.x0 >= ax_box.x0 and box.x1 <= ax_box.x1,
                f"value label {t.get_text()!r} extends outside its panel")
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            require(not boxes[i].overlaps(boxes[j]),
                    f"value labels overlap: {labels[i].get_text()!r} and {labels[j].get_text()!r}")
    axes = list(layout["axes"].values())
    require(not axes[0].get_tightbbox(renderer).overlaps(axes[1].get_tightbbox(renderer)), "panels overlap")
    legend_box = fig.legends[0].get_window_extent(renderer)
    for ax in axes:
        require(not legend_box.overlaps(ax.get_tightbbox(renderer)), "legend overlaps a panel")
    for text in fig.texts:
        require(not legend_box.overlaps(text.get_window_extent(renderer)), f"legend overlaps text {text.get_text()!r}")
    panel_texts = [t for ax in axes for t in ax.texts if t not in labels]
    for t in panel_texts + list(fig.texts):
        box = t.get_window_extent(renderer)
        for other in panel_texts + list(fig.texts):
            if other is not t:
                require(not box.overlaps(other.get_window_extent(renderer)),
                        f"text overlaps: {t.get_text()!r} and {other.get_text()!r}")


# ---------------------------------------------------------------- outputs


def write_plotted_csv(path: Path, drawn: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        w = csv.writer(handle, lineterminator="\n")
        w.writerow(["metric", "split", "unit", "method", "legend_label", "n", "source_file", "source_row_number",
                    "source_column", "source_text", "value", "plotted_height", "label_text"])
        for d in drawn:
            v = d["values"][d["metric"]]
            w.writerow([d["metric"], d["split"], d["unit"], d["method"], d["legend_label"], d["n"], d["source_file"],
                        d["source_row_number"], v["source_column"], v["source_text"], repr(v["value"]),
                        repr(d["plotted_height"]), d["label_text"]])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)

    try:
        hashes = check_hashes()
        bars = select_bars()
        reconciliation = reconcile(bars)
        footer_claim = check_footer_claim(bars)
    except DataError as exc:
        raise SystemExit(f"invalid source data: {exc}") from exc

    regular_font, bold_font = rc.locate_thai_font()
    family = rc.register_font(regular_font, bold_font)
    if "sarabun" not in family.lower():
        print(f"WARNING: Sarabun not found; using {family}")
    rc.configure_style(family, svg_editable=True)

    fig, drawn, layout = draw_figure(bars)
    if len(drawn) != len(METRICS) * len(UNITS) * len(METHODS):
        raise RuntimeError(f"expected 16 bars, drew {len(drawn)}")
    try:
        check_layout(fig, layout)
    except DataError as exc:
        raise SystemExit(f"layout check failed: {exc}") from exc

    out_dir = args.output_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    png_path = out_dir / f"{OUTPUT_STEM}.png"
    svg_path = out_dir / f"{OUTPUT_STEM}.svg"
    fig.savefig(png_path, dpi=DPI, format="png")
    fig.savefig(svg_path, format="svg")
    plt.close(fig)
    width_px, height_px = rc.png_size(png_path)
    if (width_px, height_px) != EXPECTED_PX:
        raise SystemExit(f"PNG is {width_px}x{height_px}, expected {EXPECTED_PX[0]}x{EXPECTED_PX[1]}")

    csv_path = out_dir / "plotted_values.csv"
    write_plotted_csv(csv_path, drawn)
    metadata = {
        "sources": hashes,
        "selection": {
            "split": SPLIT,
            "file": rel(METHOD_CSV),
            "filter": "unit, method (one row each)",
            "methods": {m: METHOD_LABELS[m] for m in METHODS},
            "units": UNITS,
            "unique_source_rows": len({(b["unit"], b["method"]) for b in bars}),
            "seen_2025_rows_used": False,
        },
        "data_transformations": "none (source metric values plotted as-is; no refit, retuning or recomputation)",
        "reconciliation": {"against": rel(LEADERBOARD_CSV), "columns": RECONCILE_COLUMNS,
                           "all_exact": all(r["exact_match"] for r in reconciliation), "rows": reconciliation},
        "footer_claim_check": {"text": FOOTER, "lowest_per_unit": footer_claim, "holds": True},
        "panels": {metric: {"position": "left" if metric == "deviance" else "right", "title": PANEL_TITLES[metric],
                            "source_column": METRICS[metric]["column"], "label_decimals": METRICS[metric]["decimals"],
                            **layout["y_axes"][metric]}
                   for metric in METRICS},
        "y_axis_shared_across_panels": False,
        "bar_count": len(drawn),
        "bars": [{k: d[k] for k in ("metric", "split", "unit", "method", "legend_label", "source_file",
                                    "source_row_number", "n", "x", "plotted_height", "label_text")}
                 | {"source_column": d["values"][d["metric"]]["source_column"],
                    "source_text": d["values"][d["metric"]]["source_text"],
                    "value": d["values"][d["metric"]]["value"]}
                 for d in drawn],
        "outputs": {
            "png": {"path": png_path.name, "width_px": width_px, "height_px": height_px,
                    "sha256": rc.sha256_file(png_path)},
            "svg": {"path": svg_path.name, "text_editable": True, "sha256": rc.sha256_file(svg_path)},
            "plotted_values_csv": {"path": csv_path.name, "sha256": rc.sha256_file(csv_path)},
        },
        "font": {"family": family, "regular_path": str(regular_font),
                 "bold_path": str(bold_font) if bold_font else None},
        "matplotlib_version": matplotlib.__version__,
    }
    metadata_path = out_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"wrote {png_path} ({width_px}x{height_px})")
    print(f"wrote {svg_path}")
    print(f"wrote {csv_path}")
    print(f"wrote {metadata_path}")
    print(f"font: {family} ({regular_font})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
