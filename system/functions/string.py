def contains(string,contents):
    return contents in string

def split(string,spliton,position=None):
    try:
        if position != None:
            return string.split(spliton)[position]
        return string.split(spliton)
    except:
        return ""

def strCount(string,searchString):
    try:
        return string.count(searchString)
    except:
        return 0

def join(stringList,by=None):
    if by:
        return by.join(stringList)
    else:
        return "".join(stringList)

def concat(*args):
    stringResult = ""
    try:
        for arg in args:
            stringResult += str(arg)
        return stringResult
    except:
        return stringResult

def strLower(string):
    try:
        return string.lower()
    except:
        return string

def replace(string,match,replacement):
    try:
        return string.replace(match,replacement)
    except:
        return string

def strip(string,stripOn=""):
    try:
        if stripOn:
            return string.strip(stripOn)
        return string.strip()
    except:
        return string
    
def startsWith(string, startswithString):
    try:
        return string.startswith(startswithString)
    except:
        return False
    
def endsWith(string, endswithString):
    try:
        return string.endswith(endswithString)
    except:
        return False
