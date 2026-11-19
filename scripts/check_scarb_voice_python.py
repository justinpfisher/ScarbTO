"""Reviewed authored-template contracts for offline Python public producers.

Uses only Python's standard AST parser. It performs no source fetch, generation,
catalogue update, or publication. A changed contract requires semantic review,
not blindly copying a failing test's output into the catalogue.
"""
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def source_inventory(source):
    tree = ast.parse(source)
    strings, templates, sinks = [], [], []
    functions = {node.name: node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    # Public composer bodies bind transformations as well as literal fragments.
    # Follow their local helper calls, rather than freezing every script's code.
    roots = {name for name in functions if name.startswith(("_render", "render", "build_", "write_")) or name in ("copy", "rss_description", "weekly_intro")}
    selected = set()
    def include(name):
        if name in selected or name not in functions:
            return
        selected.add(name)
        for node in ast.walk(functions[name]):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                include(node.func.id)
    for name in sorted(roots):
        include(name)
    producers = {name: ast.dump(functions[name], include_attributes=False) for name in sorted(selected)}

    class Visitor(ast.NodeVisitor):
        def __init__(self):
            self.owners = []

        def visit_FunctionDef(self, node):
            self.owners.append(node.name)
            self.generic_visit(node)
            self.owners.pop()

        visit_AsyncFunctionDef = visit_FunctionDef

        def owner(self):
            return "/".join(self.owners) or "<module>"

        def visit_Constant(self, node):
            if isinstance(node.value, str) and node.value:
                strings.append([self.owner(), node.value])

        def visit_JoinedStr(self, node):
            templates.append([self.owner(), ast.dump(node, include_attributes=False)])
            self.generic_visit(node)

        def visit_Assign(self, node):
            if any(isinstance(target, ast.Attribute) and target.attr in ("text", "tail") for target in node.targets):
                sinks.append([self.owner(), ast.dump(node, include_attributes=False)])
            self.generic_visit(node)

        def visit_Call(self, node):
            name = getattr(node.func, "attr", getattr(node.func, "id", ""))
            if name in ("SubElement", "Element", "tostring", "write_bytes", "write_text"):
                sinks.append([self.owner(), ast.dump(node, include_attributes=False)])
            self.generic_visit(node)

    Visitor().visit(tree)
    return {"strings": strings, "templates": templates, "sinks": sinks, "producers": producers}


def inspect_source(filename, source, approved):
    actual = source_inventory(source)
    if actual != approved:
        raise ValueError("Unreviewed public Python producer: " + filename)
    return sum(len(entries) for entries in actual.values())


def producer_paths(root=ROOT):
    return sorted(["scripts/" + path.name for path in (root / "scripts").glob("build_*.py")] + ["scripts/scarb_voice.py", "scripts/scarb_accepted_copy.py", "scripts/scarb_static_materialize.py"])


def check_source_gateway(root=ROOT):
    contract = json.loads((root / "scripts/scarb-reviewed-python.json").read_text(encoding="utf-8"))
    if producer_paths(root) != sorted(contract):
        raise ValueError("Unregistered public Python producer")
    return sum(inspect_source(path, (root / path).read_text(encoding="utf-8"), contract[path]) for path in producer_paths(root))


if __name__ == "__main__":
    print("Scarb Python source contracts checked:", check_source_gateway())
