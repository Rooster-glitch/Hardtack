import tempfile
from pathlib import Path

from hardtack.ledger import Ledger


def test_log_and_verify():
    with tempfile.TemporaryDirectory() as tmp:
        ledger = Ledger(tmp)
        ledger.log("human", "The fire went out.")
        ledger.log("machine", "The owl said nothing.")
        ledger.log("human", "But the hardtack was real.")
        assert ledger.verify() is True


def test_search():
    with tempfile.TemporaryDirectory() as tmp:
        ledger = Ledger(tmp)
        ledger.log("human", "The desert fox knows two winds.")
        results = ledger.search("fox")
        assert len(results) == 1
        assert "fox" in results[0]["content"]


def test_verify_detects_tamper():
    with tempfile.TemporaryDirectory() as tmp:
        ledger = Ledger(tmp)
        ledger.log("human", "Original")
        path = Path(tmp) / "entries.jsonl"
        lines = path.read_text().strip().split("\n")
        lines[0] = lines[0].replace("Original", "Tampered")
        path.write_text("\n".join(lines) + "\n")
        assert ledger.verify() is False
