"""
This is a module with Cacheable Data protocol for typing and ABC for common functionality.
"""

from collections import OrderedDict
from typing import Any, Generator, Iterable, KeysView, Protocol, Optional, Sequence, ValuesView
from abc import ABC, abstractmethod

from helpers import create_file_if_file_does_not_exist


class CacheableData(Protocol):
    """
    Caching using operations between the internal cache and the external cache.

    Internal cache is located in the memory by str keys. Can only be an OrderedDict or its subclasses.
    External cache is located in the file system, db, etc.

    Btw, file-based external cache doesn't use aiofiles because it's very unstable
    and makes lots of garbage lines. Plus pickle doesn't support async IO either.

    TODO: Probably will have to make an async version of CacheableData if I get my hands on databases. Or not.
    """
    _data: dict[str, Any]

    def __iter__(self) -> Generator[str, None, None]:
        ...

    def __setitem__(self, key: str, value: Any):
        ...

    def __getitem__(self, key: str) -> Any:
        ...

    def __delitem__(self, key: str):
        ...

    def items(self) -> tuple[str, Any]:
        """
        Gets list of tuples of keys and values of internal cache.
        """

    def keys(self) -> KeysView[str]:
        """
        Gets keys  of internal cache.
        """

    def values(self) -> ValuesView[Any]:
        """
        Gets values of internal cache.
        """

    def reorder_by(self, keys: Iterable):
        """
        Reorders memory data based on some iterable containing memory data keys.
        """

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """
        Returns the value of the given key in the internal cache or the default value.
        """

    def set(self, key: str, value: Any):
        """
        Sets the value of the given key in internal cache.
        """

    def update_internal_cache(self):
        """
        Updates the internal cache from the external cache.
        """

    def update_external_cache(self):
        """
        Updates the external cache from the internal cache.
        """


class AbstractFileCacheableData(ABC):
    """
    Caching using operations between the memory data and the file cache. Loads from cache file on __init__ by default.

    Beware that when you update external cache everything will stay there until the file is deleted or rewritten.
    It is very important to note that all previous keys will also stay unless you delete the file.
    Values, however, can be rewritten by key when you update the external cache
    with different value assigned to the corresponding key in the internal cache.
    """
    path: str
    _data: OrderedDict[str, Any]

    def __init__(self, path):
        self.path = path
        self._data = OrderedDict()
        create_file_if_file_does_not_exist(self.path)
        self.update_internal_cache()
        print(self._data)
        # sleep(10)

    def __repr__(self):     # Can't use fstrings here.
        return f'{{  length = {len(self._data)},  path = {self.path}\n\t' + ',\n\t'.join(': '.join((key, repr(self._data[key]))) for key in self._data) + '\n}'

    def __iter__(self) -> Generator[str, None, None]:
        return self.iterator()

    def __setitem__(self, key: str, value: Any):
        self._data[key] = value

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __delitem__(self, key: str):
        del self._data[key]

    def iterator(self) -> Generator[str, None, None]:
        for key in self._data:
            yield key

    def items(self) -> Generator[tuple[str, Any], None, None]:
        for key, val in self._data.items():
            yield key, val

    def keys(self) -> KeysView[str]:
        return self._data.keys()

    def values(self) -> ValuesView[Any]:
        return self._data.values()

    def reorder_by(self, keys: Sequence):
        """
        Reorders memory data based on some sequence containing memory data keys.
        """
        try:
            sort_map = dict(zip(keys, range(len(keys))))
            self._data = OrderedDict(sorted(self._data.items(), key=lambda x: sort_map[x[0]]))
        except KeyError as e:
            print('KEYS DO NOT MATCH')
            print(sort_map)
            print(self._data)
            print(e)

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """
        Returns the value of the given key in the memory data or the default value.
        """
        if key in self._data:
            value = self._data[key]
        else:
            value = default
        return value

    def set(self, key: str, value: Any):
        """
        Sets the value of the given key in the memory data.
        """
        if self._data is None:
            self._data = OrderedDict()
        self._data[key] = value

    @abstractmethod
    def update_internal_cache(self):
        """
        Updates the memory data from the file cache.
        """

    @abstractmethod
    def update_external_cache(self):
        """
        Updates the file cache from the memory data.
        """
