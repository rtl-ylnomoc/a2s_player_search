"""
This is a module that implements Master Server Query Protocol
(see https://developer.valvesoftware.com/wiki/Master_Server_Query_Protocol)
and provides an API to use by ServerNameParsers.
"""

import socket
from helpers import CONFIG

REGION_CODES_MAP = {
    'US EAST': b'\x00',
    'US WEST': b'\x01',
    'SOUTH AMERICA': b'\x02',
    'EU': b'\x03',
    'ASIA': b'\x04',
    'OCEANIA': b'\x05',
    'MIDDLE EAST': b'\x06',
    'AFRICA': b'\x07',
    'ALL': b'\xff',
}


MAX_PACKETS_PER_REQUEST = CONFIG['MASTER_SERVER_QUERIER']['MAX_PACKETS_PER_REQUEST']
FILTER = CONFIG['MASTER_SERVER_QUERIER']['FILTER']
REGION = CONFIG['MASTER_SERVER_QUERIER']['REGION']
MASTER_SERVER_ADDR = tuple(CONFIG['MASTER_SERVER_QUERIER']['MASTER_SERVER_ADDR'])


def to_cstring(string: str) -> bytes:
    """
    Converts string to utf-8 cstring with null byte ending.
    """
    cstring = string.encode()
    cstring += b'\x00'
    return cstring


class MasterServerQuery:
    _ms_socket: socket.socket
    ip_ports: set[str]
    max_packets_per_request: int
    master_server_addr: tuple[str, int]
    filter: str
    header: bytes
    ip_ports_count: int

    def __init__(self, max_ips_per_request=MAX_PACKETS_PER_REQUEST, master_server_addr=MASTER_SERVER_ADDR, filter=FILTER, region='ALL'):
        self._ms_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP socket
        self.ip_ports = set()
        self.max_packets_per_request = max_ips_per_request
        self.master_server_addr = master_server_addr
        self.filter = to_cstring(filter)
        self.header = b'1' + REGION_CODES_MAP[region]
        self.ip_ports_count = 0

    def _parse_packet(self, packet) -> tuple[set[str], str]:
        """
        Parses a given packet byte string.
        Returns a set of parsed ips and the last ip.
        """
        header = packet[:6:]
        assert header == b'\xff\xff\xff\xff\x66\x0a'    # same as b'\xff\xff\xff\xfff\n' where f is 102(x66) and \n is 10(x0A)
        data = packet[6::]
        index_pointer = 0
        ip_ports = set()
        ip_port = ''
        for index_pointer in range(0, len(data), 6):
            ip_port = ''
            bytes = []
            for byte in data[index_pointer:index_pointer+4:]:
                bytes.append(str(byte))
            ip_port = '.'.join(bytes)
            short_port = int.from_bytes(data[index_pointer+4:index_pointer+6:], 'big')
            ip_port += f':{short_port}'
            print(ip_port, self.ip_ports_count)
            self.ip_ports_count += 1
            ip_ports.add(ip_port)
        return ip_ports, ip_port

    def _get_ip_ports_packet_from_MS(self, last_ip_port):
        """
        Gets a set of ips from the Master Server query packet.
        """
        payload = self.header
        payload += last_ip_port
        payload += self.filter
        print(payload)
        self._ms_socket.sendto(payload, self.master_server_addr)
        return self._ms_socket.recv(2048)

    def request_for_ip_ports(self):
        """
        Gets a set of ips from the Master Server.
        """
        last_ip_port = to_cstring('0.0.0.0:0')
        for _ in range(self.max_packets_per_request):
            packet = self._get_ip_ports_packet_from_MS(last_ip_port)
            ips, last_ip_port = self._parse_packet(packet)
            self.ip_ports |= ips
            if last_ip_port == '0.0.0.0:0':
                break
            last_ip_port = to_cstring(last_ip_port)
        self.ip_ports.discard('0.0.0.0:0')
        return self.ip_ports


if __name__ == '__main__':
    msq = MasterServerQuery()
    msq.request_for_ip_ports()
    print(msq.ip_ports)
