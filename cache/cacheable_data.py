"""
This is a module that defines some CacheableData implementations,
including based on my own text format (TextFileCacheableData).
"""

import pickle
from collections import OrderedDict

import hjson

from .abstract_cacheable_data import AbstractFileCacheableData
from .bazed_strings import serializers, deserializers, disorders


class PickleCacheableData(AbstractFileCacheableData):
    """
    Caching using operations between the memory data and the pickled binary file.
    """

    def update_internal_cache(self):
        """
        Updates the memory data from the pickled binary file.
        """
        data = self._data
        with open(self.path, 'rb') as f:
            f.seek(0)
            unpickler = pickle.Unpickler(f, encoding='utf-8')
            try:
                data = unpickler.load()
            except EOFError as e:
                print('[UPDATING INTERNAL CACHE]', e)
        if not isinstance(data, OrderedDict):
            raise TypeError('Cache data must be a dictionary.')
        self._data = data

    def update_external_cache(self):
        """
        Updates the pickled binary file from the memory data.
        """
        with open(self.path, 'wb') as f:
            f.seek(0)
            pickler = pickle.Pickler(f)
            try:
                pickler.dump(self._data)
            except EOFError as e:
                print('[UPDATING EXTERNAL CACHE]', e)


class TextFileCacheableData(AbstractFileCacheableData):
    """
    Caching using operations between the memory data and the text file. Only supports some base types.
    """
    encoding: str

    def __init__(self, path, encoding='utf-8'):
        self.encoding = encoding
        super().__init__(path)

    def update_internal_cache(self):
        """
        Updates the memory data from the text file.
        """
        with open(self.path, 'r', encoding=self.encoding) as f:
            text = f.read().rstrip()
            if text.startswith('[VALID]'):
                self._data = OrderedDict(deserializers.loads(text[7::]))

    def update_external_cache(self):
        """
        Updates the text file from the memory data.
        """
        with open(self.path, 'w', encoding=self.encoding) as f:
            text = serializers.dumps(disorders.disorder_value(self._data))
            f.write('[VALID]'+text)


class HJSONFileCacheableData(AbstractFileCacheableData):
    def update_internal_cache(self):
        """
        Updates the memory data from the hjson file.
        """
        with open(self.path, 'r', encoding='utf-8') as f:
            self._data = hjson.load(f, encoding='utf-8')

    def update_external_cache(self):
        """
        Updates the hjson file from the memory data.
        """
        with open(self.path, 'w', encoding='utf-8') as f:
            hjson.dump(self._data, f, encoding='utf-8')
