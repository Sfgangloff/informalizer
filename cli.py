"""Unified CLI for Informalizer. Subcommands: describe, ingest, diff, state, graph."""

import argparse
import sys
from collections import Counter
from pathlib import Path

import anthropic
from rich.console import Console
from rich.table import Table
from rich.text import Text

from informalizer.lean_parser import parse_lean_file
from informalizer.dependency_graph import (
    build_dependency_graph,
    topological_sort,
    categorize_objects,
)
from informalizer.api import describe_objects_batch, generate_summary
from informalizer.formatter import print_terminal, write_markdown, write_html
from informalizer.graph_renderer import render_graph
from informalizer.knowledge_store import KnowledgeStore, make_uid, VALID_STATES
from informalizer.diff_finder import find_diff

_console = Console()

_STATE_STYLE = {
    "known":    "bold green",
    "learning": "bold yellow",
    "unknown":  "bold red",
}


# ======================================================================
# Pipeline helpers
# ======================================================================

def _resolve_output_path(lean_path: Path, output_dir: Path | None, suffix: str = ".html") -> Path:
    stem = lean_path.stem + "_informalizer" + suffix
    return output_dir / stem if output_dir else lean_path.with_name(stem)


def _process_file(
    lean_path: Path,
    client: anthropic.Anthropic,
    output_path: Path,
    terminal: bool,
    html: bool,
    markdown: bool,
    include_examples: bool = False,
) -> None:
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"Processing: {lean_path}", file=sys.stderr)

    objects = parse_lean_file(str(lean_path))
    if not objects:
        print("  No top-level objects found. Skipping.", file=sys.stderr)
        return

    counts = Counter(obj.kind for obj in objects)
    parts = ", ".join(f"{v} {k}{'s' if v > 1 else ''}" for k, v in sorted(counts.items()))
    print(f"  Found {len(objects)} objects: {parts}", file=sys.stderr)

    deps = build_dependency_graph(objects)
    ordered = topological_sort(objects, deps)
    categories = categorize_objects(objects, deps)

    descriptions, natural_names, examples = describe_objects_batch(
        client, ordered, include_examples=include_examples
    )
    summary = generate_summary(client, ordered, descriptions)

    if terminal:
        print_terminal(str(lean_path), ordered, descriptions, summary,
                       natural_names=natural_names, categories=categories)
    if html:
        html_path = output_path.with_suffix(".html")
        write_html(str(lean_path), ordered, descriptions, summary, str(html_path),
                   natural_names=natural_names, categories=categories, deps=deps,
                   examples=examples)
        print(f"  Written: {html_path}", file=sys.stderr)
    if markdown:
        md_path = output_path.with_suffix(".md")
        write_markdown(str(lean_path), ordered, descriptions, summary, str(md_path),
                       natural_names=natural_names, categories=categories, deps=deps,
                       examples=examples)
        print(f"  Written: {md_path}", file=sys.stderr)


_DEFAULT_KEY_FILE = Path(__file__).parent / "anthropic_key.txt"


def _make_client(args: argparse.Namespace) -> anthropic.Anthropic:
    api_key = getattr(args, "api_key", None)
    api_key_file = getattr(args, "api_key_file", None)
    if api_key_file:
        key_path = Path(api_key_file)
        if not key_path.exists():
            print(f"Error: API key file not found: {api_key_file}", file=sys.stderr)
            sys.exit(1)
        api_key = key_path.read_text().strip()
    if not api_key and _DEFAULT_KEY_FILE.exists():
        api_key = _DEFAULT_KEY_FILE.read_text().strip()
    return anthropic.Anthropic(api_key=api_key)


# ======================================================================
# describe
# ======================================================================

def _cmd_describe(args: argparse.Namespace) -> None:
    target = Path(args.path)
    if not target.exists():
        print(f"Error: path not found: {target}", file=sys.stderr)
        sys.exit(1)

    client = _make_client(args)
    output_dir = Path(args.output_dir) if args.output_dir else None
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    lean_files = [target] if target.is_file() else sorted(target.rglob("*.lean"))
    if not lean_files:
        print(f"No .lean files found under {target}", file=sys.stderr)
        sys.exit(0)

    if target.is_dir():
        print(f"Found {len(lean_files)} .lean file(s) under {target}", file=sys.stderr)

    write_html_flag = not args.no_html
    write_md_flag = args.markdown

    failed: list[tuple[Path, str]] = []
    for lean_path in lean_files:
        out = (
            Path(args.output)
            if (target.is_file() and args.output)
            else _resolve_output_path(lean_path, output_dir)
        )
        if args.skip_existing and out.exists():
            print(f"Skipping (output exists): {lean_path}", file=sys.stderr)
            continue
        try:
            _process_file(lean_path, client, out,
                          terminal=not args.no_terminal,
                          html=write_html_flag,
                          markdown=write_md_flag,
                          include_examples=args.examples)
        except Exception as exc:
            print(f"  ERROR processing {lean_path}: {exc}", file=sys.stderr)
            failed.append((lean_path, str(exc)))

    if target.is_dir():
        print(f"\nDone. {len(lean_files) - len(failed)} succeeded, {len(failed)} failed.",
              file=sys.stderr)
    if failed:
        for path, err in failed:
            print(f"  {path}: {err}", file=sys.stderr)
        sys.exit(1)


# ======================================================================
# ingest
# ======================================================================

def _cmd_ingest(args: argparse.Namespace) -> None:
    target = Path(args.path)
    if not target.exists():
        print(f"Error: path not found: {target}", file=sys.stderr)
        sys.exit(1)

    lean_files = [target] if target.is_file() else sorted(target.rglob("*.lean"))
    if not lean_files:
        print(f"No .lean files found under {target}", file=sys.stderr)
        sys.exit(0)

    store = KnowledgeStore()
    total_added = total_changed = 0

    for lean_path in lean_files:
        objects = parse_lean_file(str(lean_path))
        if not objects:
            continue
        added, changed = store.ingest_objects(objects, lean_path)
        total_added += len(added)
        total_changed += len(changed)
        if added or changed:
            print(f"  {lean_path.name}: +{len(added)} new, ~{len(changed)} changed",
                  file=sys.stderr)
        else:
            print(f"  {lean_path.name}: no changes", file=sys.stderr)

    print(f"\nDone. {total_added} added, {total_changed} signatures updated.", file=sys.stderr)
    print(f"Store: {store.path}", file=sys.stderr)


# ======================================================================
# diff
# ======================================================================

def _cmd_diff(args: argparse.Namespace) -> None:
    lean_path = Path(args.lean_file)
    if not lean_path.exists():
        print(f"Error: file not found: {lean_path}", file=sys.stderr)
        sys.exit(1)

    objects = parse_lean_file(str(lean_path))
    if not objects:
        print("No top-level objects found.", file=sys.stderr)
        sys.exit(0)

    store = KnowledgeStore()
    report = find_diff(objects, str(lean_path), store)

    _console.print()
    _console.print(
        f"[bold]Diff:[/bold] {lean_path.name}  "
        f"[dim]({report.total} objects total)[/dim]"
    )
    _console.print()

    if report.new:
        _console.print(f"[bold green]NEW  ({len(report.new)})[/bold green]")
        for obj in report.new:
            _console.print(
                f"  [green]+[/green] [magenta]{obj.kind:12}[/magenta] "
                f"[bold]{obj.name}[/bold]  [dim]line {obj.line_start}[/dim]"
            )
        _console.print()

    if report.changed:
        _console.print(
            f"[bold yellow]CHANGED  ({len(report.changed)})[/bold yellow]"
            "  [dim]— signature differs from stored version[/dim]"
        )
        for obj in report.changed:
            _console.print(
                f"  [yellow]~[/yellow] [magenta]{obj.kind:12}[/magenta] "
                f"[bold]{obj.name}[/bold]  [dim]line {obj.line_start}[/dim]"
            )
        _console.print()

    if report.seen:
        _console.print(f"[bold]SEEN  ({len(report.seen)})[/bold]")
        for obj in report.seen:
            state = report.state_of(obj, str(lean_path), store)
            style = _STATE_STYLE[state]
            line = Text()
            line.append("  · ", style="dim")
            line.append(f"{obj.kind:12}", style="magenta")
            line.append(f" {obj.name}  ", style="bold")
            line.append(state, style=style)
            _console.print(line)
        _console.print()


# ======================================================================
# state
# ======================================================================

def _cmd_state(args: argparse.Namespace) -> None:
    lean_path = Path(args.lean_file)
    if not lean_path.exists():
        print(f"Error: file not found: {lean_path}", file=sys.stderr)
        sys.exit(1)

    objects = parse_lean_file(str(lean_path))
    if not objects:
        print("No top-level objects found.", file=sys.stderr)
        sys.exit(0)

    store = KnowledgeStore()

    if args.all_state:
        for obj in objects:
            store.set_state(make_uid(lean_path, obj.name), args.all_state)
        style = _STATE_STYLE[args.all_state]
        _console.print(
            f"[bold]Set {len(objects)} objects → "
            f"[{style}]{args.all_state}[/{style}][/bold]  ({lean_path.name})"
        )
        return

    if args.name and args.state_value:
        if not any(o.name == args.name for o in objects):
            print(f"Error: object {args.name!r} not found in {lean_path.name}", file=sys.stderr)
            sys.exit(1)
        store.set_state(make_uid(lean_path, args.name), args.state_value)
        style = _STATE_STYLE[args.state_value]
        _console.print(f"Updated [bold]{args.name}[/bold] → [{style}]{args.state_value}[/{style}]")
        return

    table = Table(show_header=True, header_style="bold cyan", expand=True)
    table.add_column("#", width=4, justify="right")
    table.add_column("Kind", width=12)
    table.add_column("Name")
    table.add_column("State", width=10)
    table.add_column("Note")

    for i, obj in enumerate(objects, 1):
        uid = make_uid(lean_path, obj.name)
        entry = store.get_entry(uid) or {}
        state = entry.get("state", "unknown")
        note = entry.get("note", "")
        style = _STATE_STYLE[state]
        table.add_row(
            str(i),
            f"[magenta]{obj.kind}[/magenta]",
            f"[bold]{obj.name}[/bold]",
            Text(state, style=style),
            f"[dim]{note}[/dim]",
        )

    _console.print()
    _console.print(f"[bold]{lean_path.name}[/bold]  [dim]({len(objects)} objects)[/dim]")
    _console.print(table)


# ======================================================================
# graph
# ======================================================================

def _cmd_graph(args: argparse.Namespace) -> None:
    lean_path = Path(args.lean_file)
    if not lean_path.exists():
        print(f"Error: file not found: {lean_path}", file=sys.stderr)
        sys.exit(1)

    output = args.output or str(lean_path.with_name(f"{lean_path.stem}_graph.{args.fmt}"))

    print(f"Parsing {lean_path.name}...", file=sys.stderr)
    objects = parse_lean_file(str(lean_path))
    if not objects:
        print("No top-level objects found.", file=sys.stderr)
        sys.exit(0)

    print(f"Building dependency graph ({len(objects)} objects)...", file=sys.stderr)
    deps = build_dependency_graph(objects)
    render_graph(objects, deps, output_path=output, fmt=args.fmt, view=args.view)


# ======================================================================
# Argument parser
# ======================================================================

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="informalizer",
        description="Informalizer: understand Lean 4 files through natural language.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # -- describe --
    p = sub.add_parser("describe", help="Generate informal descriptions for a file or folder")
    p.add_argument("path", help="Path to a .lean file or a directory")
    p.add_argument("--output", default=None, help="Output path (single-file mode)")
    p.add_argument("--output-dir", default=None, metavar="DIR",
                   help="Write all reports into DIR (folder mode)")
    p.add_argument("--skip-existing", action="store_true",
                   help="Skip files whose report already exists")
    p.add_argument("--no-terminal", action="store_true", help="Suppress rich terminal output")
    p.add_argument("--no-html", action="store_true", help="Skip writing HTML report (default output)")
    p.add_argument("--markdown", action="store_true", help="Also write a Markdown (.md) report")
    p.add_argument("--examples", action="store_true",
                   help="Generate a short Lean 4 example for each object")
    p.add_argument("--api-key", default=None, help="Anthropic API key")
    p.add_argument("--api-key-file", default=None, help="File containing the API key")

    # -- ingest --
    p = sub.add_parser("ingest",
                       help="Register objects from a file or folder into the knowledge store")
    p.add_argument("path", help="Path to a .lean file or a directory")

    # -- diff --
    p = sub.add_parser("diff",
                       help="Show new / changed / seen objects relative to the knowledge store")
    p.add_argument("lean_file", help="Path to a .lean file")

    # -- state --
    p = sub.add_parser("state", help="View or update knowledge states")
    p.add_argument("lean_file", help="Path to a .lean file")
    p.add_argument("name", nargs="?", default=None,
                   help="Object name to update (omit to list all)")
    p.add_argument("state_value", nargs="?", default=None,
                   choices=list(VALID_STATES), metavar="STATE",
                   help="New state: known | learning | unknown")
    p.add_argument("--all", dest="all_state", default=None,
                   choices=list(VALID_STATES), metavar="STATE",
                   help="Set all objects in the file to this state")

    # -- graph --
    p = sub.add_parser("graph", help="Render the dependency graph as an image")
    p.add_argument("lean_file", help="Path to a .lean file")
    p.add_argument("--output", default=None,
                   help="Output path (default: <stem>_graph.<format>)")
    p.add_argument("--format", dest="fmt", default="png",
                   choices=["png", "svg", "pdf"], help="Output format (default: png)")
    p.add_argument("--view", action="store_true", help="Open the image after writing")

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    dispatch = {
        "describe": _cmd_describe,
        "ingest":   _cmd_ingest,
        "diff":     _cmd_diff,
        "state":    _cmd_state,
        "graph":    _cmd_graph,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
