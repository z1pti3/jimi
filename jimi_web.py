# Javascript is poorly coded and needs large amounts of work to make it better
# API is not REST compliant
# Reduce number of API calls between javascript and python server
# API calls allow you to return too much information, there are also object returned that are system objects and these need to be filtered

from flask import Flask, request, render_template, make_response, redirect, send_file, flash
from werkzeug.utils import secure_filename
import _thread
import time
import json
import requests
import uuid
from pathlib import Path
import re
import subprocess
import os

# Setup and define API ( required before other modules )
from core import api, settings
apiSettings = settings.config["api"]["web"]

api.createServer("jimi_web",template_folder=str(Path("web","templates")),static_folder=str(Path("web","static")))

from core import model

# Other pages
from web import modelEditor, conductEditor

# Add plugin blueprints
pluginPages = []
plugins = os.listdir("plugins")
for plugin in plugins:
	if os.path.isfile(Path("plugins/{0}/web/{0}.py".format(plugin))):
		mod = __import__("plugins.{0}.web.{0}".format(plugin), fromlist=["pluginPages"])
		api.webServer.register_blueprint(mod.pluginPages,url_prefix='/plugin')
		pluginPages.append(plugin)

# Plugin support - not dynamic yet
#from plugins.occurrence.web import occurrence as occurrencePages
#api.webServer.register_blueprint(occurrencePages.occurrencePages)



#from plugins.ansible.web import ansible as ansiblePages
#api.webServer.register_blueprint(ansiblePages.ansiblePages)

#from plugins.asset.web import asset as assetPages
#api.webServer.register_blueprint(assetPages.assetPages,url_prefix='/plugin')

from core import logging, db

# Installing
if "webui" not in db.list_collection_names():
    logging.debug("DB Collection webui Not Found : Creating...")
    model.registerModel("flowData","_flowData","_document","core.models.webui")

from core import audit, helpers, plugin, auth

from core.models import conduct, action, trigger, webui

@api.webServer.route("/")
def mainPage():
	from system import install
	return render_template("main.html", conducts=conduct._conduct().query(api.g["sessionData"],query={ "name" : { "$exists" : True } },sort=[( "name", 1 )])["results"], version=install.installedVersion(), pluginPages=pluginPages)

@api.webServer.route("/login")
def loginPage():
	return render_template("login.html")

def buildFlowData(conductFlow):
	flowData = {}
	flowData["operators"] = {}
	flowData["links"] = {}

	# Not the best way to build these - neaten them up by saving states into DB

	# Create Objects
	for flow in conductFlow:
		flowData["operators"][flow["flowID"]] = {}
		flowData["operators"][flow["flowID"]]["left"] = 4000 + (500 * len(flowData["operators"]))
		flowData["operators"][flow["flowID"]]["top"] = 4600 + (100 * len(flowData["operators"]))
		flowData["operators"][flow["flowID"]]["properties"] = {}
		flowData["operators"][flow["flowID"]]["properties"]["title"] = flow["flowID"]
		flowData["operators"][flow["flowID"]]["properties"]["inputs"] = {}
		flowData["operators"][flow["flowID"]]["properties"]["outputs"] = {}
		for nextFlow in flow["next"]:
			flowData["operators"][flow["flowID"]]["properties"]["outputs"][nextFlow] = {}
			flowData["operators"][flow["flowID"]]["properties"]["outputs"][nextFlow]["label"] = ">"
		
		# Build this into javascript on link create function
		if flow["type"] == "action":
			flowData["operators"][flow["flowID"]]["properties"]["inputs"]["new_input"] = {}
			flowData["operators"][flow["flowID"]]["properties"]["inputs"]["new_input"]["label"] = "new_input"
		flowData["operators"][flow["flowID"]]["properties"]["outputs"]["new_output"] = {}
		flowData["operators"][flow["flowID"]]["properties"]["outputs"]["new_output"]["label"] = "new_output"

	# Link Objects
	for flowItem in flowData["operators"]:
		if len(flowData["operators"][flowItem]["properties"]["outputs"]) > 0:
			for output in flowData["operators"][flowItem]["properties"]["outputs"]:
				if output in flowData["operators"]:
					flowData["operators"][output]["properties"]["inputs"][flowItem] = {}
					flowData["operators"][output]["properties"]["inputs"][flowItem]["label"] = ">"
					flowData["links"]["{0}>{1}".format(flowItem,output)] = {}
					flowData["links"]["{0}>{1}".format(flowItem,output)]["fromOperator"] = flowItem
					flowData["links"]["{0}>{1}".format(flowItem,output)]["fromConnector"] = output
					flowData["links"]["{0}>{1}".format(flowItem,output)]["toOperator"] = output
					flowData["links"]["{0}>{1}".format(flowItem,output)]["toConnector"] = flowItem
	return flowData

@api.webServer.route("/conduct/PropertyTypes/", methods=["GET"])
def getConductPropertyTypes():
	result = []
	models = model._model().query(api.g["sessionData"],query={ 
		"$and" : [ 
			{ 
				"$or" : [ 
					{ "name" : "action" }, 
					{ "classType" : "_action" }, 
					{ "classType" : "_trigger" }, 
					{ "name" : "trigger" } 
				]
			},
			{ 
				"$or" : [ 
					{ "hidden" : False }, 
					{ "hidden" : { "$exists" : False } }
				]
			}
		]
	},sort=[( "name", 1 )])["results"]
	for modelItem in models:
		result.append({ "_id" : modelItem["_id"], "name" : modelItem["name"] })
	return { "results" : result }, 200

@api.webServer.route("/conduct/<conductID>/flowProperties/<flowID>/", methods=["GET"])
def getConductFlowProperties(conductID,flowID):
	conductObj = conduct._conduct().query(api.g["sessionData"],id=conductID)["results"]
	if len(conductObj) == 1:
		conductObj = conductObj[0]
	else:
		return {}, 404
	flow = [ x for x in conductObj["flow"] if x["flowID"] ==  flowID]
	if len(flow) == 1:
		flow = flow[0]
		formData = None
		if "type" in flow:
			if flow["type"] == "trigger":
				triggerObj = trigger._trigger().query(api.g["sessionData"],id=flow["triggerID"])["results"]
				if len(triggerObj) == 1:
					triggerObj = triggerObj[0]
				else:
					return {}, 404
				_class = model._model().getAsClass(api.g["sessionData"],id=triggerObj["classID"])
				if len(_class) == 1:
					_class = _class[0].classObject()
				else:
					return {}, 404
				triggerObj = _class().getAsClass(api.g["sessionData"],id=triggerObj["_id"])
				if len(triggerObj) == 1:
					triggerObj = triggerObj[0]
				else:
					return {},404
				if "_properties" in dir(triggerObj):
					formData = triggerObj._properties().generate(triggerObj)
				else:
					formData = webui._properties().generate(triggerObj)
			elif flow["type"] == "action":
				actionObj = action._action().query(api.g["sessionData"],id=flow["actionID"])["results"]
				if len(actionObj) == 1:
					actionObj = actionObj[0]
				else:
					return {},404
				_class = model._model().getAsClass(api.g["sessionData"],id=actionObj["classID"])
				if len(_class) == 1:
					_class = _class[0].classObject()
				actionObj = _class().getAsClass(api.g["sessionData"],id=actionObj["_id"])
				if len(actionObj) == 1:
					actionObj = actionObj[0]
				else:
					return {}, 404
				if "_properties" in dir(actionObj):
					formData = actionObj._properties().generate(actionObj)
				else:
					formData = webui._properties().generate(actionObj)
		return { "formData" : formData }, 200

@api.webServer.route("/conduct/<conductID>/flow/<flowID>/", methods=["GET"])
def getConductFlow(conductID,flowID):
	conductObj = conduct._conduct().query(api.g["sessionData"],id=conductID)["results"]
	if len(conductObj) == 1:
		conductObj = conductObj[0]
	else:
		return {},404
	flow = [ x for x in conductObj["flow"] if x["flowID"] ==  flowID]
	if len(flow) == 1:
		flow = flow[0]
		if "type" in flow:
			flowType = flow["type"]
			if "{0}{1}".format(flowType,"ID") in flow:
				result = { "type" : flowType, "{0}{1}".format(flowType,"ID") : flow["{0}{1}".format(flowType,"ID")]}
				return { "result" : result }, 200
	return { }, 404

@api.webServer.route("/conduct/<conductID>/forceTrigger/<flowID>/", methods=["POST"])
def forceTrigger(conductID,flowID):
	conductObj = conduct._conduct().query(api.g["sessionData"],id=conductID)["results"]
	if len(conductObj) == 1:
		conductObj = conductObj[0]
	else:
		return {}, 404
	flow = [ x for x in conductObj["flow"] if x["flowID"] ==  flowID]
	flow = flow[0]
	data = json.loads(api.request.data)
	apiEndpoint = "scheduler/{0}/".format(flow["triggerID"])
	helpers.apiCall("POST",apiEndpoint,{ "action" : "trigger", "events" : data["events"] })
	return { }, 200

@api.webServer.route("/conduct/<conductID>/debug/<flowID>/", methods=["GET"])
def debugItem(conductID,flowID):
	conductObj = conduct._conduct().query(api.g["sessionData"],id=conductID)["results"]
	if len(conductObj) == 1:
		conductObj = conductObj[0]
	else:
		return {}, 404
	flow = [ x for x in conductObj["flow"] if x["flowID"] ==  flowID]
	flow = flow[0]
	if "type" in flow:
		if flow["type"] == "trigger":
			return { "_id" : flow["triggerID"] }, 200
		elif flow["type"] == "action":
			return { "_id" : flow["actionID"] }, 200
	return { }, 404

@api.webServer.route("/conduct/<conductID>/flowlogic/<flowID>/<nextflowID>/", methods=["GET"])
def getConductFlowLogic(conductID,flowID,nextflowID):
	conductObj = conduct._conduct().query(api.g["sessionData"],id=conductID)["results"]
	if len(conductObj) == 1:
		conductObj = conductObj[0]
	else:
		return {}, 404
	flow = [ x for x in conductObj["flow"] if x["flowID"] ==  flowID]
	if len(flow) == 1:
		flow = flow[0]
		if "next" in flow:
			for nextFlow in flow["next"]:
				if type(nextFlow) is str:
					if nextflowID == nextFlow:
						return {"result" : {"logic" : True}}, 200
				elif type(nextFlow) is dict:
					if nextflowID == nextFlow["flowID"]:
						return {"result" : {"logic" : nextFlow["logic"]}}, 200
	return { }, 404	

@api.webServer.route("/conduct/<conductID>/flowlogic/<flowID>/<nextflowID>/", methods=["POST"])
def setConductFlowLogic(conductID,flowID,nextflowID):
	conductObj = conduct._conduct().getAsClass(api.g["sessionData"],id=conductID)
	if len(conductObj) == 1:
		conductObj = conductObj[0]
	else:
		return {},404
	access, accessIDs, adminBypass = db.ACLAccess(api.g["sessionData"],conductObj.acl,"write")
	if access:
		flow = [ x for x in conductObj.flow if x["flowID"] ==  flowID]
		data = json.loads(api.request.data)
		if len(flow) == 1:
			flow = flow[0]
			if "next" in flow:
				found = False
				for key, nextFlow in enumerate(flow["next"]):
					if type(nextFlow) is str:
						if nextFlow == nextflowID:
							nextFlow = {"flowID" : nextflowID}
							found = True
					elif type(nextFlow) is dict:
						if nextFlow["flowID"] == nextflowID:
							found = True	
					if found:
						if "true" == data["logic"].lower():
							flow["next"][key] = {"flowID" : nextFlow["flowID"], "logic" : True}
						elif "false" == data["logic"].lower():
							flow["next"][key] = {"flowID" : nextFlow["flowID"], "logic" : False}
						elif data["logic"].startswith("if"):
							flow["next"][key] = {"flowID" : nextFlow["flowID"], "logic" : data["logic"]}
						else:
							try:
								flow["next"][key] = {"flowID" : nextFlow["flowID"], "logic" : int(data["logic"])}
							except ValueError:
								return { }, 403
						conductObj.update(["flow"])
						return { }, 200
	else:
		return {},403
	return { }, 404	

# Create/Update flow and flow class items
@api.webServer.route("/conduct/<conductID>/flow/<flowID>/", methods=["POST"])
def setConductFlow(conductID,flowID):
	# List of attributes that are prevented from updating - this needs to be made more dynamic and part of class design
	unsafeUpdateList = [ "_id", "classID", "lastCheck", "lastRun", "lastResult", "workerID", "startCheck" ]

	conductObj = conduct._conduct().query(api.g["sessionData"],id=conductID)["results"]
	conductObj = conductObj[0]
	conductObj = conduct._conduct().getAsClass(api.g["sessionData"],id=conductObj["_id"])
	if len(conductObj) == 1:
		conductObj = conductObj[0]
	else:
		return {},404
	flow = [ x for x in conductObj.flow if x["flowID"] ==  flowID]
	if len(flow) == 1:
		flow = flow[0]
		data = json.loads(api.request.data)
		modelFlowObject = None
		# Check if the modelType and object are unchanged
		if "type" in flow:
			if flow["type"] == "trigger":
				modelFlowObject = trigger._trigger().getAsClass(api.g["sessionData"],id=flow["{0}{1}".format(flow["type"],"ID")])
				if len(modelFlowObject) == 1:
					modelFlowObject = modelFlowObject[0]
				modelFlowObjectType = "trigger"
			if flow["type"] == "action":
				modelFlowObject = action._action().getAsClass(api.g["sessionData"],id=flow["{0}{1}".format(flow["type"],"ID")])
				if len(modelFlowObject) == 1:
					modelFlowObject = modelFlowObject[0]
				modelFlowObjectType = "action"

			# Was it possible to load an existing object
			if modelFlowObject:
				# Check that the object model is still the same
				if modelFlowObject.classID == data["newClassID"]:
					# Get flow object correct class
					_class = model._model().getAsClass(api.g["sessionData"],id=modelFlowObject.classID)
					if len(_class) == 1:
						_class = _class[0]
						_class = _class.classObject()
					else:
						return {},404
					modelFlowObject = _class().getAsClass(api.g["sessionData"],id=modelFlowObject._id)
					if len(modelFlowObject) == 1:
						modelFlowObject = modelFlowObject[0]
					else:
						return {},404
				else:
					modelFlowObject = None

		# New object required
		if not modelFlowObject:
			_class = model._model().getAsClass(api.g["sessionData"],id=data["newClassID"])
			if _class:
				_class = _class[0].classObject()
				# Bug exists as name value is not requried by db class but is for core models - this could result in an error if new model is added that does not accept name within new function override
				newFlowObjectID = _class().new(flow["flowID"]).inserted_id
				

				# Working out by bruteforce which type this is ( try and load it by parent class and check for error) - get on trigger if it does not exist will return None
				modelFlowObjectType = "action"
				if len(trigger._trigger().getAsClass(api.g["sessionData"],id=newFlowObjectID)) > 0:
					modelFlowObjectType = "trigger"
				modelFlowObject = _class().getAsClass(api.g["sessionData"],id=newFlowObjectID)
				if len(modelFlowObject) == 1:
					modelFlowObject = modelFlowObject[0]
				else:
					return { }, 404
				modelFlowObject.acl = { "ids" : [ { "accessID" : api.g["sessionData"]["primaryGroup"], "read" : True, "write" : True, "delete" : True } ] }
				modelFlowObject.update(["acl"])

				# Set conduct flow to correct type and objectID
				flow["type"] = modelFlowObjectType
				flow["{0}{1}".format(modelFlowObjectType,"ID")] = str(newFlowObjectID)
				conductObj.update(["flow"])

		# Updating new or existing modeFlowObject
		if modelFlowObject:
			updateItemsList = []
			changeLog = {}
			# Getting schema information so types can be set correctly
			class_ = model._model().getAsClass(api.g["sessionData"],id=modelFlowObject.classID)
			if class_:
				_class = modelFlowObject
				# Builds list of permitted ACL
				access, accessIDs, adminBypass = db.ACLAccess(api.g["sessionData"],_class.acl,"write")
				if access:
					for dataKey, dataValue in data.items():
						fieldAccessPermitted = True
						# Checking if sessionData is permitted field level access
						if _class.acl and not adminBypass:
							fieldAccessPermitted = db.fieldACLAccess(accessIDs,_class.acl,dataKey,"write")
						if fieldAccessPermitted:
							# Change update database entry _id
							if dataKey not in unsafeUpdateList:
								if hasattr(_class, dataKey):
									changeLog[dataKey] = {}
									changeLog[dataKey]["currentValue"] = getattr(_class, dataKey)
									if type(getattr(_class, dataKey)) is str:
										if dataValue:
											if _class.setAttribute(dataKey, str(dataValue)):
												updateItemsList.append(dataKey)
												changeLog[dataKey]["newValue"] = getattr(_class, dataKey)
									elif type(getattr(_class, dataKey)) is int:
										try:
											if _class.setAttribute(dataKey, int(dataValue)):
												updateItemsList.append(dataKey)
												changeLog[dataKey]["newValue"] = getattr(_class, dataKey)
										except ValueError:
											if _class.setAttribute(dataKey, 0):
												updateItemsList.append(dataKey)
												changeLog[dataKey]["newValue"] = getattr(_class, dataKey)
									elif type(getattr(_class, dataKey)) is float:
										try:
											if _class.setAttribute(dataKey, float(dataValue)):
												updateItemsList.append(dataKey)
												changeLog[dataKey]["newValue"] = getattr(_class, dataKey)
										except ValueError:
											if _class.setAttribute(dataKey, 0):
												updateItemsList.append(dataKey)
												changeLog[dataKey]["newValue"] = getattr(_class, dataKey)
									elif type(getattr(_class, dataKey)) is bool:
										if _class.setAttribute(dataKey, bool(dataValue)):
											updateItemsList.append(dataKey)
											changeLog[dataKey]["newValue"] = getattr(_class, dataKey)
									elif type(getattr(_class, dataKey)) is dict or type(getattr(_class, dataKey)) is list:
										if dataValue:
											if _class.setAttribute(dataKey, json.loads(dataValue)):
												updateItemsList.append(dataKey)
												changeLog[dataKey]["newValue"] = getattr(_class, dataKey)
					# Commit back to database
					if updateItemsList:
						_class.update(updateItemsList)
						# Adding audit record
						if "_id" in api.g["sessionData"]:
							audit._audit().add("model","update",{ "_id" : api.g["sessionData"]["_id"], "objects" : helpers.unicodeEscapeDict(changeLog) })
						else:
							audit._audit().add("model","update",{ "objects" : helpers.unicodeEscapeDict(changeLog) })
					return { "type" :  modelFlowObjectType}, 200
				else:
					return { }, 403
	return { }, 404

@api.webServer.route("/conduct/<conductID>/", methods=["GET"])
def conductPage(conductID):
	conductObj = conduct._conduct().query(api.g["sessionData"],id=conductID)["results"]
	conductObj = conductObj[0]

	existingFlow = webui._flowData().query(query={"conductID" : conductID})["results"]
	if len(existingFlow) == 1:
		existingFlow = existingFlow[0]
		flowData = existingFlow["flowData"]
	else:
		flowData = buildFlowData(conductObj["flow"])

	if "acl" not in conductObj:
		conductObj["acl"] = {}
		
	return render_template("flow.html", conductID=conductObj["_id"], conductName=conductObj["name"], conductACL=conductObj["acl"], conductEnabled=conductObj["enabled"], content=conductObj, actions=action._action().query()["results"], triggers=trigger._trigger().query()["results"], flowData=flowData)

@api.webServer.route("/conduct/<conductID>/", methods=["POST"])
def saveConduct(conductID):
	data = json.loads(api.request.data)

	conductObj = conduct._conduct().getAsClass(api.g["sessionData"],id=conductID)
	if len(conductObj) == 1:
		conductObj = conductObj[0]
	else:
		return {},404

	if data["action"] == "new":
		access, accessIDs, adminBypass = db.ACLAccess(api.g["sessionData"],conductObj.acl,"write")
		if access:
			# Get new UUID store within current conduct flow and return UUID
			newFlowID = str(uuid.uuid4())
			flow = {
				"flowID" : newFlowID, 
				"next" : []
			}
			conductObj.flow.append(flow)
			conductObj.update(["flow"])
			return { "result" : True, "flowID" :  newFlowID}, 201
		else:
			return {},403

	# Clone an existing object into a new object
	if data["action"] == "clone":
		access, accessIDs, adminBypass = db.ACLAccess(api.g["sessionData"],conductObj.acl,"write")
		if access:
			flow = [ x for x in conductObj.flow if x["flowID"] ==  data["operatorId"]]
			if len(flow) == 1:
				flow = flow[0]
				data = json.loads(api.request.data)
				modelFlowObject = None
				# Check if the modelType and object are unchanged
				if "type" in flow:
					if flow["type"] == "trigger":
						modelFlowObject = trigger._trigger().getAsClass(api.g["sessionData"],id=flow["{0}{1}".format(flow["type"],"ID")])
						if len(modelFlowObject) == 1:
							modelFlowObject = modelFlowObject[0]
						modelFlowObjectType = "trigger"
					if flow["type"] == "action":
						modelFlowObject = action._action().getAsClass(api.g["sessionData"],id=flow["{0}{1}".format(flow["type"],"ID")])
						if len(modelFlowObject) == 1:
							modelFlowObject = modelFlowObject[0]
						modelFlowObjectType = "action"

					# Was it possible to load an existing object
					if modelFlowObject:
						# Create new flowItem
						newFlowID = str(uuid.uuid4())
						flow = {
							"flowID" : newFlowID, 
							"type" : flow["type"],
							"next" : []
						}
						# New object required
						_class = model._model().getAsClass(api.g["sessionData"],id=modelFlowObject.classID)
						if _class:
							_class = _class[0].classObject()
							# Bug exists as name value is not requried by db class but is for core models - this could result in an error if new model is added that does not accept name within new function override
							newFlowObjectID = _class().new(flow["flowID"]).inserted_id

							# Working out by bruteforce which type this is ( try and load it by parent class and check for error) - get on trigger if it does not exist will return None
							modelFlowObjectClone = _class().getAsClass(api.g["sessionData"],id=newFlowObjectID)
							if len(modelFlowObjectClone) == 1:
								modelFlowObjectClone = modelFlowObjectClone[0]
							else:
								return { }, 404

							# Setting values in cloned object
							members = [attr for attr in dir(modelFlowObject) if not callable(getattr(modelFlowObject, attr)) and not "__" in attr and attr ]
							dontCopy=["_id","name"]
							updateList = []
							for member in members:
								if member not in dontCopy:
									setattr(modelFlowObjectClone,member,getattr(modelFlowObject,member))
									updateList.append(member)
							modelFlowObjectClone.update(updateList)

							# Set conduct flow to correct type and objectID
							flow["{0}{1}".format(flow["type"],"ID")] = str(newFlowObjectID)
							conductObj.flow.append(flow)
							conductObj.update(["flow"])
			return { "result" : True, "flowID" :  newFlowID}, 201
		else:
			return {},403

	# Add existing object to flow
	elif data["action"] == "existing":
		access, accessIDs, adminBypass = db.ACLAccess(api.g["sessionData"],conductObj.acl,"write")
		if access:
			newFlowID = str(uuid.uuid4())
			flow = {
				"flowID" : newFlowID, 
				"next" : []
			}
			if data["type"] == "trigger":
				flow["type"] = "trigger"
				flow["triggerID"] = data["triggerID"]
			elif data["type"] == "action":
				flow["type"] = "action"
				flow["actionID"] = data["actionID"]
			conductObj.flow.append(flow)
			conductObj.update(["flow"])
			return { "result" : True, "flowID" :  newFlowID}, 201
		else:
			return {},403

	elif data["action"] == "save":
		access, accessIDs, adminBypass = db.ACLAccess(api.g["sessionData"],conductObj.acl,"write")
		if access:
			flowData = data["flowData"]
			newFlowData = {}
			flowPopList = []
			for flow in flowData['links']:
				if flow != "{}>{}".format(flowData['links'][flow]['fromOperator'],flowData['links'][flow]['toOperator']):
					newFlowData["{}>{}".format(flowData['links'][flow]['fromOperator'],flowData['links'][flow]['toOperator'])] = flowData['links'][flow]
					flowPopList.append(flow)
			if len(newFlowData) > 0:
				flowData['links'].update(newFlowData)
				for popItem in flowPopList:
					flowData['links'].pop(popItem)
			poplistOperator = []
			poplistLink = []
			for operatorID in flowData["operators"]:
				operatorFound = None
				for flow in conductObj.flow:
					flowID = flow["flowID"]
					if operatorID == flowID:
						operatorFound = flowID
						connections = []
						for link in flowData["links"]:
							if flowData["links"][link]["fromOperator"] == flowID:
								connections.append(flowData["links"][link]["toOperator"])
						for connection in connections:
							foundFlow = False
							for index, nextFlowID in enumerate(conductObj.flow[conductObj.flow.index(flow)]["next"]):
								if type(nextFlowID) is dict:
									if connection == nextFlowID["flowID"]:
										foundFlow = True
										conductObj.flow[conductObj.flow.index(flow)]["next"][index] = { "flowID" : connection, "logic" : nextFlowID["logic"] }
								else:
									if connection == nextFlowID:
										foundFlow = True
										conductObj.flow[conductObj.flow.index(flow)]["next"][index] = { "flowID" : connection, "logic" : True }
							if not foundFlow:
								conductObj.flow[conductObj.flow.index(flow)]["next"].append({ "flowID" : connection, "logic" : True })

						notUpdatedPopList = []
						for nextFlowID in conductObj.flow[conductObj.flow.index(flow)]["next"]:
							if nextFlowID["flowID"] not in connections:
								notUpdatedPopList.append(nextFlowID)
						for notUpdatedPopItem in notUpdatedPopList:
							del conductObj.flow[conductObj.flow.index(flow)]["next"][conductObj.flow[conductObj.flow.index(flow)]["next"].index(notUpdatedPopItem)]

				if not operatorFound:
					for link in flowData["links"]:
						if flowData["links"][link]["toOperator"] == operatorID or flowData["links"][link]["fromOperator"] == operatorID:
							poplistLink.append(link)
					poplistOperator.append(operatorID)

			# Checking to ensure every flow that exists is also still within the flowData i.e. it has not been deleted
			poplistFlow = []
			for flow in conductObj.flow:
				flowID = flow["flowID"]
				if len([ x for x in flowData["operators"] if x ==  flowID]) == 0:
					poplistFlow.append(flow)

			# Deleting any items that were found within flowData but not in the conduct flow
			for pop in poplistOperator:
				del flowData["operators"][pop]
			for pop in poplistLink:
				del flowData["links"][pop]
			for pop in poplistFlow:
				del conductObj.flow[conductObj.flow.index(pop)]

			# checking if conduct has been enabled or name changed
			if "conductName" in data:
				conductObj.name = data["conductName"]
			if "conductEnabled" in data:
				conductObj.enabled = data["conductEnabled"]
			if "conductACL" in data:
				try:
					conductObj.acl = json.loads(data["conductACL"])
				except:
					pass

			# Updating all possible updated values
			conductObj.update(["flow","name","enabled","acl"])
				
			existingFlow = webui._flowData().query(query={"conductID" : conductID})["results"]
			if len(existingFlow) > 0:
				existingFlow = existingFlow[0]
				existingFlow = webui._flowData().load(existingFlow["_id"])
				existingFlow.flowData = flowData
				existingFlow.update(["flowData"])
			else:
				webui._flowData().new(conductID,flowData)
				return { "result" : True, "flowData" : flowData }, 201
			return { "result" : True, "flowData" : flowData }, 200
		else:
			return {},403

	return { "result" : False }, 404


@api.webServer.route("/conduct/", methods=["POST"])
def newConduct():
	data = json.loads(api.request.data)
	if data["action"] == "new":
		class_ = model._model().getAsClass(api.g["sessionData"],query={"name" : "conduct"})
		if class_:
			class_ = class_[0]
			access, accessIDs, adminBypass = db.ACLAccess(api.g["sessionData"],class_.acl,"read")
			if access:
				conductID = str(conduct._conduct().new(data["name"]).inserted_id)
				return { "result" : True, "conductID" :  conductID}, 201
	return { }, 403

@api.webServer.route("/admin/settings/", methods=["GET"])
def settingsPage():
	if api.g["sessionData"]:
		if "admin" in api.g["sessionData"]:
			if api.g["sessionData"]["admin"]:
				return render_template("blank.html", content="Settings")
	return {}, 403

@api.webServer.route("/audit/", methods=["GET"])
def auditPage():
	if api.g["sessionData"]:
		if "admin" in api.g["sessionData"]:
			if api.g["sessionData"]["admin"]:
				auditData = audit._audit().query(query={},fields=["_id","time","source","type","data","systemID"],limit=1000,sort=[( "_id", -1 )])["results"]
				auditContent = []
				for auditItem in auditData:
					if "time" in auditItem:
						auditItem["time"] = time.strftime('%d/%m/%Y %H:%M:%S', time.gmtime(auditItem["time"]))
					auditContent.append(auditItem)
				return render_template("audit.html", content=auditContent)
	return {}, 403

@api.webServer.route("/debug/<debugID>/", methods=["GET"])
def debug(debugID):
	if api.g["sessionData"]:
		if "admin" in api.g["sessionData"]:
			if api.g["sessionData"]["admin"]:
				return render_template("debug.html", debugID=debugID)
	return {}, 403

@api.webServer.route("/workers/", methods=["GET"])
def workerPage():
	if api.g["sessionData"]:
		if "admin" in api.g["sessionData"]:
			if api.g["sessionData"]["admin"]:
				apiEndpoint = "workers/stats/"
				workerContent = helpers.apiCall("GET",apiEndpoint).text
				return render_template("workers.html", content=workerContent)
	return {}, 403

@api.webServer.route("/myAccount/", methods=["GET"])
def myAccountPage():
	return render_template("myAccount.html")

@api.webServer.route("/admin/backups/", methods=["GET"])
def backupsPage():
	if api.g["sessionData"]:
		if "admin" in api.g["sessionData"]:
			if api.g["sessionData"]["admin"]:
				return render_template("backups.html", content="")
	return {}, 403

@api.webServer.route("/admin/backup-system/", methods=["GET"])
def backup():
	if api.g["sessionData"]:
		if "admin" in api.g["sessionData"]:
			if api.g["sessionData"]["admin"]:
				process = subprocess.Popen(["mongodump","--db={}".format(db.mongodbSettings["db"]),"--archive=/tmp/tempDBfile"], shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
				stdout, stderr = process.communicate()
				if process.returncode == 0:
					return send_file('/tmp/tempDBfile', as_attachment=True, attachment_filename="{}-{}.jimi.backup".format(db.mongodbSettings["db"],str(time.time()).split(".")[0]))
				if process.returncode == 1:
					return render_template("blank.html", content="Backup Failed!\nError Message: {}".format(str(stderr)))	
	return {} , 403

@api.webServer.route("/admin/restore-system/", methods=["POST"])
def restore():
	if api.g["sessionData"]:
		if "admin" in api.g["sessionData"]:
			if api.g["sessionData"]["admin"]:
				if "file" not in request.files:
					flash("No file found")
					return redirect("/admin/backups")
				file = request.files["file"]
				if file.filename == '':
					flash('No selected file')
					return redirect("/admin/backups")
				if file:
					filename = secure_filename(file.filename)
					file.save("/tmp/12345678-backup")
					process = subprocess.Popen(["mongorestore","--nsInclude=\"{}.*\"".format(db.mongodbSettings["db"]),"--archive=/tmp/12345678-backup","--drop"], shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
					stdout, stderr = process.communicate()
					if process.returncode == 0:
						return render_template("blank.html", content="Restore Successful!")	
					if process.returncode == 1:
						return render_template("blank.html", content="Restore Failed!\nError Message: {}".format(str(stderr)))
	return {}, 403

@api.webServer.route("/status/", methods=["GET"])
def statusPage():
	triggers = trigger._trigger().query(fields=["_id","name","lastCheck","lastResult"])["results"]
	actions = action._action().query(fields=["_id","name","lastRun","lastResult"])["results"]
	# Bad programming dont just copy and past the same thing make it dynamic!!!!!!!!!!
	triggersContent = []
	for t in triggers:
		if "lastCheck" in t:
			t["lastCheck"] = time.strftime('%d/%m/%Y %H:%M:%S', time.gmtime(t["lastCheck"]))
		triggersContent.append(t)
	actionsContent = []
	for a in actions:
		if "lastRun" in a:
			a["lastRun"] = time.strftime('%d/%m/%Y %H:%M:%S', time.gmtime(a["lastRun"]))
		actionsContent.append(a)
	return render_template("status.html", triggers=triggersContent, actions=actionsContent)

api.startServer(debug=True, use_reloader=False, host=apiSettings["bind"], port=apiSettings["port"], threaded=True)

while True:
	time.sleep(1)