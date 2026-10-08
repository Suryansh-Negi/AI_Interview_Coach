$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$streamlitExe = Join-Path $projectRoot ".venv\Scripts\streamlit.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "Creating the project virtual environment..."
    python -m venv .venv
}

Write-Host "Checking/installing project packages (no API keys are required)..."
& $venvPython -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }

$apiProcess = Start-Process `
    -FilePath $venvPython `
    -ArgumentList @("-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000") `
    -WorkingDirectory $projectRoot `
    -PassThru `
    -WindowStyle Hidden

try {
    $apiReady = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        if ($apiProcess.HasExited) { throw "The API process stopped during startup." }
        try {
            $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health" -TimeoutSec 2
            if ($health.status -eq "ok") { $apiReady = $true; break }
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    if (-not $apiReady) { throw "The API did not become ready. Check whether port 8000 is already in use." }

    Write-Host "Starting the AI Interview Coach. No .env file or API key is needed for demo mode."
    & $streamlitExe run app.py
}
finally {
    if ($apiProcess -and -not $apiProcess.HasExited) {
        Stop-Process -Id $apiProcess.Id -Force
    }
}
