import json

def strToInt(string):
    return int(string)

def strToFloat(string):
    return float(string)

def strToBool(string):
    return bool(string)

def intToStr(integer):
    return str(integer)

def lower(string):
    return string.lower()

def upper(string):
    return string.upper()

def toJson(string):
    return json.loads(string)

def fromJson(j):
    return "\"{0}\"".format(json.dumps(j))