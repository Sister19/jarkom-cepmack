MOTD = r"""
******************************************************************************************
                                                                         ___              
 _-_,,             ,,                                                   -   -_,      ,,   
(  //    _         ||                                                  (  ~/||       ||   
  _||   < \, ,._-_ ||/\  /'\\ \\/\\/\\        _-_  _-_  -_-_  \\/\\/\\ (  / ||   _-_ ||/\ 
  _||   /-||  ||   ||_< || || || || || <>-<> ||   || \\ || \\ || || ||  \/==||  ||   ||_< 
   ||  (( ||  ||   || | || || || || ||       ||   ||/   || || || || ||  /_ _||  ||   || | 
-__-,   \/\\  \\,  \\,\ \\,/  \\ \\ \\       \\,/ \\,/  ||-'  \\ \\ \\ (  - \\, \\,/ \\,\ 
                                                        |/                                
                                                        '                                 
******************************************************************************************
                            Welcome to Jarkom-cepmAck Server!
"""

class Verbose:
    def __init__(self, type:str="!", title:str="", subtitle:dict={}, content:str=""):
        self.type = type
        self.title = title
        self.subtitle = subtitle
        self.content = content
        
    def __str__(self):
        res = f"[{self.type}]"
        if self.title:
            res += f" [{self.title}]"
        if self.subtitle:
            for key, value in self.subtitle.items():
                if(value!=""):
                    res += f" [{key}={value}]"
                else:
                    res += f" [{key}]"
        if self.content:
            res += f" {self.content}"
        return res