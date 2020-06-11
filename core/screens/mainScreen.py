import requests
import time
import os
import json
from pathlib import Path

class mainScreen:
    def __init__(self):
        splash()
        self.menu = screen._screen([
            ["list", None],
            ["list workers",callWorkerAPI],
            ["list conduct",callClassAPI],
            ["list trigger",callClassAPI],
            ["list action",callClassAPI],
            ["list model",callClassAPI],
            ["list user",listUsers],
            ["list group",listGroups],
            ["list plugins",listPlugins],
            ["select", None],
            ["select conduct",callSelectClass],
            ["select trigger",callSelectClass],
            ["select action",callSelectClass],
            ["select worker",callSelectWorker],
            ["select model",callSelectClass],
            ["select user",callSelectClass],
            ["select group",callSelectClass],
            ["select core",callSelectCore],
            ["time", getTime],
            ["debug", setDebugLevel],
            ["debug filter", setDebugFilter],
            ["splash", splash],
            ["version", version],
            ], "[ jimi ] >> ")

        # Dynamic loading of plugins
        self.menu.items.append(["select plugin", None])
        apiEndpoint = "plugins/"
        for plugin in json.loads(helpers.apiCall("GET",apiEndpoint).text)["results"]:
            self.menu.items.append(["select plugin {0}".format(plugin["name"]),callSelectPlugin])
        
        self.menu.load()


from core import api, workers, logging, settings, helpers, screen

from core.screens import classScreen, coreScreen, workerScreen, pluginScreen


def splash(args=None):
    print("""
           8 8888            8 8888                    ,8.       ,8.                     8 8888 
           8 8888            8 8888                   ,888.     ,888.                    8 8888 
           8 8888            8 8888                  .`8888.   .`8888.                   8 8888 
           8 8888            8 8888                 ,8.`8888. ,8.`8888.                  8 8888 
           8 8888            8 8888                ,8'8.`8888,8^8.`8888.                 8 8888 
           8 8888            8 8888               ,8' `8.`8888' `8.`8888.                8 8888 
88.        8 8888            8 8888              ,8'   `8.`88'   `8.`8888.               8 8888 
`88.       8 888'            8 8888             ,8'     `8.`'     `8.`8888.              8 8888 
  `88o.    8 88'             8 8888            ,8'       `8        `8.`8888.             8 8888 
    `Y888888 '               8 8888           ,8'         `         `8.`8888.            8 8888 

       
            _______ __              __        ______                    __   __    
            |    ___|__|.----.-----.|  |_     |   __ \.----.-----.---.-.|  |_|  |--.
            |    ___|  ||   _|__ --||   _|    |   __ <|   _|  -__|  _  ||   _|     |
            |___|   |__||__| |_____||____|    |______/|__| |_____|___._||____|__|__|
                                                                                    
    """)

def version(args=None):
    from system import install
    print("Version:{0}".format(install.installedVersion()))

def getPluginScreens():
    pluginScreenClasses = []
    # Check Plugins Second
    plugins = os.listdir("plugins")
    for plugin in plugins:
        # Checking if the main plugin screen file exists
        if os.path.exists(Path("plugins/{0}/screens/{1}Screen.py".format(plugin,plugin))):
            pluginScreenClasses.append(plugin)
    return pluginScreenClasses

def loadPluginMenu(args):
    plugins = os.listdir("plugins")
    for plugin in plugins:
        try:
            mod = __import__("plugins.{0}.screens.{1}Screen".format(plugin,plugin), fromlist=["{0}Screen".format(plugin)])
            class_ = getattr(mod, "{0}Screen".format(plugin))
            pluginScreen = class_()
        except ModuleNotFoundError:
            pass
        except AttributeError:
            pass

# SCREENS
def setDebugLevel(args):
    if len(args) == 2:
        settings.config["debug"]["level"] = int(args[1])

def setDebugFilter(args):
    if len(args) == 3:
        logging.filter = args[2]
    else:
        logging.filter = ""

def getTime(ans):
    print(int(time.time()))

def callWorkerAPI(args):
    if len(args) == 2:
        apiEndpoint = "workers/"
        if args[0] == "list":
            print(helpers.apiCall("GET",apiEndpoint).text)

def callClassAPI(args):
    if len(args) == 2:
        apiEndpoint = "models/{0}/all/".format(args[1])
        if args[0] == "list":
            print(helpers.apiCall("GET",apiEndpoint).text)

def callSelectClass(args):
    if len(args) == 3:
        screen = classScreen.selectClass(args[1],args[2])

def callSelectWorker(args):
    if len(args) == 3:
        screen = workerScreen.selectWorker(args[2])

def callSelectCore(args):
    screen = coreScreen.selectCore()

def callSelectPlugin(args):
    if len(args) == 3:
        screen = pluginScreen.selectPlugin(args[2])

def listPlugins(args):
    if len(args) == 2:
        apiEndpoint = "plugins/"
        if args[0] == "list":
            print(helpers.apiCall("GET",apiEndpoint).text)

def listUsers(args):
    if len(args) == 2:
        apiEndpoint = "user/"
        if args[0] == "list":
            print(helpers.apiCall("GET",apiEndpoint).text)

def listGroups(args):
    if len(args) == 2:
        apiEndpoint = "group/"
        if args[0] == "list":
            print(helpers.apiCall("GET",apiEndpoint).text)

