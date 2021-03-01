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
systemVersion = 2.06

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

systemSettings = jimi.settings.config["system"]

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

	if currentVersion < 1.81:
		jimi.model.registerModel("storage","_storage","_document","core.storage")

	if currentVersion < 1.9:
		jimi.model.registerModel("getTrigger","_getTrigger","_action","system.models.action")
		jimi.model.registerModel("setTrigger","_setTrigger","_action","system.models.action")
		jimi.model.registerModel("enableTrigger","_enableTrigger","_action","system.models.action")
		jimi.model.registerModel("disableTrigger","_disableTrigger","_action","system.models.action")
		jimi.model.registerModel("getAction","_getAction","_action","system.models.action")
		jimi.model.registerModel("setAction","_setAction","_action","system.models.action")
		jimi.model.registerModel("enableAction","_enableAction","_action","system.models.action")
		jimi.model.registerModel("disableAction","_disableAction","_action","system.models.action")

	if currentVersion < 2.0:
		jimi.model.registerModel("session","_session","_document","core.auth")

	if currentVersion < 2.01:
		classID = jimi.model._model().query(query={"className" : "_plugin" })["results"][0]["_id"]
		installedPlugins = jimi.plugin._plugin().getAsClass(query={ "installed" : True })
		for installedPlugin in installedPlugins:
			installedPlugin.classID = classID
			installedPlugin.update(["classID"])

	if currentVersion < 2.03:
		# Install system manifest
		loadSystemManifest()

	if currentVersion < 2.04:
		# Update system manifest
		loadSystemManifest()
		jimi.model.registerModel("subFlow","_subFlow","_action","system.models.subFlow")

	if currentVersion < 2.05:
		# Update system manifest
		loadSystemManifest()

	if currentVersion < 2.06:
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
		# Update system manifest
		loadSystemManifest()

	return True
		
