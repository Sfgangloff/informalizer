"""Persistent knowledge-state store: tracks whether each Lean object is known, learning, or unknown."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

KnowledgeState = Literal["known", "learning", "unknown"]

VALID_STATES: frozenset[str] = frozenset({"known", "learning", "unknown"})

# CSS class names used by the HTML explorer (Phase 3B).
CSS_CLASS: dict[str, str] = {
    "known": "ks-known",
    "learning": "ks-learning",
    "unknown": "ks-unknown",
}


def make_uid(source_file: str | Path, name: str) -> str:
    """Canonical identifier: absolute path + object name."""
    return f"{Path(source_file).resolve()}::{name}"


def _find_store_path() -> Path:
    """Always use the project-local store (.informalizer/knowledge.json)."""
    return Path(".informalizer") / "knowledge.json"


class KnowledgeStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or _find_store_path()
        self._data: dict[str, dict] = {}
        self._load()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if self.path.exists():
            self._data = json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._data, indent=2, sort_keys=True), encoding="utf-8"
        )

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_state(self, uid: str) -> KnowledgeState:
        """Return the stored state, defaulting to 'unknown' for unseen objects."""
        return self._data.get(uid, {}).get("state", "unknown")

    def get_entry(self, uid: str) -> dict | None:
        """Return the full stored entry for a uid, or None if absent."""
        return self._data.get(uid)

    def get_all_for_file(self, source_file: str | Path) -> dict[str, dict]:
        """Return all entries whose uid belongs to the given source file."""
        prefix = f"{Path(source_file).resolve()}::"
        return {uid: entry for uid, entry in self._data.items() if uid.startswith(prefix)}

    def export_css_classes(self, uids: list[str]) -> dict[str, str]:
        """Map each uid to its CSS class name (used by the HTML explorer)."""
        return {uid: CSS_CLASS[self.get_state(uid)] for uid in uids}

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def set_state(self, uid: str, state: KnowledgeState, note: str = "") -> None:
        """Set the knowledge state for a single object."""
        if state not in VALID_STATES:
            raise ValueError(f"Invalid state {state!r}. Choose from: {sorted(VALID_STATES)}")
        entry = dict(self._data.get(uid, {}))
        entry["state"] = state
        entry["updated_at"] = self._now()
        if note:
            entry["note"] = note
        self._data[uid] = entry
        self._save()

    def ingest_objects(
        self,
        objects: list,          # list[LeanObject] — avoid circular import
        source_file: str | Path,
        default_state: KnowledgeState = "unknown",
    ) -> tuple[list[str], list[str]]:
        """
        Add objects to the store.

        - New objects are inserted with `default_state`.
        - Existing objects whose signature changed have their stored signature
          updated (state is preserved so the user's tagging is not lost).

        Returns (newly_added_uids, signature_changed_uids).
        """
        added: list[str] = []
        changed: list[str] = []

        for obj in objects:
            uid = make_uid(source_file, obj.name)
            if uid not in self._data:
                self._data[uid] = {
                    "kind": obj.kind,
                    "note": "",
                    "signature": obj.signature,
                    "state": default_state,
                    "updated_at": self._now(),
                }
                added.append(uid)
            else:
                if self._data[uid].get("signature", "") != obj.signature:
                    self._data[uid]["signature"] = obj.signature
                    self._data[uid]["kind"] = obj.kind
                    self._data[uid]["updated_at"] = self._now()
                    changed.append(uid)

        if added or changed:
            self._save()
        return added, changed
