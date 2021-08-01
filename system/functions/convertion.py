import json
from json2html import *

def strToInt(string):
    return int(string)

def strToFloat(string):
    return float(string)

def strToBool(string):
    return bool(string)

def intToStr(integer):
    return str(integer)

def lower(string):
    try:
        return string.lower()
    except:
        return string

def upper(string):
    try:
        return string.upper()
    except:
        return string

def toJson(string):
    try:
        return json.loads(string)
    except:
        return string

def fromJson(j,indent=False):
    try:
        if indent:
            return "\"{0}\"".format(json.dumps(j,indent = 3))
        return "\"{0}\"".format(json.dumps(j))
    except:
        return j

def jsontoHtml(json_obj,wrap=False):
    if wrap:
        conversion = f"{{{json_obj}}}"
        return json2html.convert(json = conversion )
    return json2html.convert(json = json_obj )
