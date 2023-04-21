"""
This is a module that parses player names on every available server of A2S protocol,
notifies when finds a match of a player name to a Steam account name with logging (not the logging module) support.
One day of runtime will log gigabytes on storage if you aren't careful so clean it regularly or remove CONSOLE.save_html lines.

Async might be too fast and with enough amount of servers will quickly use all of your traffic.
This is why you need to have REQUEST_COOLDOWN.

Also I didn't separate printing to console so the sync version has advantage of printing tables after the data was parsed
and it's buffer won't be overflown no matter the amount of servers.
"""

from typing import Any, Literal, Optional, OrderedDict, Protocol
from abc import ABC, abstractmethod
import asyncio
from math import isnan
import a2s

from time import sleep, asctime

from rich.traceback import install
from rich.table import Table
from rich.markup import MarkupError

from helpers import CONFIG, CONSOLE, addr_to_ip, remove_diacritics
from notifications import notify_onserver

install()


MAX_FAILS_CON = CONFIG['SERVER_PARSERS']['MAX_FAILS_CON']   # max consecutive timeouts
TIMEOUT_TIME = CONFIG['SERVER_PARSERS']['TIMEOUT_TIME']     # in seconds
# note that for async server parser it's a max for initial network ops
# Absoulute max is theoretically 2 times bigger since sleep from main is async
# and the sleeping coro can unblock and send red retry request with low enough MAX_REQUESTS_PER_SECOND value (50 ex.)
MAX_REQUESTS_PER_SECOND = CONFIG['SERVER_PARSERS']['MAX_REQUESTS_PER_SECOND']
ASYNC_REQUEST_COOLDOWN = 1/MAX_REQUESTS_PER_SECOND    # in seconds


def get_players_table_scaffold(title):
    players_table = Table(title=title)
    players_table.add_column('Name', style='green')
    players_table.add_column('Score', style='cyan1')
    players_table.add_column('Playtime', style='red')
    players_table.add_column('KPM (if playtime contributed to only one round)', style='magenta')
    return players_table


class ServerParser(Protocol):
    names: set[str]
    servers: dict[str, tuple[str, int]]
    server_names: list[str]
    names_info_map: dict[str, OrderedDict[str, bool]]
    names_on_all_servers: dict[str, list[Any]]
    excluded_servers_names_map: dict[str, set[str]]
    timeout_time: int
    max_fails_con: int

    @staticmethod
    def parse_player(player: a2s.Player) -> tuple[str, int, float, str]:
        ...

    def check_if_player_in_names(self, player_name) -> Optional[str]:
        ...

    def handle_player(self, names_on_server: set[str], server_name: str, addr: tuple[str, int], **kwargs):
        ...

    def parse_servers(self):
        ...


class AbstractServerParser(ABC):
    names: set[str]
    servers: dict[str, tuple[str, int]]                 # Map of server names to their addrs
    server_names: list[str]
    names_info_map: dict[str, OrderedDict[str, bool]]   # Map of names to their flag maps
    names_on_all_servers: dict[str, list[Any]]          # Server name: list containing server addr and names on the server
    excluded_servers_names_map: dict[str, set[str]]     # Map of server addresses to names excluded
    timeout_time: int                                   # Maximum time for one A2S response
    max_fails_con: int                                  # Maximum amount of consecutive A2S requests' fails

    @staticmethod
    def parse_player(player: a2s.Player) -> tuple[str, int, float, str]:
        """
        Parses retrieved content from a Player data class object for:
        player name, player score, player playtime in seconds, formatted string of playtime.
        """
        player_name = player.name if player.name else ''    # single line ifs for validation
        player_score = player.score if player.score else 0
        player_duration = player.duration if not isnan(player.duration) and player.duration != 0 else 1  # not 0 cuz program divides by duration later
        hours = int(player_duration // 3600)
        minutes = int(player_duration // 60 % 60)
        seconds = int(player_duration % 60)
        playtime = f'{hours:2} H, {minutes:2} M, {seconds:2} S'
        return player_name, player_score, player_duration, playtime

    def __init__(
            self, names=set(), servers=dict(), server_names=[], names_info_map=dict(),
            timeout_time=TIMEOUT_TIME, max_fails_con=MAX_FAILS_CON):
        self.names = names
        self.servers = servers
        self.server_names = server_names
        self.names_info_map = names_info_map
        self.names_on_all_servers = dict()
        self.excluded_servers_names_map = {'__all__': set()}
        self.timeout_time = timeout_time
        self.max_fails_con = max_fails_con

    def check_if_player_in_names(self, player_name) -> Optional[str]:
        """
        If player_name is in names return name else None.
        Note that it does not return player_name which may be different from name.
        """
        for name in self.names:
            if player_name.endswith(name):  # have to do it like this cuz of name prefixes sometimes
                return name
        return None

    def handle_player(self, names_on_server: set[str], server_name: str, addr: tuple[str, int], **kwargs):
        """
        Adds player name to names_on_server and self.names_on_all_servers if it's in names.

        Using kwargs here because there's too much parameters.
        kwargs: [player_name: str], [server_name: str], [playtime: str]
        """
        playtime, player_name, player_score = kwargs['playtime'], kwargs['player_name'], kwargs['player_score']
        name = self.check_if_player_in_names(player_name)
        if name:
            self.names_on_all_servers[server_name] = self.names_on_all_servers.get(server_name, [addr_to_ip(addr)]) + [
                f'{player_name}, {player_score}, {playtime.strip()}']
            if self.names_info_map[name]['on_server']:
                names_on_server.add(player_name)

    @abstractmethod
    def parse_servers(self):
        """
        Parses gameservers implementing A2S protocol, prints players tables to console and notifies when name in names is found.
        Returns matched names on all servers.
        """


class SyncServerParser(AbstractServerParser):
    def parse_server(self, server_name, fails_con) -> Optional[int]:
        addr = self.servers[server_name]
        try:
            players = sorted(a2s.players(addr), key=lambda d: d.score, reverse=True)
        except (TimeoutError, OSError) as e:
            CONSOLE.print(server_name, f'[{repr(type(e))[8:-2].upper()}:FAIL] {fails_con+1} of {self.max_fails_con}', style='red bold')
            return -1
        if not players:
            return None
        players.sort(key=lambda d: d.score, reverse=True)
        players_table = get_players_table_scaffold(server_name)
        names_on_server = set()     # type: ignore # all names on one server
        for player in players:
            player_name, player_score, player_duration, playtime = self.parse_player(player)
            players_table.add_row(remove_diacritics(player_name), str(player_score), playtime, f'{player_score*60/player_duration:.2f}')
            self.handle_player(names_on_server, server_name, addr,
                               playtime=playtime, player_name=player_name, player_score=player_score)
        try:
            CONSOLE.print(players_table, end='\n\n')
        except MarkupError:         # names with forward slashes may cause this error
            CONSOLE.print('\t\t\t\tBAD NAME ON SERVER', style="red on white")
        if names_on_server:
            try:
                CONSOLE.print(names_on_server)
            except MarkupError:     # names with forward slashes may cause this error
                CONSOLE.print('\t\t\t\tBAD NAME ON SERVER', style="red on white")
            notify_onserver(self.excluded_servers_names_map, names_on_server, server_name, addr)
        return None

    def parse_servers(self) -> dict[str, list]:
        for i in range(0, len(self.server_names)):
            for fails_con in range(self.max_fails_con):
                server_name = self.server_names[i]
                CONSOLE.print(f'{asctime()} {server_name}')
                if self.parse_server(server_name, fails_con) != -1:
                    break
        return self.names_on_all_servers


class AsyncServerParser(AbstractServerParser):
    request_cooldown: float                             # Time to sleep for after each request

    def __init__(self, names=set(), servers=dict(), server_names=[], names_info_map=dict(), timeout_time=TIMEOUT_TIME, max_fails_con=MAX_FAILS_CON, request_cooldown=ASYNC_REQUEST_COOLDOWN):
        super().__init__(names, servers, server_names, names_info_map, timeout_time, max_fails_con)
        self.request_cooldown = request_cooldown

    def parse_servers(self) -> dict[str, list]:
        self.names_on_all_servers = dict()
        return asyncio.run(self.main())

    async def parse_server(self, server_name, fails_con=0) -> Optional[Table] | Literal[-1]:
        addr = self.servers[server_name]
        players = []
        try:    # could have just written this [{repr(type(e))[8:-2].upper()}:FAIL]
            players = await a2s.aplayers(addr, timeout=self.timeout_time)
        except (asyncio.TimeoutError, OSError, a2s.BufferExhaustedError, a2s.BrokenMessageError) as e:
            CONSOLE.print(server_name, f'[{repr(type(e))[8:-2].split(".")[-1].upper()}:FAIL] {fails_con} of {self.max_fails_con}', style='red bold')
            return -1
        if not players:
            return None
        players.sort(key=lambda d: d.score, reverse=True)
        players_table = get_players_table_scaffold(server_name)
        names_on_server = set()     # type: ignore # all names on one server
        for player in players:
            player_name, player_score, player_duration, playtime = self.parse_player(player)
            players_table.add_row(remove_diacritics(player_name), str(player_score), playtime, f'{player_score*60/player_duration:.2f}')
            self.handle_player(names_on_server, server_name, addr,
                               playtime=playtime, player_name=player_name, player_score=player_score, player_duration=player_duration)
        # console.print(players_table)
        if names_on_server:
            try:
                CONSOLE.print(server_name, addr, names_on_server)
            except MarkupError:
                CONSOLE.print('BAD SERVER NAME OR NAMES ON SERVER', addr)
            notify_onserver(self.excluded_servers_names_map, names_on_server, server_name, addr)
        return players_table

    async def get_players_table(self, server_name) -> Optional[Table] | Literal[-1]:
        for fails_con in range(1, self.max_fails_con+1):
            players_table = await self.parse_server(server_name, fails_con)
            if players_table != -1:
                return players_table
            sleep(self.request_cooldown)    # affects all subsequent requests
        return None

    async def main(self) -> dict[str, list]:
        tasks = []
        # names_on_all_servers = dict()   # noqa: F841      <- this blocks flake8 linting error
        CONSOLE.print(f'{asctime()} {__name__} {__package__}')
        for i in range(len(self.server_names)):
            server_name = self.server_names[i]
            CONSOLE.print(f'{asctime()} {server_name}')
            tasks.append(asyncio.create_task(self.get_players_table(server_name)))
            await asyncio.sleep(self.request_cooldown)  # forces coro switch which might request while awaiting cooldown
            # sleep(self.request_cooldown)
        players_tables = [pt for pt in await asyncio.gather(*tasks) if pt]
        for players_table in sorted(players_tables, key=lambda x: len(x.rows), reverse=False):
            try:
                CONSOLE.print(players_table)
            except MarkupError:     # names with forward slashes may cause this error
                CONSOLE.print('\t\t\t\tBAD NAME ON SERVER', style="red on white")
        return self.names_on_all_servers


if __name__ == '__main__':  # this is easier to test in main.py
    """"""
    # server_parser = AsyncServerParser()
