$ErrorActionPreference = "Stop"

if (-not $env:APP_HOST) { $env:APP_HOST = "0.0.0.0" }
if (-not $env:APP_PORT) { $env:APP_PORT = "8000" }
if (-not $env:APP_RELOAD) { $env:APP_RELOAD = "true" }
if (-not $env:FRONTEND_ONLY) { $env:FRONTEND_ONLY = "false" }

Write-Host "[run_local] APP_HOST=$env:APP_HOST APP_PORT=$env:APP_PORT APP_RELOAD=$env:APP_RELOAD FRONTEND_ONLY=$env:FRONTEND_ONLY"
if ($env:APP_RELOAD -match '^(?i:true|1|yes|on)$') {
    uvicorn app.main:app --host $env:APP_HOST --port $env:APP_PORT --reload
} else {
    uvicorn app.main:app --host $env:APP_HOST --port $env:APP_PORT
}
