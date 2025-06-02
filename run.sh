#!/bin/bash

set -euo pipefail
IFS=$'\n\t'

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

DRY_RUN=false

log()    { echo -e "${CYAN}==> $*${NC}"; }
warn()   { echo -e "${YELLOW}WARNING: $*${NC}"; }
dry()    { echo -e "${BLUE}$*${NC}"; }
error()  { echo -e "${RED}ERROR: $*${NC}"; }
success(){ echo -e "${GREEN}$*${NC}"; }

for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
    esac
done

if command -v python3 > /dev/null; then
    success 'Python installed!'
else
    error "Python not installed! Download and install from https://www.python.org/downloads"
    exit 1
fi

if command -v curl > /dev/null; then
    success 'cURL installed!'
else
    error "cURL not installed! Download and install from https://curl.se/download.html"
    exit 1
fi

read -rp "Enter 2-letter language code: " code

while [[ ${#code} -lt 2 || ${#code} -gt 3 ]]; do
    read -rp "Invalid language code. Please provide an ISO 3166-1 alpha-2 (or alpha-3 if there's no alpha-2) code...: " code
done

if [ ! -f metadata.jsonl ]; then
    error "The metadata file doesn't exist! Download from FreeMDict cloud"
    exit 1
else
    success "Metadata file found!"
fi

log "Getting pronouncers data..."
if [[ "$DRY_RUN" == false ]]; then
    if [ ! -f metadata_"${code}"_origin_stats.json ]; then
        python3 1-get-origins.py metadata.jsonl "${code}"
    else
        log "Origin stats file exists! Skipping."
    fi
else
    if [ ! -f metadata_"${code}"_origin_stats.json ]; then
        dry 'python3 1-get-origins.py metadata.jsonl "${code}"'
    else
        log "Origin stats file exists! Skipping."
    fi
fi

if [[ "$DRY_RUN" == false ]]; then
    if [ ! -f countries.json ]; then
        log "The countries file doesn't exist. Downloading..."
        curl https://raw.githubusercontent.com/mledoze/countries/refs/heads/master/countries.json --output countries.json
    else
        log "Countries file found!"
    fi
else
    if [ ! -f countries.json ]; then
        log "The countries file doesn't exist. Downloading..."
        dry 'curl https://raw.githubusercontent.com/mledoze/countries/refs/heads/master/countries.json --output countries.json'
    else
        log "Countries file found!"
    fi
fi

log "Downloading icon flags..."
if [[ "$DRY_RUN" == false ]]; then
    if [ ! -d "flags" ] && [ ! -f "country_mappings.json" ]; then
        python3 2-download-flags.py metadata_"${code}"_origin_stats.json countries.json
    else
        log "Flags directory and country mappings found! Skipping download."
    fi
else
    if [ ! -d "flags" ] && [ ! -f "country_mappings.json" ]; then
        dry 'python3 2-download-flags.py metadata_"${code}"_origin_stats.json countries.json'
    else
        log "Flags directory and country mappings found! Skipping download."
    fi
fi

echo "Downloading gender icons..."
if [[ "$DRY_RUN" == false ]]; then
    if [ ! -f venus.svg ]; then
        curl https://raw.githubusercontent.com/free-icons/free-icons/refs/heads/master/svgs/solid-venus.svg --output venus.svg
    fi

    if [ ! -f mars.svg ]; then
        curl https://raw.githubusercontent.com/free-icons/free-icons/refs/heads/master/svgs/solid-mars.svg --output mars.svg
    fi
else
    if [ ! -f venus.svg ]; then
        dry 'curl https://raw.githubusercontent.com/free-icons/free-icons/refs/heads/master/svgs/solid-venus.svg --output venus.svg'
    fi

    if [ ! -f mars.svg ]; then
        dry 'curl https://raw.githubusercontent.com/free-icons/free-icons/refs/heads/master/svgs/solid-mars.svg --output mars.svg'
    fi
fi

log "Creating icons..."
if [[ "$DRY_RUN" == false ]]; then
    python3 3-create-icons.py metadata_"${code}"_origin_stats.json country_mappings.json flags/
else
    dry 'python3 3-create-icons.py metadata_"${code}"_origin_stats.json country_mappings.json flags/'
fi

log "Checking for python modules..."
python3 -c "import sqlite3, json, pathlib; print('All modules available')"

if [ ! -d "${code}" ]; then
    error "No audio directory found. Please download from here: https://rutracker.org/forum/viewtopic.php?t=6211002"
    exit 1
else
    success "Audio directory exists!"
    log "Creating databases..."
    if [[ "$DRY_RUN" == false ]]; then
        python3 4-create-database.py "."
    else
        dry 'python3 4-create-database.py "."'
    fi
fi

log "Generating title and description..."
if [[ "$DRY_RUN" == false ]]; then
    python3 5-title-description.py "${code}"
else
    dry 'python3 5-title-description.py "${code}"'
fi

if command -v mdict > /dev/null; then
    log 'mdict-utils installed!'
else
    error "mdict not found! Run 'pip3 install mdict-utils'!"
    read -p "Do you want to install it in a virtual environment? [y/N] " -n 1 -r
    echo # move to a new line
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        python3 -m venv .forvo
        source .forvo/bin/activate
        pip3 install mdict-utils
    else
        exit 1
    fi
fi

if [[ "$DRY_RUN" == false ]]; then
    mdict --db-txt "forvo_simple.db"
    mdict --title title.html --description description.html --encoding utf8 -a forvo_simple.db.txt forvo-"${code}".mdx
    mkdir data
    mv "${code}"/ data/
    mv icons/ data/
    mdict --title title.html --description description.html --encoding utf8 -a data forvo-"${code}".mdd
else
    dry 'mdict --db-txt "forvo_simple.db" \
    mdict --title title.html --description description.html --encoding utf8 -a forvo_simple.db.txt forvo-"${code}".mdx \
    mkdir data \
    mv "${code}"/ data/ \
    mv icons/ data/ \
    mdict --title title.html --description description.html --encoding utf8 -a data forvo-"${code}".mdd'
fi

success "All done!"

read -r -p "Remove intermediary files? (y/n) " answer

if [[ "${answer}" =~ ^[Yy]$ ]]; then
    if [[ "$DRY_RUN" == false ]]; then
        rm -rv countries.json country_mappings.json forvo_database.db forvo_processor.log forvo_simple.db forvo_simple.db.txt mars.svg venus.svg metadata_"${code}"_origin_stats.json flags icons title.html description.html
        exit 0
    else
        dry 'rm -rv countries.json country_mappings.json forvo_database.db forvo_processor.log forvo_simple.db forvo_simple.db.txt mars.svg venus.svg metadata_"${code}"_origin_stats.json flags icons title.html description.html'
        exit 0
    fi
else
    exit 0
fi