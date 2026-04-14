'''
下载仓库脚本
支持GitHub和Gitee仓库下载

Usage:
    python download_repos.py --source github --csv github_repos.csv --output repos/
    python download_repos.py --source gitee --csv gitee_repos.csv --output repos/
'''

import os
import csv
import zipfile
import subprocess
import time
from pathlib import Path
from tqdm import tqdm
from joblib import Parallel, delayed

def run_cmd(cmd, timeout):
    try:
        r = subprocess.run(
            cmd,
            shell=True,
            timeout=timeout,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return r.returncode == 0
    except subprocess.TimeoutExpired:
        return False

def download_github_repo(url, output_dir, timeout=360, try_zip=True):
    GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
    
    name = url.rstrip("/").split("/")[-1]
    full_path = Path(output_dir) / name
    
    if full_path.exists():
        return True, url
    
    url_git = url
    if GITHUB_TOKEN:
        url_git = url.replace("https://github.com", f"https://{GITHUB_TOKEN}@github.com")
    url_git += ".git"
    
    for _ in range(2):
        if run_cmd(f"git clone --depth 1 {url_git} {full_path}", timeout):
            return True, url
        time.sleep(2)
    
    if try_zip:
        zip_path = str(full_path) + ".zip"
        if run_cmd(f"wget -q {url}/archive/HEAD.zip -O {zip_path}", timeout):
            try:
                with zipfile.ZipFile(zip_path) as z:
                    z.testzip()
                return True, url
            except:
                pass
    
    if full_path.exists():
        import shutil
        shutil.rmtree(full_path)
    
    return False, url

def download_gitee_repo(url, output_dir, timeout=360, try_zip=True):
    name = url.rstrip("/").split("/")[-1]
    full_path = Path(output_dir) / name
    
    if full_path.exists():
        return True, url
    
    url_git = url + ".git"
    
    for _ in range(2):
        if run_cmd(f"git clone --depth 1 {url_git} {full_path}", timeout):
            return True, url
        time.sleep(2)
    
    if full_path.exists():
        import shutil
        shutil.rmtree(full_path)
    
    return False, url

def download_repos(csv_file, output_dir, source="github", n_jobs=10, timeout=360, try_zip=True):
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    repos = []
    with open(csv_file, newline='', encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row.get("url", "").strip()
            if url:
                repos.append(url)
    
    repos = list(set(repos))
    print(f"Total repos: {len(repos)}")
    
    download_fn = download_github_repo if source == "github" else download_gitee_repo
    
    results = Parallel(n_jobs=n_jobs, prefer="threads")(
        delayed(download_fn)(url, output_dir, timeout, try_zip)
        for url in tqdm(repos)
    )
    
    success = [r[1] for r in results if r[0]]
    failed = [r[1] for r in results if not r[0]]
    
    print(f"\nSuccess: {len(success)}")
    print(f"Failed: {len(failed)}")
    
    if failed:
        with open("failed_repos.txt", "w") as f:
            f.write("\n".join(failed))
        print("Failed list saved to failed_repos.txt")
    
    return success, failed

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Download repositories")
    parser.add_argument("--source", choices=["github", "gitee"], required=True)
    parser.add_argument("--csv", required=True, help="CSV file with repo URLs")
    parser.add_argument("--output", default="repos", help="Output directory")
    parser.add_argument("--parallel", type=int, default=10, help="Parallel jobs")
    parser.add_argument("--timeout", type=int, default=360, help="Timeout in seconds")
    parser.add_argument("--try-zip", action="store_true", help="Try zip download on git failure")
    
    args = parser.parse_args()
    
    download_repos(
        args.csv, 
        args.output, 
        source=args.source,
        n_jobs=args.parallel,
        timeout=args.timeout,
        try_zip=args.try_zip
    )
