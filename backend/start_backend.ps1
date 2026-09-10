param(
    [switch]$UseEnvDatabaseUrl
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$bloomRoot = Split-Path $PSScriptRoot -Parent
$cacheRoot = Join-Path $bloomRoot ".cache"
$hf = Join-Path $cacheRoot "huggingface"
$torch = Join-Path $cacheRoot "torch"
$pip = Join-Path $cacheRoot "pip"
@($cacheRoot, $hf, $torch, $pip) | ForEach-Object { New-Item -ItemType Directory -Force -Path $_ | Out-Null }

$env:HF_HOME = $hf
$env:TORCH_HOME = $torch
$env:PIP_CACHE_DIR = $pip
$env:BLOOM_OPENAI_API_KEY = "api-key"
$env:BLOOM_OPENAI_BASE_URL = "https://api.groq.com/openai/v1"
$env:BLOOM_OPENAI_MODEL = "llama-3.3-70b-versatile"
$env:BLOOM_OPENAI_JSON_OBJECT = "false"
$env:BLOOM_GRAMMAR_LANG = "en-GB"
$env:BLOOM_ENGLISH_VARIANT = "uk"

if (-not $UseEnvDatabaseUrl) {
    $env:BLOOM_DATABASE_URL = "postgresql://bloom:bloom@127.0.0.1:5433/bloom"
}
elseif ($env:BLOOM_DATABASE_URL -match '127\.0\.0\.1:5432\b|localhost:5432\b') {
    Write-Warning (
        "BLOOM_DATABASE_URL points at localhost:5432. That is usually a system Postgres, not this repo's Docker DB (host port 5433). " +
        "Run: .\start_backend.ps1   (omit -UseEnvDatabaseUrl) or fix/remove BLOOM_DATABASE_URL in Windows environment variables."
    )
}

Write-Host "Caches: HF_HOME=$hf"
Write-Host "Database: BLOOM_DATABASE_URL=$env:BLOOM_DATABASE_URL"
python -m uvicorn main:app --reload
