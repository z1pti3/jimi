import requests
import time

class selectClass:
    model = None
    objectID = None
    apiEndpoint = None

    def __init__(self,model,objectID):
        self.model = model
        self.objectID = objectID
        self.apiEndpoint = "models/{0}/{1}/".format(self.model,self.objectID)

        # Confirms that the requested model and objectID are valid
        if helpers.apiCall("GET",self.apiEndpoint,token=auth.generateSystemSession()).status_code != 200:
            print("Invalid objectID!")
            return
        
        self.menu = screen._screen([
            ["show", self.show],
            ["set", self.setValue],
            ["delete", self.delete],
            ["end", self.end],
            ], "[ {0}:{1} ] >> ".format(self.model,self.objectID))
        self.menu.load()

    def show(self,args):
        print(helpers.apiCall("GET",self.apiEndpoint,token=auth.generateSystemSession()).text)

    def delete(self,args):
        helpers.apiCall("DELETE",self.apiEndpoint,token=auth.generateSystemSession())

    def setValue(self,args):
        if len(args) > 2:
            value = helpers.typeCast(" ".join(args[2:]))
            data = { args[1] : value }
            helpers.apiCall("POST",self.apiEndpoint,{"action" : "update", "data" : data},token=auth.generateSystemSession())

    def end(self,args):
        raise KeyboardInterrupt

from core import api, workers, logging, settings, helpers, screen, auth
