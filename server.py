import lib.config
from lib.connection import Connection
from lib.args import Args
from lib.segment import Segment
import lib.segment
import os, sys
import random
import signal

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
        # TODO: tambah three_way_handshake untuk tiap klien
        pass

    def _three_way_error(self):
        raise Exception()

    def three_way_handshake(self, client_addr: tuple[str, int]) -> bool:
        # Three way handshake, server-side, 1 client
        signal.signal(signal.SIGALRM, self._three_way_error)
        try:
            signal.alarm(5)

            # Sequence 1: Tunggu SYN dari client
            req_segment, (req_ip, req_port) = self.connection.listen_single_segment()
            # print(req_segment)
            req_seqnumber = req_segment.get_header()['sequence']

            # Sequence 2: Kirimkan SYN + ACK ke client
            random_number = random.randint(0, 30000)
            while(random_number != req_seqnumber):
                random_number = random.randint(0, 30000)

            res_segment = Segment()
            res_segment.set_flag([lib.segment.SYN_FLAG, lib.segment.ACK_FLAG])
            res_segment.set_header({"sequence": random_number, "ack": req_seqnumber + 1})
            
            if (req_segment.valid_checksum() and (req_ip, req_port) == client_addr):
                self.connection.send_data(res_segment, (client_addr, req_port))

            # Sequence 3: Tunggu ACK dari client
            ack_segment, (ack_ip, ack_port) = self.connection.listen_single_segment()
            ack_flag = ack_segment.ack
            if ack_flag and ack_ip == client_addr:
                print(f"Client {client_addr} connected")
                return True
            else:
                print(f"Client {client_addr} disconnected")
                return False
            
        except:
            print("yah filenya ilang, seperti dia yang kamu sayang-sayang")

    def motd(self):
        print(f"[!] Server started at localhost:{self.port}")
        print(f"[!] Source file | {os.path.basename(self.path).split('/')[-1]} | {os.path.getsize(self.path)} bytes")
        print(f"[!] Listening to broadcast address for clients.")
        print()

if __name__ == '__main__':
    main = Server()
    main.motd()
    main.listen_for_clients()
    main.three_way_handshake(("127.0.0.1", 4500))
    # main.start_file_transfer()
