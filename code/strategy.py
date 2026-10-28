"""成交量标准差因子：盘前使用 T-1 数据，周首交易日收盘调仓。"""
import math
from pathlib import Path
import pandas as pd
from rqalpha.apis import *
from signals import get_rankings


def init(context):
    context.lookback = getattr(context, "lookback", 20)
    context.top_pct = getattr(context, "top_pct", 0.10)
    context.invested = 0.95
    context.last_week = None
    context.targets = None
    context.audit = []
    context.audit_dirty = False
    context.out_dir = getattr(context, "out_dir", "results/manual")


def before_trading(context):
    # 用 ISO 周标识，春节/国庆后的首个交易日也能正常调仓。
    week = context.now.date().isocalendar()[:2]
    context.targets = None
    if week == context.last_week:
        return
    context.last_week = week
    ranked = get_rankings(context.now.date(), context.lookback)
    n = len(ranked)
    k = max(1, math.ceil(n * context.top_pct)) if n else 0
    selected = ranked[:k]
    context.targets = {stock: context.invested / k for stock, _ in selected}
    context.audit_dirty = True
    # 排名、因子值和目标权重用于核对，不将目标组合冒充实际成交。
    for rank, (stock, factor) in enumerate(selected, 1):
        context.audit.append({"date": str(context.now.date()), "stock": stock,
                              "rank": rank, "factor": factor, "eligible_count": n,
                              "selected_count": k, "target_weight": context.invested/k})


def handle_bar(context, bar_dict):
    if context.targets is not None:
        # 框架负责先卖后买、整手交易、费用、涨跌停、停牌、T+1 和成交量约束。
        order_target_portfolio(context.targets)
        context.targets = None


def after_trading(context):
    # 每次调仓后保存；中途停止仍可查看已完成的选股记录。
    if context.audit_dirty and getattr(context, "save_audit", True):
        out = Path(context.out_dir)
        out.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(context.audit).to_csv(out / "selections.csv", index=False)
        context.audit_dirty = False
