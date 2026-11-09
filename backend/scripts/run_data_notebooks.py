"""Headless runner for RoadAware backend data notebooks (no browser; real kernel via nbclient).

Usage (from the repository root):
    .venv/bin/python backend/scripts/run_data_notebooks.py [--output-dir DIR] [--source-dir DIR]

* Must be launched with the project interpreter <repo>/.venv; any other Python is refused
  (no global fallback). Each notebook runs in its own fresh kernel started from that same
  interpreter via a run-local kernelspec, so namespaces never leak between notebooks.
* Without --output-dir, artifacts go to backend/data and backend/reports/data and executed
  notebooks are saved in place (backend/notebooks). With --output-dir DIR the rerun is
  self-contained: DIR/data, DIR/reports/data, DIR/notebooks.
* Stops at the first failure, saves the partially executed notebook (with the error output)
  and writes reports/data/run_manifest.json after every notebook.
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
ORDER = ["01_data_collection", "02_eda", "03_cleaning_preparation", "04_split_strategy", "05_data_leakage"]
KERNEL_NAME = "roadaware-venv"


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
                 f"Run: {py} backend/scripts/run_data_notebooks.py ...")
    return py


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


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
    ap.add_argument("--output-dir", help="self-contained rerun root (data/, reports/, notebooks/)")
    ap.add_argument("--source-dir", help="override config source_dir (raw CSV folder)")
    ap.add_argument("--timeout", type=int, default=3600, help="per-cell timeout in seconds")
    a = ap.parse_args(argv)

    py = ensure_venv()
    import nbformat  # imported after the venv check so a wrong interpreter fails clearly
    from nbclient import NotebookClient

    out = Path(a.output_dir).resolve() if a.output_dir else BACKEND
    nb_out = out / "notebooks" if a.output_dir else NB_DIR
    nb_out.mkdir(parents=True, exist_ok=True)
    rep = out / "reports" / "data"
    rep.mkdir(parents=True, exist_ok=True)
    os.environ["ROADAWARE_BACKEND_ROOT"] = str(BACKEND)
    os.environ["ROADAWARE_OUTPUT_DIR"] = str(out)
    os.environ["ROADAWARE_REQUIRE_VENV"] = "1"
    if a.source_dir:
        os.environ["ROADAWARE_SOURCE_DIR"] = str(Path(a.source_dir).resolve())
    spec = write_kernelspec(py, out)

    log = {"started_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "runner_python": sys.executable,
           "kernel_argv": spec["argv"], "backend_root": str(BACKEND), "output_dir": str(out),
           "source_dir_override": os.environ.get("ROADAWARE_SOURCE_DIR"), "status": "running", "notebooks": []}
    manifest_path = rep / "run_manifest.json"

    def save_log():
        manifest_path.write_text(json.dumps(log, indent=2, ensure_ascii=False), "utf-8")

    rc = 0
    for name in ORDER:
        src = NB_DIR / f"{name}.ipynb"
        entry = {"notebook": name, "source": str(src), "status": "missing", "error": None}
        log["notebooks"].append(entry)
        if not src.exists():
            entry["error"] = f"{src} not found"
            rc = 1
            save_log()
            print(f"[missing] {name}")
            break
        entry["source_sha256_before"] = sha256(src)
        nb = nbformat.read(src, as_version=4)
        original_kernelspec = nb.metadata.get("kernelspec")
        t0 = time.time()
        try:
            NotebookClient(nb, timeout=a.timeout, kernel_name=KERNEL_NAME,
                           resources={"metadata": {"path": str(NB_DIR)}}).execute()
            entry["status"] = "ok"
        except Exception as e:  # CellExecutionError, timeouts, dead kernel: keep evidence
            entry["status"] = "failed"
            entry["error"] = {"type": type(e).__name__, "ename": getattr(e, "ename", None),
                              "evalue": getattr(e, "evalue", None), "message": str(e)[-6000:],
                              "runner_traceback": traceback.format_exc()[-3000:]}
            failed = [i for i, c in enumerate(nb.cells) if c.cell_type == "code"
                      and any(o.get("output_type") == "error" for o in c.get("outputs", []))]
            entry["failed_cell_index"] = failed[0] if failed else None
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
        print(f"[{entry['status']}] {name} ({entry['seconds']}s) -> {dst}")
        if rc:
            break
    log["status"] = "ok" if rc == 0 else "failed"
    log["finished_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    save_log()
    print(f"run manifest: {manifest_path} (status={log['status']})")
    return rc


if __name__ == "__main__":
    sys.exit(main())
