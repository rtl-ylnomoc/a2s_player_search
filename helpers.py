"""
This is a module that contains helping functions that's shared by sync and async code plus some shared constants.
"""

from rich.console import Console
from os.path import join, dirname, realpath
from string import printable

import pickle
import hjson


def validate_address(string: str):
    """
    Primitive address validation function
    """
    return all(char in '01234567890.:' for char in string) and string.count('.') == 3 and string.count(':') == 1


def ip_to_addr(ip):
    sip = ip.split(":")
    return sip[0], int(sip[1])


def addr_to_ip(addr: tuple[str, int]):
    ip = ':'.join([addr[0], str(addr[1])])
    return ip


def pickle_data(data, path):
    with open(path, 'wb') as fw:
        pickle.dump(data, fw)


def remove_diacritics(string: str) -> str:
    """
    This is an attempt to prevent table breaking its own grid with some of unicode chars.
    Only works if those chars are diacritics for now
    P.S. spent about 6 hours for these 5 lines of code.
    """
    s = string
    for i in range(768, 880):
        h = chr(i)
        s = s.replace(h, '')
    return s


def remove_unprintable(string: str) -> str:
    """
    Removes unprintable values. Notification will not be shown if there are any.
    """
    return ''.join(c for c in string if c in set(printable))


def remove_bad_chars(string: str) -> str:
    """
    Removes illegal filename characters from the input string. 
    Unused now when logging is commented out.
    """
    return ''.join(char for char in string if char not in r'''#%&{}\<>*?/ $!'";@+`|=''')


def create_file_if_file_does_not_exist(path):
    """
    Creates file at path if it does not exist.
    """
    open(path, 'a').close()

with open('config.hjson') as f:
    CONFIG = hjson.load(f)
CONSOLE = Console(record=False)  # change to true for logs
APP_ID = 'Search for players'  # String by which notifications are going to be grouped
BASE_DIR = dirname(realpath(__file__))  # for paths based on absolute location of this file
NAMES_PATH = join(BASE_DIR, r'data\names')
CACHED_NAMES_PATH = NAMES_PATH[:-4:] + '_old.txt'
SERVER_IPS_PATH = join(BASE_DIR, r"data\server_ips.txt")
LINKS_FLAGS_MAP_PATH = join(BASE_DIR, r'links_options.hjson')
NOTIFICATIONS_PATH = join(BASE_DIR, 'notifications.py')
