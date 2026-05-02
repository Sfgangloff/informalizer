"""Regex-based parser that extracts top-level declarations from a Lean 4 source file."""

import re
from dataclasses import dataclass, field
from typing import Optional


KEYWORDS = (
    "theorem", "lemma", "def", "abbrev", "instance",
    "class", "structure", "inductive", "axiom", "example", "opaque",
)

# Matches the start of a top-level declaration, possibly preceded by
# attributes (@[...]) and modifiers (private, protected, noncomputable).
_DECL_RE = re.compile(
    r'^(?:@\[.*?\]\s*)*'
    r'(?:(?:private|protected|noncomputable|scoped)\s+)*'
    r'(' + '|'.join(KEYWORDS) + r')'
    r'(\s+|$)',
)


@dataclass
class LeanObject:
    """A single top-level Lean 4 declaration extracted from a source file."""

    name: str
    kind: str
    signature: str
    docstring: Optional[str]
    line_start: int      # 1-indexed
    line_end: int        # 1-indexed, inclusive
    raw_text: str


def parse_lean_file(filepath: str) -> list[LeanObject]:
    """Return all top-level declarations found in the given Lean 4 file, in source order."""
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Collect (line_index, keyword) for every declaration start.
    decl_starts: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        m = _DECL_RE.match(stripped)
        if m:
            decl_starts.append((i, m.group(1)))

    objects: list[LeanObject] = []
    anon_counters: dict[str, int] = {}

    for idx, (start_i, kind) in enumerate(decl_starts):
        end_i = decl_starts[idx + 1][0] - 1 if idx + 1 < len(decl_starts) else len(lines) - 1
        raw_text = "".join(lines[start_i : end_i + 1])

        name = _extract_name(lines[start_i].strip(), kind)
        if name is None:
            anon_counters[kind] = anon_counters.get(kind, 0) + 1
            name = f"{kind}_{anon_counters[kind]}"

        signature = _extract_signature(raw_text)
        docstring = _extract_docstring(lines, start_i)

        objects.append(LeanObject(
            name=name,
            kind=kind,
            signature=signature,
            docstring=docstring,
            line_start=start_i + 1,
            line_end=end_i + 1,
            raw_text=raw_text,
        ))

    return objects


def _extract_name(decl_line: str, kind: str) -> Optional[str]:
    """Extract the identifier immediately after the keyword."""
    # Strip leading attributes and modifiers to reach the keyword.
    stripped = re.sub(r'^(?:@\[.*?\]\s*)*', '', decl_line)
    stripped = re.sub(r'^(?:(?:private|protected|noncomputable|scoped)\s+)*', '', stripped)

    # Now stripped should start with the keyword.
    pattern = re.compile(re.escape(kind) + r'\s+([^\s\[\(:\{]+)')
    m = pattern.match(stripped)
    if m:
        candidate = m.group(1).strip(" :")
        if candidate and re.match(r'^[\w\'\.]+$', candidate):
            return candidate
    return None


def _extract_signature(raw_text: str) -> str:
    """
    Everything before the body delimiter: ' := ', ' where', or a trailing
    ' by' / '\nby'. Falls back to the full raw text if none found.
    """
    for delimiter in (' :=', ' where', '\nby ', '\n  by '):
        idx = raw_text.find(delimiter)
        if idx != -1:
            return raw_text[:idx].strip()
    return raw_text.strip()


def _extract_docstring(lines: list[str], decl_line_idx: int) -> Optional[str]:
    """
    Walk backwards from the declaration line collecting /-- ... -/ blocks.
    """
    i = decl_line_idx - 1
    # Skip blank lines immediately above.
    while i >= 0 and lines[i].strip() == "":
        i -= 1

    if i < 0 or "-/" not in lines[i]:
        return None

    # We're inside a doc comment block. Walk up to find its start.
    end_i = i
    while i >= 0 and "/--" not in lines[i]:
        i -= 1

    if i < 0:
        return None

    doc_lines = lines[i : end_i + 1]
    doc = "".join(doc_lines).strip()
    # Strip /-- and -/ delimiters.
    doc = re.sub(r'^/--\s*', '', doc)
    doc = re.sub(r'\s*-/$', '', doc)
    return doc.strip() or None
