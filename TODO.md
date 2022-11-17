# Go-Back-N ARQ

- set awal = 0, akhir = window-1, timeout = True
- loop sampe awal > segmen terakhir
    - kalo timeout, kirim ulang segmen [awal, akhir]
    - dengerin
    - kalo kedengeran, timeout = False
    - kalo ga kedengeran, timeout = True
    - kalo gak timeout
        - kalo ack = awal (berarti datanya ada yg ga kekirim) -> biarin sampe timeout
        - kalo ack = awal + 1 (berarti datanya kekirim):
            - awal := ack
            - kirim segmen [akhir+1, min(awal+window-1,segmen terakhir)]


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