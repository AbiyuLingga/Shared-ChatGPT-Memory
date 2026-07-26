$ErrorActionPreference = "Stop"
$pythonCommand = Get-Command py -ErrorAction SilentlyContinue
if ($pythonCommand) {
    & py -3.12 -m venv .venv
    & .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
} else {
    Write-Error "Install Python 3.12 and rerun this script."
}
