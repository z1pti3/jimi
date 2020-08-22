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
    logging.debug("DB Collection webui Not Found : Creating...")
    model.registerModel("flowData","_flowData","_document","core.models.webui")

from core import audit, helpers, plugin, auth

from core.models import conduct, action, trigger, webui

@api.webServer.route("/")
def mainPage():
	from system import install
	return render_template("main.html", version=install.installedVersion(), admin=api.g.sessionData["admin"])

@api.webServer.route("/plugins/")
def loadPluginPages():
	userPlugins = []
	userModels = model._model().getAsClass(sessionData=api.g.sessionData,query={ "name" : { "$in" : pluginPages } })
	for userModel in userModels:
		if userModel.name in pluginPages:
			userPlugins.append(userModel.name)
	return { "result"  :userPlugins }, 200

@api.webServer.route("/conducts/")
def loadConducts():
	return { "result" : conduct._conduct().query(api.g.sessionData,query={ "name" : { "$exists" : True } },sort=[( "name", 1 )])["results"] }, 200

@api.webServer.route("/login")
def loginPage():
	return render_template("login.html")

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

@api.webServer.route("/admin/settings/", methods=["GET"])
def settingsPage():
	if api.g.sessionData:
		if "admin" in api.g.sessionData:
			if api.g.sessionData["admin"]:
				return render_template("blank.html", content="Settings")
	return {}, 403

@api.webServer.route("/audit/", methods=["GET"])
def auditPage():
	if api.g.sessionData:
		if "admin" in api.g.sessionData:
			if api.g.sessionData["admin"]:
				auditData = audit._audit().query(query={},fields=["_id","time","source","type","data","systemID"],limit=1000,sort=[( "_id", -1 )])["results"]
				auditContent = []
				for auditItem in auditData:
					if "time" in auditItem:
						auditItem["time"] = time.strftime('%d/%m/%Y %H:%M:%S', time.gmtime(auditItem["time"]))
					auditContent.append(auditItem)
				return render_template("audit.html", content=auditContent)
	return {}, 403

@api.webServer.route("/workers/", methods=["GET"])
def workerPage():
	if api.g.sessionData:
		if "admin" in api.g.sessionData:
			if api.g.sessionData["admin"]:
				apiEndpoint = "workers/stats/"
				servers = cluster.getAll()
				content = ""
				for host, port in servers:
					url="http://{0}:{1}".format(host,port)
					content += "{0}:{1}".format(host,port)
					content += "<br>"
					response = helpers.apiCall("GET",apiEndpoint,token=api.g.sessionToken,overrideURL=url)
					if response:
						content += response.text
					content += "<br>"
				return render_template("workers.html", content=content)
	return {}, 403

@api.webServer.route("/clearCache/", methods=["GET"])
def clearCachePage():
	content = ""
	if api.g.sessionData:
		if "admin" in api.g.sessionData:
			if api.g.sessionData["admin"]:
				apiEndpoint = "admin/clearCache/"
				servers = cluster.getAll()
				for host, port in servers:
					content += "{0}:{1}".format(host,port)
					url="http://{0}:{1}".format(host,port)
					response = helpers.apiCall("GET",apiEndpoint,token=api.g.sessionToken,overrideURL=url)
					if response.status_code != 200:
						content += "<br>Failure<br>"
					else:
						content += "<br>Success<br>"
	return render_template("workers.html", content=content)

@api.webServer.route("/cluster/", methods=["GET"])
def clusterPage():
	if api.g.sessionData:
		if "admin" in api.g.sessionData:
			if api.g.sessionData["admin"]:
				apiEndpoint = "cluster/"
				host,port = cluster.getMaster()
				url="http://{0}:{1}".format(host,port)
				content = helpers.apiCall("GET",apiEndpoint,token=api.g.sessionToken,overrideURL=url)
				if content:
					content = content.text
				return render_template("blank.html", content=content)
	return {}, 403

@api.webServer.route("/myAccount/", methods=["GET"])
def myAccountPage():
	return render_template("myAccount.html", CSRF=api.g.sessionData["CSRF"])

@api.webServer.route("/admin/backups/", methods=["GET"])
def backupsPage():
	if api.g.sessionData:
		if "admin" in api.g.sessionData:
			if api.g.sessionData["admin"]:
				return render_template("backups.html", content="", CSRF=api.g.sessionData["CSRF"])
	return {}, 403

@api.webServer.route("/admin/backup-system/", methods=["GET"])
def backup():
	if api.g.sessionData:
		if "admin" in api.g.sessionData:
			if api.g.sessionData["admin"]:
				process = subprocess.Popen(["mongodump","--db={}".format(db.mongodbSettings["db"]),"--archive=/tmp/tempDBfile"], shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
				stdout, stderr = process.communicate()
				if process.returncode == 0:
					return send_file('/tmp/tempDBfile', as_attachment=True, attachment_filename="{}-{}.jimi.backup".format(db.mongodbSettings["db"],str(time.time()).split(".")[0]))
				if process.returncode == 1:
					return render_template("blank.html", content="Backup Failed!\nError Message: {}".format(str(stderr)))	
	return {} , 403

@api.webServer.route("/admin/restore-system/", methods=["POST"])
def restore():
	if api.g.sessionData:
		if "admin" in api.g.sessionData:
			if api.g.sessionData["admin"]:
				if "_id" in api.g.sessionData:
					audit._audit().add("system","restore start",{ "_id" : api.g.sessionData["_id"], "user" : api.g.sessionData["user"] })
				else:
					audit._audit().add("system","restore start",{ "user" : "system" })
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
					if "_id" in api.g.sessionData:
						audit._audit().add("system","restore end",{ "_id" : api.g.sessionData["_id"], "user" : api.g.sessionData["user"] })
					else:
						audit._audit().add("system","restore end",{ "user" : "system" })
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