# PowerShell helper to detect NVIDIA GPU and run docker compose with optional GPU override
param(
  [string]$Command = 'up',
  [switch]$Detached,
  [switch]$WithApp
)
if ($Command -eq 'up' -and $Detached) { $extraArgs = '-d' } else { $extraArgs = '' }
$baseCompose = '-f docker-compose.yml'
$gpuCompose = '-f docker-compose.gpu.yml'

# Respect START_APP environment variable
if ($env:START_APP) { $WithApp = $true }

function Has-Nvidia {
  try {
    $null = & nvidia-smi.exe -L 2>$null
    return $true
  } catch {
    # No nvidia-smi or failed
    return $false
  }
}

# Profile arg if enabling app
$profileArg = @()
if ($WithApp) { $profileArg = @('--profile','ai-file-organizer') }

if (Has-Nvidia) {
  if (Test-Path docker-compose.gpu.yml) {
    Write-Host "NVIDIA GPU detected — launching with GPU compose override"
    docker compose $baseCompose $gpuCompose $profileArg $Command $extraArgs
  } else {
    Write-Host "NVIDIA GPU detected but docker-compose.gpu.yml not found — launching without GPU override"
    docker compose $baseCompose $profileArg $Command $extraArgs
  }
} else {
  Write-Host "No NVIDIA GPU detected — launching without GPU override"
  docker compose $baseCompose $profileArg $Command $extraArgs
}
