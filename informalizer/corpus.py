"""Multi-file Lean object corpus backed by SQLite.

Stores parsed objects, Claude-generated descriptions, intra- and cross-file
relationships, and (optionally) embedding vectors. The wiki and explorer
both read from this corpus.
"""

import re
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import anthropic

from .api import describe_objects_batch
from .dependency_graph import build_dependency_graph
from .lean_parser import LeanObject, parse_lean_file


# ---------------------------------------------------------------------------
# Storage location
# ---------------------------------------------------------------------------

def default_corpus_path() -> Path:
    return Path(".informalizer") / "corpus.db"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ObjectRecord:
    uid: str
    name: str
    natural_name: str
    kind: str
    signature: str
    docstring: Optional[str]
    description: str
    example: str
    line_start: int
    line_end: int
    source_file: str
    domain: Optional[str] = None
    subdomain: Optional[str] = None


@dataclass
class Relationship:
    id: int
    from_uid: str
    to_uid: str
    rel_type: str           # "depends_on" | "uses" | "similar_to"
    informal: Optional[str] = None


# ---------------------------------------------------------------------------
# uid helpers
# ---------------------------------------------------------------------------

def make_uid(source_file: str | Path, name: str) -> str:
    return f"{Path(source_file).resolve()}::{name}"


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS objects (
    uid          TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    natural_name TEXT NOT NULL DEFAULT '',
    kind         TEXT NOT NULL,
    signature    TEXT NOT NULL,
    docstring    TEXT,
    description  TEXT NOT NULL DEFAULT '',
    example      TEXT NOT NULL DEFAULT '',
    line_start   INTEGER NOT NULL,
    line_end     INTEGER NOT NULL,
    source_file  TEXT NOT NULL,
    domain       TEXT,
    subdomain    TEXT,
    raw_text     TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS objects_by_name ON objects(name);
CREATE INDEX IF NOT EXISTS objects_by_source ON objects(source_file);

CREATE TABLE IF NOT EXISTS relationships (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    from_uid  TEXT NOT NULL,
    to_uid    TEXT NOT NULL,
    rel_type  TEXT NOT NULL,
    informal  TEXT,
    UNIQUE(from_uid, to_uid, rel_type)
);

CREATE INDEX IF NOT EXISTS rels_from ON relationships(from_uid);
CREATE INDEX IF NOT EXISTS rels_to   ON relationships(to_uid);

CREATE TABLE IF NOT EXISTS embeddings (
    uid    TEXT PRIMARY KEY,
    vector BLOB NOT NULL
);
"""


def open_corpus(path: Path | None = None) -> sqlite3.Connection:
    """Open (or create) the corpus DB and return a connection."""
    db_path = path or default_corpus_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# Insertion / retrieval
# ---------------------------------------------------------------------------

def _row_to_record(row: sqlite3.Row) -> ObjectRecord:
    return ObjectRecord(
        uid=row["uid"],
        name=row["name"],
        natural_name=row["natural_name"] or "",
        kind=row["kind"],
        signature=row["signature"],
        docstring=row["docstring"],
        description=row["description"] or "",
        example=row["example"] or "",
        line_start=row["line_start"],
        line_end=row["line_end"],
        source_file=row["source_file"],
        domain=row["domain"],
        subdomain=row["subdomain"],
    )


def get_object(conn: sqlite3.Connection, uid: str) -> Optional[ObjectRecord]:
    row = conn.execute("SELECT * FROM objects WHERE uid = ?", (uid,)).fetchone()
    return _row_to_record(row) if row else None


def get_all_objects(conn: sqlite3.Connection) -> list[ObjectRecord]:
    rows = conn.execute("SELECT * FROM objects ORDER BY source_file, line_start").fetchall()
    return [_row_to_record(r) for r in rows]


def get_objects_for_file(conn: sqlite3.Connection, source_file: str | Path) -> list[ObjectRecord]:
    src = str(Path(source_file).resolve())
    rows = conn.execute(
        "SELECT * FROM objects WHERE source_file = ? ORDER BY line_start",
        (src,),
    ).fetchall()
    return [_row_to_record(r) for r in rows]


def get_source_files(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT DISTINCT source_file FROM objects ORDER BY source_file"
    ).fetchall()
    return [r["source_file"] for r in rows]


def get_relationships_from(conn: sqlite3.Connection, from_uid: str) -> list[Relationship]:
    rows = conn.execute(
        "SELECT * FROM relationships WHERE from_uid = ?", (from_uid,)
    ).fetchall()
    return [Relationship(r["id"], r["from_uid"], r["to_uid"], r["rel_type"], r["informal"])
            for r in rows]


def get_relationships_to(conn: sqlite3.Connection, to_uid: str) -> list[Relationship]:
    rows = conn.execute(
        "SELECT * FROM relationships WHERE to_uid = ?", (to_uid,)
    ).fetchall()
    return [Relationship(r["id"], r["from_uid"], r["to_uid"], r["rel_type"], r["informal"])
            for r in rows]


def name_to_uid_index(conn: sqlite3.Connection) -> dict[str, list[str]]:
    """Return {object_name: [uid, ...]} across the whole corpus."""
    rows = conn.execute("SELECT name, uid FROM objects").fetchall()
    idx: dict[str, list[str]] = {}
    for r in rows:
        idx.setdefault(r["name"], []).append(r["uid"])
    return idx


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------

def ingest_file(
    conn: sqlite3.Connection,
    client: anthropic.Anthropic | None,
    filepath: str | Path,
    include_examples: bool = False,
) -> tuple[list[str], list[str]]:
    """Parse `filepath`, describe any new objects via Claude, and insert into the corpus.

    Returns (new_uids, updated_uids). `updated_uids` are objects whose signature
    changed since the last ingest; their description is regenerated.

    If `client` is None, only objects with no existing description are inserted
    with an empty description (useful for tests).
    """
    src_path = Path(filepath).resolve()
    objects = parse_lean_file(str(src_path))
    if not objects:
        return [], []

    new_objects: list[LeanObject] = []
    updated_objects: list[LeanObject] = []

    for obj in objects:
        uid = make_uid(src_path, obj.name)
        row = conn.execute(
            "SELECT signature, description FROM objects WHERE uid = ?", (uid,)
        ).fetchone()
        if row is None:
            new_objects.append(obj)
        elif row["signature"] != obj.signature or not row["description"]:
            updated_objects.append(obj)

    to_describe = new_objects + updated_objects

    descriptions: dict[str, str] = {}
    natural_names: dict[str, str] = {}
    examples: dict[str, str] = {}
    if to_describe and client is not None:
        descriptions, natural_names, examples = describe_objects_batch(
            client, to_describe, include_examples=include_examples
        )

    # Upsert all parsed objects (their lines/raw_text may have moved even
    # if signature is unchanged).
    for obj in objects:
        uid = make_uid(src_path, obj.name)
        existing = conn.execute(
            "SELECT description, natural_name, example FROM objects WHERE uid = ?", (uid,)
        ).fetchone()

        # Decide which description / natural_name / example to use:
        # - newly-described objects: the fresh Claude output
        # - already-cached objects: keep the existing values
        if obj in to_describe:
            desc = descriptions.get(obj.name, "")
            nname = natural_names.get(obj.name, "")
            ex = examples.get(obj.name, "")
        elif existing is not None:
            desc = existing["description"] or ""
            nname = existing["natural_name"] or ""
            ex = existing["example"] or ""
        else:
            desc = nname = ex = ""

        conn.execute(
            """INSERT INTO objects
               (uid, name, natural_name, kind, signature, docstring,
                description, example, line_start, line_end, source_file, raw_text)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(uid) DO UPDATE SET
                 name=excluded.name,
                 natural_name=excluded.natural_name,
                 kind=excluded.kind,
                 signature=excluded.signature,
                 docstring=excluded.docstring,
                 description=excluded.description,
                 example=excluded.example,
                 line_start=excluded.line_start,
                 line_end=excluded.line_end,
                 source_file=excluded.source_file,
                 raw_text=excluded.raw_text""",
            (uid, obj.name, nname, obj.kind, obj.signature, obj.docstring,
             desc, ex, obj.line_start, obj.line_end, str(src_path), obj.raw_text),
        )

    # Intra-file dependency edges (replace any prior ones for this file).
    file_uids = [make_uid(src_path, obj.name) for obj in objects]
    placeholders = ",".join("?" * len(file_uids))
    conn.execute(
        f"DELETE FROM relationships WHERE rel_type = 'depends_on' "
        f"AND from_uid IN ({placeholders})",
        file_uids,
    )
    deps = build_dependency_graph(objects)
    for obj in objects:
        from_uid = make_uid(src_path, obj.name)
        for dep_name in deps.get(obj.name, set()):
            to_uid = make_uid(src_path, dep_name)
            conn.execute(
                "INSERT OR IGNORE INTO relationships (from_uid, to_uid, rel_type) "
                "VALUES (?, ?, 'depends_on')",
                (from_uid, to_uid),
            )

    conn.commit()

    new_uids = [make_uid(src_path, o.name) for o in new_objects]
    updated_uids = [make_uid(src_path, o.name) for o in updated_objects]
    return new_uids, updated_uids


# ---------------------------------------------------------------------------
# Cross-file `uses` edges
# ---------------------------------------------------------------------------

_IDENT_RE = re.compile(r"\b([A-Za-z_][\w.']*)\b")


def rebuild_cross_file_edges(conn: sqlite3.Connection) -> int:
    """Scan each object's raw_text for names belonging to objects in *other* files
    and insert `uses` relationship rows. Returns the number of edges inserted."""
    conn.execute("DELETE FROM relationships WHERE rel_type = 'uses'")

    name_index: dict[str, list[str]] = {}
    rows = conn.execute("SELECT uid, name, source_file FROM objects").fetchall()
    for r in rows:
        name_index.setdefault(r["name"], []).append((r["uid"], r["source_file"]))

    raw_rows = conn.execute(
        "SELECT uid, name, source_file, raw_text FROM objects"
    ).fetchall()

    inserted = 0
    for r in raw_rows:
        from_uid = r["uid"]
        my_source = r["source_file"]
        text = r["raw_text"] or ""
        # Strip /-- ... -/ doc-comments and -- line comments (same as the
        # intra-file pass).
        clean = re.sub(r"/--.*?-/", "", text, flags=re.DOTALL)
        clean = re.sub(r"--[^\n]*", "", clean)
        seen: set[str] = set()
        for match in _IDENT_RE.finditer(clean):
            cand = match.group(1)
            if cand == r["name"] or cand in seen or cand not in name_index:
                continue
            seen.add(cand)
            for to_uid, to_source in name_index[cand]:
                if to_source == my_source or to_uid == from_uid:
                    continue
                # Ambiguous name (multiple matches across files): skip in v1.
                if len([s for _, s in name_index[cand] if s != my_source]) > 1:
                    continue
                cur = conn.execute(
                    "INSERT OR IGNORE INTO relationships (from_uid, to_uid, rel_type) "
                    "VALUES (?, ?, 'uses')",
                    (from_uid, to_uid),
                )
                if cur.rowcount:
                    inserted += 1

    conn.commit()
    return inserted


# ---------------------------------------------------------------------------
# Embedding storage
# ---------------------------------------------------------------------------

def upsert_embedding(conn: sqlite3.Connection, uid: str, vector_bytes: bytes) -> None:
    conn.execute(
        "INSERT INTO embeddings (uid, vector) VALUES (?, ?) "
        "ON CONFLICT(uid) DO UPDATE SET vector = excluded.vector",
        (uid, vector_bytes),
    )
    conn.commit()


def get_embedding(conn: sqlite3.Connection, uid: str) -> Optional[bytes]:
    row = conn.execute("SELECT vector FROM embeddings WHERE uid = ?", (uid,)).fetchone()
    return row["vector"] if row else None


def get_all_embeddings(conn: sqlite3.Connection) -> dict[str, bytes]:
    rows = conn.execute("SELECT uid, vector FROM embeddings").fetchall()
    return {r["uid"]: r["vector"] for r in rows}


# ---------------------------------------------------------------------------
# Bulk ingest helper
# ---------------------------------------------------------------------------

def ingest_paths(
    conn: sqlite3.Connection,
    client: anthropic.Anthropic | None,
    paths: Iterable[Path],
    include_examples: bool = False,
) -> tuple[int, int]:
    """Ingest each .lean file under each path. Returns (new_count, updated_count)."""
    total_new = total_updated = 0
    files: list[Path] = []
    for p in paths:
        if p.is_file():
            files.append(p)
        elif p.is_dir():
            files.extend(sorted(p.rglob("*.lean")))
    for fp in files:
        print(f"  ingesting {fp}", file=sys.stderr)
        new, updated = ingest_file(conn, client, fp, include_examples=include_examples)
        total_new += len(new)
        total_updated += len(updated)
    return total_new, total_updated
