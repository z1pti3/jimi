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

api.createServer("jimi_web",template_folder=str(Path("react-web","build")),static_folder=str(Path("react-web","build","static")))

#api.createServer("jimi_web",template_folder=str(Path("web","templates")),static_folder=str(Path("web","static")))

from core import model, cluster

# Other pages
from web import modelEditor, conductEditor, codify

# Add plugin blueprints
pluginPages = []
plugins = os.listdir("plugins")
for plugin in plugins:
	if os.path.isfile(Path("plugins/{0}/web/{0}.py".format(plugin))):
		mod = __import__("plugins.{0}.web.{0}".format(plugin), fromlist=["pluginPages"])
		api.webServer.register_blueprint(mod.pluginPages,url_prefix='/plugin')
		hidden = False
		try:
			hidden = mod.pluginPagesHidden
		except:
			pass
		if not hidden:
			pluginPages.append(plugin)

from core import logging, db

# Installing
if "webui" not in db.list_collection_names():
	if logging.debugEnabled:
		logging.debug("DB Collection webui Not Found : Creating...")
	model.registerModel("flowData","_flowData","_document","core.models.webui")

from core import audit, helpers, plugin, auth

from core.models import conduct, action, trigger, webui

@api.webServer.errorhandler(404)
def notFound(e):
	return render_template("index.html")

@api.webServer.route("/")
def indexPage():
	return render_template("index.html")

#@api.webServer.route("/")
#def mainPage():
#	from system import install
#	return render_template("main.html", version=install.installedVersion(), admin=api.g.sessionData["admin"])

# Should be migrated into plugins.py
@api.webServer.route(api.base+"plugins/")
def loadPluginPages():
	userPlugins = []
	userModels = plugin._plugin().getAsClass(sessionData=api.g.sessionData,query={ "name" : { "$in" : pluginPages } },sort=[("name", 1)])
	for userModel in userModels:
		if userModel.name in pluginPages:
			userPlugins.append({ "id" : userModel._id, "name" : userModel.name})
	return { "results"  : userPlugins }, 200

# Should be migrated into models/conduct.py
@api.webServer.route(api.base+"conducts/")
def loadConducts():
	return { "results" : conduct._conduct().query(api.g.sessionData,query={ "name" : { "$exists" : True } },sort=[( "name", 1 )])["results"] }, 200

# Should be migrated into workers.py
@api.webServer.route(api.base+"/workers/", methods=["GET"])
@auth.adminEndpoint
def workerPage():
	apiEndpoint = "workers/"
	servers = cluster.getAll()
	results = []
	for url in servers:
		response = helpers.apiCall("GET",apiEndpoint,token=api.g.sessionToken,overrideURL=url)
		responseJson = json.loads(response.text)
		if responseJson:
			for job in responseJson["results"]:
				job["server"] = url
				results.append(job)
	return { "results" : results }, 200

# Should be migrated into admin.py or cache.py
@api.webServer.route(api.base+"/clearCache/", methods=["GET"])
@auth.adminEndpoint
def clearCachePage():
	results = []
	apiEndpoint = "admin/clearCache/"
	servers = cluster.getAll()
	for url in servers:
		response = helpers.apiCall("GET",apiEndpoint,token=api.g.sessionToken,overrideURL=url)
		if response.status_code != 200:
			results.append({ "server" : url, "result" : False })
		else:
			results.append({ "server" : url, "result" : True })
	return { "results" : results }, 200

# Should be migrated into admin.py
@api.webServer.route(api.base+"/clearStartChecks/", methods=["GET"])
@auth.adminEndpoint
def clearStartChecksPage():
	apiEndpoint = "admin/clearStartChecks/"
	url = cluster.getMaster()
	response = helpers.apiCall("GET",apiEndpoint,token=api.g.sessionToken,overrideURL=url)
	if response.status_code != 200:
		return { "server" : url, "result" : False }, 403
	else:
		return { "server" : url, "result" : True }, 200

@api.webServer.route("/login")
def loginPage():
	return render_template("index.html")

@api.webServer.route("/conduct/PropertyTypes/", methods=["GET"])
def getConductPropertyTypes():
	result = []
	models = model._model().query(api.g.sessionData,query={ 
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
	conductObj = conduct._conduct().query(api.g.sessionData,id=conductID)["results"]
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
				triggerObj = trigger._trigger().query(api.g.sessionData,id=flow["triggerID"])["results"]
				if len(triggerObj) == 1:
					triggerObj = triggerObj[0]
				else:
					return {}, 404
				_class = model._model().getAsClass(api.g.sessionData,id=triggerObj["classID"])
				if len(_class) == 1:
					_class = _class[0].classObject()
				else:
					return {}, 404
				triggerObj = _class().getAsClass(api.g.sessionData,id=triggerObj["_id"])
				if len(triggerObj) == 1:
					triggerObj = triggerObj[0]
				else:
					return {},404
				if "_properties" in dir(triggerObj):
					formData = triggerObj._properties().generate(triggerObj)
				else:
					formData = webui._properties().generate(triggerObj)
			elif flow["type"] == "action":
				actionObj = action._action().query(api.g.sessionData,id=flow["actionID"])["results"]
				if len(actionObj) == 1:
					actionObj = actionObj[0]
				else:
					return {},404
				_class = model._model().getAsClass(api.g.sessionData,id=actionObj["classID"])
				if len(_class) == 1:
					_class = _class[0].classObject()
				actionObj = _class().getAsClass(api.g.sessionData,id=actionObj["_id"])
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
	conductObj = conduct._conduct().query(api.g.sessionData,id=conductID)["results"]
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
	conductObj = conduct._conduct().query(api.g.sessionData,id=conductID)["results"]
	if len(conductObj) == 1:
		conductObj = conductObj[0]
	else:
		return {}, 404
	flow = [ x for x in conductObj["flow"] if x["flowID"] ==  flowID]
	flow = flow[0]
	data = json.loads(api.request.data)
	apiEndpoint = "scheduler/{0}/".format(flow["triggerID"])
	if "_id" in api.g.sessionData:
		audit._audit().add("trigger","force",{ "_id" : api.g.sessionData["_id"], "user" : api.g.sessionData["user"], "conductID" : conductID, "flowID" : flowID })
	else:
		audit._audit().add("trigger","force",{ "user" : "system", "conductID" : conductID, "flowID" : flowID })
	host,port = cluster.getMaster()
	url="http://{0}:{1}".format(host,port)
	helpers.apiCall("POST",apiEndpoint,{ "action" : "trigger", "events" : data["events"] },token=api.g.sessionToken,overrideURL=url)
	return { }, 200

@api.webServer.route("/conduct/<conductID>/flowlogic/<flowID>/<nextflowID>/", methods=["GET"])
def getConductFlowLogic(conductID,flowID,nextflowID):
	conductObj = conduct._conduct().query(api.g.sessionData,id=conductID)["results"]
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
	conductObj = conduct._conduct().getAsClass(api.g.sessionData,id=conductID)
	if len(conductObj) == 1:
		conductObj = conductObj[0]
	else:
		return {},404
	access, accessIDs, adminBypass = db.ACLAccess(api.g.sessionData,conductObj.acl,"write")
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
						if "_id" in api.g.sessionData:
							audit._audit().add("flowLogic","update",{ "_id" : api.g.sessionData["_id"], "user" : api.g.sessionData["user"], "conductID" : conductID, "flowID" : flowID, "nextflowID" : nextflowID, "logic" : data["logic"] })
						else:
							audit._audit().add("flowLogic","update",{ "user" : "system", "conductID" : conductID, "flowID" : flowID , "nextflowID" : nextflowID, "logic" : data["logic"] })
						conductObj.update(["flow"],sessionData=api.g.sessionData)
						return { }, 200
	else:
		return {},403
	return { }, 404	

# @api.webServer.route("/admin/settings/", methods=["GET"])
# def settingsPage():
# 	if api.g.sessionData:
# 		if "admin" in api.g.sessionData:
# 			if api.g.sessionData["admin"]:
# 				return render_template("blank.html", content="Settings")
# 	return {}, 403

# @api.webServer.route("/audit/", methods=["GET"])
# def auditPage():
# 	if api.g.sessionData:
# 		if "admin" in api.g.sessionData:
# 			if api.g.sessionData["admin"]:
# 				auditData = audit._audit().query(query={},fields=["_id","time","source","type","data","systemID"],limit=1000,sort=[( "_id", -1 )])["results"]
# 				auditContent = []
# 				for auditItem in auditData:
# 					if "time" in auditItem:
# 						auditItem["time"] = time.strftime('%d/%m/%Y %H:%M:%S', time.gmtime(auditItem["time"]))
# 					auditContent.append(auditItem)
# 				return render_template("audit.html", content=auditContent)
# 	return {}, 403

# @api.webServer.route("/admin/backups/", methods=["GET"])
# def backupsPage():
# 	if api.g.sessionData:
# 		if "admin" in api.g.sessionData:
# 			if api.g.sessionData["admin"]:
# 				return render_template("backups.html", content="", CSRF=api.g.sessionData["CSRF"])
# 	return {}, 403

# @api.webServer.route("/admin/backup-system/", methods=["GET"])
# def backup():
# 	if api.g.sessionData:
# 		if "admin" in api.g.sessionData:
# 			if api.g.sessionData["admin"]:
# 				process = subprocess.Popen(["mongodump","--db={}".format(db.mongodbSettings["db"]),"--archive=/tmp/tempDBfile"], shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
# 				stdout, stderr = process.communicate()
# 				if process.returncode == 0:
# 					return send_file('/tmp/tempDBfile', as_attachment=True, attachment_filename="{}-{}.jimi.backup".format(db.mongodbSettings["db"],str(time.time()).split(".")[0]))
# 				if process.returncode == 1:
# 					return render_template("blank.html", content="Backup Failed!\nError Message: {}".format(str(stderr)))	
# 	return {} , 403

# @api.webServer.route("/admin/restore-system/", methods=["POST"])
# def restore():
# 	if api.g.sessionData:
# 		if "admin" in api.g.sessionData:
# 			if api.g.sessionData["admin"]:
# 				if "_id" in api.g.sessionData:
# 					audit._audit().add("system","restore start",{ "_id" : api.g.sessionData["_id"], "user" : api.g.sessionData["user"] })
# 				else:
# 					audit._audit().add("system","restore start",{ "user" : "system" })
# 				if "file" not in request.files:
# 					flash("No file found")
# 					return redirect("/admin/backups")
# 				file = request.files["file"]
# 				if file.filename == '':
# 					flash('No selected file')
# 					return redirect("/admin/backups")
# 				if file:
# 					filename = secure_filename(file.filename)
# 					file.save("/tmp/12345678-backup")
# 					process = subprocess.Popen(["mongorestore","--nsInclude=\"{}.*\"".format(db.mongodbSettings["db"]),"--archive=/tmp/12345678-backup","--drop"], shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
# 					stdout, stderr = process.communicate()
# 					if "_id" in api.g.sessionData:
# 						audit._audit().add("system","restore end",{ "_id" : api.g.sessionData["_id"], "user" : api.g.sessionData["user"] })
# 					else:
# 						audit._audit().add("system","restore end",{ "user" : "system" })
# 					if process.returncode == 0:
# 						return render_template("blank.html", content="Restore Successful!")	
# 					if process.returncode == 1:
# 						return render_template("blank.html", content="Restore Failed!\nError Message: {}".format(str(stderr)))
# 	return {}, 403


@api.webServer.route("/cleanup/", methods=["GET","DELETE"])
@auth.adminEndpoint
def cleanupPage():
	actions = action._action().query(api.g.sessionData,query={ "name" : { "$nin" : ["resetTrigger","failedTriggers"] } },fields=["_id","name","lastUpdateTime"])["results"]
	triggers = trigger._trigger().query(api.g.sessionData,query={ "name" : { "$nin" : ["resetTrigger","failedTriggers"] } },fields=["_id","name","lastUpdateTime"])["results"]
	actionids = [ x["_id"] for x in actions ]
	triggerids = [ x["_id"] for x in triggers ]
	conducts = conduct._conduct().query(query={ "$or" : [ { "flow.triggerID" : { "$in" : triggerids } }, { "flow.actionID" : { "$in" : actionids } } ] },fields=["_id","name","flow"])["results"]
	for c in conducts:
		for flow in c["flow"]:
			if "actionID" in flow:
				if flow["actionID"] in actionids:
					actionids.remove(flow["actionID"])
			if "triggerID" in flow:
				if flow["triggerID"] in triggerids:
					triggerids.remove(flow["triggerID"])
	unusedActionObjects = []
	unusedActionObjectsIds = []
	for actionid in actionids:
		a = [ x for x in actions if x["_id"] == actionid ]
		if a:
			unusedActionObjects.append({ "name" : a[0]["name"], "_id" : a[0]["_id"] })
			unusedActionObjectsIds.append(db.ObjectId(a[0]["_id"]))
	unusedTriggerObjects = []
	unusedTriggerObjectsIds = []
	for triggerid in triggerids:
		t= [ x for x in triggers if x["_id"] == triggerid ]
		if t:
			unusedTriggerObjects.append({ "name" : t[0]["name"], "_id" : t[0]["_id"] })
			unusedTriggerObjectsIds.append(db.ObjectId(t[0]["_id"]))
	if request.method == "DELETE":
		action._action().api_delete(query={ "_id" : { "$in" : unusedActionObjectsIds } })
		trigger._trigger().api_delete(query={ "_id" : { "$in" : unusedTriggerObjectsIds } })
		return { },200
	return render_template("cleanupObjects.html", unusedActionObjects=unusedActionObjects, unusedTriggerObjects=unusedTriggerObjects, CSRF=api.g.sessionData["CSRF"])

api.startServer(debug=True, use_reloader=False, host=apiSettings["bind"], port=apiSettings["port"], threaded=True)

while True:
	time.sleep(1)