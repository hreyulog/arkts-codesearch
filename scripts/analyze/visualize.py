'''
数据集可视化统计脚本

Usage:
    python visualize.py --input final_ds.jsonl --output visualizations/
'''

import json
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

sns.set(style="whitegrid")

def load_jsonl(file_path):
    records = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            records.append(json.loads(line.strip()))
    return pd.DataFrame(records)

def add_stats_columns(df):
    df['function_lines'] = df['function'].apply(lambda x: len(x.split('\n')) if x else 0)
    df['function_len'] = df['function'].apply(lambda x: len(x) if x else 0)
    df['docstring_len'] = df['docstring'].apply(lambda x: len(x) if x else 0)
    df['ast_len'] = df['ast_function'].apply(lambda x: len(x.split('#')) if x else 0)
    df['has_identifier'] = df['identifier'].apply(lambda x: bool(x))
    return df

def plot_distribution(data, xlabel, ylabel, title, output_path, xlim=None, bins=200, color='skyblue'):
    plt.figure(figsize=(8, 5))
    sns.histplot(data, bins=bins, kde=True, color=color)
    if xlim:
        plt.xlim(xlim)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()

def plot_pie(data, labels, output_path, colors=None, title=None):
    plt.figure(figsize=(6, 6))
    plt.pie(
        data, 
        labels=labels,
        autopct='%1.1f%%',
        startangle=90,
        colors=colors or ['skyblue', 'lightgreen']
    )
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()

def visualize_dataset(input_file, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Loading {input_file}...")
    df = load_jsonl(input_file)
    
    print("Adding statistics columns...")
    df = add_stats_columns(df)
    
    print("Generating plots...")
    
    plot_distribution(
        df['function_lines'], 
        'Number of Lines', 'Count',
        'Function Length (lines)',
        os.path.join(output_dir, 'function_lines.png'),
        xlim=(0, 300)
    )
    
    plot_distribution(
        df['docstring_len'],
        'Docstring Length', 'Count',
        'Docstring Length (characters)',
        os.path.join(output_dir, 'docstring_len.png'),
        xlim=(0, 1000),
        color='lightgreen'
    )
    
    plot_distribution(
        df['function_len'],
        'Function Length', 'Count',
        'Function Length (characters)',
        os.path.join(output_dir, 'function_len.png'),
        xlim=(0, 10000),
        color='lightgreen'
    )
    
    plot_distribution(
        df['ast_len'],
        'Number of AST Nodes', 'Count',
        'AST Length',
        os.path.join(output_dir, 'ast_len.png'),
        xlim=(0, 6000),
        color='salmon'
    )
    
    if 'source' in df.columns:
        source_counts = df['source'].value_counts()
        plot_pie(
            source_counts.values,
            source_counts.index.tolist(),
            os.path.join(output_dir, 'source_distribution.png')
        )
    
    identifier_counts = df['has_identifier'].value_counts()
    plot_pie(
        identifier_counts.values,
        ['Yes', 'No'],
        os.path.join(output_dir, 'has_identifier.png'),
        colors=['salmon', 'lightgray']
    )
    
    if 'nwo' in df.columns:
        top_nwo = df['nwo'].value_counts().head(10)
        plt.figure(figsize=(10, 5))
        sns.barplot(x=top_nwo.index, y=top_nwo.values, palette='viridis')
        plt.xlabel('Repository')
        plt.ylabel('Number of Functions')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'top_repos.png'))
        plt.close()
    
    print(f"Plots saved to {output_dir}")
    
    print("\n=== Dataset Statistics ===")
    print(f"Total records: {len(df)}")
    print(f"Function lines (mean): {df['function_lines'].mean():.2f}")
    print(f"Function length (mean): {df['function_len'].mean():.2f}")
    print(f"Docstring length (mean): {df['docstring_len'].mean():.2f}")
    
    return df

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Visualize dataset")
    parser.add_argument("--input", required=True, help="Input JSONL file")
    parser.add_argument("--output", default="visualizations", help="Output directory")
    
    args = parser.parse_args()
    visualize_dataset(args.input, args.output)
