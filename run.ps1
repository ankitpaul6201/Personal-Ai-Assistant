# JARVIS AI Assistant PowerShell Launcher
$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "JARVIS AI Assistant"

Write-Host "🤖 Starting JARVIS AI Assistant..." -ForegroundColor Cyan
Set-Location -Path $PSScriptRoot

try {
    $env:PYTHONPATH = "$PSScriptRoot\src;$env:PYTHONPATH"
    python main.py
} catch {
    Write-Host "`n❌ JARVIS exited with an error: $_" -ForegroundColor Red
    Read-Host -Prompt "Press Enter to exit..."
}
