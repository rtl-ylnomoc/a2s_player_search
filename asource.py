"""
This is a module that acts as an entry point for the application.

Asynchronous version.
"""
from os.path import join

from rich.traceback import install
from cache.cacheable_data import PickleCacheableData, TextFileCacheableData

from name_parsers import AsyncNameParser

from helpers import BASE_DIR
from server_name_parsers import AsyncServerNameParser
from server_parsers import AsyncServerParser
from main import main
install()

if __name__ == '__main__':
    # main(AsyncServerNameParser(),
    #      AsyncServerParser(),
    #      AsyncNameParser(PickleCacheableData(join(BASE_DIR, 'data/async_names_cache.bin')), is_silent=True))
    main(AsyncServerNameParser(),
         AsyncServerParser(),
         AsyncNameParser(TextFileCacheableData(join(BASE_DIR, 'data/async_names_cache.txt')), is_silent=True))
