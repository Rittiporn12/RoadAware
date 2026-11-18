#!/usr/bin/env python3
"""Render Thai actual-vs-predicted monthly line charts for the three V3 models.

Reads the accepted notebook-20 OOF arrays (2022-2023) read-only via mmap,
derives each config's routed_context policy as
where(context_mask == 1, context, core), sums every segment (and every 6 h
block) into daily totals, then into calendar-month totals. The monthly lines
are an aggregation of daily / 6 h predictions, NOT a monthly forecast model.
No training, no joblib loading, no smoothing, interpolation or date windows.

Before consuming any array the script checks its sha256 against both
arrays_index.json and the experiments manifest, validates the implicit
date -> segment -> block order and period offsets against the pinned
population_axes.json, and afterwards reconciles recomputed pooled metrics
with figure_method_comparison.csv.

Outputs (output/presentation-th/model-predictions/): one PNG + SVG per unit,
daily_totals.csv, monthly_totals.csv and metadata.json.

The caller is expected to set a writable MPLCONFIGDIR before running.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_thai_calibration as rc  # noqa: E402  (Thai font + figure helpers; sets Agg backend)

import matplotlib  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.ticker import FixedLocator, FuncFormatter  # noqa: E402

REPO_ROOT = rc.REPO_ROOT
BACKEND = REPO_ROOT / "backend"
ACCEPTED_ROOT = BACKEND / "rerun-spatial-model-016-002"
DATA_DIR = ACCEPTED_ROOT / "data" / "v3" / "spatial_experiments"
ARRAYS_DIR = DATA_DIR / "arrays"
INDEX_PATH = DATA_DIR / "arrays_index.json"
REPORT_DIR = ACCEPTED_ROOT / "reports" / "v3" / "spatial_experiments"
MANIFEST_PATH = REPORT_DIR / "spatial_experiments_manifest.json"
LOCK_PATH = REPORT_DIR / "experiment_lock.json"
SELECTION_PATH = REPORT_DIR / "selection_frozen.json"
AXES_PATH = BACKEND / "data" / "v3" / "spatial_preparation" / "population_axes.json"
EVAL_CONFIG_PATH = BACKEND / "config" / "spatial_evaluation_v3.json"
METHOD_CSV = REPO_ROOT / "output" / "spatial-model-results" / "v3-evaluation-017-002" / "figure_method_comparison.csv"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "output" / "presentation-th" / "model-predictions"

UNITS = ["daily", "6h"]
CONFIGS = ["poisson_a1e-05", "rf_poisson_fixed", "hgb_poisson_fixed"]
BASELINE = "segment_mean_k365"
SELECTED = "hgb_poisson_fixed::routed_context"
SERIES = [c + "::routed_context" for c in CONFIGS] + [BASELINE]

OOF_START, OOF_END = "2022-01-01", "2023-12-31"
EXPECTED_DAYS = 730
EXPECTED_SEGMENTS = 3105
EXPECTED_BLOCKS = {"daily": 1, "6h": 4}
EXPECTED_ROWS = {"daily": 2266650, "6h": 9066600}
EXPECTED_ACTUAL_TOTAL = 10701
EXPECTED_SELECTED_TOTAL = {"daily": 9574.098230117164, "6h": 9446.016245708677}
EXPECTED_MONTHS = 24
INDEX_ORDER = "date, then segment_id (sorted), then time_block; implicit axes = 19 population_axes.json"
AXES_ORDER = "date, then segment_id (sorted), then time_block (6h)"
INDEX_ROUTED_RULE = "derive as where(context_mask == 1, <config>__context, <config>__core)"
DEVIANCE_FLOOR = 1e-12  # backend/config/spatial_evaluation_v3.json metrics.deviance_floor (checked at runtime)
METRIC_TOL = 1e-9
TOTAL_TOL = 1e-7
CHUNK_DAYS = 31

TITLE = "แต่ละโมเดลทำนายใกล้กับข้อมูลที่บันทึกแค่ไหน?"
SUBTITLES = {
    "daily": "ผล OOF ปี 2022–2023 • ค่าทำนายรายวัน นำมารวมเป็นยอดรายเดือน (ไม่ใช่โมเดลพยากรณ์รายเดือน)",
    "6h": "ผล OOF ปี 2022–2023 • ค่าทำนายช่วงละ 6 ชั่วโมง นำมารวมเป็นยอดรายเดือน (ไม่ใช่โมเดลพยากรณ์รายเดือน)",
}
Y_LABEL = "จำนวนรายการรวมต่อเดือน"
X_LABEL = "เดือน (ค.ศ.)"
FOOTER = "รวมทุกช่วงถนนในพื้นที่ศึกษา • เส้นใกล้ข้อมูลที่บันทึก = ยอดรวมใกล้เคียง • ไม่ใช่คะแนนรายช่วงถนน"
THAI_MONTHS = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]
TOTAL_WORD = "รวม"

SERIES_LABELS = {
    "actual": "ข้อมูลที่บันทึก",
    "poisson_a1e-05::routed_context": "Poisson",
    "rf_poisson_fixed::routed_context": "Random Forest",
    "hgb_poisson_fixed::routed_context": "HGB (โมเดลที่เลือก)",
    BASELINE: "Baseline (ค่าเฉลี่ยช่วงถนน)",
}
# Okabe-Ito-leaning palette plus distinct markers so lines stay separable without colour.
SERIES_STYLE = {
    "actual": {"color": "#111111", "linewidth": 4.6, "linestyle": "-", "marker": "o", "markersize": 7.5, "zorder": 6},
    "poisson_a1e-05::routed_context": {"color": "#7B3FA0", "linewidth": 2.4, "linestyle": "-", "marker": "^", "markersize": 8, "zorder": 3},
    "rf_poisson_fixed::routed_context": {"color": "#0072B2", "linewidth": 2.4, "linestyle": "-", "marker": "s", "markersize": 7, "zorder": 4},
    "hgb_poisson_fixed::routed_context": {"color": "#009E8F", "linewidth": 3.8, "linestyle": "-", "marker": "D", "markersize": 7.5, "zorder": 5},
    BASELINE: {"color": "#8A8A8A", "linewidth": 2.6, "linestyle": (0, (6, 4)), "marker": None, "markersize": 0, "zorder": 2},
}
PLOT_ORDER = ["actual"] + SERIES

rc.ALL_TEXT = list(rc.ALL_TEXT) + [TITLE, Y_LABEL, X_LABEL, FOOTER, TOTAL_WORD] + list(SUBTITLES.values()) \
    + THAI_MONTHS + list(SERIES_LABELS.values())


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


def load_sources() -> dict:
    hashes = {p: rc.sha256_file(p) for p in (INDEX_PATH, MANIFEST_PATH, LOCK_PATH, SELECTION_PATH, AXES_PATH,
                                            EVAL_CONFIG_PATH, METHOD_CSV)}
    index, manifest, lock = read_json(INDEX_PATH), read_json(MANIFEST_PATH), read_json(LOCK_PATH)
    selection, axes, eval_cfg = read_json(SELECTION_PATH), read_json(AXES_PATH), read_json(EVAL_CONFIG_PATH)

    require(manifest.get("status") == "complete" and manifest.get("failed_checks") == [], "experiments manifest not complete/clean")
    data_files = manifest["data_files_gitignored"]
    require(data_files.get("arrays_index.json") == hashes[INDEX_PATH], "arrays_index.json hash differs from manifest")
    require(manifest["report_files"].get("experiment_lock.json") == hashes[LOCK_PATH], "experiment_lock.json hash differs from manifest")
    require(manifest["report_files"].get("selection_frozen.json") == hashes[SELECTION_PATH], "selection_frozen.json hash differs from manifest")
    require(index["experiment_lock_sha256"] == hashes[LOCK_PATH], "index lock sha differs from experiment_lock.json")
    require(lock["manager_pins"]["prepared_data_hashes"]["population_axes.json"] == hashes[AXES_PATH],
            "population_axes.json hash differs from the experiment lock pin")
    require(index["order"] == INDEX_ORDER, f"unexpected index order: {index['order']!r}")
    require(index["routed_context"] == INDEX_ROUTED_RULE, f"unexpected routed rule: {index['routed_context']!r}")
    require(axes["order"] == AXES_ORDER, f"unexpected population axes order: {axes['order']!r}")
    require(float(eval_cfg["metrics"]["deviance_floor"]) == DEVIANCE_FLOOR, "deviance floor differs from evaluation config")
    for unit in UNITS:
        sel = selection["units"][unit]
        require(sel["selected_method"] == SELECTED, f"{unit}: frozen selection is {sel['selected_method']!r}")
        require(sel["strongest_baseline"] == BASELINE, f"{unit}: strongest baseline is {sel['strongest_baseline']!r}")
    return {"hashes": hashes, "index": index, "manifest": manifest, "axes": axes}


def validate_axes(axes: dict) -> dict:
    segments, dates, blocks = axes["segments"], axes["dates"], axes["blocks"]
    require(len(segments) == EXPECTED_SEGMENTS, f"expected {EXPECTED_SEGMENTS} segments, got {len(segments)}")
    require(segments == sorted(segments) and len(set(segments)) == len(segments), "segments not sorted/unique")
    require(len(blocks) == EXPECTED_BLOCKS["6h"], f"unexpected blocks {blocks}")
    parsed = [dt.date.fromisoformat(d) for d in dates]
    require(all((b - a).days == 1 for a, b in zip(parsed, parsed[1:])), "population dates not contiguous daily")
    date_pos = {d: i for i, d in enumerate(dates)}
    require(OOF_START in date_pos and OOF_END in date_pos, "OOF window missing from population axes")
    oof_dates = dates[date_pos[OOF_START]: date_pos[OOF_END] + 1]
    require(len(oof_dates) == EXPECTED_DAYS, f"expected {EXPECTED_DAYS} OOF dates, got {len(oof_dates)}")
    return {"segments": segments, "blocks": blocks, "date_pos": date_pos, "oof_dates": oof_dates}


def validate_unit_layout(unit: str, entry: dict, ax: dict) -> dict:
    nb = EXPECTED_BLOCKS[unit]
    per_day = len(ax["segments"]) * nb
    n = EXPECTED_DAYS * per_day
    require(n == EXPECTED_ROWS[unit], f"{unit}: axes give {n} rows, expected {EXPECTED_ROWS[unit]}")
    periods = entry["oof_periods"]
    d0 = ax["date_pos"][OOF_START]
    require(periods[0]["start"] == OOF_START and periods[-1]["end"] == OOF_END, f"{unit}: OOF periods do not span {OOF_START}..{OOF_END}")
    cursor = 0
    for p in periods:
        start, end = ax["date_pos"][p["start"]], ax["date_pos"][p["end"]]
        require(p["row_offset"] == (start - d0) * per_day == cursor, f"{unit}/{p['id']}: row_offset mismatch")
        require(p["rows"] == (end - start + 1) * per_day, f"{unit}/{p['id']}: rows mismatch")
        cursor += p["rows"]
    require(cursor == n, f"{unit}: periods cover {cursor} rows, expected {n}")
    return {"blocks_per_day": nb, "rows_per_day": per_day, "rows": n, "periods": periods}


def array_keys() -> list[str]:
    keys = []
    for cid in CONFIGS:
        keys += [cid + "::core", cid + "::context"]
    return keys + [BASELINE, "y", "context_mask"]


def open_unit_arrays(unit: str, entry: dict, manifest: dict, n: int) -> tuple[dict, dict]:
    """Hash-verify each needed array against index + manifest, then mmap it read-only."""
    arrays, info = {}, {}
    data_files = manifest["data_files_gitignored"]
    for key in array_keys():
        meta = entry["oof"].get(key)
        require(meta is not None, f"{unit}: {key} missing from arrays_index.json")
        path = ARRAYS_DIR / meta["file"]
        require(path.is_file(), f"{unit}: array not found: {path}")
        manifest_sha = data_files.get("arrays/" + meta["file"])
        actual_sha = rc.sha256_file(path)
        require(actual_sha == meta["sha256"] == manifest_sha, f"{unit}: {meta['file']} sha256 mismatch")
        require(path.stat().st_size == meta["bytes"], f"{unit}: {meta['file']} size mismatch")
        arr = np.load(path, mmap_mode="r", allow_pickle=False)
        expected_dtype = "uint8" if key == "context_mask" else "float64"
        require(str(arr.dtype) == meta["dtype"] == expected_dtype, f"{unit}: {meta['file']} dtype {arr.dtype}")
        require(list(arr.shape) == meta["shape"] == [n], f"{unit}: {meta['file']} shape {arr.shape}")
        arrays[key] = arr
        info[key] = {"file": meta["file"], "kind": meta["kind"], "dtype": str(arr.dtype), "shape": list(arr.shape),
                     "bytes": meta["bytes"], "sha256": actual_sha, "index_sha256": meta["sha256"], "manifest_sha256": manifest_sha}
    return arrays, info


# ---------------------------------------------------------------- aggregation


def deviance_terms(y: np.ndarray, mu: np.ndarray) -> np.ndarray:
    # Same unit deviance as notebook 20 poisson_deviance_terms (floor applied to mu only).
    m = np.maximum(mu, DEVIANCE_FLOOR)
    ylog = np.where(y > 0, y * np.log(np.where(y > 0, y, 1.0) / m), 0.0)
    return 2.0 * (ylog - (y - m))


def aggregate_unit(unit: str, arrays: dict, layout: dict) -> dict:
    per_day = layout["rows_per_day"]
    daily = {name: np.zeros(EXPECTED_DAYS) for name in ["actual"] + SERIES}
    acc = {name: {"abs": 0.0, "sq": 0.0, "dev": 0.0} for name in SERIES}
    checks = {"context_nonfinite_where_mask0": {c: 0 for c in CONFIGS}, "mask_ones": 0, "y_nonzero_cells": 0}
    for d0 in range(0, EXPECTED_DAYS, CHUNK_DAYS):
        d1 = min(d0 + CHUNK_DAYS, EXPECTED_DAYS)
        sl = slice(d0 * per_day, d1 * per_day)
        y = np.asarray(arrays["y"][sl], dtype=np.float64)
        require(bool(np.isfinite(y).all()) and bool((y >= 0).all()), f"{unit}: y not finite/non-negative")
        require(bool((y == np.floor(y)).all()), f"{unit}: y not integer-valued")
        mask = np.asarray(arrays["context_mask"][sl])
        require(bool(np.isin(mask, (0, 1)).all()), f"{unit}: context_mask has values other than 0/1")
        on = mask == 1
        checks["mask_ones"] += int(on.sum())
        checks["y_nonzero_cells"] += int((y > 0).sum())
        daily["actual"][d0:d1] = y.reshape(d1 - d0, per_day).sum(axis=1)
        preds = {}
        for cid in CONFIGS:
            core = np.asarray(arrays[cid + "::core"][sl])
            ctx = np.asarray(arrays[cid + "::context"][sl])
            require(bool(np.isfinite(core).all()) and bool((core >= 0).all()), f"{unit}: {cid} core not finite/non-negative")
            require(bool(np.isfinite(ctx[on]).all()) and bool((ctx[on] >= 0).all()),
                    f"{unit}: {cid} context not finite/non-negative where context_mask == 1")
            checks["context_nonfinite_where_mask0"][cid] += int((~np.isfinite(ctx[~on])).sum())
            preds[cid + "::routed_context"] = np.where(mask == 1, ctx, core)
        base = np.asarray(arrays[BASELINE][sl])
        require(bool(np.isfinite(base).all()) and bool((base >= 0).all()), f"{unit}: baseline not finite/non-negative")
        preds[BASELINE] = base
        for name, mu in preds.items():
            err = mu - y
            acc[name]["abs"] += float(np.abs(err).sum())
            acc[name]["sq"] += float((err * err).sum())
            acc[name]["dev"] += float(deviance_terms(y, mu).sum())
            daily[name][d0:d1] = mu.reshape(d1 - d0, per_day).sum(axis=1)
    n = layout["rows"]
    metrics = {name: {"n": n, "mean_poisson_deviance": a["dev"] / n, "mae": a["abs"] / n, "rmse": math.sqrt(a["sq"] / n)}
               for name, a in acc.items()}
    return {"daily": daily, "metrics": metrics, "checks": checks}


def full_totals(unit: str, arrays: dict) -> dict:
    """Independent whole-array totals (not via daily sums) for the conservation check."""
    totals = {"actual": float(np.sum(arrays["y"], dtype=np.float64))}
    mask = arrays["context_mask"]
    for cid in CONFIGS:
        total = 0.0
        for start in range(0, mask.shape[0], 1 << 22):
            sl = slice(start, start + (1 << 22))
            total += float(np.where(np.asarray(mask[sl]) == 1, arrays[cid + "::context"][sl], arrays[cid + "::core"][sl]).sum())
        totals[cid + "::routed_context"] = total
    totals[BASELINE] = float(np.sum(arrays[BASELINE], dtype=np.float64))
    return totals


def monthly_from_daily(dates: list[str], daily: dict) -> tuple[list[str], dict, list[int]]:
    months = sorted({d[:7] for d in dates})
    require(len(months) == EXPECTED_MONTHS, f"expected {EXPECTED_MONTHS} months, got {len(months)}")
    month_of = np.array([months.index(d[:7]) for d in dates])
    n_days = [int((month_of == i).sum()) for i in range(len(months))]
    for i, m in enumerate(months):
        y, mo = int(m[:4]), int(m[5:7])
        nxt = dt.date(y + (mo == 12), mo % 12 + 1, 1)
        require(n_days[i] == (nxt - dt.date(y, mo, 1)).days, f"month {m} incomplete ({n_days[i]} days)")
    monthly = {name: np.bincount(month_of, weights=vals, minlength=len(months)) for name, vals in daily.items()}
    return months, monthly, n_days


def reconcile_metrics(unit: str, metrics: dict) -> list[dict]:
    with METHOD_CSV.open(newline="", encoding="utf-8") as handle:
        rows = [r for r in csv.DictReader(handle) if r["unit"] == unit]
    by_method = {r["method"]: r for r in rows}
    out = []
    for name in SERIES:
        src = by_method.get(name)
        require(src is not None, f"{unit}: {name} missing from {METHOD_CSV.name}")
        require(int(src["n"]) == metrics[name]["n"], f"{unit}/{name}: n differs from source CSV")
        row = {"unit": unit, "method": name, "n": metrics[name]["n"]}
        for key in ("mean_poisson_deviance", "mae", "rmse"):
            source = float(src[key])
            diff = abs(metrics[name][key] - source)
            require(diff <= METRIC_TOL, f"{unit}/{name}: {key} recomputed {metrics[name][key]!r} vs source {source!r} (diff {diff:.3e})")
            row[key] = {"recomputed": metrics[name][key], "source": source, "abs_diff": diff}
        out.append(row)
    return out


# ---------------------------------------------------------------- plotting


def tick_label(months: list[str], i: int) -> str:
    return f"{THAI_MONTHS[int(months[i][5:7]) - 1]}\n{months[i][:4]}"


def draw_unit(unit: str, months: list[str], monthly: dict):
    fig = plt.figure(figsize=rc.FIG_SIZE_IN, dpi=rc.DPI)
    fig.text(0.5, 0.955, TITLE, ha="center", va="top", fontsize=30, fontweight="bold", color=rc.NAVY)
    fig.text(0.5, 0.892, SUBTITLES[unit], ha="center", va="top", fontsize=17, color=rc.TEXT_GREY)
    ax = fig.add_axes([0.085, 0.205, 0.885, 0.545])
    x = np.arange(len(months), dtype=float)
    plotted = {}
    handles = []
    for name in PLOT_ORDER:
        style = SERIES_STYLE[name]
        ys = [float(v) for v in monthly[name]]
        (line,) = ax.plot(x, ys, color=style["color"], linewidth=style["linewidth"], linestyle=style["linestyle"],
                          marker=style["marker"], markersize=style["markersize"], markeredgecolor="white",
                          markeredgewidth=1.2, zorder=style["zorder"], solid_capstyle="round")
        drawn = [float(v) for v in line.get_ydata()]
        require(drawn == ys and len(drawn) == EXPECTED_MONTHS, f"{unit}/{name}: drawn points differ from monthly totals")
        plotted[name] = drawn
        label = f"{SERIES_LABELS[name]} • {TOTAL_WORD} {sum(ys):,.0f}"
        handles.append(Line2D([], [], color=style["color"], linewidth=style["linewidth"], linestyle=style["linestyle"],
                              marker=style["marker"], markersize=style["markersize"], markeredgecolor="white", label=label))

    ymax = max(max(v) for v in plotted.values())
    ax.set_xlim(-0.5, len(months) - 0.5)
    ax.set_ylim(0, ymax * 1.12)
    major = [i for i, m in enumerate(months) if (int(m[5:7]) - 1) % 3 == 0]
    ax.xaxis.set_major_locator(FixedLocator(major))
    ax.xaxis.set_minor_locator(FixedLocator(list(range(len(months)))))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _pos: tick_label(months, int(round(v)))))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _pos: f"{v:,.0f}"))
    ax.tick_params(axis="both", which="major", labelsize=15, colors=rc.TEXT_GREY, length=6)
    ax.tick_params(axis="x", which="minor", length=3, colors=rc.SPINE_GREY)
    ax.set_ylabel(Y_LABEL, fontsize=17, color=rc.TEXT_GREY, labelpad=12)
    ax.set_xlabel(X_LABEL, fontsize=15, color=rc.TEXT_GREY, labelpad=8)
    ax.grid(True, which="major", color=rc.GRID_GREY, linewidth=0.9)
    ax.set_axisbelow(True)
    year_split = next(i for i, m in enumerate(months) if m[:4] != months[0][:4])
    ax.axvline(year_split - 0.5, color=rc.SPINE_GREY, linewidth=1.2, linestyle=":", zorder=1)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(rc.SPINE_GREY)

    fig.legend(handles=handles, loc="center", bbox_to_anchor=(0.5, 0.808), ncol=3, frameon=False, fontsize=15,
               handlelength=3.0, columnspacing=2.4, labelspacing=0.55)
    fig.text(0.5, 0.03, FOOTER, ha="center", va="center", fontsize=14, color=rc.FOOTER_GREY)
    return fig, plotted


def check_layout(fig) -> None:
    clipped = rc.check_text_inside_figure(fig)
    require(not clipped, f"text extends outside the figure: {clipped}")
    renderer = fig.canvas.get_renderer()
    legend_box = fig.legends[0].get_window_extent(renderer)
    ax = fig.axes[0]
    require(not legend_box.overlaps(ax.get_window_extent(renderer)), "legend overlaps the plot area")
    for text in fig.texts:
        require(not legend_box.overlaps(text.get_window_extent(renderer)), f"legend overlaps text {text.get_text()!r}")


# ---------------------------------------------------------------- outputs


def fmt(v: float) -> str:
    return repr(float(v))


def write_csvs(out_dir: Path, results: dict) -> tuple[Path, Path]:
    cols = ["actual"] + SERIES
    daily_path, monthly_path = out_dir / "daily_totals.csv", out_dir / "monthly_totals.csv"
    with daily_path.open("w", newline="", encoding="utf-8") as handle:
        w = csv.writer(handle, lineterminator="\n")
        w.writerow(["unit", "date"] + cols)
        for unit in UNITS:
            r = results[unit]
            for i, d in enumerate(r["dates"]):
                w.writerow([unit, d] + [fmt(r["daily"][c][i]) for c in cols])
    with monthly_path.open("w", newline="", encoding="utf-8") as handle:
        w = csv.writer(handle, lineterminator="\n")
        w.writerow(["unit", "month", "n_days"] + cols)
        for unit in UNITS:
            r = results[unit]
            for i, m in enumerate(r["months"]):
                w.writerow([unit, m, r["n_days"][i]] + [fmt(r["monthly"][c][i]) for c in cols])
    return daily_path, monthly_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)

    try:
        src = load_sources()
        ax = validate_axes(src["axes"])
        results = {}
        for unit in UNITS:
            entry = src["index"]["units"][unit]
            layout = validate_unit_layout(unit, entry, ax)
            arrays, array_info = open_unit_arrays(unit, entry, src["manifest"], layout["rows"])
            agg = aggregate_unit(unit, arrays, layout)
            totals = full_totals(unit, arrays)
            months, monthly, n_days = monthly_from_daily(ax["oof_dates"], agg["daily"])
            conservation = {}
            for name in ["actual"] + SERIES:
                d_sum, m_sum = float(agg["daily"][name].sum()), float(monthly[name].sum())
                diff = max(abs(d_sum - totals[name]), abs(m_sum - totals[name]))
                require(diff <= TOTAL_TOL, f"{unit}/{name}: daily/monthly totals do not conserve the full total (diff {diff:.3e})")
                conservation[name] = {"full_array_total": totals[name], "sum_of_daily": d_sum, "sum_of_monthly": m_sum, "max_abs_diff": diff}
            require(totals["actual"] == EXPECTED_ACTUAL_TOTAL, f"{unit}: actual total {totals['actual']} != {EXPECTED_ACTUAL_TOTAL}")
            sel_diff = abs(totals[SELECTED] - EXPECTED_SELECTED_TOTAL[unit])
            require(sel_diff <= TOTAL_TOL, f"{unit}: HGB routed total {totals[SELECTED]!r} vs expected {EXPECTED_SELECTED_TOTAL[unit]!r}")
            reconciliation = reconcile_metrics(unit, agg["metrics"])
            results[unit] = {"layout": layout, "array_info": array_info, "dates": ax["oof_dates"], "daily": agg["daily"],
                             "months": months, "monthly": monthly, "n_days": n_days, "totals": totals,
                             "conservation": conservation, "selected_total_abs_diff": sel_diff,
                             "reconciliation": reconciliation, "checks": agg["checks"]}
            del arrays
    except DataError as exc:
        raise SystemExit(f"invalid model prediction data: {exc}") from exc

    regular_font, bold_font = rc.locate_thai_font()
    family = rc.register_font(regular_font, bold_font)
    rc.configure_style(family, svg_editable=True)

    out_dir = args.output_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs = {}
    for unit in UNITS:
        r = results[unit]
        fig, plotted = draw_unit(unit, r["months"], r["monthly"])
        try:
            check_layout(fig)
        except DataError as exc:
            raise SystemExit(f"layout check failed ({unit}): {exc}") from exc
        png_path, svg_path = out_dir / f"prediction_lines_{unit}_th.png", out_dir / f"prediction_lines_{unit}_th.svg"
        fig.savefig(png_path, dpi=rc.DPI, format="png")
        fig.savefig(svg_path, format="svg")
        plt.close(fig)
        width_px, height_px = rc.png_size(png_path)
        if width_px < 3000 or height_px < 1688:
            raise SystemExit(f"{png_path.name} is {width_px}x{height_px}, below 3000x1688")
        r["plotted_points_per_series"] = {name: len(v) for name, v in plotted.items()}
        outputs[png_path.name] = {"width_px": width_px, "height_px": height_px, "sha256": rc.sha256_file(png_path)}
        outputs[svg_path.name] = {"text_editable": True, "sha256": rc.sha256_file(svg_path)}
    daily_path, monthly_path = write_csvs(out_dir, results)
    outputs[daily_path.name] = {"rows": len(UNITS) * EXPECTED_DAYS, "sha256": rc.sha256_file(daily_path)}
    outputs[monthly_path.name] = {"rows": len(UNITS) * EXPECTED_MONTHS, "sha256": rc.sha256_file(monthly_path)}

    metadata = {
        "purpose": "Monthly totals of 2022-2023 OOF daily / 6 h predictions summed over every segment (and block); "
                   "an aggregation for presentation, NOT a monthly forecast model and NOT a per-segment score.",
        "caveat": "Total-line closeness shows aggregate agreement only; model ranking uses the pooled per-cell metrics below.",
        "sources": {rel(p): h for p, h in src["hashes"].items()},
        "population_axes": {"order": src["axes"]["order"], "segments": len(ax["segments"]), "blocks": ax["blocks"],
                            "oof_first_date": ax["oof_dates"][0], "oof_last_date": ax["oof_dates"][-1],
                            "oof_days": len(ax["oof_dates"])},
        "array_order": src["index"]["order"],
        "methods": {
            "routed_context": "np.where(context_mask == 1, <config>__context, <config>__core) per config (arrays_index rule)",
            "configs": CONFIGS, "selected": SELECTED, "baseline": BASELINE,
            "actual": "oof_<unit>_y.npy",
            "aggregation": "sum over all segments (x 4 blocks for 6h) per date, then calendar-month sums; no smoothing, "
                           "interpolation, fitted curves or date windows",
            "deviance": f"2*(y*log(y/m) - (y - m)), m = max(mu, {DEVIANCE_FLOOR}), y*log := 0 for y == 0",
            "loading": "np.load(mmap_mode='r', allow_pickle=False); no model files loaded, no training",
        },
        "units": {
            unit: {
                "rows": r["layout"]["rows"], "rows_per_day": r["layout"]["rows_per_day"],
                "blocks_per_day": r["layout"]["blocks_per_day"], "oof_periods": r["layout"]["periods"],
                "arrays": r["array_info"], "checks": r["checks"],
                "totals": r["totals"], "conservation": r["conservation"],
                "expected_actual_total": EXPECTED_ACTUAL_TOTAL,
                "expected_selected_total": EXPECTED_SELECTED_TOTAL[unit],
                "selected_total_abs_diff": r["selected_total_abs_diff"],
                "metric_reconciliation": r["reconciliation"],
                "months": r["months"], "month_days": r["n_days"],
                "monthly_totals": {name: [float(v) for v in vals] for name, vals in r["monthly"].items()},
                "plotted_points_per_series": r["plotted_points_per_series"],
            }
            for unit, r in results.items()
        },
        "tolerances": {"metric_abs": METRIC_TOL, "total_abs": TOTAL_TOL},
        "font": {"family": family, "regular_path": str(regular_font), "bold_path": str(bold_font) if bold_font else None},
        "outputs": outputs,
        "versions": {"numpy": np.__version__, "matplotlib": matplotlib.__version__, "python": sys.version.split()[0]},
    }
    metadata_path = out_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for name, info in outputs.items():
        print(f"wrote {out_dir / name}" + (f" ({info['width_px']}x{info['height_px']})" if "width_px" in info else ""))
    print(f"wrote {metadata_path}")
    for unit in UNITS:
        t = results[unit]["totals"]
        print(unit, " ".join(f"{k}={v:.6f}" for k, v in t.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
