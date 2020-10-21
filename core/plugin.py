import time
import json
import os
from pathlib import Path

from core import db

# Initialize 
dbCollectionName = "plugins"

# Model Class
class _plugin(db._document):
    name = str()
    enabled = bool()
    installed = bool()
    version = float()

    _dbCollection = db.db[dbCollectionName]

    # Override parent new to include name var, parent class new run after class var update
    def new(self,name):
        self.name = name
        self.acl = { "ids":[ { "accessID":"0","delete": True,"read": True,"write": True } ] }
        return super(_plugin, self).new()

    # Override parent to support plugin dynamic classes
    def loadAsClass(self,jsonList,sessionData=None):
        result = []
        # Loading json data into class
        for jsonItem in jsonList:
            _class = loadPluginClass(jsonItem["name"])
            if _class:
                result.append(helpers.jsonToClass(_class(),jsonItem))
            else:
                logging.debug("Error unable to locate plugin class, pluginName={0}".format(jsonItem["name"]))
        return result

    def installHandler(self):
        self.installHeader()
        result = self.install()
        self.installFooter()
        if result:
            self.enabled = True
            self.installed = True
            self.update(["enabled","installed"])

    def installHeader(self):
        pass

    def install(self):
        return False

    def installFooter(self):
        pass

    def upgradeHandler(self):
        LatestPluginVersion = loadPluginClass(self.name).version
        if self.version < LatestPluginVersion:
            self.upgradeHeader(LatestPluginVersion)
            self.upgrade(LatestPluginVersion)
            self.upgradeFooter(LatestPluginVersion)

    def upgradeHeader(self,LatestPluginVersion):
        logging.debug("Starting plugin upgrade, pluginName={0}".format(self.name),-1)

    def upgrade(self,LatestPluginVersion):
        pass

    def upgradeFooter(self,LatestPluginVersion):
        self.version =  LatestPluginVersion
        self.update(["version"])
        logging.debug("Plugin upgrade completed, pluginName={0}".format(self.name),-1)

    def uninstallHandler(self):
        self.enabled = False
        self.installed = False
        self.uninstallHeader()
        result = self.uninstall()
        self.uninstallFooter()
        self.update(["enabled","installed"])

    def uninstallHeader(self):
        pass

    def uninstall(self):
        return False

    def uninstallFooter(self):
        pass


from core import api, logging, model, helpers

# API
if api.webServer:
    if not api.webServer.got_first_request:
        @api.webServer.route(api.base+"plugins/<pluginName>/installed/", methods=["GET"])
        def pluginInstalled(pluginName):
            result = { "installed" : False }
            plugins = _plugin().query(api.g.sessionData,query={ "name" : pluginName })["results"]
            if len(plugins) == 1:
                plugins = plugins[0]
                if plugins["installed"]:
                    result = { "installed" : True }
            return result, 200

        @api.webServer.route(api.base+"plugins/<pluginName>/valid/", methods=["GET"])
        def pluginValid(pluginName):
            result = { "valid" : False }
            plugins = os.listdir("plugins")
            for plugin in plugins:
                if plugin == pluginName:
                    result = { "valid" : True }
            return result, 200

        @api.webServer.route(api.base+"plugins/", methods=["GET"])
        def getPlugins():
            result = {}
            result["results"] = []
            plugins = os.listdir("plugins")
            for plugin in plugins:
                result["results"].append({ "name" : plugin, "location" : "plugins/{0}".format(plugin) })
            return result, 200

        @api.webServer.route(api.base+"plugins/<pluginName>/", methods=["GET"])
        def getPlugin(pluginName):
            result = {}
            result["results"] = []
            plugins = _plugin().query(api.g.sessionData,query={ "name" : pluginName })["results"]
            if len(plugins) == 1:
                result["results"] = plugins
            if result["results"]:
                return result, 200
            else:
                return { }, 404

        @api.webServer.route(api.base+"plugins/<pluginName>/", methods=["POST"])
        def updatePlugin(pluginName):
            data = json.loads(api.request.data)
            if data["action"] == "install" or data["action"] == "uninstall" or data["action"] == "upgrade":
                pluginClass = loadPluginClass(pluginName)
                if pluginClass:
                    plugins = _plugin().query(api.g.sessionData,query={ "name" : pluginName })["results"]
                    if len(plugins) == 1:
                        plugins = plugins[0]
                        if data["action"] == "install":
                            installPlugin =  pluginClass().get(plugins["_id"])
                            installPlugin.installHandler()
                            return { }, 200
                        elif data["action"] == "uninstall":
                            uninstallPlugin =  pluginClass().get(plugins["_id"])
                            uninstallPlugin.uninstallHandler()
                            return { }, 200
                        elif data["action"] == "upgrade":
                            upgradePlugin =  pluginClass().get(plugins["_id"])
                            upgradePlugin.upgradeHandler()
                            return { }, 200
            return { }, 404

def loadPluginClass(pluginName):
    try:
        mod = __import__("plugins.{0}.{0}".format(pluginName), fromlist=["_{0}".format(pluginName)])
        class_ = getattr(mod, "_{0}".format(pluginName))
        return class_
    except ModuleNotFoundError:
        pass
    except AttributeError:
        pass
    return None

# Load / Delete valid / non-valid plugins
def updatePluginDB():
    listedPlugins = _plugin().query()["results"]
    plugins = os.listdir("plugins")
    for plugin in plugins:
        dbplugin = [ x for x in listedPlugins if x["name"] == plugin ]
        if not dbplugin:
            pluginClass = loadPluginClass(plugin)
            if pluginClass:
                newPlugin = pluginClass()
                newPlugin.name = plugin
                newPluginID = newPlugin._dbCollection.insert_one(newPlugin.parse()).inserted_id
                newPlugin = pluginClass().get(newPluginID)
                if newPlugin.installed != True:
                    newPlugin.installHandler()
                elif newPlugin.version < pluginClass.version:
                    loadedPlugin.upgradeHandler()
        else:
            dbplugin = dbplugin[0]
            pluginClass = loadPluginClass(plugin)
            loadedPlugin =  pluginClass().get(dbplugin["_id"])
            if loadedPlugin.installed != True:
                loadedPlugin.installHandler()
            elif loadedPlugin.version < pluginClass.version:
                loadedPlugin.upgradeHandler()
            del listedPlugins[listedPlugins.index(dbplugin)]
    for listedPlugin in listedPlugins:
        plugins = _plugin().api_delete(query={ "name" : listedPlugin["name"] })

def loadPluginAPIExtensions():
    plugins = os.listdir("plugins")
    for plugin in plugins:
        if os.path.isfile(Path("plugins/{0}/api/{0}.py".format(plugin))):
            mod = __import__("plugins.{0}.api.{0}".format(plugin), fromlist=["pluginPages"])
            api.webServer.register_blueprint(mod.pluginPages,url_prefix='/plugin')

# Cleans all object references for non-existent plugin models
def cleanPluginDB():
    pass