import time
import json
import os
from pathlib import Path
import importlib
import requests
import zipfile
import shutil

import jimi

# Initialize 
dbCollectionName = "plugins"

# Model Class
class _plugin(jimi.db._document):
    name = str()
    enabled = bool()
    installed = bool()
    version = float()
    manifest = dict()

    _dbCollection = jimi.db.db[dbCollectionName]

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
                result.append(jimi.helpers.jsonToClass(_class(),jsonItem))
            else:
                if jimi.logging.debugEnabled:
                    jimi.logging.debug("Error unable to locate plugin class, pluginName={0}".format(jsonItem["name"]))
        return result

    def loadManifest(self):
        if os.path.isfile(str(Path("plugins/{0}/{0}.json".format(self.name)))):
            with open(str(Path("plugins/{0}/{0}.json".format(self.name))), "r") as f:
                self.manifest = json.load(f)
            self.processManifest()
            self.update(["manifest"])
            return True
        return False
    
    def processManifest(self):
        objectTypes = ["collections","triggers","actions"]
        for objectType in objectTypes:
            for objectName, objectValue in self.manifest[objectType].items():
                try:
                    model = jimi.model._model().getAsClass(query={"name" : objectName, "location" : "plugins.{0}.{1}".format(self.name,objectValue["class_location"]) })[0]
                    objectValue["class_id"] = model._id
                    model.manifest = objectValue
                    model.update(["manifest"])
                except IndexError:
                    pass

    def installHandler(self):
        self.installHeader()
        result = self.install()
        self.installFooter()
        self.loadManifest()
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
            self.loadManifest()

    def upgradeHeader(self,LatestPluginVersion):
        jimi.logging.debug("Starting plugin upgrade, pluginName={0}".format(self.name),-1)

    def upgrade(self,LatestPluginVersion):
        pass

    def upgradeFooter(self,LatestPluginVersion):
        self.version =  LatestPluginVersion
        self.update(["version"])
        jimi.logging.debug("Plugin upgrade completed, pluginName={0}".format(self.name),-1)

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

# API
if jimi.api.webServer:
    if not jimi.api.webServer.got_first_request:
        @jimi.api.webServer.route(jimi.api.base+"plugins/<pluginName>/installed/", methods=["GET"])
        @jimi.auth.adminEndpoint
        def pluginInstalled(pluginName):
            result = { "installed" : False }
            plugins = _plugin().query(jimi.api.g.sessionData,query={ "name" : pluginName })["results"]
            if len(plugins) == 1:
                plugins = plugins[0]
                if plugins["installed"]:
                    result = { "installed" : True }
            return result, 200

        @jimi.api.webServer.route(jimi.api.base+"plugins/<pluginName>/valid/", methods=["GET"])
        @jimi.auth.adminEndpoint
        def pluginValid(pluginName):
            result = { "valid" : False }
            plugins = os.listdir("plugins")
            for plugin in plugins:
                if plugin == pluginName:
                    result = { "valid" : True }
            return result, 200

        @jimi.api.webServer.route(jimi.api.base+"plugins/<pluginName>/", methods=["GET"])
        @jimi.auth.adminEndpoint
        def getPlugin(pluginName):
            result = {}
            result["results"] = []
            plugins = _plugin().query(jimi.api.g.sessionData,query={ "name" : pluginName })["results"]
            if len(plugins) == 1:
                result["results"] = plugins
            if result["results"]:
                return result, 200
            else:
                return { }, 404

        if jimi.api.webServer.name == "jimi_core":
            @jimi.api.webServer.route(jimi.api.base+"plugins/<pluginName>/", methods=["POST"])
            @jimi.auth.systemEndpoint
            def updatePlugin(pluginName):
                data = json.loads(jimi.api.request.data)
                if data["action"] == "install" or data["action"] == "uninstall" or data["action"] == "upgrade":
                    pluginClass = loadPluginClass(pluginName)
                    if pluginClass:
                        plugins = _plugin().query(jimi.api.g.sessionData,query={ "name" : pluginName })["results"]
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

            @jimi.api.webServer.route(jimi.api.base+"plugins/<pluginName>/install/", methods=["POST"])
            @jimi.auth.adminEndpoint
            def installPluginFile(pluginName):
                f = jimi.api.request.files['file']
                filename = str(Path("data/temp/{0}.jimiPlugin".format(pluginName)))
                if not jimi.helpers.safeFilepath(filename,"plugins"):
                    return {}, 403
                f.save(filename)
                with zipfile.ZipFile(filename, 'r') as zip_ref:
                    repoFolder = zip_ref.namelist()[0]
                    zip_ref.extractall(str(Path("data/temp")))
                tempFilename = str(Path("data/temp/{0}".format(repoFolder)))
                if not jimi.helpers.safeFilepath(tempFilename,"data/temp"):
                    return {},403
                # Merge .zip contents into plugin
                for root, dirs, files in os.walk(tempFilename, topdown=False):
                    for _file in files:
                        if "__pycache__" not in root and ".git" not in root:
                            src_filename = str(Path(os.path.join(root, _file)))
                            dest_filename = src_filename.replace(tempFilename, str(Path("plugins/{0}/".format(pluginName))), 1)
                            if not jimi.helpers.safeFilepath(dest_filename:
                                return {},403
                            if os.path.isfile(dest_filename):
                                os.remove(dest_filename)
                            shutil.move(src_filename,dest_filename)
                shutil.rmtree(tempFilename)
                os.remove(filename)
                return {}, 200

        if jimi.api.webServer.name == "jimi_web":
            @jimi.api.webServer.route(jimi.api.base+"plugins/store/get/", methods=["GET"])
            @jimi.auth.adminEndpoint
            def installPluginFromRemoteStore():
                repo = jimi.api.request.args.get("githubRepo")
                pluginName = jimi.api.request.args.get("pluginName")

                # Get manifest from github repo
                response = requests.get("https://raw.githubusercontent.com/{0}/master/{1}.json".format(repo,pluginName), timeout=60)
                if response.status_code == 200:
                    manifest = json.loads(response.text)

                    # Download latest repo files
                    with requests.get("https://github.com/{0}/archive/master.zip".format(repo), stream=True, timeout=60) as r:
                        r.raise_for_status()
                        tempFilename = str(Path("data/temp/{0}.zip".format( manifest["name"])))
                        if not jimi.helpers.safeFilepath(tempFilename,"data/temp"):
                            return {}, 403
                        with open(tempFilename, 'wb') as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                f.write(chunk)

                    # Send latest repo files to master
                    headers = { "X-api-token" : jimi.api.g.sessionToken }
                    url = jimi.cluster.getMaster()
                    apiEndpoint = "plugins/{0}/install/".format(manifest["name"])
                    with open(tempFilename, 'rb') as f:
                        response = requests.post("{0}{1}{2}".format(url,jimi.api.base,apiEndpoint), headers=headers, files={"file" : f.read() }, timeout=60)
                    os.remove(tempFilename)
                    return json.loads(response.text), 200
                else:
                    return {}, 404
                return {}, 200
            

def load():
    updatePluginDB()
    loadPluginAPIExtensions()
    loadPluginFunctionExtensions()

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
    classID = jimi.model._model().query(query={"className" : "_plugin" })["results"][0]["_id"]
    listedPlugins = _plugin().query()["results"]
    plugins = os.listdir("plugins")
    for plugin in plugins:
        dbplugin = [ x for x in listedPlugins if x["name"] == plugin ]
        if not dbplugin:
            pluginClass = loadPluginClass(plugin)
            if pluginClass:
                newPlugin = pluginClass()
                newPlugin.name = plugin
                newPlugin.classID = classID
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
            jimi.api.webServer.register_blueprint(mod.pluginPages,url_prefix='/plugin')

def loadPluginFunctionExtensions():
    plugins = os.listdir("plugins")
    for plugin in plugins:
        if os.path.isdir(Path("plugins/{0}/functions".format(plugin))):
            listedFunctionFiles = os.listdir(Path("plugins/{0}/functions".format(plugin)))
            for listedFunctionFile in listedFunctionFiles:
                if listedFunctionFile[-3:] == ".py":                
                    mod = importlib.import_module("plugins.{0}.functions.{1}".format(plugin,listedFunctionFile[:-3]))
                    for func in dir(mod):
                        if func.startswith("__") == False and func.endswith("__") == False:
                            jimi.function.systemFunctions[func] = getattr(mod, func) 

# Cleans all object references for non-existent plugin models
def cleanPluginDB():
    pass