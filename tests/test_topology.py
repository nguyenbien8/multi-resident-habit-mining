import numpy as np
import pandas as pd

from mrhabits.topology import build_topology


def _walk(path, n_rounds=60, start="2024-01-01 07:00", step_s=2, gap_s=120):
    """Một người đi tới đi lui theo ``path``; giữa các lượt nghỉ ``gap_s`` giây."""
    rows, t = [], pd.Timestamp(start)
    for r in range(n_rounds):
        seq = path if r % 2 == 0 else path[::-1]
        for s in seq:
            rows.append((t, s)); t += pd.Timedelta(seconds=step_s)
        t += pd.Timedelta(seconds=gap_s)
    return rows


def test_two_rooms_become_two_zones_and_far_apart():
    room_a = ["M001", "M002", "M003"]
    room_b = ["M004", "M005", "M006"]
    rows = _walk(room_a) + _walk(room_b, start="2024-01-02 07:00") + \
        _walk(["M003", "M004"], n_rounds=6, start="2024-01-03 07:00")     # cửa nối hai phòng
    ev = pd.DataFrame(rows, columns=["ts", "sensor"]).sort_values("ts").reset_index(drop=True)
    topo = build_topology(ev, n_zones=2)
    za = {topo.zone[s] for s in room_a}; zb = {topo.zone[s] for s in room_b}
    assert len(za) == 1 and len(zb) == 1 and za != zb
    i, j = topo.index["M001"], topo.index["M006"]
    assert np.isfinite(topo.hops[i, j]) and topo.hops[i, j] >= 3
    assert topo.adjacency[topo.index["M001"], topo.index["M002"]]


def test_graph_is_connected_even_without_bridge():
    rows = _walk(["M001", "M002"]) + _walk(["M005", "M006"], start="2024-01-02 07:00")
    ev = pd.DataFrame(rows, columns=["ts", "sensor"]).sort_values("ts").reset_index(drop=True)
    topo = build_topology(ev, n_zones=2)
    assert np.isfinite(topo.hops).all()
