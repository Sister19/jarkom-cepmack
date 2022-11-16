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
            self.filename = os.path.basename(self.path)
        except FileNotFoundError:
            print("File not found")
            sys.exit(1)
        
        self.segment_count = (self.filesize + lib.config.SEGMENT_SIZE - 13) // (lib.config.SEGMENT_SIZE - 12)
        self.connection = Connection(self.ip, self.port, broadcast_bind=True)
        self.connection.set_timeout(lib.config.SERVER_LISTEN_TIMEOUT)

                

    def listen_for_clients(self):
        # Waiting client for connect
        self.client_list = []
        while True:
            resp = self.connection.listen_single_segment()
            segment = resp[0]
            addr = resp[1]
            if segment is None:
                # Timeout
                print("Timeout")
                continue
            if segment.get_flag().syn and segment.valid_checksum():
                if addr not in self.client_list:
                    self.client_list.append(addr)
                    print(f"Client {addr} connected")
                else:
                    print(f"Client {addr} already connected")
                prompt = input("[?] Listen more? (y/n) ")
                if prompt != "y":
                    break

        

    def start_file_transfer(self):
        # Handshake & file transfer for all client
        self.connected_client = []
        for(client_ip, client_port) in self.client_list:
            if self.three_way_handshake((client_ip, client_port)):
                self.connected_client.append((client_ip, client_port))

        for(client_ip, client_port) in self.connected_client:
            self.file_transfer((client_ip, client_port))

    def file_transfer(self, client_addr : tuple[str, int]):
        # File transfer, server-side, Send file to 1 client
        window_size = lib.config.WINDOW_SIZE
        seq_base = 0
        seq_max = window_size + 1
        seq_window_bound = min(seq_base + window_size, self.segment_count) - seq_base
        
        # Open file to transfer
        while seq_base < self.segment_count:
            data_segment = Segment()
            self.file.seek(lib.config.SEGMENT_SIZE - 12)
            seq_base+=1

        # Begin 2 way handshake to terminate connection
        fin_segment = Segment()
        fin_segment.set_flag([lib.segment.FIN_FLAG])
        self.connection.send_data(fin_segment, client_addr)

        # Waiting ACK response
        ack_segment, (ack_ip, ack_port) = self.connection.listen_single_segment()
        if(ack_segment is None):
            print("Timeout")
        else:
            ack_flag = ack_segment.ack
            if ack_flag and (ack_ip, ack_port) == client_addr:
                fin_ack_segment = Segment()
                fin_ack_segment.set_flag([lib.segment.ACK_FLAG, lib.segment.FIN_FLAG])
                self.connection.send_data(fin_ack_segment, client_addr)
                print(f"Client {client_addr} terminated")
            else:
                print(f"Client {client_addr} bukan ack dari client yang bersangkutan") # ganti verbosenya jika diperlukan
        

        

    def _three_way_error(self):
        raise Exception()

    def three_way_handshake(self, client_addr: tuple[str, int]) -> bool:
        # Three way handshake, server-side, 1 client
        signal.signal(signal.SIGALRM, self._three_way_error)
        try:
            signal.alarm(5)

            # Sequence 1: Tunggu SYN dari client
            # Asumsikan SYN sudah diterima

            # Sequence 2: Kirimkan SYN + ACK ke client
            res_segment = Segment()
            res_segment.set_flag([lib.segment.SYN_FLAG, lib.segment.ACK_FLAG])
            
            self.connection.send_data(res_segment, client_addr)

            # Sequence 3: Tunggu ACK dari client
            ack_segment, (ack_ip, ack_port) = self.connection.listen_single_segment()
            ack_flag = ack_segment.ack
            if ack_flag and (ack_ip, ack_port) == client_addr:
                print(f"Client {client_addr} connected")
                return True
            else:
                print(f"Client {client_addr} disconnected")
                return False
            
        except:
            print("yah filenya ilang, seperti dia yang kamu sayang-sayang")

    def motd(self):
        print(f"[!] Server started at localhost:{self.port}")
        print(f"[!] Source file | {self.filename} | {self.filesize} bytes")
        print(f"[!] Listening to broadcast address for clients.")
        print()

if __name__ == '__main__':
    main = Server()
    main.motd()
    main.listen_for_clients()
    # main.three_way_handshake(("127.0.0.1", 4500))
    main.start_file_transfer()
