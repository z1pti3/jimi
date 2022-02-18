import re

def rereplace(string,match,replacement):
    try:
        return re.sub(match,replacement,string)
    except:
        return string