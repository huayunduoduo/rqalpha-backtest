"""RQAlpha 真实回测、二维参数网格与邻域稳健选择。"""
import os
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "rqalpha"))
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "cache/matplotlib"))
os.environ.setdefault("MPLBACKEND", "Agg")
import json
import time
import argparse
import warnings
import numpy as np
import pandas as pd
from rqalpha import run_file
warnings.filterwarnings("ignore", category=FutureWarning, module=r"rqalpha\..*")

WINDOWS = [10, 15, 20, 25, 30]
PCTS = [0.05, 0.075, 0.10, 0.125, 0.15]


def config(start, end, out, window=20, pct=.1, audit=True):
    return {"base": {"start_date": start, "end_date": end, "frequency": "1d",
                     "accounts": {"stock": 10000000}, "data_bundle_path": str(ROOT / "bundle"), "capital_gain_tax_rate": 0},
            "extra": {"log_level": "error", "context_vars": {
                "lookback": window, "top_pct": pct, "out_dir": str(out), "save_audit": audit}},
            "mod": {"sys_analyser": {"enabled": True, "benchmark": "000300.XSHG", "plot": False},
                    "sys_progress": {"enabled": False},
                    "sys_simulation": {"matching_type": "current_bar", "slippage": .001,
                                       "price_limit": True, "volume_limit": True, "volume_percent": .1},
                    "sys_transaction_cost": {"stock_commission_multiplier": .375,
                                             "stock_min_commission": 5, "pit_tax": True}}}


def one(name, start, end, window=20, pct=.1, example=False, audit=True):
    out = ROOT / "results" / name
    out.mkdir(parents=True, exist_ok=True)
    cached = out / "summary.json"
    if cached.exists():
        return json.loads(cached.read_text(encoding="utf-8"))
    cfg = config(start, end, out, window, pct, audit)
    if example:
        # 官方示例 100% 下单，使用框架默认的零滑点，以免额外滑点造成资金不足。
        cfg["mod"]["sys_simulation"]["slippage"] = 0
        cfg["extra"]["log_level"] = "info"
    (out / "config.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    strategy = ROOT / "rqalpha/rqalpha/examples/buy_and_hold.py" if example else ROOT / "strategy.py"
    t0 = time.time()
    result = run_file(str(strategy), cfg)["sys_analyser"]
    if not isinstance(result, dict) or "summary" not in result:
        raise RuntimeError("回测没有返回有效结果")
    for key in ["portfolio", "benchmark_portfolio", "trades"]:
        result[key].to_csv(out / f"{key}.csv")
    if example:
        pd.to_pickle(result, out / "result.pkl")
    s = result["summary"]
    summary = {k: (v.item() if isinstance(v, np.generic) else v) for k, v in s.items()}
    summary.update(window=window, top_pct=pct, elapsed_seconds=round(time.time()-t0, 2),
                   trade_count=len(result["trades"]), name=name)
    cached.write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"DONE {name}: return={s['total_returns']:.4%}; sharpe={s['sharpe']:.3f}; "
          f"drawdown={s['max_drawdown']:.4%}; trades={len(result['trades'])}; {time.time()-t0:.1f}s", flush=True)
    return summary


def main(mode):
    if mode == "example":
        one("example", "2024-01-02", "2024-12-31", example=True)
        return
    if mode == "smoke":
        one("smoke", "2023-01-03", "2023-02-28")
        return
    if mode == "baseline":
        one("baseline_full", "2021-01-04", "2025-12-31")
        return
    records = []
    for w in WINDOWS:
        for p in PCTS:
            records.append(one(f"grid_w{w}_p{p:.3f}", "2021-01-04", "2023-12-29", w, p, audit=False))
            pd.DataFrame(records).to_csv(ROOT / "results/grid.csv", index=False)
    df = pd.DataFrame(records)
    score = df.pivot(index="window", columns="top_pct", values="sharpe").reindex(index=WINDOWS, columns=PCTS)
    candidates = []
    # 只选有完整 3×3 邻域的内部点；奖励均值，惩罚尖峰/不稳定性。
    for i in range(1, len(WINDOWS)-1):
        for j in range(1, len(PCTS)-1):
            neighbors = score.iloc[i-1:i+2, j-1:j+2].to_numpy()
            if not np.isfinite(neighbors).all():
                continue
            candidates.append({"window": WINDOWS[i], "top_pct": PCTS[j],
                               "neighbor_mean": float(neighbors.mean()),
                               "neighbor_std": float(neighbors.std()),
                               "robust_score": float(neighbors.mean()-neighbors.std()),
                               "neighbor_positive_fraction": float((neighbors>0).mean())})
    ranking = pd.DataFrame(candidates).sort_values(["robust_score", "window", "top_pct"], ascending=[False, True, True])
    ranking.to_csv(ROOT / "results/plateau_scores.csv", index=False)
    choice = ranking.iloc[0].to_dict()
    choice["window"] = int(choice["window"])
    (ROOT / "results/chosen.json").write_text(json.dumps(choice, indent=2), encoding="utf-8")
    print("FROZEN TRAINING-ONLY CHOICE: " + json.dumps(choice), flush=True)
    # 两段均不参与调参；测试区间独立从现金开始，不携带训练持仓。
    for split, start, end in [("validation", "2024-01-02", "2024-12-31"), ("test", "2025-01-02", "2025-12-31")]:
        one(f"baseline_{split}", start, end)
        one(f"optimized_{split}", start, end, choice["window"], choice["top_pct"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["example", "smoke", "baseline", "grid"])
    main(parser.parse_args().mode)
