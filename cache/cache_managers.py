"""
This is a module that contains cache manager classes.

These classes exist mainly to extract the code relating to caching of child classes
since they are already way too big.
"""

from typing import Iterable, Optional

from .abstract_cacheable_data import CacheableData

from helpers import NAMES_PATH, SERVER_IPS_PATH


HJSON_BASE_NAMES_PATH = NAMES_PATH + '_cache_based.hjson'
TEXT_BASE_NAMES_PATH = NAMES_PATH + '_cache_based.txt'
PICKLE_BASE_NAMES_PATH = NAMES_PATH + '_cache_based.bin'
HJSON_BASE_SERVER_IPS_PATH = SERVER_IPS_PATH + '_cache_based.hjson'
TEXT_BASE_SERVER_IPS_PATH = SERVER_IPS_PATH + '_cache_based.txt'
PICKLE_BASE_SERVER_IPS_PATH = SERVER_IPS_PATH + '_cache_based.bin'


class NameParserCacheManager:
    _links_info_map: CacheableData  # Cacheable name info map of links to name info

    @property
    def links_info_map(self) -> CacheableData:
        return self._links_info_map

    def __init__(self, links_info_map):
        self._links_info_map = links_info_map

    def remove_extra_links_from_cache(self, links_keys):
        """
        Removes all links from cache which are not in the links_keys.
        """
        extra_links = self._links_info_map.keys() - links_keys
        # print(links_keys)
        # print(extra_links)
        for link in extra_links:
            print(f'DELETING INTERNALLY {link}')
            del self._links_info_map[link]
        # for link in self._links_info_map:
        #     if link not in links_keys:
        #         del self._links_info_map[link]

    def get_current_link_status_from_cache(self, link: str) -> list[Optional[str]]:
        """
        Gets link's current status from cache.
        """
        # link_info = self._links_info_map.get(link)
        # return link_info['current_status'] if link_info else [None]

        link_info_map = self._links_info_map.get(link)
        link_current_status = [None]
        if link_info_map:
            link_current_status = link_info_map['current_status'] if link_info_map['current_status'] else [None]
            link_current_status = link_current_status if link_current_status else [None]
            print(link, '[LINK FOUND IN CACHE]', link_current_status)
        else:
            print(link, '[LINK NOT FOUND IN CACHE]')
        return link_current_status      # type: ignore

    def cache_info(self, link: str, flags: dict[str, bool], *current_status: str):
        link_info = {}
        link_info['current_status'] = current_status
        link_info['flags'] = flags  # type: ignore
        self._links_info_map.set(link, link_info)

    def reorder_links_info_map(self, keys: Iterable):
        self._links_info_map.reorder_by(keys)

    def save_cache(self):
        """
        Dumps all cached name info in external cache.
        """
        self._links_info_map.update_external_cache()

    def reset_cache(self):
        """
        Forces cache to reset by replacing it from external cache.
        """
        self._links_info_map.update_internal_cache()


class ServerNameParserCacheManager:
    _servers_info_map: CacheableData  # Cacheable name info map of links to name info

    @property
    def servers_info_map(self) -> CacheableData:
        return self._servers_info_map

    def __init__(self, servers_info_map):
        self._servers_info_map = servers_info_map
        self.remove_duplicates()

    def remove_duplicates(self):
        """
        Remove server names with same ips.
        It's needed because sometimes server names change but the cache remains
        In the end we would have two dict entries with the same address tuple which point to the same server.
        """
        seen_ips = set()
        for key in list(self._servers_info_map.keys())[:]:   # have to call .keys() because we mutate the dict
            if self._servers_info_map[key] in seen_ips:
                del self._servers_info_map[key]
            else:
                seen_ips.add(self._servers_info_map[key])

    def save_cache(self):
        """
        Dumps all cached server name info in external cache.
        """
        self._servers_info_map.update_external_cache()

    def reset_cache(self):
        """
        Forces cache to reset by replacing it from external cache.
        """
        self._servers_info_map.update_internal_cache()
