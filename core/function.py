import os
from pathlib import Path
import importlib

systemFunctions = {}

def load():
    global systemFunctions
    listedFunctionFiles = os.listdir(str(Path("system/functions")))
    for listedFunctionFile in listedFunctionFiles:
        if listedFunctionFile[-3:] == ".py":
            mod = importlib.import_module("system.functions.{0}".format(listedFunctionFile[:-3]))
            for func in dir(mod):
                if func.startswith("__") == False and func.endswith("__") == False:
                    systemFunctions[func] = getattr(mod, func) 

