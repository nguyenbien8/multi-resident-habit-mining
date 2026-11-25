"""Sinh bảng (LaTeX, CSV) và hình (PDF + PNG) cho khóa luận từ ``results/``.

Hình theo bảng màu tham chiếu đã kiểm định (thứ tự cố định, không xoay vòng),
nền trắng cho bản in, nét mảnh, lưới mờ, chú giải luôn có khi ≥ 2 chuỗi.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
INK, INK2, GRID, MUTED = "#0b0b0b", "#52514e", "#e4e3df", "#a3a29c"
HOMES = ["cairo", "tulum1", "tulum2", "milan", "aruba"]
HOME_LABEL = {"cairo": "Cairo", "tulum1": "Tulum1", "tulum2": "Tulum2", "milan": "Milan", "aruba": "Aruba"}
SOURCES = ["B0", "B1", "B2+H", "M1+H", "M2+H", "Oracle+H"]
SOURCE_COLOR = {s: SERIES[i] for i, s in enumerate(SOURCES)}
SOURCE_COLOR["Oracle+H"] = MUTED   # giới hạn trên, không phải phương pháp: tô xám
MODELS = ["B2", "M1", "M2"]


def _style():
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": MUTED,
        "axes.labelcolor": INK, "axes.titlesize": 10, "axes.titleweight": "bold",
        "xtick.color": INK2, "ytick.color": INK2, "axes.grid": True, "grid.color": GRID,
        "grid.linewidth": 0.6, "axes.axisbelow": True, "axes.spines.top": False,
        "axes.spines.right": False, "legend.frameon": False, "figure.dpi": 150,
        "savefig.bbox": "tight", "pdf.fonttype": 42,
    })


def _save(fig, figdir: Path, name: str):
    figdir.mkdir(parents=True, exist_ok=True)
    fig.savefig(figdir / f"{name}.pdf")
    fig.savefig(figdir / f"{name}.png", dpi=200)
    plt.close(fig)


def _homes(res: Path):
    return [h for h in HOMES if (res / h / "rq2.csv").exists()]


# --------------------------------------------------------------------------
# Bảng
# --------------------------------------------------------------------------
def _tex_table(df: pd.DataFrame, path: Path, caption: str, label: str, colfmt: str | None = None,
               bold_max_cols: list | None = None, head: list | None = None, midrules: tuple = ()):
    """Ghi bảng LaTeX. ``head``: ô tiêu đề viết sẵn bằng LaTeX (ví dụ dùng \\makecell);
    ``midrules``: chỉ số dòng mà trước nó kẻ một đường phân nhóm."""
    df = df.copy()
    cols = list(df.columns)
    body = []
    for i in range(len(df)):
        cells = []
        for c in cols:
            v = df[c].iloc[i]          # theo cột để giữ kiểu (iterrows đổi int thành float)
            if isinstance(v, np.floating):
                v = float(v)
            if isinstance(v, float):
                # Dấu thập phân kiểu Việt Nam (0,62) cho thống nhất với văn bản.
                s = "--" if np.isnan(v) else _r2(v).replace(".", "{,}")
                if bold_max_cols and c in bold_max_cols and not np.isnan(v) and v == df[c].max():
                    s = f"\\textbf{{{s}}}"
            else:
                s = str(v).replace("_", "\\_").replace("%", "\\%")
            cells.append(s)
        body.append(("\\midrule\n" if i in midrules else "") + " & ".join(cells) + " \\\\")
    if head is None:
        head = [str(c).replace("_", "\\_").replace("±", "$\\pm$") for c in cols]
    head = " & ".join(head) + " \\\\"
    colfmt = colfmt or ("l" + "r" * (len(cols) - 1))
    tabular = (f"\\begin{{tabular}}{{{colfmt}}}\n\\toprule\n{head}\n\\midrule\n"
               + "\n".join(body) + "\n\\bottomrule\n\\end{tabular}")
    tight = "\\setlength{\\tabcolsep}{4pt}\n" if len(cols) > 7 else ""
    tex = (f"\\begin{{table}}[htbp]\n\\centering\n\\caption{{{caption}}}\n\\label{{{label}}}\n"
           f"\\small\n{tight}{tabular}\n\\end{{table}}\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(tex, encoding="utf-8")


def tables(res: Path, tabdir: Path) -> dict:
    homes = _homes(res)
    out = {}
    # Dữ liệu
    rows = []
    for h in homes:
        i = json.loads((res / h / "info.json").read_text(encoding="utf-8"))
        rows.append({"Nhà": HOME_LABEL[h], "Số người": i["residents"], "Ngày dùng": i["days_kept"],
                     "Ngày bỏ": i["days_dropped"], "Huấn luyện/kiểm tra": f"{i['train_days']}/{i['test_days']}",
                     "Cảm biến": i["sensors"], "Sự kiện chuyển động": f"{i['motion_on_events']:,}".replace(",", "."),
                     "Hoạt động": i["activities"], "HĐ gắn người": len(i["per_resident_activities"]),
                     "Vùng": i["n_zones"]})
    d = pd.DataFrame(rows); out["data"] = d
    d.to_csv(res / "summary_data.csv", index=False)
    mc = lambda a, b: f"\\makecell{{{a}\\\\{b}}}"
    _tex_table(d, tabdir / "data.tex",
               "Năm bộ dữ liệu CASAS sau tiền xử lý (HĐ: hoạt động được gán nhãn; "
               "HĐ gắn người: hoạt động có tiền tố R1\\_/R2\\_)", "tab:data", "lrrrcrrrrr",
               head=["Nhà", mc("Số", "người"), mc("Ngày", "dùng"), mc("Ngày", "bỏ"), mc("Huấn luyện/", "kiểm tra"),
                     mc("Cảm", "biến"), mc("Sự kiện", "chuyển động"), mc("Số", "HĐ"), mc("HĐ gắn", "người"),
                     mc("Số", "vùng")])

    # RQ1
    rows = []
    for h in homes:
        r = pd.read_csv(res / h / "rq1.csv").set_index("model")
        row = {"Nhà": HOME_LABEL[h]}
        for m in MODELS:
            if m in r.index:
                row[f"{m} macro-F1"] = r.loc[m, "macro_f1"]
        for m in MODELS:
            if m in r.index:
                row[f"{m} micro-F1"] = r.loc[m, "micro_f1"]
        rows.append(row)
    d = pd.DataFrame(rows); out["rq1"] = d
    d.to_csv(res / "summary_rq1.csv", index=False)
    _tex_table(d, tabdir / "rq1.tex", "RQ1 -- F1 nhận dạng (người, hoạt động) theo sự kiện trên tập kiểm tra",
               "tab:rq1")

    # RQ1 theo từng hoạt động (Cairo)
    if (res / "cairo" / "rq1.csv").exists():
        r = pd.read_csv(res / "cairo" / "rq1.csv").set_index("model")
        fcols = [c for c in r.columns if c.startswith("f1_")]
        d = r[fcols].T
        d.index = [c[3:] for c in fcols]
        d = d.reset_index().rename(columns={"index": "Hoạt động"})
        out["rq1_cairo"] = d
        _tex_table(d, tabdir / "rq1_cairo.tex", "RQ1 -- F1 theo từng hoạt động trên Cairo", "tab:rq1-cairo")

    # RQ2
    rows = []
    for h in homes:
        r = pd.read_csv(res / h / "rq2.csv").set_index("source")
        for s in SOURCES:
            if s in r.index:
                x = r.loc[s]
                rows.append({"Nhà": HOME_LABEL[h], "Phương pháp": s, "P": x["precision"], "R": x["recall"],
                             "F1": x["f1"], "Lệch giờ (phút)": x["time_err_min"],
                             "Khớp/đáp án": f"{int(x['n_match'])}/{int(x['n_ref'])}",
                             "Từng người": f"{int(x['res_n_match'])}/{int(x['res_n_ref'])}"})
    d = pd.DataFrame(rows); out["rq2"] = d
    d.to_csv(res / "summary_rq2.csv", index=False)
    for h in homes:
        _tex_table(d[d["Nhà"] == HOME_LABEL[h]].drop(columns=["Nhà"]), tabdir / f"rq2_{h}.tex",
                   f"RQ2 -- So khớp thói quen với đáp án trên {HOME_LABEL[h]}", f"tab:rq2-{h}", "lrrrrcc")
    piv = d.pivot(index="Phương pháp", columns="Nhà", values="F1").reindex(SOURCES)
    piv = piv[[HOME_LABEL[h] for h in homes]].reset_index()
    piv["Trung bình"] = piv[[HOME_LABEL[h] for h in homes]].mean(1)
    out["rq2_f1"] = piv
    _tex_table(piv, tabdir / "rq2_f1.tex", "RQ2 -- F1 thói quen theo nhà và phương pháp", "tab:rq2-f1")

    # Ablation
    rows = []
    for h in homes:
        if not (res / h / "ablation.csv").exists():
            continue
        a = pd.read_csv(res / h / "ablation.csv")
        for _, x in a.iterrows():
            rows.append({"Nhà": HOME_LABEL[h], "Đầu vào": x["source"], "Biến thể": x["ablation"], "F1": x["f1"],
                         "P": x["precision"], "R": x["recall"]})
    d = pd.DataFrame(rows); out["ablation"] = d
    d.to_csv(res / "summary_ablation.csv", index=False)
    if len(d):
        piv = d.pivot_table(index=["Đầu vào", "Biến thể"], columns="Nhà", values="F1")
        hcols = [HOME_LABEL[h] for h in homes if HOME_LABEL[h] in piv.columns]
        order = [("Oracle", "method=scan", "Nhãn thật", "Quét cửa sổ (mặc định)"),
                 ("Oracle", "method=dbscan", "Nhãn thật", "DBSCAN"),
                 ("Oracle", "method=hdbscan", "Nhãn thật", "HDBSCAN"),
                 ("Oracle", "no_daytype_split", "Nhãn thật", "Không tách loại ngày"),
                 ("M1", "method=scan", "M1", "Mặc định (quét cửa sổ, nối 10 phút)"),
                 ("M1", "method=dbscan", "M1", "DBSCAN"),
                 ("M1", "method=hdbscan", "M1", "HDBSCAN"),
                 ("M1", "no_daytype_split", "M1", "Không tách loại ngày"),
                 ("M1", "merge_gap=2", "M1", "Khoảng nối 2 phút"),
                 ("M1", "merge_gap=5", "M1", "Khoảng nối 5 phút"),
                 ("M1", "merge_gap=20", "M1", "Khoảng nối 20 phút"),
                 ("M1", "merge_gap=30", "M1", "Khoảng nối 30 phút")]
        rows = [{"Đầu vào": a, "Biến thể": b, **piv.loc[(src, key), hcols].to_dict()}
                for src, key, a, b in order if (src, key) in piv.index]
        tab = pd.DataFrame(rows)
        out["ablation_f1"] = tab
        _tex_table(tab, tabdir / "ablation.tex",
                   "Ablation -- F1 thói quen khi thay một thành phần (dòng ``Nhãn thật'': khai phá trên nhãn "
                   "thật của ngày kiểm tra)", "tab:ablation", "ll" + "r" * len(hcols), midrules=(4, 8))

    # Độ nhạy: thứ hạng phương pháp có giữ nguyên khi đổi định nghĩa?
    rows = []
    for h in homes:
        if not (res / h / "sensitivity.csv").exists():
            continue
        s = pd.read_csv(res / h / "sensitivity.csv")
        for (hw, fq), g in s.groupby(["half_window_min", "freq_thr"]):
            g = g.set_index("source")["f1"]
            rows.append({"Nhà": HOME_LABEL[h], "Cửa sổ ±(phút)": int(hw), "Ngưỡng": fq,
                         **{k: g.get(k, np.nan) for k in ["B0", "B1", "B2+H", "M1+H", "M2+H"]}})
    d = pd.DataFrame(rows); out["sensitivity"] = d
    d.to_csv(res / "summary_sensitivity.csv", index=False)
    if len(d):
        dd = d.groupby(["Cửa sổ ±(phút)", "Ngưỡng"])[["B0", "B1", "B2+H", "M1+H", "M2+H"]].mean().reset_index()
        dd[dd.columns[0]] = dd[dd.columns[0]].astype(int)
        out["sensitivity_mean"] = dd
        _tex_table(dd, tabdir / "sensitivity.tex",
                   "Độ nhạy -- F1 thói quen trung bình năm nhà khi đổi tham số định nghĩa", "tab:sensitivity",
                   "rrrrrrr")

    # RQ3
    rows = []
    for h in homes:
        f = res / h / "rq3.csv"
        if not f.exists():
            continue
        q = pd.read_csv(f)
        for (t, det), g in q.groupby(["target", "detector"]):
            rows.append({"Nhà": HOME_LABEL[h], "Hoạt động đích": t, "Bộ phát hiện": DET_LABEL.get(det, det),
                         "P": g["precision"].mean(), "R": g["recall"].mean(), "F1": g["f1"].mean(),
                         "F1 std": g["f1"].std(), "Báo nhầm/ngày": g["false_alarms_per_day"].mean(),
                         "Trễ (phút)": g["alarm_delay_min"].mean()})
    d = pd.DataFrame(rows); out["rq3"] = d
    d.to_csv(res / "summary_rq3.csv", index=False)
    if len(d):
        t = d.copy()
        t["F1"] = [_pm(m, s) for m, s in zip(t["F1"], t["F1 std"])]
        cases = t[["Nhà", "Hoạt động đích"]].drop_duplicates()
        keep = ["Bộ phát hiện", "P", "R", "F1", "Báo nhầm/ngày"]
        if len(cases) > 1:
            keep = ["Nhà", "Hoạt động đích"] + keep
        _tex_table(t[keep], tabdir / "rq3.tex",
                   "RQ3 -- Phát hiện ngày bỏ thuốc \\texttt{R2\\_Take\\_Medicine} trên Cairo "
                   "(trung bình 5 lần cài; F1 ghi trung bình $\\pm$ độ lệch chuẩn)", "tab:rq3",
                   "l" * (len(keep) - 4) + "rrcr")

    # Nhiều lần chia theo thời gian
    rows = []
    for h in homes:
        f = res / h / "rolling.csv"
        if f.exists():
            rows.append(pd.read_csv(f).assign(home=HOME_LABEL[h]))
    if rows:
        r = pd.concat(rows, ignore_index=True)
        r.to_csv(res / "summary_rolling.csv", index=False)
        hl = list(dict.fromkeys(r["home"]))
        srcs = [s for s in SOURCES if s in set(r["source"])]
        tab = []
        for s in srcs:
            g = r[r["source"] == s]
            row = {"Phương pháp": s}
            for hh in hl:
                x = g[g["home"] == hh]["f1"]
                row[f"{hh} ({r[r['home'] == hh]['fold'].nunique()} lần)"] = _pm(x.mean(), x.std())
            row["Trung bình"] = _r2(g.groupby("home")["f1"].mean().mean()).replace(".", "{,}")
            tab.append(row)
        tab = pd.DataFrame(tab); out["rolling"] = tab
        _tex_table(tab, tabdir / "rolling.tex",
                   "F1 thói quen của ba nhà hai người qua nhiều lần chia theo thời gian (trung bình $\\pm$ "
                   "độ lệch chuẩn; mỗi lần kiểm tra trên 20\\% số ngày kế tiếp mốc huấn luyện; trong ngoặc: "
                   "số lần chia)", "tab:rolling",
                   "l" + "c" * (len(tab.columns) - 1))
        # So sánh cặp M1+H với B0 và B2+H trên mọi (nhà, lần chia).
        from scipy.stats import wilcoxon
        piv = r.pivot_table(index=["home", "fold"], columns="source", values="f1")
        stats = {}
        for other in ("B0", "B1", "B2+H", "M2+H"):
            if other in piv and "M1+H" in piv:
                dd = (piv["M1+H"] - piv[other]).dropna()
                p = wilcoxon(dd).pvalue if (dd != 0).any() else 1.0
                stats[other] = {"n": int(len(dd)), "wins": int((dd > 0).sum()), "ties": int((dd == 0).sum()),
                                "mean_diff": float(dd.mean()), "p_wilcoxon": float(p)}
        (res / "rolling_stats.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
        out["rolling_stats"] = stats
    return out


DET_LABEL = {"B0-zone": "B0-vùng"}


def _r2(v: float) -> str:
    """Làm tròn 2 chữ số kiểu thông thường (0,625 → 0,63), không theo kiểu 'chẵn gần nhất'."""
    from decimal import ROUND_HALF_UP, Decimal
    # Làm tròn 6 chữ số trước để khử sai số dấu phẩy động (0,6249999999 thực chất là 0,625).
    return str(Decimal(f"{float(v):.6f}").quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _pm(m: float, s: float) -> str:
    """Chuỗi ``0{,}39 $\\pm$ 0{,}10`` cho bảng LaTeX."""
    f = lambda v: "--" if v != v else _r2(v).replace(".", "{,}")
    return f"{f(m)} $\\pm$ {f(s)}"


# --------------------------------------------------------------------------
# Hình
# --------------------------------------------------------------------------
def _grouped_bars(ax, groups, series, values, colors, ymax=1.0):
    n = len(series); w = 0.8 / n
    x = np.arange(len(groups))
    for i, s in enumerate(series):
        v = [values.get((g, s), np.nan) for g in groups]
        ax.bar(x + (i - (n - 1) / 2) * w, v, w * 0.92, color=colors[s], label=s, linewidth=0)
    ax.set_xticks(x, groups)
    ax.set_ylim(0, ymax)


def fig_rq1(res: Path, figdir: Path):
    homes = _homes(res)
    vals = {}
    for h in homes:
        r = pd.read_csv(res / h / "rq1.csv").set_index("model")
        for m in MODELS:
            if m in r.index:
                vals[(HOME_LABEL[h], m)] = r.loc[m, "macro_f1"]
    fig, ax = plt.subplots(figsize=(6.2, 2.6))
    _grouped_bars(ax, [HOME_LABEL[h] for h in homes], MODELS, vals,
                  {"B2": SERIES[2], "M1": SERIES[3], "M2": SERIES[4]}, 0.8)
    ax.set_ylabel("macro-F1 (theo sự kiện)")
    ax.legend(ncol=3, loc="upper right")
    _save(fig, figdir, "rq1_macro_f1")


def fig_rq2(res: Path, figdir: Path):
    homes = _homes(res)
    vals = {}
    for h in homes:
        r = pd.read_csv(res / h / "rq2.csv").set_index("source")
        for s in SOURCES:
            if s in r.index:
                vals[(HOME_LABEL[h], s)] = r.loc[s, "f1"]
    fig, ax = plt.subplots(figsize=(6.4, 2.8))
    _grouped_bars(ax, [HOME_LABEL[h] for h in homes], SOURCES, vals, SOURCE_COLOR, 1.08)
    ax.set_ylabel("F1 thói quen")
    ax.legend(ncol=6, loc="upper center", bbox_to_anchor=(0.5, 1.18), fontsize=8)
    _save(fig, figdir, "rq2_habit_f1")


def fig_propagation(res: Path, figdir: Path):
    homes = [h for h in HOMES if (res / h / "propagation.csv").exists()]
    if not homes:
        return
    kinds = [("drop", "Bỏ sót (tỉ lệ)"), ("jitter", "Lệch giờ σ (phút)"),
             ("spurious", "Chèn giả (× số thật)"), ("swap", "Tráo người R1↔R2 (tỉ lệ)")]
    fig, axes = plt.subplots(1, 4, figsize=(7.2, 2.3), sharey=True)
    for ax, (k, lab) in zip(axes, kinds):
        for i, h in enumerate(homes):
            p = pd.read_csv(res / h / "propagation.csv")
            g = p[p["kind"] == k].groupby("level")["f1"].agg(["mean", "std"]).reset_index()
            # Tráo người chỉ có nghĩa khi nhà có đủ thói quen gắn người (≥ 3).
            if g.empty or (k == "swap" and p[p["kind"] == k]["n_ref"].max() < 3):
                continue
            c = SERIES[i]
            ax.plot(g["level"], g["mean"], color=c, lw=2, marker="o", ms=3.5, label=HOME_LABEL[h])
            ax.fill_between(g["level"], g["mean"] - g["std"], g["mean"] + g["std"], color=c, alpha=0.12, lw=0)
        ax.set_xlabel(lab, fontsize=8)
        ax.set_ylim(0, 1.05)
    axes[0].set_ylabel("F1 thói quen")
    axes[0].legend(loc="lower left", fontsize=7)
    _save(fig, figdir, "propagation")


def fig_b0_failure(res: Path, figdir: Path):
    """Phiên trong vùng bếp Cairo theo giờ: B0 gộp mọi bữa ăn và uống thuốc."""
    from .baselines import label_sessions, sessions
    from .habits import hour_of
    from .io import load_home, motion_on, split_days
    from .topology import build_topology
    h = load_home("cairo"); tr, te = split_days(h.days)
    mo = motion_on(h.events)
    topo = build_topology(mo[mo["day"].isin(tr)].reset_index(drop=True))
    ev = mo[mo["day"].isin(te)].reset_index(drop=True)
    kz = topo.zone["M021"]
    S = sessions(ev, topo)
    S = S[S["zone"] == kz].copy()
    S["label"] = label_sessions(S, h.episodes[h.episodes["day"].isin(te)])
    S["h"] = hour_of(S["start"])
    cats = [("Breakfast", "Ăn sáng"), ("Lunch", "Ăn trưa"), ("Dinner", "Ăn tối"),
            ("R2_Take_Medicine", "R2 uống thuốc")]
    fig, ax = plt.subplots(figsize=(6.4, 2.3))
    rng = np.random.default_rng(0)
    other = S[~S["label"].isin([c for c, _ in cats])]
    ax.scatter(other["h"], rng.uniform(-0.35, 0.35, len(other)), s=6, color=MUTED, alpha=0.5,
               label="Không nhãn / khác", linewidths=0)
    for i, (c, lab) in enumerate(cats):
        g = S[S["label"] == c]
        ax.scatter(g["h"], rng.uniform(-0.35, 0.35, len(g)), s=14, color=SERIES[i], label=lab, linewidths=0)
    # Cụm B0 của vùng bếp (DBSCAN như đề tài thực tập): vẽ phạm vi 10–90% giờ bắt đầu.
    import math
    from sklearn.cluster import DBSCAN
    from .habits import R as RAD, circ_window
    th = 2 * np.pi * S["h"].to_numpy() / 24
    X = np.c_[RAD * np.cos(th), RAD * np.sin(th), 0.5 * np.log1p(S["dur"].to_numpy())]
    lab = DBSCAN(eps=0.5, min_samples=max(5, math.ceil(0.2 * len(te)))).fit_predict(X)
    for c in sorted(set(lab) - {-1}):
        m = lab == c
        if S.loc[m, "day"].nunique() < 0.5 * len(te):
            continue
        lo, hi = circ_window(S.loc[m, "h"].to_numpy(), 0.8)
        ax.plot([lo, hi], [0.48, 0.48], color=INK, lw=2.5, solid_capstyle="round")
        ax.text((lo + hi) / 2, 0.53, f"B0: một cụm duy nhất ({int(m.sum())} phiên)", ha="center",
                va="bottom", fontsize=8, color=INK)
    ax.set_ylim(-0.45, 0.68)
    ax.set_yticks([]); ax.set_xlim(0, 24); ax.set_xticks(range(0, 25, 3))
    ax.set_xlabel("Giờ bắt đầu phiên trong vùng bếp (22 ngày kiểm tra)")
    ax.legend(ncol=5, loc="upper center", bbox_to_anchor=(0.5, 1.32), fontsize=7.5)
    _save(fig, figdir, "b0_kitchen_sessions")


def fig_habit_timeline(res: Path, figdir: Path, home: str = "cairo"):
    f = res / home / "habits.csv"
    if not f.exists():
        return
    hb = pd.read_csv(f)

    def tohour(s):
        hh, mm = s.split(":"); return int(hh) + int(mm) / 60
    ref = hb[hb["table"] == "reference"]
    acts = sorted(ref["activity"].unique(), key=lambda a: (a[:2] not in ("R1", "R2"), a))
    show = [("reference", "Đáp án", INK), ("M1", "M1+H", SERIES[3]), ("M2", "M2+H", SERIES[4]),
            ("B0", "B0", SERIES[0])]
    fig, ax = plt.subplots(figsize=(6.4, 0.38 * len(acts) + 0.9))
    for j, (tab, lab, c) in enumerate(show):
        sub = hb[(hb["table"] == tab) & hb["activity"].isin(acts)]
        first = True
        for _, r in sub.iterrows():
            y = acts.index(r["activity"]) + (j - 1.5) * 0.18
            lo, hi = (tohour(x) for x in r["window80"].split("–"))
            segs = [(lo, hi)] if hi >= lo else [(lo, 24), (0, hi)]
            for a, b in segs:
                ax.plot([a, b], [y, y], color=c, lw=3 if tab == "reference" else 2, solid_capstyle="round",
                        alpha=0.35 if tab == "reference" else 0.9)
            ax.plot(tohour(r["typical"]), y, "o", color=c, ms=4, label=lab if first else None)
            first = False
    ax.set_yticks(range(len(acts)), acts, fontsize=7.5)
    ax.set_xlim(0, 24); ax.set_xticks(range(0, 25, 3)); ax.invert_yaxis()
    ax.set_xlabel("Giờ trong ngày (chấm: giờ điển hình; vạch: khung 80%)")
    ax.legend(ncol=4, loc="lower center", bbox_to_anchor=(0.5, 1.0), fontsize=7.5)
    _save(fig, figdir, f"habits_timeline_{home}")


def fig_rq3(res: Path, figdir: Path):
    rows = []
    for h in HOMES:
        f = res / h / "rq3.csv"
        if f.exists():
            q = pd.read_csv(f); q["home"] = HOME_LABEL[h]; rows.append(q)
    if not rows:
        return
    q = pd.concat(rows)
    tname = {"R2_Take_Medicine": "R2 uống thuốc", "Morning_Meds": "thuốc sáng", "Eve_Meds": "thuốc tối"}
    q["case"] = q["home"] + " – " + q["target"].map(lambda t: tname.get(t, t))
    q["detector"] = q["detector"].map(lambda d: DET_LABEL.get(d, d))
    cases = list(dict.fromkeys(q["case"]))
    dets = [d for d in ["B0-vùng", "B2", "M1", "M2"] if d in set(q["detector"])]
    col = {"B0-vùng": SERIES[0], "B2": SERIES[2], "M1": SERIES[3], "M2": SERIES[4]}
    fig, ax = plt.subplots(figsize=(6.0, 2.5))
    n = len(dets); w = 0.8 / n; x = np.arange(len(cases))
    for i, d in enumerate(dets):
        g = q[q["detector"] == d].groupby("case")["f1"].agg(["mean", "std"]).reindex(cases)
        xs = x + (i - (n - 1) / 2) * w
        ax.bar(xs, g["mean"], w * 0.92, color=col[d], label=d, linewidth=0,
               yerr=g["std"], error_kw={"elinewidth": 0.8, "ecolor": INK2, "capsize": 2})
        # Ghi giá trị trên mỗi cột: cột bằng 0 nếu không ghi sẽ trông như thiếu dữ liệu.
        for xi, m, sd in zip(xs, g["mean"], g["std"].fillna(0)):
            ax.text(xi, m + sd + 0.03, _r2(m).replace(".", ","), ha="center", va="bottom",
                    fontsize=8, color=INK)
    ax.set_xticks(x, cases, fontsize=8); ax.set_ylim(0, 1.05); ax.set_ylabel("F1 phát hiện ngày bỏ thuốc")
    ax.legend(ncol=4, loc="upper right", fontsize=8)
    _save(fig, figdir, "rq3_detection")


ACT_VI = {"Breakfast": "Ăn sáng", "Lunch": "Ăn trưa", "Dinner": "Ăn tối", "R1_Wake": "R1 thức dậy",
          "R2_Wake": "R2 thức dậy", "R1_Sleep": "R1 ngủ", "R2_Sleep": "R2 ngủ", "R1_Work": "R1 làm việc",
          "R2_Take_Medicine": "R2 uống thuốc", "Night_Wandering": "Đi lại ban đêm",
          "Bed_to_Toilet": "Đi vệ sinh đêm", "Leave_Home": "Rời nhà", "Laundry": "Giặt đồ"}


def fig_activity_hours(res: Path, figdir: Path, home: str = "cairo"):
    """Giờ bắt đầu của mọi lần thực hiện theo hoạt động (nhãn thật, toàn bộ dữ liệu)."""
    from .habits import hour_of
    from .io import load_home
    h = load_home(home)
    ep = h.episodes.copy()
    ep["h"] = hour_of(ep["start"])
    acts = [a for a, c in ep["activity"].value_counts().items() if c >= 5]
    acts = sorted(acts, key=lambda a: ep.loc[ep["activity"] == a, "h"].median())
    col = {"R1": SERIES[0], "R2": SERIES[1], "H": MUTED}
    fig, ax = plt.subplots(figsize=(6.4, 0.32 * len(acts) + 1.0))
    rng = np.random.default_rng(0)
    seen = set()
    for i, a in enumerate(acts):
        g = ep[ep["activity"] == a]
        r = g["resident"].iloc[0]
        lab = {"R1": "Gắn với R1", "R2": "Gắn với R2", "H": "Chung của hộ"}[r]
        ax.scatter(g["h"], i + rng.uniform(-0.22, 0.22, len(g)), s=7, color=col[r], alpha=0.7,
                   linewidths=0, label=None if lab in seen else lab)
        seen.add(lab)
    ax.set_yticks(range(len(acts)), [ACT_VI.get(a, a) for a in acts], fontsize=7.5)
    ax.set_xlim(0, 24); ax.set_xticks(range(0, 25, 3)); ax.invert_yaxis()
    ax.set_xlabel(f"Giờ bắt đầu (mỗi chấm là một lần thực hiện, toàn bộ {len(h.days)} ngày)")
    ax.legend(ncol=3, loc="lower center", bbox_to_anchor=(0.5, 1.0), fontsize=7.5, markerscale=2)
    _save(fig, figdir, f"activity_hours_{home}")


def fig_topology(res: Path, figdir: Path, home: str = "cairo"):
    """Đồ thị kề cảm biến rút ra từ dữ liệu huấn luyện, tô màu theo vùng."""
    import networkx as nx
    from .experiments import CONFIG
    from .io import load_home, motion_on, split_days
    from .topology import build_topology
    h = load_home(home); tr, _ = split_days(h.days, CONFIG["train_ratio"])
    mo = motion_on(h.events)
    topo = build_topology(mo[mo["day"].isin(tr)].reset_index(drop=True))
    G = nx.Graph()
    G.add_nodes_from(topo.sensors)
    A = topo.adjacency
    for i, a in enumerate(topo.sensors):
        for j in range(i + 1, len(topo.sensors)):
            if A[i, j]:
                G.add_edge(a, topo.sensors[j])
    pos = nx.kamada_kawai_layout(G)
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    nx.draw_networkx_edges(G, pos, ax=ax, edge_color=MUTED, width=0.8)
    for z in range(topo.n_zones):
        nodes = [s for s in topo.sensors if topo.zone[s] == z]
        nx.draw_networkx_nodes(G, pos, nodelist=nodes, ax=ax, node_size=230, node_color=SERIES[z % len(SERIES)],
                               label=f"Vùng {z + 1}")
    nx.draw_networkx_labels(G, pos, {s: s[1:].lstrip("0") for s in topo.sensors}, ax=ax, font_size=6,
                            font_color="white", font_weight="bold")
    ax.set_axis_off()
    ax.legend(ncol=min(topo.n_zones, 6), loc="lower center", bbox_to_anchor=(0.5, -0.08), fontsize=7.5,
              markerscale=0.6)
    _save(fig, figdir, f"topology_{home}")


def fig_rf_importance(res: Path, figdir: Path, home: str = "cairo"):
    """Mức quan trọng (giảm Gini) của từng nhóm đặc trưng trong M1, huấn luyện như thực nghiệm chính."""
    from .experiments import CONFIG
    from .io import active_labels, load_home, motion_on, split_days
    from .recognition import ForestRecognizer
    from .topology import build_topology
    info = json.loads((res / home / "info.json").read_text(encoding="utf-8"))
    h = load_home(home); tr, _ = split_days(h.days, CONFIG["train_ratio"])
    mo = motion_on(h.events)
    ev = mo[mo["day"].isin(tr)].reset_index(drop=True)
    topo = build_topology(ev)
    rec = ForestRecognizer(topo, **CONFIG["rf"]).fit(ev, active_labels(ev, h.episodes, info["activities_modeled"]))
    imp = rec.rf.feature_importances_
    S, Z = len(topo.sensors), topo.n_zones
    groups = [("Tần suất mỗi cảm biến trong cửa sổ", S), ("Cảm biến hiện tại", S), ("Vùng hiện tại", Z),
              ("Giờ trong ngày (sin, cos)", 2), ("Cuối tuần", 1), ("Độ dài cửa sổ", 1),
              ("Khoảng cách tới sự kiện trước", 1), ("Tỉ lệ nhảy xa", 1), ("Số cảm biến phân biệt", 1)]
    vals, k = [], 0
    for name, n in groups:
        vals.append((name, float(imp[k:k + n].sum()), n)); k += n
    vals.sort(key=lambda x: x[1])
    pd.DataFrame(vals, columns=["group", "importance", "n_features"]).to_csv(
        res / home / "rf_importance.csv", index=False)
    fig, ax = plt.subplots(figsize=(6.0, 2.8))
    ax.barh([f"{n} ({c})" for n, _, c in vals], [v for _, v, _ in vals], color=SERIES[3], height=0.65)
    for i, (_, v, _) in enumerate(vals):
        ax.text(v + 0.005, i, _r2(v).replace(".", ","), va="center", fontsize=7.5, color=INK)
    ax.set_xlabel("Tổng mức quan trọng (giảm Gini) của nhóm; trong ngoặc: số đặc trưng")
    ax.tick_params(axis="y", labelsize=7.5)
    ax.grid(axis="y", visible=False)
    _save(fig, figdir, f"rf_importance_{home}")


def fig_rolling(res: Path, figdir: Path):
    """F1 thói quen của từng lần chia (chấm) và trung bình (gạch) theo nhà và phương pháp."""
    homes = [h for h in HOMES if (res / h / "rolling.csv").exists()]
    if not homes:
        return
    srcs = ["B0", "B2+H", "M1+H", "M2+H"]
    fig, ax = plt.subplots(figsize=(6.4, 2.7))
    n = len(srcs); w = 0.8 / n
    for i, s in enumerate(srcs):
        for k, h in enumerate(homes):
            r = pd.read_csv(res / h / "rolling.csv")
            v = r[r["source"] == s]["f1"].to_numpy()
            x = k + (i - (n - 1) / 2) * w
            ax.scatter(np.full(len(v), x), v, s=12, color=SOURCE_COLOR[s], alpha=0.8, linewidths=0,
                       label=s if k == 0 else None)
            ax.plot([x - w * 0.38, x + w * 0.38], [v.mean()] * 2, color=SOURCE_COLOR[s], lw=2.2)
    ax.set_xticks(range(len(homes)), [HOME_LABEL[h] for h in homes])
    ax.set_ylim(0, 1.0); ax.set_ylabel("F1 thói quen")
    ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.17), fontsize=8)
    _save(fig, figdir, "rolling")


def table_false_habits(res: Path, tabdir: Path, home: str = "cairo", model: str = "M1"):
    """Phân tích thói quen giả của ``model``+H: mỗi thói quen dự đoán không khớp đáp án
    được truy về nhãn thật của các lần thực hiện tạo nên nó."""
    from collections import Counter
    from .experiments import CONFIG
    from .habits import circ_diff, fmt_hour, hour_of, match_habits, mine_habits, reference_habits
    from .io import load_home, motion_on, resident_of, split_days
    from .recognition import decode_episodes
    f = res / home / f"pred_{model}.npz"
    if not f.exists():
        return None
    info = json.loads((res / home / "info.json").read_text(encoding="utf-8"))
    acts = info["activities_modeled"]
    h = load_home(home); tr, te = split_days(h.days, CONFIG["train_ratio"])
    mo = motion_on(h.events)
    ev = mo[mo["day"].isin(te)].reset_index(drop=True)
    z = np.load(f)
    B = (z["P"] >= z["th"]).astype(np.uint8)
    occ = decode_episodes(ev, B, acts, resident_of, CONFIG["decode"]["merge_gap_min"], CONFIG["decode"]["min_events"])
    w = CONFIG["habit"]["half_window_min"] / 60
    hcfg = dict(half_h=w, freq_thr=CONFIG["habit"]["freq_thr"], min_days_type=CONFIG["habit"]["min_days_daytype"])
    pred = mine_habits(occ, te, source=model, **hcfg)
    ref = reference_habits(h.episodes, te, **hcfg)
    matched = {id(p) for p, _, _ in match_habits(pred, ref, CONFIG["match_max_gap_min"]).pairs}
    ep = h.episodes[h.episodes["day"].isin(te)]
    names = {"Breakfast": "Ăn sáng", "Lunch": "Ăn trưa", "Dinner": "Ăn tối", "R1_Wake": "R1 thức dậy",
             "R2_Wake": "R2 thức dậy", "R1_Sleep": "R1 ngủ", "R2_Sleep": "R2 ngủ", "R1_Work": "R1 làm việc",
             "R2_Take_Medicine": "R2 uống thuốc", "Night_Wandering": "Đi lại ban đêm",
             "Bed_to_Toilet": "Đi vệ sinh đêm", "Leave_Home": "Rời nhà", "Laundry": "Giặt đồ"}
    nm = lambda a: names.get(a, a.replace("_", "\\_"))
    rows = []
    for p in sorted((p for p in pred if id(p) not in matched), key=lambda p: (p.activity, p.typical)):
        o = occ[occ["activity"] == p.activity]
        o = o[np.abs(circ_diff(hour_of(o["start"]), p.typical)) <= w]
        cnt = Counter()
        for s, e in zip(o["start"], o["end"]):
            ov = ep[(ep["start"] <= e) & (ep["end"] >= s)]["activity"]
            cnt[p.activity if p.activity in set(ov) else (ov.mode().iloc[0] if len(ov) else "(không nhãn)")] += 1
        top, k = cnt.most_common(1)[0] if cnt else ("--", 0)
        same = [g for g in ref if g.activity == p.activity]
        near = min(same, key=lambda g: abs(circ_diff(g.typical, p.typical))) if same else None
        rows.append({"Thói quen giả": f"{nm(p.activity)} {fmt_hour(p.typical)}",
                     "Số ngày": f"{p.n_days}",
                     "Thói quen thật gần nhất": (f"{fmt_hour(near.typical)} (lệch "
                                                  f"{abs(circ_diff(near.typical, p.typical)) * 60:.0f} phút)")
                     if near else "không có",
                     "Nhãn thật trùng nhiều nhất": (nm(top) if top != "(không nhãn)" else top)
                     + (f" ({k}/{sum(cnt.values())})" if cnt else "")})
    d = pd.DataFrame(rows)
    d.to_csv(res / home / f"false_habits_{model}.csv", index=False)
    if len(d):
        _tex_table(d, tabdir / f"false_habits_{home}.tex",
                   f"Thói quen giả của {model}+H trên {HOME_LABEL[home]}: mỗi dòng truy các lần thực hiện "
                   "tạo nên thói quen về nhãn thật trùng thời gian", f"tab:false-{home}", "lccl")
    return d


def build_all(res: Path, thesis_dir: Path = Path("thesis")):
    _style()
    figdir, tabdir = thesis_dir / "figures", thesis_dir / "tables"
    out = tables(res, tabdir)
    try:
        out["false_habits"] = table_false_habits(res, tabdir)
    except Exception as e:
        print(f"[report] table_false_habits: {e}")
    for f in (fig_rq1, fig_rq2, fig_propagation, fig_rq3, fig_b0_failure, fig_activity_hours,
              fig_topology, fig_rf_importance, fig_rolling):
        try:
            f(res, figdir)
        except Exception as e:  # một hình lỗi không làm hỏng các hình khác
            print(f"[report] {f.__name__}: {e}")
    for h in ("cairo", "tulum1"):
        fig_habit_timeline(res, figdir, h)
    print(f"[report] xong: {len(list(figdir.glob('*.pdf')))} hình, {len(list(tabdir.glob('*.tex')))} bảng")
    return out
