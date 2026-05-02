"""Renders informalizer output to the terminal (via Rich), Markdown, and HTML."""

import html
import re
from datetime import date
from pathlib import Path

import markdown as _md
from rich.console import Console
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from .lean_parser import LeanObject


_console = Console()


# ---------------------------------------------------------------------------
# Category display assets
# ---------------------------------------------------------------------------

# HTML badge: (foreground, background)
_CATEGORY_HTML_COLORS: dict[str, tuple[str, str]] = {
    "Central Result":      ("#1a5c2a", "#d8f3dc"),
    "Key Lemma":           ("#1a3c6e", "#d6eaf8"),
    "Technical Lemma":     ("#7d4e1e", "#fef3e2"),
    "Central Concept":     ("#5c1a6e", "#f3e5f5"),
    "Technical Definition":("#444444", "#f2f2f2"),
    "Core Structure":      ("#7a2000", "#fde8d8"),
    "Instance":            ("#444444", "#f2f2f2"),
    "Axiom":               ("#6b5900", "#fffde7"),
    "Other":               ("#444444", "#f2f2f2"),
}

_CATEGORY_EMOJI: dict[str, str] = {
    "Central Result":      "🏆",
    "Key Lemma":           "⭐",
    "Technical Lemma":     "🔧",
    "Central Concept":     "💡",
    "Technical Definition":"📐",
    "Core Structure":      "🏗️",
    "Instance":            "🔗",
    "Axiom":               "⚡",
    "Other":               "•",
}

_CATEGORY_RICH: dict[str, str] = {
    "Central Result":      "bold green",
    "Key Lemma":           "bold blue",
    "Technical Lemma":     "yellow",
    "Central Concept":     "bold magenta",
    "Technical Definition":"dim",
    "Core Structure":      "bold red",
    "Instance":            "dim",
    "Axiom":               "bold yellow",
    "Other":               "dim",
}


def _category_badge(category: str) -> str:
    """HTML badge for use inside Markdown."""
    fg, bg = _CATEGORY_HTML_COLORS.get(category, ("#444", "#f2f2f2"))
    return (
        f'<span style="background:{bg};color:{fg};padding:2px 8px;'
        f'border-radius:3px;font-size:0.85em;font-weight:bold">'
        f'{category}</span>'
    )


def _display_name(lean_name: str, natural_name: str) -> str:
    if natural_name and natural_name.lower() != lean_name.lower():
        return f"{natural_name} (`{lean_name}`)"
    return f"`{lean_name}`"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _first_sentence(text: str) -> str:
    lines = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#"):
            continue
        if re.fullmatch(r"\*\*[^*]+\*\*:?\s*\w*", s):
            continue
        if s:
            lines.append(s)
    clean = " ".join(lines)
    clean = re.sub(r"^\*\*[^*]{1,40}\*\*\.?\s*", "", clean)
    m = re.search(r"[.!?](?=\s|$)", clean)
    if m:
        return clean[: m.start() + 1]
    return clean[:150] + ("…" if len(clean) > 150 else "")


def _anchor_id(name: str) -> str:
    return "obj-" + re.sub(r"[^A-Za-z0-9_]", "-", name)


def _anchor_href(name: str) -> str:
    return "#" + _anchor_id(name)


def _strip_summary_heading(summary: str) -> str:
    return re.sub(r"^##\s+Summary\s*\n+", "", summary, flags=re.IGNORECASE).strip()


def _normalize_description(desc: str, name: str) -> str:
    desc = re.sub(
        r"^##\s+[`\"]?" + re.escape(name) + r"[`\"]?\s*\n+",
        "",
        desc.strip(),
        flags=re.MULTILINE,
    )
    desc = re.sub(r"^## ", "#### ", desc, flags=re.MULTILINE)
    desc = re.sub(r"^### ", "##### ", desc, flags=re.MULTILINE)
    return desc.strip()


def _add_object_links(text: str, name_to_href: dict[str, str]) -> str:
    parts = re.split(r"(```[\s\S]*?```)", text)
    sorted_names = sorted(name_to_href.keys(), key=len, reverse=True)
    result = []
    for i, part in enumerate(parts):
        if i % 2 == 1:
            result.append(part)
        else:
            for name in sorted_names:
                href = name_to_href[name]
                part = re.sub(
                    r"(?<!\[)`(" + re.escape(name) + r")`",
                    f"[`\\1`]({href})",
                    part,
                )
            result.append(part)
    return "".join(result)


def _build_used_by(
    ordered_objects: list[LeanObject],
    deps: dict[str, set[str]],
) -> dict[str, list[str]]:
    """Reverse deps: for each object, which other objects depend on it."""
    used_by: dict[str, list[str]] = {obj.name: [] for obj in ordered_objects}
    for name, dependencies in deps.items():
        for dep in dependencies:
            if dep in used_by:
                used_by[dep].append(name)
    return used_by


# ---------------------------------------------------------------------------
# Terminal output
# ---------------------------------------------------------------------------

def print_terminal(
    filepath: str,
    ordered_objects: list[LeanObject],
    descriptions: dict[str, str],
    summary: str,
    natural_names: dict[str, str] | None = None,
    categories: dict[str, str] | None = None,
) -> None:
    natural_names = natural_names or {}
    categories = categories or {}

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
    table.add_column("Category", width=22)
    table.add_column("One-liner")
    for i, obj in enumerate(ordered_objects, 1):
        cat = categories.get(obj.name, "")
        cat_style = _CATEGORY_RICH.get(cat, "dim")
        nat = natural_names.get(obj.name, "")
        name_cell = (
            f"[bold]{nat}[/bold] [dim]({obj.name})[/dim]"
            if nat and nat.lower() != obj.name.lower()
            else f"[bold]{obj.name}[/bold]"
        )
        table.add_row(
            str(i),
            f"[magenta]{obj.kind}[/magenta]",
            name_cell,
            Text(cat, style=cat_style),
            _first_sentence(descriptions.get(obj.name, "")),
        )
    _console.print(table)
    _console.print()
    _console.print(Rule("[bold yellow]OBJECTS — dependency order[/bold yellow]"))

    for i, obj in enumerate(ordered_objects, 1):
        cat = categories.get(obj.name, "")
        cat_style = _CATEGORY_RICH.get(cat, "dim")
        nat = natural_names.get(obj.name, "")

        _console.print()
        header = Text()
        header.append(f"{i}. ", style="bold")
        if nat and nat.lower() != obj.name.lower():
            header.append(nat, style="bold white")
            header.append(f" ({obj.name})", style="dim")
        else:
            header.append(obj.name, style="bold white")
        header.append(f"  (lines {obj.line_start}–{obj.line_end})", style="dim")
        _console.print(header)

        if cat:
            emoji = _CATEGORY_EMOJI.get(cat, "")
            _console.print(
                f"  [{cat_style}]{emoji} {cat}[/{cat_style}]  "
                f"[magenta]{obj.kind}[/magenta]"
            )

        sig = obj.signature
        if len(sig) > 200:
            sig = sig[:200].rstrip() + "  …"
        _console.print(f"[dim]{sig}[/dim]")
        _console.print()
        _console.print(descriptions.get(obj.name, "[no description]"))
        _console.print(Rule(style="dim"))

    _console.print()


# ---------------------------------------------------------------------------
# Markdown output
# ---------------------------------------------------------------------------

def write_markdown(
    filepath: str,
    ordered_objects: list[LeanObject],
    descriptions: dict[str, str],
    summary: str,
    output_path: str,
    natural_names: dict[str, str] | None = None,
    categories: dict[str, str] | None = None,
    deps: dict[str, set[str]] | None = None,
    examples: dict[str, str] | None = None,
) -> None:
    natural_names = natural_names or {}
    categories = categories or {}
    deps = deps or {}
    examples = examples or {}

    used_by = _build_used_by(ordered_objects, deps)

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
        "| # | Kind | Category | Name | Summary |",
        "|---|------|----------|------|---------|",
    ]

    for i, obj in enumerate(ordered_objects, 1):
        cat = categories.get(obj.name, "")
        blurb = _first_sentence(descriptions.get(obj.name, "")).replace("|", "\\|")
        href = name_to_href[obj.name]
        disp = _display_name(obj.name, natural_names.get(obj.name, ""))
        lines.append(f"| {i} | {obj.kind} | {cat} | [{disp}]({href}) | {blurb} |")

    lines += [
        "",
        "---",
        "",
        "## Objects (Dependency Order)",
        "",
    ]

    for i, obj in enumerate(ordered_objects, 1):
        cat = categories.get(obj.name, "")
        nat = natural_names.get(obj.name, "")
        blurb = _first_sentence(descriptions.get(obj.name, ""))
        desc = _normalize_description(
            descriptions.get(obj.name, "_No description available._"), obj.name
        )
        disp = _display_name(obj.name, nat)

        badge_line = ""
        if cat:
            badge_line = _category_badge(cat) + f"&ensp;`{obj.kind}`"

        lines += [
            f'<a id="{_anchor_id(obj.name)}"></a>',
            f"### {i}. {disp} _(lines {obj.line_start}–{obj.line_end})_",
            "",
        ]
        if badge_line:
            lines += [badge_line, ""]
        lines += [
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
        ]

        example = examples.get(obj.name, "")
        if example:
            lines += [
                "<details>",
                "<summary>View example</summary>",
                "",
                example,
                "",
                "</details>",
                "",
            ]

        users = used_by.get(obj.name, [])
        if users:
            user_links = ", ".join(
                f"[`{u}`]({name_to_href[u]})"
                for u in users if u in name_to_href
            )
            lines.append(f"**Used by:** {user_links}")
            lines.append("")

        lines.append("---")
        lines.append("")

    full_text = "\n".join(lines)
    full_text = _add_object_links(full_text, name_to_href)
    Path(output_path).write_text(full_text, encoding="utf-8")


# ---------------------------------------------------------------------------
# HTML output
# ---------------------------------------------------------------------------

_HTML_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
  max-width: 1020px;
  margin: 0 auto;
  padding: 2rem 2.5rem;
  color: #212529;
  line-height: 1.65;
  background: #fff;
}
h1 { font-size: 1.75rem; margin-bottom: 0.25rem; }
h2 {
  font-size: 1.3rem;
  margin: 2.5rem 0 1rem;
  padding-bottom: 0.4rem;
  border-bottom: 2px solid #dee2e6;
}
h3 { font-size: 1.05rem; margin: 0; }
h4 { font-size: 0.95rem; margin: 0.8rem 0 0.3rem; }
a { color: #0055cc; text-decoration: none; }
a:hover { text-decoration: underline; }
code {
  background: #f3f4f6;
  padding: 0.1em 0.35em;
  border-radius: 3px;
  font-size: 0.875em;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', monospace;
}
pre {
  background: #f6f8fa;
  padding: 1rem 1.2rem;
  border-radius: 6px;
  overflow-x: auto;
  border: 1px solid #e0e4e8;
  margin: 0.6rem 0;
}
pre code { background: none; padding: 0; font-size: 0.85em; }
p { margin-bottom: 0.75rem; }
ul, ol { margin: 0.4rem 0 0.8rem 1.5rem; }
li { margin-bottom: 0.2rem; }

/* Header */
.site-header {
  padding-bottom: 1.2rem;
  margin-bottom: 0.5rem;
  border-bottom: 3px solid #0055cc;
}
.site-header h1 code { font-size: 1.5rem; background: none; padding: 0; }
.meta { color: #6c757d; font-size: 0.88rem; margin-top: 0.4rem; }

/* Badge */
.badge {
  display: inline-block;
  padding: 2px 9px;
  border-radius: 3px;
  font-size: 0.78em;
  font-weight: 700;
  white-space: nowrap;
  vertical-align: middle;
}

/* Quick-reference table */
.ref-table { width: 100%; border-collapse: collapse; font-size: 0.88em; margin-top: 0.5rem; }
.ref-table th {
  background: #f8f9fa;
  font-weight: 600;
  text-align: left;
  padding: 0.55rem 0.75rem;
  border-bottom: 2px solid #dee2e6;
}
.ref-table td { padding: 0.45rem 0.75rem; border-bottom: 1px solid #f0f0f0; vertical-align: top; }
.ref-table tr:hover td { background: #fafbfc; }
.ref-table td:first-child { font-weight: 600; color: #6c757d; width: 2.5rem; text-align: right; }

/* Object cards */
#objects { margin-top: 1rem; }
.object-card {
  border: 1px solid #dee2e6;
  border-radius: 8px;
  padding: 1.2rem 1.5rem;
  margin-bottom: 1.5rem;
  scroll-margin-top: 1rem;
}
.object-header { display: flex; align-items: flex-start; gap: 1rem; margin-bottom: 0.75rem; }
.object-num {
  background: #0055cc;
  color: #fff;
  min-width: 2rem;
  height: 2rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 0.82rem;
  flex-shrink: 0;
}
.object-title { flex: 1; }
.object-meta { font-size: 0.82em; color: #6c757d; margin-top: 0.35rem; display: block; }
code.kind { background: #e8f0fe; color: #1a3c8e; padding: 0.1em 0.4em; }
.one-liner { color: #495057; font-style: italic; margin-bottom: 0.9rem; }
details.sig { margin-bottom: 0.9rem; }
details.sig summary {
  cursor: pointer;
  color: #0055cc;
  font-size: 0.88em;
  user-select: none;
  padding: 0.2rem 0;
}
details.sig summary:hover { text-decoration: underline; }
.description { margin-top: 0.4rem; }
.used-by {
  margin-top: 1rem;
  padding: 0.55rem 0.85rem;
  background: #f8f9fa;
  border-left: 3px solid #adb5bd;
  border-radius: 0 4px 4px 0;
  font-size: 0.88em;
}
.used-by strong { color: #495057; }
.back-to-top {
  display: block;
  text-align: right;
  font-size: 0.8em;
  margin-top: 0.9rem;
  padding-top: 0.5rem;
  border-top: 1px solid #f0f0f0;
}
.back-to-top a { color: #adb5bd; }
.back-to-top a:hover { color: #0055cc; text-decoration: none; }
"""

_HTML_MATHJAX = """
<script>
MathJax = {
  tex: {
    inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
    displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']]
  },
  svg: { fontCache: 'global' }
};
</script>
<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>
"""


def _render_md(text: str, name_to_href: dict[str, str]) -> str:
    """Link object names then convert Markdown to HTML."""
    linked = _add_object_links(text, name_to_href)
    return _md.markdown(linked, extensions=["fenced_code", "tables"])


def write_html(
    filepath: str,
    ordered_objects: list[LeanObject],
    descriptions: dict[str, str],
    summary: str,
    output_path: str,
    natural_names: dict[str, str] | None = None,
    categories: dict[str, str] | None = None,
    deps: dict[str, set[str]] | None = None,
    examples: dict[str, str] | None = None,
) -> None:
    natural_names = natural_names or {}
    categories = categories or {}
    deps = deps or {}
    examples = examples or {}

    used_by = _build_used_by(ordered_objects, deps)

    filename = Path(filepath).name
    today = date.today().isoformat()
    name_to_href = {obj.name: _anchor_href(obj.name) for obj in ordered_objects}

    summary_text = _strip_summary_heading(summary)
    summary_html = _render_md(summary_text, name_to_href)

    parts: list[str] = []

    # ---- <head> ----
    parts.append(f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Informalizer Report: {html.escape(filename)}</title>
  {_HTML_MATHJAX}
  <style>{_HTML_CSS}</style>
</head>
<body>
""")

    # ---- header ----
    parts.append(f"""<header id="top" class="site-header">
  <h1>Informalizer Report: <code>{html.escape(filename)}</code></h1>
  <p class="meta">Generated on {today}</p>
</header>
<main>
""")

    # ---- summary ----
    parts.append(f'<section id="summary">\n<h2>Summary</h2>\n{summary_html}\n</section>\n')

    # ---- quick reference ----
    parts.append('<section id="quick-reference">\n<h2>Quick Reference</h2>\n')
    parts.append('<table class="ref-table"><thead><tr>'
                 '<th>#</th><th>Kind</th><th>Category</th><th>Name</th><th>Summary</th>'
                 '</tr></thead><tbody>\n')

    for i, obj in enumerate(ordered_objects, 1):
        cat = categories.get(obj.name, "")
        blurb = html.escape(_first_sentence(descriptions.get(obj.name, "")))
        href = name_to_href[obj.name]
        nat = natural_names.get(obj.name, "")
        if nat and nat.lower() != obj.name.lower():
            disp_html = f'{html.escape(nat)} <code>{html.escape(obj.name)}</code>'
        else:
            disp_html = f'<code>{html.escape(obj.name)}</code>'
        badge_html = _category_badge(cat) if cat else ""
        parts.append(
            f'<tr><td>{i}</td>'
            f'<td><code>{html.escape(obj.kind)}</code></td>'
            f'<td>{badge_html}</td>'
            f'<td><a href="{href}">{disp_html}</a></td>'
            f'<td>{blurb}</td></tr>\n'
        )

    parts.append('</tbody></table>\n</section>\n')

    # ---- objects ----
    parts.append('<section id="objects">\n<h2>Objects (Dependency Order)</h2>\n')

    for i, obj in enumerate(ordered_objects, 1):
        cat = categories.get(obj.name, "")
        nat = natural_names.get(obj.name, "")
        blurb = html.escape(_first_sentence(descriptions.get(obj.name, "")))
        desc_md = _normalize_description(
            descriptions.get(obj.name, "No description available."), obj.name
        )
        desc_html = _render_md(desc_md, name_to_href)

        anchor = _anchor_id(obj.name)
        badge_html = _category_badge(cat) if cat else ""

        if nat and nat.lower() != obj.name.lower():
            header_name = f'{html.escape(nat)} <code>{html.escape(obj.name)}</code>'
        else:
            header_name = f'<code>{html.escape(obj.name)}</code>'

        sig_escaped = html.escape(obj.signature)

        # Used by
        users = used_by.get(obj.name, [])
        used_by_html = ""
        if users:
            user_links = ", ".join(
                f'<a href="{name_to_href[u]}"><code>{html.escape(u)}</code></a>'
                for u in users if u in name_to_href
            )
            used_by_html = (
                f'<div class="used-by"><strong>Used by:</strong> {user_links}</div>'
            )

        # Example
        example_html = ""
        raw_example = examples.get(obj.name, "")
        if raw_example:
            example_html = (
                '<details class="sig">'
                '<summary>View example</summary>'
                f'{_render_md(raw_example, name_to_href)}'
                '</details>'
            )

        parts.append(f"""<div id="{anchor}" class="object-card">
  <div class="object-header">
    <div class="object-num">{i}</div>
    <div class="object-title">
      <h3>{header_name}</h3>
      <span class="object-meta">
        {badge_html}&ensp;<code class="kind">{html.escape(obj.kind)}</code>
        &mdash; lines {obj.line_start}&ndash;{obj.line_end}
      </span>
    </div>
  </div>
  <p class="one-liner">{blurb}</p>
  <details class="sig">
    <summary>View signature</summary>
    <pre><code>{sig_escaped}</code></pre>
  </details>
  <div class="description">{desc_html}</div>
  {example_html}
  {used_by_html}
  <div class="back-to-top"><a href="#top">&#8593; Top</a></div>
</div>
""")

    parts.append('</section>\n</main>\n</body>\n</html>\n')

    Path(output_path).write_text("".join(parts), encoding="utf-8")
