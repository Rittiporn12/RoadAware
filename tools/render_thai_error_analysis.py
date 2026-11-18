#!/usr/bin/env python3
"""Render the two Thai Error Analysis figures for the Model Gate presentation.

Uses accepted V3 OOF 2022-2023 evaluation outputs only (no V2, no 2026):

* error_totals_th - recorded vs HGB-predicted totals, daily and 6h panels.
  Totals are summed from figure_calibration.csv (selected role) and must match
  the accepted report values 10,701 / 9,574.10 / 9,446.02.
* error_areas_th - provinces where HGB deviance is higher than the baseline.
  Values are read from figure_errors_by_group.csv; the signed reduction is
  negated so bars show a positive "HGB worse" magnitude. This is relative mean
  deviance only, not MAE and not an accident-rate change.

Outputs (PNG + SVG per figure, plus one metadata JSON) are written to
output/presentation-th/error-analysis/. The caller is expected to set a
writable MPLCONFIGDIR before running.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import struct
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.ft2font import FT2Font  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = REPO_ROOT / "output" / "spatial-model-results" / "v3-evaluation-017-002"
CALIBRATION_CSV = EVAL_DIR / "figure_calibration.csv"
GROUPS_CSV = EVAL_DIR / "figure_errors_by_group.csv"
OUTPUT_DIR = REPO_ROOT / "output" / "presentation-th" / "error-analysis"

CALIBRATION_HEADER = [
    "unit",
    "role",
    "method",
    "group",
    "n",
    "total_pred",
    "total_actual",
    "exposure_segment_km_periods",
    "predicted_records_per_km_period",
    "observed_records_per_km_period",
]
GROUPS_HEADER = [
    "unit",
    "dimension",
    "group",
    "cells",
    "records",
    "baseline_mean_deviance",
    "selected_mean_deviance",
    "baseline_deviance_sum",
    "selected_deviance_sum",
    "relative_deviance_reduction",
    "label",
]

# Accepted values from workflow/model-gate-presentation-th.md section 4 and
# model_gate_presentation_th.md; the CSV-derived values must reproduce them.
UNITS = ["daily", "6h"]
EXPECTED_CELLS = {"daily": 2_266_650, "6h": 9_066_600}
EXPECTED_ACTUAL_TOTAL = 10_701
EXPECTED_PRED_TOTAL_2DP = {"daily": "9574.10", "6h": "9446.02"}
EXPECTED_SHORTFALL_PCT_2DP = {"daily": "10.53", "6h": "11.73"}
SELECTED_ROLE = "selected"

# (province_code, Thai name, expected cells, expected records, expected signed reduction % at 4 dp)
PROVINCES = [
    ("72", "สุพรรณบุรี", 13_870, 34, "-3.5754"),
    ("20", "ชลบุรี", 10_220, 29, "-1.5434"),
    ("24", "ฉะเชิงเทรา", 163_520, 661, "-0.3536"),
]
REDUCTION_TOLERANCE = 1e-9
TOTAL_TOLERANCE = 1e-6

# 15 x 8.44 in at 200 dpi -> 3000 x 1688 px (16:9).
FIG_SIZE_IN = (15.0, 8.44)
DPI = 200
MIN_PX = (2400, 1350)

NAVY = "#1B2A49"
TEXT_GREY = "#4B5563"
FOOTER_GREY = "#6B7280"
GRID_GREY = "#E5E7EB"
SPINE_GREY = "#9CA3AF"
TEAL = "#0F8B8D"
ORANGE = "#F28C28"
ORANGE_TEXT = "#B45309"
AREA_COLOR = "#5B6B8C"

TOTALS_TITLE = "HGB ยังทำนายยอดรวมต่ำกว่าที่บันทึก"
TOTALS_SUBTITLE = "ยอดรวมทั้งช่วง OOF (ไม่ใช่ค่าเฉลี่ยต่อวันหรือต่อช่วง) • เทียบภายในแต่ละแผงเท่านั้น"
TOTALS_PANEL_TITLES = {"daily": "รายวัน", "6h": "ช่วงละ 6 ชั่วโมง"}
TOTALS_Y_LABEL = "จำนวนรายการรวม"
ACTUAL_LABEL = "ข้อมูลที่บันทึก"
PRED_LABEL = "HGB ทำนาย"
SHORTFALL_PREFIX = "ต่ำกว่าที่บันทึก"
TOTALS_FOOTER = "ผล OOF ปี 2022–2023 • เฉพาะรายการที่ผ่านการคัดเลือกและเชื่อมถนนได้"
TOTALS_Y_HEADROOM = 1.18

AREAS_TITLE = "บางพื้นที่ Baseline ยังให้ผลดีกว่า HGB"
AREAS_SUBTITLE = "Deviance ต่ำกว่า = ดีกว่า • แท่งยาว = HGB ด้อยกว่า Baseline มากกว่าในพื้นที่นั้น"
AREAS_X_LABEL = "Deviance ของ HGB สูงกว่า Baseline (%)"
RECORDS_SUFFIX = "รายการ"
AREAS_FOOTER = "OOF รายวัน ปี 2022–2023 • จังหวัดตามจุดกึ่งกลางช่วงถนน • บางกลุ่มมีรายการน้อย"
AREAS_X_HEADROOM = 1.3

ALL_TEXT = [
    TOTALS_TITLE, TOTALS_SUBTITLE, TOTALS_Y_LABEL, ACTUAL_LABEL, PRED_LABEL, SHORTFALL_PREFIX, TOTALS_FOOTER,
    AREAS_TITLE, AREAS_SUBTITLE, AREAS_X_LABEL, RECORDS_SUFFIX, AREAS_FOOTER,
]
ALL_TEXT += list(TOTALS_PANEL_TITLES.values()) + [name for _, name, _, _, _ in PROVINCES]

SARABUN_ROOT = Path("/System/Library/AssetsV2")
FALLBACK_ROOTS = [
    Path("/System/Library/Fonts"),
    Path("/Library/Fonts"),
    Path.home() / "Library" / "Fonts",
    Path("/usr/share/fonts"),
    Path("/usr/local/share/fonts"),
]
FALLBACK_PATTERNS = [
    "Sarabun*",
    "THSarabun*",
    "Thonburi*",
    "SukhumvitSet*",
    "NotoSansThai*",
    "Ayuthaya*",
    "Loma*",
    "Garuda*",
]
FONT_SUFFIXES = {".ttf", ".otf", ".ttc"}


class DataError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT) if path.is_relative_to(REPO_ROOT) else path)


# ---------------------------------------------------------------- fonts


def _safe_glob(root: Path, pattern: str) -> list[Path]:
    if not root.is_dir():
        return []
    try:
        return sorted(p for p in root.glob(pattern) if p.suffix.lower() in FONT_SUFFIXES and p.is_file())
    except OSError:
        return []


def _thai_codepoints() -> set[int]:
    return {ord(ch) for text in ALL_TEXT for ch in text if 0x0E00 <= ord(ch) <= 0x0E7F}


def _covers_thai(path: Path) -> bool:
    try:
        charmap = FT2Font(str(path)).get_charmap()
    except Exception:  # unreadable / unsupported font file
        return False
    return _thai_codepoints() <= set(charmap)


def _pick_weight(paths: list[Path], weight: str) -> Path | None:
    def stem(p: Path) -> str:
        return p.stem.lower()

    if weight == "bold":
        exact = [
            p for p in paths
            if stem(p).endswith("bold") and not any(tag in stem(p) for tag in ("semi", "extra", "italic"))
        ]
        return exact[0] if exact else None
    regular = [p for p in paths if "regular" in stem(p)]
    if regular:
        return regular[0]
    plain = [p for p in paths if not any(tag in stem(p) for tag in ("bold", "italic", "light", "thin", "medium"))]
    return min(plain or paths, key=lambda p: len(p.name)) if (plain or paths) else None


def locate_thai_font() -> tuple[Path, Path | None]:
    """Return (regular, bold-or-None), preferring Sarabun under AssetsV2."""
    candidates = _safe_glob(SARABUN_ROOT, "**/Sarabun*")
    candidates = [p for p in candidates if _covers_thai(p)]
    if not candidates:
        for pattern in FALLBACK_PATTERNS:
            for root in FALLBACK_ROOTS:
                found = [p for p in _safe_glob(root, f"**/{pattern}") if _covers_thai(p)]
                if found:
                    candidates = found
                    break
            if candidates:
                break
    if not candidates:
        raise SystemExit("No Thai-capable font found (looked for Sarabun under /System/Library/AssetsV2 and fallbacks).")
    regular = _pick_weight(candidates, "regular")
    bold = _pick_weight(candidates, "bold")
    return regular, bold


def register_font(regular: Path, bold: Path | None) -> str:
    font_manager.fontManager.addfont(str(regular))
    family = font_manager.FontProperties(fname=str(regular)).get_name()
    if bold is not None:
        font_manager.fontManager.addfont(str(bold))
    return family


# ---------------------------------------------------------------- data


def _parse_float(raw: str, field: str, row_number: int) -> float:
    try:
        value = float(raw)
    except ValueError as exc:
        raise DataError(f"row {row_number}: {field}={raw!r} is not numeric") from exc
    if not math.isfinite(value):
        raise DataError(f"row {row_number}: {field}={raw!r} is not finite")
    return value


def _parse_count(raw: str, field: str, row_number: int) -> int:
    value = _parse_float(raw, field, row_number)
    if value < 0 or not value.is_integer():
        raise DataError(f"row {row_number}: {field}={raw!r} is not a non-negative whole number")
    return int(value)


def _read_csv(path: Path, expected_header: list[str]) -> list[tuple[int, dict]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader, None)
        if header != expected_header:
            raise DataError(f"{path.name}: unexpected header {header}")
        rows = []
        for row_number, record in enumerate(reader, start=2):
            if not record:
                continue
            if len(record) != len(expected_header):
                raise DataError(f"{path.name} row {row_number}: expected {len(expected_header)} fields, got {len(record)}")
            rows.append((row_number, dict(zip(expected_header, record))))
    return rows


def load_totals(path: Path) -> dict[str, dict]:
    """Sum selected-role calibration bins per unit and check against accepted totals."""
    sums: dict[str, dict] = {}
    for row_number, raw in _read_csv(path, CALIBRATION_HEADER):
        if raw["role"] != SELECTED_ROLE:
            continue
        unit = raw["unit"]
        if unit not in UNITS:
            raise DataError(f"{path.name} row {row_number}: unexpected unit {unit!r}")
        entry = sums.setdefault(unit, {"methods": set(), "bins": 0, "cells": 0, "pred": 0.0, "actual": 0.0})
        pred = _parse_float(raw["total_pred"], "total_pred", row_number)
        actual = _parse_float(raw["total_actual"], "total_actual", row_number)
        if pred < 0 or actual < 0:
            raise DataError(f"{path.name} row {row_number}: totals must be non-negative")
        entry["methods"].add(raw["method"])
        entry["bins"] += 1
        entry["cells"] += _parse_count(raw["n"], "n", row_number)
        entry["pred"] += pred
        entry["actual"] += actual

    totals = {}
    for unit in UNITS:
        if unit not in sums:
            raise DataError(f"{path.name}: no {SELECTED_ROLE} rows for unit {unit}")
        entry = sums[unit]
        if len(entry["methods"]) != 1:
            raise DataError(f"{unit}: expected one selected method, found {sorted(entry['methods'])}")
        if entry["cells"] != EXPECTED_CELLS[unit]:
            raise DataError(f"{unit}: bins cover {entry['cells']} cells, expected {EXPECTED_CELLS[unit]}")
        if abs(entry["actual"] - EXPECTED_ACTUAL_TOTAL) > TOTAL_TOLERANCE:
            raise DataError(f"{unit}: actual total {entry['actual']} != {EXPECTED_ACTUAL_TOTAL}")
        pred_2dp = f"{entry['pred']:.2f}"
        if pred_2dp != EXPECTED_PRED_TOTAL_2DP[unit]:
            raise DataError(f"{unit}: predicted total {pred_2dp} != accepted {EXPECTED_PRED_TOTAL_2DP[unit]}")

        actual = float(EXPECTED_ACTUAL_TOTAL)
        pred = entry["pred"]
        shortfall_pct = (actual - pred) / actual * 100.0
        pred_report = float(EXPECTED_PRED_TOTAL_2DP[unit])
        shortfall_pct_report = (actual - pred_report) / actual * 100.0
        for label, value in (("csv", shortfall_pct), ("report", shortfall_pct_report)):
            if f"{value:.2f}" != EXPECTED_SHORTFALL_PCT_2DP[unit]:
                raise DataError(
                    f"{unit}: {label} shortfall {value:.4f}% != accepted {EXPECTED_SHORTFALL_PCT_2DP[unit]}%"
                )
        totals[unit] = {
            "method": next(iter(entry["methods"])),
            "calibration_bins_summed": entry["bins"],
            "cells": entry["cells"],
            "actual_total": actual,
            "predicted_total_csv_sum": pred,
            "predicted_total_report_2dp": pred_report,
            "shortfall_records": actual - pred,
            "shortfall_pct_from_csv_sum": shortfall_pct,
            "shortfall_pct_from_report_values": shortfall_pct_report,
            "shortfall_pct_display": f"{shortfall_pct:.2f}",
            "pred_over_actual": pred / actual,
        }
    return totals


def load_areas(path: Path) -> list[dict]:
    """Read daily province rows, check accepted values, and flip sign to 'HGB worse' magnitude."""
    wanted = {code: (name, cells, records, pct) for code, name, cells, records, pct in PROVINCES}
    found: dict[str, dict] = {}
    for row_number, raw in _read_csv(path, GROUPS_HEADER):
        if raw["unit"] != "daily" or raw["dimension"] != "province" or raw["group"] not in wanted:
            continue
        code = raw["group"]
        if code in found:
            raise DataError(f"{path.name} row {row_number}: duplicate daily province {code}")
        name, exp_cells, exp_records, exp_pct = wanted[code]
        cells = _parse_count(raw["cells"], "cells", row_number)
        records = _parse_count(raw["records"], "records", row_number)
        baseline_sum = _parse_float(raw["baseline_deviance_sum"], "baseline_deviance_sum", row_number)
        selected_sum = _parse_float(raw["selected_deviance_sum"], "selected_deviance_sum", row_number)
        reduction = _parse_float(raw["relative_deviance_reduction"], "relative_deviance_reduction", row_number)
        if cells != exp_cells or records != exp_records:
            raise DataError(
                f"province {code}: cells/records {cells}/{records} != accepted {exp_cells}/{exp_records}"
            )
        if baseline_sum <= 0:
            raise DataError(f"province {code}: baseline deviance sum must be positive")
        recomputed = 1.0 - selected_sum / baseline_sum
        if abs(recomputed - reduction) > REDUCTION_TOLERANCE:
            raise DataError(f"province {code}: reduction {reduction} != recomputed {recomputed}")
        signed_pct = reduction * 100.0
        if f"{signed_pct:.4f}" != exp_pct:
            raise DataError(f"province {code}: signed reduction {signed_pct:.4f}% != accepted {exp_pct}%")
        worse_pct = -signed_pct
        if worse_pct <= 0:
            raise DataError(f"province {code}: HGB is not worse than baseline ({signed_pct}%)")
        found[code] = {
            "csv_row_number": row_number,
            "province_code": code,
            "province_label_csv": raw["label"],
            "province_th": name,
            "cells": cells,
            "records": records,
            "baseline_mean_deviance": _parse_float(raw["baseline_mean_deviance"], "baseline_mean_deviance", row_number),
            "selected_mean_deviance": _parse_float(raw["selected_mean_deviance"], "selected_mean_deviance", row_number),
            "baseline_deviance_sum": baseline_sum,
            "selected_deviance_sum": selected_sum,
            "relative_deviance_reduction_signed": reduction,
            "relative_deviance_reduction_recomputed": recomputed,
            "hgb_deviance_higher_than_baseline_pct": worse_pct,
            "display_value": f"{worse_pct:.4f}%",
        }
    missing = sorted(set(wanted) - set(found))
    if missing:
        raise DataError(f"{path.name}: missing daily province rows {missing}")
    return sorted(found.values(), key=lambda r: r["hgb_deviance_higher_than_baseline_pct"], reverse=True)


# ---------------------------------------------------------------- plotting


def configure_style(family: str) -> None:
    plt.rcParams.update(
        {
            "font.family": [family, "DejaVu Sans"],
            "axes.unicode_minus": False,
            "svg.fonttype": "none",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )


def _header_footer(fig, title: str, subtitle: str, footer: str) -> None:
    fig.text(0.5, 0.955, title, ha="center", va="top", fontsize=32, fontweight="bold", color=NAVY)
    fig.text(0.5, 0.875, subtitle, ha="center", va="top", fontsize=17, color=TEXT_GREY)
    fig.text(0.5, 0.035, footer, ha="center", va="center", fontsize=13, color=FOOTER_GREY)


def _light_axes(ax, grid_axis: str) -> None:
    ax.grid(True, axis=grid_axis, color=GRID_GREY, linewidth=0.9)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(SPINE_GREY)


def draw_totals(totals: dict[str, dict]):
    fig = plt.figure(figsize=FIG_SIZE_IN, dpi=DPI)
    _header_footer(fig, TOTALS_TITLE, TOTALS_SUBTITLE, TOTALS_FOOTER)

    ax_daily = fig.add_axes([0.10, 0.15, 0.37, 0.60])
    ax_6h = fig.add_axes([0.57, 0.15, 0.37, 0.60], sharey=ax_daily)
    axes = {"daily": ax_daily, "6h": ax_6h}

    # One shared y-scale from zero for both panels.
    ymax = TOTALS_Y_HEADROOM * max(max(t["actual_total"], t["predicted_total_csv_sum"]) for t in totals.values())
    bar_width = 0.58
    arrow_x = 1 + bar_width / 2 + 0.08
    drawn = {}
    for unit, ax in axes.items():
        t = totals[unit]
        actual = t["actual_total"]
        pred = t["predicted_total_csv_sum"]
        bars = ax.bar([0, 1], [actual, pred], width=bar_width, color=[TEAL, ORANGE], zorder=3)
        heights = [float(b.get_height()) for b in bars]
        if heights != [actual, pred]:
            raise RuntimeError(f"{unit}: drawn bar heights differ from source totals")
        drawn[unit] = {"actual_bar_height": heights[0], "predicted_bar_height": heights[1]}

        for x, h, label in ((0, actual, f"{actual:,.0f}"), (1, pred, f"{pred:,.2f}")):
            ax.text(x, h - ymax * 0.025, label, ha="center", va="top", fontsize=21, fontweight="bold",
                    color="white", zorder=4)

        # Shortfall callout: dashed reference at the recorded total, arrow to the predicted bar top.
        ax.hlines(actual, bar_width / 2, arrow_x, colors=SPINE_GREY, linestyles=(0, (5, 4)), linewidth=1.6, zorder=2)
        ax.annotate("", xy=(arrow_x, pred), xytext=(arrow_x, actual),
                    arrowprops={"arrowstyle": "<->", "color": ORANGE_TEXT, "linewidth": 2.0,
                                "shrinkA": 0, "shrinkB": 0})
        ax.text(1, actual + ymax * 0.03, f"{SHORTFALL_PREFIX} {t['shortfall_pct_display']}%",
                ha="center", va="bottom", fontsize=20, fontweight="bold", color=ORANGE_TEXT)

        ax.set_xlim(-0.6, 1.62)
        ax.set_ylim(0, ymax)
        ax.set_xticks([0, 1], [ACTUAL_LABEL, PRED_LABEL])
        ax.tick_params(axis="x", length=0, labelsize=18, colors=NAVY, pad=10)
        ax.tick_params(axis="y", labelsize=14, colors=TEXT_GREY, length=0)
        ax.set_title(TOTALS_PANEL_TITLES[unit], fontsize=23, fontweight="bold", color=NAVY, pad=14)
        _light_axes(ax, "y")

    ax_daily.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax_daily.set_ylabel(TOTALS_Y_LABEL, fontsize=17, color=TEXT_GREY, labelpad=12)
    ax_6h.tick_params(axis="y", labelleft=False)
    ax_6h.spines["left"].set_visible(False)
    if ax_daily.get_ylim() != ax_6h.get_ylim() or ax_daily.get_ylim()[0] != 0:
        raise RuntimeError("panels must share a y-scale starting at 0")
    return fig, {"y_limits": list(ax_daily.get_ylim()), "bars": drawn}


def draw_areas(areas: list[dict]):
    fig = plt.figure(figsize=FIG_SIZE_IN, dpi=DPI)
    _header_footer(fig, AREAS_TITLE, AREAS_SUBTITLE, AREAS_FOOTER)

    ax = fig.add_axes([0.30, 0.19, 0.62, 0.58])
    values = [a["hgb_deviance_higher_than_baseline_pct"] for a in areas]
    ys = list(range(len(areas)))[::-1]  # largest on top
    bars = ax.barh(ys, values, height=0.56, color=AREA_COLOR, zorder=3)
    widths = [float(b.get_width()) for b in bars]
    if widths != values:
        raise RuntimeError("drawn bar lengths differ from source values")

    xmax = AREAS_X_HEADROOM * max(values)
    for y, area in zip(ys, areas):
        ax.text(area["hgb_deviance_higher_than_baseline_pct"] + xmax * 0.012, y, area["display_value"],
                ha="left", va="center", fontsize=21, fontweight="bold", color=NAVY)

    ax.set_yticks(ys, [f"{a['province_th']}\n({a['records']:,} {RECORDS_SUFFIX})" for a in areas])
    ax.set_xlim(0, xmax)
    ax.set_ylim(-0.6, len(areas) - 0.4)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    ax.tick_params(axis="y", length=0, labelsize=19, colors=NAVY, pad=12)
    ax.tick_params(axis="x", labelsize=14, colors=TEXT_GREY, length=0)
    ax.set_xlabel(AREAS_X_LABEL, fontsize=17, color=TEXT_GREY, labelpad=12)
    _light_axes(ax, "x")
    ax.spines["left"].set_visible(False)
    return fig, {"x_limits": list(ax.get_xlim()), "bar_lengths": widths}


def check_text_inside_figure(fig) -> list[str]:
    """Return labels of any text artists whose extents fall outside the canvas."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    fig_box = fig.bbox
    problems = []
    texts = list(fig.texts)
    for ax in fig.axes:
        texts += list(ax.texts) + [ax.title, ax.xaxis.label, ax.yaxis.label]
        texts += [t.label1 for t in ax.xaxis.get_major_ticks() if t.label1.get_visible()]
        texts += [t.label1 for t in ax.yaxis.get_major_ticks() if t.label1.get_visible()]
    for text in texts:
        if not text.get_text():
            continue
        box = text.get_window_extent(renderer)
        if box.x0 < fig_box.x0 or box.y0 < fig_box.y0 or box.x1 > fig_box.x1 or box.y1 > fig_box.y1:
            problems.append(text.get_text())
    return problems


def png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        head = handle.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError(f"{path} is not a PNG")
    return struct.unpack(">II", head[16:24])


def save_figure(fig, stem: str) -> dict:
    clipped = check_text_inside_figure(fig)
    if clipped:
        raise RuntimeError(f"{stem}: text extends outside the figure: {clipped}")
    png_path = OUTPUT_DIR / f"{stem}.png"
    svg_path = OUTPUT_DIR / f"{stem}.svg"
    fig.savefig(png_path, dpi=DPI, format="png")
    fig.savefig(svg_path, format="svg")
    plt.close(fig)
    width_px, height_px = png_size(png_path)
    if width_px < MIN_PX[0] or height_px < MIN_PX[1]:
        raise RuntimeError(f"{stem}: PNG {width_px}x{height_px} smaller than {MIN_PX}")
    print(f"wrote {png_path} ({width_px}x{height_px})")
    print(f"wrote {svg_path}")
    return {
        "png": {"path": png_path.name, "width_px": width_px, "height_px": height_px, "sha256": sha256_file(png_path)},
        "svg": {"path": svg_path.name, "text_editable": True, "sha256": sha256_file(svg_path)},
    }


# ---------------------------------------------------------------- main


def main() -> int:
    for path in (CALIBRATION_CSV, GROUPS_CSV):
        if not path.is_file():
            raise SystemExit(f"input not found: {path}")
    try:
        totals = load_totals(CALIBRATION_CSV)
        areas = load_areas(GROUPS_CSV)
    except DataError as exc:
        raise SystemExit(f"invalid error-analysis data: {exc}") from exc

    regular_font, bold_font = locate_thai_font()
    family = register_font(regular_font, bold_font)
    configure_style(family)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    fig, totals_drawn = draw_totals(totals)
    totals_outputs = save_figure(fig, "error_totals_th")
    fig, areas_drawn = draw_areas(areas)
    areas_outputs = save_figure(fig, "error_areas_th")

    metadata = {
        "scope": "accepted V3 OOF 2022-2023 only (no V2, no 2026); selected+linked records",
        "sources": {
            "calibration_csv": {"path": rel(CALIBRATION_CSV), "sha256": sha256_file(CALIBRATION_CSV)},
            "groups_csv": {"path": rel(GROUPS_CSV), "sha256": sha256_file(GROUPS_CSV)},
        },
        "error_totals_th": {
            "accepted_values": {
                "actual_total": EXPECTED_ACTUAL_TOTAL,
                "predicted_total_2dp": EXPECTED_PRED_TOTAL_2DP,
                "shortfall_pct_2dp": EXPECTED_SHORTFALL_PCT_2DP,
                "cells": EXPECTED_CELLS,
            },
            "derivation": "sum of selected-role total_pred/total_actual/n over calibration bins; "
                          "shortfall_pct = (actual - predicted) / actual * 100",
            "units": totals,
            "drawn": totals_drawn,
            "outputs": totals_outputs,
        },
        "error_areas_th": {
            "accepted_signed_reduction_pct_4dp": {code: pct for code, _, _, _, pct in PROVINCES},
            "derivation": "hgb_deviance_higher_than_baseline_pct = -relative_deviance_reduction * 100; "
                          "relative_deviance_reduction = 1 - selected_deviance_sum / baseline_deviance_sum. "
                          "Sign flipped intentionally to show a positive 'HGB worse' magnitude; "
                          "this is relative deviance, not MAE and not an accident-rate change.",
            "unit": "daily",
            "dimension": "province (segment midpoint)",
            "rows": areas,
            "drawn": areas_drawn,
            "outputs": areas_outputs,
        },
        "font": {
            "family": family,
            "regular_path": str(regular_font),
            "bold_path": str(bold_font) if bold_font else None,
        },
        "matplotlib_version": matplotlib.__version__,
    }
    metadata_path = OUTPUT_DIR / "error_analysis_th_metadata.json"
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {metadata_path}")
    print(f"font: {family} ({regular_font})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
