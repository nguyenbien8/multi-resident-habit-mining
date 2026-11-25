"""Chạy toàn bộ thực nghiệm cho một nhà và ghi kết quả vào ``results/<nhà>/``.

Thứ tự: chia dữ liệu → cấu trúc nhà → RQ1 (B2, M1, M2) → RQ2 (B0, B1, B2+H,
M1+H, M2+H, Oracle+H) → ablation và độ nhạy → RQ3 (nhà có hoạt động uống
thuốc) → lỗi lan truyền (nhà 2 người).

Mọi quyết định (ngưỡng, số epoch, cấu hình GRU) chỉ dùng tập huấn luyện/kiểm
định. Tập kiểm tra chỉ dùng một lần để báo cáo.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score

from . import anomaly as A
from .baselines import sessions, track_ids, zone_habits
from .habits import habits_frame, match_habits, mine_habits, reference_habits
from .io import active_labels, describe, load_home, motion_on, resident_of, split_days
from .propagation import propagation_curve
from .recognition import (ForestRecognizer, GRURecognizer, LookupRecognizer, decode_episodes,
                          rq1_scores, smooth, tune_thresholds)
from .topology import build_topology

CONFIG = {
    "train_ratio": 0.6, "val_ratio_in_train": 0.25, "min_episodes": 5,
    "habit": {"half_window_min": 30, "freq_thr": 0.5, "min_days_daytype": 4, "method": "scan"},
    "match_max_gap_min": 60, "decode": {"smooth_k": 5, "merge_gap_min": 10, "min_events": 2},
    "rf": {"W": 20, "n_estimators": 150}, "gru": {"W": 30, "hidden": 64, "dropout": 0.2, "lr": 1e-3},
    "rq3": {"targets": {"cairo": ["R2_Take_Medicine"], "milan": ["Morning_Meds", "Eve_Meds"]},
            "frac": 0.2, "seeds": 5, "margin_min": 30},
    "propagation": {"homes": ["cairo", "tulum1", "tulum2"], "seeds": 5},
}

# Phân vùng đọc từ bản đồ chính thức của Cairo (floorplans.zip, Zenodo 15708568)
# — chỉ dùng để kiểm chứng phân vùng tự động.
CAIRO_MANUAL_ZONES = {
    **{f"M{i:03d}": "kitchen" for i in (19, 20, 21, 22, 24)},
    **{f"M{i:03d}": "living" for i in (13, 16, 17, 18, 23)},
    **{f"M{i:03d}": "hall" for i in (11, 12, 14, 15)},
    **{f"M{i:03d}": "bedroom" for i in (5, 6, 7, 8, 9)},
    **{f"M{i:03d}": "upper_left" for i in (1, 2, 3, 10)},
    "M004": "upper_right",
    **{f"M{i:03d}": "basement" for i in (25, 26, 27)},
}


def _log(msg: str, fh=None):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    if fh:
        fh.write(line + "\n"); fh.flush()


def _match_row(src: str, pred, ref, extra=None) -> dict:
    r = match_habits(pred, ref, CONFIG["match_max_gap_min"])
    pr = [h for h in pred if h.resident != "H"]; rr = [h for h in ref if h.resident != "H"]
    q = match_habits(pr, rr, CONFIG["match_max_gap_min"])
    return {"source": src, "precision": r.precision, "recall": r.recall, "f1": r.f1,
            "time_err_min": r.time_err_min, "freq_err": r.freq_err, "n_pred": r.n_pred,
            "n_ref": r.n_ref, "n_match": r.n_match,
            "res_precision": q.precision, "res_recall": q.recall, "res_f1": q.f1,
            "res_n_pred": q.n_pred, "res_n_ref": q.n_ref, "res_n_match": q.n_match, **(extra or {})}


def run_home(name: str, out_root: Path = Path("results"), models=("B2", "M1", "M2"),
             log_fh=None) -> dict:
    out = out_root / name
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    home = load_home(name)
    train, test = split_days(home.days, CONFIG["train_ratio"])
    fit_d, val_d = split_days(train, 1 - CONFIG["val_ratio_in_train"])
    mo = motion_on(home.events)
    ep = home.episodes
    acts = sorted(a for a, c in ep[ep["day"].isin(train)]["activity"].value_counts().items()
                  if c >= CONFIG["min_episodes"])

    def part(days):
        e = mo[mo["day"].isin(days)].reset_index(drop=True)
        return e, active_labels(e, ep, acts)

    ev_fit, Y_fit = part(fit_d); ev_val, Y_val = part(val_d)
    ev_tr, Y_tr = part(train); ev_te, Y_te = part(test)
    topo = build_topology(ev_tr)
    info = {**describe(home), "train_days": len(train), "test_days": len(test),
            "fit_days": len(fit_d), "val_days": len(val_d), "activities_modeled": acts,
            "n_zones": topo.n_zones, "zones": {s: z for s, z in topo.zone.items()},
            "events_train": len(ev_tr), "events_test": len(ev_te)}
    if name == "cairo":
        ss = [s for s in topo.sensors if s in CAIRO_MANUAL_ZONES]
        info["zone_ari_vs_floorplan"] = float(adjusted_rand_score(
            [CAIRO_MANUAL_ZONES[s] for s in ss], [topo.zone[s] for s in ss]))
    _log(f"{name}: {len(train)} ngày huấn luyện, {len(test)} ngày kiểm tra, "
         f"{len(acts)} hoạt động, {topo.n_zones} vùng", log_fh)

    # ---------------- RQ1 ----------------
    rq1, binaries, recognizers, thresholds = [], {}, {}, {}
    for m in models:
        t = time.time()
        if m == "B2":
            th = tune_thresholds(smooth(LookupRecognizer(topo).fit(ev_fit, Y_fit).predict_proba(ev_val)), Y_val)
            rec = LookupRecognizer(topo).fit(ev_tr, Y_tr)
        elif m == "M1":
            th = tune_thresholds(smooth(ForestRecognizer(topo, **CONFIG["rf"]).fit(ev_fit, Y_fit)
                                        .predict_proba(ev_val)), Y_val)
            rec = ForestRecognizer(topo, **CONFIG["rf"]).fit(ev_tr, Y_tr)
        elif m == "M2":
            g = GRURecognizer(topo, **CONFIG["gru"]).fit(ev_fit, Y_fit, ev_val, Y_val,
                                                         log=lambda s: _log(s, log_fh))
            th = tune_thresholds(smooth(g.predict_proba(ev_val)), Y_val)
            rec = GRURecognizer(topo, **{**CONFIG["gru"], "epochs": g.best_epoch}).fit(
                ev_tr, Y_tr, log=lambda s: _log(s, log_fh))
            info["gru_best_epoch"] = g.best_epoch
        else:
            raise ValueError(m)
        P = smooth(rec.predict_proba(ev_te))
        B = (P >= th).astype(np.uint8)
        s = rq1_scores(Y_te, B, acts)
        rq1.append({"model": m, "macro_f1": s.macro_f1, "micro_f1": s.micro_f1,
                    "seconds": round(time.time() - t, 1),
                    **{f"f1_{k}": v for k, v in s.per_activity.items()}})
        binaries[m], recognizers[m], thresholds[m] = B, rec, th
        np.savez_compressed(out / f"pred_{m}.npz", P=P.astype(np.float32), th=th)
        _log(f"  RQ1 {m}: macro-F1 {s.macro_f1:.3f}, micro-F1 {s.micro_f1:.3f} ({time.time() - t:.0f}s)", log_fh)
    pd.DataFrame(rq1).to_csv(out / "rq1.csv", index=False)

    # ---------------- RQ2 ----------------
    hcfg = dict(half_h=CONFIG["habit"]["half_window_min"] / 60, freq_thr=CONFIG["habit"]["freq_thr"],
                min_days_type=CONFIG["habit"]["min_days_daytype"])
    ep_te = ep[ep["day"].isin(test)]
    ref = reference_habits(ep, test, **hcfg)
    habit_tables = {"reference": ref}
    rows = []
    for src in ("B0", "B1"):
        tk = track_ids(ev_te, topo, n_tracks=max(2, home.n_residents)) if src == "B1" else None
        S = sessions(ev_te, topo, tk)
        hb, n_unlab = zone_habits(S, test, ep_te, source=src)
        habit_tables[src] = hb
        rows.append(_match_row(src, hb, ref, {"n_unlabeled_clusters": n_unlab, "n_sessions": len(S),
                                              "median_session_min": float(S["dur"].median())}))
    occ_by = {}
    for m, B in binaries.items():
        occ = decode_episodes(ev_te, B, acts, resident_of, CONFIG["decode"]["merge_gap_min"],
                              CONFIG["decode"]["min_events"])
        occ_by[m] = occ
        hb = mine_habits(occ, test, source=m, **hcfg)
        habit_tables[m] = hb
        rows.append(_match_row(f"{m}+H", hb, ref))
    orc = mine_habits(ep_te, test, source="oracle", **hcfg)
    habit_tables["oracle"] = orc
    rows.append(_match_row("Oracle+H", orc, ref))
    pd.DataFrame(rows).to_csv(out / "rq2.csv", index=False)
    pd.concat([habits_frame(v).assign(table=k) for k, v in habit_tables.items() if v],
              ignore_index=True).to_csv(out / "habits.csv", index=False)
    for r in rows:
        _log(f"  RQ2 {r['source']}: F1 {r['f1']:.2f} (P {r['precision']:.2f}, R {r['recall']:.2f}); "
             f"từng người F1 {r['res_f1']:.2f} ({r['res_n_match']}/{r['res_n_ref']})", log_fh)

    # ---------------- Ablation & độ nhạy ----------------
    # Mô hình cho ablation cố định là M1 (không chọn theo kết quả tập kiểm tra).
    best = "M1"
    abl = []
    for label, occ in (("Oracle", ep_te), (best, occ_by[best])):
        for meth in ("scan", "dbscan", "hdbscan"):
            abl.append(_match_row(label, mine_habits(occ, test, method=meth, **hcfg), ref,
                                  {"ablation": f"method={meth}"}))
        abl.append(_match_row(label, mine_habits(occ, test, split_daytype=False, **hcfg), ref,
                              {"ablation": "no_daytype_split"}))
    for gap in (2, 5, 10, 20, 30):
        occ = decode_episodes(ev_te, binaries[best], acts, resident_of, gap, CONFIG["decode"]["min_events"])
        abl.append(_match_row(best, mine_habits(occ, test, **hcfg), ref, {"ablation": f"merge_gap={gap}"}))
    sens = []
    for hw in (15, 30, 45):
        for fq in (0.4, 0.5, 0.6):
            kw = dict(half_h=hw / 60, freq_thr=fq, min_days_type=4)
            rf = reference_habits(ep, test, **kw)
            for m, occ in [("Oracle", ep_te)] + list(occ_by.items()):
                sens.append(_match_row(f"{m}+H", mine_habits(occ, test, **kw), rf,
                                       {"half_window_min": hw, "freq_thr": fq}))
            for src in ("B0", "B1"):
                sens.append(_match_row(src, habit_tables[src], rf, {"half_window_min": hw, "freq_thr": fq}))
    pd.DataFrame(abl).to_csv(out / "ablation.csv", index=False)
    pd.DataFrame(sens).to_csv(out / "sensitivity.csv", index=False)
    info["best_model_for_ablation"] = best

    # ---------------- RQ3 ----------------
    targets = CONFIG["rq3"]["targets"].get(name, [])
    rq3 = []
    for target in targets:
        wins = A.normal_windows(ep[ep["day"].isin(train)], train, target, CONFIG["rq3"]["margin_min"])
        if not wins:
            _log(f"  RQ3 {target}: không có thói quen chuẩn trong tập huấn luyện", log_fh)
            continue
        tgt_ev = ev_tr[Y_tr[:, acts.index(target)] == 1] if target in acts else ev_tr.iloc[:0]
        top = tgt_ev["sensor"].value_counts()
        zone_id = topo.zone[top.index[0]] if len(top) else -1
        zone_sensors = {s for s, z in topo.zone.items() if z == zone_id}
        orig = A.day_truth(ep_te, test, target, wins)
        eval_days = [d for d, missed in orig.items() if not missed]
        n_ambiguous = sum(orig.values())
        for seed in range(CONFIG["rq3"]["seeds"]):
            rng = np.random.default_rng(seed)
            ev_inj, ep_inj, chosen = A.inject(ev_te, ep, eval_days, target, CONFIG["rq3"]["frac"], rng)
            truth = {d: d in chosen for d in eval_days}
            n_days = len(truth)
            res = {"B0-zone": A.zone_presence_detect(ev_inj, test, zone_sensors, wins)}
            for m, rec in recognizers.items():
                if target not in acts:
                    continue
                B = (smooth(rec.predict_proba(ev_inj)) >= thresholds[m]).astype(np.uint8)
                occ = decode_episodes(ev_inj, B, acts, resident_of, CONFIG["decode"]["merge_gap_min"],
                                      CONFIG["decode"]["min_events"])
                res[m] = A.detect(occ, test, target, wins)
            for det, alarm in res.items():
                rq3.append({"target": target, "seed": seed, "detector": det, "n_injected": len(chosen),
                            "n_eval_days_total": len(eval_days), "n_ambiguous_days": int(n_ambiguous),
                            "alarm_delay_min": A.alarm_delay_min(wins),
                            "windows": "; ".join(f"{w.habit.day_type}:{w.lo:.2f}-{w.hi:.2f}" for w in wins),
                            **A.score(truth, alarm, n_days)})
        _log(f"  RQ3 {target}: xong {CONFIG['rq3']['seeds']} lần cài", log_fh)
    if rq3:
        pd.DataFrame(rq3).to_csv(out / "rq3.csv", index=False)

    # ---------------- Lỗi lan truyền ----------------
    if name in CONFIG["propagation"]["homes"]:
        seeds = range(CONFIG["propagation"]["seeds"])
        curves = [propagation_curve(ep, test, "drop", [0, .1, .2, .3, .4, .5], seeds),
                  propagation_curve(ep, test, "jitter", [0, 5, 10, 20, 30, 45], seeds),
                  propagation_curve(ep, test, "spurious", [0, .1, .25, .5, 1.0, 2.0], seeds),
                  propagation_curve(ep, test, "swap", [0, .1, .2, .3, .4, .5], seeds,
                                    per_resident_only=True)]
        pd.concat(curves, ignore_index=True).to_csv(out / "propagation.csv", index=False)
        _log("  Lỗi lan truyền: xong", log_fh)

    info["seconds_total"] = round(time.time() - t0, 1)
    (out / "info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (out_root / "config.json").write_text(json.dumps(CONFIG, ensure_ascii=False, indent=2), encoding="utf-8")
    _log(f"{name}: xong sau {info['seconds_total']:.0f}s", log_fh)
    return info


# Đánh giá theo nhiều mốc thời gian (rolling-origin): huấn luyện trên mọi ngày
# trước mốc, kiểm tra trên 20% số ngày kế tiếp. Ba tập kiểm tra không chồng nhau.
FOLDS = ((0.4, 0.6), (0.6, 0.8), (0.8, 1.0))


def run_rolling(name: str, out_root: Path = Path("results"), models=("B2", "M1", "M2"),
                log_fh=None) -> pd.DataFrame:
    """RQ2 trên ba lần chia theo thời gian; ghi ``results/<nhà>/rolling.csv``."""
    out = out_root / name
    out.mkdir(parents=True, exist_ok=True)
    home = load_home(name)
    mo = motion_on(home.events)
    ep = home.episodes
    days = list(home.days)
    hcfg = dict(half_h=CONFIG["habit"]["half_window_min"] / 60, freq_thr=CONFIG["habit"]["freq_thr"],
                min_days_type=CONFIG["habit"]["min_days_daytype"])
    rows = []
    for k, (a, b) in enumerate(FOLDS):
        n_a, n_b = int(round(len(days) * a)), int(round(len(days) * b))
        train, test = days[:n_a], days[n_a:n_b]
        fit_d, val_d = split_days(train, 1 - CONFIG["val_ratio_in_train"])
        acts = sorted(x for x, c in ep[ep["day"].isin(train)]["activity"].value_counts().items()
                      if c >= CONFIG["min_episodes"])

        def part(ds):
            e = mo[mo["day"].isin(ds)].reset_index(drop=True)
            return e, active_labels(e, ep, acts)

        ev_fit, Y_fit = part(fit_d); ev_val, Y_val = part(val_d)
        ev_tr, Y_tr = part(train); ev_te, Y_te = part(test)
        topo = build_topology(ev_tr)
        ep_te = ep[ep["day"].isin(test)]
        ref = reference_habits(ep, test, **hcfg)
        extra = {"fold": k, "train_days": len(train), "test_days": len(test)}
        for src in ("B0", "B1"):
            tk = track_ids(ev_te, topo, n_tracks=max(2, home.n_residents)) if src == "B1" else None
            hb, _ = zone_habits(sessions(ev_te, topo, tk), test, ep_te, source=src)
            rows.append(_match_row(src, hb, ref, extra))
        for m in models:
            if m == "B2":
                th = tune_thresholds(smooth(LookupRecognizer(topo).fit(ev_fit, Y_fit).predict_proba(ev_val)), Y_val)
                rec = LookupRecognizer(topo).fit(ev_tr, Y_tr)
            elif m == "M1":
                th = tune_thresholds(smooth(ForestRecognizer(topo, **CONFIG["rf"]).fit(ev_fit, Y_fit)
                                            .predict_proba(ev_val)), Y_val)
                rec = ForestRecognizer(topo, **CONFIG["rf"]).fit(ev_tr, Y_tr)
            elif m == "M2":
                g = GRURecognizer(topo, **CONFIG["gru"]).fit(ev_fit, Y_fit, ev_val, Y_val, log=lambda s: None)
                th = tune_thresholds(smooth(g.predict_proba(ev_val)), Y_val)
                rec = GRURecognizer(topo, **{**CONFIG["gru"], "epochs": g.best_epoch}).fit(
                    ev_tr, Y_tr, log=lambda s: None)
            else:
                raise ValueError(m)
            B = (smooth(rec.predict_proba(ev_te)) >= th).astype(np.uint8)
            occ = decode_episodes(ev_te, B, acts, resident_of, CONFIG["decode"]["merge_gap_min"],
                                  CONFIG["decode"]["min_events"])
            rows.append(_match_row(f"{m}+H", mine_habits(occ, test, source=m, **hcfg), ref, extra))
        _log(f"{name} lần chia {k}: {len(train)}/{len(test)} ngày, {len(ref)} thói quen đáp án; " +
             ", ".join(f"{r['source']} {r['f1']:.2f}" for r in rows if r["fold"] == k), log_fh)
    df = pd.DataFrame(rows)
    df.to_csv(out / "rolling.csv", index=False)
    return df
