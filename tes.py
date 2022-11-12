import os


f = open("server.py", "rb")
print(os.stat("server.py").st_size)