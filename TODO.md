# Go-Back-N ARQ

- set awal = 0, akhir = window-1
- loop sampe awal > segmen terakhir
- kalo timeout, kirim ulang segmen [awal, akhir]
- kalo gak timeout
    - kalo ack = awal (berarti datanya ada yg ga kekirim) -> biarin sampe timeout
    - kalo ack > awal (berarti datanya kekirim):
        - awal := ack
        - kirim segmen [akhir+1, min(awal+window-1,segmen terakhir)]
        - akhir := min(awal+window-1, segmen terakhir)