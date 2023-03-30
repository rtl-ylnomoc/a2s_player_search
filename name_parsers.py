"""
This is a module that defines sync and async name parsers.
They retrieve current names by Steam account links and also dump them in CacheableData form
for caching or interoperability with other name parser instances.

P.S. btw not using steam api in order to not hit api limits.
"""

import socket
import asyncio
import concurrent
from abc import ABC, abstractmethod
from time import perf_counter
from typing import Optional, Protocol

import aiohttp
import requests     # type: ignore # lib stubs
import bs4

from cache.abstract_cacheable_data import CacheableData
from cache.cacheable_data import TextFileCacheableData, PickleCacheableData
from cache.cache_managers import NameParserCacheManager
from helpers import CONFIG, CONSOLE, LINKS_FLAGS_MAP_PATH, NAMES_PATH, remove_diacritics
from hjson import loads
from rich import box, table

from notifications import notify_ingame


def get_links_flags_map() -> dict[str, dict[str, bool]]:
    with open(LINKS_FLAGS_MAP_PATH) as f:
        links_flags_map = loads(f.read())
    return links_flags_map


def get_name_table_scaffold() -> table.Table:
    name_table = table.Table(title='Name Table', box=box.SIMPLE_HEAD)    # console table of names
    name_table.add_column('Name', style='red')
    name_table.add_column('Status', style='bright_magenta')
    name_table.add_column('Flags', style='cyan1')
    return name_table


TIMEOUT_TIME = CONFIG['NAME_PARSERS']['TIMEOUT_TIME']
MAX_FAILS_CON = CONFIG['NAME_PARSERS']['MAX_FAILS_CON']   # max timeout time = MAX_FAILS_CON * TIMEOUT_TIME
# notify when a steam account is in these games if possible. All Steam games should work if the titles are correct.
INGAMES = CONFIG['NAME_PARSERS']['INGAMES']

TEXT_NAMES_PATH = NAMES_PATH + '_cache_prod.txt'
PICKLE_NAMES_PATH = NAMES_PATH + '_cache_prod.bin'
HJSON_NAMES_PATH = NAMES_PATH + '_cache_prod.hjson'

LINKS_FLAGS_MAP = get_links_flags_map()


class NameParser(Protocol):
    _links_flags_map: dict[str, dict[str, bool]]  # Mappings of Steam account links to their flag maps
    names: set[str]     # Set of parsed names.
    timeout_time: int   # Maximum time for one HTTP response
    max_fails_con: int  # Maximum consecutive fails to get name info
    ingames: list[str]  # A list of games that summon notifications if 'in_game' flag enabled
    is_silent: bool     # Whether to log failed connection attempts

    @staticmethod
    def parse_name_status_ingame(parser: bs4.BeautifulSoup) -> tuple[str, str, str]:
        ...
        
    def is_ingame(self, link: str, status: str, ingame: str) -> bool:
        ...
    
    def get_flags_by_link(self, link: str) -> dict[str, bool]:
        ...

    def get_all_links(self) -> list[str]:
        ...

    @abstractmethod
    def parse_links_info(self) -> CacheableData:
        ...


class AbstractNameParser(ABC, NameParserCacheManager):  # Trying different OOP approaches. Don't want too much delegating code.
    _links_flags_map: dict[str, dict[str, bool]]  # Mappings of Steam account links to their flag maps
    names: set[str]     # Set of parsed names.
    timeout_time: int   # Maximum time for one HTTP response
    max_fails_con: int  # Maximum consecutive fails to get name info
    ingames: list[str]  # A list of games that summon notifications if 'in_game' flag enabled
    is_silent: bool     # Whether to log failed connection attempts

    @staticmethod
    def parse_name_status_ingame(parser: bs4.BeautifulSoup) -> tuple[str, str, str]:
        """
        Parses retrieved content from a Steam account link page.
        """
        name = str(parser.select_one('.actual_persona_name').contents[0])  # it's always available if link opened
        status = parser.select_one('.profile_in_game_header')
        if status and len(status.contents) > 0:
            status = str(status.contents[0].strip())
        else:
            status = 'Private'
        ingame = parser.select_one('.profile_in_game_name')
        if ingame and len(ingame.contents) > 0:
            ingame = str(ingame.contents[0].strip())
        else:
            ingame = ''
        return name, status, ingame

    def __init__(self, links_info_map, timeout_time=TIMEOUT_TIME, max_fails_con=MAX_FAILS_CON, ingames=INGAMES,
                 links_flags_map=LINKS_FLAGS_MAP, is_silent=False):
        super().__init__(links_info_map)
        self.timeout_time = timeout_time
        self.max_fails_con = max_fails_con
        self._links_flags_map = links_flags_map
        self.ingames = ingames
        self.is_silent = is_silent
        self.remove_extra_links_from_cache(links_flags_map.keys())

    def is_ingame(self, link: str, status: str, ingame: str) -> bool:
        """
        Checks in_game flag and status. If in_game flag is true and the account is in game returns True.
        """
        return (self.get_flags_by_link(link).get('in_game', False) and  # type: ignore # btw using () instead of \ cuz can't type ignore with them
                (status != 'Private' and status.startswith('Currently In-Game')) and
                (ingame and ingame in self.ingames))

    def get_flags_by_link(self, link: str) -> dict[str, bool]:
        """
        Gets flags map by it's corresponding link.
        """
        return self._links_flags_map[link]

    def get_all_links(self) -> list[str]:
        """
        Gets a list of all links from links flags map.
        """
        return list(self._links_flags_map.keys())

    @abstractmethod
    def parse_links_info(self) -> CacheableData:
        """
        Parses all links and populates links_info_map.
        Returns a links_info_map of successufully parsed names
        """


class SyncNameParser(AbstractNameParser):
    def parse_links_info(self):
        """
        Runs link parsing tasks and returns a set of parsed names and links info map.
        Saves cached links info in proper order.
        """
        links, names = set(), set()
        with requests.Session() as session:
            for link in self._links_flags_map:
                result = self.parse_link_for_current_info(link, session)
                if None not in result:
                    links.add(result[0])
                    names.add(result[1])
                print(result)
        self.names = names
        self.reorder_links_info_map([key for key in self.get_all_links() if key in links])
        self.save_cache()
        return self.links_info_map

    def parse_link_for_current_info(self, link: str, session: requests.Session) -> tuple[Optional[str], ...]:
        """
        Parses link to get current Steam account name, status and game the player is currently in.
        If successful writes info to memory cache in proper order since it's sync.
        Unless it manages to get previously unretrieved values, of course.
        """
        for fails_con in range(self.max_fails_con):
            try:
                reqt = session.get(link, timeout=self.timeout_time)
                content = reqt.content
                parser = bs4.BeautifulSoup(content, 'html.parser')
                name, status, ingame = self.parse_name_status_ingame(parser)
                # self._names_flags_map[name] = self.get_flags_by_link(link)
                if self.is_ingame(link, status, ingame):
                    notify_ingame(name, ingame)
                self.cache_info(link, self.get_flags_by_link(link), name, status, ingame)
                break
            except (AttributeError, requests.exceptions.ConnectionError) as e:  # page didn't load or connection aborted
                if not self.is_silent:
                    print(link, f'[{e}] {fails_con+1} of {self.max_fails_con}')
        else:  # Executes when consecutive errors exceed maximum
            return link, *self.get_current_link_status_from_cache(link)  # might be None
        return link, name, status, ingame


class AsyncNameParser(AbstractNameParser):
    def parse_links_info(self):
        """
        Runs main in an event loop and provides a synchronous interface for name parsing.
        Returns a set of parsed names and links info map.
        """
        return asyncio.run(self.main())

    async def main(self) -> CacheableData:
        """
        Schedules link parsing tasks and returns a set of parsed names.
        Saves cached links info in proper order.
        """
        tasks, links, names = [], set(), set()
        async with aiohttp.ClientSession(conn_timeout=self.timeout_time, read_timeout=self.timeout_time) as session:
            for link in self._links_flags_map:
                tasks.append(asyncio.create_task(self.parse_link_for_current_info(link, session)))
            for result in asyncio.as_completed(tasks):
                result = await result       # type: ignore
                if None not in result:
                    links.add(result[0])    # type: ignore
                    names.add(result[1])    # type: ignore
        self.names = names
        self.reorder_links_info_map([key for key in self.get_all_links() if key in links])
        self.save_cache()
        return self.links_info_map

    async def parse_link_for_current_info(self, link: str, session: aiohttp.ClientSession) -> tuple[Optional[str], ...]:
        """
        Parses link to get current Steam account name, status and game the player is currently in.
        Uses caching.
        """
        for fails_con in range(self.max_fails_con):
            try:
                async with session.get(link) as reqt:
                    content = await reqt.content.read()
                    parser = bs4.BeautifulSoup(content, 'html.parser')
                    name, status, ingame = self.parse_name_status_ingame(parser)
                    if self.is_ingame(link, status, ingame):
                        notify_ingame(name, ingame)
                    self.cache_info(link, self.get_flags_by_link(link), name, status, ingame)
                    break
            except (AttributeError, ConnectionError, aiohttp.ClientConnectorError, aiohttp.ServerDisconnectedError,
                    asyncio.exceptions.TimeoutError) as e:  # page didn't load or connection aborted
                if not self.is_silent:
                    print(link, f'[{e}] {fails_con+1} of {self.max_fails_con}')
        else:  # Executes when consecutive errors exceed maximum
            return link, *self.get_current_link_status_from_cache(link)  # might be None
        return link, name, status, ingame


# TESTING/BENCHMARKING

TEST_TEXT_NAMES_PATH = NAMES_PATH + 'cache_test.txt'
TEST_PICKLE_NAMES_PATH = NAMES_PATH + 'cache_pickle_test.bin'
TEST_HJSON_NAMES_PATH = NAMES_PATH + 'cache_test.hjson'


def block_socket(*args, **kwargs):
    """
    Function for removing reference from socket.socket.
    """
    raise requests.exceptions.ConnectionError("DENIED")


def toggle_internet(socket_module):
    """
    Generator for switching Internet access from code on and off.
    """
    unblock_socket = socket_module.socket   # saving reference for socket.socket
    while True:
        socket_module.socket = block_socket
        yield  # BLOCKED
        socket_module.socket = unblock_socket
        yield  # UNBLOCKED


def name_parser_benchmark(name_parser: NameParser):
    """
    Benchmarks name parser without cache.
    """
    name_parser.reset_cache()
    start_time = perf_counter()
    name_parser.parse_links_info()  # dict with server_names as keys and adrs as values {server_name: adr}
    finish_time = perf_counter()
    return f'{type(name_parser).__name__} finished parsing in: {finish_time - start_time:.3}.'


def name_parser_cache_benchmark(name_parser: NameParser):
    """
    Benchmarks name parser's cache.
    If the test subject didn't parse at current runtime beforehand (no in-memory cache), benchmarks the external cache.
    If both external and internal cache are empty, it will benchmark empty cache because no Internet connection.
    """

    internet_switcher = toggle_internet(socket)
    next(internet_switcher)     # blocking name parser's Internet requests
    start_time = perf_counter()
    name_parser.parse_links_info()
    finish_time = perf_counter()
    next(internet_switcher)     # unblocking them
    return f'{type(name_parser).__name__} Caching took: {finish_time - start_time:.3}'


def benchmark_sync_and_async_name_parsers_procedure():
    CONSOLE.print('[START SYNC/ASYNC NAME PARSERS BENCHMARK PROCEDURE]')
    pickle_cache_manager = PickleCacheableData(TEST_PICKLE_NAMES_PATH)
    text_cache_manager = TextFileCacheableData(TEST_TEXT_NAMES_PATH)
    async_name_parser = AsyncNameParser(links_info_map=pickle_cache_manager)
    sync_name_parser = SyncNameParser(links_info_map=text_cache_manager)
    to_benchmark = [async_name_parser, sync_name_parser]
    # CONSOLE.print(*map(name_parser_benchmark, to_benchmark), sep='\n')
    with concurrent.futures.ProcessPoolExecutor() as executor:
        CONSOLE.print(*executor.map(name_parser_benchmark, to_benchmark), sep='\n')
    CONSOLE.print('[END SYNC/ASYNC NAME PARSERS BENCHMARK PROCEDURE]\n')


def benchmark_name_parsers_common_cache_procedure():
    CONSOLE.print('[START NAME PARSERS COMMON CACHE BENCHMARK PROCEDURE]')
    common_cacheable_data = TextFileCacheableData(TEST_TEXT_NAMES_PATH)
    # common_cacheable_data = PickleCacheableData(TEST_PICKLE_NAMES_PATH)
    async_name_parser = AsyncNameParser(links_info_map=common_cacheable_data)
    sync_name_parser = SyncNameParser(links_info_map=common_cacheable_data, is_silent=True)  # Will log a lot of fails.
    to_benchmark = [async_name_parser, sync_name_parser]
    # CONSOLE.print(*map(name_parser_benchmark, to_benchmark), sep='\n')
    with concurrent.futures.ProcessPoolExecutor() as executor:
        # CONSOLE.print(*executor.map(name_parser_benchmark, to_benchmark), sep='\n')
        CONSOLE.print(executor.submit(name_parser_benchmark, to_benchmark[0]).result())
        CONSOLE.print(executor.submit(name_parser_cache_benchmark, to_benchmark[1]).result())
        # next(internet_switcher)  # unblocking the internet
    # CONSOLE.print(common_cacheable_data)
    CONSOLE.print('[END NAME PARSERS COMMON CACHE BENCHMARK PROCEDURE]')


def name_parser_name_table_test(name_parser: NameParser):
    links_info_map = name_parser.parse_links_info()
    # links_info_map = name_parser.links_info_map
    name_table = get_name_table_scaffold()
    for link, link_info in links_info_map.items():
        if link_info:
            name, status, ingame = link_info['current_status']
            name_table.add_row(
                remove_diacritics(name),
                f"{status} {ingame if ingame != 'None' else ''}",
                f"{links_info_map[link]['flags']}")  # building the Name Table
    CONSOLE.print(name_table)


def test_name_table_procedure():
    CONSOLE.print('[START NAME TABLE TEST PROCEDURE]')
    name_parser = AsyncNameParser()
    name_parser_name_table_test(name_parser)
    CONSOLE.print('[END NAME TABLE TEST PROCEDURE]')


if __name__ == '__main__':
    # benchmark_sync_and_async_name_parsers_procedure()
    benchmark_name_parsers_common_cache_procedure()
    test_name_table_procedure()
