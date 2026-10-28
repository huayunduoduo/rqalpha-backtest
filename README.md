# 量化笔试题二：复现说明

本项目已在 Windows 本机真实执行。完整答案见 submission/量化笔试题二_完整答案.html。

## 环境

- 工作目录：D:\rqalpha_exam
- 完整 Anaconda Distribution 2024.02-1，安装于 D:\rqalpha_exam\anaconda3，conda 24.1.2
- Python 3.11.11，独立 conda 环境 D:\rqalpha_exam\envs\rqalpha
- RQAlpha 6.4.0；克隆提交 a5fb4e43879c381e61131399dcc094d495c7080a
- 官方行情包 rqbundle_202608.tar.bz2，解压到 bundle/
- 起初用 Miniconda 引导建立环境，后补齐完整 Anaconda（含 Navigator），用其 conda 管理同一独立环境并重新执行官方示例。没有改动环境内回测依赖。
- 环境、下载、pip/conda 缓存、运行缓存均位于 D 盘。

## 在本机复现（PowerShell）

```powershell
Set-Location D:\rqalpha_exam
.\run.ps1 demo.py
.\run.ps1 run_experiment.py smoke
.\run.ps1 run_experiment.py grid
.\run.ps1 run_experiment.py baseline
.\run.ps1 verify.py
.\run.ps1 make_report.py
```

run.ps1 设置解释器路径、源码导入路径、DLL 路径以及 D 盘缓存目录，并通过完整 Anaconda 的 conda run 执行。完整发行版缺失时才回退到独立环境解释器。
运行脚本根据已有 summary.json 跳过成功完成的实验。如果更换代码、数据或配置，先移动/删除对应旧 results 子目录。
更改股票池、因子窗口、成交量处理或数据包时，还须清理 cache/signals_v1。
不要使用别人提供的未知 pickle 缓存；此项目的 pickle 只读取本机生成内容。

## 新机器

将 code/ 下文件放入单独的 D 盘目录（例如 D:\rqalpha_exam），然后：

1. 从 Anaconda 官方下载 Anaconda Distribution，指定安装到 D:\rqalpha_exam\anaconda3。将 TEMP、TMP、CONDA_PKGS_DIRS、CONDA_ENVS_PATH、PIP_CACHE_DIR 设到 D 盘。
2. `git clone https://github.com/ricequant/rqalpha.git D:\rqalpha_exam\rqalpha`
3. `git -C D:\rqalpha_exam\rqalpha checkout a5fb4e43879c381e61131399dcc094d495c7080a`
4. `conda create -p D:\rqalpha_exam\envs\rqalpha python=3.11 -y`
5. 激活该环境，安装 requirements-lock.txt 中锁定的第三方包和 `pip install -e D:\rqalpha_exam\rqalpha`。锁文件里的 editable 路径需按实际路径调整。
6. 下载 https://bundle.assets.ricequant.com/bundles_v4/rqbundle_202608.tar.bz2 并解压至 bundle/（stocks.h5 等直接位于该目录）。
7. 按本机命令顺序运行。运行入口会自动调用完整 Anaconda 的 conda 管理器。

## 文件

- strategy.py：周首交易日盘前因子计算、收盘执行、等权调仓。
- signals.py：历史股票池过滤、样本标准差、降序选股、可复用历史截面缓存。
- run_experiment.py：官方示例、基准回测、25 组网格、邻域选择、2024/2025 样本外。
- demo.py：第 1 题可截图的实际示例执行入口。
- verify.py：独立原始行情复算以及调仓、比例、净值和成交检查。
- make_report.py：图表、中文 HTML 报告及提交目录整理。
- evidence/：真实 VS Code 截图、执行日志、环境与检查记录。
- results/：汇总、净值、基准、实际成交及目标选股记录。

参数：训练 2021—2023，验证 2024，测试 2025；窗口 10/15/20/25/30；比例 5/7.5/10/12.5/15%。
选择规则只看训练：内部 3×3 邻域夏普均值减标准差，最大得分中心。
这不是保证盈利的规则。收益差也如实报告。

官方示例保留满仓下单方式并使用零滑点；因子实验全部采用 0.1% 单边滑点、万三佣金和历史印花税。
完整原始框架源码、环境和大体积行情留在 D 盘工作目录，不包含在提交压缩包内。
