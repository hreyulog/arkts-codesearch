import re
import signal
from abc import ABC, abstractmethod, abstractproperty
from contextlib import contextmanager
from typing import List, Dict, Any, Set, Optional

DOCSTRING_REGEX_TOKENIZER = re.compile(
    r"[^\s,'\"`.():\[\]=*;>{\}+-/\\]+|\\+|\.+|\(\)|{\}|\[\]|\(+|\)+|:+|\[+|\]+|{+|\}+|=+|\*+|;+|>+|\++|-+|/+")


class TimeoutException(Exception): pass


@contextmanager
def time_limit(seconds):
    """
    Timeout in seconds for any process; abort the process when time is up
    :param seconds: seconds to work
    :return:
    """
    def signal_handler(signum, frame):
        raise TimeoutException("Timed out!")

    signal.signal(signal.SIGALRM, signal_handler)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


def tokenize_docstring(docstring: str) -> List[str]:
    """
    Split docstring into tokens
    """
    return [t for t in DOCSTRING_REGEX_TOKENIZER.findall(docstring) if t is not None and len(t) > 0]


def tokenize_code(node, nodes_to_exclude=None) -> List:
    """
    Split source code that node contains into tokens
    :param node: node contains code which have to be splatted
    :param nodes_to_exclude: list of nodes than won't be added to result
    :return: list of code tokens
    """
    if nodes_to_exclude is None:
        nodes_to_exclude = []
    tokens = []
    traverse(node, tokens)
    return [token.text.decode() for token in tokens if
            nodes_to_exclude is None or token not in nodes_to_exclude]


def traverse(node, results: List) -> None:
    """
    Recursive search for all strings in subtree
    :param node: node from which subtree starts
    :param results: list to add founded nodes
    """
    if node.type == 'string':
        results.append(node)
        return
    for n in node.children:
        traverse(n, results)
    if not node.children:
        results.append(node)


def traverse_comments(node, results: List) -> None:
    """
    Recursive search for all comments in subtree
    :param node: node from which subtree starts
    :param results: list to add founded nodes
    """
    if node.type in ['comment', 'line_comment', 'block_comment']:
        results.append(node)
        return
    for n in node.children:
        traverse(n, results)
    if not node.children:
        results.append(node)


def nodes_are_equal(n1, n2):
    """
    Check for nodes equality
    :param n1: first node to compare
    :param n2: second node to compare
    :return: True is nodes are equal, else False
    """
    return n1.type == n2.type and n1.start_point == n2.start_point and n1.end_point == n2.end_point and n1.text == n2.text


def traverse_type(node, results: List, kind: str) -> None:
    """
    Recursive search for all nodes with passed kind in subtree
    :param node: node from which subtree starts
    :param results: list to add founded nodes
    :param kind: node type to search
    """
    if node.type == kind:
        results.append(node)
    if not node.children:
        return
    for n in node.children:
        traverse_type(n, results, kind)


def traverse_obf(node, results, identifier_type, blacklist):
    """
    Recursive search for all identifiers in subtree that will be obfuscated
    :param node: node from which subtree starts
    :param results: list to add founded nodes
    :param identifier_type: identifier type to search
    :param blacklist: list of nodes than won't be added to result
    """
    if node.type == identifier_type:
        if node in blacklist:
            return
        elif node.prev_sibling is not None:
            if node.prev_sibling.text.decode() != '.':
                results.append(node)
        else:
            results.append(node)
    if not node.children:
        return
    for n in node.children:
        traverse_obf(n, results, identifier_type, blacklist)


def ast_to_sequence(node, mappings, blacklist=None):
    """
    Convert the code in subtree to code with AST tokens
    :param node: node from which subtree starts
    :param mappings: map of AST types which should be converted to another interpretation in result list
    :param blacklist: list of nodes than won't be added to result
    :return: list of AST and code tokens
    """
    if blacklist is None:
        blacklist = []
    sequences = []
    if node in blacklist:
        pass
    else:
        if len(node.children) == 0 or node.type == 'string':
            sequences.append(node.text.decode())
        else:
            if node.type in mappings.keys():
                sequences.append(f'AST#{mappings[node.type]}#Left')
            else:
                sequences.append(f'AST#{node.type}#Left')
            for c in node.children:
                sequences.extend(ast_to_sequence(c, mappings, blacklist))
            if node.type in mappings.keys():
                sequences.append(f'AST#{mappings[node.type]}#Right')
            else:
                sequences.append(f'AST#{node.type}#Right')
    return sequences


def clean_comments(node):
    """
    Clean comments in subtree.
    :param node: node from which subtree starts
    :return: function without comments
    """
    results = []
    traverse_comments(node, results)
    func = node.text.decode()
    for comm in results:
        func = func.replace(comm.text.decode(), '')
    return func


class LanguageParser(ABC):
    @staticmethod
    @abstractmethod
    def get_definition(tree) -> List[Dict[str, Any]]:
        pass

    @staticmethod
    @abstractmethod
    def get_class_metadata(class_node):
        pass

    @staticmethod
    @abstractmethod
    def get_function_metadata(function_node, local_functions, imports: Dict[str, List[str]]) -> Dict[str, Any]:
        pass

    @staticmethod
    @abstractmethod
    def get_context(tree):
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def get_calls(tree):
        raise NotImplementedError
