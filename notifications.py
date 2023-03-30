"""
This is a module with predefined notifications invoker functions.
"""

from winotify import Notification

from sys import path
from os.path import join

from helpers import APP_ID, BASE_DIR, addr_to_ip, remove_unprintable


def notify_ingame(name: str, ingame: str):
    Notification(app_id=ingame,
                 title=remove_unprintable(name),
                 duration='short',
                 icon=join(path[0], join(BASE_DIR, r'noticons\games.png'))).show()    # not using NOTIFIER to categorize notifications by app_id


def notify_exception(exception: Exception, title: str = 'Exception'):
    Notification(
        app_id=APP_ID,
        title=title,
        msg=exception,
        duration='long',
        icon=join(path[0], join(BASE_DIR, r'noticons\error.png'))).show()


def notify_onserver(
        excluded_servers_names_map: dict[str, set[str]],
        names_on_server: set[str], server_name: str, addr: tuple[str, int],):
    """
    Notifies about names present on the server.
    Exclusions disable notifications for their corresponding areas:
        __all__      name       ,   <-  to exclude a set of names for every server;
        1.1.1.1:1    name       ,   <-  to exclude a set of names for a specific server by its ip:port;
        1.1.1.1:1    __all__    ,   <-  to exclude a specific server by its ip:port for all names.
    """
    address = addr_to_ip(addr)
    if '__all__' in excluded_servers_names_map.get(address, set()):
        print(f'SERVER IS EXCLUDED  {excluded_servers_names_map}')
        return
    excluded_names = set()  # not removing from names_on_server directly for safe iterations.
    for name_on_server in names_on_server:
        if name_on_server in excluded_servers_names_map.get(address, set()) | excluded_servers_names_map['__all__']:
            excluded_names.add(name_on_server)
            print(f'REMOVED NAME    {name_on_server}')
    names_on_server -= excluded_names
    if not names_on_server:   # check if empty
        print(f'ALL NAMES REMOVED   {excluded_servers_names_map}')
        return
    Notification(
        app_id=APP_ID,
        title=', '.join(remove_unprintable(s) for s in names_on_server),
        msg=remove_unprintable(server_name),
        duration='short',
        icon=join(path[0], join(BASE_DIR, r'noticons\loupe.png'))).show()
