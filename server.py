import lib.config
from lib.connection import Connection
from lib.args import Args
from lib.segment import Segment
import lib.segment
import os, sys
import random
import signal
import math

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
            print("[!] [ERR] File not found")
            sys.exit(1)
        
        self.payload_size = lib.config.SEGMENT_SIZE - 12
        self.segment_count = (self.filesize + self.payload_size - 1) // (self.payload_size - 12)
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
                continue
            if segment.get_flag().syn and segment.valid_checksum():
                if addr not in self.client_list:
                    (client_ip, client_port) = addr
                    self.client_list.append((segment.get_header(), addr))
                    print(segment)
                    print(f"[!] Received request from {client_ip}:{client_port}")
                else:
                    print(f"[!] Received request from {client_ip}:{client_port} but already received before")
                prompt = input("[?] Listen more? (y/n) ")
                if prompt != "y":
                    print()
                    print("Client list")
                    for i in range(len(self.client_list)):
                        (_, (client_ip, client_port)) = self.client_list[i]
                        print(f"[{i}] {client_ip}:{client_port}")
                    print()
                    break
            elif not segment.get_flag().syn:
                print("[!] [ERR] Received non SYN segment request")
            elif not segment.valid_checksum():
                print("[!] [ERR] Received request segment with invalid checksum")
        

    def start_file_transfer(self):
        # Handshake & file transfer for all client
        print("[!] Starting file transfer")
        self.connected_client = []
        i = 1
        for client_header, client_addr in self.client_list:
            # 3 way handshake
            print()
            print(f"[!] [Handshake] Handshake to client {i} at {client_addr[0]}:{client_addr[1]}")
            if(self.three_way_handshake(i, client_header, client_addr)):
                self.connected_client.append(client_addr)
                i+=1
            else:
                print(f"[!] [Handshake] Handshake with {client_addr[0]}:{client_addr[1]} failed, skipping...")
        
        # File transfer
        print()
        for client_addr in self.connected_client:
            self.file_transfer(client_addr)

                

    def file_transfer(self, client_addr : tuple[str, int]):
        # File transfer, server-side, Send file to 1 client
        window_size = lib.config.WINDOW_SIZE
        seq_base = 0
        seq_max = window_size + 1
        seq_window_bound = min(seq_base + window_size, self.segment_count) - seq_base
        
        # File transfer
        while seq_base < self.segment_count:
            # Send segment within window
            for i in range(seq_window_bound):
                data_segment = Segment()
                self.file.seek(self.payload_size * (seq_base + i))
                data_segment.set_payload(self.file.read(self.payload_size))
                data_segment.set_header({"sequence": seq_base + i, "ack": 0})
                self.connection.send_data(data_segment, client_addr)
                self._verbose(type="transfer", address=client_addr, seq_number=seq_base + i)
            
            # set max_seq_base to seq_base + window_size
            max_seq_base = seq_base + window_size

            while seq_base < max_seq_base:
                res_segment, (res_ip, res_port) = self.connection.listen_single_segment()
                if(res_segment is None):
                    self._verbose(type="timeout")
                elif res_segment.get_flag().ack:
                    ack_number = res_segment.get_header()["ack"]
                    if ack_number > seq_base:
                        seq_base += 1
                        seq_window_bound = min(seq_base + window_size, self.segment_count) - seq_base
                        self._verbose(type="ack", address=client_addr, message=f"ACK number {ack_number} > {seq_base-1}, shift sequence base to {seq_base}")
                    else: # ack_number <= seq_base
                        self._verbose(type="ack", address=client_addr, message=f"ACK number {ack_number} = {seq_base}, retaining sequence base...")
                # else:
                    # self._verbose(address=client_addr, message="[Timeout] ACK response timeout, resending segment(s)...")

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
                self._verbose(address=client_addr, message=f"Client connection terminated")
            else:
                self._verbose(message=f"Client {client_addr} bukan ack dari client yang bersangkutan") # ganti verbosenya jika diperlukan

    def _verbose(self, type: str=None, address: tuple[str, int]=None, seq_number: int=None, ack_number: int=None, message: str=None):
        """
        types: None (tidak ada pesan spesifik), "handshake", "init", "transfer", "ack", "timeout", "close", "fin"
        message: Pesan yang ingin disampaikan
        """
        if type == "handshake":
            print(f"[!] [Handshake] Handshake to {address[0]}:{address[1]}")
        elif type == "init":
            print(f"[!] [{address[0]}:{address[1]}] Initiating file transfer...")
        elif type == "transfer":
            print(f"[!] [{address[0]}:{address[1]}] [Num={seq_number if seq_number is not None else 'NULL'}] Sending segment to client...")
        elif type == "ack":
            print(f"[!] [{address[0]}:{address[1]}] [Num={ack_number if ack_number is not None else 'NULL'}] [ACK] {message}")
        elif type == "timeout":
            print(f"[!] [ERR] [Timeout] ACK response timeout!")
        elif type == "close":
            print(f"[!] [{address[0]}:{address[1]}] [CLS] File transfer completed, initiating closing connection...")
        elif type == "fin":
            print(f"[!] [{address[0]}:{address[1]}] [FIN] Sending FIN...")
        elif type == "error":
            print(f"[!] [Error] {message}")
        else:
            print(f"[!] [{address[0]}:{address[1] if address is not None else ''}] {message}")


    def three_way_handshake(self, client_id: int, client_header:dict, client_addr: tuple[str, int]) -> bool:
        # Three way handshake, server-side, 1 client

        # Sequence 2: Kirimkan SYN + ACK ke client
        print(f"[!] [Handshake] [Client {client_id}] Sending SYN + ACK to {client_addr[0]}:{client_addr[1]}")
        res_segment = Segment()
        res_segment.set_flag([lib.segment.SYN_FLAG, lib.segment.ACK_FLAG])
        res_segment.set_header({"sequence": 1, "ack": client_header['sequence']+1})
        
        self.connection.send_data(res_segment, client_addr)

        # Sequence 3: Tunggu ACK dari client
        print(f"[!] [Handshake] [Client {client_id}] Waiting ACK from {client_addr[0]}:{client_addr[1]}")
        ack_segment, (ack_ip, ack_port) = self.connection.listen_single_segment()
        ack_flag = ack_segment.ack
        if ack_flag and (ack_ip, ack_port) == client_addr and ack_segment.get_header()['ack'] == 2:
            print(f"[!] [Handshake] [Client {client_id}] Handshake ACK from {client_addr[0]}:{client_addr[1]} received")
            print(f"[!] [Handshake] [Client {client_id}] Handshake to {client_addr[0]}:{client_addr[1]} completed")
            return True
        elif not ack_flag:
            print(f"[!] [ERR] [Handshake] [Client {client_id}] Handshake to {client_addr[0]}:{client_addr[1]} failed, ACK flag not set")
            return False
        elif (ack_ip, ack_port) != client_addr:
            print(f"[!] [ERR] [Handshake] [Client {client_id}] Handshake to {client_addr[0]}:{client_addr[1]} failed, ACK address not match")
            return False
        elif ack_segment.get_header()['ack'] != 2:
            print(f"[!] [ERR] [Handshake] [Client {client_id}] Handshake to {client_addr[0]}:{client_addr[1]} failed, ACK number not match")
            return False
        

    def motd(self):
        print(f"[!] Server started at {self.ip}:{self.port}")
        print(f"[!] Source file | {self.filename} | {self.filesize} bytes")
        print(f"[!] Listening to broadcast address for clients.")
        print()

if __name__ == '__main__':
    main = Server()
    main.motd()
    main.listen_for_clients()
    # main.three_way_handshake(("127.0.0.1", 4500))
    main.start_file_transfer()
