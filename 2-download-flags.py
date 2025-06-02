import json
import os
import urllib.request
from urllib.error import HTTPError, URLError
import argparse
import unicodedata

def normalize_country_name(name):
    return unicodedata.normalize('NFKD', name.strip().lower()).encode('ascii', 'ignore').decode('ascii')

def build_country_mapping(countries_data):
    country_mapping = {}
    for country in countries_data:
        code = country.get('cca2', country.get('cca3', None))
        if not code:
            continue
        
        common_name = normalize_country_name(country['name']['common'])
        country_mapping[common_name] = code
        
        official_name = normalize_country_name(country['name']['official'])
        country_mapping[official_name] = code
        
        for alt in country.get('altSpellings', []):
            alt_name = normalize_country_name(alt)
            country_mapping[alt_name] = code
            
        for lang, trans in country.get('translations', {}).items():
            trans_common = normalize_country_name(trans.get('common', ''))
            if trans_common:
                country_mapping[trans_common] = code
            trans_official = normalize_country_name(trans.get('official', ''))
            if trans_official:
                country_mapping[trans_official] = code
    
    return country_mapping

def download_flag(code, flags_dir='flags'):
    os.makedirs(flags_dir, exist_ok=True)
    filename = f"{code}.svg"
    filepath = os.path.join(flags_dir, filename)
    url = f"https://hatscripts.github.io/circle-flags/flags/{code.lower()}.svg"
    
    try:
        urllib.request.urlretrieve(url, filepath)
        return filename, None
    except (HTTPError, URLError) as e:
        return None, str(e)

def main():
    parser = argparse.ArgumentParser(description='Map country names to ISO codes and download flags')
    parser.add_argument('input_file', help='JSON file from previous script')
    parser.add_argument('countries_file', help='Path to countries.json')
    parser.add_argument('--output', help='Output JSON file name', default='country_mappings.json')
    args = parser.parse_args()

    with open(args.input_file, 'r') as f:
        data = json.load(f)
        countries_list = data['unique_countries_origin']

    with open(args.countries_file, 'r') as f:
        countries_data = json.load(f)
    
    country_mapping = build_country_mapping(countries_data)
    
    results = []
    for country in countries_list:
        normalized = normalize_country_name(country)
        if normalized in country_mapping:
            code = country_mapping[normalized]
            flag_file, error = download_flag(code)
            result = {
                'original_name': country,
                'normalized_name': normalized,
                'iso_code': code,
                'flag_file': flag_file,
                'error': error
            }
        else:
            result = {
                'original_name': country,
                'normalized_name': normalized,
                'iso_code': None,
                'flag_file': None,
                'error': 'Country not found in mapping'
            }
        results.append(result)
    
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2)
    
    found_count = sum(1 for r in results if r['iso_code'])
    download_success = sum(1 for r in results if r['flag_file'])
    print(f"Processed {len(countries_list)} countries")
    print(f"Successfully mapped: {found_count}")
    print(f"Flags downloaded: {download_success}")
    print(f"Results saved to {args.output}")
    print(f"Flags saved to 'flags/' directory")

if __name__ == "__main__":
    main()