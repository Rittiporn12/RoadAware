#!/usr/bin/env python3
"""Render the Thai calibration figure for the Evaluation Metrics slide.

Reads the accepted figure_calibration.csv, validates it, and plots every row
as-is (no refit, rebinning, or recalibration). Outputs a PNG, an SVG with
editable text, and a metadata JSON recording the source hash, every plotted
point, and the rate reconciliation.

The caller is expected to set a writable MPLCONFIGDIR before running.
"""

from __future__ import annotations

import argparse
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
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.ticker import LogLocator, NullFormatter  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = (
    REPO_ROOT / "output" / "spatial-model-results" / "v3-evaluation-017-002" / "figure_calibration.csv"
)
DEFAULT_OUTPUT_DIR = REPO_ROOT / "output" / "presentation-th"

EXPECTED_HEADER = [
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
UNITS = ["daily", "6h"]
ROLES = ["selected", "baseline"]
RATE_TOLERANCE = 1e-12
LOG_MARGIN_DECADES = 0.3

# 15 x 8.44 in at 200 dpi -> 3000 x 1688 px (16:9).
FIG_SIZE_IN = (15.0, 8.44)
DPI = 200

NAVY = "#1B2A49"
TEXT_GREY = "#4B5563"
FOOTER_GREY = "#6B7280"
GRID_GREY = "#E5E7EB"
SPINE_GREY = "#9CA3AF"
DIAGONAL_GREY = "#374151"
TEAL = "#0F8B8D"
ORANGE = "#F28C28"

TITLE = "ค่าทำนายใกล้เคียงกับข้อมูลที่บันทึกแค่ไหน?"
SUBTITLE = "ผล OOF ปี 2022–2023 • HGB เทียบกับ Baseline"
PANEL_TITLES = {"daily": "รายวัน", "6h": "ช่วงละ 6 ชั่วโมง"}
X_LABEL = "ค่าทำนาย (รายการ / กม. / ช่วงเวลา)"
Y_LABEL = "ข้อมูลที่บันทึก (รายการ / กม. / ช่วงเวลา)"
ROLE_LABELS = {"selected": "HGB (โมเดลที่เลือก)", "baseline": "Baseline"}
DIAGONAL_LABEL = "ทำนายตรงกับข้อมูล"
EXPLANATION = "ใกล้เส้นประ = สอดคล้อง  |  เหนือเส้น = ทำนายต่ำ  |  ใต้เส้น = ทำนายสูง"
FOOTER = "แกนลอการิทึม • เฉพาะรายการที่ผ่านการคัดเลือกและเชื่อมถนนได้"
ROLE_STYLE = {
    "selected": {"color": TEAL, "marker": "o"},
    "baseline": {"color": ORANGE, "marker": "s"},
}

ALL_TEXT = [TITLE, SUBTITLE, X_LABEL, Y_LABEL, DIAGONAL_LABEL, EXPLANATION, FOOTER]
ALL_TEXT += list(PANEL_TITLES.values()) + list(ROLE_LABELS.values())

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
            try:
                n = int(raw["n"])
            except ValueError as exc:
                raise DataError(f"row {row_number}: n={raw['n']!r} is not an integer") from exc
            row = {
                "csv_row_number": row_number,
                "unit": raw["unit"],
                "role": raw["role"],
                "method": raw["method"],
                "group": raw["group"],
                "n": n,
            }
            for field in EXPECTED_HEADER[5:]:
                row[field] = _parse_float(raw[field], field, row_number)
            rows.append(row)
    return rows


def validate_rows(rows: list[dict]) -> list[dict]:
    """Check structure and recompute rates; return per-row reconciliation."""
    if not rows:
        raise DataError("CSV has no data rows")
    reconciliation = []
    methods: dict[tuple[str, str], set[str]] = {}
    groups: dict[tuple[str, str], list[str]] = {}
    for row in rows:
        num = row["csv_row_number"]
        if row["unit"] not in UNITS:
            raise DataError(f"row {num}: unexpected unit {row['unit']!r}")
        if row["role"] not in ROLES:
            raise DataError(f"row {num}: unexpected role {row['role']!r}")
        if row["n"] <= 0:
            raise DataError(f"row {num}: n must be positive")
        if row["total_pred"] < 0 or row["total_actual"] < 0:
            raise DataError(f"row {num}: totals must be non-negative")
        exposure = row["exposure_segment_km_periods"]
        if exposure <= 0:
            raise DataError(f"row {num}: exposure must be positive")
        x = row["predicted_records_per_km_period"]
        y = row["observed_records_per_km_period"]
        if x <= 0 or y <= 0:
            raise DataError(f"row {num}: rates must be positive for a log-log plot (x={x}, y={y})")
        x_recomputed = row["total_pred"] / exposure
        y_recomputed = row["total_actual"] / exposure
        x_diff = abs(x_recomputed - x)
        y_diff = abs(y_recomputed - y)
        if x_diff > RATE_TOLERANCE or y_diff > RATE_TOLERANCE:
            raise DataError(
                f"row {num}: rate mismatch (pred diff {x_diff:.3e}, observed diff {y_diff:.3e}) "
                f"exceeds tolerance {RATE_TOLERANCE}"
            )
        key = (row["unit"], row["role"])
        methods.setdefault(key, set()).add(row["method"])
        groups.setdefault(key, []).append(row["group"])
        reconciliation.append(
            {
                "csv_row_number": num,
                "unit": row["unit"],
                "role": row["role"],
                "x_recomputed_total_pred_over_exposure": x_recomputed,
                "y_recomputed_total_actual_over_exposure": y_recomputed,
                "x_abs_diff": x_diff,
                "y_abs_diff": y_diff,
                "within_tolerance": True,
            }
        )
    expected_keys = {(unit, role) for unit in UNITS for role in ROLES}
    if set(methods) != expected_keys:
        missing = sorted(expected_keys - set(methods))
        raise DataError(f"missing unit/role series: {missing}")
    for key, found in methods.items():
        if len(found) != 1:
            raise DataError(f"{key}: expected exactly one method, found {sorted(found)}")
    for key, found in groups.items():
        if len(found) != len(set(found)):
            raise DataError(f"{key}: duplicate group labels")
    return reconciliation


def series_for(rows: list[dict], unit: str, role: str) -> list[dict]:
    # CSV order is preserved; no sorting or rebinning.
    return [row for row in rows if row["unit"] == unit and row["role"] == role]


def shared_log_bounds(rows: list[dict]) -> tuple[float, float]:
    values = [row["predicted_records_per_km_period"] for row in rows]
    values += [row["observed_records_per_km_period"] for row in rows]
    low = math.log10(min(values)) - LOG_MARGIN_DECADES
    high = math.log10(max(values)) + LOG_MARGIN_DECADES
    return 10.0**low, 10.0**high


# ---------------------------------------------------------------- plotting


def configure_style(family: str, svg_editable: bool) -> None:
    plt.rcParams.update(
        {
            "font.family": [family, "DejaVu Sans"],
            "axes.unicode_minus": False,
            "svg.fonttype": "none" if svg_editable else "path",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )


def draw_figure(rows: list[dict], bounds: tuple[float, float]):
    fig = plt.figure(figsize=FIG_SIZE_IN, dpi=DPI)
    width_in, height_in = FIG_SIZE_IN

    fig.text(0.5, 0.955, TITLE, ha="center", va="top", fontsize=30, fontweight="bold", color=NAVY)
    fig.text(0.5, 0.892, SUBTITLE, ha="center", va="top", fontsize=18, color=TEXT_GREY)

    # Two square panels with identical log ranges, so the diagonal sits at 45 degrees.
    bottom, top = 0.205, 0.755
    side_h = top - bottom
    side_w = side_h * height_in / width_in
    gap = 0.09
    left0 = (1.0 - (2 * side_w + gap)) / 2 + 0.012
    axes = {
        "daily": fig.add_axes([left0, bottom, side_w, side_h]),
        "6h": fig.add_axes([left0 + side_w + gap, bottom, side_w, side_h]),
    }

    low, high = bounds
    plotted = []
    for unit, ax in axes.items():
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(low, high)
        ax.set_ylim(low, high)
        ax.plot([low, high], [low, high], linestyle=(0, (6, 4)), linewidth=2.0, color=DIAGONAL_GREY, zorder=2)
        for role in ROLES:
            series = series_for(rows, unit, role)
            xs = [row["predicted_records_per_km_period"] for row in series]
            ys = [row["observed_records_per_km_period"] for row in series]
            style = ROLE_STYLE[role]
            (line,) = ax.plot(
                xs,
                ys,
                color=style["color"],
                marker=style["marker"],
                markersize=11,
                markeredgecolor="white",
                markeredgewidth=1.6,
                linewidth=2.6,
                zorder=3 if role == "baseline" else 4,
            )
            drawn_x = [float(v) for v in line.get_xdata()]
            drawn_y = [float(v) for v in line.get_ydata()]
            if drawn_x != xs or drawn_y != ys:
                raise RuntimeError(f"{unit}/{role}: drawn points differ from CSV values")
            for row, x, y in zip(series, drawn_x, drawn_y):
                if not (low <= x <= high and low <= y <= high):
                    raise RuntimeError(f"row {row['csv_row_number']}: point outside axis bounds")
                plotted.append(
                    {
                        "csv_row_number": row["csv_row_number"],
                        "unit": unit,
                        "role": role,
                        "method": row["method"],
                        "group": row["group"],
                        "n": row["n"],
                        "x_predicted_records_per_km_period": x,
                        "y_observed_records_per_km_period": y,
                    }
                )

        ax.set_title(PANEL_TITLES[unit], fontsize=23, fontweight="bold", color=NAVY, pad=14)
        ax.set_xlabel(X_LABEL, fontsize=16, color=TEXT_GREY, labelpad=10)
        ax.xaxis.set_major_locator(LogLocator(base=10))
        ax.yaxis.set_major_locator(LogLocator(base=10))
        ax.xaxis.set_minor_locator(LogLocator(base=10, subs=range(2, 10)))
        ax.yaxis.set_minor_locator(LogLocator(base=10, subs=range(2, 10)))
        ax.xaxis.set_minor_formatter(NullFormatter())
        ax.yaxis.set_minor_formatter(NullFormatter())
        ax.tick_params(axis="both", which="major", labelsize=14, colors=TEXT_GREY, length=6)
        ax.tick_params(axis="both", which="minor", length=3, colors=SPINE_GREY)
        ax.grid(True, which="major", color=GRID_GREY, linewidth=0.9)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(SPINE_GREY)
    axes["daily"].set_ylabel(Y_LABEL, fontsize=16, color=TEXT_GREY, labelpad=10)

    handles = [
        Line2D([], [], color=TEAL, marker="o", markersize=11, markeredgecolor="white", linewidth=2.6,
               label=ROLE_LABELS["selected"]),
        Line2D([], [], color=ORANGE, marker="s", markersize=11, markeredgecolor="white", linewidth=2.6,
               label=ROLE_LABELS["baseline"]),
        Line2D([], [], color=DIAGONAL_GREY, linestyle=(0, (6, 4)), linewidth=2.0, label=DIAGONAL_LABEL),
    ]
    fig.legend(
        handles=handles,
        loc="center",
        bbox_to_anchor=(0.5, 0.825),
        ncol=3,
        frameon=False,
        fontsize=17,
        handlelength=2.8,
        columnspacing=2.8,
    )

    fig.text(0.5, 0.072, EXPLANATION, ha="center", va="center", fontsize=18, color=NAVY)
    fig.text(0.5, 0.026, FOOTER, ha="center", va="center", fontsize=12, color=FOOTER_GREY)
    return fig, plotted


def check_text_inside_figure(fig) -> list[str]:
    """Return labels of any text artists whose extents fall outside the canvas."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    fig_box = fig.bbox
    problems = []
    texts = list(fig.texts)
    for ax in fig.axes:
        texts += [ax.title, ax.xaxis.label, ax.yaxis.label]
        texts += [t.label1 for t in ax.xaxis.get_major_ticks() if t.label1.get_visible()]
        texts += [t.label1 for t in ax.yaxis.get_major_ticks() if t.label1.get_visible()]
    for legend in fig.legends:
        texts += list(legend.get_texts())
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
    rows = load_rows(input_path)
    try:
        reconciliation = validate_rows(rows)
    except DataError as exc:
        raise SystemExit(f"invalid calibration data: {exc}") from exc

    regular_font, bold_font = locate_thai_font()
    family = register_font(regular_font, bold_font)
    configure_style(family, svg_editable=True)

    bounds = shared_log_bounds(rows)
    fig, plotted = draw_figure(rows, bounds)
    if len(plotted) != len(rows):
        raise RuntimeError(f"plotted {len(plotted)} points but CSV has {len(rows)} rows")
    clipped = check_text_inside_figure(fig)
    if clipped:
        raise RuntimeError(f"text extends outside the figure: {clipped}")

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    png_path = output_dir / "calibration_th.png"
    svg_path = output_dir / "calibration_th.svg"
    metadata_path = output_dir / "calibration_th_metadata.json"

    fig.savefig(png_path, dpi=DPI, format="png")
    fig.savefig(svg_path, format="svg")
    plt.close(fig)
    width_px, height_px = png_size(png_path)

    counts = {
        f"{unit}/{role}": sum(1 for p in plotted if p["unit"] == unit and p["role"] == role)
        for unit in UNITS
        for role in ROLES
    }
    metadata = {
        "source_csv": str(input_path.relative_to(REPO_ROOT) if input_path.is_relative_to(REPO_ROOT) else input_path),
        "source_csv_sha256": csv_sha256,
        "source_row_count": len(rows),
        "plotted_point_count": len(plotted),
        "plotted_points_per_series": counts,
        "methods": {
            f"{unit}/{role}": series_for(rows, unit, role)[0]["method"] for unit in UNITS for role in ROLES
        },
        "data_transformations": "none (CSV rates plotted as-is; no refit, rebinning, or recalibration)",
        "axes": {
            "scale": "log10 (both axes, shared across panels)",
            "lower_bound": bounds[0],
            "upper_bound": bounds[1],
            "margin_decades": LOG_MARGIN_DECADES,
            "x": "predicted_records_per_km_period",
            "y": "observed_records_per_km_period",
        },
        "reconciliation": {
            "tolerance_abs": RATE_TOLERANCE,
            "all_within_tolerance": all(r["within_tolerance"] for r in reconciliation),
            "max_x_abs_diff": max(r["x_abs_diff"] for r in reconciliation),
            "max_y_abs_diff": max(r["y_abs_diff"] for r in reconciliation),
            "rows": reconciliation,
        },
        "plotted_points": plotted,
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
