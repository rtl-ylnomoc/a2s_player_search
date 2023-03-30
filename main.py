"""
This is a module with logic that scaffolds all of the app's functionality.

Also provides logging (upd. p.s.) and runtime exclusion commands support.

P.S. Logging is commented out due to storage bloating (gigabytes of logging files per few hours of parsing)
"""

from threading import Thread
from winotify import Notification   # type: ignore

from sys import path
from os import system
from os.path import join
from time import sleep, perf_counter

from rich.traceback import install
from cache.cacheable_data import PickleCacheableData

from name_parsers import AsyncNameParser, get_name_table_scaffold
from helpers import CONFIG, CONSOLE, APP_ID, BASE_DIR, remove_diacritics
from server_name_parsers import AsyncServerNameParser
from server_parsers import AsyncServerParser, ServerParser
install()


HARDCODED_NAMES = set(CONFIG['MAIN']['HARDCODED_NAMES'])  # Use this in case you don't have a reliable Steam account link.
MINIMUM_CYCLE_PERIOD = CONFIG['MAIN']['MINIMUM_CYCLE_PERIOD']   # in secs
MINIMUM_SLEEP_TIME = CONFIG['MAIN']['MINIMUM_SLEEP_TIME']
# CYCLES_PER_LOG = CONFIG['MAIN']['CYCLES_PER_LOG']


def parse_command(server_parser: ServerParser, string: str):
    global CONSOLE
    first_space_index = string.find(' ')
    exclude_address = string[:first_space_index:]
    if not (exclude_address == '__all__' or validate_address(exclude_address)):
        CONSOLE.print(f'ADDRESS IS INVALID {exclude_address}', style='bold red')
        return
    name = string[first_space_index+1::]
    if name == '':
        raise ValueError
    if exclude_address == '__all__':
        print(f'EXCLUDED NAME {name}')
    else:
        if name == '__all__':
            print(f'EXCLUDED SERVER {exclude_address}')
        else:
            print(f'EXCLUDED NAME {name} ON SERVER {exclude_address}')

    server_parser.excluded_servers_names_map[exclude_address] = server_parser.excluded_servers_names_map.get(exclude_address, set()) | {name}


def process_input_commands(server_parser):
    while True:
        command = input().strip()
        try:
            parse_command(server_parser, command)
        except ValueError:
            CONSOLE.print(f'INPUT IS INVALID {command}', style='bold red')
        except IndexError:
            CONSOLE.print('EMPTY INPUT', style='bold red')
        except (EOFError, KeyboardInterrupt):
            CONSOLE.print('SHUTTING DOWN INPUT THREAD')
            exit()


def inject_names(names, names_info_map, names_to_inject: set[str]):
    """
    Inject names to parse servers for without the need to know their Steam account links.
    Note that it assigns corresponding name flags names_info_map['on_server'] to True

    Use in context after names and names_info_map are initialized.
    """
    flags = {'on_server': True}
    names |= names_to_inject
    for name in names_to_inject:
        names_info_map[name] = flags


def validate_address(string: str):
    """
    Primitive ip:port validation function
    """
    return '__all__' or all(char in '01234567890.:' for char in string) and string.count('.') == 3 and string.count(':') == 1


def main(server_name_parser, server_parser, name_parser):
    # Path('logs').mkdir(parents=True, exist_ok=True)
    start_sn_time = perf_counter()
    server_name_parser = server_name_parser
    servers = server_name_parser.get_servers_dict()   # had to made async cuz sync is too slow when there's a lot of servers
    server_names = list(servers.keys())
    end_sn_time = perf_counter()
    CONSOLE.print(f'\nSERVER NAMES finished in: {end_sn_time - start_sn_time}')
    server_parser = server_parser
    server_parser.servers = servers
    server_parser.server_names = server_names
    name_parser = name_parser
    cycled = 0
    names = {}
    input_thread = Thread(target=process_input_commands, args=(server_parser,), daemon=True)
    input_thread.start()
    while True:
        try:
            system('CLS')
            CONSOLE.clear_live()
            CONSOLE.print(f'HARDCODED NAMES: {HARDCODED_NAMES}\n')
            start_iter_time = perf_counter()
            links_info_map = name_parser.parse_links_info()
            names = name_parser.names
            names_info_map = {}     # {'name': dict(flags)}
            inject_names(names, names_info_map, HARDCODED_NAMES)
            name_table = get_name_table_scaffold()
            for link, link_info in links_info_map.items():
                if link_info:
                    name, status, ingame = link_info['current_status']
                    flags = links_info_map.get(link)['flags']
                    names_info_map[name] = flags
                    name_table.add_row(
                        remove_diacritics(name),
                        f"{status} {ingame if ingame != 'None' else ''}",
                        f"{flags}")  # building the Name Table
            CONSOLE.print(name_table)
            get_names_time = perf_counter()
            server_parser.names = names
            server_parser.names_info_map = names_info_map

            names_on_all_servers = server_parser.parse_servers()  # main procedure

            total_time = perf_counter()-start_iter_time  # getting names time is included in total
            names_time = get_names_time-start_iter_time

            sleep_for = int(MINIMUM_CYCLE_PERIOD-total_time) if total_time < MINIMUM_CYCLE_PERIOD - MINIMUM_SLEEP_TIME else MINIMUM_SLEEP_TIME
            # ^ this makes the program sleep for at least MINIMUM_SLEEP_TIME or for the time needed to make whole cycle run for each MINIMUM_CYCLE_PERIOD
            cycled += 1

            server_names_speed = 0  # safe measure against zero divisions just in case
            names_speed = 0
            if server_names:
                server_names_speed = len(server_names)/total_time
            if names:
                names_speed = len(names)/names_time

            for key, val in names_on_all_servers.items():
                CONSOLE.print(f'{key}\t{val}')
            CONSOLE.print(f'\nExcluded names on servers map: {server_parser.excluded_servers_names_map}\n')
            CONSOLE.print(f'Scanning number {cycled} took {int(total_time)} seconds ({server_names_speed} servers/second); \
    getting names: {int(names_time)} seconds ({names_speed} names/second).\nSleeping for {sleep_for} seconds\n')
            CONSOLE.print('''Write console exclusion commands while main thread is sleeping.\nExamples: \n\
    __all__ name        (to exclude name on all servers) \n\
    1.1.1.1:0 __all__   (to exclude server for all names) \n\
    1.1.1.1:0 name      (to exclude name on one server)\n''')
            sleep(sleep_for)
            # if not cycled % CYCLES_PER_LOG:     # True when remainder is 0
            # pass
            # CONSOLE.save_html(join(BASE_DIR, f'logs\\log-{cycled}-{time()}.html'))
            # CONSOLE.clear_live()
        except KeyboardInterrupt:   # handle stopping the program
            CONSOLE.print('SHUTTING DOWN MAIN THREAD')
            exit()
            # CONSOLE.save_html(join(BASE_DIR, f'logs\\KeyboardInterrupt-log-{cycled}-{time()}.html'))
        except ZeroDivisionError as e:
            Notification(app_id=APP_ID, title='Names list is likely empty', msg=e,
                         duration='long', icon=join(path[0], join(BASE_DIR, r'noticons\icon.png'))).show()
            CONSOLE.print_exception()
            # CONSOLE.save_html(join(BASE_DIR, f'logs\\ZeroDivisionError-log-{cycled}-{time()}.html'))
            CONSOLE.print(names)
            exit()
        except Exception as e:
            Notification(app_id=APP_ID, title='Exception occurred', msg=e,
                         duration='long', icon=join(path[0], join(BASE_DIR, r'noticons\icon.png'))).show()
            CONSOLE.print_exception()
            # CONSOLE.save_html(join(BASE_DIR, f"logs\\{remove_bad_chars(str(e)).title()}-log-{cycled}-{time()}.html"))
            sleep(1)    # sleep for 1 second to reduce notifications spamming
            continue


if __name__ == '__main__':
    main(AsyncServerNameParser(),
         AsyncServerParser(),
         AsyncNameParser(PickleCacheableData(join(BASE_DIR, 'data/async_names_cache.bin')), is_silent=True))
