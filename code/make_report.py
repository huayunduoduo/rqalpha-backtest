"""生成中文答案、实际回测图和可独立打开的 HTML 报告。"""
import os
from pathlib import Path
ROOT = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "cache/matplotlib"))
import json
import base64
import html
import shutil
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

OUT = ROOT / "submission"
FIG = OUT / "figures"
FIG.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
                     "axes.unicode_minus": False, "figure.dpi": 140,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": .18, "font.size": 10})


def summary(name):
    return json.loads((ROOT / "results" / name / "summary.json").read_text(encoding="utf-8"))


def portfolio(name):
    return pd.read_csv(ROOT / "results" / name / "portfolio.csv", index_col=0, parse_dates=True)


def save(fig, name):
    fig.savefig(FIG / name, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def metrics_table(rows):
    data = []
    for label, s in rows:
        data.append([label, f'{s["total_returns"]:.2%}', f'{s["annualized_returns"]:.2%}',
                     f'{s["sharpe"]:.3f}', f'{s["max_drawdown"]:.2%}', str(s['trade_count'])])
    return pd.DataFrame(data, columns=["策略 / 区间", "累计收益", "年化收益", "夏普比率", "最大回撤", "成交笔数"]).to_html(index=False, border=0)


def main():
    env = json.loads((ROOT / "evidence/environment.json").read_text(encoding="utf-8"))
    chosen = json.loads((ROOT / "results/chosen.json").read_text(encoding="utf-8"))
    w, p = chosen["window"], chosen["top_pct"]
    grid = pd.read_csv(ROOT / "results/grid.csv")
    base, opt = summary("baseline_test"), summary("optimized_test")
    full = summary("baseline_full")
    example = summary("example")
    nv = portfolio("baseline_full")
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True, gridspec_kw={"height_ratios": [2, 1]})
    axes[0].plot(nv.index, nv.unit_net_value, color="#137f84", label="20 日 / 前 10%")
    axes[0].plot(nv.index, nv.benchmark_unit_net_value, color="#a4a7ac", label="沪深 300")
    axes[0].set(title="20 日成交量标准差策略｜2021—2025 年", ylabel="累计净值（初始 1）")
    axes[0].legend(loc="upper left")
    drawdown = nv.unit_net_value / np.maximum(nv.unit_net_value.cummax(), 1) - 1
    axes[1].fill_between(nv.index, drawdown, 0, color="#ce7274", alpha=.8)
    axes[1].set_ylabel("策略回撤")
    axes[1].yaxis.set_major_formatter(PercentFormatter(1))
    for ax in axes:
        for date in ["2024-01-01", "2025-01-01"]:
            ax.axvline(pd.Timestamp(date), color="#5e6470", linestyle="--", linewidth=.9)
    fig.tight_layout()
    save(fig, "01_baseline.png")

    windows = sorted(grid.window.unique())
    pcts = sorted(grid.top_pct.unique())
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    for ax, field, title, fmt, cmap in zip(axes.flat,
            ["sharpe", "annualized_returns", "max_drawdown", "annualized_twoside_turnover"],
            ["训练期夏普比率", "训练期年化收益", "训练期最大回撤", "训练期年化双边换手倍数"],
            [".2f", ".1%", ".1%", ".1f"], ["YlGnBu", "YlGnBu", "YlOrRd", "PuBu"]):
        z = grid.pivot(index="window", columns="top_pct", values=field).reindex(index=windows, columns=pcts).to_numpy()
        im = ax.imshow(z, cmap=cmap, aspect="auto")
        for i in range(len(windows)):
            for j in range(len(pcts)):
                ax.text(j, i, format(z[i,j], fmt), ha="center", va="center", fontsize=9,
                        color="white" if (z[i,j]-np.nanmin(z))/(np.nanmax(z)-np.nanmin(z)+1e-12)>.65 else "#172533")
        from matplotlib.patches import Rectangle
        ax.add_patch(Rectangle((pcts.index(p)-.5, windows.index(w)-.5), 1, 1,
                               fill=False, edgecolor="#ef7839", linewidth=3))
        ax.set(xticks=range(len(pcts)), xticklabels=[f"{x:.1%}" for x in pcts],
               yticks=range(len(windows)), yticklabels=windows,
               xlabel="选股比例", ylabel="成交量窗口 / 交易日", title=title)
        ax.grid(False)
        fig.colorbar(im, ax=ax, shrink=.8)
    fig.suptitle("参数平原检验｜2021—2023 年｜橙框为训练期邻域稳健选择", fontsize=14)
    fig.tight_layout()
    save(fig, "02_parameter_heatmaps.png")

    z = grid.pivot(index="window", columns="top_pct", values="sharpe").reindex(index=windows, columns=pcts).to_numpy()
    x, y = np.meshgrid(np.array(pcts)*100, windows)
    fig = plt.figure(figsize=(10, 6))
    ax = fig.add_subplot(111, projection="3d")
    ax.plot_surface(x, y, z, cmap="viridis", edgecolor="white", linewidth=.4, alpha=.9)
    ax.set(xlabel="选股比例 / %", ylabel="窗口 / 日", zlabel="夏普比率",
           title="参数曲面：观察连续区域，而非单点峰值")
    ax.set_xticks(np.array(pcts)*100)
    ax.set_yticks(windows)
    ax.zaxis.set_rotate_label(False)
    ax.set_zlabel("夏普比率", labelpad=20, rotation=90)
    ax.view_init(27, -125)
    save(fig, "03_parameter_surface.png")

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    for ax, split, title in zip(axes, ["validation", "test"], ["2024 年验证期", "2025 年独立测试期"]):
        b, o = portfolio("baseline_"+split), portfolio("optimized_"+split)
        ax.plot(b.index, b.unit_net_value, label="基准参数 20 日 / 10%", color="#4576ba")
        ax.plot(o.index, o.unit_net_value, label=f"稳健参数 {w} 日 / {p:.1%}", color="#137f84")
        ax.plot(b.index, b.benchmark_unit_net_value, label="沪深 300", color="#a4a7ac", linestyle="--")
        ax.set(title=title+"（独立从现金开始）", ylabel="累计净值")
        ax.legend(fontsize=8)
        ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    save(fig, "04_out_of_sample.png")

    monthly = nv.unit_net_value.resample("ME").last().pct_change()
    monthly.iloc[0] = nv.unit_net_value.resample("ME").last().iloc[0]-1
    m = pd.DataFrame({"year": monthly.index.year, "month": monthly.index.month, "return": monthly.values}).pivot(index="year",columns="month",values="return")
    fig, ax = plt.subplots(figsize=(11,4))
    limit = np.nanmax(abs(m.to_numpy()))
    im = ax.imshow(m, cmap="RdYlGn", vmin=-limit, vmax=limit, aspect="auto")
    for i in range(len(m)):
        for j in range(12):
            ax.text(j,i,f"{m.iloc[i,j]:.1%}",ha="center",va="center",fontsize=9)
    ax.set(xticks=range(12),xticklabels=range(1,13),yticks=range(len(m)),yticklabels=m.index,
           title="基准策略月度收益",xlabel="月份")
    ax.grid(False)
    fig.colorbar(im,ax=ax,format=PercentFormatter(1))
    save(fig,"05_monthly_returns.png")

    for sub in ["code", "evidence", "results"]:
        (OUT/sub).mkdir(exist_ok=True)
    for name in ["strategy.py", "signals.py", "run_experiment.py", "demo.py", "verify.py", "make_report.py", "lock_env.py", "run.ps1", "requirements-lock.txt", "README.md", "environment.yml"]:
        if (ROOT/name).exists(): shutil.copy2(ROOT/name, OUT/"code"/name)
    for file in (ROOT/"evidence").glob("*"):
        if file.is_file(): shutil.copy2(file, OUT/"evidence"/file.name)
    for name in ["grid.csv", "plateau_scores.csv", "chosen.json"]:
        shutil.copy2(ROOT/"results"/name, OUT/"results"/name)
    for name in ["baseline_full", "baseline_validation", "optimized_validation", "baseline_test", "optimized_test", "example"]:
        shutil.copytree(ROOT/"results"/name, OUT/"results"/name, dirs_exist_ok=True)

    def picture(name, caption, directory="figures"):
        f = OUT/directory/name
        src = base64.b64encode(f.read_bytes()).decode()
        return f'<figure><img src="data:image/png;base64,{src}" alt="{html.escape(caption)}"><figcaption>{caption}</figcaption></figure>'
    def code(name):
        return '<pre><code>'+html.escape((ROOT/name).read_text(encoding="utf-8"))+'</code></pre>'
    test_change = opt["total_returns"] - base["total_returns"]
    best = grid.sort_values("sharpe",ascending=False).iloc[0]
    conclusion = ("独立测试期累计收益提高" if test_change>=0 else "独立测试期累计收益降低")+f" {abs(test_change)*100:.2f} 个百分点。"
    plateau = ("所选邻域的夏普多数为正，但仍需结合样本外表现，不能据此声称长期有效。" if chosen["neighbor_positive_fraction"]>.5
               else "所选邻域正夏普比例不高，不能将它解释为已找到稳定盈利的参数平原。")
    audit = pd.read_csv(ROOT/"results/baseline_full/selections.csv")
    first = audit[audit.date==audit.date.min()].head(10)[["stock","rank","factor","target_weight"]]
    proof = json.loads((ROOT/"evidence/verification.json").read_text())
    body = f'''
<header><div class="kicker">QUANTITATIVE RESEARCH · RQALPHA</div><h1>成交量标准差因子<br>周度选股与参数平原</h1><p>量化笔试题二 · 代码、真实回测、运行证据</p><div class="tags">RQAlpha {env['rqalpha']} / Anaconda Python 3.11 / 沪深 A 股 / 2021—2025</div></header>
<main><section><h2>答题完成情况</h2><p>已克隆官方仓库，在 D 盘安装完整 Anaconda Distribution 2024.02-1，配置独立 conda 环境，实际运行官方示例；实现 20 日成交量标准差、每周排名前 10% 等权选股；完成 25 组参数回测、邻域稳健参数选择及独立样本外测试。<strong>完整发行版位于 D:\\rqalpha_exam\\anaconda3，conda 版本为 24.1.2。</strong>官方示例已通过该 Anaconda 管理器重新执行，保留原始运行日志。</p>
<p>所有图表来自本机 RQAlpha 执行结果。IDE 图片为真实截图，运行结果图片展示执行后原始日志在 VS Code 中的内容。</p></section>
<section><h2>1. 克隆、环境配置及官方示例</h2><p>仓库：<a href="https://github.com/ricequant/rqalpha">ricequant/rqalpha</a>。固定提交：<code>{env['commit']}</code>。解释器：<code>{env['executable']}</code>。numpy {env['numpy']}，pandas {env['pandas']}。环境、依赖和缓存均位于 D 盘。</p>
<pre>git clone https://github.com/ricequant/rqalpha.git D:\\rqalpha_exam\\rqalpha
conda create -p D:\\rqalpha_exam\\envs\\rqalpha python=3.11 -y
conda activate D:\\rqalpha_exam\\envs\\rqalpha
python -m pip install -e D:\\rqalpha_exam\\rqalpha
.\\run.ps1 demo.py</pre>
<p>实际安装时克隆连接使用本机已有代理；独立 conda 环境先由 Miniconda Python 3.11 基础环境克隆建立，再用完整 Anaconda 的 conda 管理同一环境。pip 依赖通过清华镜像下载。源码以 editable 方式安装，<code>pip check</code> 通过。Anaconda 安装包来自官方归档，数字签名验证为 Anaconda, Inc.，安装、下载和缓存均在 D 盘。</p>
<p>示例为仓库原生 <code>buy_and_hold.py</code>，首次买入平安银行并持有。为了保持原示例 100% 资金下单方式，示例使用零滑点；第 2、3 题统一使用 0.1% 单边滑点。示例结果：</p>
{metrics_table([('官方示例 / 2024',example)])}
{picture('01_ide_code.png','图 1：实际 VS Code 项目与官方示例运行入口。','evidence')}
{picture('02_example_run.png','图 2：实际执行日志，含 Anaconda Python 路径、版本、收益及成交记录。','evidence')}
<details><summary>展示第 1 题示例运行代码 demo.py</summary>{code('demo.py')}</details></section>
<section><h2>2. 成交量标准差因子与周度调仓</h2><p>题目未指定排序方向、股票池、标准差自由度和回测年份。本文明确采用以下口径：</p>
<table><tr><th>项目</th><th>设定</th></tr><tr><td>因子</td><td>前 20 个市场交易日原始成交量的样本标准差（ddof=1）；不归一化、不复权</td></tr><tr><td>股票池</td><td>当日已上市的沪深 A 股，含科创板及创业板；上市满 180 个自然日，剔除 ST、当前停牌、窗口内零成交/缺失数据；排除 B 股和北交所</td></tr><tr><td>排名</td><td>因子从大到小，选 ceil(N×10%)；因子相同时按股票代码排序</td></tr><tr><td>调仓</td><td>每个 ISO 周的首个交易日，盘前计算至 T−1 的因子，日线模式当日收盘撮合</td></tr><tr><td>资金与持仓</td><td>初始 1,000 万元，选中股票等权，总目标仓位 95%，预留 5% 现金</td></tr><tr><td>摩擦与约束</td><td>双边佣金万三、每笔最低 5 元；历史印花税；单边滑点 0.1%；单日成交量上限 10%；框架原生整手、T+1、停牌及涨跌停约束</td></tr><tr><td>基准与期间</td><td>沪深 300；基准策略完整回测 2021-01-04 至 2025-12-31</td></tr></table>
<div class="formula">V̄ᵢ,t = (1/L) Σ Vᵢ,t−j；　STDᵢ,t = √[ Σ(Vᵢ,t−j − V̄ᵢ,t)² / (L−1) ]，j = 1…L。</div>
<p>固定 L 时，ddof=0 与 ddof=1 只相差相同缩放常数，不改变横截面排名。原始成交量标准差同时反映成交规模与波动，容易偏向高成交量股票，不等于纯粹的成交活跃度变化；标准化成交量或换手率因子属于后续扩展，不用于替代本题指定因子。</p>
<p>避免未来函数：只在 <code>before_trading</code> 调用 <code>history_bars</code>，并断言最大行情时间小于调仓日。不能仅在日线 <code>handle_bar</code> 中设置 <code>include_now=False</code> 就认为已排除当日行情。每周首交易日由 ISO 周判断，避免固定周一导致节假日漏调仓。</p>
<p>历史股票池按当日上市/退市状态筛选，不使用当前指数成分股回填历史。因子截面缓存只保存历史因子排名，不读取后续收益；更换数据包或因子逻辑后应清空 <code>cache/signals_v1</code>，并删除对应旧回测输出再运行。</p>
{metrics_table([('20 日 / 10% / 2021—2025',full)])}
{picture('01_baseline.png','图 3：完整基准回测净值与回撤；虚线分别为验证和测试年份边界。')}
{picture('05_monthly_returns.png','图 4：基准策略月度收益，含交易成本。')}
<h3>首个调仓日的前 10 名选股</h3>{first.to_html(index=False,border=0,float_format=lambda v:f'{v:,.6f}')}
<p>目标选股记录与实际成交记录分别存放。涨跌停、资金及交易规则可能使实际权重偏离目标；未成交不会被假定为已成交，等待下次调仓再调整。交易按框架日线收盘成交模型处理，不等价于真实逐笔实盘。</p>
<h3>策略代码 strategy.py</h3>{code('strategy.py')}<h3>因子与排序 signals.py</h3>{code('signals.py')}</section>
<section><h2>3. 参数平原与稳健优化</h2><p>因子窗口 L∈{{10,15,20,25,30}}，选股比例 q∈{{5%,7.5%,10%,12.5%,15%}}，共 25 组；周度调仓、资金和成本保持一致。2021—2023 为训练期；2024 为验证期；2025 为独立测试期。每一格都在 RQAlpha 中真实回测，不以简化向量化收益替代成交。</p>
<p>对网格内部 9 个候选中心，取完整 3×3 邻域，计算 <strong>稳健得分 = 邻域夏普均值 − 邻域夏普标准差</strong>。按该分数选中心点，避免追逐单点尖峰。仅用训练期选择，参数写入 <code>chosen.json</code> 后冻结；验证和测试结果不回流调参。无有限指标的邻域不参与选择。</p>
{picture('02_parameter_heatmaps.png','图 5：收益、风险、夏普及换手的二维参数平原。')}
{picture('03_parameter_surface.png','图 6：训练期夏普曲面；仅连接已计算的 25 个网格点，不代表未测参数的真实回测。')}
<p>训练期单点最高夏普：窗口 {int(best.window)} 日、选股 {best.top_pct:.1%}、夏普 {best.sharpe:.3f}。邻域规则最终选择：<strong>{w} 日 / 前 {p:.1%}</strong>；邻域均值 {chosen['neighbor_mean']:.3f}，邻域标准差 {chosen['neighbor_std']:.3f}，稳健得分 {chosen['robust_score']:.3f}，邻域正夏普比例 {chosen['neighbor_positive_fraction']:.1%}。{plateau}</p>
{metrics_table([('原参数 / 2024 验证',summary('baseline_validation')),('稳健参数 / 2024 验证',summary('optimized_validation')),('原参数 / 2025 测试',base),('稳健参数 / 2025 测试',opt)])}
{picture('04_out_of_sample.png','图 7：固定参数后的样本外对比；两个区间均独立从现金开始。')}
<p><strong>结果解释：</strong>{conclusion}测试期夏普由 {base['sharpe']:.3f} 变为 {opt['sharpe']:.3f}，最大回撤由 {base['max_drawdown']:.2%} 变为 {opt['max_drawdown']:.2%}。参数优化是训练期规则选择，不保证样本外各项指标全部改善；单个测试年度也不足以证明长期有效。</p>
<details><summary>展示完整回测和参数选择代码 run_experiment.py</summary>{code('run_experiment.py')}</details></section>
<section><h2>复现、核验与数据边界</h2><p>行情来源为 RQAlpha 官方 202608 数据包；研究仅使用截至 2025 年的历史交易数据。数据包包含分红、复权、停牌、ST、退市信息，权益处理由框架完成；供应商后续修订和数据覆盖边界仍可能影响历史结果，不宣称完全消除所有数据偏差。沪深 300 基准与全 A 股策略股票池不同，超额收益含风格差异。</p>
<p>收益、年化收益、夏普和最大回撤均取 RQAlpha 原生分析器。夏普使用框架的利率数据及年化口径，因此不手工用零无风险利率替换。年化收益与单个自然年度累计收益可能略有差异。图表回撤包含初始净值 1，净值 CSV 保存到 6 位小数，汇总指标保持框架精度。</p>
<p>独立核验：{len(proof)} 个结果通过。复算前、中、后调仓日的因子值；核对每周最多一次调仓、前 q 比例、无重复股票、权重和、成交笔数及期末净值与汇总收益一致。证据见 <code>evidence/verification.json</code>。</p>
<pre>.\\run.ps1 demo.py
.\\run.ps1 run_experiment.py smoke
.\\run.ps1 run_experiment.py grid
.\\run.ps1 run_experiment.py baseline
.\\run.ps1 verify.py
.\\run.ps1 make_report.py</pre>
<p>完整工作目录：<code>D:\\rqalpha_exam</code>。提交包含代码、锁定依赖、配置、真实截图、图表、完整基准与样本外成交/净值/选股文件及 25 组训练网格指标。环境、源码仓库和约 3.4 GB 的解压行情保留在工作目录，不塞入提交包。</p>
<h3>参考与可追溯记录</h3><ul><li><a href="https://github.com/ricequant/rqalpha">RQAlpha 官方仓库及许可证</a></li><li><a href="https://rqalpha.readthedocs.io/zh_CN/latest/api/base_api.html">RQAlpha API 文档</a></li><li><a href="https://repo.anaconda.com/archive/Anaconda3-2024.02-1-Windows-x86_64.exe">Anaconda 官方完整发行版安装包</a></li><li><a href="{env['bundle_url']}">本次官方行情数据包</a></li></ul><p class="small">本答案为量化研究与题目复现，不将历史回测结果视作未来收益承诺。报告生成于本机实际执行结束后。</p></section></main>'''
    css = '''body{margin:0;background:#eef2f4;color:#243140;font:16px/1.8 "Microsoft YaHei",sans-serif}header{background:#102b3b;color:white;padding:55px max(6vw,24px)}header h1{font-size:42px;line-height:1.35;margin:16px 0}.kicker{font:13px monospace;letter-spacing:3px;color:#7cd2cd}.tags{color:#bdd5df;font-size:14px}main{max-width:1080px;margin:26px auto;padding:0 22px}section{background:white;padding:30px 40px;margin-bottom:24px;border-radius:10px}h2{font-size:25px;color:#155866;border-bottom:2px solid #e6eeee;padding-bottom:12px}h3{font-size:19px}p{margin:16px 0}table{border-collapse:collapse;width:100%;font-size:13px;margin:20px 0}th{background:#e8f2f3;text-align:left}th,td{padding:10px;border-bottom:1px solid #dce5e8}pre{background:#152a39;color:#dbe8ee;padding:22px;overflow:auto;font:13px/1.65 Consolas,"Microsoft YaHei",monospace;white-space:pre-wrap;word-break:break-word;border-radius:7px}code{font-family:Consolas,monospace}figure{margin:28px 0}img{max-width:100%;display:block;margin:auto;border:1px solid #e4e9ec}figcaption{font-size:13px;color:#657480;margin-top:9px}.formula{padding:20px;background:#edf7f7;font-size:18px}.small{font-size:13px;color:#73808a}summary{cursor:pointer;font-weight:bold;color:#12656c}a{color:#0b7180}@media print{body{background:white}header{padding:30px}section{padding:10px 0;break-inside:auto}figure,table{break-inside:avoid}details{display:block}}'''
    (OUT/"量化笔试题二_完整答案.html").write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>量化笔试题二｜完整答案</title><style>'+css+'</style>'+body+'</html>',encoding="utf-8")
    print(f"Report: {OUT / '量化笔试题二_完整答案.html'}")
    print(f"Training-only chosen: {w} days / {p:.1%}; test return {opt['total_returns']:.2%}")


if __name__ == "__main__":
    main()
