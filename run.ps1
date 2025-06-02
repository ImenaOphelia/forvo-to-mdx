#!/usr/bin/env pwsh

param(
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$Colors = @{
    Red    = [System.ConsoleColor]::Red
    Green  = [System.ConsoleColor]::Green
    Yellow = [System.ConsoleColor]::Yellow
    Blue   = [System.ConsoleColor]::Blue
    Cyan   = [System.ConsoleColor]::Cyan
}

function Write-Log {
    param([string]$Message)
    Write-Host "==> $Message" -ForegroundColor $Colors.Cyan
}

function Write-Warning {
    param([string]$Message)
    Write-Host "WARNING: $Message" -ForegroundColor $Colors.Yellow
}

function Write-DryRun {
    param([string]$Message)
    Write-Host $Message -ForegroundColor $Colors.Blue
}

function Write-Error {
    param([string]$Message)
    Write-Host "ERROR: $Message" -ForegroundColor $Colors.Red
}

function Write-Success {
    param([string]$Message)
    Write-Host $Message -ForegroundColor $Colors.Green
}

try {
    $pythonVersion = python --version 2>$null
    if ($pythonVersion) {
        Write-Success "Python installed!"
    }
} catch {
    Write-Error "Python not installed! Download and install from https://www.python.org/downloads"
    exit 1
}

try {
    $curlVersion = curl --version 2>$null
    if ($curlVersion) {
        Write-Success "cURL installed!"
    }
} catch {
    Write-Warning "cURL not found, will use PowerShell Invoke-WebRequest instead"
}

do {
    $code = Read-Host "Enter 2-letter language code"
} while ($code.Length -lt 2 -or $code.Length -gt 3)

if (-not (Test-Path "metadata.jsonl")) {
    Write-Error "The metadata file doesn't exist! Download from FreeMDict cloud"
    exit 1
} else {
    Write-Success "Metadata file found!"
}

Write-Log "Getting pronouncers data..."
$originStatsFile = "metadata_$($code)_origin_stats.json"

if (-not (Test-Path $originStatsFile)) {
    if ($DryRun) {
        Write-DryRun "python 1-get-origins.py metadata.jsonl $code"
    } else {
        & python 1-get-origins.py metadata.jsonl $code
    }
} else {
    Write-Log "Origin stats file exists! Skipping."
}

if (-not (Test-Path "countries.json")) {
    Write-Log "The countries file doesn't exist. Downloading..."
    if ($DryRun) {
        Write-DryRun "Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/mledoze/countries/refs/heads/master/countries.json' -OutFile 'countries.json'"
    } else {
        try {
            Invoke-WebRequest -Uri "https://raw.githubusercontent.com/mledoze/countries/refs/heads/master/countries.json" -OutFile "countries.json"
        } catch {
            & curl "https://raw.githubusercontent.com/mledoze/countries/refs/heads/master/countries.json" --output "countries.json"
        }
    }
} else {
    Write-Log "Countries file found!"
}

Write-Log "Downloading icon flags..."
if (-not (Test-Path "flags" -PathType Container) -and -not (Test-Path "country_mappings.json")) {
    if ($DryRun) {
        Write-DryRun "python 2-download-flags.py $originStatsFile countries.json"
    } else {
        & python 2-download-flags.py $originStatsFile countries.json
    }
} else {
    Write-Log "Flags directory and country mappings found! Skipping download."
}

Write-Log "Downloading gender icons..."
if (-not (Test-Path "venus.svg")) {
    if ($DryRun) {
        Write-DryRun "Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/free-icons/free-icons/refs/heads/master/svgs/solid-venus.svg' -OutFile 'venus.svg'"
    } else {
        try {
            Invoke-WebRequest -Uri "https://raw.githubusercontent.com/free-icons/free-icons/refs/heads/master/svgs/solid-venus.svg" -OutFile "venus.svg"
        } catch {
            & curl "https://raw.githubusercontent.com/free-icons/free-icons/refs/heads/master/svgs/solid-venus.svg" --output "venus.svg"
        }
    }
}

if (-not (Test-Path "mars.svg")) {
    if ($DryRun) {
        Write-DryRun "Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/free-icons/free-icons/refs/heads/master/svgs/solid-mars.svg' -OutFile 'mars.svg'"
    } else {
        try {
            Invoke-WebRequest -Uri "https://raw.githubusercontent.com/free-icons/free-icons/refs/heads/master/svgs/solid-mars.svg" -OutFile "mars.svg"
        } catch {
            & curl "https://raw.githubusercontent.com/free-icons/free-icons/refs/heads/master/svgs/solid-mars.svg" --output "mars.svg"
        }
    }
}

Write-Log "Creating icons..."
if ($DryRun) {
    Write-DryRun "python 3-create-icons.py $originStatsFile country_mappings.json flags/"
} else {
    & python 3-create-icons.py $originStatsFile country_mappings.json flags/
}

Write-Log "Checking for python modules..."
& python -c "import sqlite3, json, pathlib; print('All modules available')"

if (-not (Test-Path $code -PathType Container)) {
    Write-Error "No audio directory found. Please download from here: https://rutracker.org/forum/viewtopic.php?t=6211002"
    exit 1
} else {
    Write-Success "Audio directory exists!"
    Write-Log "Creating databases..."
    if ($DryRun) {
        Write-DryRun "python 4-create-database.py ."
    } else {
        & python 4-create-database.py "."
    }
}

Write-Log "Generating title and description..."
if ($DryRun) {
    Write-DryRun "python 5-title-description.py $code"
} else {
    & python 5-title-description.py $code
}

try {
    $mdictVersion = & mdict --help 2>$null
    Write-Log "mdict-utils installed!"
} catch {
    Write-Error "mdict not found! Run 'pip install mdict-utils'!"
    $install = Read-Host "Do you want to install it in a virtual environment? [y/N]"
    if ($install -match "^[Yy]$") {
        & python -m venv .forvo
        if ($IsWindows) {
            & .forvo\Scripts\Activate.ps1
        } else {
            & .forvo/bin/Activate.ps1
        }
        & pip install mdict-utils
    } else {
        exit 1
    }
}

if ($DryRun) {
    Write-DryRun @"
mdict --db-txt "forvo_simple.db"
mdict --title title.html --description description.html --encoding utf8 -a forvo_simple.db.txt forvo-$code.mdx
New-Item -ItemType Directory -Name "data"
Move-Item "$code/" "data/"
Move-Item "icons/" "data/"
mdict --title title.html --description description.html --encoding utf8 -a data forvo-$code.mdd
"@
} else {
    & mdict --db-txt "forvo_simple.db"
    & mdict --title title.html --description description.html --encoding utf8 -a forvo_simple.db.txt "forvo-$code.mdx"
    New-Item -ItemType Directory -Name "data" -Force
    Move-Item "$code/" "data/" -Force
    Move-Item "icons/" "data/" -Force
    & mdict --title title.html --description description.html --encoding utf8 -a data "forvo-$code.mdd"
}

Write-Success "All done!"

$cleanup = Read-Host "Remove intermediary files? (y/n)"
if ($cleanup -match "^[Yy]$") {
    $filesToRemove = @(
        "countries.json", "country_mappings.json", "forvo_database.db", 
        "forvo_processor.log", "forvo_simple.db", "forvo_simple.db.txt", 
        "mars.svg", "venus.svg", $originStatsFile, "flags", "icons", 
        "title.html", "description.html"
    )
    
    if ($DryRun) {
        Write-DryRun "Remove-Item -Recurse -Force $($filesToRemove -join ', ')"
    } else {
        foreach ($file in $filesToRemove) {
            if (Test-Path $file) {
                Remove-Item -Recurse -Force $file
                Write-Log "Removed: $file"
            }
        }
    }
}

exit 0