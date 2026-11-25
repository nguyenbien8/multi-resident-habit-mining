"""Định nghĩa thói quen, khai phá thói quen (H) và so khớp với đáp án.

Thói quen (văn bản định nghĩa đề tài, mục 3): tập các lần thực hiện **cùng một
hoạt động, bởi cùng một người**, giờ bắt đầu lệch nhau không quá ~30 phút, xuất
hiện ở ít nhất 50% số ngày quan sát.

Giờ trong ngày là đại lượng vòng tròn (23:50 và 00:10 cách nhau 20 phút), nên
mỗi giờ bắt đầu h được đặt lên vòng tròn bán kính R = 24/(2π):

    x = (R cos θ, R sin θ),   θ = 2π h / 24.

Chu vi vòng tròn bằng 24 nên khoảng cách Euclid giữa hai điểm xấp xỉ số giờ
chênh lệch khi chênh lệch nhỏ. Nhờ đó ngưỡng 0,5 có nghĩa trực tiếp là ~30 phút.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from sklearn.cluster import DBSCAN, HDBSCAN

R = 24.0 / (2.0 * math.pi)
DAY_TYPES = ("all", "weekday", "weekend")


# --------------------------------------------------------------------------
# Thống kê vòng tròn
# --------------------------------------------------------------------------
def to_circle(hours: np.ndarray) -> np.ndarray:
    th = 2.0 * np.pi * np.asarray(hours, float) / 24.0
    return np.c_[R * np.cos(th), R * np.sin(th)]


def circ_mean(hours: np.ndarray) -> float:
    th = 2.0 * np.pi * np.asarray(hours, float) / 24.0
    m = math.atan2(np.sin(th).mean(), np.cos(th).mean())
    return (m * 24.0 / (2.0 * math.pi)) % 24.0


def circ_diff(a, b):
    """Chênh lệch có dấu a − b trên vòng 24 giờ, trong khoảng [−12, 12)."""
    return (np.asarray(a, float) - np.asarray(b, float) + 12.0) % 24.0 - 12.0


def circ_window(hours: np.ndarray, coverage: float = 0.8) -> tuple[float, float]:
    """Khung giờ chứa ``coverage`` số lần, lấy đối xứng quanh trung bình vòng tròn."""
    m = circ_mean(hours)
    d = np.sort(circ_diff(hours, m))
    lo = np.quantile(d, (1 - coverage) / 2)
    hi = np.quantile(d, 1 - (1 - coverage) / 2)
    return ((m + lo) % 24.0, (m + hi) % 24.0)


def hour_of(ts: pd.Series) -> np.ndarray:
    return (ts.dt.hour + ts.dt.minute / 60.0 + ts.dt.second / 3600.0).to_numpy()


# --------------------------------------------------------------------------
# Biểu diễn một thói quen
# --------------------------------------------------------------------------
@dataclass
class Habit:
    activity: str
    resident: str
    day_type: str
    typical: float              # giờ điển hình (trung bình vòng tròn)
    window: tuple[float, float]  # khung 80%
    duration_min: float         # thời lượng trung vị (phút)
    n_days: int                 # số ngày có xuất hiện
    freq: float                 # n_days / số ngày quan sát cùng loại
    n_points: int               # số lần thực hiện trong cụm
    source: str = ""            # phương pháp sinh ra thói quen
    extra: dict = field(default_factory=dict)

    def as_row(self) -> dict:
        lo, hi = self.window
        return {
            "activity": self.activity, "resident": self.resident,
            "day_type": self.day_type, "typical": fmt_hour(self.typical),
            "window80": f"{fmt_hour(lo)}–{fmt_hour(hi)}",
            "duration_min": round(self.duration_min, 1), "n_days": self.n_days,
            "freq": round(self.freq, 3), "n_points": self.n_points,
            "source": self.source, **self.extra,
        }


def fmt_hour(h: float) -> str:
    total = int(round((h % 24.0) * 60)) % (24 * 60)
    return f"{total // 60:02d}:{total % 60:02d}"


def day_mask(days: pd.Series, day_type: str) -> np.ndarray:
    wd = days.dt.day_of_week.to_numpy()
    if day_type == "weekday":
        return wd < 5
    if day_type == "weekend":
        return wd >= 5
    return np.ones(len(days), bool)


def n_days_of_type(days: list, day_type: str) -> int:
    return int(day_mask(pd.Series(pd.to_datetime(days)), day_type).sum())


# --------------------------------------------------------------------------
# Tìm thói quen trong một tập giờ bắt đầu
# --------------------------------------------------------------------------
@dataclass
class _Group:
    hours: np.ndarray   # giờ bắt đầu của các lần thuộc thói quen (mỗi ngày một lần)
    durs: np.ndarray    # thời lượng tương ứng (phút)
    days: np.ndarray    # ngày tương ứng
    n_points: int       # tổng số lần (kể cả nhiều lần trong một ngày)


def _scan(h: np.ndarray, dur: np.ndarray, day: np.ndarray, n_obs: int,
          half_h: float, freq_thr: float, step_min: int = 5) -> list[_Group]:
    """**Hiện thực trực tiếp định nghĩa thói quen.**

    Trượt cửa sổ ±``half_h`` giờ quanh vòng 24 giờ (bước ``step_min`` phút).
    Tại mỗi tâm c, đếm số **ngày phân biệt** có hoạt động bắt đầu trong
    [c − half_h, c + half_h]. Các tâm đạt ≥ ``freq_thr`` × ``n_obs`` ngày tạo
    thành các đoạn liên tiếp trên vòng tròn; mỗi đoạn cho một thói quen với
    tâm là điểm có số ngày lớn nhất (hòa thì lấy giữa vùng hòa). Đếm theo ngày
    nên một hoạt động lặp nhiều lần trong ngày không làm phồng tần suất, và
    cửa sổ có bề rộng cố định nên không có hiện tượng "chuỗi hóa" như DBSCAN.
    """
    grid = np.arange(0, 24 * 60, step_min) / 60.0
    D = np.abs(circ_diff(h[None, :], grid[:, None]))          # (n_grid, n_pts)
    inside = D <= half_h
    codes, day_idx = np.unique(day, return_inverse=True)
    counts = np.array([len(np.unique(day_idx[row])) for row in inside])
    ok = counts >= freq_thr * n_obs
    if not ok.any():
        return []
    # Các đoạn liên tiếp của ok trên vòng tròn.
    n = len(grid)
    if ok.all():
        runs = [np.arange(n)]
    else:
        start = int(np.argmin(ok))           # bắt đầu duyệt từ một điểm không đạt
        order = (np.arange(n) + start) % n
        runs, cur = [], []
        for i in order:
            if ok[i]:
                cur.append(i)
            elif cur:
                runs.append(np.array(cur)); cur = []
        if cur:
            runs.append(np.array(cur))
    # Mỗi đoạn cho một ứng viên (tâm, số ngày). Khử đỉnh không cực đại: hai
    # thói quen của cùng hoạt động phải cách nhau ≥ 2·half_h (cửa sổ không chồng
    # lên nhau); ưu tiên ứng viên có nhiều ngày hơn.
    cands = []
    for run in runs:
        best = counts[run].max()
        ties = run[counts[run] == best]
        cands.append((int(best), float(grid[ties[len(ties) // 2]])))
    centers: list[float] = []
    for _, c in sorted(cands, key=lambda x: -x[0]):
        if all(abs(circ_diff(c, o)) >= 2 * half_h for o in centers):
            centers.append(c)
    groups = []
    for c in sorted(centers):
        sel = np.abs(circ_diff(h, c)) <= half_h
        # Mỗi ngày lấy lần gần tâm nhất làm "lần thực hiện thói quen" của ngày đó.
        hs, ds, dys = h[sel], dur[sel], day[sel]
        dist = np.abs(circ_diff(hs, c))
        keep = pd.DataFrame({"d": dys, "dist": dist}).groupby("d")["dist"].idxmin().to_numpy()
        groups.append(_Group(hs[keep], ds[keep], dys[keep], int(sel.sum())))
    return groups


def _cluster(h, dur, day, n_obs, method, half_h, freq_thr, min_frac) -> list[_Group]:
    if method == "scan":
        return _scan(h, dur, day, n_obs, half_h, freq_thr)
    X = to_circle(h)
    if method == "dbscan":
        lab = DBSCAN(eps=half_h, min_samples=max(3, math.ceil(min_frac * n_obs))).fit_predict(X)
    elif method == "hdbscan":
        mcs = max(3, math.ceil(min_frac * n_obs))
        lab = (HDBSCAN(min_cluster_size=mcs, allow_single_cluster=True, copy=True).fit_predict(X)
               if len(X) >= mcs else -np.ones(len(X), int))
    else:
        raise ValueError(method)
    out = []
    for c in sorted(set(lab) - {-1}):
        m = lab == c
        out.append(_Group(h[m], dur[m], day[m], int(m.sum())))
    return out


def mine_habits(occ: pd.DataFrame, obs_days: list, *, method: str = "scan",
                half_h: float = 0.5, freq_thr: float = 0.5, min_frac: float = 0.2,
                split_daytype: bool = True, min_days_type: int = 4,
                source: str = "") -> list[Habit]:
    """Khai phá thói quen từ các lần thực hiện hoạt động.

    ``occ`` có các cột ``activity, resident, start, end``. Với mỗi hoạt động và
    mỗi loại ngày, tìm nhóm giờ bắt đầu (``method``: ``scan`` = định nghĩa,
    ``dbscan``/``hdbscan`` = phương án so sánh), giữ nhóm xuất hiện ở ít nhất
    ``freq_thr`` số ngày quan sát cùng loại.

    Thói quen riêng ngày thường hoặc cuối tuần được giữ khi: không có thói quen
    'all' nào cách < 1 giờ, và có ít nhất ``min_days_type`` ngày (tránh trường
    hợp 3/6 ngày cuối tuần đã đạt 50%).
    """
    habits: list[Habit] = []
    if occ.empty:
        return habits
    occ = occ.copy()
    occ["day"] = occ["start"].dt.normalize()
    occ["h"] = hour_of(occ["start"])
    occ["dur"] = (occ["end"] - occ["start"]).dt.total_seconds() / 60.0
    obs = pd.Series(pd.to_datetime(sorted(obs_days)))
    types = DAY_TYPES if split_daytype else ("all",)

    for (act, res), g in occ.groupby(["activity", "resident"], sort=True):
        found: dict[str, list[Habit]] = {t: [] for t in types}
        for t in types:
            n_obs = int(day_mask(obs, t).sum())
            gt = g[day_mask(g["day"], t)]
            if n_obs == 0 or gt.empty:
                continue
            for grp in _cluster(gt["h"].to_numpy(), gt["dur"].to_numpy(),
                                gt["day"].to_numpy(), n_obs, method, half_h,
                                freq_thr, min_frac):
                nd = len(np.unique(grp.days))
                if nd / n_obs < freq_thr:
                    continue
                if t != "all" and nd < min_days_type:
                    continue
                found[t].append(Habit(
                    act, res, t, circ_mean(grp.hours), circ_window(grp.hours),
                    float(np.median(grp.durs)), int(nd), nd / n_obs,
                    grp.n_points, source))
        habits.extend(found.get("all", []))
        for t in ("weekday", "weekend"):
            for hb in found.get(t, []):
                if not any(abs(circ_diff(a.typical, hb.typical)) * 60 < 60
                           for a in found.get("all", [])):
                    habits.append(hb)
    return habits


def reference_habits(episodes: pd.DataFrame, days: list, **kw) -> list[Habit]:
    """Thói quen đáp án: áp **đúng định nghĩa** (quét cửa sổ ±30 phút, ngưỡng
    50% số ngày) lên nhãn thật của các ngày ``days``."""
    ep = episodes[episodes["start"].dt.normalize().isin(days)]
    return mine_habits(ep, days, method="scan", source="reference", **kw)


def habits_frame(habits: list[Habit]) -> pd.DataFrame:
    return pd.DataFrame([h.as_row() for h in habits])


# --------------------------------------------------------------------------
# So khớp thói quen tìm được với đáp án
# --------------------------------------------------------------------------
@dataclass
class MatchResult:
    precision: float
    recall: float
    f1: float
    time_err_min: float      # sai số giờ điển hình trung bình (phút) của cặp khớp
    freq_err: float          # sai số tần suất trung bình của cặp khớp
    n_pred: int
    n_ref: int
    n_match: int
    pairs: list


def match_habits(pred: list[Habit], ref: list[Habit],
                 max_gap_min: float = 60.0) -> MatchResult:
    """Ghép một-một thói quen dự đoán với đáp án **cùng hoạt động** bằng thuật
    toán Hungary trên chênh lệch giờ điển hình; chỉ nhận cặp lệch
    ≤ ``max_gap_min`` phút.

    Loại ngày không bắt buộc trùng: thói quen "uống thuốc 06:57 mọi ngày" vẫn
    đúng về bản chất với đáp án "uống thuốc 07:08 ngày thường" (ngưỡng 50% đặt
    trên hai tập ngày khác nhau nên một thói quen gần ngưỡng có thể rơi vào loại
    ngày khác). Số cặp lệch loại ngày được ghi lại trong ``pairs``.
    """
    pairs = []
    keys = {h.activity for h in pred} | {h.activity for h in ref}
    for key in keys:
        P = [h for h in pred if h.activity == key]
        G = [h for h in ref if h.activity == key]
        if not P or not G:
            continue
        C = np.array([[abs(circ_diff(p.typical, g.typical)) * 60 for g in G] for p in P])
        Cb = np.where(C <= max_gap_min, C, 1e6)
        ri, ci = linear_sum_assignment(Cb)
        for i, j in zip(ri, ci):
            if C[i, j] <= max_gap_min:
                pairs.append((P[i], G[j], float(C[i, j])))
    n_m, n_p, n_r = len(pairs), len(pred), len(ref)
    prec = n_m / n_p if n_p else 0.0
    rec = n_m / n_r if n_r else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    te = float(np.mean([c for _, _, c in pairs])) if pairs else float("nan")
    fe = float(np.mean([abs(p.freq - g.freq) for p, g, _ in pairs])) if pairs else float("nan")
    return MatchResult(prec, rec, f1, te, fe, n_p, n_r, n_m, pairs)
