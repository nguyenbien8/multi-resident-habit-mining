"""RQ1 — gán các đoạn sự kiện cảm biến cho (người, hoạt động).

Bài toán đa nhãn trên từng sự kiện chuyển động-ON: ``Y[i, k] = 1`` nếu sự kiện
i nằm trong một lần thực hiện hoạt động k. Tên hoạt động giữ tiền tố người
(``R2_Take_Medicine``) nên "đúng người" được mã hóa sẵn trong nhãn. Hai người có
thể làm hai việc cùng lúc nên một sự kiện có thể mang nhiều nhãn.

Ba bộ nhận dạng:

- **B2** tra bảng: P(hoạt động | vùng của cảm biến, khung 30 phút) từ dữ liệu
  huấn luyện — baseline không học đặc trưng.
- **M1** Random Forest trên đặc trưng của cửa sổ W sự kiện gần nhất.
- **M2** Bi-GRU trên chuỗi W sự kiện gần nhất (nhúng cảm biến + thời gian).

Mọi bộ nhận dạng chỉ nhìn **quá khứ** (cửa sổ kết thúc tại sự kiện hiện tại),
giống điều kiện khi triển khai thật. Ngưỡng quyết định của từng hoạt động được
chọn trên tập kiểm định (25% số ngày cuối của tập huấn luyện), không nhìn tập
kiểm tra.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score

from .topology import Topology


# --------------------------------------------------------------------------
# Đặc trưng
# --------------------------------------------------------------------------
def _seconds(ts: pd.Series) -> np.ndarray:
    return ts.to_numpy().astype("datetime64[ms]").astype(np.int64) / 1000.0


def window_features(ev: pd.DataFrame, topo: Topology, W: int = 20) -> np.ndarray:
    """Đặc trưng cửa sổ W sự kiện kết thúc tại mỗi sự kiện (đã sắp xếp)."""
    n, S = len(ev), len(topo.sensors)
    sid = ev["sensor"].map(topo.index).fillna(-1).astype(int).to_numpy()
    t = _seconds(ev["ts"])
    hour = ev["ts"].dt.hour.to_numpy() + ev["ts"].dt.minute.to_numpy() / 60.0
    zones = np.array([topo.zone.get(s, -1) for s in topo.sensors] + [-1])

    onehot = np.zeros((n, S + 1), np.float32)
    onehot[np.arange(n), np.where(sid >= 0, sid, S)] = 1
    cs = np.cumsum(onehot, axis=0)
    # Đếm cảm biến trong cửa sổ = cs[i] − cs[i−W]
    shifted = np.zeros_like(cs)
    shifted[W:] = cs[:-W]
    counts = (cs - shifted)[:, :S] / W

    # "Nhảy xa": hai sự kiện liên tiếp ở hai cảm biến cách ≥ 3 bước trên đồ thị
    # kề trong vòng 10 giây — dấu hiệu có hơn một người đang hoạt động.
    hops = topo.hops
    a, b = sid[:-1], sid[1:]
    valid = (a >= 0) & (b >= 0)
    hop = np.zeros(n)
    hop[1:][valid] = hops[a[valid], b[valid]]
    hop[~np.isfinite(hop)] = 10
    dt = np.r_[0.0, np.diff(t)]
    jump = ((hop >= 3) & (dt <= 10)).astype(float)
    jc = np.cumsum(jump)
    jsh = np.zeros(n); jsh[W:] = jc[:-W]
    jumps = (jc - jsh) / W

    span = t - t[np.maximum(np.arange(n) - W + 1, 0)]
    zone_now = zones[np.where(sid >= 0, sid, S)]
    zone_oh = np.zeros((n, topo.n_zones), np.float32)
    ok = zone_now >= 0
    zone_oh[np.arange(n)[ok], zone_now[ok]] = 1
    n_distinct = (counts > 0).sum(1)
    wd = ev["ts"].dt.day_of_week.to_numpy()
    X = np.column_stack([
        counts, onehot[:, :S], zone_oh,
        np.sin(2 * np.pi * hour / 24), np.cos(2 * np.pi * hour / 24),
        (wd >= 5).astype(float), np.log1p(span), np.log1p(dt), jumps, n_distinct,
    ]).astype(np.float32)
    return X


def sequence_inputs(ev: pd.DataFrame, topo: Topology, W: int = 30):
    """Đầu vào cho Bi-GRU: chỉ số cảm biến (+1, 0 = đệm) và đặc trưng thời gian
    của W sự kiện gần nhất cho mỗi vị trí."""
    n = len(ev)
    sid = ev["sensor"].map(topo.index).fillna(-1).astype(int).to_numpy() + 1
    t = _seconds(ev["ts"])
    hour = ev["ts"].dt.hour.to_numpy() + ev["ts"].dt.minute.to_numpy() / 60.0
    dt = np.r_[0.0, np.diff(t)]
    tf = np.column_stack([np.sin(2 * np.pi * hour / 24), np.cos(2 * np.pi * hour / 24),
                          np.log1p(np.clip(dt, 0, None)) / 5.0]).astype(np.float32)
    idx = np.arange(n)[:, None] - np.arange(W - 1, -1, -1)[None, :]   # (n, W)
    pad = idx < 0
    idx = np.clip(idx, 0, None)
    S = sid[idx]; S[pad] = 0
    T = tf[idx]; T[pad] = 0
    return S.astype(np.int64), T


# --------------------------------------------------------------------------
# Bộ nhận dạng
# --------------------------------------------------------------------------
class LookupRecognizer:
    """B2: P(hoạt động k | vùng, khung 30 phút) đếm từ dữ liệu huấn luyện."""

    def __init__(self, topo: Topology, slot_min: int = 30):
        self.topo, self.slot = topo, slot_min

    def _cells(self, ev):
        z = ev["sensor"].map(self.topo.zone).fillna(-1).astype(int).to_numpy() + 1
        s = (ev["ts"].dt.hour * 60 + ev["ts"].dt.minute).to_numpy() // self.slot
        return z * (24 * 60 // self.slot) + s

    def fit(self, ev, Y):
        c = self._cells(ev)
        n_cells = (self.topo.n_zones + 1) * (24 * 60 // self.slot)
        num = np.zeros((n_cells, Y.shape[1])); den = np.zeros(n_cells)
        np.add.at(num, c, Y); np.add.at(den, c, 1)
        self.p = num / np.maximum(den, 1)[:, None]
        return self

    def predict_proba(self, ev):
        return self.p[self._cells(ev)]


class ForestRecognizer:
    """M1: Random Forest đa đầu ra trên đặc trưng cửa sổ."""

    def __init__(self, topo: Topology, W: int = 20, n_estimators: int = 150, seed: int = 0):
        self.topo, self.W = topo, W
        self.rf = RandomForestClassifier(n_estimators=n_estimators, min_samples_leaf=3,
                                         max_features="sqrt", class_weight="balanced_subsample",
                                         n_jobs=-1, random_state=seed)

    def fit(self, ev, Y):
        self.rf.fit(window_features(ev, self.topo, self.W), Y)
        return self

    def predict_proba(self, ev):
        P = self.rf.predict_proba(window_features(ev, self.topo, self.W))
        if not isinstance(P, list):
            P = [P]
        out = []
        for p, cls in zip(P, self.rf.classes_):
            cls = list(cls)
            out.append(p[:, cls.index(1)] if 1 in cls else np.zeros(len(p)))
        return np.column_stack(out)


class GRURecognizer:
    """M2: Bi-GRU trên chuỗi W sự kiện (nhúng cảm biến 16 chiều + 3 đặc trưng
    thời gian), đầu ra sigmoid đa nhãn. Dừng sớm theo mất mát trên tập kiểm định."""

    # Cấu hình mặc định chọn theo mất mát trên tập kiểm định Cairo trong 3 cấu
    # hình thử (64/0.2/1e-3/0: 0.3626; 32/0.3/5e-4/1e-4: 0.3645;
    # 32/0.5/3e-4/1e-3: 0.3772) — xem v1/nhat_ky_thuc_nghiem.md.
    def __init__(self, topo: Topology, W: int = 30, hidden: int = 64, epochs: int = 15,
                 batch: int = 512, lr: float = 1e-3, weight_decay: float = 0.0,
                 dropout: float = 0.2, seed: int = 0, patience: int = 3):
        self.topo, self.W, self.hidden, self.dropout = topo, W, hidden, dropout
        self.epochs, self.batch, self.lr, self.wd = epochs, batch, lr, weight_decay
        self.seed, self.patience = seed, patience
        self.best_val = math.inf
        self.best_epoch = epochs

    def _net(self, n_sensors, K):
        import torch.nn as nn

        class Net(nn.Module):
            def __init__(s):
                super().__init__()
                s.emb = nn.Embedding(n_sensors + 1, 16, padding_idx=0)
                s.gru = nn.GRU(16 + 3, self.hidden, batch_first=True, bidirectional=True)
                s.drop = nn.Dropout(self.dropout)
                s.out = nn.Linear(2 * self.hidden, K)

            def forward(s, S, T):
                import torch
                x = torch.cat([s.emb(S), T], dim=-1)
                _, h = s.gru(x)                       # h: (2, B, H)
                h = torch.cat([h[0], h[1]], dim=-1)
                return s.out(s.drop(h))
        return Net()

    def fit(self, ev, Y, ev_val=None, Y_val=None, log=print):
        import torch
        torch.manual_seed(self.seed); np.random.seed(self.seed)
        S, T = sequence_inputs(ev, self.topo, self.W)
        K = Y.shape[1]
        self.net = self._net(len(self.topo.sensors), K)
        pos = Y.mean(0).clip(1e-4, None)
        pw = torch.tensor(np.clip((1 - pos) / pos, 1, 50), dtype=torch.float32)
        lossf = torch.nn.BCEWithLogitsLoss(pos_weight=pw)
        opt = torch.optim.Adam(self.net.parameters(), lr=self.lr, weight_decay=self.wd)
        St, Tt, Yt = torch.from_numpy(S), torch.from_numpy(T), torch.from_numpy(Y.astype(np.float32))
        if ev_val is not None:
            Sv, Tv = sequence_inputs(ev_val, self.topo, self.W)
            Sv, Tv, Yv = torch.from_numpy(Sv), torch.from_numpy(Tv), torch.from_numpy(Y_val.astype(np.float32))
        best, best_state, bad = math.inf, None, 0
        for ep in range(self.epochs):
            self.net.train()
            perm = torch.randperm(len(St))
            tot = 0.0
            for i in range(0, len(perm), self.batch):
                b = perm[i:i + self.batch]
                opt.zero_grad()
                loss = lossf(self.net(St[b], Tt[b]), Yt[b])
                loss.backward(); opt.step()
                tot += float(loss.detach()) * len(b)
            msg = f"    epoch {ep + 1}: train loss {tot / len(St):.4f}"
            if ev_val is not None:
                self.net.eval()
                with torch.no_grad():
                    vl = sum(float(lossf(self.net(Sv[i:i + 4096], Tv[i:i + 4096]), Yv[i:i + 4096])) * len(Sv[i:i + 4096])
                             for i in range(0, len(Sv), 4096)) / len(Sv)
                msg += f", val loss {vl:.4f}"
                if vl < best - 1e-4:
                    best, bad = vl, 0
                    self.best_epoch = ep + 1
                    best_state = {k: v.clone() for k, v in self.net.state_dict().items()}
                else:
                    bad += 1
            log(msg)
            if ev_val is not None and bad >= self.patience:
                break
        if best_state is not None:
            self.net.load_state_dict(best_state)
        self.best_val = best
        return self

    def predict_proba(self, ev):
        import torch
        S, T = sequence_inputs(ev, self.topo, self.W)
        self.net.eval()
        out = []
        with torch.no_grad():
            for i in range(0, len(S), 4096):
                out.append(torch.sigmoid(self.net(torch.from_numpy(S[i:i + 4096]),
                                                  torch.from_numpy(T[i:i + 4096]))).numpy())
        return np.vstack(out)


# --------------------------------------------------------------------------
# Ngưỡng, giải mã thành lần thực hiện, chỉ số RQ1
# --------------------------------------------------------------------------
def smooth(P: np.ndarray, k: int = 5) -> np.ndarray:
    """Trung bình trượt nhân quả trên k sự kiện để giảm nhấp nháy."""
    c = np.cumsum(np.vstack([np.zeros((1, P.shape[1])), P]), axis=0)
    i = np.arange(1, len(P) + 1)
    lo = np.maximum(i - k, 0)
    return (c[i] - c[lo]) / (i - lo)[:, None]


def tune_thresholds(P: np.ndarray, Y: np.ndarray, grid=np.arange(0.1, 0.91, 0.05)) -> np.ndarray:
    """Mỗi hoạt động chọn ngưỡng cho F1 cao nhất trên tập kiểm định."""
    th = np.full(P.shape[1], 0.5)
    for k in range(P.shape[1]):
        if Y[:, k].sum() == 0:
            continue
        f = [f1_score(Y[:, k], P[:, k] >= g, zero_division=0) for g in grid]
        th[k] = grid[int(np.argmax(f))]
    return th


def decode_episodes(ev: pd.DataFrame, B: np.ndarray, activities: list[str],
                    resident_of, merge_gap_min: float = 10.0, min_events: int = 2) -> pd.DataFrame:
    """Biến dự đoán nhị phân theo sự kiện thành các lần thực hiện hoạt động:
    các sự kiện dương liên tiếp, nối khi cách nhau ≤ ``merge_gap_min`` phút, bỏ
    đoạn có ít hơn ``min_events`` sự kiện."""
    ts = ev["ts"].to_numpy()
    rows = []
    gap = np.timedelta64(int(merge_gap_min * 60), "s")
    for k, act in enumerate(activities):
        pos = np.flatnonzero(B[:, k])
        if len(pos) == 0:
            continue
        tpos = ts[pos]
        brk = np.flatnonzero(np.diff(tpos) > gap)
        starts = np.r_[0, brk + 1]; ends = np.r_[brk, len(pos) - 1]
        for s, e in zip(starts, ends):
            if e - s + 1 >= min_events:
                rows.append((act, resident_of(act), pd.Timestamp(tpos[s]), pd.Timestamp(tpos[e])))
    out = pd.DataFrame(rows, columns=["activity", "resident", "start", "end"])
    out["day"] = out["start"].dt.normalize() if len(out) else pd.Series(dtype="datetime64[ns]")
    return out


@dataclass
class RQ1Scores:
    macro_f1: float
    micro_f1: float
    per_activity: dict


def rq1_scores(Y: np.ndarray, B: np.ndarray, activities: list[str]) -> RQ1Scores:
    present = [k for k in range(Y.shape[1]) if Y[:, k].sum() > 0]
    per = {activities[k]: float(f1_score(Y[:, k], B[:, k], zero_division=0)) for k in present}
    return RQ1Scores(float(np.mean(list(per.values()))) if per else float("nan"),
                     float(f1_score(Y[:, present], B[:, present], average="micro", zero_division=0)),
                     per)
