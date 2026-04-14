'''
Parquet转JSONL脚本

Usage:
    python parquet_to_jsonl.py --input functions_parquet/ --output output.jsonl
'''

import os
import json
import pandas as pd
import numpy as np
from tqdm import tqdm

def convert_obj(obj):
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj

def parquet_to_jsonl(input_dir, output_file):
    parquet_files = [f for f in os.listdir(input_dir) if f.endswith(".parquet")]
    
    with open(output_file, 'w', encoding='utf-8') as f_out:
        for file_name in tqdm(parquet_files, desc="Converting"):
            file_path = os.path.join(input_dir, file_name)
            df = pd.read_parquet(file_path)
            for record in df.to_dict(orient="records"):
                f_out.write(json.dumps(record, default=convert_obj, ensure_ascii=False) + "\n")
    
    print(f"Converted {len(parquet_files)} parquet files to {output_file}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Convert Parquet to JSONL")
    parser.add_argument("--input", required=True, help="Input directory with parquet files")
    parser.add_argument("--output", required=True, help="Output JSONL file")
    
    args = parser.parse_args()
    parquet_to_jsonl(args.input, args.output)
