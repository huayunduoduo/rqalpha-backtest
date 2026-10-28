"""独立核验：历史因子值、选择比例、调仓频率、净值收益和交易记录。"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import h5py
ROOT = Path(__file__).resolve().parent
checks = []
with h5py.File(ROOT / "bundle/stocks.h5", "r") as f:
    for name in ["smoke", "baseline_full", "baseline_test", "optimized_test"]:
        folder = ROOT / "results" / name
        if not (folder / "summary.json").exists():
            continue
        summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
        selections = pd.read_csv(folder / "selections.csv")
        grouped = selections.groupby("date")
        for day, rows in grouped:
            assert len(rows) == int(np.ceil(rows.eligible_count.iloc[0] * summary["top_pct"]))
            assert rows.stock.is_unique
            assert abs(rows.target_weight.sum() - .95) < 1e-10
            assert rows.factor.is_monotonic_decreasing
        weeks = pd.to_datetime(pd.Series(list(grouped.groups))).dt.isocalendar()
        assert not weeks[["year", "week"]].duplicated().any()
        # 原始 HDF5 逐条复算前、中、后 3 个调仓日各 3 支股票。
        days = sorted(grouped.groups)
        for day in [days[0], days[len(days)//2], days[-1]]:
            for row in grouped.get_group(day).iloc[:3].itertuples():
                a = f[row.stock][:]
                a = a[a["datetime"] < int(day.replace("-", ""))*1000000]
                expected = a["volume"][-int(summary["window"]):].std(ddof=1)
                assert np.isclose(row.factor, expected, rtol=1e-10)
        nav = pd.read_csv(folder / "portfolio.csv")
        assert np.isclose(nav.unit_net_value.iloc[-1]-1, summary["total_returns"], atol=2e-6)
        trades = pd.read_csv(folder / "trades.csv")
        assert len(trades) == summary["trade_count"] > 0
        checks.append({"run": name, "status": "PASS", "rebalance_dates": len(grouped),
                       "factor_samples_verified": 9, "trades": len(trades)})
(ROOT / "evidence/verification.json").write_text(json.dumps(checks, indent=2), encoding="utf-8")
print(json.dumps(checks, indent=2))
