import sys
import json
import os
from collections import defaultdict

def process_jsonl(input_path, language_code):
    unique_genders = set()
    unique_countries = set()
    unique_combinations = set()
    
    processed = 0
    
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    
                    if entry.get('language') != language_code:
                        continue
                    
                    origin = entry.get('origin', [])
                    if len(origin) < 3:
                        continue
                    
                    gender = origin[1].strip()
                    country = origin[2].strip()
                    
                    unique_genders.add(gender)
                    unique_countries.add(country)
                    unique_combinations.add((gender, country))
                    
                    processed += 1
                    if processed % 100000 == 0:
                        print(f"Processed {processed:,} entries...")
                        
                except json.JSONDecodeError:
                    print(f"Skipping invalid JSON line: {line.strip()}")
                except Exception as e:
                    print(f"Error processing line: {e}")
    
    except FileNotFoundError:
        print(f"Error: File '{input_path}' not found.")
        return
    
    print(f"\nFinished processing. Total matching entries: {processed:,}")
    print(f"Unique genderss: {len(unique_genders)}")
    print(f"Unique countries: {len(unique_countries)}")
    print(f"Unique combinations: {len(unique_combinations)}")
    
    output = {
        "unique_genders_origin": sorted(unique_genders),
        "unique_countries_origin": sorted(unique_countries),
        "unique_combinations": sorted(
            [[s, t] for s, t in unique_combinations],
            key=lambda x: (x[0], x[1])
        )
    }
    
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    output_file = f"{base_name}_{language_code}_origin_stats.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)
    
    print(f"\nResults saved to: {output_file}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python 1-get-origins.py <input_file.jsonl> <language_code>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    target_language = sys.argv[2]
    
    process_jsonl(input_file, target_language)