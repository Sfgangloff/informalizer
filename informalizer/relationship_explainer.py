"""Generate informal natural-language explanations for relationships in the corpus.

For each Relationship row whose `informal` column is NULL or empty, ask Claude
to produce a 1-2 sentence account of how the two objects are connected,
then write it back to the DB. Uses the Messages Batch API.
"""

import sys
import time
from typing import Optional

import anthropic

from .corpus import ObjectRecord, get_object


MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 160

SYSTEM_PROMPT = """\
You are an expert mathematician and Lean 4 specialist. Given two formal \
objects from a Lean 4 file and the type of dependency between them, write a \
short (1-2 sentences, ≤ 50 words) plain-English account of how the two are \
related mathematically. Avoid Lean syntax; speak as you would to a \
mathematician reading a paper. Do NOT restate either object in full — focus \
on the *link*.\
"""

_REL_LABEL = {
    "depends_on": "A directly references B in its definition or proof",
    "uses":       "A (in another file) references B by name",
    "similar_to": "A and B are semantically similar according to embeddings",
}


def _prompt_for(rec_a: ObjectRecord, rec_b: ObjectRecord, rel_type: str) -> str:
    label = _REL_LABEL.get(rel_type, rel_type)
    return (
        f"Object A: [{rec_a.kind}] {rec_a.name}\n"
        f"Description: {rec_a.description.strip() or '(no description)'}\n\n"
        f"Object B: [{rec_b.kind}] {rec_b.name}\n"
        f"Description: {rec_b.description.strip() or '(no description)'}\n\n"
        f"Relationship: {rel_type} ({label}).\n\n"
        "In 1-2 sentences, explain in plain mathematical English how A and B "
        "are related. Be specific about what role B plays in A (or vice versa)."
    )


def explain_relationships(
    client: anthropic.Anthropic,
    conn,
    only_missing: bool = True,
    limit: Optional[int] = None,
) -> int:
    """Fill in `informal` for every relationship row missing one.

    Returns the number of rows written.
    """
    query = "SELECT id, from_uid, to_uid, rel_type, informal FROM relationships"
    if only_missing:
        query += " WHERE informal IS NULL OR informal = ''"
    if limit is not None:
        query += f" LIMIT {int(limit)}"
    rows = conn.execute(query).fetchall()
    if not rows:
        print("relationships: nothing to explain.", file=sys.stderr)
        return 0

    # Build batch requests; skip any pair we can't load both records for.
    batch_items: list[tuple[int, str]] = []  # (rel_id, custom_id)
    requests = []
    skipped = 0
    for r in rows:
        rec_a = get_object(conn, r["from_uid"])
        rec_b = get_object(conn, r["to_uid"])
        if not rec_a or not rec_b:
            skipped += 1
            continue
        if not (rec_a.description.strip() and rec_b.description.strip()):
            # Without descriptions on both sides Claude has nothing to work
            # with — skip rather than spend tokens on a guess.
            skipped += 1
            continue
        custom_id = f"rel-{r['id']}"
        batch_items.append((r["id"], custom_id))
        requests.append({
            "custom_id": custom_id,
            "params": {
                "model": MODEL,
                "max_tokens": MAX_TOKENS,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user",
                              "content": _prompt_for(rec_a, rec_b, r["rel_type"])}],
            },
        })

    if skipped:
        print(f"relationships: skipped {skipped} rows (missing description or record).",
              file=sys.stderr)
    if not requests:
        return 0

    print(f"Submitting batch of {len(requests)} relationship explanations...",
          file=sys.stderr)
    batch = client.messages.batches.create(requests=requests)

    while True:
        batch = client.messages.batches.retrieve(batch.id)
        counts = batch.request_counts
        done = counts.succeeded + counts.errored + counts.canceled + counts.expired
        print(f"  {done}/{len(requests)} processed "
              f"(succeeded={counts.succeeded}, errored={counts.errored})",
              file=sys.stderr)
        if batch.processing_status == "ended":
            break
        time.sleep(5)

    id_by_custom = {cid: rel_id for rel_id, cid in batch_items}
    written = 0
    for result in client.messages.batches.results(batch.id):
        rel_id = id_by_custom.get(result.custom_id)
        if rel_id is None:
            continue
        if result.result.type != "succeeded":
            continue
        text = result.result.message.content[0].text.strip()
        if not text:
            continue
        conn.execute(
            "UPDATE relationships SET informal = ? WHERE id = ?",
            (text, rel_id),
        )
        written += 1

    conn.commit()
    print(f"relationships: wrote {written} explanations.", file=sys.stderr)
    return written
