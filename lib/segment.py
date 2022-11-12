import struct

# Constants 
SYN_FLAG = 0b00000010
ACK_FLAG = 0b00010000
FIN_FLAG = 0b00000001

class SegmentFlag:
    def __init__(self, flag : bytes):
        # Init flag variable from flag byte
        self.flag = flag
        self.syn = bool(self.flag & SYN_FLAG)
        self.ack = bool(self.flag & ACK_FLAG)
        self.fin = bool(self.flag & FIN_FLAG)

    def get_flag_bytes(self) -> bytes:
        # Convert this object to flag in byte form
        return struct.pack("B", self.flag)

    def toggle_syn(self):
        # Toggle SYN flag
        self.flag = self.flag ^ SYN_FLAG
        self.syn = not self.syn
    
    def toggle_ack(self):
        # Toggle ACK flag
        self.flag = self.flag ^ ACK_FLAG
        self.ack = not self.ack

    def toggle_fin(self):
        # Toggle FIN flag
        self.flag = self.flag ^ FIN_FLAG
        self.fin = not self.fin

class Segment:
    # -- Internal Function --
    def __init__(self):
        # Initalize segment
        self.sequence = 0
        self.ack = 0
        self.flag = SegmentFlag(0b00000000)
        self.checksum = 0
        self.payload = b''

    def __str__(self):
        # Optional, override this method for easier print(segmentA)
        output = ""
        output += f"{'Sequence number':24} | {self.sequence}\n"
        output += f"{'Acknowledgement number':24} | {self.ack}\n"
        output += f"{'Flags':24} | [SYN: {self.flag.syn}] [ACK: {self.flag.ack}] [FIN: {self.flag.fin}]\n"
        output += f"{'Checksum':24} | {self.checksum} [IS VALID: {self.valid_checksum()}]\n"
        output += f"{'Data length':24} | {len(self.payload)}\n"
        return output

    def __calculate_checksum(self) -> int:
        # Calculate checksum here, return checksum result
        data = self.get_bytes_without_checksum()
        for i in range(0, len(data), 2):
            data_chunk = data[i:i+2]
            if(len(data_chunk) == 1):
                data_chunk += b'\x00'
            self.checksum += struct.unpack("!H", data_chunk)[0]

    
        self.checksum = ~self.checksum & 0xFFFF
        return self.checksum
        


    # -- Setter --
    def set_header(self, header : dict):
        pass

    def set_payload(self, payload : bytes):
        pass

    def set_flag(self, flag_list : list):
        pass


    # -- Getter --
    def get_flag(self) -> SegmentFlag:
        pass

    def get_header(self) -> dict:
        pass

    def get_payload(self) -> bytes:
        pass


    # -- Marshalling --
    def set_from_bytes(self, src : bytes):
        # From pure bytes, unpack() and set into python variable
        pass

    def get_bytes(self) -> bytes:
        # Convert this object to pure bytes
        res = b''
        res += struct.pack("!I", self.sequence)
        res += struct.pack("!I", self.ack)
        res += self.flag.get_flag_bytes()
        res += struct.pack("x")
        res += struct.pack("!H", self.__calculate_checksum())
        res += self.payload
        return res

    def get_bytes_without_checksum(self) -> bytes:
        # Get bytes without checksum
        res = b''
        res += struct.pack("!I", self.sequence)
        res += struct.pack("!I", self.ack)
        res += self.flag.get_flag_bytes()
        res += struct.pack("x") 
        res += struct.pack("!H", 0x0000)
        res += self.payload
        return res



    # -- Checksum --
    def valid_checksum(self) -> bool:
        # Use __calculate_checksum() and check integrity of this object
        return self.__calculate_checksum() == 0x0000
