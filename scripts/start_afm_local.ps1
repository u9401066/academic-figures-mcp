[CmdletBinding(PositionalBinding = $false)]
param(
    [Parameter(Position = 0)]
    [ValidateSet("server", "run")]
    [string]$Mode = "server",

    [string]$EnvFile = "env",

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Arguments
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot

function Import-EnvFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path $Path)) {
        throw "Env file not found: $Path"
    }

    foreach ($rawLine in Get-Content $Path) {
        $line = $rawLine.Trim()
        if (-not $line -or $line.StartsWith("#")) {
            continue
        }

        if ($line.StartsWith("export ")) {
            $line = $line.Substring(7).Trim()
        }
        elseif ($line.StartsWith("set ")) {
            $line = $line.Substring(4).Trim()
        }

        $parts = $line -split "=", 2
        if ($parts.Length -ne 2) {
            continue
        }

        $name = $parts[0].Trim()
        $value = $parts[1].Trim()
        if (-not $name) {
            continue
        }

        if ((($value.StartsWith('"')) -and ($value.EndsWith('"'))) -or (($value.StartsWith("'")) -and ($value.EndsWith("'")))) {
            $value = $value.Substring(1, $value.Length - 2)
        }

        Set-Item -Path "Env:$name" -Value $value
    }
}

Set-Location $repoRoot
Import-EnvFile -Path $EnvFile

if ($Mode -eq "server") {
    uv run --project $repoRoot python -m src.presentation.server @Arguments
    exit $LASTEXITCODE
}

uv run --project $repoRoot python -m src.presentation.direct_run @Arguments
exit $LASTEXITCODE