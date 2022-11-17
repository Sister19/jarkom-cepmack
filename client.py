import lib.config
from lib.connection import Connection
from lib.args import Args
from lib.segment import Segment
import lib.segment
import os, sys
import signal
from lib.verbose import Verbose
import lib.verbose

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

        try:
            self.file = open(self.path, 'wb')
        except:
            print(Verbose(title="ERR", subtitle={"FILE":"", "PATH":self.path}, content=f"File path not found."))
            sys.exit(1)
        
        self.connection = Connection(self.ip, self.port, send_broadcast=True)
        self.server_ip = BROADCAST_ADDRESS
        self.motd()

    def __signal_error(self, sig, frame):
        raise Exception()

    def three_way_handshake(self):
        signal.signal(signal.SIGALRM, self.__signal_error)
        self.connection.set_timeout(lib.config.CLIENT_LISTEN_TIMEOUT)
        try:
            signal.alarm(lib.config.CLIENT_LISTEN_TIMEOUT*3)
            # Hendshek pertama ngirim SYN
            print(Verbose(title="Handshake", subtitle={"SYN":"", "SEQ":0}, content=f"Sending syn request to broadcast address at {self.broadcast_port}."))
            server_request = Segment()
            server_request.set_flag([lib.segment.SYN_FLAG])
            server_request.set_header({"sequence": 0, "ack" : 0})

            self.connection.send_data(server_request, (BROADCAST_ADDRESS, self.broadcast_port))

            # Hendshek kedua nunggu SYN+ACK
            print(Verbose(title="Handshake", subtitle={"SYN+ACK":""}, content=f"Waiting for syn+ack from server."))
            segment_recv, (addr_recv, port_recv) = self.connection.listen_single_segment()
            # print('sampe sini ga')

            while(not segment_recv):
                print(Verbose(title="Handshake", subtitle={"SYN+ACK":"","ERR":""}, content=f"No response from server, retrying..."))
                self.connection.send_data(server_request, (BROADCAST_ADDRESS, self.broadcast_port))
                segment_recv, (addr_recv, port_recv) = self.connection.listen_single_segment()

            self.server_ip = addr_recv


            # Hendshek ketiga ngirim ACK (kalo dapet)
            

            if segment_recv.valid_checksum() and segment_recv.get_flag().ack and segment_recv.get_flag().syn and segment_recv.get_header()['ack'] == 1:
                print(Verbose(title="Handshake", 
                    subtitle={"SYN+ACK":"", "SEQ":segment_recv.get_header()['sequence'], 
                    "ACK":segment_recv.get_header()['ack']}, 
                    content=f"Received syn+ack from server, sending ack."))
                
                ack_res = Segment()
                ack_res.set_flag([lib.segment.ACK_FLAG])
                ack_res.set_header({"sequence": 1, "ack" : segment_recv.get_header()["sequence"]+1})
                self.connection.send_data(ack_res, (addr_recv, port_recv))
                # print("[!] [Handshake] ACK received, handshake success.")
                # print("[!] [Handshake] Handshake success.")

                print(Verbose(title="Handshake",
                    subtitle={"ACK":"", 
                    "ACK":ack_res.get_header()['ack']}, 
                    content=f"ACK has been sent, handshake success."))

                signal.alarm(0)
            elif not segment_recv.valid_checksum():
                print(Verbose(title="Handshake", subtitle={"SYN+ACK":"", "ERR":"", "CHECKSUM":segment_recv.checksum}, content=f"Handshake failed, checksum invalid."))
                sys.exit(1)
            elif not segment_recv.get_flag().ack or segment_recv.get_flag().syn:
                flag = segment_recv.get_flag()
                print(Verbose(title="Handshake", subtitle={"SYN+ACK":"", "ERR":"", "SYN":flag.syn, "ACK":flag.ack}, content=f"Handshake failed, syn+ack flag not set."))
                sys.exit(1)
            elif segment_recv.get_header()['ack'] != 1:
                print(Verbose(title="Handshake", subtitle={"SYN+ACK":"", "ERR":"", "ACK":segment_recv.get_header()['ack']}, content=f"Handshake failed, ack number not match the sequence."))
                sys.exit(1)
        except:
            print(Verbose(title="Handshake", subtitle={"SYN+ACK":"", "ERR":"", "TIMEOUT":""}, content=f"Server not found at port {self.broadcast_port}"))
            sys.exit(1)
            # print("tiga jalan goyang tangan")
            # print("untuk membuka jaringan")
            # print("gagal dijalankan")
            # print("sangat disayangkan")
            # print(f"[!] [ERR] [TIMEOUT] Server not found at {BROADCAST_ADDRESS}:{self.broadcast_port}")
            
            
    def listen_file_transfer(self):
        # File transfer, client-side
        payload = b''
        Rn = 0
        active = True
        print()
        print(Verbose(title="File Transfer", content=f"Waiting for file transfer from server..."))
        print()
        while active:
            # print('hmm')
            segment_recv, addr_recv = self.connection.listen_single_segment()
            if(segment_recv and segment_recv.get_flag().fin):
                print(Verbose(title="File Transfer", subtitle={"FIN":""}, content=f"Received fin from server, sending ack."))
                segment_ack = Segment()
                segment_ack.set_flag([lib.segment.ACK_FLAG])
                self.connection.send_data(segment_ack, addr_recv)
                # CLOSING PROCESS
                print(Verbose(title="File Transfer", subtitle={"CLS":""}, content=f"Closing connection..."))
                segment_fin = Segment()
                segment_fin.set_flag([lib.segment.FIN_FLAG])
                self.connection.send_data(segment_fin, addr_recv)
                # TODO verbose nutup toko
                signal.signal(signal.SIGALRM, self.__signal_error)
                try:
                    signal.alarm(5)
                    while True:
                        segment_ack, addr = self.connection.listen_single_segment()
                        if segment_ack and addr == (self.server_ip, self.broadcast_port) and segment_ack.get_flag().ack:
                            signal.alarm(0)
                            self.connection.close_socket()
                            active = False
                except:
                    self.connection.close_socket()
                    active = False
                # TODO: handle receive ack
            elif addr_recv or (self.server_ip, self.broadcast_port) == addr_recv:
                if(segment_recv and segment_recv.get_header()['sequence'] == Rn and segment_recv.valid_checksum()):
                    payload += segment_recv.get_payload()
                    print(Verbose(title="File Transfer", subtitle={"NUM":Rn}, content=f"Received segment {Rn}, sending ack..."))
                    Rn += 1
                else:
                    # buang segmen
                    if(segment_recv):
                        # print('buang segmen') 
                        print(Verbose(title="File Transfer", subtitle={"NUM":Rn, "ERR":""}, content=f"Received out of order segment {segment_recv.get_header()['sequence']}, sending ack..."))
                    else:
                        # print('ga dpt segmen')
                        print(Verbose(title="File Transfer", subtitle={"NUM":Rn, "ERR":"", "TIMEOUT":""}, content=f"Received no segment, sending ack..."))
                segment_ack = Segment()
                segment_ack.set_header({'sequence': 0, 'ack': Rn})
                segment_ack.set_flag([lib.segment.ACK_FLAG])
                self.connection.send_data(segment_ack, (self.server_ip, self.broadcast_port))
        



        # pengiriman file selesai

        
        print(Verbose(title="File Transfer", subtitle={"PAYLOAD":""}, content=f"Transfer success! Cumulative payload length: {len(payload)} bytes, commence writing file..."))
        self.file.write(payload)
        print(Verbose(title="File Transfer", subtitle={"PAYLOAD":""}, content=f"File written to {self.path}"))
        self.file.close()
        
    def motd(self):
        print(lib.verbose.MOTD)
        print(Verbose(content=f"Client started at {self.ip}:{self.port}"))
        print(Verbose(content=f"Starting handshake with server at {self.broadcast_port}"))
        print()
        


if __name__ == '__main__':
    main = Client()
    main.three_way_handshake()
    main.listen_file_transfer()
