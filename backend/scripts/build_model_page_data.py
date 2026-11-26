"""Build frontend/public/data/model-v1.json for the website's "โมเดล" page from the project's own reports.

  model selection  backend/rerun-spatial-model-national-*/reports/v4/spatial_experiments/
                   (leaderboard_oof.csv, fold_metrics.csv, folds.csv, selection.csv) — rolling-origin backtest 2565–2566
  unseen test      backend/rerun-2026-eval-national-*/reports/v4/evaluation_2026/method_comparison.csv — 2569 Jan–Sep
  ML families      backend/rerun-spatial-model-pilot-repro-*/reports/v3/spatial_experiments/ (leaderboard_oof, fold_metrics,
                   model_fits) — pilot 3,105 segments: Poisson Regression vs Random Forest vs HGB, same folds and baselines
  colour check     backend/rerun-spatial-eval-national-*/reports/v4/spatial_evaluation/colour_exposure_capture.csv —
                   share of road-time cells vs share of real accidents per map colour (out-of-fold 2565–2566)
Numbers are copied, not recomputed, except the relative improvement 1 − selected/baseline.
Run:  .venv/bin/python backend/scripts/build_model_page_data.py
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BACK = ROOT / "backend"
OUT = ROOT / "frontend" / "public" / "data" / "model-v1.json"
EXP = sorted(BACK.glob("rerun-spatial-model-national-2026*/reports/v4/spatial_experiments/leaderboard_oof.csv"))[-1].parent
EVAL = sorted(BACK.glob("rerun-2026-eval-national-*/reports/v4/evaluation_2026/method_comparison.csv"))[-1].parent
PILOT = sorted(BACK.glob("rerun-spatial-model-pilot-repro-*/reports/v3/spatial_experiments/leaderboard_oof.csv"))[-1].parent
COLOUR = sorted(BACK.glob("rerun-spatial-eval-national-*/reports/v4/spatial_evaluation/colour_exposure_capture.csv"))[-1].parent
CHAMP, BASE = "hgb_poisson_fixed::routed_context", "segment_mean_k365"
FAMILIES = [("poisson_a1e-05", "poisson"), ("rf_poisson_fixed", "random_forest"), ("hgb_poisson_fixed", "hist_gradient_boosting")]


def r(x, n=6):
    return None if pd.isna(x) else round(float(x), n)


lb = pd.read_csv(EXP / "leaderboard_oof.csv")
fm = pd.read_csv(EXP / "fold_metrics.csv")
folds = pd.read_csv(EXP / "folds.csv")
sel = pd.read_csv(EXP / "selection.csv")
mc = pd.read_csv(EVAL / "method_comparison.csv")
plb = pd.read_csv(PILOT / "leaderboard_oof.csv")
pfm = pd.read_csv(PILOT / "fold_metrics.csv")
pfits = pd.read_csv(PILOT / "model_fits.csv")
cap = pd.read_csv(COLOUR / "colour_exposure_capture.csv")

out = {"meta": {"experiment_run": EXP.parents[2].name, "evaluation_run": EVAL.parents[2].name,
                "pilot_run": PILOT.parents[2].name, "colour_run": COLOUR.parents[2].name,
                "champion": CHAMP, "baseline": BASE}, "units": {}}
for unit in ("daily", "6h"):
    s = sel[sel["unit"] == unit].iloc[0]
    board = [{"method": m.method, "kind": m.kind, "eligible": bool(m.deployment_eligible),
              "deviance": r(m.mean_poisson_deviance, 7), "mae": r(m.mae, 7)}
             for m in lb[lb["unit"] == unit].itertuples()]
    f_unit = folds[(folds["unit"] == unit) & (folds["fold_id"] != "benchmark_2024")]
    fold_rows = []
    for f in f_unit.itertuples():
        row = {"fold": f.fold_id, "eval_start": f.eval_start, "eval_end": f.eval_end,
               "train_cutoff": str(f.train_cutoff_local)[:10]}
        for meth in (CHAMP, BASE, "hgb_poisson_fixed::core"):
            x = fm[(fm["unit"] == unit) & (fm["fold_id"] == f.fold_id) & (fm["method"] == meth)]
            row[meth] = r(x["mean_poisson_deviance"].iloc[0], 7) if len(x) else None
        fold_rows.append(row)

    def groups(dim):
        x = mc[(mc["unit"] == unit) & (mc["dim"] == dim)]
        res = []
        for g in x.itertuples():
            a, b = g.deviance_floor_audit_selected, g.deviance_floor_audit_baseline
            res.append({"group": str(g.group), "records": int(g.n_raw_records), "selected": r(a, 5), "baseline": r(b, 5),
                        "improvement": r(1 - a / b, 4) if b and not pd.isna(b) else None})
        return res

    prov = groups("province")

    # ML families on the pilot (same rolling folds, same baselines): routed_context policy of each family vs segment_mean_k365
    pl = plb[plb["unit"] == unit].set_index("method")
    pf = pfm[(pfm["unit"] == unit) & pfm["fold_id"].isin(["2022H1", "2022H2", "2023H1", "2023H2"])].pivot(index="fold_id", columns="method", values="mean_poisson_deviance")
    pb = pl.loc[BASE, "mean_poisson_deviance"]
    ml = []
    for cid, fam in FAMILIES:
        m = cid + "::routed_context"
        secs = pfits[(pfits["unit"] == unit) & (pfits["config_id"] == cid)]["seconds"].sum()
        ml.append({"family": fam, "method": m, "deviance": r(pl.loc[m, "mean_poisson_deviance"], 7),
                   "improvement": r(1 - pl.loc[m, "mean_poisson_deviance"] / pb, 4), "fold_wins": int((pf[m] < pf[BASE]).sum()),
                   "fit_seconds": r(secs, 1)})
    pilot = {"segments": 3105, "baseline": BASE, "baseline_deviance": r(pb, 7), "families": ml}

    # map colours vs real accidents (out-of-fold 2565–2566, every segment x period cell)
    cc = cap[(cap["unit"] == unit) & (cap["scope"] == "oof_2022_2023") & (cap["colour"] != "grey")].set_index("colour")
    colours = [{"colour": c, "cell_share": r(cc.loc[c, "cell_share"], 4), "record_share": r(cc.loc[c, "record_share"], 4),
                "records": int(cc.loc[c, "records"]), "predicted": r(cc.loc[c, "predicted_records"], 1)} for c in ("red", "orange", "yellow", "base")]
    out["units"][unit] = {
        "selection": {"strongest_baseline": s.strongest_baseline, "selected": s.selected_method,
                      "relative_deviance_reduction": r(s.relative_deviance_reduction, 5), "mae_ratio": r(s.mae_ratio, 4),
                      "fold_wins": int(s.n_fold_wins), "n_folds": len(fold_rows), "reason": s.reason},
        "leaderboard": board, "folds": fold_rows, "ml_families": pilot, "colours": colours,
        "test2026": {
            "overall": groups("overall")[0], "month": groups("month"), "festival": groups("festival"),
            "time_block": groups("time_block_group"), "weekday": groups("weekday"), "season": groups("season"),
            "province_wins": sum(1 for p in prov if p["improvement"] is not None and p["improvement"] > 0),
            "province_count": len(prov),
            "weeks_better": sum(1 for p in groups("iso_week_start") if p["improvement"] is not None and p["improvement"] > 0),
            "weeks": len(groups("iso_week_start")),
        },
    }
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("wrote", OUT.relative_to(ROOT), OUT.stat().st_size, "bytes")
