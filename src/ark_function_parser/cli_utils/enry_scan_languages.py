'''
scan_source_files
scan all repositories in output directory
run enry for each directory and store json with source files in the source_info directory

Usage:
    enry_scan_languages.py [options]

Options:
    -h --help
    -e --enry directory             directory with list of files to scan from enry [default: enry_jsons]
    -r --repos directory            directory with repos to scan [default: repos]
    -p --parallel n_jobs            number of parallel jobs to run [default: 20]

'''

import os
import sys
from pathlib import Path
import json

from joblib import Parallel, delayed
from tqdm import tqdm


def enry_scan_languages(repo_dir, output_dir, n_jobs):

# args = docopt(__doc__)
    repo_dir=Path(repo_dir)
    output_dir=Path(output_dir)
    n_jobs = int(n_jobs)

    exec_path = Path(os.path.dirname(__file__)) / 'enry'

    downloaded_repos = os.listdir(repo_dir)

    if not output_dir.exists():
        os.makedirs(output_dir)

    def source_files(repo_name):
        input_dir_name = repo_dir / repo_name
        # print(input_dir_name)
        output_file = output_dir / (repo_name + ".json")
        if not os.path.exists(output_file) :
            #print (f"Start {repo_name}")
            ret = os.system(f'{exec_path} --json {input_dir_name} > {output_file}')
            #print (f"Done {repo_name} {ret:04x}")
        #else:
            #print(f"Already processed {repo}")
        if str(input_dir_name).split('.')[-1]=='ets':
            try:
                with open(output_file,"r",encoding='utf-8') as reader:
                    enry_dict=json.load(reader)
                    enry_dict['language']='arkts'
                with open(output_file,"w",encoding='utf-8') as writer:
                    json.dump(enry_dict,writer)
            except:
                return
    Parallel(n_jobs=n_jobs, prefer="threads")(
        delayed(source_files)(name) for name in tqdm(downloaded_repos))

