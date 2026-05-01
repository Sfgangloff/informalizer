"""Claude API calls: batch-describes Lean objects and generates a file-level summary."""

import sys
import time
import anthropic
from lean_parser import LeanObject


MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 512

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
- For classes/structures: explain what data or properties they package together\
"""

SUMMARY_SYSTEM = """\
You are an expert mathematician. Given a structured list of Lean 4 objects with \
their natural language descriptions, write a cohesive high-level summary of the file.\
"""


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
) -> dict[str, str]:
    """
    Submit all objects as a single Messages Batch request.
    Poll until complete, then return {object_name: description}.
    """
    id_to_name = {f"obj-{i}": obj.name for i, obj in enumerate(objects)}
    requests = [
        {
            "custom_id": f"obj-{i}",
            "params": {
                "model": MODEL,
                "max_tokens": MAX_TOKENS,
                "system": SYSTEM_PROMPT,
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
    for result in client.messages.batches.results(batch.id):
        name = id_to_name[result.custom_id]
        if result.result.type == "succeeded":
            descriptions[name] = result.result.message.content[0].text
        else:
            descriptions[name] = f"[Description unavailable: {result.result.type}]"

    return descriptions


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
