import lib.config
from lib.connection import Connection
from lib.args import Args
from lib.segment import Segment
import lib.segment
import os, sys
import signal

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

    def _three_way_error(self):
        raise Exception()

    def three_way_handshake(self):
        signal.signal(signal.SIGALRM, self._three_way_error)
        try:
            signal.alarm(5)
            print("test")
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


            # Hendshek ketiga ngirim ACK (kalo dapet)
            if segment_recv.valid_checksum() and segment_recv.get_flag().ack and segment_recv.get_flag().syn:
                ack_res = Segment()
                ack_res.set_flag([lib.segment.ACK_FLAG])
                ack_res.set_header({"sequence": 1, "ack" : segment_recv.get_header()["sequence"]+1})
                self.connection.send_data(ack_res, (addr_recv, port_recv))
            else:
                print("bukan synack")
        except:
            print("tiga jalan goyang tangan")
            print("untuk membuka jaringan")
            print("gagal dijalankan")
            print("sangat disayangkan")
            
            
    def listen_file_transfer(self):
        # File transfer, client-side
        Rn = 0
        while True:
            segment_recv, (addr_recv, port_recv) = self.connection.listen_single_segment()


if __name__ == '__main__':
    main = Client()
    main.three_way_handshake()
    # main.listen_file_transfer()
