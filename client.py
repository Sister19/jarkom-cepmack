import lib.config
from lib.connection import Connection
from lib.args import Args
from lib.segment import Segment
import lib.segment
import os, sys
import signal
import random

# ini broadcast address kalau di windows, kalau di linux keknya bisa broadcast = "" aja;
BROADCAST_ADDRESS = "<broadcast>"

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
        self.server_ip = BROADCAST_ADDRESS
        self.motd()

    def _three_way_error(self, sig, frame):
        raise Exception()

    def three_way_handshake(self):
        signal.signal(signal.SIGALRM, self._three_way_error)
        self.connection.set_timeout(lib.config.CLIENT_LISTEN_TIMEOUT)
        try:
            signal.alarm(lib.config.CLIENT_LISTEN_TIMEOUT*3)
            # Hendshek pertama ngirim SYN
            print(f"[!] [Handshake] Sending syn request to broadcast address at {self.broadcast_port}.")
            server_request = Segment()
            server_request.set_flag([lib.segment.SYN_FLAG])
            server_request.set_header({"sequence": 0, "ack" : 0})

            self.connection.send_data(server_request, (BROADCAST_ADDRESS, self.broadcast_port))

            # Hendshek kedua nunggu SYN+ACK
            print("[!] [Handshake] Waiting for syn+ack from server.")
            segment_recv, (addr_recv, port_recv) = self.connection.listen_single_segment()
            print('sampe sini ga')

            while(not segment_recv):
                print("[!] [Handshake] No response from server, retrying...")
                self.connection.send_data(server_request, (BROADCAST_ADDRESS, self.broadcast_port))
                segment_recv, (addr_recv, port_recv) = self.connection.listen_single_segment()

            self.server_ip = addr_recv


            # Hendshek ketiga ngirim ACK (kalo dapet)
            print("[!] [Handshake] Received syn+ack from server, sending ack.")
            if segment_recv.valid_checksum() and segment_recv.get_flag().ack and segment_recv.get_flag().syn and segment_recv.get_header()['ack'] == 1:
                ack_res = Segment()
                ack_res.set_flag([lib.segment.ACK_FLAG])
                ack_res.set_header({"sequence": 1, "ack" : segment_recv.get_header()["sequence"]+1})
                self.connection.send_data(ack_res, (addr_recv, port_recv))
                print("[!] [Handshake] ACK received, handshake success.")
                print("[!] [Handshake] Handshake success.")
                signal.alarm(0)
                return True
            elif not segment_recv.valid_checksum():
                print("[!] [ERR] [Handshake] Handshake failed, checksum invalid.")
                raise Exception()
            elif not segment_recv.get_flag().ack or segment_recv.get_flag().syn:
                print("[!] [ERR] [Handshake] Handshake failed, syn+ack not received.")
                raise Exception()
            elif segment_recv.get_header()['ack'] != 1:
                print("[!] [ERR] [Handshake] Handshake failed, ack header doen't match.")
                raise Exception()
        except:
            print("tiga jalan goyang tangan")
            print("untuk membuka jaringan")
            print("gagal dijalankan")
            print("sangat disayangkan")
            print(f"[!] [ERR] [TIMEOUT] Server not found at {BROADCAST_ADDRESS}:{self.broadcast_port}")
            return False
            
            
    def listen_file_transfer(self):
        # File transfer, client-side
        payload = b''
        Rn = 0
        active = True
        while active:
            print('hmm')
            segment_recv, addr_recv = self.connection.listen_single_segment()
            if(segment_recv and segment_recv.get_flag().fin):
                segment_ack = Segment()
                segment_ack.set_flag([lib.segment.FIN_FLAG])
                self.connection.send_data(segment_ack, addr_recv)
                active = False
            elif not addr_recv or (self.server_ip, self.broadcast_port) == addr_recv:
                if(segment_recv and segment_recv.get_header()['sequence'] == Rn and segment_recv.valid_checksum()):
                    payload += segment_recv.get_payload()
                    Rn += 1
                else:
                    # buang segmen
                    if(segment_recv):
                        print('buang segmen') 
                    else:
                        print('ga dpt segmen')
                segment_ack = Segment()
                segment_ack.set_header({'sequence': 0, 'ack': Rn})
                segment_ack.set_flag([lib.segment.ACK_FLAG])
                self.connection.send_data(segment_ack, (self.server_ip, self.broadcast_port))
        



        # pengiriman file selesai


        file = open(self.path, 'wb')
        file.write(payload)


        file.close()
        
    def motd(self):
        print(f"[!] Client started at {self.ip}:{self.port}")
        print(f"[!] Sending syn request to broadcast address at {self.broadcast_port}.")
        print()
        


if __name__ == '__main__':
    main = Client()
    if main.three_way_handshake():
        main.listen_file_transfer()
