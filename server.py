import lib.config
from lib.connection import Connection
from lib.args import Args
from lib.segment import Segment
import lib.segment
import os, sys

class Server:
    def __init__(self):
        # Init server
        argList = [
            ("port", int, "Port of server"), 
            ("path", str, "File path to send")
        ]

        args = Args("Run a server that can send file", argList).parse()
        self.ip = lib.config.SERVER_IP
        self.port = args.port
        self.path = args.path

        try:
            self.file = open(self.path, "rb")
            self.filesize = os.stat(self.path).st_size
        except FileNotFoundError:
            print("File not found")
            sys.exit(1)
        
        self.segment_count = (self.filesize + lib.config.SEGMENT_SIZE - 1) // lib.config.SEGMENT_SIZE
        self.connection = Connection(self.ip, self.port, broadcast_bind=True)
        self.connection.set_timeout(lib.config.SERVER_LISTEN_TIMEOUT)

                

    def listen_for_clients(self):
        # Waiting client for connect

        # START OF NYOBAIN DOANG (UPDATE THIS IF YOU ARE GOING TO USE THIS)
        self.client_list = []
        while True:
            resp = self.connection.listen_single_segment()
            segment = resp[0]
            addr = resp[1]
            if segment is None:
                # Timeout
                continue
            if segment.get_flag().syn and segment.valid_checksum():
                if addr not in self.client_list:
                    self.client_list.append(addr)
                    print(segment)
                    print(f"Client {addr} connected")
                prompt = input("[?] Listen more? (y/n) ")
                if prompt != "y":
                    break

        # END OF NYOBAIN DOANG (UPDATE THIS IF YOU ARE GOING TO USE THIS)


    def start_file_transfer(self):
        # Handshake & file transfer for all client
        pass

    def file_transfer(self, client_addr : tuple[str, int]):
        # File transfer, server-side, Send file to 1 client
        pass

    def three_way_handshake(self, client_addr: tuple[str, int]) -> bool:
       # Three way handshake, server-side, 1 client
       pass


if __name__ == '__main__':
    main = Server()
    main.listen_for_clients()
    main.start_file_transfer()
