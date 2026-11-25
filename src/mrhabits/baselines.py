"""Baseline không dùng nhãn khi khai phá thói quen.

- **B0** — phương pháp của đề tài thực tập: gom sự kiện thành *phiên* (ở liên
  tục trong một vùng), biểu diễn phiên bằng (giờ trên vòng tròn, thời lượng
  log), chạy DBSCAN theo từng vùng, giữ cụm xuất hiện ≥ 50% số ngày. Không tách
  người: hai người hoạt động xen kẽ làm phiên bị cắt vụn và trộn lẫn.
- **B1** — thêm bước **tách luồng theo vị trí** (ý tưởng chương 3 của Chen,
  2021: hai sự kiện liên tiếp ở hai nơi xa nhau khó do cùng một người gây ra).
  Mỗi sự kiện được gán vào "vệt" (track) có cảm biến cuối gần nhất trên đồ thị
  kề; nếu mọi vệt đều xa và chưa đủ số người thì mở vệt mới. Phiên được gom
  trong từng vệt.

B0/B1 không biết tên hoạt động. **Chỉ để đánh giá**, mỗi cụm được gán nhãn đa
số của các lần thực hiện có nhãn trùng thời gian với phiên của nó (đa số tính trên các phiên có nhãn); cụm có dưới 20% phiên
trùng nhãn được báo cáo riêng là "không nhãn". Cách gán này
thuận lợi cho baseline (dùng nhãn tập kiểm tra), nên so sánh là thận trọng
đối với các mô hình đề xuất.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN

from .habits import Habit, circ_mean, circ_window, hour_of, R
from .io import resident_of
from .topology import Topology

UNLABELED = "(không nhãn)"


def track_ids(ev: pd.DataFrame, topo: Topology, n_tracks: int = 2,
              near_hops: float = 2, idle_min: float = 15.0) -> np.ndarray:
    """Gán mỗi sự kiện vào một vệt (B1). Trả về mã vệt tăng dần."""
    sid = ev["sensor"].map(topo.index).to_numpy()
    t = ev["ts"].to_numpy().astype("datetime64[s]").astype(np.int64)
    idle = idle_min * 60
    tracks: list[list] = []      # [id, last_sensor, last_time]
    out = np.empty(len(ev), np.int64)
    next_id = 0
    for i in range(len(ev)):
        s, ti = sid[i], t[i]
        active = [tr for tr in tracks if ti - tr[2] <= idle]
        best, bd = None, math.inf
        for tr in active:
            d = topo.hops[tr[1], s]
            if d < bd or (d == bd and best is not None and tr[2] > best[2]):
                best, bd = tr, d
        if best is None or (bd > near_hops and len(active) < n_tracks):
            best = [next_id, s, ti]; next_id += 1
            tracks = active + [best]
        else:
            tracks = active
        best[1], best[2] = s, ti
        out[i] = best[0]
    return out


def sessions(ev: pd.DataFrame, topo: Topology, tracks: np.ndarray | None = None,
             gap_min: float = 30.0, min_dur_min: float = 1.0) -> pd.DataFrame:
    """Phiên = chuỗi sự kiện liên tiếp (trong cùng vệt nếu có) ở cùng một vùng,
    tách khi đổi vùng hoặc im lặng quá ``gap_min`` phút."""
    df = pd.DataFrame({"ts": ev["ts"].to_numpy(),
                       "zone": ev["sensor"].map(topo.zone).to_numpy(),
                       "track": tracks if tracks is not None else np.zeros(len(ev), int)})
    out = []
    for tr, g in df.groupby("track", sort=False):
        z = g["zone"].to_numpy(); ts = g["ts"].to_numpy()
        brk = np.r_[True, (z[1:] != z[:-1]) | (np.diff(ts) > np.timedelta64(int(gap_min * 60), "s"))]
        sid = np.cumsum(brk)
        s = pd.DataFrame({"sid": sid, "ts": ts, "zone": z}).groupby("sid").agg(
            start=("ts", "first"), end=("ts", "last"), zone=("zone", "first"), n=("ts", "size"))
        s["track"] = tr
        out.append(s)
    S = pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=["start", "end", "zone", "n", "track"])
    S["dur"] = (S["end"] - S["start"]).dt.total_seconds() / 60.0
    S = S[S["dur"] >= min_dur_min].reset_index(drop=True)
    S["day"] = S["start"].dt.normalize()
    return S.sort_values("start").reset_index(drop=True)


def label_sessions(S: pd.DataFrame, episodes: pd.DataFrame) -> np.ndarray:
    """Nhãn có thời gian chồng lấn lớn nhất với mỗi phiên (chỉ để đánh giá)."""
    lab = np.full(len(S), None, dtype=object)
    if S.empty or episodes.empty:
        return lab
    es = episodes["start"].to_numpy().astype("datetime64[s]").astype(np.int64)
    ee = episodes["end"].to_numpy().astype("datetime64[s]").astype(np.int64)
    acts = episodes["activity"].to_numpy()
    ss = S["start"].to_numpy().astype("datetime64[s]").astype(np.int64)
    se = S["end"].to_numpy().astype("datetime64[s]").astype(np.int64)
    for i0 in range(0, len(S), 2000):                     # theo khối để tiết kiệm bộ nhớ
        a, b = ss[i0:i0 + 2000, None], se[i0:i0 + 2000, None]
        ov = np.minimum(ee[None, :], b) - np.maximum(es[None, :], a)
        best = ov.argmax(1)
        ok = ov[np.arange(len(best)), best] > 0
        lab[i0:i0 + 2000][ok] = acts[best[ok]]
    return lab


def zone_habits(S: pd.DataFrame, obs_days: list, episodes: pd.DataFrame, *,
                eps: float = 0.5, dur_weight: float = 0.5, freq_thr: float = 0.5,
                min_labeled: float = 0.2, source: str = "B0") -> tuple[list[Habit], int]:
    """DBSCAN theo từng vùng như đề tài thực tập; trả về (thói quen có nhãn,
    số thói quen không gán được nhãn)."""
    n_days = len(obs_days)
    ms = max(5, math.ceil(0.2 * n_days))
    S = S[S["day"].isin(obs_days)].copy()
    S["label"] = label_sessions(S, episodes)
    S["h"] = hour_of(S["start"])
    habits, n_unlab = [], 0
    for z, g in S.groupby("zone"):
        if len(g) < ms:
            continue
        th = 2 * np.pi * g["h"].to_numpy() / 24
        X = np.c_[R * np.cos(th), R * np.sin(th), dur_weight * np.log1p(g["dur"].to_numpy())]
        lab = DBSCAN(eps=eps, min_samples=ms).fit_predict(X)
        for c in sorted(set(lab) - {-1}):
            m = g[lab == c]
            nd = m["day"].nunique()
            if nd / n_days < freq_thr:
                continue
            # Nhãn của cụm = nhãn đa số trong các phiên CÓ nhãn; cụm có dưới
            # ``min_labeled`` phiên trùng nhãn nào đó được coi là "không nhãn".
            vc = m["label"].dropna().value_counts()
            if len(vc) == 0 or vc.sum() / len(m) < min_labeled:
                n_unlab += 1
                continue
            act = vc.index[0]
            hs = m["h"].to_numpy()
            habits.append(Habit(act, resident_of(act), "all", circ_mean(hs), circ_window(hs),
                                float(m["dur"].median()), int(nd), nd / n_days, len(m), source,
                                {"zone": int(z), "purity": round(float(vc.iloc[0] / vc.sum()), 3)}))
    return habits, n_unlab
