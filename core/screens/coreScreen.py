import requests
import time
import types

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
            ["clear",None],
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
        print(helpers.apiCall("GET",self.apiEndpoint).text)

    def showWorker(self,args):
        self.apiEndpoint = "workers/0/"
        print(helpers.apiCall("GET",self.apiEndpoint).text)

    def setWorker(self,args):
        if len(args) == 4:
            self.apiEndpoint = "workers/"
            postData = { "action" : "settings", args[2] : args[3] }
            helpers.apiCall("POST",self.apiEndpoint,postData)

    def callStart(self,args):
        self.callWorkerStart(args)
        self.callSchedulerStart(args)

    def callWorkerStart(self,args):
        apiEndpoint = "workers/"
        helpers.apiCall("POST",apiEndpoint,{"action" : "start"})

    def callSchedulerStart(self,args):
        apiEndpoint = "scheduler/"
        helpers.apiCall("POST",apiEndpoint,{"action" : "start"})

    def end(self,args):
        raise KeyboardInterrupt

    def statsWorker(self,args):
        self.apiEndpoint = "workers/stats/"
        print(helpers.apiCall("GET",self.apiEndpoint).text)

    def showWorkerSettings(self,args):
        self.apiEndpoint = "workers/settings/"
        print(helpers.apiCall("GET",self.apiEndpoint).text)

    def showCache(self,args):
        print(cache.globalCache.getSummary())

    def clearCache(self,args):
        if len(args) == 3:
            cache.globalCache.clearCache(args[2])

    def showCluster(self,args):
        self.apiEndpoint = "cluster/"
        print(helpers.apiCall("GET",self.apiEndpoint).text)

from core import api, workers, logging, settings, helpers, screen, cache
