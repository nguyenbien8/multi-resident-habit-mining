import numpy as np
import pandas as pd
import pytest

from mrhabits.habits import (Habit, circ_diff, circ_mean, circ_window, match_habits,
                             mine_habits, reference_habits)


def occ(activity, starts, dur_min=5, resident="H"):
    s = pd.to_datetime(starts)
    return pd.DataFrame({"activity": activity, "resident": resident,
                         "start": s, "end": s + pd.Timedelta(minutes=dur_min)})


def days(n, start="2024-01-01"):                 # 2024-01-01 là thứ Hai
    return list(pd.date_range(start, periods=n, freq="D"))


def test_circular_mean_wraps_midnight():
    assert circ_mean(np.array([23.5, 0.5])) == pytest.approx(0.0, abs=1e-6) or \
        circ_mean(np.array([23.5, 0.5])) == pytest.approx(24.0, abs=1e-6)
    assert circ_diff(0.25, 23.75) == pytest.approx(0.5)


def test_circular_window_contains_mean():
    lo, hi = circ_window(np.array([7.0, 7.1, 7.2, 7.3, 7.4]))
    assert lo <= 7.2 <= hi


def test_scan_finds_daily_habit_and_ignores_rare_one():
    d = days(10)
    daily = [x + pd.Timedelta(hours=7, minutes=10 + i % 3) for i, x in enumerate(d)]
    rare = [d[0] + pd.Timedelta(hours=15), d[1] + pd.Timedelta(hours=15)]
    hb = mine_habits(pd.concat([occ("Meds", daily, 1, "R2"), occ("Meds", rare, 1, "R2")]),
                     d, split_daytype=False)
    assert len(hb) == 1
    h = hb[0]
    assert h.activity == "Meds" and h.resident == "R2"
    assert h.n_days == 10 and h.freq == 1.0
    assert circ_diff(h.typical, 7 + 11 / 60) == pytest.approx(0, abs=0.05)


def test_scan_counts_days_not_occurrences():
    """Một hoạt động lặp 5 lần trong MỘT ngày không được thành thói quen."""
    d = days(10)
    burst = [d[0] + pd.Timedelta(hours=12, minutes=m) for m in range(0, 25, 5)]
    assert mine_habits(occ("Snack", burst), d, split_daytype=False) == []


def test_scan_does_not_chain_like_dbscan():
    """Hoạt động trải đều cả ngày không tạo một thói quen dài cả ngày."""
    d = days(10)
    spread = [x + pd.Timedelta(hours=h) for x in d for h in range(8, 22, 2)]
    for h in mine_habits(occ("TV", spread), d, split_daytype=False):
        lo, hi = h.window
        assert (hi - lo) % 24 <= 1.0 + 1e-9


def test_weekend_only_habit_is_kept():
    d = days(28)
    wk = [x + pd.Timedelta(hours=9) for x in d if x.day_of_week >= 5]
    hb = mine_habits(occ("Wake", wk, resident="R2"), d)
    assert [h.day_type for h in hb] == ["weekend"]


def test_reference_restricts_to_given_days():
    d = days(10)
    starts = [x + pd.Timedelta(hours=7) for x in d]
    ep = occ("Wake", starts)
    assert len(reference_habits(ep, d[:5], split_daytype=False)) == 1


def H(act, t, day_type="all"):
    return Habit(act, "H", day_type, t, (t, t), 1, 5, 0.5, 5)


def test_match_hungarian_and_gap():
    ref = [H("A", 7.0), H("A", 19.0), H("B", 12.0)]
    pred = [H("A", 7.4), H("A", 13.0), H("B", 12.2, "weekday")]
    r = match_habits(pred, ref, max_gap_min=60)
    assert r.n_match == 2                 # A@7.4↔7.0 và B (khác loại ngày vẫn khớp)
    assert r.precision == pytest.approx(2 / 3) and r.recall == pytest.approx(2 / 3)
    assert r.time_err_min == pytest.approx((24 + 12) / 2)


def test_match_empty():
    r = match_habits([], [H("A", 7)])
    assert r.f1 == 0 and r.recall == 0
