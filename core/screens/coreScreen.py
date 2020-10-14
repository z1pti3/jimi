import requests
import time
import types
import random

class selectCore:
    def __init__(self):
        
        self.menu = screen._screen([
            ["show", self.show],
            ["show scheduler", self.showScheduler],
            ["show worker", self.showWorker],
            ["show worker settings", self.showWorkerSettings],
            ["show cache",self.showCache],
            ["show cluster",self.showCluster],
            ["start", self.callStart],
            ["start worker", None],
            ["start worker thread", self.callWorkerStart],
            ["start scheduler", None],
            ["start scheduler thread", self.callSchedulerStart],
            ["stats",None],
            ["stats worker",self.statsWorker],
            ["set",None],
            ["set worker",None],
            ["set worker",self.setWorker],
            ["reload", self.reload],
            ["reset", None],
            ["reset root", self.resetRoot],
            ["clear",None],
            ["clear startCheck",self.clearStartCheck],
            ["clear cache",self.clearCache],
            ["end", self.end],
            ], "[ core ] >> ")
        self.menu.load()

    def reload(self,args):
        helpers.reload()

    def show(self,args):
        self.showWorker(args)
        self.showScheduler(args)

    def showScheduler(self,args):
        self.apiEndpoint = "scheduler/"
        print(helpers.apiCall("GET",self.apiEndpoint,token=auth.generateSystemSession()).text)

    def showWorker(self,args):
        self.apiEndpoint = "workers/0/"
        print(helpers.apiCall("GET",self.apiEndpoint,token=auth.generateSystemSession()).text)

    def setWorker(self,args):
        if len(args) == 4:
            self.apiEndpoint = "workers/"
            postData = { "action" : "settings", args[2] : args[3] }
            helpers.apiCall("POST",self.apiEndpoint,postData,token=auth.generateSystemSession())

    def callStart(self,args):
        self.callWorkerStart(args)
        self.callSchedulerStart(args)

    def callWorkerStart(self,args):
        apiEndpoint = "workers/"
        helpers.apiCall("POST",apiEndpoint,{"action" : "start"},token=auth.generateSystemSession())

    def callSchedulerStart(self,args):
        apiEndpoint = "scheduler/"
        helpers.apiCall("POST",apiEndpoint,{"action" : "start"},token=auth.generateSystemSession())

    def end(self,args):
        raise KeyboardInterrupt

    def statsWorker(self,args):
        self.apiEndpoint = "workers/stats/"
        print(helpers.apiCall("GET",self.apiEndpoint,token=auth.generateSystemSession()).text)

    def showWorkerSettings(self,args):
        self.apiEndpoint = "workers/settings/"
        print(helpers.apiCall("GET",self.apiEndpoint,token=auth.generateSystemSession()).text)

    def showCache(self,args):
        print(cache.globalCache.getSummary())

    def clearCache(self,args):
        if len(args) == 3:
            cache.globalCache.clearCache(args[2])
            print("Cache Cleared!")

    def showCluster(self,args):
        self.apiEndpoint = "cluster/"
        print(helpers.apiCall("GET",self.apiEndpoint,token=auth.generateSystemSession()).text)

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
            rootUser.update(["passwordHash"])
            logging.debug("Root user password reset! Password is: {}".format(rootPass),-1)

from core import api, workers, logging, settings, helpers, screen, cache, auth
