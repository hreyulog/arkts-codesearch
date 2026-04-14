'''
deduplicate functions using pyspark sql

Usage:
    deduplicate_functions.py [options]

Options:
    -h --help
    -f --functions directory        directory to read function parquet files  [default: functions_parquet]
    -o --output directory           directory to store results [default: results]
    -i --info directory             directory with repo info [default: github_repo_info]
    -m --spark-memory size          spark.driver.memory [default: 64g]
    -t --tmp directory              tmp directory in case of small disks [default: /tmp]
'''
from pathlib import Path


def deduplicate_functions(info_dir, output_dir, funcs_dir, spark_mem, spark_tmp_dir):
    # args = docopt(__doc__)
    info_dir = str(Path(info_dir).absolute())
    output_dir = str(Path(output_dir).absolute())
    funcs_dir = str(Path(funcs_dir).absolute())
    # spark_mem=args['--spark-memory']
    # spark_tmp_dir=args['--tmp']

    from pyspark.sql import SparkSession
    import findspark
    from pyspark.sql.window import Window
    from pyspark.sql.functions import col, row_number, collect_list

    findspark.init()
    spark = SparkSession.builder.config("spark.local.dir", spark_tmp_dir).config("spark.driver.memory",
                                                                                 spark_mem).appName(
        'deduplicate').getOrCreate()

    func = spark.read.parquet(funcs_dir)
    repo = spark.read.parquet(info_dir) \
        .selectExpr("full_name", "fork", "forks", "stargazers_count", "watchers", "array_join(topics, ' ') as topics")

    df = func.join(repo, func.nwo == repo.full_name, "left").selectExpr(
        # quadrant accept 16 byte UUID as id only
        "substr(function_sha, 0, 32) as function_sha",
        "url",
        "nwo",
        "language",
        "path",
        "identifier",
        "parameters",
        "imports",
        "calls",
        "local_calls",
        "argument_list",
        "return_statement",
        "docstring",
        "docstring_summary",
        "docstring_tokens",
        "function",
        "function_tokens",
        "ast_function",
        "ast_function_tokens",
        "obf_function",
        "obf_function_tokens",
        "topics",
        "forks as forks_count",
        "stargazers_count",
        "watchers")

    windowSpec = Window.partitionBy("function_sha").orderBy(col("stargazers_count").desc())
    windowSpecAgg = Window.partitionBy("function_sha")
    result = df.withColumn("row", row_number().over(windowSpec)) \
        .withColumn("duplicates", collect_list(col("url")).over(windowSpecAgg)) \
        .where(col("row") == 1).drop("row")

    result.write.mode("overwrite").parquet(output_dir)
