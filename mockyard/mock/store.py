from collections import defaultdict
from typing import Any


class Store:
    def __init__(self):
        self._data: dict[str, dict[str, Any]] = defaultdict(dict)

    def list(self, collection: str) -> list[Any]:
        return list(self._data[collection].values())

    def get(self, collection: str, item_id: str) -> Any | None:
        return self._data[collection].get(item_id)

    def put(self, collection: str, item_id: str, value: Any):
        self._data[collection][item_id] = value

    def delete(self, collection: str, item_id: str) -> bool:
        return self._data[collection].pop(item_id, None) is not None