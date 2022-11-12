import socket

from .segment import Segment
from . import config


class Connection:
    def __init__(self, ip : str, port : int):
        # Init UDP socket
        self.ip = ip
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.socket.bind((self.ip, self.port))
        
    def set_timeout(self, timeout : float):
        # Set timeout for socket
        self.socket.settimeout(timeout)

    def send_data(self, msg : Segment, dest : tuple[str, int]):
        # dest: (ip, port)
        # Send single segment into destination
        self.socket.sendto(msg.to_bytes(), dest)

    def listen_single_segment(self) -> tuple(Segment, tuple[str, int]):
        # Listen single UDP datagram within timeout and convert into segment
        try:
            data, addr = self.socket.recvfrom(config.BUFFER_SIZE)
            return Segment.from_bytes(data), addr
        except self.socket.timeout:
            return None


    def close_socket(self):
        # Release UDP socket
        self.socket.close()
