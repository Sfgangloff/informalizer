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
# Depth & external-reference metrics
# ---------------------------------------------------------------------------

def compute_in_file_depths(deps: dict[str, set[str]]) -> dict[str, int]:
    """
    For each object, the length of the longest dependency chain ending at it
    (using only file-local deps). Leaves (no in-file deps) have depth 0.
    Cycle members fall back to 0.
    """
    memo: dict[str, int] = {}
    visiting: set[str] = set()

    def depth(name: str) -> int:
        if name in memo:
            return memo[name]
        if name in visiting:
            return 0
        visiting.add(name)
        d = 0
        for dep in deps.get(name, ()):
            if dep in deps:
                d = max(d, 1 + depth(dep))
        visiting.discard(name)
        memo[name] = d
        return d

    return {name: depth(name) for name in deps}


# Tokens that should never be counted as "external references": Lean keywords,
# tactic combinators, and core Lean type names. Everything else that looks like
# a namespaced identifier (containing a dot) is treated as a mathlib-style ref.
_LEAN_NOISE = frozenset({
    # declaration keywords
    "theorem", "lemma", "def", "abbrev", "instance", "class", "structure",
    "inductive", "axiom", "example", "opaque",
    "private", "protected", "noncomputable", "scoped",
    # control / binders / proof keywords
    "by", "fun", "let", "if", "then", "else", "match", "with", "do",
    "return", "have", "haveI", "show", "obtain", "from", "using", "at",
    "in", "this", "where", "and", "or", "not",
    "import", "open", "namespace", "end", "section", "variable", "variables",
    "universe", "universes", "set_option", "deriving", "extends",
    # tactic verbs
    "exact", "exact_mod_cast", "apply", "intro", "intros", "refine", "rfl",
    "trivial", "simp", "simp_all", "rw", "rewrite", "calc", "constructor",
    "left", "right", "use", "split", "cases", "rcases", "induction",
    "linarith", "nlinarith", "ring", "ring_nf", "field_simp", "norm_num",
    "norm_cast", "push_cast", "push_neg", "omega", "subst", "all_goals",
    "any_goals", "try", "first", "repeat", "decide", "tauto", "aesop",
    "by_contra", "contradiction", "ext", "funext", "absurd", "unfold",
    # core type names that aren't mathlib
    "Type", "Prop", "Sort", "True", "False", "Bool", "Nat", "Int", "Char",
    "String", "List", "Array", "Option", "Unit", "Empty", "PUnit",
    "true", "false",
})

_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_']*(?:\.[A-Za-z_][A-Za-z0-9_']*)*")


def compute_external_metrics(
    objects: list[LeanObject],
) -> dict[str, dict]:
    """
    Heuristic proxy for "how much does this object lean on mathlib?".

    For each object, scan its body (with comments stripped) and collect the
    distinct *namespaced* identifiers (containing at least one dot) that are
    not file-local — these are overwhelmingly mathlib/external references.

    Returns a dict per object:
      - ext_refs:  number of distinct external namespaced refs
      - ns_depth:  max number of dots in any single external ref
      - refs:      sorted list of those refs (capped to avoid bloat)
    """
    local_names = {o.name for o in objects}
    out: dict[str, dict] = {}
    for obj in objects:
        searchable = _strip_comments(obj.raw_text)
        refs: set[str] = set()
        for tok in _IDENT_RE.findall(searchable):
            if "." not in tok:
                continue
            if tok in local_names:
                continue
            head = tok.split(".", 1)[0]
            if head in _LEAN_NOISE:
                continue
            # also drop refs whose entire prefix happens to be a local name
            # (e.g. `box.card` if `box` were local — defensive)
            if head in local_names:
                continue
            refs.add(tok)
        ns_depth = max((t.count(".") for t in refs), default=0)
        out[obj.name] = {
            "ext_refs": len(refs),
            "ns_depth": ns_depth,
            "refs": sorted(refs)[:25],
        }
    return out


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
