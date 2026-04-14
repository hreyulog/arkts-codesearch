import setuptools

setuptools.setup(
    name='ark-function-parser',
    version='0.0.1',
    description='source code parser for ArkTS programming language',
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src", exclude=("tests",)),
    install_requires=['click', 'findspark', 'GitPython', 'joblib', 'pyarrow', 'pyspark', 'requests',
                      'setuptools', 'tqdm', 'tree_sitter>=0.23.0','tree-sitter-arkts-open'],
    package_data={'': ['tree-sitter-languages.so', 'enry']},
    python_requires=">=3.9",
    entry_points="""
        [console_scripts]
        ark_function_parser=ark_function_parser.cli:command_line
    """
)
