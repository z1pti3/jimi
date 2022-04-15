from sys import modules
import time
import json
import os
import subprocess
from pathlib import Path
import importlib
import requests
import zipfile
import shutil
import re

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
        installPluginPythonRequirements(self.name)

    def install(self):
        return False

    def installFooter(self):
        pass

    def upgradeHandler(self,LatestPluginVersion):
        self.upgradeHeader(LatestPluginVersion)
        self.upgrade(LatestPluginVersion)
        self.upgradeFooter(LatestPluginVersion)
        self.loadManifest()

    def upgradeHeader(self,LatestPluginVersion):
        jimi.logging.debug("Starting plugin upgrade, pluginName={0}".format(self.name),-1)
        installPluginPythonRequirements(self.name)

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

loadedPluginPages = []

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

            @jimi.api.webServer.route(jimi.api.base+"plugins/install_dependencies/<pluginName>/", methods=["GET"])
            @jimi.auth.adminEndpoint
            def installPluginDependencies(pluginName):
                installPluginPythonRequirements(pluginName)
                return { }, 200

            @jimi.api.webServer.route(jimi.api.base+"plugins/<pluginName>/install/", methods=["POST"])
            @jimi.auth.adminEndpoint
            def installPluginFile(pluginName):
                jimi.logging.debug("Info: Starting plugin install. pluginName={0}".format(pluginName),-1)
                # Some basic checks on pluginName
                if re.match(r"[\.\\\/]+",pluginName):
                    return { "message" : "Failed" }, 403
                # Get latest plugin
                f = jimi.api.request.files['file']
                filename = str(Path("data/temp/{0}.jimiPlugin".format(pluginName)))
                if not jimi.helpers.safeFilepath(filename,"data/temp"):
                    return { "message" : "Failed" }, 403
                f.save(filename)
                with zipfile.ZipFile(filename, 'r') as zip_ref:
                    repoFolder = zip_ref.namelist()[0]
                    zip_ref.extractall(str(Path("data/temp")))
                tempFilename = str(Path("data/temp/{0}".format(repoFolder)))
                if not jimi.helpers.safeFilepath(tempFilename,"data/temp"):
                    return { "message" : "Failed" },403
                # Merge .zip contents into plugin
                for root, dirs, files in os.walk(tempFilename, topdown=False):
                    for _file in files:
                        if "__pycache__" not in root and ".git" not in root:
                            src_filename = str(Path(os.path.join(root, _file)))
                            dest_filename = src_filename.replace(tempFilename, str(Path("plugins/{0}/".format(pluginName))), 1)
                            if not jimi.helpers.safeFilepath(dest_filename):
                                return { "message" : "Failed" },403
                            if os.path.isfile(dest_filename):
                                os.remove(dest_filename)
                            os.makedirs(os.path.dirname(dest_filename), exist_ok=True)
                            shutil.move(src_filename,dest_filename)
                shutil.rmtree(tempFilename)
                os.remove(filename)

                # Install / update plugin ( will need to be converted to manifest one day )
                manifestFile = str(Path("plugins/{0}/{0}.json".format(pluginName)))
                pluginsFolder = str(Path("plugins/{0}".format(pluginName)))
                if not jimi.helpers.safeFilepath(manifestFile,pluginsFolder) or not jimi.helpers.safeFilepath(pluginsFolder):
                    return { "message" : "Failed" },403
                with open(manifestFile, "r") as manifest_file:
                    manifest = json.load(manifest_file)
                if pluginName != manifest["name"]:
                    return { "message" : "Failed" }, 403
                pluginVersion = manifest["version"]

                plugin = _plugin().getAsClass(query={"name" : pluginName})
                installType = -1
                if len(plugin) > 0:
                    plugin = plugin[0]
                    if plugin.version < pluginVersion and plugin.installed:
                        installType = 1
                        jimi.logging.debug("Info: Upgrading plugin. pluginName={0}, currentVersion={1}, newVersion={2}".format(pluginName,plugin.version,pluginVersion),-1)
                        plugin.upgradeHandler(pluginVersion)
                    elif plugin.installed:
                        jimi.logging.debug("Info: Plugin already up to date. pluginName={0}, currentVersion={1}, newVersion={2}".format(pluginName,plugin.version,pluginVersion),-1)
                else:
                    classID = jimi.model._model(False).query(query={"className" : "_plugin" })["results"][0]["_id"]
                    pluginClass = loadPluginClass(pluginName)
                    newPlugin = pluginClass()
                    newPlugin.name = pluginName
                    newPlugin.classID = classID
                    newPlugin.acl = { "ids":[ { "accessID":"0","delete": True,"read": True,"write": True } ] }
                    newPluginID = newPlugin._dbCollection.insert_one(newPlugin.parse()).inserted_id
                    newPlugin = pluginClass().get(newPluginID)
                    if newPlugin.installed != True:
                        newPlugin.installHandler()
                    jimi.logging.debug("Info: Installing new plugin. pluginName={0}, version={1}".format(pluginName,pluginVersion),-1)

                # Apply system updates
                if installType > -1:
                    jimi.system.regenerateSystemFileIntegrity()
                    if installType == 1:
                        module = "plugins.{0}".format(pluginName)
                        clusterMembers = jimi.cluster.getAll()
                        for clusterMember in clusterMembers:
                            headers = { "x-api-token" : jimi.auth.generateSystemSession(expiry=300) }
                            requests.get("{0}{1}system/update/{2}/".format(clusterMember,jimi.api.base,jimi.cluster.getMasterId()),headers=headers, timeout=60)
                            requests.get("{0}{1}plugins/install_dependencies/{2}/".format(clusterMember,jimi.api.base,module),headers=headers, timeout=60)
                            requests.get("{0}{1}system/reload/module/{2}/".format(clusterMember,jimi.api.base,module),headers=headers, timeout=60)

                return { "message" : "Success" }, 200

        if jimi.api.webServer.name == "jimi_web":
            from flask import Flask, request, render_template
            from web import ui

            @jimi.api.webServer.route("/plugins/", methods=["GET"])
            def pluginPages():
                userPlugins = []
                userModels = _plugin().getAsClass(sessionData=jimi.api.g.sessionData,query={ "name" : { "$in" : loadedPluginPages } },sort=[("name", 1)])
                for userModel in userModels:
                    if userModel.name in loadedPluginPages:
                        userPlugins.append({ "id" : userModel._id, "name" : userModel.name})
                return render_template("plugins.html",CSRF=jimi.api.g.sessionData["CSRF"], plugins=userPlugins)

            @jimi.api.webServer.route("/plugins/store/", methods=["GET"])
            @jimi.auth.adminEndpoint
            def store():
                # Get installed plugin list
                installedPlugins = []
                foundPlugins = jimi.plugin._plugin().getAsClass(sessionData=jimi.api.g.sessionData,query={ },sort=[("name", 1)])
                for foundPlugin in foundPlugins:
                    installedPlugins.append(foundPlugin.name)

                # Get official plugin list
                response = requests.get("https://raw.githubusercontent.com/z1pti3/jimiPlugins/main/plugins.json", timeout=60)
                if response.status_code == 200:
                    storeJson = json.loads(response.text)
                storePlugins = []
                for pluginName, pluginData in storeJson.items():
                    installed = False
                    if pluginName in installedPlugins:
                        installed = True
                    storePlugins.append({ "_id" : len(storePlugins), "name" : pluginName, "githubRepo" : pluginData["githubRepo"], "installed" : installed, "description" : pluginData["description"], "image" : pluginData["image"] })
                
                return render_template("store.html",plugins=storePlugins,CSRF=jimi.api.g.sessionData["CSRF"])

            @jimi.api.webServer.route("/plugins/store/list/", methods=["GET"])
            @jimi.auth.adminEndpoint
            def storeItem():
                repo = jimi.api.request.args.get("githubRepo")
                pluginName = jimi.api.request.args.get("pluginName")

                # Get manifest from github repo
                response = requests.get("https://raw.githubusercontent.com/{0}/master/{1}.json".format(repo,pluginName), timeout=60)
                if response.status_code == 200:
                    manifest = json.loads(response.text)
        
                return render_template("storeItem.html",manifest=ui.dictTable(manifest),CSRF=jimi.api.g.sessionData["CSRF"])

            @jimi.api.webServer.route(jimi.api.base+"plugins/store/install/", methods=["GET"])
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
                            return { "message" : "Failed" }, 403
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
                    module = "plugins.{0}".format(pluginName)
                    jimi.helpers.reloadModulesWithinPath(module)
                    refreshPluginBlueprints()
                    return json.loads(response.text), 200
                else:
                    return { "message" : "Failed" }, 404
                return { "message" : "Success" }, 200

            @jimi.api.webServer.route(jimi.api.base+"plugins/list/", methods=["GET"])
            @jimi.auth.adminEndpoint
            def getInstalledPlugins():
                userPlugins = []
                foundPlugins = jimi.plugin._plugin().getAsClass(sessionData=jimi.api.g.sessionData,query={ },sort=[("name", 1)])
                for foundPlugin in foundPlugins:
                    userPlugins.append({ "id" : foundPlugin._id, "name" : foundPlugin.name})
                return { "results"  : userPlugins }, 200

            @jimi.api.webServer.route(jimi.api.base+"plugins/store/list/", methods=["GET"])
            @jimi.auth.adminEndpoint
            def getStorePlugins():
                # Get installed plugin list
                installedPlugins = []
                foundPlugins = jimi.plugin._plugin().getAsClass(sessionData=jimi.api.g.sessionData,query={ },sort=[("name", 1)])
                for foundPlugin in foundPlugins:
                    installedPlugins.append(foundPlugin.name)

                # Get official plugin list
                response = requests.get("https://raw.githubusercontent.com/z1pti3/jimiPlugins/main/plugins.json", timeout=60)
                if response.status_code == 200:
                    storeJson = json.loads(response.text)
                storePlugins = []
                for pluginName, pluginData in storeJson.items():
                    installed = False
                    if pluginName in installedPlugins:
                        installed = True
                    storePlugins.append({ "_id" : len(storePlugins), "name" : pluginName, "githubRepo" : pluginData["githubRepo"], "installed" : installed })

                return { "results"  : storePlugins }, 200
                
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

# Dont like these, they need to be merged into the plugin class or somthing?
def loadPluginAPIExtensions():
    global loadedPluginPages
    pluginPages = []
    plugins = os.listdir("plugins")
    for plugin in plugins:
        if os.path.isfile(Path("plugins/{0}/api/{0}.py".format(plugin))):
            mod = __import__("plugins.{0}.api.{0}".format(plugin), fromlist=["pluginPages"])
            jimi.api.webServer.register_blueprint(mod.pluginPages,url_prefix='/plugin/{0}'.format(plugin))
            pluginPages.append(plugin)
    loadedPluginPages = pluginPages

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

def installPluginPythonRequirements(pluginName=None):
    if jimi.settings.getSetting("plugins","install_dependencies"):
        if pluginName:
            if os.path.isfile(Path("plugins/{0}/requirements.txt".format(pluginName))):
                p = subprocess.run(["pip3","install","-r",Path("plugins/{0}/requirements.txt".format(pluginName))])
        else:
            plugins = os.listdir("plugins")
            for plugin in plugins:
                if os.path.isfile(Path("plugins/{0}/requirements.txt".format(plugin))):
                    p = subprocess.run(["pip3","install","-r",Path("plugins/{0}/requirements.txt".format(plugin))])

def updatePluginDB():
    classID = jimi.model._model(False).query(query={"className" : "_plugin" })["results"][0]["_id"]
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
                newPlugin.acl = { "ids":[ { "accessID":"0","delete": True,"read": True,"write": True } ] }
                newPluginID = newPlugin._dbCollection.insert_one(newPlugin.parse()).inserted_id
                newPlugin = pluginClass().get(newPluginID)
                if newPlugin.installed != True:
                    newPlugin.installHandler()
                elif newPlugin.version < pluginClass.version:
                    loadedPlugin.upgradeHandler(pluginClass.version)
        else:
            dbplugin = dbplugin[0]
            pluginClass = loadPluginClass(plugin)
            if pluginClass:
                loadedPlugin =  pluginClass().get(dbplugin["_id"])
                if loadedPlugin.installed != True:
                    loadedPlugin.installHandler()
                elif loadedPlugin.version < pluginClass.version:
                    loadedPlugin.upgradeHandler(pluginClass.version)

def refreshPluginBlueprints():
    global loadedPluginPages
    pluginPages = []
    plugins = os.listdir("plugins")
    for plugin in plugins:
        if os.path.isfile(Path("plugins/{0}/web/{0}.py".format(plugin))):
            if plugin not in loadedPluginPages:
                mod = __import__("plugins.{0}.web.{0}".format(plugin), fromlist=["pluginPages"])
                jimi.api.webServer.register_blueprint(mod.pluginPages,url_prefix='/plugin/{0}'.format(plugin))
                hidden = False
                try:
                    hidden = mod.pluginPagesHidden
                except:
                    pass
                if not hidden:
                    pluginPages.append(plugin)
            else:
                pluginPages.append(plugin)
    loadedPluginPages = pluginPages