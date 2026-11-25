"""RQ3 — dùng thói quen để phát hiện ngày bỏ thuốc.

Quy trình (văn bản định nghĩa đề tài, mục 7–8):

1. **Thói quen chuẩn** của hoạt động đích (ví dụ ``R2_Take_Medicine``) học từ
   nhãn của các ngày huấn luyện bằng chính định nghĩa thói quen. Cửa sổ phát
   hiện = khung 80% của thói quen nới thêm 30 phút mỗi phía.
2. **Cài bất thường**: chọn ngẫu nhiên 20% số ngày kiểm tra có uống thuốc, xóa
   mọi sự kiện cảm biến nằm trong các lần uống thuốc của ngày đó — mô phỏng
   "hôm đó không ai tới chỗ để thuốc". Các sự kiện khác (ăn sáng cùng bếp) giữ
   nguyên, nên bài toán không dễ: bếp vẫn có người đúng giờ đó.
3. **Phát hiện**: chạy bộ nhận dạng trên luồng đã sửa; nếu trong cửa sổ không
   có lần thực hiện hoạt động đích nào được nhận ra thì báo động.

Chỉ chấm điểm trên các ngày **có uống thuốc thật trong cửa sổ ở dữ liệu gốc**:
dương tính = ngày bị cài, âm tính = ngày còn nguyên. Ngày vốn không có nhãn uống
thuốc trong cửa sổ bị loại khỏi chấm điểm vì không phân biệt được "bỏ thuốc thật"
với "người chú thích không ghi nhãn"; số ngày này được báo cáo riêng.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .habits import Habit, circ_diff, day_mask, hour_of, mine_habits


@dataclass
class Window:
    habit: Habit
    lo: float   # giờ bắt đầu cửa sổ
    hi: float   # giờ kết thúc cửa sổ


def normal_windows(train_ep: pd.DataFrame, train_days: list, activity: str,
                   margin_min: float = 30.0) -> list[Window]:
    hb = [h for h in mine_habits(train_ep[train_ep["activity"] == activity], train_days)
          if h.activity == activity]
    m = margin_min / 60.0
    return [Window(h, (h.window[0] - m) % 24, (h.window[1] + m) % 24) for h in hb]


def _in_window(hours: np.ndarray, w: Window) -> np.ndarray:
    width = (w.hi - w.lo) % 24
    return ((hours - w.lo) % 24) <= width


def applies(w: Window, day: pd.Timestamp) -> bool:
    return bool(day_mask(pd.Series([day]), w.habit.day_type)[0])


def inject(events: pd.DataFrame, episodes: pd.DataFrame, candidate_days: list,
           activity: str, frac: float, rng: np.random.Generator):
    """Xóa sự kiện trong các lần thực hiện ``activity`` ở ``frac`` số ngày ứng viên
    (các ngày có thực hiện ``activity`` đúng thói quen trong dữ liệu gốc)."""
    ep = episodes[(episodes["activity"] == activity) & episodes["day"].isin(candidate_days)]
    cand = sorted(ep["day"].unique())
    k = max(1, int(round(frac * len(cand))))
    chosen = set(pd.to_datetime(rng.choice(np.array(cand, dtype="datetime64[ns]"), k, replace=False)))
    drop = np.zeros(len(events), bool)
    ts = events["ts"].to_numpy()
    for s, e, d in ep[["start", "end", "day"]].itertuples(index=False):
        if d in chosen:
            drop |= (ts >= np.datetime64(s)) & (ts <= np.datetime64(e))
    kept_ep = episodes[~((episodes["activity"] == activity) & episodes["day"].isin(chosen))]
    return events[~drop].reset_index(drop=True), kept_ep, chosen


def day_truth(episodes: pd.DataFrame, days: list, activity: str, windows: list[Window]) -> dict:
    """``True`` = ngày bỏ thuốc (không có lần thật nào trong cửa sổ áp dụng)."""
    ep = episodes[episodes["activity"] == activity]
    out = {}
    for d in days:
        ws = [w for w in windows if applies(w, d)]
        if not ws:
            continue
        h = hour_of(ep.loc[ep["day"] == d, "start"])
        out[d] = not any(_in_window(h, w).any() for w in ws)
    return out


def detect(pred_occ: pd.DataFrame, days: list, activity: str, windows: list[Window]) -> dict:
    """Báo động (``True``) nếu không nhận ra lần thực hiện nào trong cửa sổ."""
    occ = pred_occ[pred_occ["activity"] == activity]
    return day_truth(occ.assign(day=occ["start"].dt.normalize()) if len(occ) else occ,
                     days, activity, windows)


def zone_presence_detect(events: pd.DataFrame, days: list, zone_sensors: set,
                         windows: list[Window]) -> dict:
    """Baseline kiểu B0: báo động nếu vùng của chỗ để thuốc không có ai trong cửa sổ.
    Thói quen theo phòng không phân biệt "vào bếp uống thuốc" với "vào bếp ăn sáng"."""
    ev = events[events["sensor"].isin(zone_sensors)]
    occ = pd.DataFrame({"activity": "zone", "start": ev["ts"], "day": ev["day"]})
    return day_truth(occ, days, "zone", windows)


def score(truth: dict, alarm: dict, n_days: int) -> dict:
    keys = [d for d in truth if d in alarm]
    t = np.array([truth[d] for d in keys]); a = np.array([alarm[d] for d in keys])
    tp, fp, fn = int((t & a).sum()), int((~t & a).sum()), int((t & ~a).sum())
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": p, "recall": r,
            "f1": 2 * p * r / (p + r) if p + r else 0.0,
            "false_alarms_per_day": fp / max(n_days, 1), "n_eval_days": len(keys)}


def alarm_delay_min(windows: list[Window]) -> float:
    """Độ trễ báo động: từ giờ điển hình của thói quen đến cuối cửa sổ (phút)."""
    return float(np.mean([circ_diff(w.hi, w.habit.typical) % 24 * 60 for w in windows])) if windows else float("nan")
