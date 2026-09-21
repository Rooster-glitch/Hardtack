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
            self._reset_md()

    def _reset_md(self) -> None:
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

        self._append_md(entry)
        return entry

    def _append_md(self, entry: Dict[str, Any]) -> None:
        with self.md_path.open("a", encoding="utf-8") as f:
            f.write(f"## {entry['timestamp']} — {entry['role']}\n\n{entry['content']}\n\n")
            if entry.get("metadata"):
                f.write(f"```json\n{json.dumps(entry['metadata'], indent=2)}\n```\n\n")
            f.write(f"`hash: {entry['hash']}`\n\n---\n\n")

    def _rebuild_md(self) -> None:
        self._reset_md()
        for entry in self.get_entries():
            self._append_md(entry)

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
        if not entries:
            return True

        for i, entry in enumerate(entries):
            # Verify internal hash structure first
            hash_copy = dict(entry)
            stored_hash = hash_copy.pop("hash", None)
            if self._hash(hash_copy) != stored_hash:
                return False

            # First entry verification
            if i == 0:
                is_checkpoint = (
                    entry.get("role") == "system"
                    and "CHECKPOINT" in entry.get("content", "")
                )
                if is_checkpoint:
                    # Checkpoint's prev_hash must match its metadata's last_archived_hash
                    expected_archive_hash = entry.get("metadata", {}).get("last_archived_hash")
                    if entry.get("prev_hash") != expected_archive_hash:
                        return False
                else:
                    # Standard genesis entry starts from zero-hash
                    if entry.get("prev_hash") != "0" * 64:
                        return False
            else:
                # Every subsequent entry must point strictly to the previous entry's hash
                if entry.get("prev_hash") != entries[i - 1]["hash"]:
                    return False

        return True

    def prune(self, before_timestamp: str) -> int:
        """Archives entries older than timestamp, re-chains active entries, and rebuilds state."""
        entries = self.get_entries()
        if not entries:
            return 0

        archived: List[Dict[str, Any]] = []
        active_raw: List[Dict[str, Any]] = []

        for e in entries:
            if e["timestamp"] < before_timestamp:
                archived.append(e)
            else:
                active_raw.append(e)

        if not archived:
            return 0

        # 1. Save archive
        archive_dir = self.root / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        archive_file = archive_dir / f"entries_archive_{timestamp_str}.jsonl"

        with archive_file.open("w", encoding="utf-8") as f:
            for e in archived:
                f.write(json.dumps(e, sort_keys=True) + "\n")

        # 2. Build Checkpoint
        last_archived_hash = archived[-1]["hash"]
        checkpoint = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "role": "system",
            "content": f"CHECKPOINT: Pruned {len(archived)} entries. Archive: {archive_file.name}",
            "metadata": {
                "archive_file": str(archive_file.name),
                "last_archived_hash": last_archived_hash,
            },
            "prev_hash": last_archived_hash,
        }
        checkpoint["hash"] = self._hash(checkpoint)

        # 3. Re-chain active entries onto the checkpoint
        rechained_active: List[Dict[str, Any]] = [checkpoint]
        current_prev = checkpoint["hash"]

        for item in active_raw:
            new_item = dict(item)
            new_item["prev_hash"] = current_prev
            new_item["hash"] = self._hash(new_item)
            rechained_active.append(new_item)
            current_prev = new_item["hash"]

        # 4. Overwrite JSONL and sync Markdown
        with self.jsonl_path.open("w", encoding="utf-8") as f:
            for e in rechained_active:
                f.write(json.dumps(e, sort_keys=True) + "\n")

        self._rebuild_md()
        return len(archived)

    def search(self, query: str) -> List[Dict[str, Any]]:
        q = query.lower()
        return [
            e
            for e in self.get_entries()
            if q in e.get("content", "").lower() or q in e.get("role", "").lower()
        ]

    def export_markdown(self) -> str:
        return self.md_path.read_text(encoding="utf-8")
            
