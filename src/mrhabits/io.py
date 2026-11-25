"""Đọc dữ liệu CASAS (bản Zenodo 17180309) thành hai bảng chuẩn.

- ``events``: mỗi dòng một sự kiện cảm biến ``ts, sensor, value``.
- ``episodes``: mỗi dòng một lần thực hiện hoạt động có nhãn
  ``activity, resident, start, end``. Nhãn chỉ dùng để huấn luyện mô hình
  (trên ngày huấn luyện) và để đánh giá; không bao giờ là đầu vào lúc suy luận.

Quy ước người: nhãn có tiền tố ``R1_``/``R2_`` gắn với người đó; nhãn còn lại
là hoạt động **chung của hộ** (``resident = "H"``). Tên hoạt động giữ nguyên
nhãn gốc (ví dụ ``R2_Take_Medicine``) để không mất thông tin người.
"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

DATASETS = ("cairo", "tulum1", "tulum2", "milan", "aruba")
N_RESIDENTS = {"cairo": 2, "tulum1": 2, "tulum2": 2, "milan": 1, "aruba": 1}
DEFAULT_ZIP = Path("data/raw/casas/new_labeled_data.zip")


@dataclass
class HomeData:
    """Dữ liệu một nhà sau khi đọc và làm sạch."""

    name: str
    events: pd.DataFrame      # ts, sensor, value, day
    episodes: pd.DataFrame    # activity, resident, start, end, day
    days: list                # các ngày giữ lại (đã lọc chất lượng), tăng dần
    dropped_days: list        # các ngày bị loại vì quá ít sự kiện
    n_residents: int


def resident_of(activity: str) -> str:
    """``R1_Wake`` -> ``R1``; nhãn không có tiền tố -> ``H`` (chung của hộ)."""
    if activity.startswith("R1_"):
        return "R1"
    if activity.startswith("R2_"):
        return "R2"
    return "H"


def _parse_lines(text: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Tách văn bản CASAS thành sự kiện và các mốc begin/end của nhãn."""
    rows, marks = [], []
    for line in text.splitlines():
        p = line.split()
        if len(p) < 4:
            continue
        ts = p[0] + " " + p[1]
        rows.append((ts, p[2], p[3]))
        # Nhãn nằm ở 2 cột cuối: "<Activity> begin|end". Một dòng lỗi trong
        # tulum2 chỉ có chữ "begin" mà không có tên hoạt động -> bỏ qua.
        if len(p) >= 6 and p[-1] in ("begin", "end"):
            marks.append((ts, p[-2], p[-1]))
    ev = pd.DataFrame(rows, columns=["ts", "sensor", "value"])
    mk = pd.DataFrame(marks, columns=["ts", "activity", "mark"])
    for df in (ev, mk):
        # format="ISO8601" chấp nhận cả giây có và không có phần lẻ.
        df["ts"] = pd.to_datetime(df["ts"], format="ISO8601")
    return ev, mk


def _pair_marks(marks: pd.DataFrame) -> pd.DataFrame:
    """Ghép begin/end cùng tên hoạt động thành đoạn [start, end].

    Một ``begin`` mới khi đoạn trước chưa ``end`` sẽ đóng đoạn trước tại thời
    điểm đó (trường hợp hiếm, 4 lần trong tulum2). ``end`` không có ``begin``
    bị bỏ qua.
    """
    open_: dict[str, pd.Timestamp] = {}
    out = []
    for ts, act, mark in marks.sort_values("ts", kind="stable").itertuples(index=False):
        if mark == "begin":
            if act in open_:
                out.append((act, open_.pop(act), ts))
            open_[act] = ts
        elif act in open_:
            out.append((act, open_.pop(act), ts))
    ep = pd.DataFrame(out, columns=["activity", "start", "end"])
    ep = ep[ep["end"] > ep["start"]].reset_index(drop=True)
    ep["resident"] = ep["activity"].map(resident_of)
    return ep


def load_home(name: str, zip_path: Path | str = DEFAULT_ZIP,
              min_day_ratio: float = 0.2) -> HomeData:
    """Đọc một nhà, sắp xếp theo thời gian, lọc ngày thiếu dữ liệu.

    Quy tắc lọc (cố định trong văn bản định nghĩa đề tài): bỏ ngày có số sự
    kiện dưới ``min_day_ratio`` × trung vị số sự kiện mỗi ngày.
    """
    if name not in DATASETS:
        raise ValueError(f"Không biết bộ dữ liệu '{name}'. Chọn trong {DATASETS}.")
    with zipfile.ZipFile(zip_path) as z:
        text = z.read(f"{name}.txt").decode("utf-8", "replace")
    ev, mk = _parse_lines(text)
    ev = ev.sort_values("ts", kind="stable").reset_index(drop=True)
    ev["day"] = ev["ts"].dt.normalize()

    counts = ev.groupby("day").size()
    keep = counts[counts >= min_day_ratio * counts.median()].index
    dropped = sorted(set(counts.index) - set(keep))
    ev = ev[ev["day"].isin(keep)].reset_index(drop=True)

    ep = _pair_marks(mk)
    ep["day"] = ep["start"].dt.normalize()
    ep = ep[ep["day"].isin(keep)].reset_index(drop=True)
    return HomeData(name, ev, ep, sorted(keep), dropped, N_RESIDENTS[name])


def split_days(days: list, train_ratio: float = 0.6) -> tuple[list, list]:
    """Chia theo thứ tự thời gian: ``train_ratio`` số ngày đầu để huấn luyện."""
    n_train = int(round(len(days) * train_ratio))
    return list(days[:n_train]), list(days[n_train:])


def motion_on(events: pd.DataFrame) -> pd.DataFrame:
    """Chỉ giữ sự kiện cảm biến chuyển động bật (``M*`` = ON).

    Đây là đơn vị quan sát của mọi phương pháp: cảm biến nhiệt độ đổi chậm và
    không chỉ ra vị trí người; sự kiện OFF chỉ lặp lại thông tin của ON.
    """
    m = events["sensor"].str.startswith("M") & (events["value"] == "ON")
    return events[m].reset_index(drop=True)


def active_labels(events: pd.DataFrame, episodes: pd.DataFrame,
                  activities: list[str]) -> np.ndarray:
    """Ma trận nhãn đa nhãn: ``Y[i, k] = 1`` nếu sự kiện i nằm trong một đoạn
    của hoạt động k. Hai người có thể làm hai việc cùng lúc nên một sự kiện có
    thể mang nhiều nhãn.
    """
    ts = events["ts"].to_numpy()
    Y = np.zeros((len(events), len(activities)), dtype=np.uint8)
    for k, act in enumerate(activities):
        ep = episodes[episodes["activity"] == act]
        if ep.empty:
            continue
        starts = ep["start"].to_numpy()
        ends = ep["end"].to_numpy()
        # Đếm số đoạn đã bắt đầu trừ số đoạn đã kết thúc tại mỗi thời điểm.
        inside = (np.searchsorted(np.sort(starts), ts, side="right")
                  - np.searchsorted(np.sort(ends), ts, side="left"))
        Y[:, k] = inside > 0
    return Y


def describe(home: HomeData) -> dict:
    """Thống kê mô tả cho chương Dữ liệu."""
    ep = home.episodes
    return {
        "home": home.name,
        "residents": home.n_residents,
        "days_kept": len(home.days),
        "days_dropped": len(home.dropped_days),
        "first_day": str(home.days[0].date()),
        "last_day": str(home.days[-1].date()),
        "events": len(home.events),
        "motion_on_events": int((home.events["sensor"].str.startswith("M")
                                 & (home.events["value"] == "ON")).sum()),
        "sensors": int(home.events["sensor"].nunique()),
        "activities": int(ep["activity"].nunique()),
        "episodes": len(ep),
        "per_resident_activities": sorted(ep.loc[ep["resident"] != "H", "activity"].unique()),
    }

