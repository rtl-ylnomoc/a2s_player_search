"""
This is a module that retrieves server names by their ips and also can dumps them in binary form.
Asynchronous version
"""

from abc import ABC, abstractmethod
from typing import Any, Protocol
import a2s
import asyncio
# import aiofiles   # aiofiles doesn't give any significant performance advantage in this case so I put fileops in abstract class
import concurrent.futures
from time import perf_counter
from cache.cacheable_data import PickleCacheableData
from cache.cache_managers import ServerNameParserCacheManager
from helpers import CONFIG, CONSOLE, SERVER_IPS_PATH, ip_to_addr, create_file_if_file_does_not_exist, validate_address
from master_server_querier import MasterServerQuery


# max consecutive fails for one server. If zero only sync would work and will also behave like it's equal to one.
MAX_FAILS_CON = CONFIG['SERVER_NAME_PARSERS']['MAX_FAILS_CON']
INFO_TIMEOUT_TIME = CONFIG['SERVER_NAME_PARSERS']['INFO_TIMEOUT_TIME']   # a2s.ainfo timeout time

TEXT_SERVERS_NAMES_PATH = SERVER_IPS_PATH[:-4:] + '_cache_prod.txt'
PICKLE_SERVER_NAMES_PATH = SERVER_IPS_PATH[:-4:] + '_cache_prod.bin'
HJSON_SERVER_NAMES_PATH = SERVER_IPS_PATH[:-4:] + '_cache_prod.hjson'


class ServerNameParser(Protocol):
    max_fails_con: int
    timeout_time: float
    _ip_ports: list[str]
    _extras: list[Any]

    def load_ips_with_extras_from_file(self, path: str):
        ...

    def load_ips_from_set(self, ips_ports: set[str]):
        ...

    def get_servers_dict(self) -> dict[str, tuple[str, int]]:
        ...

    def reset(self) -> None:
        ...


class AbstractServerNameParser(ABC, ServerNameParserCacheManager):
    max_fails_con: int
    timeout_time: float
    _ip_ports: list[str]
    _extras: list[Any]

    def __init__(self, max_fails_con=MAX_FAILS_CON, timeout_time=INFO_TIMEOUT_TIME, servers_info_map=PickleCacheableData(PICKLE_SERVER_NAMES_PATH)):
        self.max_fails_con = max_fails_con
        self.timeout_time = timeout_time
        self._ip_ports = []
        self._extras = []
        super().__init__(servers_info_map)

    def load_ips_with_extras_from_file(self, path=SERVER_IPS_PATH):
        create_file_if_file_does_not_exist(path)
        with open(path, 'r') as fr:
            for line in fr:
                ip_port, *extra = line.split()
                if ip_port in self._ip_ports:
                    continue
                self._ip_ports.append(ip_port)
                self._extras.append(extra)

    def load_ips_from_set(self, ips_ports: set[str]):
        for ip_port in ips_ports:
            if ip_port in self._ip_ports:
                continue
            self._ip_ports.append(ip_port)
            self._extras.append('[IMPORTED FROM SET]')

    @abstractmethod
    def get_servers_dict(self) -> dict[str, tuple[str, int]]:
        ...

    @abstractmethod
    def reset(self) -> None:
        ...


class SyncServerNameParser(AbstractServerNameParser):
    # def load_ips_with_extras_from_file(self, path=SERVER_IPS_PATH):
    #     with open(path, 'r') as fr:
    #         for line in fr:
    #             ip, *extra = line.split()
    #             self._ips.append(ip)
    #             self._extras.append(extra)

    # def load_ips_from_set(self, ips: set[str]):
    #     for ip in ips:
    #         self._ips.append(ip)
    #         self._extras.append('[IMPORTED FROM SET]')

    def get_servers_dict(self):
        self.load_ips_with_extras_from_file()
        self.load_ips_from_set(MasterServerQuery().request_for_ip_ports())
        fails_con = 0   # current amount of consecutive timeouts
        start_i = 0
        while True:

            for i in range(start_i, len(self._ip_ports)):
                ip_port = self._ip_ports[i]
                extra = self._extras[i]
                if not validate_address(ip_port):
                    fails_con = self.max_fails_con
                    break
                addr = ip_to_addr(ip_port)
                try:
                    info = a2s.info(addr, timeout=self.timeout_time)
                    server_name = str(info.server_name)
                    fails_con = 0
                    CONSOLE.print(f"[SYNC] {server_name} {ip_port}\n{info}\n")
                    self.servers_info_map[server_name] = addr
                except (TimeoutError, ConnectionResetError, OSError) as e:
                    fails_con += 1
                    CONSOLE.print(f'[SYNC FAIL] {ip_port} {extra} [{e}] {fails_con} of {self.max_fails_con}\n')
                    if addr in self.servers_info_map.values():
                        CONSOLE.print(f'[GRABBED FROM CACHE] {addr}')
                        break
                    start_i = i
                    break

            else:   # case when exited for loop without break i.e. without raising an exception
                break

            if fails_con >= self.max_fails_con:
                start_i += 1
                fails_con = 0
                continue
        self.save_cache()
        return self.servers_info_map

    def reset(self):
        self._ip_ports = []
        self._extras = []
        self.reset_cache()


class AsyncServerNameParser(AbstractServerNameParser):
    def __init__(self, max_fails_con=MAX_FAILS_CON, timeout_time=INFO_TIMEOUT_TIME, servers_info_map=PickleCacheableData(PICKLE_SERVER_NAMES_PATH)):
        super().__init__(max_fails_con=max_fails_con, timeout_time=timeout_time, servers_info_map=servers_info_map)
        self._tasks = []

    async def load_tasks_from_ips_extras(self):
        """
        P.S. Implementation differs for the sake of efficiency.
        It's best performing when you create tasks as soon as possible.
        """
        # ips, extras, tasks = [], [], []
        for ip_port, extra in zip(self._ip_ports, self._extras):                                                        # type: ignore
            self._tasks.append(asyncio.create_task(self.get_server_name_task(ip_port, extra)))

    async def get_server_name_task(self, ip_port, extra):
        if not validate_address(ip_port):
            return None, f'INVALID {ip_port}'
        addr = ip_to_addr(ip_port)
        server_name = None
        for fails_con in range(1, self.max_fails_con+1):
            try:
                info = await a2s.ainfo(addr, timeout=self.timeout_time)
                server_name = str(info.server_name)                                                                                                  # type: ignore
                CONSOLE.print(f"[ASYNC] {server_name} {ip_port}\n{info}\n")
                break
            except (asyncio.exceptions.TimeoutError, ConnectionResetError, OSError) as e:
                CONSOLE.print(f"[ASYNC FAIL]\t{ip_port}\t{extra} [{e}] {fails_con} of {self.max_fails_con}\n")
                if addr in self.servers_info_map.values():
                    CONSOLE.print(f'[GRABBED FROM CACHE]\t{addr}\n')
                    break   # if there was a server name in cache doesn't bother try more. Remove break to try anyway.
        return server_name, addr

    async def run(self):
        self.load_ips_with_extras_from_file()
        self.load_ips_from_set(MasterServerQuery().request_for_ip_ports())
        await self.load_tasks_from_ips_extras()
        # await self.load_tasks_from_set(MasterServerQuery().request_for_ips())
        results = await asyncio.gather(*self._tasks)     # [(server_name, adr), ...]
        # self._extras = []
        self._tasks = []
        for server_name, addr in results:
            if server_name:
                self.servers_info_map[server_name] = addr
        self.remove_duplicates()
        self.save_cache()
        return self.servers_info_map

    def reset(self):
        # self._extras = []
        self._tasks = []
        self.reset_cache()

    def get_servers_dict(self):
        return asyncio.run(self.run())


def msn_benchmark(msn: ServerNameParser):
    msn.reset()
    start_time = perf_counter()
    servers_dict = msn.get_servers_dict()  # dict with server_names as keys and adrs as values {server_name: adr}
    # servers_dict = msn.get_servers_dict()  # check caching
    # pickle_data(servers_dict, SERVERS_BINARY_PATH)
    elapsed_time = perf_counter() - start_time
    CONSOLE.print(servers_dict)
    return f'{type(msn).__name__} finished in: {elapsed_time:3}\n'


if __name__ == '__main__':
    smsn = SyncServerNameParser()
    amsn = AsyncServerNameParser()
    msns_to_benchmark = [amsn, ]
    with concurrent.futures.ProcessPoolExecutor() as executor:
        CONSOLE.print(*executor.map(msn_benchmark, msns_to_benchmark), sep='')
