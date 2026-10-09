$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $pythonPath)) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCommand) {
        throw 'Python 3.11 or newer is required. Install Python, then run this script again.'
    }
    & $pythonCommand.Source -m venv (Join-Path $projectRoot '.venv')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$requirementsPath = Join-Path $projectRoot 'backend\requirements.txt'
& $pythonPath -c 'import alembic, fastapi, multipart, sqlalchemy, uvicorn' 2>$null
if ($LASTEXITCODE -ne 0) {
    & $pythonPath -m pip install -r $requirementsPath
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

& $pythonPath (Join-Path $PSScriptRoot 'run_local.py') @args
exit $LASTEXITCODE
