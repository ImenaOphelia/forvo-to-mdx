# Forvo to MDX

Generate an MDX dictionary from Forvo pronunciation data.

## Requirements

- Python (latest version recommended)
- cURL (optional on Windows)
- [mdict-utils](https://github.com/liuyug/mdict-utils) (you will be prompted to install this if not already installed)
- On Linux: `xz-utils` for decompressing `.xz` files

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/ImenaOphelia/forvo-to-mdx.git
cd forvo-to-mdx
```

Alternatively, download the ZIP from GitHub (Code → Download ZIP) and extract it. git is not required for running the script.


---

### 2. Download Required Files

The script will automatically download most required files, except for two large ones due to hosting restrictions.

#### a. Download metadata.jsonl

Download metadata.jsonl.xz from this link, then extract it with:

```bash
xz -d metadata.jsonl.xz
```

Make sure the extracted file is named metadata.jsonl and placed in the root of the project directory.

#### b. Download Audio Files

1. Go to the Opus audio folder and download the folder for your target language.


2. Alternatively, use the torrent link if the files are not available directly.


3. Extract the downloaded audio folder and place it in the project root. The folder name should match the 2-letter language code (e.g., ru for Russian).



Example structure (for Russian):

```
forvo-to-mdx/
├── ru/
│   ├── username1/
│   │   ├── word1.opus
│   │   └── ...
│   └── ...
├── metadata.jsonl
├── run.sh
├── 1-get-origins.py
├── 2-download-flags.py
├── 3-create-icons.py
├── 4-create-database.py
├── 5-title-description.py
├── languages.json
└── README.md
```

---

### 3. Run the Script

On Linux/macOS:

```bash
chmod +x run.sh
./run.sh
```

On Windows:

```ps1
.\run.ps1
```

**DISCLAIMER**! Since I don't use Windows, the PowerShell script was written by artificial intelligence. I am not able to troubleshoot or help with any issues related to it.


---

## Contributing

Bug reports, suggestions, and especially pull requests are very welcome.

