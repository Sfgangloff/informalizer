"""Generate a static HTML wiki from the corpus.

Layout:
  {output}/index.html              — site index (per-file listing + name index)
  {output}/files/{slug}.html       — one page per ingested .lean file
  {output}/static/site.css         — shared stylesheet
"""

import html
import re
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Optional

import markdown as _md
from jinja2 import Environment

from .corpus import (
    ObjectRecord,
    get_all_objects,
    get_relationships_from,
    get_relationships_to,
    name_to_uid_index,
)
from .embedder import top_k_similar
from .knowledge_store import KnowledgeStore, make_uid as ks_make_uid


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

_SITE_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
  max-width: 1080px;
  margin: 0 auto;
  padding: 2rem 2.5rem 4rem;
  color: #212529;
  line-height: 1.65;
  background: #fff;
}
h1 { font-size: 1.7rem; margin-bottom: 0.4rem; }
h2 { font-size: 1.25rem; margin: 2rem 0 0.8rem; padding-bottom: 0.3rem; border-bottom: 2px solid #dee2e6; }
h3 { font-size: 1.02rem; margin: 0.2rem 0; }
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
  padding: 0.9rem 1.1rem;
  border-radius: 6px;
  overflow-x: auto;
  border: 1px solid #e0e4e8;
  margin: 0.5rem 0;
}
pre code { background: none; padding: 0; font-size: 0.85em; }

/* Site header */
.site-header {
  padding-bottom: 1.0rem;
  margin-bottom: 1.4rem;
  border-bottom: 3px solid #0055cc;
}
.site-header .meta { color: #6c757d; font-size: 0.88rem; margin-top: 0.4rem; }
.site-header nav { margin-top: 0.6rem; font-size: 0.92rem; }
.site-header nav a { margin-right: 1rem; }

/* Search */
#search { width: 100%; padding: 0.55rem 0.8rem; font-size: 1rem;
  border: 1px solid #ced4da; border-radius: 6px; margin-bottom: 1rem; }

/* File index list */
.file-list { list-style: none; margin: 0; padding: 0; }
.file-list li { padding: 0.55rem 0; border-bottom: 1px solid #f0f0f0; }
.file-list .count { color: #6c757d; font-size: 0.85em; margin-left: 0.4rem; }

/* Name index */
.name-index { columns: 2; column-gap: 1.5rem; font-size: 0.9rem; }
.name-index a { display: block; padding: 0.15rem 0; }

/* Badges */
.badge {
  display: inline-block;
  padding: 2px 9px;
  border-radius: 3px;
  font-size: 0.78em;
  font-weight: 700;
  white-space: nowrap;
  vertical-align: middle;
}
code.kind { background: #e8f0fe; color: #1a3c8e; padding: 0.1em 0.4em; }

.ks-known    { background: #d8f3dc; color: #1a5c2a; }
.ks-learning { background: #fef3e2; color: #7d4e1e; }
.ks-unknown  { background: #f8d7da; color: #842029; }

/* Object cards */
.object-card {
  border: 1px solid #dee2e6;
  border-radius: 8px;
  padding: 1.1rem 1.3rem;
  margin-bottom: 1.2rem;
  scroll-margin-top: 1rem;
}
.object-header {
  display: flex; align-items: center; gap: 0.7rem;
  margin-bottom: 0.6rem; flex-wrap: wrap;
}
.object-header h3 { flex: 1 1 auto; }
.object-meta { font-size: 0.82em; color: #6c757d; margin-top: 0.3rem; }
details.sig summary {
  cursor: pointer;
  color: #0055cc;
  font-size: 0.88em;
  user-select: none;
  padding: 0.2rem 0;
}
details.sig summary:hover { text-decoration: underline; }
.description { margin-top: 0.5rem; }
.related {
  margin-top: 0.9rem;
  padding: 0.55rem 0.85rem;
  background: #f8f9fa;
  border-left: 3px solid #adb5bd;
  border-radius: 0 4px 4px 0;
  font-size: 0.88em;
}
.related strong { color: #495057; }
.related ul { margin-left: 1.1rem; }
.back-to-top {
  display: block;
  text-align: right;
  font-size: 0.8em;
  margin-top: 0.7rem;
  padding-top: 0.4rem;
  border-top: 1px solid #f0f0f0;
}
.back-to-top a { color: #adb5bd; }
.back-to-top a:hover { color: #0055cc; }
"""

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

_INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Informalizer wiki</title>
<link rel="stylesheet" href="static/site.css">
</head>
<body>
<header class="site-header">
  <h1>Informalizer wiki</h1>
  <div class="meta">
    {{ object_count }} object{{ '' if object_count == 1 else 's' }}
    across {{ files|length }} file{{ '' if files|length == 1 else 's' }}
    · generated {{ generated_on }}
  </div>
  <nav><a href="index.html">Index</a></nav>
</header>

<input id="search" type="search" placeholder="Filter by name…" autocomplete="off">

<h2>Files</h2>
<ul class="file-list" id="file-list">
{% for f in files %}
  <li data-search="{{ f.display_path|lower }} {{ f.names_blob }}">
    <a href="files/{{ f.slug }}.html">{{ f.display_path }}</a>
    <span class="count">({{ f.count }} object{{ '' if f.count == 1 else 's' }})</span>
  </li>
{% endfor %}
</ul>

<h2>Name index</h2>
<div class="name-index" id="name-index">
{% for n in names %}
  <a href="files/{{ n.file_slug }}.html#{{ n.anchor }}" data-search="{{ n.name|lower }}">{{ n.name }}</a>
{% endfor %}
</div>

<script>
(() => {
  const input = document.getElementById('search');
  const fileItems = Array.from(document.querySelectorAll('#file-list li'));
  const nameItems = Array.from(document.querySelectorAll('#name-index a'));
  input.addEventListener('input', () => {
    const q = input.value.trim().toLowerCase();
    fileItems.forEach(el => {
      el.style.display = (!q || el.dataset.search.includes(q)) ? '' : 'none';
    });
    nameItems.forEach(el => {
      el.style.display = (!q || el.dataset.search.includes(q)) ? '' : 'none';
    });
  });
})();
</script>
</body>
</html>
"""

_FILE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{{ display_path }} · Informalizer wiki</title>
<link rel="stylesheet" href="../static/site.css">
</head>
<body>
<header class="site-header">
  <h1>{{ display_path }}</h1>
  <div class="meta">{{ records|length }} object{{ '' if records|length == 1 else 's' }}</div>
  <nav><a href="../index.html">← back to index</a></nav>
</header>

<h2>Contents</h2>
<ul>
{% for r in records %}
  <li>
    <a href="#{{ r.anchor }}">{{ r.display_name }}</a>
    <code class="kind">{{ r.kind }}</code>
    <span class="badge {{ r.state_class }}">{{ r.state }}</span>
  </li>
{% endfor %}
</ul>

<h2>Objects</h2>
{% for r in records %}
<section class="object-card" id="{{ r.anchor }}">
  <div class="object-header">
    <h3>{{ r.display_name }}</h3>
    <code class="kind">{{ r.kind }}</code>
    <span class="badge {{ r.state_class }}">{{ r.state }}</span>
  </div>
  <div class="object-meta">lines {{ r.line_start }}–{{ r.line_end }}</div>
  <details class="sig"><summary>signature</summary>
<pre><code class="language-lean">{{ r.signature_html }}</code></pre>
  </details>
  <div class="description">{{ r.description_html|safe }}</div>
  {% if r.example_html %}
  <div class="example">{{ r.example_html|safe }}</div>
  {% endif %}
  {% if r.depends_on or r.used_by_in_file %}
  <div class="related">
    {% if r.depends_on %}
    <div><strong>Depends on:</strong>
      {% for d in r.depends_on %}<a href="#{{ d.anchor }}">{{ d.label }}</a>{{ ", " if not loop.last }}{% endfor %}
    </div>
    {% endif %}
    {% if r.used_by_in_file %}
    <div><strong>Used by:</strong>
      {% for d in r.used_by_in_file %}<a href="#{{ d.anchor }}">{{ d.label }}</a>{{ ", " if not loop.last }}{% endfor %}
    </div>
    {% endif %}
  </div>
  {% endif %}
  {% if r.uses_external or r.used_externally or r.similar %}
  <div class="related">
    {% if r.uses_external %}
    <div><strong>Uses (other files):</strong>
      <ul>{% for d in r.uses_external %}<li><a href="{{ d.href }}">{{ d.label }}</a> <span class="meta">{{ d.source }}</span></li>{% endfor %}</ul>
    </div>
    {% endif %}
    {% if r.used_externally %}
    <div><strong>Used by (other files):</strong>
      <ul>{% for d in r.used_externally %}<li><a href="{{ d.href }}">{{ d.label }}</a> <span class="meta">{{ d.source }}</span></li>{% endfor %}</ul>
    </div>
    {% endif %}
    {% if r.similar %}
    <div><strong>Similar across the corpus:</strong>
      <ul>{% for d in r.similar %}<li><a href="{{ d.href }}">{{ d.label }}</a> <span class="meta">{{ d.source }} · score {{ d.score }}</span></li>{% endfor %}</ul>
    </div>
    {% endif %}
  </div>
  {% endif %}
  <div class="back-to-top"><a href="#top">↑ back to top</a></div>
</section>
{% endfor %}
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slugify(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "-", text).strip("-")


def _anchor(name: str) -> str:
    return "obj-" + _slugify(name)


def _display_name(rec: ObjectRecord) -> str:
    if rec.natural_name and rec.natural_name.lower() != rec.name.lower():
        return f"{rec.natural_name} ({rec.name})"
    return rec.name


def _build_file_slugs(records: list[ObjectRecord]) -> dict[str, str]:
    """Map source_file (absolute) → URL slug, ensuring uniqueness."""
    sources = sorted({r.source_file for r in records})
    used: set[str] = set()
    out: dict[str, str] = {}
    for src in sources:
        base = _slugify(Path(src).stem) or "file"
        slug = base
        i = 2
        while slug in used:
            slug = f"{base}-{i}"
            i += 1
        used.add(slug)
        out[src] = slug
    return out


def _common_root(paths: list[str]) -> Path:
    """Common ancestor *directory* of the given files (always returns a directory,
    so a single-file corpus still has a sensible relative display path)."""
    if not paths:
        return Path()
    parents = [Path(p).resolve().parent.parts for p in paths]
    common: list[str] = []
    for items in zip(*parents):
        if all(x == items[0] for x in items):
            common.append(items[0])
        else:
            break
    return Path(*common) if common else Path("/")


def _display_path(source_file: str, root: Path) -> str:
    p = Path(source_file)
    try:
        rel = p.relative_to(root)
    except ValueError:
        return p.name
    rel_str = str(rel)
    return rel_str if rel_str not in ("", ".") else p.name


def _linkify(text: str, name_to_href: dict[str, str]) -> str:
    """Replace `name` in description with a link to its anchor, only inside
    inline-code spans (to avoid rewriting prose words that happen to coincide)."""
    if not name_to_href:
        return text
    parts = re.split(r"(```[\s\S]*?```)", text)
    sorted_names = sorted(name_to_href.keys(), key=len, reverse=True)
    out = []
    for i, part in enumerate(parts):
        if i % 2 == 1:
            out.append(part)
            continue
        for name in sorted_names:
            href = name_to_href[name]
            part = re.sub(
                r"(?<!\[)`(" + re.escape(name) + r")`",
                f"[`\\1`]({href})",
                part,
            )
        out.append(part)
    return "".join(out)


def _render_md(text: str, name_to_href: dict[str, str]) -> str:
    if not text.strip():
        return ""
    linked = _linkify(text, name_to_href)
    return _md.markdown(linked, extensions=["fenced_code", "tables"])


def _render_example(example: str, name_to_href: dict[str, str]) -> str:
    if not example.strip():
        return ""
    body = example.strip()
    if "```" not in body:
        body = "```lean\n" + body.rstrip() + "\n```"
    return _render_md("**Example.**\n\n" + body, name_to_href)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_wiki(
    conn,
    output_dir: str | Path,
    knowledge_store: Optional[KnowledgeStore] = None,
    similar_k: int = 3,
) -> None:
    output = Path(output_dir)
    (output / "files").mkdir(parents=True, exist_ok=True)
    (output / "static").mkdir(parents=True, exist_ok=True)

    records = get_all_objects(conn)
    if not records:
        print("wiki: corpus is empty — nothing to generate.")
        return

    ks = knowledge_store or KnowledgeStore()
    file_slugs = _build_file_slugs(records)
    root = _common_root(list(file_slugs.keys()))

    # name-to-href used for linkification *within* a file's page (we link to
    # the same-page anchor for in-file objects, and to the other file's page
    # for objects living elsewhere). Built per-page.
    by_file: dict[str, list[ObjectRecord]] = defaultdict(list)
    for r in records:
        by_file[r.source_file].append(r)
    for src in by_file:
        by_file[src].sort(key=lambda r: r.line_start)

    name_index_global = name_to_uid_index(conn)
    uid_to_record = {r.uid: r for r in records}

    env = Environment(autoescape=False)
    file_template = env.from_string(_FILE_TEMPLATE)
    index_template = env.from_string(_INDEX_TEMPLATE)

    # ---- per-file pages ----
    for src, file_records in sorted(by_file.items()):
        slug = file_slugs[src]
        display_path = _display_path(src, root)

        # Local linkify map: any name with a unique uid in the corpus
        # becomes a link to its appropriate page.
        name_to_href: dict[str, str] = {}
        for name, uids in name_index_global.items():
            if len(uids) > 1:
                continue
            target = uid_to_record[uids[0]]
            if target.source_file == src:
                name_to_href[name] = "#" + _anchor(name)
            else:
                target_slug = file_slugs[target.source_file]
                name_to_href[name] = f"{target_slug}.html#{_anchor(name)}"

        page_records = []
        for rec in file_records:
            uid = rec.uid
            state = ks.get_state(ks_make_uid(rec.source_file, rec.name))
            state_class = f"ks-{state}"

            # Intra-file deps / dependents
            depends_on = []
            used_by_in_file = []
            uses_external = []
            used_externally = []

            for rel in get_relationships_from(conn, uid):
                target = uid_to_record.get(rel.to_uid)
                if not target:
                    continue
                if rel.rel_type == "depends_on":
                    depends_on.append({
                        "anchor": _anchor(target.name),
                        "label": target.name,
                    })
                elif rel.rel_type == "uses":
                    uses_external.append({
                        "href": f"{file_slugs[target.source_file]}.html#{_anchor(target.name)}",
                        "label": target.name,
                        "source": _display_path(target.source_file, root),
                    })

            for rel in get_relationships_to(conn, uid):
                source = uid_to_record.get(rel.from_uid)
                if not source:
                    continue
                if rel.rel_type == "depends_on" and source.source_file == src:
                    used_by_in_file.append({
                        "anchor": _anchor(source.name),
                        "label": source.name,
                    })
                elif rel.rel_type == "uses":
                    used_externally.append({
                        "href": f"{file_slugs[source.source_file]}.html#{_anchor(source.name)}",
                        "label": source.name,
                        "source": _display_path(source.source_file, root),
                    })

            # Cross-corpus similarity
            similar = []
            for sim_uid, score in top_k_similar(conn, uid, k=similar_k, exclude_same_file=True):
                target = uid_to_record.get(sim_uid)
                if not target:
                    continue
                similar.append({
                    "href": f"{file_slugs[target.source_file]}.html#{_anchor(target.name)}",
                    "label": target.name,
                    "source": _display_path(target.source_file, root),
                    "score": f"{score:.2f}",
                })

            description_html = _render_md(rec.description, name_to_href)
            example_html = _render_example(rec.example, name_to_href)

            page_records.append({
                "anchor": _anchor(rec.name),
                "display_name": _display_name(rec),
                "kind": rec.kind,
                "state": state,
                "state_class": state_class,
                "line_start": rec.line_start,
                "line_end": rec.line_end,
                "signature_html": html.escape(rec.signature),
                "description_html": description_html,
                "example_html": example_html,
                "depends_on": depends_on,
                "used_by_in_file": used_by_in_file,
                "uses_external": uses_external,
                "used_externally": used_externally,
                "similar": similar,
            })

        page_html = file_template.render(
            display_path=display_path,
            records=page_records,
        )
        (output / "files" / f"{slug}.html").write_text(page_html, encoding="utf-8")

    # ---- index page ----
    index_files = []
    for src in sorted(by_file.keys()):
        recs = by_file[src]
        names_blob = " ".join(r.name.lower() for r in recs)
        index_files.append({
            "slug": file_slugs[src],
            "display_path": _display_path(src, root),
            "count": len(recs),
            "names_blob": names_blob,
        })

    name_entries = []
    for r in sorted(records, key=lambda r: r.name.lower()):
        name_entries.append({
            "name": r.name,
            "anchor": _anchor(r.name),
            "file_slug": file_slugs[r.source_file],
        })

    index_html = index_template.render(
        files=index_files,
        names=name_entries,
        object_count=len(records),
        generated_on=str(date.today()),
    )
    (output / "index.html").write_text(index_html, encoding="utf-8")
    (output / "static" / "site.css").write_text(_SITE_CSS, encoding="utf-8")

    print(
        f"wiki: wrote {len(by_file)} file page(s) and the index to {output}/",
    )
