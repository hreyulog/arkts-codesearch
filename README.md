# ArkTS Code Search

<p align="center">
  <img src="arktscodesearch.jpeg" alt="ArkTS-CodeSearch" width="600">
</p>

Source code parsing library based on [Tree-Sitter](https://tree-sitter.github.io/tree-sitter/) incremental parser

Run `build.sh` to install the library.

## Directory Structure

```
├── src/                    # Core parsing library
├── scripts/                # Data collection and processing scripts
│   ├── collect/           # Repository collection (download, license check)
│   ├── process/           # Data processing (filter, merge, convert)
│   └── analyze/           # Visualization and statistics
└── tests/                  # Unit tests
```

## Scripts Usage

### 1. Collect Repositories

```bash
# Get GitHub repo info
python scripts/collect/repo_info.py --source github --output github_repos.csv

# Get Gitee repo info  
python scripts/collect/repo_info.py --source gitee --output gitee_repos.csv --pages 100

# Download repositories
python scripts/collect/download_repos.py --source github --csv github_repos.csv --output repos/

# Check licenses
python scripts/collect/license_check.py --source github --csv github_repos.csv --output licenses.jsonl
```

### 2. Process Data

```bash
# Convert parquet to JSONL
python scripts/process/parquet_to_jsonl.py --input functions_parquet/ --output output.jsonl

# Filter data
python scripts/process/filter_data.py --input output.jsonl --output filtered.jsonl --filter-empty-docstring

# Merge datasets
python scripts/process/merge_dataset.py --inputs gitee.jsonl github.jsonl --output final.jsonl --sources gitee github
```

### 3. Analyze

```bash
# Visualize dataset
python scripts/analyze/visualize.py --input final.jsonl --output visualizations/
```

## Library Usage

Usage: `ark_function_parser COMMAND [OPTIONS]`

### Output data format
```
language - source language
identifier - qualified name of function
parameters - list of parameters passed to function
imports - imports used in function body
calls - all function calls in function body
local_calls - local function calls in function body
docstring - doc comment of this function
docstring_summary - summary of doc comment
function - function body
function_tokens - function split to tokens (without comments). Use this for the indexing (e.g. joining by whitespace)
obf_function - obfuscated function body
obf_function_tokens - obfuscated function split to tokens
ast_function - flatten ast function string
ast_function_tokens - ast function split to tokens
url - github link (if possible)
function_sha - hash of function
```

Available commands:

1. enry_scan_languages:

scan_source_files\
scan all repositories in output directory\
run enry for each directory and store json with source files in the source_info directory

Usage: `ark_function_parser enry_scan_languages [OPTIONS]`

Options:

    -e --enry_directory             directory with list of files to scan from enry [default: enry_jsons]
    -r --repos_directory            directory with repos to scan [default: repos]
    -p --parallel_jobs              number of parallel jobs to run [default: 20]


2. scan_functions:

scan all repositories in output directory\
run enry for each directory and store json with source files in the source_info directory

Usage: `ark_function_parser scan_functions [OPTIONS]`

Options:

    -l --lang                       language: arkts [default: arkts]
    -f --functions_directory        directory to store results [default: functions_parquet]
    -e --enry_directory             directory with list of files to scan from enry [default: enry_jsons]
    -r --repos_directory            directory with repos to scan [default: repos]
    -p --parallel_jobs              number of parallel jobs to run [default: 20]


3. deduplicate_functions:

deduplicate functions using pyspark sql

Usage: `ark_function_parser deduplicate_functions [OPTIONS]`

Options:

    -f --functions_directory        directory to read function parquet files  [default: functions_parquet]
    -o --output_directory           directory to store results [default: results]
    -i --info_directory             directory with repo info [default: github_repo_info]
    -m --memory                     spark.driver.memory [default: 64g]
    -t --tmp_directory              tmp directory in case of small disks [default: /tmp]

4. parse_single_file:

extract functions in output data format from single source code file

Usage: `ark_function_parser parse_single_file [OPTIONS]`

Options:

    -l --lang                       language: arkts [required]
    -p --path_file                  source code file path [required]
    -o --output_file                file to store results [json, parquet], if nothing passed then results are going to print in stdout 


5. parse_jsonl:

extract functions in output data format from jsonl rawtext file

Usage: `ark_function_parser parse_jsonl [OPTIONS]`

Options:

    -l --lang                       language: arkts [required]
    -p --path_jsonl                 source code jsonl path [required]
    -o --output_file                file to store results [json, parquet], if nothing passed then results are going to print in stdout 

6. parse_parquet:

extract functions in output data format from parquet directory (for big datasets)

Usage: `ark_function_parser process_parquet [OPTIONS]`

Options:

    -l --lang                       language: arkts [required]
    -p --parquet_dir                direcrory to read source code parquet files [required]
    -o --output_dir                 directory to store results, if nothing passed then results are going to save in {parquet_dir}/parsed
    -m --spark-memory size          spark.driver.memory [default: 64g]
    -t --tmp directory              tmp directory in case of small disks [default: /tmp]


Usage example:

1. Source file
```shell
ark_function_parser parse_single_file arkts tests/extraction_samples/arkts_test.ets arkts_example.json
```

2. Json rawtext
```shell
ark_function_parser parse_jsonl arkts tests/extraction_samples/arkts_test.ets arkts_example.json
```

3. Parquet rawtext
```shell
ark_function_parser process_parquet -l arkts -p tests/test_fossminer
```

4. GitHub pipeline
```shell
# Use scripts/collect/ for repository collection
python scripts/collect/repo_info.py --source github --output github_repos.csv
python scripts/collect/download_repos.py --source github --csv github_repos.csv

# Parse functions
ark_function_parser enry_scan_languages
ark_function_parser scan_functions
ark_function_parser deduplicate_functions
```

Example: You can also use the library in Python. If you run the code
```python
from ark_function_parser.process import init_parser
func = '''function a(x: number): number {
    return x
}'''.encode('utf-8')
processor = init_parser('arkts') # initialize language parser
tree = processor.PARSER.parse(func) # get source code AST
print(processor.language_parser.get_definition(tree)) # run the process of extract functions and print the result
```


Example: If you want to get all comments from ArkTS code, you can do this:
```python
from ark_function_parser.process import init_parser
from ark_function_parser.parsers.language_parser import traverse_type
func = '''// example comment
// one more comment

function a(x: number): number {
    // inside comment
    return x
}'''.encode('utf-8')
processor = init_parser('arkts') # initialize language parser
tree = processor.PARSER.parse(func) # get source code AST
comments = []
traverse_type(node=tree.root_node, results=comments, kind='comment') # find all nodes with 'comment' type 
print(comments)
```

## Evaluation

Evaluation code: https://github.com/hreyulog/retrieval_eval


## Citation


```bibtex
@misc{he2026arktscodesearchopensourcearktsdataset,
      title={ArkTS-CodeSearch: A Open-Source ArkTS Dataset for Code Retrieval}, 
      author={Yulong He and Artem Ermakov and Sergey Kovalchuk and Artem Aliev and Dmitry Shalymov},
      year={2026},
      eprint={2602.05550},
      archivePrefix={arXiv},
      primaryClass={cs.SE},
      url={https://arxiv.org/abs/2602.05550}, 
}
