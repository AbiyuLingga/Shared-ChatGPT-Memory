$ErrorActionPreference = "Stop"
$baseUrl = if ($env:SMOKE_BASE_URL) { $env:SMOKE_BASE_URL } else { "http://localhost:8000" }
if (-not $env:SMOKE_TOKEN) { throw "Set SMOKE_TOKEN to a short-lived Auth0 access token." }
$headers = @{ Authorization = "Bearer $env:SMOKE_TOKEN" }
Invoke-RestMethod "$baseUrl/health" | Out-Null
Invoke-RestMethod "$baseUrl/v1/memories/search" -Method Post -Headers $headers -ContentType "application/json" -Body '{"query":"smoke marker"}' | Out-Null
Write-Host "Basic authenticated smoke checks passed. Use the manual checklist for add/update/delete."
