"""Compile a TikZ snippet to an inline SVG via pdflatex + pdftocairo.

The model emits raw TikZ code (`\\begin{tikzpicture}...\\end{tikzpicture}` or a
bare body). We wrap it in a `standalone` document, compile to PDF, then
convert to SVG. Returns None if any step fails or the toolchain is missing,
so the caller can simply skip the illustration.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


_STANDALONE_PREAMBLE = r"""\documentclass[tikz,border=4pt]{standalone}
\usepackage{tikz}
\usetikzlibrary{arrows.meta,positioning,calc,decorations.pathreplacing,
                shapes.geometric,patterns,fit,backgrounds}
\begin{document}
"""

_STANDALONE_END = "\n\\end{document}\n"


def _normalize_body(tikz: str) -> str:
    """Ensure the snippet is a valid standalone body. Accept either a full
    `\\begin{tikzpicture}...\\end{tikzpicture}` block, a `\\tikz ...;` one-liner,
    or a bare path-spec body that we wrap ourselves."""
    body = tikz.strip()
    if "\\begin{tikzpicture}" in body or body.startswith("\\tikz"):
        return body
    # Bare body — wrap.
    return "\\begin{tikzpicture}\n" + body + "\n\\end{tikzpicture}"


def compile_tikz_to_svg(tikz: str) -> str | None:
    """Compile a TikZ snippet to an inline SVG (`<svg ...>...</svg>` string).

    Returns None on any failure (missing toolchain, LaTeX error, parse issue).
    """
    pdflatex = shutil.which("pdflatex")
    pdftocairo = shutil.which("pdftocairo")
    if not pdflatex or not pdftocairo:
        print(
            "tikz_renderer: pdflatex or pdftocairo not found — skipping",
            file=sys.stderr,
        )
        return None

    body = _normalize_body(tikz)
    src = _STANDALONE_PREAMBLE + body + _STANDALONE_END

    with tempfile.TemporaryDirectory(prefix="informalizer-tikz-") as td:
        tdir = Path(td)
        tex_path = tdir / "fig.tex"
        tex_path.write_text(src, encoding="utf-8")

        try:
            proc = subprocess.run(
                [
                    pdflatex,
                    "-interaction=nonstopmode",
                    "-halt-on-error",
                    "-output-directory", str(tdir),
                    str(tex_path),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            print("tikz_renderer: pdflatex timed out", file=sys.stderr)
            return None

        pdf_path = tdir / "fig.pdf"
        if not pdf_path.exists():
            tail = "\n".join(proc.stdout.splitlines()[-15:])
            print(f"tikz_renderer: pdflatex failed:\n{tail}", file=sys.stderr)
            return None

        svg_path = tdir / "fig.svg"
        try:
            subprocess.run(
                [pdftocairo, "-svg", str(pdf_path), str(svg_path)],
                check=True,
                capture_output=True,
                timeout=15,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            print(f"tikz_renderer: pdftocairo failed: {exc}", file=sys.stderr)
            return None

        if not svg_path.exists():
            return None

        raw = svg_path.read_text(encoding="utf-8")
        # Strip XML / DOCTYPE prologue so the <svg> is inlineable.
        idx = raw.find("<svg")
        return raw[idx:] if idx != -1 else raw


_TIKZ_FENCE_RE = re.compile(r"```(?:tikz|latex|tex)?\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_tikz(text: str) -> str | None:
    """Pull a TikZ snippet out of a fenced code block, or return the text
    as-is if it already looks like raw TikZ. None if nothing usable."""
    m = _TIKZ_FENCE_RE.search(text)
    if m:
        return m.group(1).strip()
    if "\\begin{tikzpicture}" in text or text.strip().startswith("\\tikz"):
        return text.strip()
    return None
