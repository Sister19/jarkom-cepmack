import lib.config
from lib.connection import Connection
from lib.args import Args
from lib.segment import Segment
import lib.verbose
import lib.segment
import os, sys
from lib.verbose import Verbose
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
            print(Verbose(Verbose(title="ERR", subtitle={"FILE":"", "PATH":self.path}, content=f"File path not found.")))
            sys.exit(1)
        
        self.payload_size = lib.config.SEGMENT_SIZE - 12
        self.segment_count = (self.filesize + self.payload_size - 1) // (self.payload_size - 12)
        self.connection = Connection(self.ip, self.port, broadcast_bind=True)
        self.connection.set_timeout(lib.config.SERVER_LISTEN_TIMEOUT)

                

    def listen_for_clients(self):
        # Waiting client for connect
        self.client_list = []
        print(Verbose(title="Handshake", content=f"Waiting for syn requests from clients..."))
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
                    print(f"[!] Received request from {client_ip}:{client_port}")
                    print(Verbose(title="Handshake", subtitle={"SYN":""}, content=f"Received request from {client_ip}:{client_port}"))
                else:
                    print(Verbose(title="Handshake", subtitle={"SYN":""}, content=f"Received request from {client_ip}:{client_port}, but already received before"))
                print(Verbose(type="?", content=f"Listen more? [Y/n]"), end=" ")
                prompt = input()
                if prompt != "y" and prompt != "Y":
                    print()
                    print("Client list")
                    for i in range(len(self.client_list)):
                        (_, (client_ip, client_port)) = self.client_list[i]
                        print(Verbose(content=f"[{i+1}] {client_ip}:{client_port}"))
                    print()
                    break
            elif not segment.get_flag().syn:
                print(Verbose(title="Handshake", subtitle={"ERR":""}, content=f"Received non syn segment from {addr[0]}:{addr[1]}"))
            elif not segment.valid_checksum():
                print(Verbose(title="Handshake", subtitle={"ERR":"", "CHECKSUM":segment.checksum}, content=f"Received invalid checksum from {addr[0]}:{addr[1]}"))
        

    def start_file_transfer(self):
        # Handshake & file transfer for all client
        self.connected_client = []
        i = 1
        for client_header, client_addr in self.client_list:
            # 3 way handshake
            print(Verbose(title="Handshake", subtitle={"CLIENT":f"{i}"}, content=f"Handshake to client {i} at {client_addr[0]}:{client_addr[1]}"))
            if(self.three_way_handshake(i, client_header, client_addr)):
                self.connected_client.append(client_addr)
                i+=1
            else:
                Verbose(title="Handshake", subtitle={"CLIENT":f"{i}", "ERR":""}, content=f"Handshake with {client_addr[0]}:{client_addr[1]} failed, skipping...")
            print()
        
        # File transfer
        i = 1
        for client_addr in self.connected_client:
            print(Verbose(title="File Transfer", subtitle={"CLIENT":f"{i}"}, content=f"Starting file transfer to client {i} at {client_addr[0]}:{client_addr[1]}"))
            self.file_transfer(i, client_addr)
            i+=1
        if(i>1):
            print(Verbose(title="File Transfer", content=f"File transfer finished."))
            print()
        print(Verbose(subtitle={"CLS":""}, content=f"Closing server..."))
        self.connection.close_socket()
        sys.exit()


    def __signal_error(self, sig, frame):
        raise Exception()
                

    def file_transfer(self, client_id:int, client_addr : tuple[str, int]):
        # File transfer, server-side, Send file to 1 client
        window_size = lib.config.WINDOW_SIZE
        seq_lower_base = 0
        seq_upper_base = seq_lower_base + window_size - 1
        self.connection.set_timeout(lib.config.SERVER_TRANSFER_TIMEOUT)
        for i in range(seq_lower_base, min(seq_upper_base, self.segment_count-1) + 1):
            data_segment = Segment()
            self.file.seek(self.payload_size * i)
            data_segment.set_payload(self.file.read(self.payload_size))
            data_segment.set_header({"sequence": i, "ack": 0})
            self.connection.send_data(data_segment, client_addr)
            print(Verbose(title="File Transfer", subtitle={"CLIENT":f"{client_id}", "NUM":i}, content=f"Sent segment {i} to {client_addr[0]}:{client_addr[1]}"))
        
        while seq_lower_base <= self.segment_count-1:
            # Listen for ACK(s)
            ack_segment, (ack_ip, ack_port) = self.connection.listen_single_segment()
            if not ack_segment:
                # Send segment within window_size
                print(Verbose(title="File Transfer", subtitle={"CLIENT":f"{client_id}", "ERR":"", "TIMEOUT":""}, content=f"Timeout, resending segment {seq_lower_base} to {client_addr[0]}:{client_addr[1]}"))
                for i in range(seq_lower_base, min(seq_upper_base, self.segment_count-1) + 1):
                    data_segment = Segment()
                    self.file.seek(self.payload_size * i)
                    data_segment.set_payload(self.file.read(self.payload_size))
                    data_segment.set_header({"sequence": i, "ack": 0})
                    self.connection.send_data(data_segment, client_addr)
                    print(Verbose(title="File Transfer", subtitle={"CLIENT":f"{client_id}", "NUM":i}, content=f"Sent segment {i} to {client_addr[0]}:{client_addr[1]}"))
            else:
                ack_number = ack_segment.get_header()["ack"]
                if ack_number > seq_lower_base + 1:
                    print(Verbose(title="File Transfer", subtitle={"CLIENT":f"{client_id}", "NUM":seq_lower_base, "ACK":""}, content=f"Received ACK {ack_number} from {ack_ip}:{ack_port}"))
                    seq_lower_base = ack_number
                    for i in range(seq_lower_base+1, min(seq_upper_base + window_size - 1, self.segment_count-1) + 1):
                        data_segment = Segment()
                        self.file.seek(self.payload_size * i)
                        data_segment.set_payload(self.file.read(self.payload_size))
                        data_segment.set_header({"sequence": i, "ack": 0})
                        self.connection.send_data(data_segment, client_addr)
                        print(Verbose(title="File Transfer", subtitle={"CLIENT":f"{client_id}", "NUM":i}, content=f"Sent segment {i} to {client_addr[0]}:{client_addr[1]}"))
                    seq_upper_base = min(seq_lower_base + window_size - 1, self.segment_count - 1)
                else:
                    print(Verbose(title="File Transfer", 
                    subtitle={"CLIENT":f"{client_id}", "ERR":"", "ACK": ack_number}, 
                    content=f"Received invalid ACK from {ack_ip}:{ack_port}, expected {seq_lower_base+1}. Ignoring..."))
                # print(Verbose(title="File Transfer", subtitle={"CLIENT":f"{client_id}", "NUM":seq_lower_base,"ACK": "", "ACK":ack_number}, content=f"Waiting for ACK from {client_addr[0]}:{client_addr[1]}"))

        # Begin 2 way handshake to terminate connection
        print()
        print(Verbose(title="File Transfer", subtitle={"CLIENT":f"{client_id}", "CLS":""}, content=f"File transfer to {client_addr[0]}:{client_addr[1]} completed. Closing connection..."))
        print(Verbose(title="File Transfer", subtitle={"CLIENT":f"{client_id}", "FIN":""}, content=f"Sending FIN to {client_addr[0]}:{client_addr[1]}"))
        fin_segment = Segment()
        fin_segment.set_flag([lib.segment.FIN_FLAG])
        self.connection.send_data(fin_segment, client_addr)

        # Waiting ACK response
        signal.signal(signal.SIGALRM, self.__signal_error)
        self.connection.set_timeout(lib.config.SERVER_LISTEN_TIMEOUT)
        try:
            signal.alarm(lib.config.SERVER_LISTEN_TIMEOUT*3)
            ack_segment, (ack_ip, ack_port) = self.connection.listen_single_segment()
            print(Verbose(title="File Transfer", subtitle={"CLIENT":f"{client_id}", "ACK":""}, content=f"Waiting ACK from {client_addr[0]}:{client_addr[1]}"))
            while(ack_segment is None):
                self.connection.send_data(fin_segment, client_addr)
                ack_segment, (ack_ip, ack_port) = self.connection.listen_single_segment()
            else:
                ack_flag = ack_segment.ack
                print(Verbose(title="File Transfer", subtitle={"CLIENT":f"{client_id}", "FIN":""}, content=f"Waiting FIN from {client_addr[0]}:{client_addr[1]}"))
                fin_segment, (fin_ip, fin_port) = self.connection.listen_single_segment()
                while(fin_segment is None):
                    self.connection.send_data(fin_segment, client_addr)
                    fin_segment, (fin_ip, fin_port) = self.connection.listen_single_segment()
                else:
                    fin_flag = fin_segment.get_flag()
                    if ack_flag and (ack_ip, ack_port) == client_addr and fin_flag.fin and (fin_ip, fin_port) == client_addr:
                        fin_ack_segment = Segment()
                        fin_ack_segment.set_flag([lib.segment.ACK_FLAG])
                        self.connection.send_data(fin_ack_segment, client_addr)
                        print(Verbose(title="File Transfer", subtitle={"CLIENT":f"{client_id}", "FIN+ACK":""}, content=f"FIN+ACK received from {client_addr[0]}:{client_addr[1]}"))
                        print(Verbose(title="File Transfer", subtitle={"CLIENT":f"{client_id}", "ACK":""}, content=f"ACK sent to {client_addr[0]}:{client_addr[1]}"))
                        # self._verbose(address=client_addr, message=f"Client connection terminated")
                    else:
                        print(Verbose(title="File Transfer", 
                        subtitle={"CLIENT":f"{client_id}", "FIN+ACK":"", "ERR":"", "ACK":ack_flag.ack, "FIN":fin_flag.fin}, 
                        content=f"Received invalid FIN+ACK from {ack_ip}:{ack_port}. Ignoring..."))
        except Exception as e:
            print(Verbose(title="File Transfer", subtitle={"CLIENT":f"{client_id}", "FIN+ACK":"", "ERR":"", "TIMEOUT":""}, content=f"Listen FIN+ACK timeout, ignoring..."))


    def three_way_handshake(self, client_id: int, client_header:dict, client_addr: tuple[str, int]) -> bool:
        # Three way handshake, server-side, 1 client

        # Sequence 2: Kirimkan SYN + ACK ke client
        res_segment = Segment()
        res_segment.set_flag([lib.segment.SYN_FLAG, lib.segment.ACK_FLAG])
        res_segment.set_header({"sequence": 1, "ack": client_header['sequence']+1})

        print(Verbose(title="Handshake", 
        subtitle={"CLIENT":f"{client_id}", "SYN+ACK":"", "SEQ":1, "ACK":res_segment.get_header()["ack"]}, 
        content=f"Sending SYN + ACK to {client_addr[0]}:{client_addr[1]}"))
        
        self.connection.send_data(res_segment, client_addr)

        # Sequence 3: Tunggu ACK dari client
        print(Verbose(title="Handshake", subtitle={"CLIENT":f"{client_id}", "ACK":""}, content=f"Waiting for ACK from {client_addr[0]}:{client_addr[1]}"))
        ack_segment, (ack_ip, ack_port) = self.connection.listen_single_segment()
        if(ack_segment is None):
            print(Verbose(title="Handshake", subtitle={"CLIENT":f"{client_id}", "ACK":"", "ERR":"", "TIMEOUT":""}, content=f"Listen ACK timeout, ignoring..."))
            return False
        ack_flag = ack_segment.ack
        if ack_flag and (ack_ip, ack_port) == client_addr and ack_segment.get_header()['ack'] == 2:
            print(Verbose(title="Handshake", subtitle={"CLIENT":f"{client_id}", "ACK":"", "ACK":2}, content=f"Received ACK from {client_addr[0]}:{client_addr[1]}"))
            print(Verbose(title="Handshake", subtitle={"CLIENT":f"{client_id}"}, content=f"Handshake with {client_addr[0]}:{client_addr[1]} success"))
            return True
        elif not ack_flag:
            print(Verbose(title="Handshake", subtitle={"CLIENT":f"{client_id}", "ACK":"", "ERR":""}, content=f"Handshake with {client_addr[0]}:{client_addr[1]} failed, ACK flag not set"))
            return False
        elif (ack_ip, ack_port) != client_addr:
            print(Verbose(title="Handshake", subtitle={"CLIENT":f"{client_id}", "ACK":"", "ERR":""}, 
            content=f"Handshake with {client_addr[0]}:{client_addr[1]} failed, ACK request address not match"))
            return False
        elif ack_segment.get_header()['ack'] != 2:
            print(Verbose(title="Handshake", subtitle={"CLIENT":f"{client_id}", "ACK":"", "ERR":"", "ACK":ack_segment.get_header()['ack']},
            content=f"Handshake with {client_addr[0]}:{client_addr[1]} failed, ACK number not match SYN ACK sequence number"))
            return False
        

    def motd(self):
        print(lib.verbose.MOTD)
        print(f"Starting server at {self.ip}:{self.port}...")
        print(Verbose(content=f"Starting server at {self.ip}:{self.port}"))
        print(Verbose(content=f"Source file | {self.filename} | Size: {self.filesize} bytes | Segments: {self.segment_count}"))
        print(Verbose(content="Listening for incoming connections..."))
        print()

if __name__ == '__main__':
    main = Server()
    main.motd()
    main.listen_for_clients()
    # main.three_way_handshake(("127.0.0.1", 4500))
    main.start_file_transfer()
