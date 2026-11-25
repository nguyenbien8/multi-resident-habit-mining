import numpy as np
import pandas as pd
import pytest

from mrhabits.anomaly import Window, day_truth, inject, score
from mrhabits.baselines import sessions, track_ids
from mrhabits.habits import Habit
from mrhabits.io import _pair_marks, _parse_lines, active_labels, resident_of, split_days
from mrhabits.propagation import corrupt
from mrhabits.recognition import decode_episodes, smooth, tune_thresholds
from mrhabits.topology import Topology


RAW = """2009-06-10 07:00:00.1 M001 ON R2_Take_Medicine begin
2009-06-10 07:00:05 M002 ON
2009-06-10 07:00:03 M001 OFF
2009-06-10 07:01:00 M002 OFF R2_Take_Medicine end
2009-06-10 07:02:00 T001 21.5
2009-06-10 07:03:00 M003 ON Breakfast begin
2009-06-10 07:20:00 M003 OFF Breakfast end
"""


def test_parse_and_pair():
    ev, mk = _parse_lines(RAW)
    assert len(ev) == 7 and len(mk) == 4
    ep = _pair_marks(mk)
    assert set(ep["activity"]) == {"R2_Take_Medicine", "Breakfast"}
    assert dict(zip(ep["activity"], ep["resident"])) == {"R2_Take_Medicine": "R2", "Breakfast": "H"}


def test_resident_prefix():
    assert resident_of("R1_Wake") == "R1" and resident_of("Dinner") == "H"


def test_split_is_chronological():
    d = list(pd.date_range("2024-01-01", periods=10))
    tr, te = split_days(d, 0.6)
    assert tr == d[:6] and te == d[6:]


def test_active_labels_multi_label():
    ev = pd.DataFrame({"ts": pd.to_datetime(["2024-01-01 07:00:30", "2024-01-01 07:10:00"])})
    ep = pd.DataFrame({"activity": ["A", "B"],
                       "start": pd.to_datetime(["2024-01-01 07:00", "2024-01-01 07:00"]),
                       "end": pd.to_datetime(["2024-01-01 07:01", "2024-01-01 07:30"])})
    Y = active_labels(ev, ep, ["A", "B"])
    assert Y.tolist() == [[1, 1], [0, 1]]


def test_smooth_and_thresholds():
    P = np.array([[0.0], [1.0], [1.0], [1.0]])
    assert smooth(P, 2)[:, 0].tolist() == [0.0, 0.5, 1.0, 1.0]
    Y = np.array([[0], [1], [1], [0]]); Pp = np.array([[0.2], [0.8], [0.7], [0.3]])
    assert 0.3 <= tune_thresholds(Pp, Y)[0] <= 0.7


def test_decode_merges_close_events():
    ts = pd.to_datetime(["2024-01-01 07:00", "2024-01-01 07:05", "2024-01-01 09:00", "2024-01-01 09:01"])
    ev = pd.DataFrame({"ts": ts})
    B = np.array([[1], [1], [1], [1]])
    occ = decode_episodes(ev, B, ["R1_Wake"], resident_of, merge_gap_min=10, min_events=2)
    assert len(occ) == 2 and set(occ["resident"]) == {"R1"}


def _line_topo(n=6):
    sensors = [f"M{i:03d}" for i in range(n)]
    hops = np.abs(np.subtract.outer(np.arange(n), np.arange(n))).astype(float)
    return Topology(sensors, {s: i for i, s in enumerate(sensors)}, np.zeros((n, n)),
                    hops == 1, hops, {s: (0 if i < n // 2 else 1) for i, s in enumerate(sensors)}, 2)


def test_tracks_separate_two_distant_people():
    topo = _line_topo()
    t0 = pd.Timestamp("2024-01-01 07:00")
    seq = ["M000", "M005", "M001", "M004", "M000", "M005"]
    ev = pd.DataFrame({"ts": [t0 + pd.Timedelta(seconds=10 * i) for i in range(6)], "sensor": seq})
    tk = track_ids(ev, topo, n_tracks=2)
    assert tk[0] == tk[2] == tk[4] and tk[1] == tk[3] == tk[5] and tk[0] != tk[1]
    S = sessions(ev, topo, tk, min_dur_min=0)
    assert len(S) == 2                       # mỗi người một phiên, không bị cắt vụn


def test_corrupt_swap_and_drop():
    ep = pd.DataFrame({"activity": ["R1_Wake"] * 100, "resident": ["R1"] * 100,
                       "start": pd.Timestamp("2024-01-01 07:00"), "end": pd.Timestamp("2024-01-01 07:05")})
    rng = np.random.default_rng(0)
    sw = corrupt(ep, "swap", 1.0, rng, [])
    assert set(sw["activity"]) == {"R2_Wake"} and set(sw["resident"]) == {"R2"}
    assert len(corrupt(ep, "drop", 0.5, np.random.default_rng(0), [])) == pytest.approx(50, abs=15)


def test_inject_and_detect():
    d = list(pd.date_range("2024-01-01", periods=10))
    ep = pd.DataFrame({"activity": "Meds", "resident": "H",
                       "start": [x + pd.Timedelta(hours=7) for x in d],
                       "end": [x + pd.Timedelta(hours=7, minutes=2) for x in d]})
    ep["day"] = ep["start"].dt.normalize()
    ev = pd.DataFrame({"ts": [x + pd.Timedelta(hours=7, minutes=1) for x in d], "sensor": "M001"})
    ev["day"] = ev["ts"].dt.normalize()
    ev2, ep2, chosen = inject(ev, ep, d, "Meds", 0.2, np.random.default_rng(0))
    assert len(chosen) == 2 and len(ev2) == 8
    w = [Window(Habit("Meds", "H", "all", 7.0, (6.9, 7.1), 2, 10, 1, 10), 6.5, 7.5)]
    truth = day_truth(ep2, d, "Meds", w)
    assert sum(truth.values()) == 2
    s = score(truth, truth, 10)
    assert s["f1"] == 1.0 and s["false_alarms_per_day"] == 0
