"""Measure the three selected modules. Run with Radon 6.0.1 and an apps/api path."""

import argparse
import ast
import hashlib
import json
from importlib.metadata import version
from pathlib import Path

from radon.complexity import cc_visit
from radon.raw import analyze
from radon.visitors import Function

MODULES = (
    "plane/utils/issue_filters.py",
    "plane/utils/filters/filter_backend.py",
    "plane/utils/filters/converters.py",
)


def comma_split_functions(source):
    tree = ast.parse(source)
    return [
        function.name
        for function in ast.walk(tree)
        if isinstance(function, ast.FunctionDef)
        and any(
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and call.func.attr == "split"
            and call.args
            and isinstance(call.args[0], ast.Constant)
            and call.args[0].value == ","
            for call in ast.walk(function)
        )
    ]


def measure(path):
    content = path.read_bytes()
    source = content.decode()
    functions = {block.fullname: block.complexity for block in cc_visit(source) if isinstance(block, Function)}
    return {
        "sha256": hashlib.sha256(content).hexdigest(),
        "sloc": analyze(source).sloc,
        "max_function_complexity": max(functions.values()),
        "decisions": sum(score - 1 for score in functions.values()),
        "function_complexity": functions,
        "comma_split_functions": comma_split_functions(source),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("api_directory", type=Path)
    args = parser.parse_args()
    data = {name: measure(args.api_directory / name) for name in MODULES}
    print(json.dumps({"radon": version("radon"), "modules": data}, indent=2))
