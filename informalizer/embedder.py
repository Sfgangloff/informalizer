"""Description embeddings (TF-IDF + truncated SVD) for similarity search.

The model is fit on every object currently in the corpus, then per-uid
50-dim vectors are stored back in the corpus's `embeddings` table.
The fitted vectorizer + SVD are persisted to .informalizer/embedder.pkl
so that later additions can be embedded without refitting.
"""

import pickle
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer

from .corpus import (
    ObjectRecord,
    get_all_embeddings,
    get_all_objects,
    upsert_embedding,
)


N_COMPONENTS = 50
MODEL_FILENAME = "embedder.pkl"


@dataclass
class EmbeddingModel:
    vectorizer: TfidfVectorizer
    svd: TruncatedSVD
    n_components: int

    def transform(self, texts: list[str]) -> np.ndarray:
        tfidf = self.vectorizer.transform(texts)
        return self.svd.transform(tfidf)


def _model_path(corpus_db_path: Path) -> Path:
    return corpus_db_path.parent / MODEL_FILENAME


def _record_text(rec: ObjectRecord) -> str:
    name = rec.natural_name or rec.name
    return f"{rec.kind} {name}: {rec.description}"


def _vector_to_bytes(vec: np.ndarray) -> bytes:
    return np.asarray(vec, dtype=np.float32).tobytes()


def _bytes_to_vector(data: bytes) -> np.ndarray:
    return np.frombuffer(data, dtype=np.float32)


# ---------------------------------------------------------------------------
# Fit / transform
# ---------------------------------------------------------------------------

def fit_corpus(conn, corpus_db_path: Path) -> Optional[EmbeddingModel]:
    """Fit a fresh model on every described object in the corpus, write each
    object's embedding back into the DB, persist the model, and return it.

    Returns None if there is nothing usable to fit on (e.g. no descriptions yet)."""
    records = [r for r in get_all_objects(conn) if r.description.strip()]
    if not records:
        print("embedder: no described objects yet — skipping fit.", file=sys.stderr)
        return None

    texts = [_record_text(r) for r in records]
    vectorizer = TfidfVectorizer(
        lowercase=True,
        ngram_range=(1, 2),
        min_df=1,
        max_df=0.95,
        stop_words="english",
    )
    tfidf = vectorizer.fit_transform(texts)

    n_components = min(N_COMPONENTS, max(1, min(tfidf.shape) - 1))
    svd = TruncatedSVD(n_components=n_components, random_state=0)
    vectors = svd.fit_transform(tfidf)

    # L2-normalise so cosine similarity reduces to a dot product.
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    vectors = vectors / norms

    for rec, vec in zip(records, vectors):
        upsert_embedding(conn, rec.uid, _vector_to_bytes(vec))

    model = EmbeddingModel(vectorizer=vectorizer, svd=svd, n_components=n_components)
    save_model(model, corpus_db_path)
    print(
        f"embedder: fit on {len(records)} objects → {n_components}-dim vectors.",
        file=sys.stderr,
    )
    return model


def save_model(model: EmbeddingModel, corpus_db_path: Path) -> None:
    path = _model_path(corpus_db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        pickle.dump(model, f)


def load_model(corpus_db_path: Path) -> Optional[EmbeddingModel]:
    path = _model_path(corpus_db_path)
    if not path.exists():
        return None
    with path.open("rb") as f:
        return pickle.load(f)


# ---------------------------------------------------------------------------
# Similarity queries
# ---------------------------------------------------------------------------

def load_vectors(conn) -> dict[str, np.ndarray]:
    return {uid: _bytes_to_vector(b) for uid, b in get_all_embeddings(conn).items()}


def top_k_similar(
    conn,
    uid: str,
    k: int = 3,
    exclude_same_file: bool = False,
) -> list[tuple[str, float]]:
    """Return [(uid, similarity), ...] for the k most similar objects to `uid`.

    `exclude_same_file=True` filters out matches in the same source file as `uid`,
    which is what the wiki uses for the "related across the corpus" panel.
    """
    vectors = load_vectors(conn)
    if uid not in vectors:
        return []

    query = vectors[uid]
    q_norm = float(np.linalg.norm(query)) or 1.0

    # Source file of the query, used for the same-file filter.
    same_file_source: Optional[str] = None
    if exclude_same_file:
        row = conn.execute(
            "SELECT source_file FROM objects WHERE uid = ?", (uid,)
        ).fetchone()
        same_file_source = row["source_file"] if row else None

    sources: dict[str, str] = {}
    if exclude_same_file:
        for r in conn.execute("SELECT uid, source_file FROM objects").fetchall():
            sources[r["uid"]] = r["source_file"]

    scored: list[tuple[str, float]] = []
    for other_uid, other_vec in vectors.items():
        if other_uid == uid:
            continue
        if exclude_same_file and sources.get(other_uid) == same_file_source:
            continue
        denom = q_norm * (float(np.linalg.norm(other_vec)) or 1.0)
        sim = float(np.dot(query, other_vec) / denom)
        scored.append((other_uid, sim))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:k]
