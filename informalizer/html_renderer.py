"""Self-contained interactive HTML explorer for a single Lean file.

Layout:
  Left pane  — the Lean source, line-numbered, with every occurrence of a
               file-local object name wrapped in a clickable span coloured
               by knowledge state.
  Right pane — details panel: kind, KS dropdown, signature, description,
               example, related objects (intra-file + cross-file + similar).

Two modes:
  * Static (default): all data is embedded as JSON in a <script> tag — no
    server needed. Knowledge-state changes are persisted to localStorage
    under keys of the form `informalizer:ks:<uid>` and are NOT written back
    to .informalizer/knowledge.json.
  * Server (`server_mode=True`, used by `informalizer serve`): state changes
    POST to `/api/state` and are written through to .informalizer/knowledge.json,
    so the wiki picks them up on the next regeneration.
"""

import html
import json
import re
from datetime import date
from pathlib import Path
from typing import Optional

import markdown as _md

from .corpus import (
    ObjectRecord,
    get_objects_for_file,
    get_relationships_from,
    get_relationships_to,
    get_object,
)
from .embedder import top_k_similar
from .knowledge_store import KnowledgeStore, make_uid as ks_make_uid


# ---------------------------------------------------------------------------
# CSS (kept inline for self-containment)
# ---------------------------------------------------------------------------

_EXPLORER_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { height: 100%; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
  color: #212529;
  line-height: 1.55;
  background: #fff;
  display: flex;
  flex-direction: column;
}
header.site-header {
  padding: 0.9rem 1.4rem;
  border-bottom: 3px solid #0055cc;
  background: #fff;
  flex: 0 0 auto;
}
header h1 { font-size: 1.2rem; }
header .meta { color: #6c757d; font-size: 0.83rem; margin-top: 0.15rem; }

.layout {
  flex: 1 1 auto;
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr);
  gap: 0;
  min-height: 0;
}

/* Source pane */
.source-pane {
  overflow-y: auto;
  border-right: 1px solid #e0e4e8;
  padding: 0.6rem 0;
  background: #fafbfc;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', monospace;
  font-size: 0.86rem;
}
.srcrow {
  display: flex;
  white-space: pre;
  padding: 0 1rem;
}
.srcrow:hover { background: #f0f2f5; }
.lineno {
  flex: 0 0 3.5rem;
  text-align: right;
  padding-right: 0.9rem;
  color: #adb5bd;
  user-select: none;
}
.srccode { flex: 1 1 auto; }
.obj-ref {
  cursor: pointer;
  border-radius: 3px;
  padding: 0 2px;
  border-bottom: 2px solid transparent;
  transition: background 0.1s;
}
.obj-ref:hover { background: rgba(0, 85, 204, 0.12); }
.obj-ref.active { background: rgba(0, 85, 204, 0.2); border-bottom-color: #0055cc; }
.obj-ref.ks-known    { border-bottom-color: #1a5c2a; }
.obj-ref.ks-learning { border-bottom-color: #b07a1f; }
.obj-ref.ks-unknown  { border-bottom-color: #c8313a; }

/* Details pane */
.details-pane {
  overflow-y: auto;
  padding: 1.2rem 1.6rem;
}
.details-pane .placeholder {
  color: #6c757d;
  font-style: italic;
  margin-top: 2rem;
  text-align: center;
}
.details-header { display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap; }
.details-header h2 { font-size: 1.1rem; }
.details-meta { color: #6c757d; font-size: 0.82rem; margin: 0.2rem 0 0.9rem; }

code {
  background: #f3f4f6;
  padding: 0.1em 0.35em;
  border-radius: 3px;
  font-size: 0.9em;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', monospace;
}
pre {
  background: #f6f8fa;
  padding: 0.8rem 1rem;
  border-radius: 6px;
  overflow-x: auto;
  border: 1px solid #e0e4e8;
  margin: 0.4rem 0 0.8rem;
}
pre code { background: none; padding: 0; font-size: 0.85em; }

.badge {
  display: inline-block;
  padding: 2px 9px;
  border-radius: 3px;
  font-size: 0.75em;
  font-weight: 700;
  white-space: nowrap;
}
code.kind { background: #e8f0fe; color: #1a3c8e; padding: 0.1em 0.4em; }

.ks-controls { margin: 0.5rem 0 1rem; font-size: 0.88em; }
.ks-controls label { color: #495057; margin-right: 0.4rem; }
.ks-controls select { padding: 0.2rem 0.4rem; border: 1px solid #ced4da; border-radius: 4px; }

.section h3 {
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #6c757d;
  margin: 1rem 0 0.4rem;
}
.section ul { list-style: none; margin: 0; padding: 0; }
.section li { padding: 0.25rem 0; }
.section .obj-link {
  cursor: pointer;
  color: #0055cc;
}
.section .obj-link:hover { text-decoration: underline; }
.section .rel-text { color: #495057; font-size: 0.88em; display: block; margin-left: 0.4rem; }
.section .meta { color: #adb5bd; font-size: 0.82em; margin-left: 0.3rem; }

.ks-dot {
  display: inline-block;
  width: 0.6em;
  height: 0.6em;
  border-radius: 50%;
  margin-right: 0.4em;
  vertical-align: middle;
}
.ks-dot.ks-known    { background: #1a5c2a; }
.ks-dot.ks-learning { background: #b07a1f; }
.ks-dot.ks-unknown  { background: #c8313a; }

.legend { margin-top: 0.4rem; font-size: 0.8rem; color: #6c757d; }
.legend span { margin-right: 0.8rem; }
"""


_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title} · Informalizer explorer</title>
<style>{css}</style>
</head>
<body>
<header class="site-header">
  <h1>{title}</h1>
  <div class="meta">{n_objects} objects · {n_lines} lines · generated {generated_on}</div>
  <div class="legend">
    <span><span class="ks-dot ks-known"></span>known</span>
    <span><span class="ks-dot ks-learning"></span>learning</span>
    <span><span class="ks-dot ks-unknown"></span>unknown</span>
    <span style="margin-left:0.6rem; color:#adb5bd;">click any underlined name on the left</span>
  </div>
</header>

<div class="layout">
  <div class="source-pane">
{source_html}
  </div>
  <div class="details-pane" id="details">
    <div class="placeholder">Select an object on the left to see details.</div>
  </div>
</div>

<script id="data" type="application/json">
{data_json}
</script>

<script>
{js}
</script>
</body>
</html>
"""


_JS = r"""
(() => {
  const data = JSON.parse(document.getElementById('data').textContent);
  const objects = data.objects;             // name -> object record
  const fileKey = data.fileKey;             // localStorage prefix uid base
  const detailsEl = document.getElementById('details');

  const serverMode = !!data.serverMode;

  function ksKey(name) {
    return 'informalizer:ks:' + fileKey + '::' + name;
  }
  function getKS(name) {
    if (serverMode) {
      return objects[name].state || 'unknown';
    }
    const stored = localStorage.getItem(ksKey(name));
    if (stored && (stored === 'known' || stored === 'learning' || stored === 'unknown')) {
      return stored;
    }
    return objects[name].state || 'unknown';
  }
  function setKS(name, state) {
    objects[name].state = state;
    refreshHighlights();
    if (serverMode) {
      fetch('/api/state', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name: name, state: state}),
      }).catch(err => console.error('state save failed:', err));
    } else {
      localStorage.setItem(ksKey(name), state);
    }
  }

  function refreshHighlights() {
    document.querySelectorAll('.obj-ref').forEach(el => {
      const name = el.dataset.obj;
      el.classList.remove('ks-known', 'ks-learning', 'ks-unknown');
      el.classList.add('ks-' + getKS(name));
    });
  }

  function escapeHtml(s) {
    return s.replace(/[&<>"']/g, c => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;',
      '"': '&quot;', "'": '&#39;'
    }[c]));
  }

  function objLink(name, label) {
    const safeLabel = escapeHtml(label || name);
    return '<span class="obj-link" data-jump="' + escapeHtml(name) + '">' + safeLabel + '</span>';
  }

  function externalLink(href, label, source) {
    return '<a href="' + escapeHtml(href) + '" target="_blank">' + escapeHtml(label) +
           '</a><span class="meta">' + escapeHtml(source || '') + '</span>';
  }

  function relRow(item) {
    const link = objLink(item.name);
    const text = item.informal ? '<span class="rel-text">' + escapeHtml(item.informal) + '</span>' : '';
    return '<li>' + link + text + '</li>';
  }

  function externalRow(item) {
    return '<li>' + externalLink(item.href, item.name, item.source) +
           (item.informal ? '<span class="rel-text">' + escapeHtml(item.informal) + '</span>' : '') +
           '</li>';
  }

  function similarRow(item) {
    return '<li>' + externalLink(item.href, item.name, item.source) +
           '<span class="meta">score ' + item.score + '</span></li>';
  }

  function render(name) {
    const o = objects[name];
    if (!o) return;
    const state = getKS(name);
    const heading = o.naturalName && o.naturalName.toLowerCase() !== name.toLowerCase()
      ? escapeHtml(o.naturalName) + ' <code>' + escapeHtml(name) + '</code>'
      : '<code>' + escapeHtml(name) + '</code>';

    let html = '';
    html += '<div class="details-header">';
    html += '<h2>' + heading + '</h2>';
    html += '<code class="kind">' + escapeHtml(o.kind) + '</code>';
    html += '</div>';
    html += '<div class="details-meta">lines ' + o.lineStart + '–' + o.lineEnd + '</div>';

    html += '<div class="ks-controls">';
    html += '<label>Knowledge state:</label>';
    html += '<select id="ks-select">';
    for (const opt of ['known', 'learning', 'unknown']) {
      html += '<option value="' + opt + '"' + (opt === state ? ' selected' : '') + '>' + opt + '</option>';
    }
    html += '</select>';
    html += '</div>';

    html += '<div class="section"><h3>Signature</h3>';
    html += '<pre><code>' + escapeHtml(o.signature) + '</code></pre></div>';

    if (o.descriptionHtml) {
      html += '<div class="section"><h3>Description</h3>' + o.descriptionHtml + '</div>';
    }
    if (o.exampleHtml) {
      html += '<div class="section"><h3>Example</h3>' + o.exampleHtml + '</div>';
    }
    if (o.dependsOn && o.dependsOn.length) {
      html += '<div class="section"><h3>Depends on</h3><ul>' +
              o.dependsOn.map(relRow).join('') + '</ul></div>';
    }
    if (o.usedByInFile && o.usedByInFile.length) {
      html += '<div class="section"><h3>Used by (this file)</h3><ul>' +
              o.usedByInFile.map(relRow).join('') + '</ul></div>';
    }
    if (o.usesExternal && o.usesExternal.length) {
      html += '<div class="section"><h3>Uses (other files)</h3><ul>' +
              o.usesExternal.map(externalRow).join('') + '</ul></div>';
    }
    if (o.usedExternally && o.usedExternally.length) {
      html += '<div class="section"><h3>Used by (other files)</h3><ul>' +
              o.usedExternally.map(externalRow).join('') + '</ul></div>';
    }
    if (o.similar && o.similar.length) {
      html += '<div class="section"><h3>Similar across the corpus</h3><ul>' +
              o.similar.map(similarRow).join('') + '</ul></div>';
    }

    detailsEl.innerHTML = html;

    detailsEl.querySelector('#ks-select').addEventListener('change', e => {
      setKS(name, e.target.value);
    });
    detailsEl.querySelectorAll('[data-jump]').forEach(el => {
      el.addEventListener('click', () => activate(el.dataset.jump));
    });
  }

  function activate(name) {
    if (!objects[name]) return;
    document.querySelectorAll('.obj-ref').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.obj-ref[data-obj="' + CSS.escape(name) + '"]')
      .forEach(el => el.classList.add('active'));
    render(name);
    // scroll the first declaration line into view
    const decl = document.getElementById('line-' + objects[name].lineStart);
    if (decl) decl.scrollIntoView({block: 'center', behavior: 'smooth'});
  }

  document.querySelectorAll('.obj-ref').forEach(el => {
    el.addEventListener('click', () => activate(el.dataset.obj));
  });

  refreshHighlights();
})();
"""


# ---------------------------------------------------------------------------
# Source rendering helpers
# ---------------------------------------------------------------------------

def _render_source_html(
    source_lines: list[str],
    object_names: list[str],
    name_to_state: dict[str, str],
) -> str:
    """Wrap every word-boundary occurrence of a known name in a clickable span,
    then emit one <div class="srcrow"> per line with a line number."""
    if not object_names:
        # No names — just render plain lines.
        rows = []
        for i, line in enumerate(source_lines, 1):
            rows.append(
                f'<div class="srcrow" id="line-{i}">'
                f'<span class="lineno">{i}</span>'
                f'<span class="srccode">{html.escape(line.rstrip(chr(10)))}</span>'
                f'</div>'
            )
        return "\n".join(rows)

    sorted_names = sorted(object_names, key=len, reverse=True)
    pattern = re.compile(
        r"\b(" + "|".join(re.escape(n) for n in sorted_names) + r")\b"
    )

    rows = []
    for i, raw in enumerate(source_lines, 1):
        line = raw.rstrip("\n")

        # Tokenize: alternate non-match / match chunks so we can escape each
        # piece independently and only wrap real matches.
        out_parts = []
        last = 0
        for m in pattern.finditer(line):
            out_parts.append(html.escape(line[last:m.start()]))
            name = m.group(1)
            ks = name_to_state.get(name, "unknown")
            out_parts.append(
                f'<span class="obj-ref ks-{ks}" data-obj="{html.escape(name)}">'
                f'{html.escape(name)}</span>'
            )
            last = m.end()
        out_parts.append(html.escape(line[last:]))
        code_html = "".join(out_parts) or "&nbsp;"

        rows.append(
            f'<div class="srcrow" id="line-{i}">'
            f'<span class="lineno">{i}</span>'
            f'<span class="srccode">{code_html}</span>'
            f'</div>'
        )
    return "\n".join(rows)


def _render_md(text: str) -> str:
    if not text.strip():
        return ""
    return _md.markdown(text, extensions=["fenced_code", "tables"])


def _render_example(example: str) -> str:
    if not example.strip():
        return ""
    body = example.strip()
    if "```" not in body:
        body = "```lean\n" + body.rstrip() + "\n```"
    return _render_md(body)


def _wiki_link_for(target: ObjectRecord) -> str:
    """Best-effort link to the wiki page for an external object. The wiki uses
    `_slugify(stem)` for filenames and `obj-<slug>` anchors; we mirror that here
    so the explorer can deep-link without importing the wiki module."""
    stem = re.sub(r"[^A-Za-z0-9_]", "-", Path(target.source_file).stem).strip("-") or "file"
    anchor = "obj-" + re.sub(r"[^A-Za-z0-9_]", "-", target.name)
    return f"../wiki_out/files/{stem}.html#{anchor}"


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def render_explorer_html(
    conn,
    source_file: str | Path,
    knowledge_store: Optional[KnowledgeStore] = None,
    similar_k: int = 3,
    server_mode: bool = False,
) -> str:
    """Build the explorer HTML and return it as a string.

    `server_mode=True` makes the JS POST state changes to /api/state instead
    of writing localStorage; pair it with `informalizer.server.serve_explorer`.
    """
    src_path = Path(source_file).resolve()
    records = get_objects_for_file(conn, src_path)
    if not records:
        raise ValueError(
            f"{src_path} has no objects in the corpus. Run "
            f"`informalizer corpus add {source_file}` first."
        )

    if not src_path.exists():
        raise FileNotFoundError(f"source file not found: {src_path}")
    source_lines = src_path.read_text(encoding="utf-8").splitlines(keepends=False)

    ks = knowledge_store or KnowledgeStore()
    name_to_state = {
        rec.name: ks.get_state(ks_make_uid(src_path, rec.name)) for rec in records
    }

    # ------------------------------------------------------------------
    # Per-object payload for the JSON blob.
    # ------------------------------------------------------------------
    by_uid = {r.uid: r for r in records}
    payload: dict[str, dict] = {}

    for rec in records:
        depends_on = []
        used_by_in_file = []
        uses_external = []
        used_externally = []

        for rel in get_relationships_from(conn, rec.uid):
            target = by_uid.get(rel.to_uid) or get_object(conn, rel.to_uid)
            if not target:
                continue
            if rel.rel_type == "depends_on":
                depends_on.append({
                    "name": target.name,
                    "informal": rel.informal or "",
                })
            elif rel.rel_type == "uses":
                uses_external.append({
                    "name": target.name,
                    "source": Path(target.source_file).name,
                    "href": _wiki_link_for(target),
                    "informal": rel.informal or "",
                })

        for rel in get_relationships_to(conn, rec.uid):
            source = by_uid.get(rel.from_uid) or get_object(conn, rel.from_uid)
            if not source:
                continue
            if rel.rel_type == "depends_on" and source.source_file == str(src_path):
                used_by_in_file.append({
                    "name": source.name,
                    "informal": rel.informal or "",
                })
            elif rel.rel_type == "uses":
                used_externally.append({
                    "name": source.name,
                    "source": Path(source.source_file).name,
                    "href": _wiki_link_for(source),
                    "informal": rel.informal or "",
                })

        similar = []
        for sim_uid, score in top_k_similar(conn, rec.uid, k=similar_k, exclude_same_file=True):
            target = get_object(conn, sim_uid)
            if not target:
                continue
            similar.append({
                "name": target.name,
                "source": Path(target.source_file).name,
                "href": _wiki_link_for(target),
                "score": f"{score:.2f}",
            })

        payload[rec.name] = {
            "name": rec.name,
            "naturalName": rec.natural_name or "",
            "kind": rec.kind,
            "signature": rec.signature,
            "descriptionHtml": _render_md(rec.description),
            "exampleHtml": _render_example(rec.example),
            "lineStart": rec.line_start,
            "lineEnd": rec.line_end,
            "state": name_to_state.get(rec.name, "unknown"),
            "dependsOn": depends_on,
            "usedByInFile": used_by_in_file,
            "usesExternal": uses_external,
            "usedExternally": used_externally,
            "similar": similar,
        }

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------
    source_html = _render_source_html(
        source_lines, [r.name for r in records], name_to_state
    )

    data_json = json.dumps({
        "fileKey": str(src_path),
        "serverMode": bool(server_mode),
        "objects": payload,
    })
    # Defuse any literal "</script>" inside JSON so it can't break out of the tag.
    data_json = data_json.replace("</", "<\\/")

    return _TEMPLATE.format(
        title=html.escape(src_path.name),
        css=_EXPLORER_CSS,
        n_objects=len(records),
        n_lines=len(source_lines),
        generated_on=str(date.today()),
        source_html=source_html,
        data_json=data_json,
        js=_JS,
    )


def render_explorer(
    conn,
    source_file: str | Path,
    output_path: str | Path,
    knowledge_store: Optional[KnowledgeStore] = None,
    similar_k: int = 3,
) -> None:
    """Render the explorer to a static HTML file (no server)."""
    html_doc = render_explorer_html(
        conn, source_file,
        knowledge_store=knowledge_store,
        similar_k=similar_k,
        server_mode=False,
    )
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_doc, encoding="utf-8")
    print(f"explorer: wrote {out}")
