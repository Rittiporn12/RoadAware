"""Headless runner for RoadAware backend MODEL notebooks (no browser; real kernel via nbclient).

Usage (from the repository root):
    .venv/bin/python backend/scripts/run_model_notebooks.py [--output-dir DIR] [--data-root DIR] [--timeout SEC]

* Must be launched with the project interpreter <repo>/.venv; any other Python is refused. Each notebook runs in its
  own fresh kernel started from that interpreter via a run-local kernelspec.
* --data-root (default backend/) is the READ-ONLY verified data foundation (data/ and reports/data/ from notebooks
  01-05). It is never regenerated or written by this runner.
* --output-dir (default backend/) receives model outputs only: data/model/, reports/models/ and, when given,
  notebooks/. Without --output-dir executed notebooks are saved in place (backend/notebooks).
* Writes reports/models/run_manifest.json after every cell/notebook; never touches reports/data/run_manifest.json.
* Stops at the first failure and saves the partially executed notebook with its error output.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import sys
import time
import traceback
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
NB_DIR = BACKEND / "notebooks"
ORDER = ["06_baseline_candidate_models"]
KERNEL_NAME = "roadaware-venv"
PANEL = Path("data") / "processed" / "province_day_panel.csv"
DATA_RUN_MANIFEST = Path("reports") / "data" / "run_manifest.json"


def venv_python():
    for rel in ("bin/python", "Scripts/python.exe"):
        p = REPO / ".venv" / rel
        if p.exists():
            return p  # deliberately not resolved: resolving the symlink would escape the venv
    return None


def ensure_venv():
    py = venv_python()
    if py is None:
        sys.exit(f"Project interpreter not found under {REPO / '.venv'}.\n"
                 "Create it: python3 -m venv .venv && .venv/bin/pip install -r backend/requirements-data.txt")
    if Path(sys.prefix).resolve() != (REPO / ".venv").resolve():
        sys.exit(f"Refusing to run with {sys.executable} (prefix {sys.prefix}).\n"
                 f"Run: {py} backend/scripts/run_model_notebooks.py ...")
    return py


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def maybe_sha(path):
    return sha256(path) if Path(path).is_file() else None


def write_kernelspec(py, out):
    """Run-local kernelspec pinned to the .venv interpreter; found via JUPYTER_PATH."""
    kdir = out / ".runner" / "jupyter" / "kernels" / KERNEL_NAME
    kdir.mkdir(parents=True, exist_ok=True)
    spec = {"argv": [str(py), "-m", "ipykernel_launcher", "-f", "{connection_file}"],
            "display_name": "RoadAware .venv", "language": "python"}
    (kdir / "kernel.json").write_text(json.dumps(spec, indent=2), "utf-8")
    os.environ["JUPYTER_PATH"] = os.pathsep.join(
        [str(out / ".runner" / "jupyter")] + [p for p in os.environ.get("JUPYTER_PATH", "").split(os.pathsep) if p])
    return spec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--output-dir", help="model output root (data/model, reports/models, notebooks/)")
    ap.add_argument("--data-root", help="verified data-foundation root holding data/ and reports/data/ (read-only)")
    ap.add_argument("--timeout", type=int, default=7200, help="per-cell timeout in seconds")
    a = ap.parse_args(argv)

    py = ensure_venv()
    import nbformat  # imported after the venv check so a wrong interpreter fails clearly
    from nbclient import NotebookClient

    out = Path(a.output_dir).resolve() if a.output_dir else BACKEND
    data_root = Path(a.data_root).resolve() if a.data_root else BACKEND
    if not (data_root / PANEL).is_file():
        sys.exit(f"{data_root / PANEL} not found; run backend/scripts/run_data_notebooks.py first or pass --data-root")
    nb_out = out / "notebooks" if a.output_dir else NB_DIR
    nb_out.mkdir(parents=True, exist_ok=True)
    rep = out / "reports" / "models"
    rep.mkdir(parents=True, exist_ok=True)
    manifest_path = rep / "run_manifest.json"
    assert manifest_path.resolve() != (out / DATA_RUN_MANIFEST).resolve()
    os.environ["ROADAWARE_BACKEND_ROOT"] = str(BACKEND)
    os.environ["ROADAWARE_DATA_ROOT"] = str(data_root)
    os.environ["ROADAWARE_OUTPUT_DIR"] = str(out)
    os.environ["ROADAWARE_REQUIRE_VENV"] = "1"
    spec = write_kernelspec(py, out)

    watched = {"panel": data_root / PANEL, "data_run_manifest": data_root / DATA_RUN_MANIFEST}
    log = {"started_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "runner_python": sys.executable,
           "kernel_argv": spec["argv"], "backend_root": str(BACKEND), "data_root": str(data_root), "output_dir": str(out),
           "data_inputs_sha256_before": {k: maybe_sha(p) for k, p in watched.items()},
           "status": "running", "notebooks": []}

    def save_log():
        manifest_path.write_text(json.dumps(log, indent=2, ensure_ascii=False, allow_nan=False), "utf-8")

    rc = 0
    for name in ORDER:
        src = NB_DIR / f"{name}.ipynb"
        entry = {"notebook": name, "source": str(src), "status": "missing", "error": None,
                 "cells_completed": 0, "current_cell_index": None}
        log["notebooks"].append(entry)
        if not src.exists():
            entry["error"] = f"{src} not found"
            rc = 1
            save_log()
            print(f"[missing] {name}", flush=True)
            break
        entry["source_sha256_before"] = sha256(src)
        nb = nbformat.read(src, as_version=4)
        original_kernelspec = nb.metadata.get("kernelspec")
        n_code = sum(1 for c in nb.cells if c.cell_type == "code")
        entry["status"] = "running"
        t0 = time.time()
        cell_t0 = {}

        def on_start(cell, cell_index, **kw):
            cell_t0[cell_index] = time.time()
            entry["current_cell_index"] = cell_index
            if cell.cell_type == "code":
                print(f"  [{name}] cell {cell_index} start ({entry['cells_completed'] + 1}/{n_code} code cells)", flush=True)

        def on_executed(cell, cell_index, **kw):
            if cell.cell_type != "code":
                return
            entry["cells_completed"] += 1
            secs = round(time.time() - cell_t0.get(cell_index, time.time()), 1)
            print(f"  [{name}] cell {cell_index} done in {secs}s", flush=True)
            for o in cell.get("outputs", []):  # echo the cell's stdout tail for progress visibility
                if o.get("output_type") == "stream":
                    for line in o.get("text", "").rstrip().splitlines()[-15:]:
                        print(f"      {line}", flush=True)
            save_log()

        try:
            NotebookClient(nb, timeout=a.timeout, kernel_name=KERNEL_NAME,
                           resources={"metadata": {"path": str(NB_DIR)}},
                           on_cell_start=on_start, on_cell_executed=on_executed).execute()
            entry["status"] = "ok"
        except Exception as e:  # CellExecutionError, timeouts, dead kernel: keep evidence
            entry["status"] = "failed"
            entry["error"] = {"type": type(e).__name__, "ename": getattr(e, "ename", None),
                              "evalue": getattr(e, "evalue", None), "message": str(e)[-6000:],
                              "runner_traceback": traceback.format_exc()[-3000:]}
            failed = [i for i, c in enumerate(nb.cells) if c.cell_type == "code"
                      and any(o.get("output_type") == "error" for o in c.get("outputs", []))]
            entry["failed_cell_index"] = failed[0] if failed else entry["current_cell_index"]
            rc = 1
        if original_kernelspec is not None:
            nb.metadata["kernelspec"] = original_kernelspec  # keep VS Code-selectable metadata
        dst = nb_out / f"{name}.ipynb"
        try:
            nbformat.validate(nb)
            entry["nbformat_valid"] = True
        except Exception as e:
            entry["nbformat_valid"] = False
            entry["nbformat_error"] = str(e)[-2000:]
            rc = 1
        nbformat.write(nb, dst)
        entry.update(seconds=round(time.time() - t0, 2), output=str(dst), output_sha256=sha256(dst))
        save_log()
        print(f"[{entry['status']}] {name} ({entry['seconds']}s) -> {dst}", flush=True)
        if rc:
            break

    log["data_inputs_sha256_after"] = {k: maybe_sha(p) for k, p in watched.items()}
    log["data_inputs_unchanged"] = log["data_inputs_sha256_after"] == log["data_inputs_sha256_before"]
    if not log["data_inputs_unchanged"]:
        rc = 1
        print("ERROR: verified data inputs changed during the model run", flush=True)
    log["status"] = "ok" if rc == 0 else "failed"
    log["finished_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    save_log()
    print(f"model run manifest: {manifest_path} (status={log['status']})", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
