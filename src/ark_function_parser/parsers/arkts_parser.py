from typing import List, Dict, Any

from ark_function_parser.parsers.commentutils import get_docstring_summary, strip_c_style_comment_delimiters, \
    match_license_comment
from ark_function_parser.parsers.language_parser import LanguageParser, tokenize_code, traverse_type, \
    time_limit, ast_to_sequence, traverse_obf, traverse


class ArkTSParser(LanguageParser):
    """
    Parser for ArkTS/TypeScript source code
    """

    FILTER_PATHS = ('test', 'node_modules')

    BLACKLISTED_FUNCTION_NAMES = {'toString', 'toLocaleString', 'valueOf'}

    AST_MAPPINGS = {}

    FUNCTION_NODES = ['function_declaration', 'function']

    @staticmethod
    def get_docstring(node) -> str:
        """Extract docstring from comments."""
        docstring = ''
        parent_node = node.parent

        if parent_node.type == 'variable_declarator':
            base_node = parent_node.parent
        elif parent_node.type == 'pair':
            base_node = parent_node
        else:
            base_node = node
        prev_sibling = base_node.prev_sibling
        if prev_sibling is not None and prev_sibling.type == 'comment':
            all_prev_comment_nodes = [prev_sibling]
            prev_sibling = prev_sibling.prev_sibling
            while prev_sibling is not None and prev_sibling.type == 'comment':
                if not match_license_comment(prev_sibling.text.decode().lower()):
                    all_prev_comment_nodes.append(prev_sibling)
                last_comment_start_line = prev_sibling.start_point[0]
                prev_sibling = prev_sibling.prev_sibling
                if prev_sibling is None or prev_sibling.end_point[0] + 1 < last_comment_start_line:
                    break  # if there is an empty line, stop expanding.
            print("all_prev_comment_nodes:",all_prev_comment_nodes)
            docstring = ' '.join(
                (strip_c_style_comment_delimiters(s.text.decode()) for s in all_prev_comment_nodes[::-1]))
        return docstring

    @staticmethod
    def obfuscate(function_node, excluded: list = None, blacklist: list = None):
        """
        Obfuscate the JS/TS function declaration and body in function subtree.
        :param function_node: node from which subtree starts
        :param excluded: list of nodes that won't be obfuscated
        :param blacklist: list of nodes that won't be added into result functions and tokens
        :return: function and function tokens with obfuscated identifiers
        """
        if excluded is None:
            excluded = []
        if blacklist is None:
            blacklist = []
        nodes_to_obf = []
        for c in function_node.named_children:
            if c.type == 'formal_parameters' or c.type == 'statement_block':
                traverse_obf(c, nodes_to_obf, 'identifier', excluded)

        obf_dict = dict.fromkeys(
            [ids.text.decode() for ids in nodes_to_obf])
        v = 0
        for k in obf_dict.keys():
            obf_dict[k] = f'arg_{v}'
            v += 1

        tokens = []
        traverse(function_node, tokens)
        obf_tokens = []
        for token in tokens:
            if token in nodes_to_obf:
                obf_tokens.append(obf_dict[token.text.decode()])
            elif token not in blacklist:
                obf_tokens.append(token.text.decode())
        obf_function = function_node.text.decode()
        diff = 0
        for node in nodes_to_obf:
            identifier = node.text.decode()
            if identifier in obf_dict.keys():
                obf_function = obf_function[:node.start_byte - function_node.start_byte + diff] + obf_dict[
                    identifier] + obf_function[
                                  node.end_byte - function_node.start_byte + diff:]
                diff += len(obf_dict[identifier]) - len(identifier)
        for comm in blacklist:
            obf_function = obf_function.replace(comm.text.decode(), '')
        return obf_function, obf_tokens


    @staticmethod
    def get_definition(tree) -> List[Dict[str, Any]]:
        """Parse source tree and extract functions from it."""
        function_nodes = []
        functions = []
        traverse_type(tree.root_node, function_nodes, 'method_declaration')
        traverse_type(tree.root_node, function_nodes, 'build_method')
        traverse_type(tree.root_node, function_nodes, 'function_declaration')
        traverse_type(tree.root_node, function_nodes, 'decorated_function_declaration')
        traverse_type(tree.root_node, function_nodes, 'export_declaration')
        traverse_type(tree.root_node, function_nodes, 'decorated_export_declaration')

        traverse_type(tree.root_node, function_nodes, 'constructor_declaration')
        traverse_type(tree.root_node, function_nodes, 'function_expression')
        traverse_type(tree.root_node, function_nodes, 'arrow_function')

        # traverse_type(tree.root_node, function_nodes, 'function')
        # traverse_type(tree.root_node, function_nodes, 'decorator')

        for function in function_nodes:
            if function.children is None or len(function.children) == 0:
                continue
            parent_node = function.parent
            functions.append((parent_node.type, function, ArkTSParser.get_docstring(function)))

        definitions = []
        for node_type, function_node, docstring in functions:
            try:
                with time_limit(0.1):
                    metadata = ArkTSParser.get_function_metadata(function_node)
                    docstring_summary = get_docstring_summary(docstring)
                    ast_tokens = ast_to_sequence(function_node, ArkTSParser.AST_MAPPINGS)

                    obf_blacklist = []
                    traverse_type(function_node, obf_blacklist, 'comment')

                    obf = ArkTSParser.obfuscate(function_node, blacklist=obf_blacklist)

                    if metadata['identifier'] in ArkTSParser.BLACKLISTED_FUNCTION_NAMES:
                        continue
                    definitions.append({
                        'type': node_type,
                        'identifier': metadata['identifier'],
                        'parameters': metadata['parameters'],
                        'imports': metadata['imports'],
                        'calls': metadata['calls'],
                        'local_calls': metadata['local_calls'],
                        'function': function_node.text.decode(),
                        'function_tokens': tokenize_code(function_node),
                        'ast_function': ' '.join(ast_tokens),
                        'ast_function_tokens': ast_tokens,
                        'obf_function': obf[0],
                        'obf_function_tokens': obf[1],
                        'docstring': docstring,
                        'docstring_summary': docstring_summary,
                        'start_point': function_node.start_point,
                        'end_point': function_node.end_point
                    })
            except:
                pass
        return definitions

    @staticmethod
    def get_function_metadata(function_node) -> Dict[str, str]:
        """
        Extract function metadata: identifier and parameters.
        :param function_node: node from which subtree starts
        :return: map of function metadata
        """
        # TODO: imports, calls, local calls
        metadata = {
            'identifier': '',
            'parameters': '',
            'imports': [],
            'calls': [],
            'local_calls': []
        }
        identifier_nodes = [child for child in function_node.children if child.type == 'identifier']
        formal_parameters_nodes = [child for child in function_node.children if child.type == 'formal_parameters']
        if identifier_nodes:
            metadata['identifier'] = identifier_nodes[0].text.decode()
        if formal_parameters_nodes:
            metadata['parameters'] = formal_parameters_nodes[0].text.decode()
        return metadata
