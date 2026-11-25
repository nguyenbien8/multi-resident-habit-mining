"""RQ2 — phân tích lỗi lan truyền từ khâu nhận dạng sang khâu thói quen.

Thay vì chỉ quan sát vài mô hình, ta **làm nhiễu nhãn thật một cách có kiểm
soát** rồi khai phá thói quen trên nhãn đã nhiễu và so với đáp án. Bốn loại lỗi
mô phỏng đúng những gì một bộ nhận dạng có thể làm sai:

- ``drop``: bỏ sót một tỉ lệ p lần thực hiện (nhận dạng thiếu);
- ``jitter``: lệch giờ bắt đầu theo phân phối chuẩn độ lệch σ phút;
- ``spurious``: chèn thêm lần thực hiện giả ở giờ ngẫu nhiên, số lượng bằng p
  lần số thật (nhận dạng thừa);
- ``swap``: tráo người R1 ↔ R2 với xác suất p trên các hoạt động gắn người —
  lỗi đặc trưng của nhà nhiều người.

Kết quả là đường cong "mức lỗi → F1 thói quen", cho biết bộ nhận dạng cần tốt
đến đâu thì thói quen mới đáng tin.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .habits import match_habits, mine_habits, reference_habits


def corrupt(ep: pd.DataFrame, kind: str, level: float, rng: np.random.Generator,
            days: list) -> pd.DataFrame:
    ep = ep.copy().reset_index(drop=True)
    if level <= 0:
        return ep
    if kind == "drop":
        return ep[rng.random(len(ep)) >= level].reset_index(drop=True)
    if kind == "jitter":                      # level = σ (phút)
        sh = pd.to_timedelta(rng.normal(0, level, len(ep)), unit="m")
        ep["start"] += sh; ep["end"] += sh
        return ep
    if kind == "spurious":
        n = int(round(level * len(ep)))
        src = ep.sample(n, replace=True, random_state=int(rng.integers(1 << 31)))
        day = rng.choice(np.array(days, dtype="datetime64[ns]"), n)
        start = pd.to_datetime(day) + pd.to_timedelta(rng.uniform(0, 24 * 60, n), unit="m")
        dur = src["end"].to_numpy() - src["start"].to_numpy()
        fake = pd.DataFrame({"activity": src["activity"].to_numpy(),
                             "resident": src["resident"].to_numpy(),
                             "start": start, "end": start + dur})
        return pd.concat([ep, fake], ignore_index=True)
    if kind == "swap":
        m = (ep["resident"] != "H").to_numpy() & (rng.random(len(ep)) < level)
        other = {"R1": "R2", "R2": "R1"}
        acts = ep["activity"].to_numpy().copy()
        res = ep["resident"].to_numpy().copy()
        for i in np.flatnonzero(m):
            new = other[res[i]]
            cand = new + acts[i][2:]                 # R1_Wake -> R2_Wake
            acts[i], res[i] = cand, new
        ep["activity"], ep["resident"] = acts, res
        return ep
    raise ValueError(kind)


def propagation_curve(episodes: pd.DataFrame, days: list, kind: str, levels,
                      seeds=range(5), per_resident_only: bool = False) -> pd.DataFrame:
    ep = episodes[episodes["start"].dt.normalize().isin(days)]
    ref = reference_habits(ep, days)
    if per_resident_only:
        ref = [h for h in ref if h.resident != "H"]
    rows = []
    for lv in levels:
        for sd in seeds:
            rng = np.random.default_rng(1000 + sd)
            noisy = corrupt(ep, kind, lv, rng, days)
            pred = mine_habits(noisy, days)
            if per_resident_only:
                pred = [h for h in pred if h.resident != "H"]
            r = match_habits(pred, ref)
            rows.append({"kind": kind, "level": lv, "seed": sd, "precision": r.precision,
                         "recall": r.recall, "f1": r.f1, "time_err_min": r.time_err_min,
                         "n_ref": r.n_ref, "n_pred": r.n_pred})
    return pd.DataFrame(rows)
