def contains(string,contents):
    return contents in string

def split(string,spliton,position):
    return string.split(spliton)[position]

def strCount(string,searchString):
    return string.count(searchString)

def join(stringList,by=None):
    if by:
        return by.join(stringList)
    else:
        return "".join(stringList)

def concat(*args):
    stringResult = 0
    for arg in args:
        stringResult += arg
    return stringResult

def strLower(string):
    return string.lower()