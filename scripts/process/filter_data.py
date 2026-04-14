'''
数据过滤脚本
支持按docstring过滤和按许可证过滤

Usage:
    python filter_data.py --input input.jsonl --output output.jsonl --filter-empty-docstring
    python filter_data.py --input input.jsonl --output output.jsonl --license-file licenses.jsonl
'''

import json
from pathlib import Path

ALLOWED_LICENSES = {
    '0BSD', 'ZLIB', 'ISC', 'BSD-3-CLAUSE', 'BSD-2-CLAUSE',
    'APACHE-2.0', 'Apache-2.0', 'MIT',
    'LGPL-3.0', 'LGPL-2.1',
    'EPL-1.0', 'MULANPSL-2.0', 'MulanPSL-2.0',
    'CC-BY-4.0', 'MPL-2.0', 'BSD-3-Clause', 'Unlicense'
}

def filter_empty_docstring(input_file, output_file, deduplicate=True):
    seen = set()
    count = 0
    
    with open(input_file, 'r', encoding='utf-8') as infile, \
         open(output_file, 'w', encoding='utf-8') as outfile:
        
        for line in infile:
            line = line.strip()
            if not line:
                continue
            
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            
            docstring = data.get('docstring')
            function = data.get('function')
            
            if not docstring:
                continue
            
            if deduplicate:
                key = (docstring, function)
                if key in seen:
                    continue
                seen.add(key)
            
            outfile.write(json.dumps(data, ensure_ascii=False) + '\n')
            count += 1
    
    print(f"Filtered {count} records to {output_file}")
    return count

def filter_by_license(input_file, license_file, output_file):
    repo_license_map = {}
    
    with open(license_file, "r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line)
            key = (data.get("source", ""), data.get("repo", ""))
            repo_license_map[key] = data.get("license")
    
    count = 0
    with open(input_file, "r", encoding="utf-8") as infile, \
         open(output_file, "w", encoding="utf-8") as outfile:
        
        for line in infile:
            data = json.loads(line)
            source = data.get("source", "")
            nwo = data.get("nwo", "")
            
            license_type = repo_license_map.get((source, nwo))
            if license_type in ALLOWED_LICENSES:
                outfile.write(json.dumps(data, ensure_ascii=False) + "\n")
                count += 1
    
    print(f"Filtered {count} records with allowed licenses")
    return count

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Filter data")
    parser.add_argument("--input", required=True, help="Input JSONL file")
    parser.add_argument("--output", required=True, help="Output JSONL file")
    parser.add_argument("--filter-empty-docstring", action="store_true", help="Filter empty docstrings")
    parser.add_argument("--license-file", help="License JSONL file for license filtering")
    parser.add_argument("--no-dedup", action="store_true", help="Disable deduplication")
    
    args = parser.parse_args()
    
    if args.filter_empty_docstring:
        filter_empty_docstring(args.input, args.output, deduplicate=not args.no_dedup)
    elif args.license_file:
        filter_by_license(args.input, args.license_file, args.output)
    else:
        print("Please specify --filter-empty-docstring or --license-file")
