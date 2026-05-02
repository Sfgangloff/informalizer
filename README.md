# Informalizer

Informalizer takes a Lean 4 source file (or an entire folder of files) and produces a Markdown report that explains every top-level object — definitions, lemmas, structures, instances — in plain mathematical English.

Every object gets a **natural-language name** alongside its Lean identifier, and is automatically assigned a **role category** (Central Result, Key Lemma, Technical Lemma, Central Concept, …) based on its position in the dependency graph. The report uses coloured badges to make the structure of the file immediately readable.

## How it works

1. **Parse** — extract all top-level Lean 4 declarations with a regex-based parser.
2. **Dependency graph** — build a dependency graph and sort objects topologically, so foundational pieces are explained before the things that use them.
3. **Categorise** — assign a role to each object (Central Result, Key Lemma, …) from graph topology: in-degree, kind, and connectivity.
4. **Describe** — send all objects to Claude in a single batch API request; each object gets a short natural-language name and a concise description.
5. **Summarize** — generate a high-level summary of what the file is about.
6. **Format** — write a Markdown report with coloured role badges, natural-language names, a quick-reference table, and per-object sections with clickable cross-references.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

For best-quality dependency graph images, also install the system graphviz package:

```bash
brew install graphviz   # macOS
apt install graphviz    # Debian / Ubuntu
```

Requires Python 3.10+ and an [Anthropic API key](https://console.anthropic.com/).

## Usage

Set your API key:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

All commands go through the unified `cli.py` entry point:

```
python cli.py <subcommand> [options]
```

### `describe` — generate a report

```bash
# single file → writes example_informalizer.md next to the source
python cli.py describe examples/example.lean

# suppress rich terminal output (recommended for long files)
python cli.py describe examples/example.lean --no-terminal

# custom output path
python cli.py describe examples/example.lean --output report.md

# whole folder, all reports into one directory, skip already-done files
python cli.py describe path/to/project --output-dir ./reports --skip-existing --no-terminal

# pass the API key via a file
python cli.py describe examples/example.lean --api-key-file anthropic_key.txt
```

### `graph` — visualise the dependency graph

Produces a colour-coded directed graph image (PNG, SVG, or PDF).
Node colours indicate kind: theorem/lemma = green, def = blue, structure = orange, …

```bash
# writes example_graph.png next to the source file
python cli.py graph examples/example.lean

# SVG, open immediately
python cli.py graph examples/example.lean --format svg --view
```

Falls back to `networkx` + `matplotlib` automatically if the graphviz system package is absent.

### `ingest` — register objects in the knowledge store

Parses Lean files and adds every object to the knowledge store with state `unknown`.
No Claude API calls are made. Use this before `diff` or `state`.

```bash
python cli.py ingest examples/example.lean
python cli.py ingest path/to/project/
```

### `diff` — see what is new

Shows which objects in a file are **new** (not yet in the store), **changed** (signature differs), or **seen** (already tracked, with their current state).

```bash
python cli.py diff examples/example.lean
```

### `state` — track your understanding

Each object can be tagged `unknown` (default) / `learning` / `known` — displayed in red / yellow / green everywhere.

```bash
# show all objects and their current state
python cli.py state examples/example.lean

# mark one object
python cli.py state examples/example.lean mulShift known

# mark everything in the file
python cli.py state examples/example.lean --all learning
```

States are stored in `.informalizer/knowledge.json` (project-local) or `~/.informalizer/knowledge.json` (global).

## Output

The generated Markdown report contains:

- **Summary** — 1–3 paragraphs describing the mathematical content of the file.
- **Quick Reference** — table with role category (🏆 Central Result, ⭐ Key Lemma, …), kind, natural-language name, and one-liner per object.
- **Objects (Dependency Order)** — one section per object with a coloured role badge, natural-language name, Lean signature, and full description inside a collapsible block. Every mention of a file-local object name is a clickable link.

See [`examples/example_informalizer.md`](examples/example_informalizer.md) for a sample generated from [`examples/example.lean`](examples/example.lean), a Lean 4 file on symbolic dynamics.

## Project structure

```
informalizer/           # Python package — all library code
├── lean_parser.py      # Regex-based Lean 4 parser
├── dependency_graph.py # DAG construction, topological sort, categorisation
├── api.py              # Claude API calls — batch descriptions, summary
├── formatter.py        # Terminal output (Rich) and Markdown generation
├── graph_renderer.py   # Dependency graph image (graphviz / matplotlib)
├── knowledge_store.py  # Persistent knowledge-state store (JSON)
└── diff_finder.py      # Diff a file against the knowledge store

cli.py                  # Unified entry point (describe / graph / ingest / diff / state)
examples/               # Sample Lean file and generated report
requirements.txt
plan.txt
```

## Requirements

```
anthropic>=0.49.0
rich>=13.0.0
graphviz>=0.20.0
networkx>=3.0
matplotlib>=3.8.0
```
