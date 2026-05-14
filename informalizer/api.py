"""Claude API calls: batch-describes Lean objects and generates a file-level summary."""

import sys
import time
import anthropic
from .lean_parser import LeanObject


MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 512
MAX_TOKENS_WITH_EXAMPLES = 900

SYSTEM_PROMPT = """\
You are an expert mathematician and Lean 4 specialist. Your role is to explain \
Lean 4 formal objects in clear, precise natural language aimed at mathematicians \
who understand the math but may not know Lean syntax.

Rules:
- Be concise (2-5 sentences per object unless complexity genuinely requires more)
- Lead with what the object IS (a definition, a theorem, a type class, ...)
- State the mathematical content plainly
- Mention notable proof strategies only if clearly visible from the signature
- Do NOT explain Lean syntax mechanics unless essential to the meaning
- For instances: explain what mathematical structure is being equipped to what type
- For classes/structures: explain what data or properties they package together

Response format (required):
First line must be: NAME: <a short natural-language name, 2-6 words, no Lean identifiers>
Then a blank line, then your description as usual.\
"""

SYSTEM_PROMPT_WITH_EXAMPLES = SYSTEM_PROMPT.rstrip("\\") + """

After the description, add a concrete example under an EXAMPLE: heading:
- For definitions/structures: show a small Lean 4 snippet that constructs or uses the object
- For lemmas/theorems: show a concrete instantiation or a brief usage in a proof step
- Keep the example to 3-10 lines of Lean 4 code with a one-sentence comment explaining it
- Use realistic type variables and values; avoid trivial or degenerate cases

EXAMPLE:
```lean
-- <one-sentence explanation>
<lean 4 code>
```\
"""

SUMMARY_SYSTEM = """\
You are an expert mathematician. Given a structured list of Lean 4 objects with \
their natural language descriptions, write a cohesive high-level summary of the file.\
"""


VISUALS_SYSTEM = """\
You are an expert mathematician helping to illustrate Lean 4 file summaries. \
You produce between 1 and 3 small TikZ figures that visually support the \
file's high-level summary. You decide what is most useful to illustrate — \
pick mathematical objects whose geometric/structural intuition genuinely \
benefits from a picture (a finite set in a lattice, a bijection, a tiling, \
a quotient, a region in a plane, …). If nothing genuinely benefits from a \
picture, produce zero illustrations rather than padding.

Hard requirements for each figure:
- The figure must contain NO TEXT WHATSOEVER inside the picture: no labels, \
  no node text, no annotations, no axis ticks with numbers. All explanation \
  goes in the CAPTION line. (You may use coordinate values internally — \
  just don't draw them.)
- Use only standard TikZ + these libraries: arrows.meta, positioning, calc, \
  decorations.pathreplacing, shapes.geometric, patterns, fit, backgrounds. \
  Do NOT load extra packages or include preamble — the wrapper provides it.
- Keep figures compact (fits inside ~6cm wide). Prefer clean line art with \
  one accent fill colour (e.g. blue!20, gray!30).
- Output only the body — start at `\\begin{tikzpicture}` and end at \
  `\\end{tikzpicture}`. No surrounding markdown unless the wrapper uses \
  fenced blocks (see format below).\
"""


def _parse_response(text: str) -> tuple[str, str, str]:
    """
    Split a Claude response into (natural_name, description, example).
    Expects 'NAME: ...' on the first line; falls back gracefully if absent.
    The EXAMPLE: block (if present) is separated from the description.
    """
    lines = text.strip().splitlines()
    natural_name = ""
    if lines and lines[0].startswith("NAME:"):
        natural_name = lines[0][5:].strip()
        body = "\n".join(lines[1:]).strip().lstrip("\n").strip()
    else:
        body = text.strip()

    # Split off the EXAMPLE: block if present.
    example = ""
    marker = "\nEXAMPLE:"
    idx = body.find(marker)
    if idx != -1:
        example = body[idx + len(marker):].strip()
        body = body[:idx].strip()

    return natural_name, body, example


def _object_prompt(obj: LeanObject) -> str:
    """Build the user-turn prompt for a single Lean object."""
    parts = [
        "Explain the following Lean 4 object in natural language:\n",
        f"Kind: {obj.kind}",
        f"Name: {obj.name}",
        f"Signature:\n{obj.signature}",
    ]
    if obj.docstring:
        parts.append(f"Docstring: {obj.docstring}")
    return "\n".join(parts)


def describe_objects_batch(
    client: anthropic.Anthropic,
    objects: list[LeanObject],
    include_examples: bool = False,
) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """
    Submit all objects as a single Messages Batch request.
    Poll until complete, then return (descriptions, natural_names, examples)
    where all three are dicts keyed by object name.
    When include_examples is False, examples is an empty dict.
    """
    system = SYSTEM_PROMPT_WITH_EXAMPLES if include_examples else SYSTEM_PROMPT
    max_tok = MAX_TOKENS_WITH_EXAMPLES if include_examples else MAX_TOKENS

    id_to_name = {f"obj-{i}": obj.name for i, obj in enumerate(objects)}
    requests = [
        {
            "custom_id": f"obj-{i}",
            "params": {
                "model": MODEL,
                "max_tokens": max_tok,
                "system": system,
                "messages": [{"role": "user", "content": _object_prompt(obj)}],
            },
        }
        for i, obj in enumerate(objects)
    ]

    print(f"Submitting batch of {len(objects)} objects...", file=sys.stderr)
    batch = client.messages.batches.create(requests=requests)
    print(f"Batch submitted (ID: {batch.id}). Waiting for results...", file=sys.stderr)

    while True:
        batch = client.messages.batches.retrieve(batch.id)
        counts = batch.request_counts
        done = counts.succeeded + counts.errored + counts.canceled + counts.expired
        print(
            f"  {done}/{len(objects)} processed "
            f"(succeeded={counts.succeeded}, errored={counts.errored})",
            file=sys.stderr,
        )
        if batch.processing_status == "ended":
            break
        time.sleep(5)

    descriptions: dict[str, str] = {}
    natural_names: dict[str, str] = {}
    examples: dict[str, str] = {}
    for result in client.messages.batches.results(batch.id):
        name = id_to_name[result.custom_id]
        if result.result.type == "succeeded":
            natural_name, description, example = _parse_response(
                result.result.message.content[0].text
            )
            descriptions[name] = description
            natural_names[name] = natural_name
            if example:
                examples[name] = example
        else:
            descriptions[name] = f"[Description unavailable: {result.result.type}]"
            natural_names[name] = ""

    return descriptions, natural_names, examples


def generate_summary(
    client: anthropic.Anthropic,
    ordered_objects: list[LeanObject],
    descriptions: dict[str, str],
) -> str:
    """Single call to produce a high-level summary from all descriptions."""
    object_list = "\n\n".join(
        f"### [{obj.kind}] {obj.name}\n{descriptions.get(obj.name, '')}"
        for obj in ordered_objects
    )
    prompt = (
        "Below is a Lean 4 file's objects listed in dependency order, each with "
        "a natural language description. Write a high-level summary (1–3 paragraphs) "
        "of what this file is about, what mathematical area it covers, what the main "
        "results are, and how the pieces fit together.\n\n"
        + object_list
    )

    print("Generating summary...", file=sys.stderr)
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SUMMARY_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def _parse_visuals(text: str) -> list[tuple[str, str]]:
    """Parse the visuals response into a list of (caption, tikz_body).

    Expected format:
      === ILLUSTRATION ===
      CAPTION: <one-sentence caption>
      ```tikz
      \\begin{tikzpicture}
        ...
      \\end{tikzpicture}
      ```
      === ILLUSTRATION ===
      ...
    """
    import re

    illustrations: list[tuple[str, str]] = []
    chunks = re.split(r"===\s*ILLUSTRATION(?:\s+\d+)?\s*===", text, flags=re.IGNORECASE)
    for chunk in chunks[1:]:
        cap_m = re.search(r"CAPTION:\s*(.+?)$", chunk, re.MULTILINE)
        caption = cap_m.group(1).strip() if cap_m else ""

        # Prefer a fenced code block (tikz/latex/tex/none); fall back to a raw
        # \begin{tikzpicture}...\end{tikzpicture} match.
        fence_m = re.search(
            r"```(?:tikz|latex|tex)?\s*\n(.*?)```",
            chunk, re.DOTALL | re.IGNORECASE,
        )
        if fence_m:
            tikz = fence_m.group(1).strip()
        else:
            raw_m = re.search(
                r"\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}",
                chunk, re.DOTALL,
            )
            if not raw_m:
                continue
            tikz = raw_m.group(0).strip()

        illustrations.append((caption, tikz))

    return illustrations


def generate_visualizations(
    client: anthropic.Anthropic,
    ordered_objects: list[LeanObject],
    descriptions: dict[str, str],
    summary: str,
    natural_names: dict[str, str] | None = None,
    categories: dict[str, str] | None = None,
) -> list[tuple[str, str]]:
    """Generate 1-3 TikZ illustrations of the summary. Returns a list of
    (caption, tikz_body) tuples. The TikZ body is the raw `\\begin{tikzpicture}
    ... \\end{tikzpicture}` block (no preamble) — `tikz_renderer.compile_tikz_to_svg`
    handles the document wrapping. Returns [] if the model produces nothing
    usable; callers should treat the list as optional."""
    natural_names = natural_names or {}
    categories = categories or {}

    obj_lines = []
    for obj in ordered_objects:
        cat = categories.get(obj.name, "")
        nat = natural_names.get(obj.name, "")
        blurb = descriptions.get(obj.name, "").strip().split("\n", 1)[0][:140]
        label = nat or obj.name
        obj_lines.append(f"- [{cat or obj.kind}] {label} (`{obj.name}`): {blurb}")
    object_block = "\n".join(obj_lines)

    prompt = (
        "Below is a Lean 4 file's high-level summary, followed by all of its "
        "objects with short descriptions. Produce between 1 and 3 small TikZ "
        "illustrations that visually support the summary. You choose what is "
        "most worth illustrating (geometric setup, a bijection, a region, a "
        "discrete grid, …) — only illustrate concepts that genuinely benefit "
        "from a picture. If nothing does, produce zero illustrations.\n\n"
        "Critical constraint: each figure must contain **no text at all** — "
        "no labels, no node names, no axis numbers, no annotations. All "
        "explanation goes in the CAPTION line.\n\n"
        "Output format (no extra commentary, no preamble, no \\documentclass):\n"
        "=== ILLUSTRATION ===\n"
        "CAPTION: <one-sentence caption explaining what is shown>\n"
        "```tikz\n"
        "\\begin{tikzpicture}\n"
        "  ...\n"
        "\\end{tikzpicture}\n"
        "```\n"
        "=== ILLUSTRATION ===\n"
        "CAPTION: ...\n"
        "```tikz\n"
        "\\begin{tikzpicture}...\\end{tikzpicture}\n"
        "```\n\n"
        "--- SUMMARY ---\n"
        f"{summary.strip()}\n\n"
        "--- OBJECTS ---\n"
        f"{object_block}\n"
    )

    print("Generating TikZ illustrations...", file=sys.stderr)
    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=VISUALS_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text
    illustrations = _parse_visuals(text)
    print(f"  parsed: {len(illustrations)} illustration(s)", file=sys.stderr)
    return illustrations
