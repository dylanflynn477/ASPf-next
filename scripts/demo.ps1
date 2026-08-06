$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    Write-Output "`n== ASP{f} source =="
    Get-Content "examples/01_basic_assignment.aspf"

    Write-Output "`n== Reference lowering =="
    aspf "examples/01_basic_assignment.aspf" --emit-lowered

    Write-Output "`n== Normalized model =="
    aspf "examples/01_basic_assignment.aspf"

    Write-Output "`n== Functionality conflict =="
    aspf "examples/04_conflicting_values.aspf"
}
finally {
    Pop-Location
}
