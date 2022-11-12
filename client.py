import lib.config
from lib.connection import Connection
from lib.args import Args
from lib.segment import Segment
import lib.segment
import os, sys


# ini broadcast address kalau di windows, kalau di linux keknya bisa broadcast = "" aja;
BROADCAST_ADDRESS = "255.255.255.255"

class Client:
    def __init__(self):
        # Init client
        argList = [
            ("port", int, "Port of client"), 
            ("broadcast_port", int, "Broadcast port of server"),
            ("path", str, "File path to save")
        ]

        args = Args("Run a client that can save file from server", argList).parse()
        self.ip = lib.config.CLIENT_IP
        self.port = args.port
        self.broadcast_port = args.broadcast_port
        self.path = args.path
        
        self.connection = Connection(self.ip, self.port, send_broadcast=True)
        self.connection.set_timeout(lib.config.CLIENT_LISTEN_TIMEOUT)

    def three_way_handshake(self):
        # Three Way Handshake, client-side
        server_request = Segment()
        server_request.set_flag([lib.segment.SYN_FLAG])

        # START OF NYOBAIN DOANG (DELETE THIS IF YOU ARE GOING TO USE THIS)
        server_request.set_header({"sequence": 1, "ack": 1000})
        # END OF NYOBAIN DOANG (DELETE THIS IF YOU ARE GOING TO USE THIS)

        self.connection.send_data(server_request, (BROADCAST_ADDRESS, self.broadcast_port))

    def listen_file_transfer(self):
        # File transfer, client-side
        pass


if __name__ == '__main__':
    main = Client()
    main.three_way_handshake()
    main.listen_file_transfer()
