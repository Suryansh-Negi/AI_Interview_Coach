$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$streamlitExe = Join-Path $projectRoot ".venv\Scripts\streamlit.exe"
$mongoUri = $env:MONGODB_URI
$mongoRequired = $env:MONGODB_REQUIRED
if (Test-Path (Join-Path $projectRoot ".env")) {
    foreach ($line in Get-Content (Join-Path $projectRoot ".env")) {
        if ($line -match '^\s*MONGODB_URI\s*=\s*(.*)$' -and -not $env:MONGODB_URI) {
            $mongoUri = $Matches[1].Trim().Trim('"').Trim("'")
        }
        if ($line -match '^\s*MONGODB_REQUIRED\s*=\s*(.*)$' -and -not $env:MONGODB_REQUIRED) {
            $mongoRequired = $Matches[1].Trim().Trim('"').Trim("'")
        }
    }
}
$mongoRequired = "$mongoRequired".Trim().ToLowerInvariant() -in @("1", "true", "yes", "on")
$usesLocalMongo = [string]::IsNullOrWhiteSpace($mongoUri) -or $mongoUri -match '^mongodb://(127\.0\.0\.1|localhost):27017/?$'

if (-not (Test-Path $venvPython)) {
    Write-Host "Creating the project virtual environment..."
    python -m venv .venv
}

Write-Host "Checking/installing project packages (no API keys are required)..."
& $venvPython -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }

if ($mongoRequired -and $usesLocalMongo) {
    $mongoReachable = Test-NetConnection -ComputerName 127.0.0.1 -Port 27017 -InformationLevel Quiet -WarningAction SilentlyContinue
    if (-not $mongoReachable) {
        throw "MongoDB is required but is not listening on 127.0.0.1:27017. Install/start the MongoDB Server Windows service, then rerun this script."
    }
}

$apiProcess = Start-Process `
    -FilePath $venvPython `
    -ArgumentList @("-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000") `
    -WorkingDirectory $projectRoot `
    -PassThru `
    -WindowStyle Hidden

try {
    $apiReady = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        if ($apiProcess.HasExited) {
            if ($mongoRequired) { throw "The API stopped during startup. MongoDB is required; confirm the MongoDB service is running and MONGODB_URI is correct." }
            throw "The API process stopped during startup."
        }
        try {
            $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health" -TimeoutSec 2
            if ($health.status -eq "ok") { $apiReady = $true; break }
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    if (-not $apiReady) { throw "The API did not become ready. Check whether port 8000 is already in use." }

    if ($health.database -eq "mongodb") {
        Write-Host "Connected to MongoDB. Users and interview history will persist between runs."
    } elseif ($mongoRequired) {
        throw "MongoDB is required, but the API reports temporary storage. Check MONGODB_URI and the MongoDB server."
    } else {
        Write-Warning "MongoDB is not connected. This run uses temporary storage; data clears when the API stops."
    }

    Write-Host "Starting the AI Interview Coach."
    & $streamlitExe run app.py
}
finally {
    if ($apiProcess -and -not $apiProcess.HasExited) {
        Stop-Process -Id $apiProcess.Id -Force
    }
}
