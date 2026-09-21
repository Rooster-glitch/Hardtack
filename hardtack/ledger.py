from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class Ledger:
    """Append-only, hash-chained context ledger."""

    def __init__(self, root: str | Path = ".hardtack"):
        self.root = Path(root)
        self.jsonl_path = self.root / "entries.jsonl"
        self.md_path = self.root / "entries.md"
        self.root.mkdir(parents=True, exist_ok=True)
        if not self.jsonl_path.exists():
            self.jsonl_path.touch()
        if not self.md_path.exists():
            self.md_path.write_text("# Hardtack Ledger\n\n", encoding="utf-8")

    def _canonical(self, entry: Dict[str, Any]) -> str:
        return json.dumps(entry, sort_keys=True, separators=(",", ":"))

    def _hash(self, entry: Dict[str, Any]) -> str:
        return hashlib.sha256(self._canonical(entry).encode("utf-8")).hexdigest()

    def _last_hash(self) -> str:
        entries = self.get_entries()
        if not entries:
            return "0" * 64
        return entries[-1]["hash"]

    def log(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        prev_hash = self._last_hash()
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "prev_hash": prev_hash,
        }
        entry["hash"] = self._hash(entry)

        with self.jsonl_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, sort_keys=True) + "\n")

        with self.md_path.open("a", encoding="utf-8") as f:
            f.write(f"## {entry['timestamp']} — {role}\n\n{content}\n\n")
            if metadata:
                f.write(f"```json\n{json.dumps(metadata, indent=2)}\n```\n\n")
            f.write(f"`hash: {entry['hash']}`\n\n---\n\n")

        return entry

    def get_entries(self) -> List[Dict[str, Any]]:
        entries: List[Dict[str, Any]] = []
        if not self.jsonl_path.exists():
            return entries
        with self.jsonl_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entries.append(json.loads(line))
        return entries

    def verify(self) -> bool:
        entries = self.get_entries()
        prev = "0" * 64
        for entry in entries:
            if entry.get("prev_hash") != prev:
                return False
            hash_copy = dict(entry)
            stored_hash = hash_copy.pop("hash")
            if self._hash(hash_copy) != stored_hash:
                return False
            prev = stored_hash
        return True

    def search(self, query: str) -> List[Dict[str, Any]]:
        q = query.lower()
        return [
            e
            for e in self.get_entries()
            if q in e.get("content", "").lower() or q in e.get("role", "").lower()
        ]

    def export_markdown(self) -> str:
        return self.md_path.read_text(encoding="utf-8")


def prune(self, before_timestamp: str) -> int:
    """Archives entries older than the timestamp and resets the active chain."""
    entries = self.get_entries()
    if not entries:
        return 0

    archived = []
    active = []

    for e in entries:
        if e["timestamp"] < before_timestamp:
            archived.append(e)
        else:
            active.append(e)

    if not archived:
        print("No entries match the prune criteria.")
        return 0

    # 1. Save the archive
    archive_dir = self.root / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_file = archive_dir / f"entries_archive_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.jsonl"
    
    with archive_file.open("w", encoding="utf-8") as f:
        for e in archived:
            f.write(json.dumps(e, sort_keys=True) + "\n")

    # 2. Create the new Genesis Checkpoint
    last_archived_hash = archived[-1]["hash"]
    checkpoint = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "role": "system",
        "content": f"CHECKPOINT: Pruned {len(archived)} entries. Archive: {archive_file.name}",
        "metadata": {"archive_file": str(archive_file.name), "last_archived_hash": last_archived_hash},
        "prev_hash": last_archived_hash # Links the new chain to the old chain's head
    }
    checkpoint["hash"] = self._hash(checkpoint)
    active.insert(0, checkpoint)

    # 3. Rewrite the active ledger
    with self.jsonl_path.open("w", encoding="utf-8") as f:
        for e in active:
            f.write(json.dumps(e, sort_keys=True) + "\n")

    print(f"Pruned {len(archived)} entries. Archive saved to {archive_file}")
    return len(archived)


def prune(self, before_timestamp: str) -> int:
    """Archives entries older than the timestamp and resets the active chain."""
    entries = self.get_entries()
    if not entries:
        return 0

    archived = []
    active = []

    for e in entries:
        if e["timestamp"] < before_timestamp:
            archived.append(e)
        else:
            active.append(e)

    if not archived:
        print("No entries match the prune criteria.")
        return 0

    # 1. Save the archive
    archive_dir = self.root / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_file = archive_dir / f"entries_archive_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.jsonl"
    
    with archive_file.open("w", encoding="utf-8") as f:
        for e in archived:
            f.write(json.dumps(e, sort_keys=True) + "\n")

    # 2. Create the new Genesis Checkpoint
    last_archived_hash = archived[-1]["hash"]
    checkpoint = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "role": "system",
        "content": f"CHECKPOINT: Pruned {len(archived)} entries. Archive: {archive_file.name}",
        "metadata": {"archive_file": str(archive_file.name), "last_archived_hash": last_archived_hash},
        "prev_hash": last_archived_hash # Links the new chain to the old chain's head
    }
    checkpoint["hash"] = self._hash(checkpoint)
    active.insert(0, checkpoint)

    # 3. Rewrite the active ledger
    with self.jsonl_path.open("w", encoding="utf-8") as f:
        for e in active:
            f.write(json.dumps(e, sort_keys=True) + "\n")

    print(f"Pruned {len(archived)} entries. Archive saved to {archive_file}")
    return len(archived)

def verify(self) -> bool:
    entries = self.get_entries()
    if not entries:
        return True
    
    prev = "0" * 64
    for i, entry in enumerate(entries):
        # Allow the first entry to be a Checkpoint linked to an archive
        if i == 0 and entry.get("role") == "system" and "CHECKPOINT" in entry.get("content", ""):
            if entry.get("prev_hash") != entry.get("metadata", {}).get("last_archived_hash"):
                return False
        else:
            if entry.get("prev_hash") != prev:
                return False
        
        hash_copy = dict(entry)
        stored_hash = hash_copy.pop("hash")
        if self._hash(hash_copy) != stored_hash:
            return False
        prev = stored_hash
    return True
