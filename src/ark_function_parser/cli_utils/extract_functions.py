"""
Usage:
    parser_cli.py [options] INPUT_FILEPATH

Options:
    -h --help
    -l --language LANGUAGE          Language
    -o --output file                file to store results
    -e --enry file                     list of files to scan from enry
"""
import hashlib
import json
import os
import re
import subprocess
import traceback
import pyarrow as pa
import pyarrow.parquet as pq
from pyspark.sql.functions import udf, explode
from pyspark.sql.session import SparkSession
from pyspark.sql.types import *

from ark_function_parser.language_data import LANGUAGE_METADATA
from ark_function_parser.parsers.language_parser import time_limit, TimeoutException
from ark_function_parser.process import init_parser

ENRY_NAMES = {
    'arkts': 'ArkTS'
}

data_schema = pa.schema([
    pa.field("nwo", pa.string()),
    pa.field("sha", pa.string()),
    pa.field("path", pa.string()),
    pa.field("language", pa.string()),
    pa.field("identifier", pa.string()),
    pa.field("parameters", pa.string()),
    pa.field("argument_list", pa.string()),
    pa.field("return_statement", pa.string()),
    pa.field("imports", pa.list_(pa.string())),
    pa.field("calls", pa.list_(pa.string())),
    pa.field("local_calls", pa.list_(pa.string())),
    pa.field("docstring", pa.string()),
    pa.field("docstring_summary", pa.string()),
    pa.field("docstring_tokens", pa.list_(pa.string())),
    pa.field("function", pa.string()),
    pa.field("function_tokens", pa.list_(pa.string())),
    pa.field("ast_function", pa.string()),
    pa.field("ast_function_tokens", pa.list_(pa.string())),
    pa.field("obf_function", pa.string()),
    pa.field("obf_function_tokens", pa.list_(pa.string())),
    pa.field("url", pa.string()),
    pa.field("function_sha", pa.string())
])


def hash(function):
    """
    calculate unique hash for the function as id for deduplication
    :param function: function Dict
    :return: sha1.hash (docstring + "\n" + function)
    """
    data = function['docstring'] + '\n' + function['function']
    h = hashlib.sha1(data.encode('utf-8')).hexdigest()
    return h


def walk(dir, lang: str):
    ext = LANGUAGE_METADATA[lang]['ext']
    results = []
    for root, _, files in os.walk(dir):
        for f in files:
            if f.endswith('.' + ext):
                results.append(os.path.join(root, f))
    return results


def read_enry(dir, enry_file_name, lang):
    if not os.path.exists(enry_file_name):
        return []
    with open(enry_file_name) as f:
        data = json.load(f)
    files = data.get(ENRY_NAMES[lang], [])
    return [os.path.join(dir, f) for f in files]


def get_repo_info(path):
    # git rev-parse HEAD
    cmd = ['/bin/bash', '-c', f'cd {path} && git rev-parse HEAD']
    sha = subprocess.check_output(cmd).strip().decode('utf-8')
    cmd = ['/bin/bash', '-c', f'cd {path} && git remote get-url origin']
    url = subprocess.check_output(cmd).strip().decode('utf-8')
    if 'gitee' in url:
        repo = re.match('https?://gitee\.com/(.*?)(\.git)?$', url).group(1)
    else:
        repo = re.match('http(.+?)github\.com/(.*)(\.git)?$', url).group(2)

    return (repo, sha)


def process_dee(processor, dir, lang, enry_file_name):
    # Process dependees (libraries) to get function implementations
    indexes = []
    if enry_file_name is None:
        files = walk(dir, lang)
    else:
        files = read_enry(dir, enry_file_name, lang)

    if not files:
        return indexes

    # files = glob.iglob(dir + '/**/*.{}'.format(ext), recursive=True)
    nwo, sha = get_repo_info(dir)

    for f in files:
        try:
            with time_limit(10):
                definitions = processor.get_function_definitions(f)
                if definitions is None:
                    continue
                    # cut dir name
                dir = str(dir)
                dir_name_len = len(dir)
                path = f[dir_name_len + 1:]
                _, _, functions = definitions
                indexes.extend((processor.extract_function_data(func, nwo, path, sha) for func in functions if
                                len(func['function_tokens']) > 1))
        except TimeoutException as e:
            print(e, "\nCheck the source file:", f)
        except RecursionError as e:
            print(e, "\nCheck the source file:", f)
        except Exception as e:
            print(e, "Can't parse the source file:", f)

    return indexes


def process(path, lang, enry_file_name=None):
    processor = init_parser(lang)
    if os.path.isdir(path):
        functions = process_dee(processor, path, lang, enry_file_name)
    else:
        functions = processor.process_single_file(path)
    if functions:
        # add function hash
        for function in functions:
            function['function_sha'] = hash(function)

    return functions


def process_jsonl(lang, jsonl_array):
    processor = init_parser(lang)
    result = []
    for source in jsonl_array:
        try:
            with time_limit(10):
                file_name = source["file_name"]
                content = source["raw_text"]
                tree = processor.PARSER.parse(content.encode('utf-8'))
                functions = processor.language_parser.get_definition(tree)
                if functions:
                    for func in functions:
                        if len(func['function_tokens']) > 1:
                            e = processor.extract_function_data(func, '', file_name, '')
                            e['function_sha'] = hash(e)
                            result.append(e)
        except TimeoutException as e:
            print(e, "\nCheck the source file:", file_name)
        except RecursionError as e:
            print(e, "\nCheck the source file:", file_name)
        except Exception as e:
            print(e, "Can't parse the source file:", file_name)

    return result


def process_parquets(lang, path, output_path, spark_mem, spark_tmp_dir):
    spark = SparkSession.builder.config(
        "spark.local.dir", spark_tmp_dir).config(
        "spark.driver.memory", spark_mem).config(
        "spark.sql.shuffle.partitions", 10000).config(
        "spark.master", "local[10]").appName(
        "process parquet").getOrCreate()
    if output_path is None:
        output_path = f"{path}/parsed"
    schema = ArrayType(
        StructType(
            [StructField('type', StringType()),
             StructField('identifier', StringType()),
             StructField('parameters', StringType()),
             StructField('imports', ArrayType(StringType())),
             StructField('calls', ArrayType(StringType())),
             StructField('local_calls', ArrayType(StringType())),
             StructField("function", StringType()),
             StructField("function_tokens", ArrayType(StringType())),
             StructField("ast_function", StringType()),
             StructField("ast_function_tokens", ArrayType(StringType())),
             StructField("obf_function", StringType()),
             StructField("obf_function_tokens", ArrayType(StringType())),
             StructField("docstring", StringType()),
             StructField("docstring_summary", StringType()),
             StructField("start_point", StringType()),
             StructField("end_point", StringType()),
             StructField("language", StringType())]
        )
    )

    errors = {
        'Timeout': 0,
        'Recursion': 0,
        'Other': 0
    }

    def process_raw_text(raw_text, file_name):
        processor = init_parser(lang)
        try:
            with time_limit(10):
                code = raw_text.encode('utf-8')
                if len(code) > 2 ** 20:
                    return
                tree = processor.PARSER.parse(str(raw_text).encode('utf-8'))
                results = processor.language_parser.get_definition(tree)
                for r in results:
                    r['language'] = lang
                return results
        except TimeoutException as e:
            errors['Timeout'] += 1
            print(e, "\nCheck the source file:", file_name)
            return
        except RecursionError as e:
            errors['Recursion'] += 1
            print(e, "\nCheck the source file:", file_name)
            return
        except Exception as e:
            errors['Other'] = 1
            print(e, "Can't parse the source file:", file_name)
            return

    process_udf = udf(process_raw_text, schema)
    df = spark.read.parquet(path)
    s = df.count()
    df = df.coalesce(max(s // 10000, 1))
    result = process_udf(df.content, df.max_stars_repo_path)
    df2 = df.withColumn('data', explode(result)).select('data.*')
    df2.write.parquet(output_path, mode="append")


def process_jsongz(lang, path, output_path, spark_mem, spark_tmp_dir):
    list_file=os.listdir(path)
    spark = SparkSession.builder.config(
        "spark.local.dir", spark_tmp_dir).config(
        "spark.driver.memory", spark_mem).config(
        "spark.sql.shuffle.partitions", 10000).config(
        "spark.master", "local[10]").config("spark.sql.debug.maxToStringFields", 1000).appName(
        "process parquet").getOrCreate()
    if output_path is None:
        output_path = f"{path}/parsed"
    have_files=os.listdir(output_path)
    list_file.remove('_SUCCESS')
    for file in have_files:
        list_file.remove(f"{file.split('.')[0]}.json.gz") 
    schema = ArrayType(StructType(
            [StructField('type', StringType()),
             StructField('identifier', StringType()),
             StructField('parameters', StringType()),
             StructField('imports', ArrayType(StringType())),
             StructField('calls', ArrayType(StringType())),
             StructField('local_calls', ArrayType(StringType())),
             StructField("function", StringType()),
             StructField("function_tokens", ArrayType(StringType())),
             StructField("ast_function", StringType()),
             StructField("ast_function_tokens", ArrayType(StringType())),
             StructField("obf_function", StringType()),
             StructField("obf_function_tokens", ArrayType(StringType())),
             StructField("docstring", StringType()),
             StructField("docstring_summary", StringType()),
             StructField("start_point", StringType()),
             StructField("end_point", StringType()),
             StructField("language", StringType())]
        )
    )

    errors = {
        'Timeout': 0,
        'Recursion': 0,
        'Other': 0
    }

    def process_raw_text(raw_text, file_name):
        processor = init_parser(lang)
        try:
            with time_limit(10):
                code = raw_text.encode('utf-8')
                if len(code) > 2 ** 15:
                    return
                tree = processor.PARSER.parse(str(raw_text).encode('utf-8'))
                results = processor.language_parser.get_definition(tree)
                for r in results:
                    r['language'] = lang
                return results
        except TimeoutException as e:
            errors['Timeout'] += 1
            print(e, "\nCheck the source file:", file_name)
            return
        except RecursionError as e:
            errors['Recursion'] += 1
            print(e, "\nCheck the source file:", file_name)
            return
        except Exception as e:
            errors['Other'] = 1
            print(e, "Can't parse the source file:", file_name)
            return
    process_udf = udf(process_raw_text, schema)
    df=spark.read.json(path)
    result = process_udf(df.content, df.path)
    df2 = df.withColumn('data', explode(result)).select('data.*')
    write_file_path=f"{output_path}"
    df2.write.parquet(write_file_path, mode="overwrite")
        


def process_and_save(lang, jsonl_array=None, path=None, output_file_name=None, enry_file_name=None):
    assert not (jsonl_array is None and path is None), "either jsonl or path to the directory should be passed"
    if jsonl_array is not None:
        functions = process_jsonl(lang, jsonl_array)
    else:
        functions = process(path=path, lang=lang, enry_file_name=enry_file_name)
    if output_file_name is not None:
        if str(output_file_name).endswith(".json"):
            with open(output_file_name, "w") as fp:
                json.dump(functions, fp, indent=2)
        else:
            table = pa.Table.from_pylist(functions, schema=data_schema)
            pq.write_table(table, output_file_name, compression='GZIP')
    else:
        print(json.dumps(functions, indent=2))
        


# if __name__ == '__main__':
#     args = docopt(__doc__)
#
#     path = args['INPUT_FILEPATH']
#     lang = args['--language'].lower()
#     output_file_name = args['--output']
#     enry_file_name = args['--enry']
#     process_and_save(lang=lang, path=path, output_file_name=output_file_name, enry_file_name=enry_file_name)
