"""第 1 题：运行仓库自带的买入持有示例。"""
import sys
import os
import json
import platform
import importlib.metadata as metadata
from pathlib import Path
from run_experiment import ROOT, config
from rqalpha import run_file

print("RQALPHA OFFICIAL EXAMPLE / ACTUAL EXECUTION", flush=True)
print("Python:", sys.version, flush=True)
print("Conda environment:", sys.executable, flush=True)
print("Conda manager:", os.environ.get("CONDA_EXE", "direct environment interpreter"), flush=True)
print("RQAlpha:", metadata.version("rqalpha"), flush=True)
print("OS:", platform.platform(), flush=True)
print("Example: rqalpha/rqalpha/examples/buy_and_hold.py", flush=True)
print("Period: 2024-01-02 -> 2024-12-31", flush=True)
print("Capital: CNY 10,000,000 | benchmark: CSI 300", flush=True)
cfg = config("2024-01-02", "2024-12-31", ROOT / "results/example")
cfg["mod"]["sys_simulation"]["slippage"] = 0
result = run_file(str(ROOT / "rqalpha/rqalpha/examples/buy_and_hold.py"), cfg)["sys_analyser"]
summary = result["summary"]
assert len(result["trades"]) > 0, "示例未实际成交"
print("\nBACKTEST COMPLETED SUCCESSFULLY", flush=True)
for key in ["total_returns", "annualized_returns", "sharpe", "max_drawdown"]:
    print(f"{key:22s}: {summary[key]:.6f}", flush=True)
print("Actual trade records:", len(result["trades"]), flush=True)
print(result["trades"][["order_book_id", "side", "last_quantity", "last_price"]].to_string(index=False), flush=True)
print("\nFull results: results/example/", flush=True)
