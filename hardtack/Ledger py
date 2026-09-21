from __future__ import annotations

import hashlib
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class Ledger:
    """Append-only, hash-chained context ledger with archival verification."""

    def __init__(self, root: str | Path = ".hardtack"):
        self.root = Path(root)
        self.jsonl_path = self.root / "entries.jsonl"
        self.md_path = self.root / "entries.md"
        self.archive_dir = self.root / "archive"
        
        self.root.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.jsonl_path.exists():
            self.jsonl_path.touch()
        if not self.md_path.exists():
            self._reset_md()

    def _reset_md(self) -> None:
        self.md_path.write_text("# Hardtack Ledger\n\n", encoding="utf-8")

    def _canonical(self, entry: Dict[str, Any]) -> str:
        """Returns deterministic JSON string without whitespace formatting differences."""
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

        # Append canonical JSON to eliminate whitespace variances
        with self.jsonl_path.open("a", encoding="utf-8") as f:
            f.write(self._canonical(entry) + "\n")

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

    def get_entries(self, target_path: Optional[Path] = None) -> List[Dict[str, Any]]:
        path = target_path or self.jsonl_path
        entries: List[Dict[str, Any]] = []
        if not path.exists():
            return entries
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entries.append(json.loads(line))
        return entries

    def verify(self, check_archives: bool = False) -> bool:
        """
        Verifies the cryptographic chain integrity.
        If check_archives is True, follows checkpoints into historical archive files.
        """
        entries = self.get_entries()
        if not entries:
            return True

        for i, entry in enumerate(entries):
            # 1. Check internal node hash structure
            hash_copy = dict(entry)
            stored_hash = hash_copy.pop("hash", None)
            if self._hash(hash_copy) != stored_hash:
                return False

            # 2. Check chain link consistency
            if i == 0:
                is_checkpoint = (
                    entry.get("role") == "system"
                    and "CHECKPOINT" in entry.get("content", "")
                )
                if is_checkpoint:
                    expected_archive_hash = entry.get("metadata", {}).get("last_archived_hash")
                    if entry.get("prev_hash") != expected_archive_hash:
                        return False
                    
                    # Recursively verify the referenced archive file if requested
                    if check_archives:
                        archive_filename = entry.get("metadata", {}).get("archive_file")
                        if archive_filename:
                            archive_path = self.archive_dir / archive_filename
                            if not archive_path.exists():
                                return False
                            archive_entries = self.get_entries(archive_path)
                            if not archive_entries or archive_entries[-1]["hash"] != expected_archive_hash:
                                return False
                else:
                    if entry.get("prev_hash") != "0" * 64:
                        return False
            else:
                if entry.get("prev_hash") != entries[i - 1]["hash"]:
                    return False

        return True

    def prune(self, before_timestamp: str) -> int:
        """Archives entries older than timestamp, re-chains active entries, and writes atomically."""
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

        # 1. Write archive file atomically
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        archive_file_name = f"entries_archive_{timestamp_str}.jsonl"
        archive_path = self.archive_dir / archive_file_name

        with archive_path.open("w", encoding="utf-8") as f:
            for e in archived:
                f.write(self._canonical(e) + "\n")

        # 2. Construct Genesis Checkpoint
        last_archived_hash = archived[-1]["hash"]
        checkpoint = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "role": "system",
            "content": f"CHECKPOINT: Pruned {len(archived)} entries. Archive: {archive_file_name}",
            "metadata": {
                "archive_file": archive_file_name,
                "last_archived_hash": last_archived_hash,
            },
            "prev_hash": last_archived_hash,
        }
        checkpoint["hash"] = self._hash(checkpoint)

        # 3. Re-chain active entries onto the new checkpoint head
        rechained_active: List[Dict[str, Any]] = [checkpoint]
        current_prev = checkpoint["hash"]

        for item in active_raw:
            new_item = dict(item)
            new_item["prev_hash"] = current_prev
            new_item["hash"] = self._hash(new_item)
            rechained_active.append(new_item)
            current_prev = new_item["hash"]

        # 4. Atomic write to active jsonl to prevent zero-byte corruptions
        with tempfile.NamedTemporaryFile("w", dir=self.root, delete=False, encoding="utf-8") as tf:
            temp_name = tf.name
            for e in rechained_active:
                tf.write(self._canonical(e) + "\n")

        Path(temp_name).replace(self.jsonl_path)

        # 5. Rebuild Markdown output
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
