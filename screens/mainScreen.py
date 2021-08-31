import requests
import time
import os
import json
from pathlib import Path

class mainScreen:
    def __init__(self):
        splash()
        self.menu = screen._screen([
            ["select", None],
            ["select core",callSelectCore],
            ["time", getTime],
            ["splash", splash],
            ["version", version],
            ], "[ jimi ] >> ")
        
        self.menu.load()


from core import api, workers, logging, settings, helpers, screen, auth

from screens import coreScreen


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
def getTime(ans):
    print(int(time.time()))

def callSelectCore(args):
    screen = coreScreen.selectCore()

