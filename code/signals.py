"""仅缓存由 RQAlpha 盘前 API 读取的历史截面，不读取未来收益。"""
import numpy as np
import pandas as pd
import pickle
import os
from pathlib import Path
from rqalpha.apis import all_instruments, history_bars, is_st_stock, is_suspended

WINDOWS = [10, 15, 20, 25, 30]
_cache = {}
_cache_dir = Path(__file__).resolve().parent / "cache/signals_v1"


def get_rankings(day, lookback):
    key = (day, lookback)
    if key in _cache:
        return _cache[key]
    if len(_cache) >= 100:
        _cache.clear()  # 限制内存占用；历史截面仍可从本机磁盘缓存复用。
    cache_file = _cache_dir / f"{day}.pkl"
    if cache_file.exists():
        try:
            with cache_file.open("rb") as f:
                cached = pickle.load(f)
        except (EOFError, pickle.UnpicklingError):
            cached = {}
        if lookback in cached:
            for w, values in cached.items():
                _cache[(day, w)] = values
            return _cache[key]
    windows = sorted(set(WINDOWS + [lookback]))
    rankings = {w: [] for w in windows}
    pool = all_instruments(type="CS", date=day)
    for row in pool.itertuples(index=False):
        stock = row.order_book_id
        # 仅沪深 A 股（排除 B 股、北交所）；按当日状态过滤已退市股票。
        if not (stock.startswith(("000", "001", "002", "003", "300", "301", "600", "601", "603", "605", "688", "689"))):
            continue
        listed = pd.Timestamp(row.listed_date).date()
        delisted = pd.Timestamp(row.de_listed_date).date()
        if listed > day or (day - listed).days < 180 or delisted <= day:
            continue
        if is_st_stock(stock) or is_suspended(stock):
            continue
        # 注意：此函数只能从 before_trading 调用；日线 handle_bar 会包含 T 日。
        bars = history_bars(stock, max(windows), "1d", ["datetime", "volume"],
                            skip_suspended=False, adjust_type="none")
        if len(bars) and int(bars["datetime"][-1]) // 1000000 >= int(day.strftime("%Y%m%d")):
            raise AssertionError("发现当日或未来行情，停止回测")
        for w in windows:
            volume = bars["volume"][-w:]
            if len(volume) != w or not np.isfinite(volume).all() or (volume <= 0).any():
                continue
            # 样本标准差。固定窗口下 ddof=0 与 ddof=1 的截面排序相同。
            rankings[w].append((stock, float(np.std(volume, ddof=1))))
    for w, values in rankings.items():
        _cache[(day, w)] = sorted(values, key=lambda x: (-x[1], x[0]))
    _cache_dir.mkdir(parents=True, exist_ok=True)
    temporary = cache_file.with_suffix(f".{os.getpid()}.tmp")
    with temporary.open("wb") as f:
        pickle.dump({w: _cache[(day, w)] for w in windows}, f)
    os.replace(temporary, cache_file)
    return _cache[key]
