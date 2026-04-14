"""
Usage:
    process.py [options] INPUT_DIR OUTPUT_DIR

Options:
    -h --help
    --language LANGUAGE             Language
    --processes PROCESSES           # of processes to use [default: 16]
    --license-filter FILE           License metadata to filter, every row contains [nwo, license, language, score] (e.g. ['pandas-dev/pandas', 'bsd-3-clause', 'Python', 0.9997])
    --tree-sitter-build FILE        [default: /src/build/py-tree-sitter-languages.so]
"""
import os
from os import PathLike
from typing import Optional, Tuple, Type, List, Dict, Any, Union

from tree_sitter import Language, Parser

from ark_function_parser.language_data import LANGUAGE_METADATA
from ark_function_parser.parsers.language_parser import LanguageParser, tokenize_docstring, time_limit, \
    TimeoutException
from ark_function_parser.utils import download, get_sha, remap_nwo, walk

lib_path = os.path.dirname(__file__) + '/cli_utils/tree-sitter-languages.so'

class DataProcessor:

    PARSER = Parser()

    def __init__(self, language: str, language_parser: Type[LanguageParser]):
        self.language = language
        self.language_parser = language_parser

    def process_dee(self, nwo, ext) -> List[Dict[str, Any]]:
        # Process dependees (libraries) to get function implementations
        indexes = []
        _, nwo = remap_nwo(nwo)
        if nwo is None:
            return indexes

        tmp_dir = download(nwo)
        files = walk(tmp_dir, ext)
        # files = glob.iglob(tmp_dir.name + '/**/*.{}'.format(ext), recursive=True)
        sha = None

        for f in files:
            definitions = self.get_function_definitions(f)
            if definitions is None:
                continue
            if sha is None:
                sha = get_sha(tmp_dir, nwo)

            nwo, path, functions = definitions
            indexes.extend((self.extract_function_data(func, nwo, path, sha) for func in functions if len(func['function_tokens']) > 1))
        return indexes

    def process_dent(self, nwo, ext, library_candidates) -> Tuple[List[Dict[str, Any]], List[Tuple[str, str]]]:
        # Process dependents (applications) to get function calls
        dents = []
        edges = []
        _, nwo = remap_nwo(nwo)
        if nwo is None:
            return dents, edges

        tmp_dir = download(nwo)
        files = walk(tmp_dir, ext)
        sha = None

        for f in files:
            context_and_calls = self.get_context_and_function_calls(f)
            if context_and_calls is None:
                continue
            if sha is None:
                sha = get_sha(tmp_dir, nwo)

            nwo, path, context, calls = context_and_calls
            libraries = []
            for cxt in context:
                if type(cxt) == dict:
                    libraries.extend([v.split('.')[0] for v in cxt.values()])
                elif type(cxt) == list:
                    libraries.extend(cxt)

            match_scopes = {}
            for cxt in set(libraries):
                if cxt in library_candidates:
                    match_scopes[cxt] = library_candidates[cxt]

            for call in calls:
                for depended_library_name, dependend_library_functions in match_scopes.items():
                    for depended_library_function in dependend_library_functions:
                        # Other potential filters: len(call['identifier']) > 6 or len(call['identifier'].split('_')) > 1
                        if (call['identifier'] not in self.language_parser.STOPWORDS and
                            ((depended_library_function['identifier'].split('.')[-1] == '__init__' and
                              call['identifier'] == depended_library_function['identifier'].split('.')[0]) or
                             ((len(call['identifier']) > 9 or
                               (not call['identifier'].startswith('_') and len(call['identifier'].split('_')) > 1)) and
                              call['identifier'] == depended_library_function['identifier'])
                            )):
                            dent = {
                                'nwo': nwo,
                                'sha': sha,
                                'path': path,
                                'language': self.language,
                                'identifier': call['identifier'],
                                'argument_list': call['argument_list'],
                                'url': 'https://github.com/{}/blob/{}/{}#L{}-L{}'.format(nwo, sha, path,
                                                                                         call['start_point'][0] + 1,
                                                                                         call['end_point'][0] + 1)
                            }
                            dents.append(dent)
                            edges.append((dent['url'], depended_library_function['url']))
        return dents, edges

    def process_single_file(self, filepath: PathLike) -> Union[List[Dict[str, Any]], None]:
        try:
            with time_limit(10):
                definitions = self.get_function_definitions(filepath)
                if definitions is None:
                    return []
                _, _, functions = definitions

                return [self.extract_function_data(func, '', '', '') for func in functions if len(func['function_tokens']) > 1]
        except TimeoutException as e:
            print(e, "\nCheck the source file:", filepath)
            return
        except RecursionError as e:
            print(e, "\nCheck the source file:", filepath)
            return
        except Exception as e:
            print(e, "Can't parse the source file:", filepath)
            return

    def extract_function_data(self, function: Dict[str, Any], nwo, path: str, sha: str):
        return {
            'nwo': nwo,
            'sha': sha,
            'path': path,
            'language': self.language,
            'identifier': function['identifier'],
            'parameters': function.get('parameters', ''),
            'imports': function.get('imports', []),
            'calls': function.get('calls', []),
            'local_calls': function.get('local_calls', []),
            'argument_list': function.get('argument_list', ''),
            'return_statement': function.get('return_statement', ''),
            'docstring': function['docstring'].strip(),
            'docstring_summary': function['docstring_summary'].strip(),
            'docstring_tokens': tokenize_docstring(function['docstring_summary']),
            'function': function['function'].strip(),
            'function_tokens': function['function_tokens'],
            'ast_function': function['ast_function'].strip(),
            'ast_function_tokens': function['ast_function_tokens'],
            'obf_function': function['obf_function'].strip(),
            'obf_function_tokens': function['obf_function_tokens'],
            'url': 'https://github.com/{}/blob/{}/{}#L{}-L{}'.format(nwo, sha, path, function['start_point'][0] + 1,
                                                                     function['end_point'][0] + 1)
        }

    def get_context_and_function_calls(self, filepath: str) -> Optional[Tuple[str, str, List, List]]:
        nwo = '/'.join(filepath.split('/')[3:5])
        path = '/'.join(filepath.split('/')[5:])
        if any(fp in path.lower() for fp in self.language_parser.FILTER_PATHS):
            return None
        try:
            with open(filepath) as source_code:
                blob = source_code.read()
            tree = DataProcessor.PARSER.parse(blob.encode('utf-8'))
            return nwo, path, self.language_parser.get_context(tree), self.language_parser.get_calls(tree)
        except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError, ValueError, OSError):
            return None

    def get_function_definitions(self, filepath: str) -> Optional[Tuple[str, str, List]]:
        nwo = '/'.join(filepath.split('/')[3:5])
        path = '/'.join(filepath.split('/')[5:])
        if any(fp in path.lower() for fp in self.language_parser.FILTER_PATHS):
            return None
        try:
            with open(filepath) as source_code:
                blob = source_code.read()
            tree = DataProcessor.PARSER.parse(blob.encode())
            return nwo, path, self.language_parser.get_definition(tree)
        except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError, ValueError, OSError):
            return None


def init_parser(lang: str = "arkts") -> DataProcessor:
    if lang =='arkts':
        import tree_sitter_arkts as arkts
        ARKTS_LANGUAGE = Language(arkts.language())
        DataProcessor.PARSER.language = ARKTS_LANGUAGE

    proc = DataProcessor(language=lang,
                              language_parser=LANGUAGE_METADATA[lang]['language_parser'])
    return proc
