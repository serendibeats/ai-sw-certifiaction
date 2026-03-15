import uuid
import time


class DLQEntry:
    def __init__(self, record, error, processor_name=None):
        self.id = str(uuid.uuid4())
        self.record = record
        self.error = str(error)
        self.processor_name = processor_name
        self.timestamp = time.time()

    def to_dict(self):
        return {
            "id": self.id,
            "record_id": self.record.id if hasattr(self.record, 'id') else None,
            "error": self.error,
            "processor_name": self.processor_name,
            "timestamp": self.timestamp,
        }


class DeadLetterQueue:
    def __init__(self, max_size=1000):
        self.max_size = max_size
        self._entries = {}

    def add(self, record, error=None, processor_name=None):
        if len(self._entries) >= self.max_size:
            # Remove oldest entry
            oldest_key = min(self._entries, key=lambda k: self._entries[k].timestamp)
            del self._entries[oldest_key]

        if error is None:
            error = "Unknown error"
        entry = DLQEntry(record, error, processor_name)
        self._entries[entry.id] = entry
        return entry

    def get_all(self):
        return list(self._entries.values())

    def get_by_processor(self, processor_name):
        return [
            entry for entry in self._entries.values()
            if entry.processor_name is not None
            and entry.processor_name.lower() == processor_name.lower()
        ]

    def retry(self, entry_id):
        if entry_id not in self._entries:
            raise KeyError(f"Entry '{entry_id}' not found")
        entry = self._entries.pop(entry_id)
        return entry.record

    def clear(self):
        self._entries.clear()

    @property
    def count(self):
        return len(self._entries)
