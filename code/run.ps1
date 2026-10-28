$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$env:TEMP = Join-Path $root 'tmp'
$env:TMP = $env:TEMP
$env:PIP_CACHE_DIR = Join-Path $root 'cache/pip'
$env:CONDA_PKGS_DIRS = Join-Path $root 'cache/conda'
$env:CONDA_ENVS_PATH = Join-Path $root 'envs'
$env:PYTHONPYCACHEPREFIX = Join-Path $root 'cache/pycache'
$env:MPLCONFIGDIR = Join-Path $root 'cache/matplotlib'
$env:MPLBACKEND = 'Agg'
$env:PYTHONUTF8 = '1'
$env:PYTHONPATH = Join-Path $root 'rqalpha'
$env:PATH = "$root\envs\rqalpha;$root\envs\rqalpha\Library\bin;$root\envs\rqalpha\Scripts;" + $env:PATH
Set-Location $root
if (Test-Path "$root\anaconda3\Scripts\conda.exe") {
    & "$root\anaconda3\Scripts\conda.exe" run -p "$root\envs\rqalpha" --no-capture-output python @args
} else {
    & "$root\envs\rqalpha\python.exe" @args
}
exit $LASTEXITCODE
