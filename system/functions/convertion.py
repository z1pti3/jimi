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
    return string.lower()

def upper(string):
    return string.upper()

def toJson(string):
    return json.loads(string)

def fromJson(j,indent=False):
    if indent:
       return "\"{0}\"".format(json.dumps(j,indent = 3))
    return "\"{0}\"".format(json.dumps(j))

def jsontoHtml(json_obj,wrap=False):
    if wrap:
        conversion = f"{{{json_obj}}}"
        return json2html.convert(json = conversion )
    return json2html.convert(json = json_obj )
