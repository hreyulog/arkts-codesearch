'''
仓库信息收集脚本
支持GitHub和Gitee仓库信息爬取

Usage:
    python repo_info.py --source github --output github_repos.csv
    python repo_info.py --source gitee --output gitee_repos.csv --pages 100
'''

import os
import json
import time
import math
import pickle
import requests
from bs4 import BeautifulSoup
import csv
from pathlib import Path

def get_github_repo_info(keyword: str = "ArkTS", output_dir: str = "repo_info"):
    os.makedirs(output_dir, exist_ok=True)
    
    USER = os.environ.get("GITHUB_USER", "")
    TOKEN = os.environ.get("GITHUB_TOKEN", "")
    
    if not TOKEN:
        print("Warning: GITHUB_TOKEN not set. API rate limits will apply.")
    
    repo_list = []
    full_info_list = []
    
    def save_jsonl(lower_bound, upper_bound):
        nonlocal full_info_list
        file_name = f"{output_dir}/repo_{lower_bound}_{upper_bound}.json"
        i = 1
        while os.path.exists(file_name):
            file_name = f"{output_dir}/repo_{lower_bound}_{upper_bound}_{i}.json"
            i += 1
        
        with open(file_name, 'w', encoding='utf8') as outfile:
            for entry in full_info_list:
                json.dump(entry, outfile, ensure_ascii=False)
                outfile.write('\n')
        full_info_list = []
    
    def get_request(page=1):
        r = requests.get(
            f'https://api.github.com/search/repositories?q={keyword}&per_page=100&page={page}',
            auth=(USER, TOKEN) if TOKEN else None
        )
        
        if r.status_code == 403:
            print('API rate limit exceeded.')
            return None
        elif r.status_code == 422:
            return False
        
        return r
    
    for page in range(1, 11):
        r = get_request(page)
        if r is None or r is False:
            break
        
        for repository in r.json()['items']:
            full_info_list.append(repository)
            repo_list.append((
                repository['full_name'],
                repository['stargazers_count'],
                repository['language']
            ))
        
        n_results = r.json()['total_count']
        n_query_pages = min(math.ceil(n_results/100), 10)
        
        if page >= n_query_pages:
            break
        
        time.sleep(2)
    
    save_jsonl(0, 0)
    
    return repo_list

def get_gitee_repo_info(max_pages: int = 100, output_dir: str = "gitee_harmony_repos"):
    os.makedirs(output_dir, exist_ok=True)
    
    BASE_URL = "https://gitee.com/explore/harmony"
    HEADERS = {"User-Agent": "Mozilla/5.0"}
    
    all_repos = []
    
    for page in range(1, max_pages + 1):
        print(f"Fetching page {page}...")
        r = requests.get(BASE_URL, params={"order": "starred", "page": page}, headers=HEADERS)
        
        if r.status_code != 200:
            print(f"Failed: {r.status_code}")
            break
        
        soup = BeautifulSoup(r.text, "html.parser")
        items = soup.select("div.item")
        
        if not items:
            break
        
        for item in items:
            name_tag = item.select_one("h3 > a.title.project-namespace-path")
            if not name_tag:
                continue
            
            repos_entry = {
                "full_name": name_tag.get("title", "").strip(),
                "url": "https://gitee.com" + name_tag.get("href", "").strip(),
                "stars": int(item.select_one("div.stars-count").get("data-count", 0)) if item.select_one("div.stars-count") else 0,
                "description": item.select_one("div.project-desc").get("title", "").strip() if item.select_one("div.project-desc") else "",
                "language": item.select_one("a.project-language").get("title", "").strip() if item.select_one("a.project-language") else ""
            }
            all_repos.append(repos_entry)
        
        with open(f"{output_dir}/harmony_page_{page}.json", "w", encoding="utf-8") as f:
            json.dump([r for r in all_repos[len(all_repos)-len(items):]], f, ensure_ascii=False, indent=2)
        
        time.sleep(1)
    
    return all_repos

def save_to_csv(repo_list, output_file, fields=None):
    if not fields:
        fields = ["full_name", "stars", "language", "url"] if repo_list and isinstance(repo_list[0], dict) else None
    
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        if isinstance(repo_list[0], tuple):
            writer = csv.writer(f)
            for repo in repo_list:
                writer.writerow(repo)
        else:
            writer = csv.DictWriter(f, fieldnames=fields or list(repo_list[0].keys()))
            writer.writeheader()
            writer.writerows(repo_list)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Collect repository information")
    parser.add_argument("--source", choices=["github", "gitee"], required=True)
    parser.add_argument("--output", default=None)
    parser.add_argument("--keyword", default="ArkTS", help="Search keyword for GitHub")
    parser.add_argument("--pages", type=int, default=100, help="Pages to crawl for Gitee")
    
    args = parser.parse_args()
    
    if args.source == "github":
        repos = get_github_repo_info(keyword=args.keyword)
        output = args.output or "github_repos.csv"
    else:
        repos = get_gitee_repo_info(max_pages=args.pages)
        output = args.output or "gitee_repos.csv"
    
    save_to_csv(repos, output)
    print(f"Saved {len(repos)} repos to {output}")
