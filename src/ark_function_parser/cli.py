import json
import click
import pyarrow as pa
import pyarrow.parquet as pq

from ark_function_parser.cli_utils.deduplicate_functions import deduplicate_functions
from ark_function_parser.cli_utils.enry_scan_languages import enry_scan_languages
from ark_function_parser.cli_utils.extract_functions import process_parquets, process_jsonl, process, data_schema,process_jsongz
from ark_function_parser.cli_utils.scan_functions import scan_functions


def save(functions, output_file):
    if output_file is not None:
        if str(output_file).endswith(".json"):
            with open(output_file, "w") as fp:
                json.dump(functions, fp, indent=2)
        else:
            table = pa.Table.from_pylist(functions, schema=data_schema)
            pq.write_table(table, output_file, compression='GZIP')
    else:
        print(json.dumps(functions, indent=2))


@click.group()
def command_line():
    pass


@click.command(name="parse_single_file")
@click.option("-l", "--lang", required=True)
@click.option("-p", "--path_file", required=True)
@click.option("-o", "--output_file", required=False)
def parse_single_sile(lang: str, file_path: str, output_file: str):
    assert lang in ['arkts'], "Unknown language"
    functions = process(file_path, lang)
    save(functions, output_file)


@click.command(name="parse_jsonl")
@click.option("-l", "--lang", required=True)
@click.option("-p", "--path_jsonl", required=True)
@click.option("-o", "--output_file", required=False)
def parse_jsonl(lang: str, path_jsonl: str, output_file: str):
    assert lang in ['arkts'], "Unknown language"
    with open(path_jsonl) as f:
        data = [json.loads(line) for line in f]
    functions = process_jsonl(lang, data)
    save(functions, output_file)


@click.command(name="parse_jsongz")
@click.option("-l", "--lang", required=True)
@click.option("-p", "--parquet_dir", required=True)
@click.option("-o", "--output_dir", default=None, required=False)
def parse_jsongz(lang: str, parquet_dir: str, output_dir: str, memory: str, tmp_directory):
    assert lang in ['arkts'], "Unknown language"
    process_jsongz(lang, parquet_dir, output_dir, memory, tmp_directory)


@click.command(name="process_parquet")
@click.option("-l", "--lang", required=True)
@click.option("-p", "--parquet_dir", required=True)
@click.option("-o", "--output_dir", default=None, required=False)
@click.option("-m", "--memory", default="64g")
@click.option("-t", "--tmp_directory", default="/tmp")
def parse_parquet_dir(lang: str, parquet_dir: str, output_dir: str, memory: str, tmp_directory):
    assert lang in ['arkts'], "Unknown language"
    process_parquets(lang, parquet_dir, output_dir, memory, tmp_directory)


@click.command(name="scan_functions")
@click.option("-l", "--lang", default="arkts")
@click.option("-f", "--functions_directory", default="functions_parquet")
@click.option("-e", "--enry_directory", default="enry_jsons")
@click.option("-r", "--repos_directory", default="repos")
@click.option("-p", "--parallel_jobs", default=20)
def scan_funcs(lang, functions_directory, enry_directory, repos_directory, parallel_jobs):
    assert lang in ['arkts'], "Unknown language"
    scan_functions(lang, repos_directory, enry_directory, functions_directory, parallel_jobs)


@click.command(name="deduplicate_functions")
@click.option("-f", "--functions", default="functions_parquet")
@click.option("-o", "--output_directory", default="results")
@click.option("-i", "--info_directory", default="github_repo_info")
@click.option("-m", "--memory", default="64g")
@click.option("-t", "--tmp_directory", default="/tmp")
def dedup_funcs(functions, output_directory, info_directory, memory, tmp_directory):
    deduplicate_functions(info_directory, output_directory, functions, memory, tmp_directory)

@click.command(name="enry_scan_languages")
@click.option("-e", "--enry_directory", default="enry_jsons")
@click.option("-r", "--repos_directory", default="repos")
@click.option("-p", "--parallel_jobs", default=20)
def enry_scan(enry_directory, repos_directory, parallel_jobs):
    enry_scan_languages(repos_directory, enry_directory, parallel_jobs)

command_line.add_command(parse_single_sile)
command_line.add_command(parse_jsonl)
command_line.add_command(parse_parquet_dir)
command_line.add_command(scan_funcs)
command_line.add_command(enry_scan)
command_line.add_command(dedup_funcs)
command_line.add_command(parse_jsongz)
