"""Small async in-memory document store used only when MongoDB is unavailable."""

from copy import deepcopy
from types import SimpleNamespace

from bson import ObjectId
from pymongo.errors import DuplicateKeyError


def _matches(document: dict, query: dict) -> bool:
    return all(document.get(field) == value for field, value in query.items())


class MemoryCursor:
    def __init__(self, documents: list[dict]):
        self.documents = documents
        self.index = 0

    def sort(self, field: str, direction: int):
        self.documents.sort(key=lambda document: document.get(field), reverse=direction < 0)
        return self

    def limit(self, count: int):
        self.documents = self.documents[:count]
        return self

    def __aiter__(self):
        self.index = 0
        return self

    async def __anext__(self):
        if self.index >= len(self.documents):
            raise StopAsyncIteration
        document = deepcopy(self.documents[self.index])
        self.index += 1
        return document


class MemoryCollection:
    def __init__(self, *, unique_fields: tuple[str, ...] = ()):
        self.documents: list[dict] = []
        self.unique_fields = unique_fields

    async def create_index(self, *_args, **_kwargs):
        return None

    async def insert_one(self, document: dict):
        for field in self.unique_fields:
            if any(existing.get(field) == document.get(field) for existing in self.documents):
                raise DuplicateKeyError(f"Duplicate value for {field}")
        stored = deepcopy(document)
        stored.setdefault("_id", ObjectId())
        self.documents.append(stored)
        return SimpleNamespace(inserted_id=stored["_id"])

    async def find_one(self, query: dict):
        for document in self.documents:
            if _matches(document, query):
                return deepcopy(document)
        return None

    def find(self, query: dict):
        return MemoryCursor([deepcopy(document) for document in self.documents if _matches(document, query)])

    async def update_one(self, query: dict, update: dict):
        values = update.get("$set", {})
        for document in self.documents:
            if _matches(document, query):
                for field, value in values.items():
                    document[field] = deepcopy(value)
                return SimpleNamespace(matched_count=1, modified_count=1)
        return SimpleNamespace(matched_count=0, modified_count=0)


class MemoryDatabase:
    def __init__(self):
        self.users = MemoryCollection(unique_fields=("email",))
        self.sessions = MemoryCollection()

    async def command(self, _command: str):
        return {"ok": 1}
