# Informalizer

Informalizer takes a Lean 4 source file and produces a Markdown report that explains every top-level object — definitions, lemmas, structures, instances — in plain mathematical English.

## How it works

1. **Parse** — extract all top-level Lean 4 declarations with a regex-based parser.
2. **Dependency graph** — build a dependency graph over the file-local objects and sort them topologically, so foundational pieces are explained before the things that use them.
3. **Describe** — send all objects to Claude in a single batch API request; each object gets a concise natural-language description.
4. **Summarize** — generate a high-level summary of what the file is about and how the pieces fit together.
5. **Format** — write a Markdown report with a summary, a quick-reference table, and a detailed section per object, with clickable cross-references whenever one object is mentioned inside another's description.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Requires Python 3.10+ and an [Anthropic API key](https://console.anthropic.com/).

## Usage

```bash
# reads example.lean, writes example_informalizer.md
python main.py example.lean

# custom output path
python main.py example.lean --output report.md

# skip terminal output
python main.py example.lean --no-terminal

# pass the API key via a file instead of the environment variable
python main.py example.lean --api-key-file anthropic_key.txt
```

Set your API key via the environment variable:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

## Output

The generated Markdown report contains:

- **Summary** — 1–3 paragraphs describing the mathematical content of the file.
- **Quick Reference** — a table listing every object with its kind and a one-line description, each linked to its full entry.
- **Objects (Dependency Order)** — one section per object with its signature and a detailed description inside a collapsible block. Every mention of a file-local object name is a clickable link to that object's section.

See [`example_informalizer.md`](example_informalizer.md) for a sample generated from `example.lean`, a Lean 4 file on symbolic dynamics.

## Project structure

| File | Role |
|------|------|
| `main.py` | CLI entry point |
| `lean_parser.py` | Regex-based Lean 4 parser |
| `dependency_graph.py` | Dependency graph construction and topological sort (Kahn's algorithm) |
| `informalizer.py` | Claude API calls — batch object descriptions and file summary |
| `formatter.py` | Terminal output (Rich) and Markdown generation |

## Requirements

```
anthropic>=0.49.0
rich>=13.0.0
```
