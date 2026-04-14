import ark_function_parser

from git import Git, Repo
from pathlib import Path
from tree_sitter import Language

_GRAMMARs = {
    "arkts":("https://github.com/Million-mo/tree-sitter-arkts.git",'tree-sitter-arkts','')
}

def main():
    print(str(Path(ark_function_parser.__path__[0]) / "cli_utils/tree-sitter-languages.so"))
    languages = []
    for lang, (url, dir, tag) in _GRAMMARs.items():
        repo_dir = Path(ark_function_parser.__path__[0]) / dir
        if not repo_dir.exists():
            repo = Repo.clone_from(url, repo_dir)
        g = Git(str(repo_dir))
        if dir!='tree-sitter-arkts':
            g.checkout(tag)
        if dir == 'tree-sitter-typescript':
            languages.append(str(repo_dir) + '/tsx')
            languages.append(str(repo_dir) + '/typescript')
        else:
            languages.append(str(repo_dir))
    
    Language.build_library(
        # Store the library in the directory
        str(Path(ark_function_parser.__path__[0]) / "cli_utils/tree-sitter-languages.so"),
        # Include one or more languages
        languages
    )

if __name__ == '__main__':
  main()
