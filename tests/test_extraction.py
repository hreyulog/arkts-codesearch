import json
import os.path
from ark_function_parser.cli_utils.extract_functions import process, process_jsonl


def test_extract_arkts():
    path = os.path.relpath(
        os.path.dirname(__file__)) + '/extraction_samples/arkts_test.ets'
    lang = 'arkts'
    functions = process(path=path, lang=lang)
    assert len(functions) >= 2
    assert functions[0]['identifier'] == 'add'
    assert functions[1]['identifier'] == 'multiply'
