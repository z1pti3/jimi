import time
import sys
import secrets
import random
import string
from pathlib import Path
import os
import json
import logging

import jimi

# Current System Version
systemVersion = 3.133

# Initialize 
dbCollectionName = "system"

# system Class
class _system(jimi.db._document):
    name = str()
    data = dict()

    _dbCollection = jimi.db.db[dbCollectionName]

    # Blanking some non required class functions
    def new(self,name):
        result = self._dbCollection.insert_one({ "name" : name })
        return result

systemSettings = jimi.config["system"]

def installedVersion():
    systemAbout = _system().query(query={ "name" : "about" })["results"]
    systemAbout = systemAbout[0]["_id"]
    systemAbout = _system().get(systemAbout)
    return systemAbout.data["version"]

def getSecure():
    systemSecure = _system().query(query={ "name" : "secure" })["results"]
    if len(systemSecure) == 1:
        systemSecure = systemSecure[0]["_id"]
        systemSecure = _system().get(systemSecure)
        if "string" in systemSecure.data:
            return systemSecure.data["string"]
        else:
            systemSecure.data["string"] = secrets.token_hex(32)
            systemSecure.update(["data"])
            return systemSecure.data["string"]
    return None

def setup():
    systemAbout = _system().query(query={ "name" : "about" })["results"]
    if len(systemAbout) < 1:
        systemAbout = _system().new("about").inserted_id
        systemAbout = _system().get(systemAbout)
    else:
        systemAbout = systemAbout[0]["_id"]
        systemAbout = _system().get(systemAbout)

    upgrade = False
    install = True
    if "version" in systemAbout.data:
        install = False
        if systemVersion > systemAbout.data["version"]:
            upgrade = True

    if install:
        logging.info("Starting system install")
        if systemInstall():
            # Set system version number if install and/or upgrade
            systemAbout.data["version"] = systemVersion
            systemAbout.update(["data"])
            logging.info("Starting system install completed")
            sys.exit(0)
        else:
            sys.exit("Unable to complete install")
    elif upgrade:
        logging.info("Starting system upgrade")
        if systemUpgrade(systemAbout.data["version"]):
            # Set system version number if install and/or upgrade
            systemAbout.data["version"] = systemVersion
            systemAbout.update(["data"])
            logging.info("Starting system upgrade completed")
        else:
            sys.exit("Unable to complete upgrade")

    # Loading functions
    jimi.function.load()

    # Initialize plugins
    jimi.plugin.load()

# Set startCheck to 0 so that all triggers start
def resetTriggers():
    triggers = jimi.trigger._trigger(False).query(query={"startCheck" : { "$gt" : 0}})["results"]
    for triggerJson in triggers:
        triggerClass = jimi.trigger._trigger().get(triggerJson["_id"])
        triggerClass.startCheck = 0
        triggerClass.attemptCount = 0
        triggerClass.update(["startCheck","attemptCount"])

def randomString(length=12):
    charSet = string.ascii_letters + string.digits
    return ''.join([random.choice(charSet) for i in range(length)])

def processSystemManifest(manifest):
    objectTypes = ["collections","triggers","actions"]
    for objectType in objectTypes:
        for objectName, objectValue in manifest[objectType].items():
            try:
                model = jimi.model._model().getAsClass(query={"name" : objectName, "location" : "{0}".format(objectValue["class_location"]) })[0]
                objectValue["class_id"] = model._id
                model.manifest = objectValue
                model.update(["manifest"])
            except IndexError:
                pass

def loadSystemManifest():
    if os.path.isfile(str(Path("system/system.json"))):
        with open(str(Path("system/system.json")), "r") as f:
            manifest = json.load(f)
        processSystemManifest(manifest)
        return True
    return False

def systemInstall():
    # Adding ENC secure
    systemSecure = _system().query(query={ "name" : "secure" })["results"]
    if len(systemSecure) < 1:
        systemSecure = _system().new("secure").inserted_id
        systemSecure = _system().get(systemSecure)
        systemSecure.data = { "string" : secrets.token_hex(32) }
        systemSecure.update(["data"])

    # Installing model if that DB is not installed
    if "model" not in jimi.db.list_collection_names():
        logging.info("DB Collection 'model' Not Found : Creating...")
        # Creating default model required so other models can be registered
        logging.info("Registering default model class...")
        m = jimi.model._model()
        m.name = "model"
        m.classID = None
        m.acl = { "ids":[ { "accessID":"0","delete": True,"read": True,"write": True } ] }
        m.className = "_model"
        m.classType = "_document"
        m.location = "core.model"
        m.insert_one(m.parse())
    if "conducts" not in jimi.db.list_collection_names():
        logging.info("DB Collection conducts Not Found : Creating...")
        jimi.model.registerModel("conduct","_conduct","_document","core.models.conduct")
    if "triggers" not in jimi.db.list_collection_names():
        logging.info("DB Collection action Not Found : Creating...")
        jimi.model.registerModel("trigger","_trigger","_document","core.models.trigger")
    if "actions" not in jimi.db.list_collection_names():
        logging.info("DB Collection action Not Found : Creating...")
        jimi.model.registerModel("action","_action","_document","core.models.action")
    if "webui" not in jimi.db.list_collection_names():
        logging.info("DB Collection webui Not Found : Creating...")
        jimi.model.registerModel("flowData","_flowData","_document","core.models.webui")
    if "modelUI" not in jimi.db.list_collection_names():
        logging.info("DB Collection modelUI Not Found : Creating...")
        jimi.model.registerModel("modelUI","_modelUI","_document","core.models.webui")
    if "editorUI" not in jimi.db.list_collection_names():
        logging.info("DB Collection editorUI Not Found : Creating...")
        jimi.model.registerModel("editorUI","_editorUI","_document","core.models.webui")
    if "clusterMembers" not in jimi.db.list_collection_names():
        logging.info("DB Collection clusterMembers Not Found : Creating...")
        jimi.model.registerModel("clusterMember","_clusterMember","_document","core.cluster")

    # Settings
    jimi.model.registerModel("settings","_settings","_document","core.settings")
    config = {}
    if os.path.exists(str(Path("data/settings.json"))):
        with open(str(Path("data/settings.json"))) as f:
            config = json.load(f)
    if not jimi.settings._settings().new("debug",{
        "level" : -1,
        "buffer" : 1000
    }):
        print("ERROR: Unable to build system debug ")
        return False
    if not jimi.settings._settings().new("workers",{ 
        "concurrent" : 15,
        "loopT" : 0.01,
        "loopT1" : 0.25,
        "loopL" : 200
    }):
        print("ERROR: Unable to build system workers ")
        return False
    if not jimi.settings._settings().new("cpuSaver",{ 
        "enabled" : True,
        "loopT" : 0.01,
        "loopL" : 100
    }):
        print("ERROR: Unable to build system cpuSaver ")
        return False
    if not jimi.settings._settings().new("scheduler",{
        "loopP" : 5
    }):
        print("ERROR: Unable to build system scheduler ")
        return False
    if not jimi.settings._settings().new("cluster",{
        "loopP" : 10,
        "recoveryTime" : 60,
        "deadTimer" : 30
    }):
        print("ERROR: Unable to build system cluster ")
        return False
    if not jimi.settings._settings().new("audit",{
        "db" : {
            "enabled" : True
        },
        "file" : {
            "enabled" : False,
            "logdir" : "log"
        }
    }):
        print("ERROR: Unable to build system audit ")
        return False
    if "auth" in config:
        result = jimi.settings._settings().new("auth",config["auth"])
    else:
        result = jimi.settings._settings().new("auth",{
            "enabled" : True,
            "auto_generate" : True,
            "sessionTimeout" : 1800,
            "apiSessionTimeout" : 300,
            "cacheSessionTimeout" : 60,
            "singleUserSessions" : True,
            "rsa" : {
                "cert" : None,
                "key" : None
            },
            "rsa_web" : {
                "cert" : None,
                "key" : None
            },
            "policy" : {
                "minLength" : 12,
                "minNumbers" : 1,
                "minLower" : 1,
                "minUpper" : 1,
                "minSpecial" : 0
            }
        })
    if not result:
        print("ERROR: Unable to build system auth ")
        return False
    if not jimi.settings._settings().new("cache",{
        "garbageCollector" : True
    }):
        print("ERROR: Unable to build system cache ")
        return False
    if not jimi.settings._settings().new("plugins",{
        "install_dependencies" : True
    }):
        print("ERROR: Unable to build system plugins")
        return False

    # System documents
    jimi.model.registerModel("systemFiles","_systemFiles","_document","system.system")

    # System - failedTriggers
    triggers = jimi.trigger._trigger(False).getAsClass(query={"name" : "failedTriggers"})
    if len(triggers) < 1:
        from system.models import trigger as systemTrigger
        jimi.model.registerModel("failedTriggers","_failedTriggers","_trigger","system.models.trigger")
        if not systemTrigger._failedTriggers().new("failedTriggers"):
            logging.error("Unable to register failedTriggers")
            return False
    temp = jimi.model._model().getAsClass(query={ "name" : "failedTriggers" })
    if len(temp) == 1:
        temp = temp[0]
        temp.hidden = True
        temp.update(["hidden"])

    # System - failedActions
    triggers = jimi.trigger._trigger(False).getAsClass(query={"name" : "failedActions"})
    if len(triggers) < 1:
        from system.models import trigger as systemTrigger
        jimi.model.registerModel("failedActions","_failedActions","_trigger","system.models.trigger")
        if not systemTrigger._failedActions().new("failedActions"):
            logging.error("Unable to register failedActions")
            return False
    temp = jimi.model._model().getAsClass(query={ "name" : "failedActions" })
    if len(temp) == 1:
        temp = temp[0]
        temp.hidden = True
        temp.update(["hidden"])

    # System - Actions
    # resetTrigger
    actions = jimi.action._action().getAsClass(query={"name" : "resetTrigger"})
    if len(actions) < 1:
        from system.models import action as systemAction
        jimi.model.registerModel("resetTrigger","_resetTrigger","_action","system.models.action")
        if not systemAction._resetTrigger().new("resetTrigger"):
            logging.error("Unable to register resetTrigger")
            return False
    temp = jimi.model._model().getAsClass(query={ "name" : "resetTrigger" })
    if len(temp) == 1:
        temp = temp[0]
        temp.hidden = True
        temp.update(["hidden"])
    # Trigger / Action Actions
    jimi.model.registerModel("getTrigger","_getTrigger","_action","system.models.action")
    jimi.model.registerModel("setTrigger","_setTrigger","_action","system.models.action")
    jimi.model.registerModel("enableTrigger","_enableTrigger","_action","system.models.action")
    jimi.model.registerModel("disableTrigger","_disableTrigger","_action","system.models.action")
    jimi.model.registerModel("getAction","_getAction","_action","system.models.action")
    jimi.model.registerModel("setAction","_setAction","_action","system.models.action")
    jimi.model.registerModel("enableAction","_enableAction","_action","system.models.action")
    jimi.model.registerModel("disableAction","_disableAction","_action","system.models.action")
    jimi.model.registerModel("break","_break","_action","system.models.action")
    jimi.model.registerModel("exit","_exit","_action","system.models.action")

    # forEach
    actions = jimi.action._action(False).query(query={"name" : "forEach"})["results"]
    if len(actions) < 1:
        jimi.model.registerModel("forEach","_forEach","_action","system.models.forEach")

    # subFlow
    jimi.model.registerModel("subFlow","_subFlow","_action","system.models.subFlow")
    jimi.model.registerModel("subFlowReturn","_subFlowReturn","_action","system.models.subFlow")

    # global
    jimi.model.registerModel("global","_global","_document","system.models.global")
    jimi.model.registerModel("globalSet","_globalSet","_action","system.models.global")
    jimi.model.registerModel("globalGet","_globalGet","_action","system.models.global")

    # Sleep
    jimi.model.registerModel("sleep","_sleep","_action","system.models.sleep")

    # Collect
    jimi.model.registerModel("collect","_collect","_action","system.models.collect")

    # Extract
    jimi.model.registerModel("extract","_extract","_action","system.models.extract")

    # Storage
    jimi.model.registerModel("storageTrigger","_storageTrigger","_trigger","system.models.storage")

    # Adding model for plugins
    jimi.model.registerModel("plugins","_plugin","_document","core.plugin")

    # Adding model for fileStorage
    jimi.model.registerModel("storage","_storage","_document","core.storage")

    # Adding models for user and groups
    jimi.model.registerModel("user","_user","_document","core.auth")
    jimi.model.registerModel("group","_group","_document","core.auth")
    jimi.model.registerModel("session","_session","_document","core.auth")

    # Generate password function	
    jimi.model.registerModel("generatePassword","_generatePassword","_action","system.models.action")

    # Adding default admin group
    adminGroup = jimi.auth._group().getAsClass(query={ "name" : "admin" })
    if len(adminGroup) == 0:
        adminGroup = jimi.auth._group().new("admin")
        adminGroup = jimi.auth._group().getAsClass(query={ "name" : "admin" })
    adminGroup = adminGroup[0]
    
    #Set admin group description
    adminGroup.description = "The default administration group for jimi"
    adminGroup.update(["description"])

    # Adding default root user
    rootUser = jimi.auth._user().getAsClass(query={ "username" : "root" })
    if len(rootUser) == 0:
        rootPass = randomString(30)
        rootUser = jimi.auth._user().new("root","root",rootPass)
        rootUser = jimi.auth._user().getAsClass(query={ "username" : "root" })
        logging.info("Root user created! Password is: {}".format(rootPass))
    rootUser = rootUser[0]

    # Adding root to group
    if rootUser._id not in adminGroup.members:
        adminGroup.members.append(rootUser._id)
        adminGroup.update(["members"])

    # Adding primary group for root user
    rootUser.primaryGroup = adminGroup._id
    rootUser.update(["primaryGroup"])

    # Adding default everyone group
    everyoneGroup = jimi.auth._group().getAsClass(query={ "name" : "everyone" })
    if len(everyoneGroup) == 0:
        everyoneGroup = jimi.auth._group().new("everyone")

    # Adding model for revisions
    jimi.model.registerModel("revision","_revision","_document","core.revision")

    # Adding model for flowDebugSnapshots
    jimi.model.registerModel("flowDebugSnapshot","_flowDebugSnapshot","_document","core.debug")

    #Adding ldap and oauth settings
    if len(jimi.settings._settings().getAsClass(query={"name" : "ldap"})) == 0:
        jimi.settings._settings().new("ldap",{"domains":[]})
    if len(jimi.settings._settings().getAsClass(query={"name" : "oauth"})) == 0:
        jimi.settings._settings().new("oauth",{})

    #Adding org model
    jimi.model.registerModel("organisation","_organisation","_document","core.organisation")

    #Adding additional auth settings
    authSettings = jimi.settings._settings().getAsClass(query={"name" : "auth"})[0]
    if "types" not in authSettings.values:
        authSettings.values["types"] = ["local"]
        authSettings.update(["values"])

    # Adding secret model
    jimi.model.registerModel("secret","_secret","_document","core.secrets")

    # Creating indexes
    logging.info("Creating indexes...")
    jimi.revision._revision()._dbCollection.create_index([("objectID", 1),("classID", 1)])
    jimi.audit._audit()._dbCollection.create_index([("eventSource", 1),("eventType", 1)])

    # Install system manifest
    loadSystemManifest()

    return True

def systemUpgrade(currentVersion):
    # Attempts to upgrade all installed plugins
    def upgradeInstalledPlugins():
        installedPlugins = jimi.plugin._plugin().query(query={ "installed" : True })["results"]
        for installedPlugin in installedPlugins:
            pluginClass = jimi.plugin._plugin().getAsClass(id=installedPlugin["_id"])
            if len(pluginClass) == 1:
                pluginClass = pluginClass[0]
                pluginClass.upgradeHandler()
        return True
    
    if currentVersion < 2.07:
        jimi.model.registerModel("systemFiles","_systemFiles","_document","system.system")

    if currentVersion < 2.09:
        loadSystemManifest()

    if currentVersion < 2.10:
        # New generate password system function
        jimi.model.registerModel("generatePassword","_generatePassword","_action","system.models.action")

    if currentVersion < 3.0:
        if jimi.model.registerModel("settings","_settings","_document","core.settings"):
            import json
            from pathlib import Path
            with open(str(Path("data/settings.json"))) as f:
                config = json.load(f)
            if not jimi.settings._settings().new("debug",config["debug"]):
                print("ERROR: Unable to build system debug ")
                return False
            if not jimi.settings._settings().new("workers",config["workers"]):
                print("ERROR: Unable to build system workers ")
                return False
            if not jimi.settings._settings().new("cpuSaver",config["cpuSaver"]):
                print("ERROR: Unable to build system cpuSaver ")
                return False
            if not jimi.settings._settings().new("scheduler",config["scheduler"]):
                print("ERROR: Unable to build system scheduler ")
                return False
            if not jimi.settings._settings().new("cluster",config["cluster"]):
                print("ERROR: Unable to build system cluster ")
                return False
            if not jimi.settings._settings().new("audit",config["audit"]):
                print("ERROR: Unable to build system audit ")
                return False
            if not jimi.settings._settings().new("auth",config["auth"]):
                print("ERROR: Unable to build system auth ")
                return False
            if not jimi.settings._settings().new("cache",{ "garbageCollector" : True }):
                print("ERROR: Unable to build system cache ")
                return False
            sys.exit(0)

    if currentVersion < 3.01:
        jimi.model.registerModel("editorUI","_editorUI","_document","core.models.webui")

    if currentVersion < 3.02:
        # Adding default everyone group
        everyoneGroup = jimi.auth._group().getAsClass(query={ "name" : "everyone" })
        if len(everyoneGroup) == 0:
            everyoneGroup = jimi.auth._group().new("everyone")
        # Update ACLs of editorUI model for each object to fix bug
        existingObjects = jimi.webui._editorUI().getAsClass()
        for existingObject in existingObjects:
            existingObject.acl = {"ids":[{"accessID":0,"delete":True,"read":True,"write":True}]}
            existingObject.update(["acl"])

    if currentVersion < 3.03:
        jimi.model.registerModel("extract","_extract","_action","system.models.extract")

    if currentVersion < 3.034:
        loadSystemManifest()

    if currentVersion < 3.035:
        jimi.model.registerModel("revision","_revision","_document","core.revision")

    if currentVersion < 3.036:
        users = jimi.auth._user().getAsClass(query={  })
        for user in users:
            user.whatsNew = True
            user.update(["whatsNew"])

    if currentVersion < 3.04:
        #Adding additional auth settings
        authSettings = jimi.settings._settings().getAsClass(query={"name" : "auth"})[0]
        if "types" not in authSettings.values:
            authSettings.values["types"] = ["local"]
            authSettings.update(["values"])
        
        #Setting all users to local initially
        users = jimi.auth._user().getAsClass(query={  })
        for user in users:
            user.loginType = "local"
            user.update(["loginType"])

        #Add ldap and oauth settings
        if len(jimi.settings._settings().getAsClass(query={"name" : "ldap"})) == 0:
            jimi.settings._settings().new("ldap",{"domains":[]})
        if len(jimi.settings._settings().getAsClass(query={"name" : "oauth"})) == 0:
            jimi.settings._settings().new("oauth",{})

        #Adding org model
        jimi.model.registerModel("organisation","_organisation","_document","core.organisation")

    if currentVersion < 3.112:
        for conductItem in jimi.conduct._conduct().getAsClass():
            for flowItem in conductItem.flow:
                for flowItemNext in flowItem["next"]:
                    if "tag" not in flowItemNext:
                        flowItemNext["tag"] = ""
            conductItem.update(["flow"])

    if currentVersion < 3.113:
        jimi.model.registerModel("storageTrigger","_storageTrigger","_trigger","system.models.storage")

    if currentVersion < 3.1151:
        loadSystemManifest()

    if currentVersion < 3.1152:
        jimi.model.registerModel("break","_break","_action","system.models.action")
        jimi.model.registerModel("exit","_exit","_action","system.models.action")
        loadSystemManifest()

    if currentVersion < 3.1153:
        jimi.model.registerModel("flowDebugSnapshot","_flowDebugSnapshot","_document","core.debug")

    if currentVersion < 3.12:
        jimi.settings._settings().new("plugins",{ "install_dependencies" : True })

    if currentVersion < 3.122:
        authSettings = jimi.settings._settings(False).getAsClass(query={ "name" : "auth" })[0]
        authSettings.values["auto_generate"] = True
        authSettings.values["rsa_web"] = {
            "cert" : None,
            "key" : None
        }
        authSettings.update(["values"])

    if currentVersion < 3.123:
        jimi.model.registerModel("secret","_secret","_document","core.secrets")

    if currentVersion < 3.124:
        loadSystemManifest()
    
    if currentVersion < 3.1241:
        jimi.settings._settings().new("storage",{ "maxBytesChecked" : 26214400})

    if currentVersion < 3.1246:
        logging.info("Creating indexes...")
        jimi.revision._revision()._dbCollection.create_index([("objectID", 1),("classID", 1)])
        jimi.audit._audit()._dbCollection.create_index([("eventSource", 1),("eventType", 1)])

    if currentVersion < 3.13:
        jimi.model.registerModel("subFlowReturn","_subFlowReturn","_action","system.models.subFlow")
        loadSystemManifest()

    if currentVersion < 3.132:
        loadSystemManifest()

    if currentVersion < 3.133:
        for plugin in jimi.plugin._plugin().getAsClass(query={ "acl.ids.accessID" : { "$ne" : 0 } }):
            plugin.acl ={ "ids":[ { "accessID":"0","delete": True,"read": True,"write": True } ] }
            plugin.update(["acl"])

    return True
