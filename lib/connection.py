import socket


from .segment import Segment
from . import config


class Connection:
    def __init__(self, ip : str, port : int, broadcast_bind : bool = False, send_broadcast : bool = False):
        # Init UDP socket
        self.ip = ip
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if send_broadcast:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        if broadcast_bind:
            self.socket.bind(("", port))
        else:
            self.socket.bind((self.ip, self.port))
        
    def set_timeout(self, timeout : float):
        # Set timeout for socket
        self.socket.settimeout(timeout)

    def send_data(self, msg : Segment, dest : tuple[str, int]):
        # dest: (ip, port)
        # Send single segment into destination
        print("Sending data to", dest)
        self.socket.sendto(msg.get_bytes(), dest)

    def listen_single_segment(self) -> tuple[Segment, tuple[str, int]]:
        # Listen single UDP datagram within timeout and convert into segment
        try:
            data, addr = self.socket.recvfrom(config.BUFFER_SIZE)
            segment = Segment()
            segment.set_from_bytes(data)
            return segment, addr
        except socket.timeout:
            return None, (None, None)


    def close_socket(self):
        # Release UDP socket
        self.socket.close()
