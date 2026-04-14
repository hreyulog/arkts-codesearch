#!/usr/bin/env bash

VERSION=$(sed -nE "s/^ *version='(.*)'.*$/\1/p" setup.py)
echo "last detected version is $VERSION"

#python3 -m pip install --upgrade build
#python3 -m pip install -r requirements.txt
python3 -m build || exit
python3 -m /home/hreyulog/arkts/csn_function_parser/src/ark_function_parser/build_grammars.py
#pip install tree-sitter==0.20.1

pip uninstall -y ark-function-parser || exit
pip install "./dist/ark_function_parser-$VERSION-py3-none-any.whl"
