import requests
import time
import types
import random

class selectCore:
    def __init__(self):
        
        self.menu = screen._screen([
            ["reset", None],
            ["reset root", self.resetRoot],
            ["clear",None],
            ["clear startCheck",self.clearStartCheck],
            ["end", self.end],
            ], "[ core ] >> ")
        self.menu.load()

    def end(self,args):
        raise KeyboardInterrupt

    def clearStartCheck(self,args):
        from system import install
        install.resetTriggers()
        print("All triggers reset!")
    
    def resetRoot(self,args):
        from core import auth
        from system import install
        rootUser = auth._user().getAsClass(query={ "username" : "root" })
        if len(rootUser) == 1:
            rootUser = rootUser[0]
            rootPass = install.randomString(30)
            rootUser.setAttribute("passwordHash",rootPass)
            rootUser.enabled = True
            rootUser.failedLoginCount = 0
            rootUser.update(["passwordHash","enabled","failedLoginCount"])
            logging.debug("Root user password reset! Password is: {}".format(rootPass),-1)

from core import api, workers, logging, settings, helpers, screen, cache, auth
