import requests
import time

class selectWorker:
    model = None
    workerID = None
    apiEndpoint = None

    def __init__(self,workerID):
        self.workerID = workerID
        self.apiEndpoint = "workers/{0}/".format(self.workerID)

        # Confirms that the requested model and objectID are valid
        url = "{0}/{1}".format(helpers.apiURL,self.apiEndpoint)
        if requests.get(url).status_code != 200:
            print("Invalid workerID!")
            return
        
        self.menu = screen._screen([
            ["show", self.show],
            ["kill", self.kill],
            ["end", self.end],
            ], "[ worker:{0} ] >> ".format(self.workerID))
        self.menu.load()

    def show(self,args):
        print(helpers.apiCall("GET",self.apiEndpoint).text)

    def kill(self,args):
        helpers.apiCall("DELETE",self.apiEndpoint)

    def end(self,args):
        raise KeyboardInterrupt

from core import api, workers, logging, settings, helpers, screen
