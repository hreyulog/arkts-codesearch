'''
许可证检查脚本
支持GitHub和Gitee仓库许可证查询

Usage:
    python license_check.py --source github --csv github_repos.csv --output github_licenses.jsonl
    python license_check.py --source gitee --csv gitee_repos.csv --output gitee_licenses.jsonl
'''

import os
import csv
import json
import time
import requests

GITHUB_API_BASE = "https://api.github.com"
GITEE_API_BASE = "https://gitee.com/api/v5"

ALLOWED_LICENSES = {
    '0BSD', 'ZLIB', 'ISC', 'BSD-3-CLAUSE', 'BSD-2-CLAUSE',
    'APACHE-2.0', 'Apache-2.0', 'MIT',
    'LGPL-3.0', 'LGPL-2.1',
    'EPL-1.0', 'MULANPSL-2.0', 'MulanPSL-2.0',
    'CC-BY-4.0', 'MPL-2.0', 'BSD-3-Clause', 'Unlicense'
}

def get_github_license(owner, repo):
    USER = os.environ.get("GITHUB_USER", "")
    TOKEN = os.environ.get("GITHUB_TOKEN", "")
    
    repo = repo.replace(".git", "")
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
    
    try:
        r = requests.get(url, timeout=10, auth=(USER, TOKEN) if TOKEN else None)
        if r.status_code == 200:
            data = r.json()
            lic = data.get("license")
            if lic and lic.get("spdx_id"):
                return lic["spdx_id"]
    except Exception as e:
        print(f"GitHub API error: {e}")
    return None

def get_gitee_license(owner, repo):
    TOKEN = os.environ.get("GITEE_TOKEN", "")
    repo = repo.replace("_arkts", "").replace(".git", "")
    
    url = f"{GITEE_API_BASE}/repos/{owner}/{repo}/license"
    params = {"access_token": TOKEN} if TOKEN else {}
    
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            lic = data.get("license") or data.get("spdx")
            if lic:
                return lic.upper()
    except Exception as e:
        print(f"Gitee API error: {e}")
    return None

def check_licenses(csv_file, output_file, source="github"):
    results = []
    
    with open(csv_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    for row in tqdm(rows, desc=f"Checking {source} licenses"):
        repo_name = row.get("filename") or row.get("full_name", "")
        
        if source == "github":
            if "/" in repo_name:
                owner, repo = repo_name.split("/", 1)
            else:
                continue
            lic = get_github_license(owner, repo)
        else:
            if "##" in repo_name:
                owner, repo = repo_name.split("##", 1)
            elif "/" in repo_name:
                owner, repo = repo_name.split("/", 1)
            else:
                continue
            lic = get_gitee_license(owner, repo)
        
        results.append({
            "source": source,
            "repo": repo_name,
            "license": lic,
            "allowed": lic in ALLOWED_LICENSES if lic else False
        })
        
        time.sleep(0.2)
    
    with open(output_file, "w", encoding="utf-8") as f:
        for entry in results:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    print(f"Saved {len(results)} results to {output_file}")
    allowed_count = sum(1 for r in results if r["allowed"])
    print(f"Allowed licenses: {allowed_count}/{len(results)}")
    
    return results

if __name__ == "__main__":
    import argparse
    from tqdm import tqdm
    
    parser = argparse.ArgumentParser(description="Check repository licenses")
    parser.add_argument("--source", choices=["github", "gitee"], required=True)
    parser.add_argument("--csv", required=True, help="CSV file with repo names")
    parser.add_argument("--output", required=True, help="Output JSONL file")
    
    args = parser.parse_args()
    
    check_licenses(args.csv, args.output, args.source)
