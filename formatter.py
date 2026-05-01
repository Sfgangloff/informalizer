"""Renders informalizer output to the terminal (via Rich) and to a Markdown file."""

import re
from datetime import date
from pathlib import Path

from rich.console import Console
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from lean_parser import LeanObject


_console = Console()


def _first_sentence(text: str) -> str:
    """Extract a clean one-liner from a markdown description."""
    lines = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#"):
            continue
        # skip lines that are only a bold label, e.g. "**Kind:** Definition"
        if re.fullmatch(r"\*\*[^*]+\*\*:?\s*\w*", s):
            continue
        if s:
            lines.append(s)
    clean = " ".join(lines)
    # strip a leading bold phrase like "**Definition.**" or "**`foo`** is …"
    clean = re.sub(r"^\*\*[^*]{1,40}\*\*\.?\s*", "", clean)
    # first sentence boundary
    m = re.search(r"[.!?](?=\s|$)", clean)
    if m:
        return clean[: m.start() + 1]
    return clean[:150] + ("…" if len(clean) > 150 else "")


def _anchor_id(name: str) -> str:
    """Generate the HTML id attribute value for an object's anchor."""
    return "obj-" + re.sub(r"[^A-Za-z0-9_]", "-", name)


def _anchor_href(name: str) -> str:
    """Generate the markdown link href for an object."""
    return "#" + _anchor_id(name)


def _strip_summary_heading(summary: str) -> str:
    """Remove a leading '## Summary' heading the AI may have added."""
    return re.sub(r"^##\s+Summary\s*\n+", "", summary, flags=re.IGNORECASE).strip()


def _normalize_description(desc: str, name: str) -> str:
    """Remove redundant title heading and downgrade remaining headings."""
    # Strip a leading ## heading that repeats the object name
    desc = re.sub(
        r"^##\s+[`\"]?" + re.escape(name) + r"[`\"]?\s*\n+",
        "",
        desc.strip(),
        flags=re.MULTILINE,
    )
    # Downgrade ## → #### and ### → ##### so they stay smaller than the H3 section header
    desc = re.sub(r"^## ", "#### ", desc, flags=re.MULTILINE)
    desc = re.sub(r"^### ", "##### ", desc, flags=re.MULTILINE)
    return desc.strip()


def _add_object_links(text: str, name_to_href: dict[str, str]) -> str:
    """
    Replace `objectName` references with markdown links, skipping fenced code blocks.
    Longer names are processed first to avoid partial matches.
    """
    parts = re.split(r"(```[\s\S]*?```)", text)
    sorted_names = sorted(name_to_href.keys(), key=len, reverse=True)
    result = []
    for i, part in enumerate(parts):
        if i % 2 == 1:  # inside a fenced code block — leave untouched
            result.append(part)
        else:
            for name in sorted_names:
                href = name_to_href[name]
                # Match `name` not already preceded by [ (i.e. not already a link)
                part = re.sub(
                    r"(?<!\[)`(" + re.escape(name) + r")`",
                    f"[`\\1`]({href})",
                    part,
                )
            result.append(part)
    return "".join(result)


def print_terminal(
    filepath: str,
    ordered_objects: list[LeanObject],
    descriptions: dict[str, str],
    summary: str,
) -> None:
    """Print a styled report to the terminal using Rich."""
    _console.print()
    _console.print(Rule("[bold cyan]INFORMALIZER REPORT[/bold cyan]"))
    _console.print(f"[bold]File:[/bold] {filepath}")
    _console.print(f"[bold]Objects found:[/bold] {len(ordered_objects)}")
    _console.print(Rule())

    _console.print("\n[bold green]SUMMARY[/bold green]\n")
    _console.print(_strip_summary_heading(summary))
    _console.print()

    table = Table(show_header=True, header_style="bold cyan", expand=True)
    table.add_column("#", width=4, justify="right")
    table.add_column("Kind", width=12)
    table.add_column("Name")
    table.add_column("One-liner")
    for i, obj in enumerate(ordered_objects, 1):
        table.add_row(
            str(i),
            f"[magenta]{obj.kind}[/magenta]",
            f"[bold]{obj.name}[/bold]",
            _first_sentence(descriptions.get(obj.name, "")),
        )
    _console.print(table)
    _console.print()
    _console.print(Rule("[bold yellow]OBJECTS — dependency order[/bold yellow]"))

    for i, obj in enumerate(ordered_objects, 1):
        _console.print()
        header = Text()
        header.append(f"{i}. ", style="bold")
        header.append(f"[{obj.kind}] ", style="bold magenta")
        header.append(obj.name, style="bold white")
        header.append(f"  (lines {obj.line_start}–{obj.line_end})", style="dim")
        _console.print(header)

        sig = obj.signature
        if len(sig) > 200:
            sig = sig[:200].rstrip() + "  …"
        _console.print(f"[dim]{sig}[/dim]")
        _console.print()
        _console.print(descriptions.get(obj.name, "[no description]"))
        _console.print(Rule(style="dim"))

    _console.print()


def write_markdown(
    filepath: str,
    ordered_objects: list[LeanObject],
    descriptions: dict[str, str],
    summary: str,
    output_path: str,
) -> None:
    """Write the full Markdown report with anchors and cross-reference links."""
    filename = Path(filepath).name
    today = date.today().isoformat()

    name_to_href = {obj.name: _anchor_href(obj.name) for obj in ordered_objects}
    summary = _strip_summary_heading(summary)

    lines: list[str] = [
        f"# Informalizer Report: `{filename}`",
        f"_Generated on {today}_",
        "",
        "## Summary",
        "",
        summary,
        "",
        "---",
        "",
        "## Quick Reference",
        "",
        "| # | Kind | Name | Summary |",
        "|---|------|------|---------|",
    ]
    for i, obj in enumerate(ordered_objects, 1):
        blurb = _first_sentence(descriptions.get(obj.name, "")).replace("|", "\\|")
        href = name_to_href[obj.name]
        lines.append(f"| {i} | {obj.kind} | [`{obj.name}`]({href}) | {blurb} |")

    lines += [
        "",
        "---",
        "",
        "## Objects (Dependency Order)",
        "",
    ]

    for i, obj in enumerate(ordered_objects, 1):
        blurb = _first_sentence(descriptions.get(obj.name, ""))
        desc = _normalize_description(
            descriptions.get(obj.name, "_No description available._"), obj.name
        )
        lines += [
            f'<a id="{_anchor_id(obj.name)}"></a>',
            f"### {i}. [{obj.kind}] `{obj.name}` _(lines {obj.line_start}–{obj.line_end})_",
            "",
            f"_{blurb}_",
            "",
            "<details>",
            "<summary>View details</summary>",
            "",
            "**Signature:**",
            "```lean",
            obj.signature,
            "```",
            "",
            desc,
            "",
            "</details>",
            "",
            "---",
            "",
        ]

    full_text = "\n".join(lines)
    full_text = _add_object_links(full_text, name_to_href)
    Path(output_path).write_text(full_text, encoding="utf-8")
