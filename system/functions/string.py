def contains(string,contents):
    return string in contents

def split(string,spliton,position):
    return string.split(spliton)[position]

def strCount(string,searchString):
    return string.count(searchString)

def join(stringList,by=None):
    if by:
        return by.join(stringList)
    else:
        return "".join(stringList)

def strLower(string):
    return string.lower()