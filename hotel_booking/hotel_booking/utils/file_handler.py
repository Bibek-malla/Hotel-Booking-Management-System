"""Reusable, safe JSON persistence layer.

One ``JsonStore`` manages one JSON file that holds a list of records
(dictionaries). Writes are atomic (temp file + replace) so a crash while
saving cannot leave a half-written file behind.
"""
import json
import logging
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from utils.exceptions import DataStoreError, NotFoundError

logger = logging.getLogger(__name__)


class JsonStore:
    """List-of-records JSON file with CRUD helpers."""

    def __init__(self, path, id_field):
        self.path = Path(path)
        self.id_field = id_field
        self._ensure_file()

    # ------------------------------------------------------------------
    # File level operations
    # ------------------------------------------------------------------
    def _ensure_file(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            file_missing = not self.path.exists()
        except OSError as exc:
            raise DataStoreError(
                f"Cannot prepare data folder for '{self.path}': {exc}"
            ) from exc
        if file_missing:
            self.write_all([])

    def read_all(self):
        """Return all records. Missing/corrupted files are recovered."""
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except FileNotFoundError:
            self.write_all([])
            return []
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            self._recover_corrupt_file(str(exc))
            return []
        except OSError as exc:  # includes PermissionError
            raise DataStoreError(
                f"Cannot read '{self.path.name}': {exc}"
            ) from exc

        if not isinstance(data, list):
            self._recover_corrupt_file("top-level JSON value is not a list")
            return []
        return [record for record in data if isinstance(record, dict)]

    def write_all(self, records):
        """Atomically replace the file content with ``records``."""
        tmp_path = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=self.path.parent,
                suffix=".tmp", delete=False,
            ) as tmp:
                tmp_path = Path(tmp.name)
                json.dump(records, tmp, indent=2, ensure_ascii=False)
                tmp.flush()
                os.fsync(tmp.fileno())
            os.replace(tmp_path, self.path)
        except (OSError, TypeError) as exc:
            self._discard_temp_file(tmp_path)
            raise DataStoreError(
                f"Cannot write '{self.path.name}': {exc}"
            ) from exc

    @staticmethod
    def _discard_temp_file(tmp_path):
        if tmp_path is None or not tmp_path.exists():
            return
        try:
            tmp_path.unlink()
        except OSError as exc:
            logger.warning("Could not remove temp file %s: %s", tmp_path, exc)

    def _recover_corrupt_file(self, reason):
        """Keep a backup of an unreadable file and start with an empty one."""
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = self.path.with_name(
            f"{self.path.stem}.corrupt-{stamp}{self.path.suffix}"
        )
        try:
            os.replace(self.path, backup)
        except OSError as exc:
            raise DataStoreError(
                f"'{self.path.name}' is corrupted and could not be backed "
                f"up: {exc}"
            ) from exc
        print(
            f"[WARNING] {self.path.name} was unreadable ({reason}). "
            f"A backup was saved as {backup.name}; a new file was created.",
            file=sys.stderr,
        )
        self.write_all([])

    # ------------------------------------------------------------------
    # Record level operations
    # ------------------------------------------------------------------
    @staticmethod
    def _is_valid_id(value):
        return isinstance(value, int) and not isinstance(value, bool)

    def next_id(self, records=None):
        """Return the next unused integer id."""
        records = self.read_all() if records is None else records
        ids = [r[self.id_field] for r in records
               if self._is_valid_id(r.get(self.id_field))]
        return max(ids, default=0) + 1

    def get(self, id_value):
        """Return the record with the given id, or None."""
        for record in self.read_all():
            if record.get(self.id_field) == id_value:
                return record
        return None

    def find(self, predicate):
        """Return all records for which ``predicate(record)`` is true."""
        return [r for r in self.read_all() if predicate(r)]

    def add(self, record):
        """Append a record, generating its id when it has none."""
        records = self.read_all()
        new_record = dict(record)
        if new_record.get(self.id_field) is None:
            new_record[self.id_field] = self.next_id(records)
        elif any(r.get(self.id_field) == new_record[self.id_field]
                 for r in records):
            raise DataStoreError(
                f"Duplicate id {new_record[self.id_field]} in "
                f"{self.path.name}."
            )
        records.append(new_record)
        self.write_all(records)
        return new_record

    def update(self, id_value, changes):
        """Merge ``changes`` into the record with the given id."""
        records = self.read_all()
        for record in records:
            if record.get(self.id_field) == id_value:
                record.update(changes)
                record[self.id_field] = id_value
                self.write_all(records)
                return dict(record)
        raise NotFoundError(
            f"Record {id_value} not found in {self.path.name}."
        )

    def delete(self, id_value):
        """Remove a record. Returns True if something was deleted."""
        records = self.read_all()
        remaining = [r for r in records
                     if r.get(self.id_field) != id_value]
        if len(remaining) == len(records):
            return False
        self.write_all(remaining)
        return True
