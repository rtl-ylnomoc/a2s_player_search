"""
This is a module that acts as an entry point for the application.

Synchronous version (*).

(*) Note that only server parser is synchronous
    because SyncServerParser implementation provides at least some advantages over using AsyncServerParser
    unlike other sync implementations which are too slow, especially on scale.
"""
from os.path import join

from rich.traceback import install
from cache.cacheable_data import PickleCacheableData

from name_parsers import AsyncNameParser, SyncNameParser
from helpers import BASE_DIR
from server_name_parsers import AsyncServerNameParser, SyncServerNameParser
from server_parsers import AsyncServerParser, SyncServerParser
from main import main
install()

if __name__ == '__main__':
    main(AsyncServerNameParser(),
         SyncServerParser(),
         AsyncNameParser(PickleCacheableData(join(BASE_DIR, 'data/async_names_cache.bin')), is_silent=True))
