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
        self.connection.set_timeout(lib.config.CLIENT_LISTEN_TIMEOUT)

    def _three_way_error(self):
        raise Exception()

    def three_way_handshake(self):
        signal.signal(signal.SIGALRM, self._three_way_error)
        try:
            signal.alarm(5)
            # Hendshek pertama ngirim SYN
            server_request = Segment()
            server_request.set_flag([lib.segment.SYN_FLAG])
            server_request.set_header({"sequence": 0, "ack" : 0})

            self.connection.send_data(server_request, (BROADCAST_ADDRESS, self.broadcast_port))

            # Hendshek kedua nunggu SYN+ACK
            segment_recv, (addr_recv, port_recv) = self.connection.listen_single_segment()

            while(not segment_recv):
                self.connection.send_data(server_request, (BROADCAST_ADDRESS, self.broadcast_port))
                segment_recv, (addr_recv, port_recv) = self.connection.listen_single_segment()

            print('test')
            # Hendshek ketiga ngirim ACK (kalo dapet)
            if segment_recv.valid_checksum() and segment_recv.get_flag().ack and segment_recv.get_flag().syn:
                ack_res = Segment()
                ack_res.set_flag([lib.segment.ACK_FLAG])
                ack_res.set_header({"sequence": 1, "ack" : segment_recv.get_header()["sequence"]+1})
                self.connection.send_data(ack_res, (addr_recv, port_recv))
                print('kelar goyang tangan')
            else:
                print("bukan synack")
        except:
            print("tiga jalan goyang tangan")
            print("untuk membuka jaringan")
            print("gagal dijalankan")
            print("sangat disayangkan")
            
            
    def listen_file_transfer(self):
        # File transfer, client-side
        segment_list = []
        Rn = 0
        active = True
        while active:
            segment_recv, addr_recv = self.connection.listen_single_segment()
            segment_recv_seq = segment_recv.get_header()['sequence']
            segment_recv_ack = segment_recv.get_header()['ack']
            if(segment_recv.get_flag().fin):
                segment_ack = Segment()
                segment_ack.set_flag([lib.segment.FIN_ACK])
                self.connection.send_data(segment_ack, addr_recv)
                active = False
            else:
                if(segment_recv_seq == Rn):
                    segment_list.append(segment_recv)
                    Rn += 1
                segment_ack = Segment()
                random_number = random.randint(0, 30000)
                while(random_number != segment_recv_seq):
                    random_number = random.randint(0, 30000)
                segment_ack.set_header({'sequence': random_number, 'ack': segment_recv_seq+1})
                segment_ack.set_flag([lib.segment.ACK_FLAG])
                self.connection.send_data(segment_ack, addr_recv)
    
        return segment_list
        


if __name__ == '__main__':
    main = Client()
    main.three_way_handshake()
    # main.listen_file_transfer()
