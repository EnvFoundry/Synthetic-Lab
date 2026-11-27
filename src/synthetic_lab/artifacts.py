"""External storage for large JSON values produced by laboratory models."""

import json
import os
import uuid
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path


@dataclass(frozen=True)
class StoredArtifact:
    id: str
    storage_key: str
    media_type: str
    encoding: str
    size_bytes: int

    def reference(self):
        return {
            "$artifact": {
                "id": self.id,
                "uri": f"artifact://{self.id}",
                "media_type": self.media_type,
                "encoding": self.encoding,
                "size_bytes": self.size_bytes,
            }
        }


def _encoder():
    return json.JSONEncoder(
        ensure_ascii=False,
        sort_keys=True,
        allow_nan=False,
        separators=(",", ":"),
    )


def _same_file(first, second, chunk_size=1024 * 1024):
    if not second.is_file() or first.stat().st_size != second.stat().st_size:
        return False
    with first.open("rb") as left, second.open("rb") as right:
        while True:
            a = left.read(chunk_size)
            b = right.read(chunk_size)
            if a != b:
                return False
            if not a:
                return True


class LocalArtifactStore:
    """A directory-backed store with opaque artifact identifiers."""

    def __init__(self, root):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / ".tmp").mkdir(exist_ok=True)

    def put_json(self, value, *, previous=None):
        temporary = self.root / ".tmp" / f"{uuid.uuid4().hex}.tmp"
        size = 0
        try:
            with temporary.open("wb") as stream:
                for text in _encoder().iterencode(value):
                    chunk = text.encode("utf-8")
                    stream.write(chunk)
                    size += len(chunk)
                stream.flush()
                os.fsync(stream.fileno())
            if previous is not None and size == previous.size_bytes:
                prior = self.root / previous.storage_key
                if _same_file(temporary, prior):
                    return previous
            identifier = uuid.uuid4().hex
            storage_key = f"{identifier[:2]}/{identifier}.json"
            destination = self.root / storage_key
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary.replace(destination)
            return StoredArtifact(identifier, storage_key, "application/json", "utf-8", size)
        finally:
            temporary.unlink(missing_ok=True)

    def open(self, storage_key):
        return (self.root / storage_key).open("rb")

    def discard(self, storage_key):
        (self.root / storage_key).unlink(missing_ok=True)


class MemoryArtifactStore:
    """An in-process store for in-memory experiment databases."""

    def __init__(self):
        self._objects = {}

    def put_json(self, value, *, previous=None):
        content = b"".join(text.encode("utf-8") for text in _encoder().iterencode(value))
        if previous is not None and self._objects.get(previous.storage_key) == content:
            return previous
        identifier = uuid.uuid4().hex
        self._objects[identifier] = content
        return StoredArtifact(identifier, identifier, "application/json", "utf-8", len(content))

    def open(self, storage_key):
        return BytesIO(self._objects[storage_key])

    def discard(self, storage_key):
        self._objects.pop(storage_key, None)


def json_size(value):
    return sum(len(text.encode("utf-8")) for text in _encoder().iterencode(value))


def is_reference(value):
    return (
        isinstance(value, dict)
        and set(value) == {"$artifact"}
        and isinstance(value["$artifact"], dict)
        and isinstance(value["$artifact"].get("id"), str)
    )
