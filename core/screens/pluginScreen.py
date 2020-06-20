import requests
import time
import json

class selectPlugin:
    def __init__(self,pluginName):
        self.pluginName = pluginName

        self.menu = screen._screen([
            ["end", self.end],
            ], "[ plugin:{0} ] >> ".format(self.pluginName))

        # Check plugin exists
        self.apiEndpoint = "plugins/{0}/valid/".format(self.pluginName)
        response = helpers.apiCall("GET",self.apiEndpoint,token=auth.generateSystemSession())
        response = json.loads(response.text)
        if response["valid"] == False:
            return

        # Get plugin installed status
        self.apiEndpoint = "plugins/{0}/installed/".format(self.pluginName)
        response = helpers.apiCall("GET",self.apiEndpoint,token=auth.generateSystemSession())
        response = json.loads(response.text)
        if response["installed"] == True:
            self.menu.items.append(["show", self.show])
            self.menu.items.append(["uninstall", self.uninstall])
            self.menu.items.append(["upgrade", self.upgrade])
        else:
            self.menu.items.append(["install", self.install])

        self.menu.load()

    def end(self,args):
        raise KeyboardInterrupt

    def show(self,args):
        self.apiEndpoint = "plugins/{0}/".format(self.pluginName)
        print(helpers.apiCall("GET",self.apiEndpoint,token=auth.generateSystemSession()).text)

    def install(self,args):
        self.apiEndpoint = "plugins/{0}/".format(self.pluginName)
        postAction={ "action" : "install" }
        helpers.apiCall("POST",self.apiEndpoint,postAction,token=auth.generateSystemSession())
        raise KeyboardInterrupt

    def uninstall(self,args):
        self.apiEndpoint = "plugins/{0}/".format(self.pluginName)
        postAction={ "action" : "uninstall" }
        helpers.apiCall("POST",self.apiEndpoint,postAction,token=auth.generateSystemSession())
        raise KeyboardInterrupt

    def upgrade(self,args):
        self.apiEndpoint = "plugins/{0}/".format(self.pluginName)
        postAction={ "action" : "upgrade" }
        helpers.apiCall("POST",self.apiEndpoint,postAction,token=auth.generateSystemSession())

    def showWorkerSettings(self,args):
        self.apiEndpoint = "workers/settings/"
        helpers.apiCall("GET",self.apiEndpoint,token=auth.generateSystemSession())

from core import api, logging, settings, plugin, screen, helpers, auth
