"""Lệnh dòng lệnh: ``python -m mrhabits.cli run --homes cairo tulum1``."""

from __future__ import annotations

import argparse
from pathlib import Path

from .experiments import run_home, run_rolling
from .io import DATASETS


def main(argv=None):
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(prog="mrhabits")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="chạy thực nghiệm cho các nhà")
    r.add_argument("--homes", nargs="+", default=list(DATASETS), choices=DATASETS)
    r.add_argument("--models", nargs="+", default=["B2", "M1", "M2"])
    r.add_argument("--out", default="results")
    ro = sub.add_parser("rolling", help="RQ2 trên ba lần chia theo thời gian")
    ro.add_argument("--homes", nargs="+", default=list(DATASETS), choices=DATASETS)
    ro.add_argument("--models", nargs="+", default=["B2", "M1", "M2"])
    ro.add_argument("--out", default="results")
    f = sub.add_parser("figures", help="vẽ hình và bảng tổng hợp từ results/")
    f.add_argument("--out", default="results")
    a = ap.parse_args(argv)
    if a.cmd in ("run", "rolling"):
        out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
        fn = run_home if a.cmd == "run" else run_rolling
        with open(out / "run.log", "a", encoding="utf-8") as fh:
            for h in a.homes:
                fn(h, out, tuple(a.models), fh)
    elif a.cmd == "figures":
        from .report import build_all
        build_all(Path(a.out))


if __name__ == "__main__":
    main()
