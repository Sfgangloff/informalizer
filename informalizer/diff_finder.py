"""Find objects in a Lean file that are new, changed, or already seen in the knowledge store."""

from dataclasses import dataclass, field

from .lean_parser import LeanObject
from .knowledge_store import KnowledgeStore, KnowledgeState, make_uid


@dataclass
class DiffReport:
    new: list[LeanObject] = field(default_factory=list)
    changed: list[LeanObject] = field(default_factory=list)
    seen: list[LeanObject] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.new) + len(self.changed) + len(self.seen)

    def state_of(self, obj: LeanObject, source_file: str, store: KnowledgeStore) -> KnowledgeState:
        """Convenience: return the stored knowledge state for an object."""
        return store.get_state(make_uid(source_file, obj.name))


def find_diff(
    objects: list[LeanObject],
    source_file: str,
    store: KnowledgeStore,
) -> DiffReport:
    """
    Compare a parsed file's objects against the knowledge store.

    - new:     uid absent from the store
    - changed: uid present but stored signature differs from current
    - seen:    uid present and signature unchanged
    """
    report = DiffReport()
    for obj in objects:
        uid = make_uid(source_file, obj.name)
        entry = store.get_entry(uid)
        if entry is None:
            report.new.append(obj)
        elif entry.get("signature", "") != obj.signature:
            report.changed.append(obj)
        else:
            report.seen.append(obj)
    return report
