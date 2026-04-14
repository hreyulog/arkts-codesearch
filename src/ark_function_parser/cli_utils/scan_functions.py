'''
scan_source_files
scan all repositories in output directory
run enry for each directory and store json with source files in the source_info directory

Usage:
    scan_functions.py [options]

Options:
    -h --help
    -l --language LANGUAGE          Language: arkts
                                    [default: arkts]
    -f --functions directory        directory to store results [default: functions_parquet]
    -e --enry directory             directory with list of files to scan from enry [default: enry_jsons]
    -r --repos directory            directory with repos to scan [default: repos]
    -p --parallel n_jobs            number of parallel jobs to run [default: 20]
'''

import os
import traceback
from pathlib import Path

from joblib import Parallel, delayed
from tqdm import tqdm

from ark_function_parser.cli_utils.extract_functions import process_and_save


def scan_functions(lang, repo_dir, enry_dir, funcs_dir, n_jobs):
    repo_dir=Path(repo_dir)
    # enry_dir=Path(enry_dir)
    funcs_dir=Path(funcs_dir)
    n_jobs = int(n_jobs)
    batch_size = 10000

    if not funcs_dir.exists():
        os.makedirs(funcs_dir)

    downloaded_repos = os.listdir(repo_dir)

    def source_files(repo_name):
        try:
            input_dir_name = repo_dir / repo_name
            # enry_file = enry_dir / (repo_name + ".json")
            output_file = funcs_dir  / (repo_name + '_' + lang + ".parquet")
            if not os.path.exists(output_file):
                process_and_save(lang, path=str(input_dir_name), output_file_name=output_file)
    #        else:
    #            print(f"Already processed {repo_name}")
        except BaseException as error:
            traceback.print_exc()
            print(f'{repo_name} fail: {error}')

    Parallel(n_jobs=n_jobs)(
        delayed(source_files)(name) for name in tqdm(downloaded_repos))
