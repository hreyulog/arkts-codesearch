'''
合并数据集脚本
支持多个JSONL文件合并、去重、字段清理

Usage:
    python merge_dataset.py --inputs file1.jsonl file2.jsonl --output final.jsonl
'''

import json
from pathlib import Path

DEFAULT_DROP_KEYS = {
    "parameters",
    "argument_list",
    "return_statement",
    "imports",
    "calls",
    "local_calls",
    "docstring_summary",
    "docstring_tokens",
    "obf_function_tokens",
    "ast_function_tokens",
    "function_tokens"
}

def merge_datasets(input_files, output_file, drop_keys=None, source_labels=None):
    if drop_keys is None:
        drop_keys = DEFAULT_DROP_KEYS
    
    seen = set()
    merged = []
    
    for i, path in enumerate(input_files):
        source_label = source_labels[i] if source_labels else None
        
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line)
                
                if source_label:
                    data["source"] = source_label
                
                for k in drop_keys:
                    data.pop(k, None)
                
                dedup_key = (
                    data.get("docstring", ""),
                    data.get("function", "")
                )
                
                if dedup_key not in seen:
                    seen.add(dedup_key)
                    merged.append(data)
    
    with open(output_file, "w", encoding="utf-8") as f:
        for item in merged:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    
    print(f"Merged {len(merged)} records to {output_file}")
    return merged

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Merge datasets")
    parser.add_argument("--inputs", nargs="+", required=True, help="Input JSONL files")
    parser.add_argument("--output", required=True, help="Output JSONL file")
    parser.add_argument("--sources", nargs="+", help="Source labels for each input file")
    parser.add_argument("--drop-keys", nargs="+", help="Keys to drop from records")
    
    args = parser.parse_args()
    
    merge_datasets(
        args.inputs, 
        args.output,
        drop_keys=set(args.drop_keys) if args.drop_keys else None,
        source_labels=args.sources
    )
