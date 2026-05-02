"""Render the intra-file dependency graph of a Lean 4 file as a PNG/SVG/PDF image."""

import argparse
import sys
from pathlib import Path

from .lean_parser import LeanObject, parse_lean_file
from .dependency_graph import build_dependency_graph

# Node fill colours by object kind.
_KIND_COLOR: dict[str, str] = {
    "theorem":   "#d4edda",   # light green
    "lemma":     "#d4edda",
    "def":       "#cce5ff",   # light blue
    "abbrev":    "#cce5ff",
    "opaque":    "#cce5ff",
    "structure": "#ffe8cc",   # light orange
    "class":     "#ffe8cc",
    "inductive": "#e8d5f5",   # light purple
    "instance":  "#fff9c4",   # light yellow
    "axiom":     "#e2e3e5",   # light grey
    "example":   "#e2e3e5",
}
_DEFAULT_COLOR = "#f8f9fa"


def _render_graphviz(
    objects: list[LeanObject],
    deps: dict[str, set[str]],
    output_path: str,
    fmt: str,
    view: bool,
) -> None:
    import graphviz  # type: ignore

    dot = graphviz.Digraph(
        name="dependency_graph",
        graph_attr={
            "rankdir": "TB",
            "splines": "ortho",
            "bgcolor": "white",
            "fontname": "Helvetica",
            "pad": "0.4",
        },
        node_attr={
            "shape": "box",
            "style": "filled,rounded",
            "fontname": "Helvetica",
            "fontsize": "11",
            "margin": "0.15,0.08",
        },
        edge_attr={
            "arrowsize": "0.7",
            "color": "#555555",
        },
    )

    for obj in objects:
        color = _KIND_COLOR.get(obj.kind, _DEFAULT_COLOR)
        label = f"{obj.name}\n[{obj.kind}]"
        dot.node(obj.name, label=label, fillcolor=color)

    for name, dependencies in deps.items():
        for dep in dependencies:
            dot.edge(name, dep)

    # graphviz appends the extension itself; strip it from output_path if present.
    base = str(Path(output_path).with_suffix(""))
    dot.render(filename=base, format=fmt, cleanup=True, view=view)
    actual = f"{base}.{fmt}"
    print(f"Graph written to {actual}", file=sys.stderr)


def _render_matplotlib(
    objects: list[LeanObject],
    deps: dict[str, set[str]],
    output_path: str,
    view: bool,
) -> None:
    """Fallback renderer using networkx + matplotlib (no system graphviz needed)."""
    try:
        import networkx as nx          # type: ignore
        import matplotlib.pyplot as plt  # type: ignore
        import matplotlib.patches as mpatches  # type: ignore
    except ImportError:
        print(
            "Error: neither graphviz nor networkx+matplotlib are installed.\n"
            "Install one of:\n"
            "  pip install graphviz   (+ brew/apt install graphviz)\n"
            "  pip install networkx matplotlib",
            file=sys.stderr,
        )
        sys.exit(1)

    G = nx.DiGraph()
    for obj in objects:
        G.add_node(obj.name, kind=obj.kind)
    for name, dependencies in deps.items():
        for dep in dependencies:
            G.add_edge(name, dep)

    # Hierarchical layout via networkx's built-in (requires graphviz) or spring.
    try:
        pos = nx.nx_agraph.graphviz_layout(G, prog="dot")
    except Exception:
        pos = nx.spring_layout(G, seed=42, k=2.5)

    fig, ax = plt.subplots(figsize=(max(12, len(objects) * 0.8), max(8, len(objects) * 0.5)))
    ax.set_axis_off()

    node_colors = [_KIND_COLOR.get(G.nodes[n].get("kind", ""), _DEFAULT_COLOR) for n in G.nodes]
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=2000,
                           node_shape="s", ax=ax)
    nx.draw_networkx_labels(G, pos, font_size=7, ax=ax)
    nx.draw_networkx_edges(G, pos, arrows=True, arrowsize=15,
                           edge_color="#555555", ax=ax)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"Graph written to {output_path}", file=sys.stderr)
    if view:
        plt.show()


def render_graph(
    objects: list[LeanObject],
    deps: dict[str, set[str]],
    output_path: str,
    fmt: str = "png",
    view: bool = False,
) -> None:
    """
    Render the dependency graph to an image file.

    Tries graphviz first (best layout for DAGs); falls back to
    networkx + matplotlib if the graphviz system package is not installed.
    """
    try:
        _render_graphviz(objects, deps, output_path, fmt, view)
    except ImportError:
        print(
            "graphviz Python package not found; falling back to matplotlib.",
            file=sys.stderr,
        )
        _render_matplotlib(objects, deps, output_path, view)
    except Exception as exc:
        # graphviz is installed as a Python package but the dot binary is missing.
        if "ExecutableNotFound" in type(exc).__name__ or "not found" in str(exc).lower():
            print(
                f"graphviz dot binary not found ({exc}); falling back to matplotlib.",
                file=sys.stderr,
            )
            _render_matplotlib(objects, deps, output_path, view)
        else:
            raise


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render the dependency graph of a Lean 4 file as an image."
    )
    parser.add_argument("lean_file", help="Path to the .lean file")
    parser.add_argument(
        "--output", default=None,
        help="Output image path (default: <stem>_graph.<format>)",
    )
    parser.add_argument(
        "--format", dest="fmt", default="png", choices=["png", "svg", "pdf"],
        help="Output format (default: png)",
    )
    parser.add_argument(
        "--view", action="store_true",
        help="Open the image after writing",
    )
    args = parser.parse_args()

    lean_path = Path(args.lean_file)
    if not lean_path.exists():
        print(f"Error: file not found: {lean_path}", file=sys.stderr)
        sys.exit(1)

    output = args.output or str(lean_path.with_name(f"{lean_path.stem}_graph.{args.fmt}"))

    print(f"Parsing {lean_path.name}...", file=sys.stderr)
    objects = parse_lean_file(str(lean_path))
    if not objects:
        print("No top-level objects found. Exiting.", file=sys.stderr)
        sys.exit(0)

    print(f"Building dependency graph ({len(objects)} objects)...", file=sys.stderr)
    deps = build_dependency_graph(objects)

    render_graph(objects, deps, output_path=output, fmt=args.fmt, view=args.view)


if __name__ == "__main__":
    main()
