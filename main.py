"""CLI entry point: parse a Lean 4 file, describe its objects via Claude, and write a report."""

import argparse
import sys
from collections import Counter
from pathlib import Path

import anthropic

from lean_parser import parse_lean_file
from dependency_graph import build_dependency_graph, topological_sort
from informalizer import describe_objects_batch, generate_summary
from formatter import print_terminal, write_markdown


def main() -> None:
    """Parse arguments, run the full pipeline, and write the Markdown report."""
    parser = argparse.ArgumentParser(
        description="Informalizer: generate natural language explanations for a Lean 4 file."
    )
    parser.add_argument("lean_file", help="Path to the .lean file to analyze")
    parser.add_argument(
        "--output",
        default=None,
        help="Output Markdown file path (default: <lean_file_stem>_informalizer.md)",
    )
    parser.add_argument("--no-terminal", action="store_true", help="Suppress terminal output")
    parser.add_argument("--no-markdown", action="store_true", help="Skip writing Markdown file")
    parser.add_argument("--api-key", default=None, help="Anthropic API key (default: ANTHROPIC_API_KEY env)")
    parser.add_argument("--api-key-file", default=None, help="Path to file containing the Anthropic API key")
    args = parser.parse_args()

    api_key = args.api_key
    if args.api_key_file:
        key_path = Path(args.api_key_file)
        if not key_path.exists():
            print(f"Error: API key file not found: {args.api_key_file}", file=sys.stderr)
            sys.exit(1)
        api_key = key_path.read_text().strip()

    lean_path = Path(args.lean_file)
    if not lean_path.exists():
        print(f"Error: file not found: {args.lean_file}", file=sys.stderr)
        sys.exit(1)

    output_path = args.output or str(lean_path.with_name(lean_path.stem + "_informalizer.md"))

    # --- Step 1: Parse ---
    print(f"Parsing {lean_path.name}...", file=sys.stderr)
    objects = parse_lean_file(str(lean_path))

    if not objects:
        print("No top-level objects found. Exiting.", file=sys.stderr)
        sys.exit(0)

    counts = Counter(obj.kind for obj in objects)
    summary_parts = ", ".join(f"{v} {k}{'s' if v > 1 else ''}" for k, v in sorted(counts.items()))
    print(f"Found {len(objects)} objects: {summary_parts}", file=sys.stderr)

    # --- Step 2: Dependency graph + topological sort ---
    print("Building dependency graph...", file=sys.stderr)
    deps = build_dependency_graph(objects)
    ordered = topological_sort(objects, deps)

    # --- Step 3: Batch describe ---
    client = anthropic.Anthropic(api_key=api_key)
    descriptions = describe_objects_batch(client, ordered)

    # --- Step 4: Summary ---
    summary = generate_summary(client, ordered, descriptions)

    # --- Step 5: Output ---
    if not args.no_terminal:
        print_terminal(str(lean_path), ordered, descriptions, summary)

    if not args.no_markdown:
        write_markdown(str(lean_path), ordered, descriptions, summary, output_path)
        print(f"Done. Markdown written to {output_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
