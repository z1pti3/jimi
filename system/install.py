import time
import sys
import secrets
import random
import string
from pathlib import Path
import os
import json

import jimi

# Current System Version
systemVersion = 3.0

# Initialize 
dbCollectionName = "system"

# system Class
class _system(jimi.db._document):
	name = str()
	systemID = int()
	data = dict()

	_dbCollection = jimi.db.db[dbCollectionName]

	# Blanking some non required class functions
	def new(self,name):
		result = self._dbCollection.insert_one({ "name" : name })
		return result

systemSettings = jimi.config["system"]

def installedVersion():
	systemAbout = _system().query(query={ "name" : "about", "systemID" : systemSettings["systemID"] })["results"]
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
	systemAbout = _system().query(query={ "name" : "about", "systemID" : systemSettings["systemID"] })["results"]
	if len(systemAbout) < 1:
		systemAbout = _system().new("about").inserted_id
		systemAbout = _system().get(systemAbout)
		systemAbout.systemID = systemSettings["systemID"]
		systemAbout.update(["systemID"])
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
		jimi.logging.debug("Starting system install",-1)
		if systemInstall():
			# Set system version number if install and/or upgrade
			systemAbout.data["version"] = systemVersion
			systemAbout.systemID = systemSettings["systemID"]
			systemAbout.update(["data","systemID"])
			jimi.logging.debug("Starting system install completed",-1)
		else:
			sys.exit("Unable to complete install")
	elif upgrade:
		jimi.logging.debug("Starting system upgrade",-1)
		systemUpgrade(systemAbout.data["version"])
		if systemUpgrade(systemAbout.data["version"]):
			# Set system version number if install and/or upgrade
			systemAbout.data["version"] = systemVersion
			systemAbout.update(["data"])
			jimi.logging.debug("Starting system upgrade completed",-1)
		else:
			sys.exit("Unable to complete upgrade")

	# Loading functions
	jimi.function.load()

	# Initialize plugins
	jimi.plugin.load()

# Set startCheck to 0 so that all triggers start
def resetTriggers():
	triggers = jimi.trigger._trigger().query(query={"startCheck" : { "$gt" : 0}})["results"]
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
				model = jimi.model._model().getAsClass(query={"name" : objectName, "location" : "system.{0}".format(objectValue["class_location"]) })[0]
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
		jimi.logging.debug("DB Collection 'model' Not Found : Creating...")
		# Creating default model required so other models can be registered
		jimi.logging.debug("Registering default model class...")
		m = jimi.model._model()
		m.name = "model"
		m.classID = None
		m.acl = { "ids":[ { "accessID":"0","delete": True,"read": True,"write": True } ] }
		m.className = "_model"
		m.classType = "_document"
		m.location = "core.model"
		m.insert_one(m.parse())
	if "conducts" not in jimi.db.list_collection_names():
		jimi.logging.debug("DB Collection conducts Not Found : Creating...")
		jimi.model.registerModel("conduct","_conduct","_document","core.models.conduct")
	if "triggers" not in jimi.db.list_collection_names():
		jimi.logging.debug("DB Collection action Not Found : Creating...")
		jimi.model.registerModel("trigger","_trigger","_document","core.models.trigger")
	if "actions" not in jimi.db.list_collection_names():
		jimi.logging.debug("DB Collection action Not Found : Creating...")
		jimi.model.registerModel("action","_action","_document","core.models.action")
	if "webui" not in jimi.db.list_collection_names():
		jimi.logging.debug("DB Collection webui Not Found : Creating...")
		jimi.model.registerModel("flowData","_flowData","_document","core.models.webui")
	if "modelUI" not in jimi.db.list_collection_names():
		jimi.logging.debug("DB Collection modelUI Not Found : Creating...")
		jimi.model.registerModel("modelUI","_modelUI","_document","core.models.webui")
	if "clusterMembers" not in jimi.db.list_collection_names():
		jimi.logging.debug("DB Collection clusterMembers Not Found : Creating...")
		jimi.model.registerModel("clusterMember","_clusterMember","_document","core.cluster")

	# Settings
	jimi.model.registerModel("settings","_settings","_document","core.settings")
	if not jimi.settings._settings().new("system",{
        "systemID" : 0,
        "accessAddress" : "127.0.0.1",
        "accessPort" : 5000,
        "secure" : False
    }):
		print("ERROR: Unable to build system settings ")
		return False
	if not jimi.settings._settings().new("debug",{
        "level" : -1,
        "buffer" : 1000
    }):
		print("ERROR: Unable to build system debug ")
		return False
	if not jimi.settings._settings().new("api",{
        "core" : {
            "bind" : "127.0.0.1",
            "port" : 5000,
            "base" : "api/1.0",
            "apiKey" : None
        },
        "worker" : {
            "bind" : "127.0.0.1",
            "startPort" : 5001,
            "base" : "api/1.0",
            "apiKey" : None
        },
        "web" : {
            "bind" : "127.0.0.1",
            "port" : 5015,
            "base" : "api/1.0",
            "apiKey" : None
        },
        "proxy" : {
            "http" : None,
            "https" : None
        }
    }):
		print("ERROR: Unable to build system api ")
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
	if not jimi.settings._settings().new("aduit",{
        "db" : {
            "enabled" : True
        },
        "file" : {
            "enabled" : True,
            "logdir" : "log"
        }
    }):
		print("ERROR: Unable to build system aduit ")
		return False
	if not jimi.settings._settings().new("auth",{
        "enabled" : True,
        "sessionTimeout" : 1800,
        "apiSessionTimeout" : 300,
        "cacheSessionTimeout" : 60,
        "singleUserSessions" : True,
        "rsa" : {
            "cert" : "data/sessionPub.pem",
            "key" : "data/sessionPriv.pem"
        },
        "policy" : {
            "minLength" : 12,
            "minNumbers" : 1,
            "minLower" : 1,
            "minUpper" : 1,
            "minSpecial" : 0
        }
    }):
		print("ERROR: Unable to build system auth ")
		return False
	if not jimi.settings._settings().new("cache",{
        "garbageCollector" : True
    }):
		print("ERROR: Unable to build system cache ")
		return False

	# System documents
	jimi.model.registerModel("systemFiles","_systemFiles","_document","system.system")

	# System - failedTriggers
	triggers = jimi.trigger._trigger().getAsClass(query={"name" : "failedTriggers"})
	if len(triggers) < 1:
		from system.models import trigger as systemTrigger
		jimi.model.registerModel("failedTriggers","_failedTriggers","_trigger","system.models.trigger")
		if not systemTrigger._failedTriggers().new("failedTriggers"):
			jimi.logging.debug("Unable to register failedTriggers",-1)
			return False
	temp = jimi.model._model().getAsClass(query={ "name" : "failedTriggers" })
	if len(temp) == 1:
		temp = temp[0]
		temp.hidden = True
		temp.update(["hidden"])

	# System - failedActions
	triggers = jimi.trigger._trigger().getAsClass(query={"name" : "failedActions"})
	if len(triggers) < 1:
		from system.models import trigger as systemTrigger
		jimi.model.registerModel("failedActions","_failedActions","_trigger","system.models.trigger")
		if not systemTrigger._failedActions().new("failedActions"):
			jimi.logging.debug("Unable to register failedActions",-1)
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
			jimi.logging.debug("Unable to register resetTrigger",-1)
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

	# forEach
	actions = jimi.action._action().query(query={"name" : "forEach"})["results"]
	if len(actions) < 1:
		jimi.model.registerModel("forEach","_forEach","_action","system.models.forEach")

	# subFlow
	jimi.model.registerModel("subFlow","_subFlow","_action","system.models.subFlow")

	# global
	jimi.model.registerModel("global","_global","_document","system.models.global")
	jimi.model.registerModel("globalSet","_globalSet","_action","system.models.global")
	jimi.model.registerModel("globalGet","_globalGet","_action","system.models.global")

	# Sleep
	jimi.model.registerModel("sleep","_sleep","_action","system.models.sleep")

	# Collect
	jimi.model.registerModel("collect","_collect","_action","system.models.collect")

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

	# Adding default root user
	rootUser = jimi.auth._user().getAsClass(query={ "username" : "root" })
	if len(rootUser) == 0:
		rootPass = randomString(30)
		rootUser = jimi.auth._user().new("root","root",rootPass)
		rootUser = jimi.auth._user().getAsClass(query={ "username" : "root" })
		jimi.logging.debug("Root user created! Password is: {}".format(rootPass),-1)
	rootUser = rootUser[0]

	# Adding root to group
	if rootUser._id not in adminGroup.members:
		adminGroup.members.append(rootUser._id)
		adminGroup.update(["members"])

	# Adding primary group for root user
	rootUser.primaryGroup = adminGroup._id
	rootUser.update(["primaryGroup"])

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
		jimi.model.registerModel("settings","_settings","_document","core.settings")
		import json
		from pathlib import Path
		with open(str(Path("data/settings.json"))) as f:
			config = json.load(f)
		if not jimi.settings._settings().new("system",config["system"]):
			print("ERROR: Unable to build system settings ")
			return False
		if not jimi.settings._settings().new("debug",config["debug"]):
			print("ERROR: Unable to build system debug ")
			return False
		if not jimi.settings._settings().new("api",config["api"]):
			print("ERROR: Unable to build system api ")
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
	return True
