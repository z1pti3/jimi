import time
import json
import uuid
import inspect

import jimi

debugSettings = jimi.settings.getSetting("debug",None)
try:
    debugEnabled = debugSettings["enabled"]
except:
    debugEnabled = False

filter = ""
buffer = []

def debug(msg,level=98,fullstack=True):
    global filter
    display = False
    if debugSettings["level"] >= level:
        display = True
        if filter:
            if filter in msg:
                display = True
            else:
                display = False
        if display:
            if fullstack:
                print()
                fullstackMsg = "{0} : {1}".format(msg,inspect.stack()[1])
                print(fullstackMsg)
            else:
                print(msg)
