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
You are an expert mathematician. You produce a structured high-level
summary of a Lean 4 file, following a strict three-section template
that downstream tooling depends on.

Output format (markdown, exactly these three sections, in this order):

## Summary

One or two short paragraphs of prose giving the high-level picture:
the mathematical area, the goal of the file, and how the pieces fit
together. Do not enumerate every object.

## Main definitions

A SYNTHETIC short paragraph (target: roughly one short clause per
definition; total length 3-7 sentences for the whole subsection,
regardless of how many definitions there are). Mention each main
definition exactly once, with its **display name** in bold and its
"(Figure N)" citation. Do NOT restate the full description — name the
role of the definition in the file in one short clause and move on.
Group closely related definitions in the same sentence when natural.

## Main results

A SYNTHETIC short paragraph (target: roughly one short clause per
result; total length 4-9 sentences for the whole subsection). Mention
each main result exactly once, with its **display name** in bold and
its "(Figure N)" citation. State what each result asserts in one
short clause — no proof sketches, no restating descriptions. Group
results that are minor variants of each other (e.g. round-trip
identities, monotonicity + degenerate case) into a single sentence.

Hard rules:
- Use exactly the three headings above with `## ` prefixes.
- Write flowing prose in each subsection, not bullet lists.
- Bold every object name with double asterisks the FIRST time it appears
  in its subsection (use the display name from the input).
- Cite figures verbatim as "(Figure N)" where N is the number provided
  in the input. Do not invent figure numbers.
- Do not invent objects or restate signatures. Use only what is provided.
- Be terse. The descriptions of each object are listed elsewhere in
  the document; this is the overview, not a re-explanation.
"""


FIGURE_SYSTEM = """\
You are an expert mathematician producing a single small TikZ figure
that visually illustrates ONE Lean 4 object (a definition or a theorem).

You MUST output BOTH of the following, in this exact order, with no
additional prose:

DESCRIPTION: <one short paragraph (2-4 sentences) describing what the
picture shows — the geometric setup, what each shape represents, and
the coordinate convention. This description is shown to you again on
later figure prompts so the model can build overlays on top of this
picture; write it for that audience.>

```tikz
\\begin{tikzpicture}
  ...
\\end{tikzpicture}
```

Hard requirements on the figure:
- Output exactly one TikZ body wrapped in a ```tikz fenced block.
  No preamble, no \\documentclass, no extra markdown.
- The figure contains NO TEXT WHATSOEVER inside the picture: no labels,
  no node text, no math, no annotations, no axis ticks with numbers.
  The figure must be self-explanatory through geometry alone — the
  only caption shown next to it is the figure number.
- Use only standard TikZ plus these libraries: arrows.meta, positioning,
  calc, decorations.pathreplacing, shapes.geometric, patterns, fit,
  backgrounds. Do NOT load extra packages.
- Keep the figure compact (fits inside ~6cm wide). Prefer clean line
  art with at most one accent fill colour (e.g. blue!20, gray!30).

Reuse via placeholders (only when the user lists upstream figures):
- If the user provides a list of upstream figures with their
  descriptions, you may embed any of them by writing a comment line
  on its own line, exactly:
      % PLACEHOLDER: <upstream_lean_name>
  At render time this line is replaced verbatim by the inner drawing
  commands of that upstream figure. Do NOT copy upstream code yourself.
- You may wrap the placeholder in a `\\begin{scope}[shift={(dx,dy)},
  scale=s] ... \\end{scope}` if you need to translate or rescale the
  upstream picture.
- After the placeholder, ADD what is specific to this object — typically
  extra arrows, a highlighted subset, a relationship marker.
- Only placeholder names from the supplied list are valid. Do NOT
  invent placeholders for unrelated objects.
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


_RESULT_CATEGORIES = frozenset({"Central Result", "Key Lemma"})
_DEFINITION_CATEGORIES = frozenset({"Central Concept", "Core Structure"})
MAIN_CATEGORIES = _RESULT_CATEGORIES | _DEFINITION_CATEGORIES


def _display_name(obj: LeanObject, natural_names: dict[str, str]) -> str:
    nat = natural_names.get(obj.name, "")
    if nat and nat.lower() != obj.name.lower():
        return f"{nat} (`{obj.name}`)"
    return f"`{obj.name}`"


def select_main_objects(
    ordered_objects: list[LeanObject],
    categories: dict[str, str],
) -> tuple[list[LeanObject], list[LeanObject]]:
    """Partition the file's objects into (main_definitions, main_results),
    preserving dependency order within each list. Used both for figure
    generation and for the summary's two prose subsections."""
    main_defs: list[LeanObject] = []
    main_results: list[LeanObject] = []
    for obj in ordered_objects:
        cat = categories.get(obj.name, "")
        if cat in _DEFINITION_CATEGORIES:
            main_defs.append(obj)
        elif cat in _RESULT_CATEGORIES:
            main_results.append(obj)
    return main_defs, main_results


def assign_figure_numbers(
    main_defs: list[LeanObject],
    main_results: list[LeanObject],
) -> dict[str, int]:
    """Definitions get Figure 1..k, results get Figure k+1..k+m."""
    numbering: dict[str, int] = {}
    n = 1
    for obj in main_defs:
        numbering[obj.name] = n
        n += 1
    for obj in main_results:
        numbering[obj.name] = n
        n += 1
    return numbering


def generate_summary(
    client: anthropic.Anthropic,
    ordered_objects: list[LeanObject],
    descriptions: dict[str, str],
    natural_names: dict[str, str] | None = None,
    categories: dict[str, str] | None = None,
    figure_numbers: dict[str, int] | None = None,
) -> str:
    """Generate the structured summary (Summary / Main definitions / Main
    results). Requires the figure numbering so the prose can cite figures
    verbatim as "(Figure N)" — those tokens are later turned into anchored
    links during HTML rendering."""
    natural_names = natural_names or {}
    categories = categories or {}
    figure_numbers = figure_numbers or {}

    main_defs, main_results = select_main_objects(ordered_objects, categories)

    def _block(objs: list[LeanObject]) -> str:
        if not objs:
            return "(none)"
        lines = []
        for obj in objs:
            disp = _display_name(obj, natural_names)
            fig = figure_numbers.get(obj.name)
            fig_str = f"Figure {fig}" if fig else "(no figure)"
            desc = descriptions.get(obj.name, "").strip()
            lines.append(
                f"- DISPLAY_NAME: **{disp}**\n"
                f"  FIGURE: {fig_str}\n"
                f"  KIND: {obj.kind}\n"
                f"  DESCRIPTION: {desc}"
            )
        return "\n".join(lines)

    other_lines = []
    for obj in ordered_objects:
        cat = categories.get(obj.name, "")
        if cat in MAIN_CATEGORIES:
            continue
        disp = _display_name(obj, natural_names)
        blurb = descriptions.get(obj.name, "").strip().split("\n", 1)[0][:160]
        other_lines.append(f"- {disp} [{cat or obj.kind}]: {blurb}")
    other_block = "\n".join(other_lines) if other_lines else "(none)"

    prompt = (
        "Produce a structured summary of the following Lean 4 file. Follow the\n"
        "three-section template from the system prompt EXACTLY. Bold every\n"
        "object name (using the **DISPLAY_NAME** form provided). Cite each\n"
        "main object's figure verbatim as `(Figure N)` using the FIGURE\n"
        "value listed below — do not invent numbers, do not renumber.\n\n"
        "--- MAIN DEFINITIONS (use these for the `## Main definitions` section) ---\n"
        f"{_block(main_defs)}\n\n"
        "--- MAIN RESULTS (use these for the `## Main results` section) ---\n"
        f"{_block(main_results)}\n\n"
        "--- SUPPORTING OBJECTS (context only; do NOT introduce them as main) ---\n"
        f"{other_block}\n"
    )

    print("Generating structured summary...", file=sys.stderr)
    response = client.messages.create(
        model=MODEL,
        max_tokens=1536,
        system=SUMMARY_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


import re as _re


_TIKZ_FENCE_RE = _re.compile(
    r"```(?:tikz|latex|tex)?\s*\n(.*?)```",
    _re.DOTALL | _re.IGNORECASE,
)
_TIKZ_RAW_RE = _re.compile(
    r"\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}",
    _re.DOTALL,
)
_DESCRIPTION_RE = _re.compile(
    r"DESCRIPTION:\s*(.+?)(?=\n\s*```|\n\s*\\begin\{tikzpicture\}|\Z)",
    _re.DOTALL | _re.IGNORECASE,
)
_BEGIN_TIKZPIC_RE = _re.compile(
    r"\\begin\{tikzpicture\}(?:\[[^\]]*\])?",
)
_PLACEHOLDER_RE = _re.compile(
    r"^[ \t]*%[ \t]*PLACEHOLDER:[ \t]*([A-Za-z_][\w'.]*)[ \t]*$",
    _re.MULTILINE,
)


def _extract_tikz_body(text: str) -> str | None:
    """Pull a TikZ body out of a fenced code block, or out of raw text that
    contains a `\\begin{tikzpicture}...\\end{tikzpicture}`. None if nothing
    usable was returned."""
    fence_m = _TIKZ_FENCE_RE.search(text)
    if fence_m:
        candidate = fence_m.group(1).strip()
        if "\\begin{tikzpicture}" in candidate:
            return candidate
    raw_m = _TIKZ_RAW_RE.search(text)
    if raw_m:
        return raw_m.group(0).strip()
    return None


def _parse_figure_response(text: str) -> tuple[str, str | None]:
    """Pull (description, tikz_body) out of a figure response. The
    description is the paragraph after `DESCRIPTION:` and before the first
    fenced code block or raw `\\begin{tikzpicture}` — empty string if
    absent. The tikz_body may still contain `% PLACEHOLDER: <name>` lines
    awaiting substitution; it is None if nothing parseable was found."""
    desc_m = _DESCRIPTION_RE.search(text)
    description = desc_m.group(1).strip() if desc_m else ""
    return description, _extract_tikz_body(text)


def _strip_tikzpicture_wrapper(body: str) -> str:
    """Return the inner drawing commands of a `\\begin{tikzpicture}[...]
    ... \\end{tikzpicture}` block — what should be substituted into a
    placeholder line. If no wrapper is found, return the body as-is
    (defensive)."""
    m = _BEGIN_TIKZPIC_RE.search(body)
    if not m:
        return body.strip()
    inner = body[m.end():]
    end_idx = inner.rfind("\\end{tikzpicture}")
    if end_idx == -1:
        return inner.strip()
    return inner[:end_idx].strip()


def _substitute_placeholders(
    tikz: str,
    upstream_bodies: dict[str, str],
    allowed: set[str],
) -> tuple[str, list[str]]:
    """Replace `% PLACEHOLDER: <name>` lines with the inner drawing commands
    of the named upstream figure. Returns (substituted_tikz, warnings).
    Names not in `allowed` or not in `upstream_bodies` are left as a
    comment marker and recorded in warnings."""
    warnings: list[str] = []

    def repl(m: _re.Match) -> str:
        name = m.group(1)
        if name not in allowed:
            warnings.append(f"disallowed placeholder: {name}")
            return f"% [placeholder {name!r} not in allowed list]"
        body = upstream_bodies.get(name)
        if body is None:
            warnings.append(f"missing upstream body for placeholder: {name}")
            return f"% [placeholder {name!r} has no upstream body]"
        inner = _strip_tikzpicture_wrapper(body)
        return inner

    return _PLACEHOLDER_RE.sub(repl, tikz), warnings


def _figure_prompt(
    obj: LeanObject,
    description: str,
    natural_name: str,
    figure_number: int,
    reuse_entries: list[tuple[str, str, str, int]],
) -> str:
    """Build the per-object figure prompt. `reuse_entries` is a list of
    (lean_name, display_name, picture_description, fig_n) for upstream
    main objects whose figures may be embedded via placeholders. The
    upstream TikZ code itself is NOT sent — only the description, which is
    enough for the model to plan overlays and pick a placeholder."""
    label = natural_name or obj.name
    parts = [
        f"Produce ONE small TikZ figure that illustrates the following Lean 4 "
        f"{obj.kind}. The figure will be labelled `Figure {figure_number}` "
        f"in the rendered document and shown WITHOUT any other caption, so "
        f"the picture itself must convey the geometric/structural idea.",
        "",
        f"Display name: {label}",
        f"Lean name: `{obj.name}`",
        f"Kind: {obj.kind}",
        "",
        "Signature / statement:",
        "```lean",
        obj.signature,
        "```",
        "",
        "Informal description:",
        description.strip() or "(no description)",
    ]
    if reuse_entries:
        parts += [
            "",
            ("UPSTREAM FIGURES AVAILABLE FOR PLACEHOLDER REUSE — the following "
             "objects appear in this object's statement and already have their "
             "own figures. Embed their picture by writing a line "
             "`% PLACEHOLDER: <lean_name>` on its own line where you want the "
             "upstream picture inserted; the renderer will substitute the "
             "drawing commands verbatim. The figure body sent to you previously "
             "for these objects is NOT included here — work from the "
             "descriptions only. After the placeholder, add overlays specific "
             "to THIS object (extra arrows, highlighted subsets, etc.)."),
            "",
            "Allowed placeholder names (use the exact Lean name):",
        ]
        for lean_name, disp, picdesc, n in reuse_entries:
            parts += [
                f"- `{lean_name}` ({disp}, Figure {n}) — {picdesc}",
            ]
    parts += [
        "",
        "Output format (no extra prose outside of these two pieces):",
        "DESCRIPTION: <one short paragraph>",
        "",
        "```tikz",
        "\\begin{tikzpicture}",
        "  % PLACEHOLDER: <lean_name>   (only if a reusable upstream exists)",
        "  ...",
        "\\end{tikzpicture}",
        "```",
    ]
    return "\n".join(parts)


def generate_object_figures(
    client: anthropic.Anthropic,
    main_defs: list[LeanObject],
    main_results: list[LeanObject],
    descriptions: dict[str, str],
    deps: dict[str, set[str]],
    natural_names: dict[str, str] | None = None,
    figure_numbers: dict[str, int] | None = None,
) -> dict[str, str]:
    """Generate one TikZ body per main object. Two batched calls:
    Phase A produces (picture_description, tikz_body) for each main
    definition. Phase B asks each main result to emit a tikz body that
    embeds upstream pictures via `% PLACEHOLDER: <name>` lines, given
    only the upstream picture *descriptions*. After phase B we substitute
    each placeholder with the inner drawing commands of the named
    upstream body. Returns {object_name: tikz_body_with_placeholders_resolved}."""
    natural_names = natural_names or {}
    figure_numbers = figure_numbers or {
        obj.name: i + 1
        for i, obj in enumerate(main_defs + main_results)
    }

    bodies: dict[str, str] = {}
    pic_descriptions: dict[str, str] = {}

    # ---- Phase A: definitions, no reuse ----
    if main_defs:
        a_bodies, a_descs = _batch_figures(
            client,
            [(obj, []) for obj in main_defs],
            descriptions, natural_names, figure_numbers,
            phase_label="definitions",
        )
        bodies.update(a_bodies)
        pic_descriptions.update(a_descs)

    # ---- Phase B: results, with placeholder-reuse from phase A ----
    if main_results:
        def_by_name = {d.name: d for d in main_defs}
        result_requests: list[tuple[LeanObject, list[tuple[str, str, str, int]]]] = []
        for obj in main_results:
            reuse: list[tuple[str, str, str, int]] = []
            for dep_name in deps.get(obj.name, set()):
                if dep_name not in bodies:
                    continue
                dep_obj = def_by_name.get(dep_name)
                if dep_obj is None:
                    continue
                disp = _display_name(dep_obj, natural_names)
                picdesc = pic_descriptions.get(dep_name, "").strip() or "(no description)"
                reuse.append((dep_name, disp, picdesc, figure_numbers[dep_name]))
            result_requests.append((obj, reuse))

        b_bodies, b_descs = _batch_figures(
            client, result_requests,
            descriptions, natural_names, figure_numbers,
            phase_label="results",
        )
        # Substitute placeholders with the inner commands of the matching
        # definition bodies before storing.
        allowed_per_result: dict[str, set[str]] = {
            obj.name: {entry[0] for entry in reuse}
            for obj, reuse in result_requests
        }
        for name, body in b_bodies.items():
            allowed = allowed_per_result.get(name, set())
            resolved, warns = _substitute_placeholders(body, bodies, allowed)
            for w in warns:
                print(f"  figure {name}: {w}", file=sys.stderr)
            bodies[name] = resolved
        pic_descriptions.update(b_descs)

    return bodies


def _batch_figures(
    client: anthropic.Anthropic,
    requests_data: list[tuple[LeanObject, list[tuple[str, str, str, int]]]],
    descriptions: dict[str, str],
    natural_names: dict[str, str],
    figure_numbers: dict[str, int],
    phase_label: str,
) -> tuple[dict[str, str], dict[str, str]]:
    """Submit one batch for the given (object, reuse_entries) pairs and
    return ({name: tikz_body_with_unresolved_placeholders},
            {name: picture_description}). Items that errored or whose
    response couldn't be parsed are simply absent."""
    if not requests_data:
        return {}, {}

    id_to_name = {f"fig-{i}": obj.name for i, (obj, _) in enumerate(requests_data)}
    requests = []
    for i, (obj, reuse) in enumerate(requests_data):
        prompt = _figure_prompt(
            obj,
            descriptions.get(obj.name, ""),
            natural_names.get(obj.name, ""),
            figure_numbers[obj.name],
            reuse,
        )
        requests.append({
            "custom_id": f"fig-{i}",
            "params": {
                "model": MODEL,
                "max_tokens": 2048,
                "system": FIGURE_SYSTEM,
                "messages": [{"role": "user", "content": prompt}],
            },
        })

    print(
        f"Submitting {phase_label} figure batch ({len(requests_data)} objects)...",
        file=sys.stderr,
    )
    batch = client.messages.batches.create(requests=requests)
    print(f"  batch id: {batch.id}", file=sys.stderr)

    while True:
        batch = client.messages.batches.retrieve(batch.id)
        counts = batch.request_counts
        done = counts.succeeded + counts.errored + counts.canceled + counts.expired
        print(
            f"  {phase_label}: {done}/{len(requests_data)} processed "
            f"(succeeded={counts.succeeded}, errored={counts.errored})",
            file=sys.stderr,
        )
        if batch.processing_status == "ended":
            break
        time.sleep(5)

    bodies_out: dict[str, str] = {}
    descs_out: dict[str, str] = {}
    for result in client.messages.batches.results(batch.id):
        name = id_to_name[result.custom_id]
        if result.result.type != "succeeded":
            print(
                f"  figure for {name} failed: {result.result.type}",
                file=sys.stderr,
            )
            continue
        text = result.result.message.content[0].text
        desc, tikz = _parse_figure_response(text)
        if tikz:
            bodies_out[name] = tikz
            descs_out[name] = desc
        else:
            print(f"  figure for {name}: could not extract TikZ body",
                  file=sys.stderr)
    return bodies_out, descs_out
