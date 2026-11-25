"""Cấu trúc nhà rút ra từ dữ liệu: đồ thị kề giữa cảm biến và vùng (zone).

Không dùng tọa độ vẽ tay: hai cảm biến được coi là kề nhau nếu một người hay
kích hoạt chúng liên tiếp trong vài giây. Từ đó có:

- ``hops[i, j]``: số bước ngắn nhất trên đồ thị kề (dùng để tách người ở B1 và
  làm đặc trưng "nhảy xa" cho mô hình học);
- ``zone[s]``: vùng của cảm biến, phân cụm phổ trên ma trận chuyển tiếp. Vùng
  đóng vai trò "phòng" của phương pháp thực tập khi bộ dữ liệu không ghi phòng.

Chỉ dùng dữ liệu của các **ngày huấn luyện**.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.sparse.csgraph import shortest_path
from sklearn.cluster import SpectralClustering


@dataclass
class Topology:
    sensors: list[str]
    index: dict[str, int]
    transitions: np.ndarray   # số lần chuyển liên tiếp i -> j (đối xứng hóa)
    adjacency: np.ndarray     # bool, kề nhau
    hops: np.ndarray          # số bước ngắn nhất (inf nếu không nối)
    zone: dict[str, int]
    n_zones: int


def transition_matrix(ev: pd.DataFrame, sensors: list[str],
                      max_gap_s: float = 10.0) -> np.ndarray:
    idx = {s: i for i, s in enumerate(sensors)}
    s = ev["sensor"].map(idx).to_numpy()
    t = ev["ts"].to_numpy().astype("datetime64[ms]").astype(np.int64) / 1000.0
    a, b, dt = s[:-1], s[1:], np.diff(t)
    m = (dt <= max_gap_s) & (a != b)
    T = np.zeros((len(sensors), len(sensors)))
    np.add.at(T, (a[m], b[m]), 1)
    return T + T.T


def build_topology(motion_train: pd.DataFrame, n_zones: int | None = None,
                   min_share: float = 0.08, max_gap_s: float = 5.0,
                   seed: int = 0) -> Topology:
    """``motion_train``: sự kiện chuyển động-ON của ngày huấn luyện, đã sắp xếp."""
    sensors = sorted(motion_train["sensor"].unique())
    T = transition_matrix(motion_train, sensors, max_gap_s)
    row = T.sum(1, keepdims=True)
    share = np.divide(T, row, out=np.zeros_like(T), where=row > 0)
    # Kề nhau: chiếm ≥ min_share số lần rời khỏi cảm biến theo ít nhất một chiều.
    # Ngưỡng 8% và cửa sổ 5 giây loại các "chuyển tiếp giả" sinh ra khi hai
    # người kích hoạt hai cảm biến xa nhau gần như cùng lúc (kiểm chứng trên
    # bản đồ Cairo: bếp M021 và phòng ngủ tầng trên M005 không còn kề nhau).
    adj = (share >= min_share) | (share.T >= min_share)
    np.fill_diagonal(adj, False)
    _connect(adj, share)
    hops = shortest_path(adj.astype(float), unweighted=True, directed=False)

    A = share + share.T
    if n_zones is None:
        n_zones = _eigengap(A, kmin=3, kmax=min(10, len(sensors) - 1))
    lab = SpectralClustering(n_clusters=n_zones, affinity="precomputed",
                             random_state=seed, assign_labels="discretize").fit_predict(A + 1e-9)
    zone = {s: int(z) for s, z in zip(sensors, lab)}
    return Topology(sensors, {s: i for i, s in enumerate(sensors)}, T, adj, hops, zone, n_zones)


def _connect(adj: np.ndarray, share: np.ndarray) -> None:
    """Nếu đồ thị bị tách rời, nối các thành phần bằng cạnh mạnh nhất giữa chúng."""
    from scipy.sparse.csgraph import connected_components
    while True:
        n, lab = connected_components(adj, directed=False)
        if n <= 1:
            return
        A = share + share.T
        m = lab[:, None] != lab[None, :]
        i, j = np.unravel_index(np.argmax(np.where(m, A, -1)), A.shape)
        adj[i, j] = adj[j, i] = True


def _eigengap(A: np.ndarray, kmin: int, kmax: int) -> int:
    """Chọn số vùng bằng khoảng cách trị riêng lớn nhất của Laplacian chuẩn hóa."""
    d = A.sum(1)
    d[d == 0] = 1
    Dm = np.diag(1 / np.sqrt(d))
    L = np.eye(len(A)) - Dm @ A @ Dm
    w = np.sort(np.linalg.eigvalsh(L))
    gaps = np.diff(w[: kmax + 1])
    k = int(np.argmax(gaps[kmin - 1: kmax]) + kmin)
    return k
