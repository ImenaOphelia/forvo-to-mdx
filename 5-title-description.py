import json
import sys
from pathlib import Path

def main():
    if len(sys.argv) != 2:
        print("Usage: python 5-title-description.py <language_code>")
        sys.exit(1)

    code = sys.argv[1]
    mapping_file = Path("languages.json")

    if not mapping_file.exists():
        print("Error: 'languages.json' file not found.")
        sys.exit(1)

    try:
        with open(mapping_file, 'r', encoding='utf-8') as f:
            lang_map = json.load(f)
    except json.JSONDecodeError:
        print("Error: Invalid JSON format in 'languages.json'.")
        sys.exit(1)

    language = lang_map.get(code)
    if not language:
        print(f"Error: Language code '{code}' not found in the mapping.")
        sys.exit(1)

    title_content = f"Forvo {language}"
    description_content = f"All Forvo {language} audios uploaded until 2021.<br>Converted with script by ImenaOphelia"

    with open("title.html", "w", encoding="utf-8") as f:
        f.write(title_content)

    with open("description.html", "w", encoding="utf-8") as f:
        f.write(description_content)

    print("Generated:")
    print(f"  - title.html: {title_content}")
    print(f"  - description.html: {description_content}")

if __name__ == "__main__":
    main()