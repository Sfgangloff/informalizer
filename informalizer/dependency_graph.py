"""Builds a dependency graph over file-local Lean objects and topologically sorts them."""

import re
import sys
from collections import deque
from .lean_parser import LeanObject


def _strip_comments(text: str) -> str:
    """Remove /-- ... -/ doc-comment blocks and -- line comments before dependency scan."""
    text = re.sub(r'/--.*?-/', '', text, flags=re.DOTALL)
    text = re.sub(r'--[^\n]*', '', text)
    return text


def build_dependency_graph(objects: list[LeanObject]) -> dict[str, set[str]]:
    """
    For each object, find which other file-local objects it references.
    Returns deps[name] = set of names that `name` depends on.
    """
    all_names = {obj.name for obj in objects}

    deps: dict[str, set[str]] = {}
    for obj in objects:
        # Strip doc comments so that the docstring of a following declaration
        # (captured in raw_text when it precedes a multi-line @[...] attribute)
        # does not generate false-positive dependencies.
        searchable = _strip_comments(obj.raw_text)
        found: set[str] = set()
        for name in all_names:
            if name == obj.name:
                continue
            # Word-boundary match to avoid substring false positives.
            if re.search(r'\b' + re.escape(name) + r'\b', searchable):
                found.add(name)
        deps[obj.name] = found

    return deps


def topological_sort(
    objects: list[LeanObject],
    deps: dict[str, set[str]],
) -> list[LeanObject]:
    """
    Kahn's algorithm. Objects with no local dependencies come first.
    Falls back to original file order for any cycle members and emits a warning.
    """
    by_name = {obj.name: obj for obj in objects}
    original_order = {obj.name: i for i, obj in enumerate(objects)}

    # Build reverse graph: who depends on me?
    dependents: dict[str, set[str]] = {obj.name: set() for obj in objects}
    in_degree: dict[str, int] = {obj.name: 0 for obj in objects}

    for name, depends_on in deps.items():
        for dep in depends_on:
            if dep in dependents:
                dependents[dep].add(name)
                in_degree[name] += 1

    # Start with nodes that have no in-file dependencies.
    queue: deque[str] = deque(
        sorted(
            (n for n, d in in_degree.items() if d == 0),
            key=lambda n: original_order[n],
        )
    )

    sorted_names: list[str] = []
    while queue:
        name = queue.popleft()
        sorted_names.append(name)
        for dependent in sorted(dependents[name], key=lambda n: original_order[n]):
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)

    # Handle cycles: append remaining nodes in original file order.
    if len(sorted_names) < len(objects):
        cyclic = sorted(
            (n for n in by_name if n not in set(sorted_names)),
            key=lambda n: original_order[n],
        )
        print(
            f"Warning: dependency cycle detected among: {cyclic}. "
            "Falling back to file order for these objects.",
            file=sys.stderr,
        )
        sorted_names.extend(cyclic)

    return [by_name[n] for n in sorted_names]


# ---------------------------------------------------------------------------
# Categorisation
# ---------------------------------------------------------------------------

_THEOREM_KINDS = frozenset({"theorem", "lemma"})
_DEF_KINDS     = frozenset({"def", "abbrev", "opaque"})
_TYPE_KINDS    = frozenset({"structure", "class", "inductive"})


def categorize_objects(
    objects: list[LeanObject],
    deps: dict[str, set[str]],
) -> dict[str, str]:
    """
    Assign a role category to each object based on its kind and graph position.

    in_degree[X] = number of file-local objects that depend on X.
    High in_degree → X is structural/central; in_degree=0 for a theorem → it
    is a standalone result (no other object in the file builds on it).
    """
    in_degree: dict[str, int] = {obj.name: 0 for obj in objects}
    for dependencies in deps.values():
        for dep in dependencies:
            if dep in in_degree:
                in_degree[dep] += 1

    max_in = max(in_degree.values(), default=0)
    # "high" threshold: top ~40 % of the in-degree range, minimum 2.
    high = max(2, int(max_in * 0.4))

    categories: dict[str, str] = {}
    for obj in objects:
        ideg = in_degree.get(obj.name, 0)
        if obj.kind in _THEOREM_KINDS:
            if ideg == 0:
                categories[obj.name] = "Central Result"
            elif ideg >= high:
                categories[obj.name] = "Key Lemma"
            else:
                categories[obj.name] = "Technical Lemma"
        elif obj.kind in _DEF_KINDS:
            if ideg >= high:
                categories[obj.name] = "Central Concept"
            else:
                categories[obj.name] = "Technical Definition"
        elif obj.kind in _TYPE_KINDS:
            categories[obj.name] = "Core Structure"
        elif obj.kind == "instance":
            categories[obj.name] = "Instance"
        elif obj.kind == "axiom":
            categories[obj.name] = "Axiom"
        else:
            categories[obj.name] = "Other"

    return categories
