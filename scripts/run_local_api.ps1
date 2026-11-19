param(
    [switch]$NoReload
)

$ErrorActionPreference = "Stop"
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$environmentFile = Join-Path $repositoryRoot ".env"

if (-not (Test-Path $environmentFile -PathType Leaf)) {
    throw "Missing $environmentFile. Copy .env.example to .env and configure it first."
}

foreach ($line in Get-Content $environmentFile) {
    if ($line -match '^\s*#' -or $line -match '^\s*$') {
        continue
    }
    if ($line -notmatch '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$') {
        throw "Invalid environment line in .env."
    }

    $name = $Matches[1]
    $value = $Matches[2]
    if ($value.Length -ge 2 -and
        (($value.StartsWith('"') -and $value.EndsWith('"')) -or
         ($value.StartsWith("'") -and $value.EndsWith("'")))) {
        $value = $value.Substring(1, $value.Length - 2)
    }
    Set-Item -Path "Env:$name" -Value $value
}

foreach ($requiredName in @("AUTH0_DOMAIN", "AUTH0_AUDIENCE")) {
    if (-not (Get-Item -Path "Env:$requiredName" -ErrorAction SilentlyContinue).Value) {
        throw "$requiredName is empty in .env."
    }
}

if (-not (Get-Item -Path "Env:AUTH0_ALLOWED_SUBJECTS" -ErrorAction SilentlyContinue).Value) {
    Write-Warning "AUTH0_ALLOWED_SUBJECTS is empty; protected API routes will deny access."
}

Push-Location $repositoryRoot
try {
    $virtualEnvironmentPython = Join-Path $repositoryRoot ".venv\Scripts\python.exe"
    if (Test-Path $virtualEnvironmentPython -PathType Leaf) {
        $pythonCommand = $virtualEnvironmentPython
    }
    else {
        $pythonCommand = (Get-Command python -ErrorAction Stop).Source
    }

    & $pythonCommand -c "import fastapi, uvicorn, jwt" 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Backend dependencies are missing. Run '.\.venv\Scripts\python.exe -m pip install -r requirements.txt' first."
    }

    $arguments = @("-m", "uvicorn", "src.api.main:app", "--host", "127.0.0.1", "--port", "8765")
    if (-not $NoReload) {
        $arguments += "--reload"
    }
    & $pythonCommand @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Uvicorn exited with code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
