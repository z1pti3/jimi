import time
import sys
import secrets
import random
import string

from core import db

# Current System Version
systemVersion = 0.553

# Initialize 
dbCollectionName = "system"

# system Class
class _system(db._document):
	name = str()
	systemID = int()
	data = dict()

	_dbCollection = db.db[dbCollectionName]

	# Blanking some non required class functions
	def new(self,name):
		result = self._dbCollection.insert_one({ "name" : name })
		return result

from core import db, logging, model, settings

systemSettings = settings.config["system"]

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
		logging.debug("Starting system install",-1)
		if systemInstall():
			# Set system version number if install and/or upgrade
			systemAbout.data["version"] = systemVersion
			systemAbout.systemID = systemSettings["systemID"]
			systemAbout.update(["data","systemID"])
			logging.debug("Starting system install completed",-1)
		else:
			sys.exit("Unable to complete install")
	elif upgrade:
		logging.debug("Starting system upgrade",-1)
		systemUpgrade(systemAbout.data["version"])
		if systemUpgrade(systemAbout.data["version"]):
			# Set system version number if install and/or upgrade
			systemAbout.data["version"] = systemVersion
			systemAbout.update(["data"])
			logging.debug("Starting system upgrade completed",-1)
		else:
			sys.exit("Unable to complete upgrade")

# Set startCheck to 0 so that all triggers start
def resetTriggers():
	from core.models import trigger
	print(len(trigger._trigger().getAsClass()))
	# Clearing any triggers with a startCheck set - Very poor as it hammers the DB, be better to do this as one mass update command to the database
	# This wont scale to clustering as it will clear all running triggers even if they were running by another cluster node
	triggers = trigger._trigger().query(query={"startCheck" : { "$gt" : 0}})["results"]
	for triggerJson in triggers:
		triggerClass = trigger._trigger().get(triggerJson["_id"])
		triggerClass.startCheck = 0
		triggerClass.update(["startCheck"])

def randomString(length=12):
	charSet = string.ascii_letters + string.digits
	return ''.join([random.choice(charSet) for i in range(length)])

def systemInstall():
	# Adding ENC secure
	systemSecure = _system().query(query={ "name" : "secure" })["results"]
	if len(systemSecure) < 1:
		systemSecure = _system().new("secure").inserted_id
		systemSecure = _system().get(systemSecure)
		systemSecure.data = { "string" : secrets.token_hex(32) }
		systemSecure.update(["data"])

	# Installing model if that DB is not installed
	if "model" not in db.list_collection_names():
		logging.debug("DB Collection 'model' Not Found : Creating...")
		# Creating default model required so other models can be registered
		logging.debug("Registering default model class...")
		m = model._model()
		m.name = "model"
		m.classID = None
		m.acl = { "ids":[ { "accessID":"0","delete": True,"read": True,"write": True } ] }
		m.className = "_model"
		m.classType = "_document"
		m.location = "core.model"
		m.insert_one(m.parse())
	if "conducts" not in db.list_collection_names():
		logging.debug("DB Collection conducts Not Found : Creating...")
		model.registerModel("conduct","_conduct","_document","core.models.conduct")
	if "triggers" not in db.list_collection_names():
		logging.debug("DB Collection action Not Found : Creating...")
		model.registerModel("trigger","_trigger","_document","core.models.trigger")
	if "actions" not in db.list_collection_names():
		logging.debug("DB Collection action Not Found : Creating...")
		model.registerModel("action","_action","_document","core.models.action")
	if "webui" not in db.list_collection_names():
		logging.debug("DB Collection webui Not Found : Creating...")
		model.registerModel("flowData","_flowData","_document","core.models.webui")
	if "modelUI" not in db.list_collection_names():
		logging.debug("DB Collection modelUI Not Found : Creating...")
		model.registerModel("modelUI","_modelUI","_document","core.models.webui")
	if "clusterMembers" not in db.list_collection_names():
		logging.debug("DB Collection clusterMembers Not Found : Creating...")
		model.registerModel("clusterMember","_clusterMember","_document","core.cluster")

	# System - failedTriggers
	from core.models import trigger
	triggers = trigger._trigger().query(query={"name" : "failedTriggers"})["results"]
	if len(triggers) < 1:
		from system.models import trigger as systemTrigger
		model.registerModel("failedTriggers","_failedTriggers","_trigger","system.models.trigger")
		if not systemTrigger._failedTriggers().new("failedTriggers"):
			logging.debug("Unable to register failedTriggers",-1)
			return False
	temp = model._model().getAsClass(query={ "name" : "failedTriggers" })
	if len(temp) == 1:
		temp = temp[0]
		temp.hidden = True
		temp.update(["hidden"])

	# System - Actions
	from core.models import action
	actions = action._action().query(query={"name" : "resetTrigger"})["results"]
	if len(actions) < 1:
		from system.models import action as systemAction
		model.registerModel("resetTrigger","_resetTrigger","_action","system.models.action")
		if not systemAction._resetTrigger().new("resetTrigger"):
			logging.debug("Unable to register resetTrigger",-1)
			return False
	temp = model._model().getAsClass(query={ "name" : "resetTrigger" })
	if len(temp) == 1:
		temp = temp[0]
		temp.hidden = True
		temp.update(["hidden"])

	from core import auth

	# Adding models for user and groups
	model.registerModel("user","_user","_document","core.auth")
	model.registerModel("group","_group","_document","core.auth")

	# Adding default admin group
	adminGroup = auth._group().getAsClass(query={ "name" : "admin" })
	if len(adminGroup) == 0:
		adminGroup = auth._group().new("admin")
		adminGroup = auth._group().getAsClass(query={ "name" : "admin" })
	adminGroup = adminGroup[0]

	# Adding default root user
	rootUser = auth._user().getAsClass(query={ "username" : "root" })
	if len(rootUser) == 0:
		rootPass = randomString(30)
		rootUser = auth._user().new("root","root",rootPass)
		rootUser = auth._user().getAsClass(query={ "username" : "root" })
		logging.debug("Root user created! Password is: {}".format(rootPass),-1)
	rootUser = rootUser[0]

	# Adding root to group
	if rootUser._id not in adminGroup.members:
		adminGroup.members.append(rootUser._id)
		adminGroup.update(["members"])

	# Adding primary group for root user
	rootUser.primaryGroup = adminGroup._id
	rootUser.update(["primaryGroup"])

	return True

def systemUpgrade(currentVersion):
	# Attempts to upgrade all installed plugins
	def upgradeInstalledPlugins():
		from core import plugin
		installedPlugins = plugin._plugin().query(query={ "installed" : True })["results"]
		for installedPlugin in installedPlugins:
			pluginClass = plugin._plugin().getAsClass(id=installedPlugin["_id"])
			if len(pluginClass) == 1:
				pluginClass = pluginClass[0]
				pluginClass.upgradeHandler()

	## 0.6 ##
	if systemVersion > 0.5 and currentVersion < 0.6:
		from core.models import conduct
		conducts = conduct._conduct().query()["results"]
		for conductItem in conducts:
			temp = conduct._conduct().get(conductItem["_id"])
			temp.log = False
			temp.update(["log"])

		from core import model
		from core.models import action
		# Checking to see if on Demand is still in use - these need to be removed before upgrade
		onDemandModel = model._model().query(query={ "name" : "onDemand", "location" : "system.models.trigger" })["results"]
		if len(onDemandModel) == 1:
			logging.debug("onDemand is installed!",-1)
			onDemandModel = onDemandModel[0]["classID"]
			onDemandInUse = action._action().query(query={ "classID" : onDemandModel })["results"]
			if len(onDemandInUse) > 0:
				logging.debug("onDemand actions still exist - This has been depricated for plugin 'manual'",-1)
				return False
			model.deregisterModel("onDemand","_onDemand","_trigger","system.models.trigger")

		# Setting model ACL to fix vulnrability
		modelModel = model._model().getAsClass(query={ "name" : "model", "location" : "core.model" })
		if len(modelModel) == 1:
			modelModel = modelModel[0]
			modelModel.acl = { "ids":[ { "accessID":"0","delete": True,"read": True,"write": True } ] }
			modelModel.update(["acl"])
			logging.debug("Updated model ACL - success",-1)

		# Adding new model for cluster
		model.registerModel("clusterMember","_clusterMember","_document","core.cluster")
		
		return True

	## 0.5 ##
	if systemVersion > 0.4 and currentVersion < 0.5:
		from core import model
		if "modelUI" not in db.list_collection_names():
			logging.debug("DB Collection modelUI Not Found : Creating...")
			model.registerModel("modelUI","_modelUI","_document","core.models.webui")

		return True

	## 0.4 ##
	if systemVersion > 0.3 and currentVersion < 0.4:
		# Adding ENC secure
		systemSecure = _system().query(query={ "name" : "secure" })["results"]
		if len(systemSecure) < 1:
			systemSecure = _system().new("secure").inserted_id
			systemSecure = _system().get(systemSecure)
			systemSecure.data = { "string" : secrets.token_hex(32) }
			systemSecure.update(["data"])

		from core import model
		modles = model._model().query()["results"]
		for modelItem in modles:
			tempModel = model._model().get(modelItem["_id"])
			tempModel.acl = { "ids" : [ { "accessID" : "0", "read" : True, "write" : True, "delete" : True } ] }
			tempModel.update(["acl"])

		# System - Trigger hiding
		temp = model._model().getAsClass(query={ "name" : "failedTriggers" })
		if len(temp) == 1:
			temp = temp[0]
			temp.hidden = True
			temp.update(["hidden"])

		# System - Actions
		from core.models import action
		actions = action._action().query(query={"name" : "resetTrigger"})["results"]
		if len(actions) < 1:
			from system.models import action as systemAction
			something = systemAction._resetTrigger().new("resetTrigger")
			model.registerModel("resetTrigger","_resetTrigger","_action","system.models.action")
		temp = model._model().getAsClass(query={ "name" : "resetTrigger" })
		if len(temp) == 1:
			temp = temp[0]
			temp.hidden = True
			temp.update(["hidden"])

		# Adding new system model triggers
		model.registerModel("onDemand","_onDemand","_trigger","system.models.trigger")

		# Adding models for user and groups
		model.registerModel("user","_user","_document","core.auth")
		model.registerModel("group","_group","_document","core.auth")

		from core import auth
		# Adding default admin group
		adminGroup = auth._group().getAsClass(query={ "name" : "admin" })
		if len(adminGroup) == 0:
			adminGroup = auth._group().new("admin")
			adminGroup = auth._group().getAsClass(query={ "name" : "admin" })
		adminGroup = adminGroup[0]

		# Adding default root user
		rootUser = auth._user().getAsClass(query={ "username" : "root" })
		if len(rootUser) == 0:
			rootPass = randomString(30)
			rootUser = auth._user().new("root","root",rootPass)
			rootUser = auth._user().getAsClass(query={ "username" : "root" })
			logging.debug("Root user created! Password is: {}".format(rootPass),-1)
		rootUser = rootUser[0]

		# Adding root to group
		if rootUser._id not in adminGroup.members:
			adminGroup.members.append(rootUser._id)
			adminGroup.update(["members"])

		# Adding primary group for root user
		rootUser.primaryGroup = adminGroup._id
		rootUser.update(["primaryGroup"])

		# Adding model for plugin
		model.registerModel("plugin","_plugin","_document","core.plugin")
		pluginModel = model._model().query(query={ "name" : "plugin" })["results"]
		if len(pluginModel) == 1:
			pluginModel = pluginModel[0]
			from core import plugin
			plugins = plugin._plugin().getAsClass()
			for pluginObj in plugins:
				pluginObj.classID = pluginModel["_id"]
				pluginObj.update(["classID"])

		# Updating ACLs
		from core.models import trigger
		triggers = trigger._trigger().query()["results"]
		for triggerItem in triggers:
			temp = trigger._trigger().get(triggerItem["_id"])
			temp.acl = { "ids" : [ { "accessID" : adminGroup._id, "read" : True, "write" : True, "delete" : True } ] }
			temp.update(["acl"])

		from core.models import action
		actions = action._action().query()["results"]
		for actionItem in actions:
			temp = action._action().get(actionItem["_id"])
			temp.acl = { "ids" : [ { "accessID" : adminGroup._id, "read" : True, "write" : True, "delete" : True } ] }
			temp.update(["acl"])

		from core.models import conduct
		conducts = conduct._conduct().query()["results"]
		for conductItem in conducts:
			temp = conduct._conduct().get(conductItem["_id"])
			temp.acl = { "ids" : [ { "accessID" : adminGroup._id, "read" : True, "write" : True, "delete" : True } ] }
			temp.update(["acl"])

		# Attempt to upgrade any plugins
		upgradeInstalledPlugins()

		return True

	## 0.3 ##
	# Upgrade varDefintions from versions older than 0.21
	def upgrade021_varDefinitions(_class,jsonResult):
		if "varDefinitions" in jsonResult:
			if type(jsonResult["varDefinitions"]) is list:
				if len(jsonResult["varDefinitions"]) > 0:
					varDefinitions = {}
					for varDefinition in jsonResult["varDefinitions"]:
						varDefinitions[varDefinition[0]] = { "value" : varDefinition[1] }
					_class.varDefinitions = varDefinitions
					_class.update(["varDefinitions"])
	if systemVersion > 0.2 and currentVersion < 0.31:
		# Adds new systemID to system about table for future cluster support
		systemAbout = _system().query(query={ "name" : "about" })["results"]
		systemAbout = systemAbout[0]["_id"]
		systemAbout = _system().get(systemAbout)
		systemAbout.systemID = systemSettings["systemID"]
		systemAbout.update(["systemID"])

		# Convert trigger and action varDefinitions to new dict format
		from core.models import trigger
		foundTriggers = trigger._trigger().query()["results"]
		for foundTrigger in foundTriggers:
			tempTrigger = trigger._trigger().get(foundTrigger["_id"])
			upgrade021_varDefinitions(tempTrigger,foundTrigger)
		from core.models import action
		foundActions = action._action().query()["results"]
		for foundAction in foundActions:
			tempAction = action._action().get(foundAction["_id"])
			upgrade021_varDefinitions(tempAction,foundAction)

		# Convert plugin int to float
		from core import plugin
		foundPlugins = plugin._plugin().query()["results"]
		for foundPlugin in foundPlugins:
			tempPlugin = plugin._plugin().get(foundPlugin["_id"])
			tempPlugin.version = float(foundPlugin["version"])
			tempPlugin.update(["version"])

		# Attempt to upgrade any plugins
		upgradeInstalledPlugins()

		return True
		
	return False

