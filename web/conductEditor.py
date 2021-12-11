from math import e
import time
import json
import  uuid
import copy
from operator import itemgetter
from pathlib import Path
from urllib.parse import quote

from flask import Flask, request, render_template, make_response, redirect, send_file
from werkzeug.utils import send_from_directory

import jimi

@jimi.api.webServer.route("/conductEditor/", methods=["GET"])
def editConduct():
    conductID = request.args.get('conductID')
    conductObj = jimi.conduct._conduct().query(jimi.api.g.sessionData,id=conductID)["results"]
    if len(conductObj) == 1:
        conductObj = conductObj[0]
        # Load objects that the user can use
        objects = []
        models = jimi.model._model(False).query(jimi.api.g.sessionData,query={ 
            "$and" : [ 
                { 
                    "$or" : [ 
                        { "name" : "action" }, 
                        { "name" : "trigger" }, 
                        { "classType" : "_action" }, 
                        { "classType" : "_trigger" }
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
        for model in models:
            # trigger and action are part of _document class for UI purpose make them _trigger and _action
            if model["name"] == "trigger":
                model["classType"] = "_trigger"
            elif model["name"] == "action":
                model["classType"] = "_action"
            try:
                objects.append({ "type" : model["classType"], "classID" : model["_id"], "name" : model["name"], "description" : model["manifest"]["description"] })
            except KeyError:
                objects.append({ "type" : model["classType"], "classID" : model["_id"], "name" : model["name"], "description" : "" })
        triggers = jimi.trigger._trigger(False).query(sessionData=jimi.api.g.sessionData,query={ "scope" : { "$gt" : 0 } })["results"]
        for trigger in triggers:
            objects.append({ "type" : "existingTrigger", "_id" : trigger["_id"], "name" : trigger["name"], "description" : trigger["comment"] })
        actions = jimi.action._action(False).query(sessionData=jimi.api.g.sessionData,query={ "scope" : { "$gt" : 0 } })["results"]
        for action in actions:
            objects.append({ "type" : "existingAction", "_id" : action["_id"], "name" : action["name"], "description" : action["comment"] })
        return render_template("conductEditor.html", CSRF=jimi.api.g.sessionData["CSRF"],conductName=conductObj["name"],objects=objects)
    else:
        return { }, 404

@jimi.api.webServer.route("/conductEditor/<conductID>/", methods=["POST"])
def conductFlowchartPoll(conductID):
    conductObj = jimi.conduct._conduct().query(jimi.api.g.sessionData,id=conductID)["results"]
    if len(conductObj) == 1:
        conductObj = conductObj[0]
    else:
        return {},404
    data = json.loads(jimi.api.request.data)

    flowchartOperators = data["operators"]
    flowchartLinks = data["links"]

    flowchartResponse = { "operators" : { "delete" : {}, "create" : {}, "update" : {}, "nodes" : [] }, "links" : { "delete" : {}, "create" : {}, "update" : {}, "links" : [] } }

    # Getting all UI flow details for flows in this conduct
    flows = [ x for x in conductObj["flow"] ]
    flowTriggers = [ jimi.db.ObjectId(x["triggerID"]) for x in flows if x["type"] == "trigger" ]
    flowActions = [ jimi.db.ObjectId(x["actionID"]) for x in flows if x["type"] == "action" ]
    flowsList = [ x["flowID"] for x in flows ]
    nodesList = {}
    linksList = {}

    # For every refresh the entire flow object and UI is loaded from the database - this may need improvement for speed in future
    flowsUI = jimi.webui._modelUI().getAsClass(jimi.api.g.sessionData,query={ "flowID" : { "$in" :flowsList }, "conductID" : conductID })
    flowsUIByID = {}
    for obj in flowsUI:
        flowsUIByID[obj.flowID] = obj
    actions = jimi.action._action(False).getAsClass(jimi.api.g.sessionData,query={ "_id" : { "$in" : flowActions } })
    actionsByID = {}
    for obj in actions:
        actionsByID[obj._id] = obj
    triggers = jimi.trigger._trigger(False).getAsClass(jimi.api.g.sessionData,query={ "_id" : { "$in" : flowTriggers } })
    triggersByID = {}
    for obj in triggers:
        triggersByID[obj._id] = obj

    if not jimi.revision._revision().gotRecent(conductObj["_id"],conductObj["classID"]):
        # Get data without sessionData so that it is complete
        revisionData = { "conduct" : jimi.conduct._conduct().query(id=conductID)["results"], "modelUI" : jimi.webui._modelUI().query(query={ "flowID" : { "$in" :flowsList }, "conductID" : conductID }) }
        if not jimi.revision._revision().newCustomData(conductObj["_id"],conductObj["classID"],revisionData):
            return { "msg" : "Unable to create conduct revision" }, 403

    # Parse CSS Theme - Should cache this in future for improved speed? - If flow updates are slow this could be the problem????
    colors = {
        "nodeEnableColor" : "#0a0a0a",
        "nodeDisabledColor" : "gray",
        "nodeErrorColor" : "red",
        "nodeRunningColor" : "green",
        "nodeBorderColor" : "#595959",
        "nodeUnknownColor" : "black",
        "linkColor" : "green",
        "linkTrueColor" : "#6FA92D",
        "linkFalseColor" : "#FF392E",
        "linkRCColor" : "#FBB121",
        "linkLogicColor" : "#D04D8A",
        "linkAllColor" : "#3DBEFF",
        "nodeTextColor" : "#adadad"
    }
    try:
        themeFile = "web/build/static/themes/theme-{0}.css".format(jimi.api.g.sessionData["theme"])
        if jimi.helpers.safeFilepath(themeFile,"web/build/static/themes"):
            with open(Path(themeFile)) as f:
                themeFile = f.read()
            for colorName, colorValue in colors.items():
                if "--{0}: ".format(colorName) in themeFile:
                    colors[colorName] = themeFile.split("--{0}: ".format(colorName))[1].split(";")[0]
    except:
        pass

    # nodeShapeTemplate = """<svg xmlns="http://www.w3.org/2000/svg" width="390" height="65">
    #     <rect x="0" y="0" width="100%" height="100%" fill="#7890A7" stroke-width="20" stroke="#ffffff" >
    #     </rect>
    #     <foreignObject x="15" y="10" width="100%" height="100%">
    #         <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:40px">
    #             <em>I</em> am
    #             <span style="color:white; text-shadow:0 0 20px #000000;">
    #             HTML in SVG!</span>
    #         </div>
    #     </foreignObject>
    # </svg>
    # """
    # nodeShapeTemplate = "data:image/svg+xml;charset=utf-8,{0}".format(quote(nodeShapeTemplate))
    nodeTemplate = {
        "id" : "",
        "x" : 0,
        "y" : 0,
        "label" : "",
        "shape" : "box",
        "widthConstraint" : { 
            "minimum": 75, 
            "maximum": 275
        },
        "heightConstraint" : { 
            "minimum": 35, 
            "maximum": 75 
        },
        "borderWidth" : 1,
        "font" : { 
            "color" : colors["nodeTextColor"], 
            "multi": True 
        },
        "shadow" : { 
            "enabled": True, 
            "color": "rgba(0, 0, 0, 0.12)",	
            "size": 10, 
            "x": 5, 
            "y": 5	
        }
    }
    linkTemplate = {
        "id": "",
		"from": "", 
		"to": "",
		"label": "",
		"color": {
			"color": "#6FA92D"
		},
		"arrows": {
			"middle": {
			  "enabled": True,
			  "type": "arrow"
			}
		},
		"smooth": {
			"enabled": True,
			"type": "cubicBezier",
			"roundness": 0.7
		},
		"width": 1.5
    }

    for flow in flows:
        try:
            flowType = flow["type"]
            try:
                flowSubtype = flow["subtype"]
            except KeyError:
                flowSubtype = ""
            if "{0}{1}".format(flowType,"ID") in flow:
                objectID = "{0}{1}".format(flowType,"ID")
                flowID = flow["flowID"]
                name = flow["flowID"]
                # Generate nodes
                node = copy.deepcopy(nodeTemplate)
                try:
                    flowUI = flowsUIByID[flow["flowID"]]
                    node["id"] = flowID
                    node["x"] = flowUI.x
                    node["y"] = flowUI.y
                    # node["shape"] = "box"
                    if flow["type"] == "trigger":
                        node["flowType"] = "trigger"
                        obj = triggersByID[flow["triggerID"]]
                        node["objID"] = obj._id
                        node["name"] = obj.name
                        modeClass = jimi.cache.globalCache.get("modelCache",obj.classID,jimi.model.getClassObject,sessionData=jimi.api.g.sessionData)[0]
                        label = "({0}.{1},{2})\n<b>{3}</b>\n{4}".format(obj.systemID,obj.systemIndex,obj.clusterSet,obj.name,modeClass.name)
                        color = None
                        if obj.enabled:
                            color = colors["nodeEnableColor"]
                        duration = obj.maxDuration
                        if duration == 0:
                            duration = 60
                        if (((obj.startCheck != 0) and (obj.startCheck + duration > time.time())) or (obj.lastCheck > time.time()-2.5)):
                            color = colors["nodeRunningColor"]
                        if ((obj.startCheck != 0) and (obj.startCheck + duration < time.time())):
                            color = colors["nodeErrorColor"]
                        if not obj.enabled:
                            color = colors["nodeDisabledColor"]
                        node["color"] = { "border" : colors["nodeBorderColor"], "background" : color, "highlight" : { "background" : color }, "hover" : { "background" : color } }
                    elif flow["type"] == "action":
                        node["flowType"] = "action"
                        obj = actionsByID[flow["actionID"]]
                        node["objID"] = obj._id
                        node["name"] = obj.name
                        modeClass = jimi.cache.globalCache.get("modelCache",obj.classID,jimi.model.getClassObject,sessionData=jimi.api.g.sessionData)[0]
                        label = "<b>{0}</b>\n{1}".format(obj.name,modeClass.name)
                        color = None
                        if obj.enabled:
                            color = colors["nodeEnableColor"]
                        if not obj.enabled:
                            color = colors["nodeDisabledColor"]
                        node["color"] = { "border" : colors["nodeBorderColor"], "background" : color, "highlight" : { "background" : color }, "hover" : { "background" : color } }
                    node["label"] = label
                except (IndexError, KeyError) as e:
                    node["label"] = "Unknown Object"
                    node["color"] = { "background" : colors["nodeUnknownColor"] }
                nodesList[flowID] = node
                # Generate links
                for nextFlow in flow["next"]:
                    link = copy.deepcopy(linkTemplate)
                    linkName = "{0}->{1}".format(flowID,nextFlow["flowID"])
                    link["id"] = linkName
                    link["to"] = nextFlow["flowID"]
                    link["from"] = flowID
                    try:
                        if nextFlow["order"] > 0:
                            link["label"] = str(nextFlow["order"])
                    except KeyError:
                        pass
                    try:
                        if nextFlow["tag"] != "":
                            if link["label"] != "":
                                link["label"] = "{0}:{1}".format(str(nextFlow["order"]),nextFlow["tag"])
                            else:
                                link["label"] = "{0}".format(nextFlow["tag"])
                    except KeyError:
                        pass
                    if link["label"] == "":
                        link["label"] = " "
                    color = colors["linkColor"]
                    if type(nextFlow["logic"]) is bool:
                        if nextFlow["logic"] == True:
                            color = colors["linkTrueColor"]
                        else:
                            color = colors["linkFalseColor"]
                    elif type(nextFlow["logic"]) is int:
                        color = colors["linkRCColor"]
                    elif type(nextFlow["logic"]) is str:
                        if nextFlow["logic"].startswith("if "):
                            color = colors["linkLogicColor"]
                        elif nextFlow["logic"] == "*":
                            color = colors["linkAllColor"]
                    link["color"] = color
                    linksList[linkName] = link
        except KeyError:
            pass

    if len(flowchartOperators) == 0 and len(flowchartLinks) == 0:
        flowchartResponse["operators"]["nodes"] = [ x for x in nodesList.values() ]
        flowchartResponse["links"]["links"] = [ x for x in linksList.values() ]
    else:
        # Comparing displayed nodes to generated nodes
        for node in flowchartOperators:
            try:
                if node != nodesList[node["id"]]:
                    flowchartResponse["operators"]["update"][node["id"]] = nodesList[node["id"]]
                del nodesList[node["id"]]
            except KeyError:
                flowchartResponse["operators"]["delete"][node["id"]] = node
        for node in nodesList.values():
            flowchartResponse["operators"]["create"][node["id"]] = node
        # Comparing displayed links to generated links
        for link in flowchartLinks:
            try:
                if link != linksList[link["id"]]:
                    flowchartResponse["links"]["update"][link["id"]] = linksList[link["id"]]
                del linksList[link["id"]]
            except KeyError:
                flowchartResponse["links"]["delete"][link["id"]] = link
        for link in linksList.values():
            flowchartResponse["links"]["create"][link["id"]] = link

    # Active user stuff (BETA)
    editorObj = jimi.webui._editorUI().getAsClass(query={"objectId":conductID,"objectType":"conduct"})
    if len(editorObj) == 1:
        editorObj = editorObj[0]
    else:
        jimi.webui._editorUI().new(conductID,"conduct")
        editorObj = jimi.webui._editorUI().getAsClass(query={"objectId":conductID,"objectType":"conduct"})[0]
    editorObj.currentUsers[jimi.api.g.sessionData["user"]] = time.time()
    #Remove old users
    if jimi.db.ACLAccess(jimi.api.g.sessionData,conductObj["acl"],"write"):
        popList = []
        for user in editorObj.currentUsers:
            if editorObj.currentUsers[user] < time.time() - 5:
                popList.append(user)
        for user in popList:
            editorObj.currentUsers.pop(user)
        editorObj.update(["currentUsers"])
    flowchartResponse["currentUsers"] = [user for user in editorObj.currentUsers if editorObj.currentUsers[user] > time.time() - 5]

    return flowchartResponse, 200

@jimi.api.webServer.route("/conductEditor/<conductID>/export/", methods=["GET"])
def conductExport(conductID):
    conductObj = jimi.conduct._conduct().getAsClass(jimi.api.g.sessionData,id=conductID)
    if len(conductObj) == 1:
        conductObj = conductObj[0]
    else:
        return { }, 404
    flows = [ x for x in conductObj.flow ]
    
    # Apply filter to the flows if passed in GET
    data = request.args
    if "flowID" in data:
        processQueue = []
        currentFlowID = data["flowID"]
        specifiedFlows = []
        while True:
            for flow in flows:
                if flow["flowID"] == currentFlowID and flow["flowID"] not in specifiedFlows:
                    specifiedFlows.append(flow["flowID"])
                    for nextFlow in flow["next"]:
                        processQueue.append(nextFlow["flowID"])
            if len(processQueue) == 0:
                break
            else:
                currentFlowID = processQueue[-1]
                processQueue.pop()
        poplist = []
        for flow in flows:
            if flow["flowID"] not in specifiedFlows:
                poplist.append(flow)
        for pop in poplist:
            flows.remove(pop)

    flowTriggers = [ jimi.db.ObjectId(x["triggerID"]) for x in flows if x["type"] == "trigger" ]
    flowActions = [ jimi.db.ObjectId(x["actionID"]) for x in flows if x["type"] == "action" ]
    actions = jimi.action._action(False).getAsClass(jimi.api.g.sessionData,query={ "_id" : { "$in" : flowActions } })
    triggers = jimi.trigger._trigger(False).getAsClass(jimi.api.g.sessionData,query={ "_id" : { "$in" : flowTriggers } })
    result = { "flow" : flows, "action" : {}, "trigger" : {}, "ui" : {} }

    for flow in flows:
        obj = None
        if flow["type"] == "trigger":
            for t in triggers:
                if flow["triggerID"] == t._id:
                    obj = t
                    break
        elif flow["type"] == "action":
            for a in actions:
                if flow["actionID"] == a._id:
                    obj = a
                    break
        if obj:
            classObj = _class = jimi.model._model().getAsClass(id=obj.classID)
            classObj = classObj[0]
            if obj._id not in result[flow["type"]]:
                result[flow["type"]][obj._id] = { "className" : classObj.name }
                blacklist = ["acl","classID","workerID","startCheck","nextCheck","lastUpdateTime","creationTime","systemID"]
                typeList = [str,int,float,dict,list,bool]
                members = [attr for attr in dir(obj) if not callable(getattr(obj, attr)) and not "__" in attr and attr ]
                for member in members:
                    if member not in blacklist:
                        value = getattr(obj,member)
                        if type(value) in typeList:
                            result[flow["type"]][obj._id][member] = value
            if flow["flowID"] not in result["ui"]:
                result["ui"][flow["flowID"]] = { "x" : 0, "y" : 0, "title" : "" }
                flowUI = jimi.webui._modelUI().getAsClass(jimi.api.g.sessionData,query={ "flowID" : flow["flowID"], "conductID" : conductID })
                if len(flowUI) > 0:
                    flowUI = flowUI[0]
                    result["ui"][flow["flowID"]]["x"] = flowUI.x
                    result["ui"][flow["flowID"]]["y"] = flowUI.y
                    result["ui"][flow["flowID"]]["title"] = flowUI.title
    tempFilename = "data/temp/{0}".format(str(uuid.uuid4()))
    if jimi.helpers.safeFilepath(tempFilename,"data/temp"):
        with open(Path(tempFilename), "w") as f:
            json.dump(result,f,indent=3)
        return send_file(Path(tempFilename), attachment_filename=conductObj.name+".json", as_attachment=True)
    return { }, 404

@jimi.api.webServer.route("/conductEditor/<conductID>/import/", methods=["GET"])
def conductImport(conductID):
    return render_template("import.html", CSRF=jimi.api.g.sessionData["CSRF"]), 200

@jimi.api.webServer.route("/conductEditor/<conductID>/import/", methods=["POST"])
def conductImportData(conductID):
    conductObj = jimi.conduct._conduct().getAsClass(jimi.api.g.sessionData,id=conductID)
    if len(conductObj) == 1:
        conductObj = conductObj[0]
    else:
        return { }, 404
    access = jimi.db.ACLAccess(jimi.api.g.sessionData,conductObj.acl,"write")
    if access:
        data = json.loads(jimi.api.request.data)
        importData = json.loads(data["importData"])

        #Legacy support remove in 5.0 - old imports dont have tag
        for flow in importData["flow"]:
            for nextFlow in flow["next"]:
                if "tag" not in nextFlow:
                    nextFlow["tag"] = ""

        if data["appendObjects"]:
            conductObj.flow = conductObj.flow + importData["flow"]
        else:
            conductObj.flow=importData["flow"]

        # Build lookup and regen IDs if appending
        flowLookup = {}
        flowLookupReverse = {}
        flows = importData["flow"]
        for flow in flows:
            if flow["flowID"] not in flowLookup:
                # Regen IDs for appends
                if data["appendObjects"]:
                    flowLookup[flow["flowID"]] = str(uuid.uuid4())
                else:
                    flowLookup[flow["flowID"]] = flow["flowID"]
                flowLookupReverse[flowLookup[flow["flowID"]]] = flow["flowID"]
            flow["flowID"] = flowLookup[flow["flowID"]]
            for nextFlow in flow["next"]:
                if nextFlow["flowID"] not in flowLookup:
                    # Regen IDs for appends
                    if data["appendObjects"]:
                        flowLookup[nextFlow["flowID"]] = str(uuid.uuid4())
                    else:
                        flowLookup[nextFlow["flowID"]] = nextFlow["flowID"]
                    flowLookupReverse[flowLookup[nextFlow["flowID"]]] = nextFlow["flowID"]
                nextFlow["flowID"] = flowLookup[nextFlow["flowID"]]
 
        for flow in importData["flow"]:
            flowUI = jimi.webui._modelUI().getAsClass(jimi.api.g.sessionData,query={ "flowID" : flow["flowID"], "conductID" : conductID })
            if len(flowUI) > 0:
                flowUI = flowUI[0]
                flowUI.x = importData["ui"][flow["flowID"]]["x"] + int(data["offsetX"])
                flowUI.y = importData["ui"][flow["flowID"]]["y"] + int(data["offsetY"])
                flowUI.title = importData["ui"][flow["flowID"]]["title"]
                flowUI.update(["x","y","title"])
            else:
                jimi.webui._modelUI().new(conductObj._id,conductObj.acl,flow["flowID"],importData["ui"][flowLookupReverse[flow["flowID"]]]["x"],importData["ui"][flowLookupReverse[flow["flowID"]]]["y"],importData["ui"][flowLookupReverse[flow["flowID"]]]["title"])
            if flow["type"] == "trigger":
                classObj = _class = jimi.model._model().getAsClass(jimi.api.g.sessionData,query={ "name" : importData["trigger"][flow["triggerID"]]["className"] })
                if len(classObj) > 0:
                    classObj = classObj[0]
                    existingTrigger = []
                    if data["duplicateObjects"] == False:
                        existingTrigger = jimi.trigger._trigger(False).getAsClass(jimi.api.g.sessionData,query={ "name" : importData["trigger"][flow["triggerID"]]["name"], "classID" : classObj._id })
                    if len(existingTrigger) > 0:
                        existingTriggers = existingTrigger
                        existingTrigger = None
                        # Checking that the found object is the same as the imported object
                        for existingTriggerItem in existingTriggers:
                            members = [attr for attr in dir(existingTriggerItem) if not callable(getattr(existingTriggerItem, attr)) and not "__" in attr and attr ]
                            blacklist = ["_id","classID","className","acl","lastCheck","executionCount"]
                            same = True
                            for member in members:
                                if member in importData["trigger"][flow["triggerID"]] and member not in blacklist:
                                    if getattr(existingTriggerItem,member) != importData["trigger"][flow["triggerID"]][member]:
                                        same = False
                                        break 
                            if same:
                                existingTrigger = existingTriggerItem
                                break
                    else:
                        existingTrigger = None
                    if existingTrigger == None:
                        _class = classObj.classObject()
                        acl = { "ids" : [ { "accessID" : jimi.api.g.sessionData["primaryGroup"], "read" : True, "write" : True, "delete" : True } ] }
                        newObjectID = _class().new(importData["trigger"][flow["triggerID"]]["name"],acl=acl).inserted_id
                        existingTrigger = _class().getAsClass(jimi.api.g.sessionData,id=newObjectID)[0]
                    members = [attr for attr in dir(existingTrigger) if not callable(getattr(existingTrigger, attr)) and not "__" in attr and attr ]
                    blacklist = ["_id","classID","className","acl","lastCheck","executionCount"]
                    updateList = []
                    for member in members:
                        if member in importData["trigger"][flow["triggerID"]]:
                            if member not in blacklist:
                                if data["duplicateObjects"] and member == "name":
                                    setattr(existingTrigger,member,"{0}-{1}".format(importData["trigger"][flow["triggerID"]][member],existingTrigger._id))
                                else:
                                    setattr(existingTrigger,member,importData["trigger"][flow["triggerID"]][member])
                                updateList.append(member)
                    existingTrigger.update(updateList,sessionData=jimi.api.g.sessionData)
                    flow["triggerID"] = existingTrigger._id
            elif flow["type"] == "action":
                classObj = _class = jimi.model._model().getAsClass(jimi.api.g.sessionData,query={ "name" : importData["action"][flow["actionID"]]["className"] })
                if len(classObj) > 0:
                    classObj = classObj[0]
                    existingAction = []
                    if data["duplicateObjects"] == False:
                        existingAction = jimi.action._action(False).getAsClass(jimi.api.g.sessionData,query={ "name" : importData["action"][flow["actionID"]]["name"], "classID" : classObj._id })
                    if len(existingAction) > 0:
                        existingActions = existingAction
                        existingAction = None
                        # Checking that the found object is the same as the imported object
                        for existingActionItem in existingActions:
                            members = [attr for attr in dir(existingActionItem) if not callable(getattr(existingActionItem, attr)) and not "__" in attr and attr ]
                            blacklist = ["_id","classID","className","acl","lastCheck"]
                            same = True
                            for member in members:
                                if member in importData["action"][flow["actionID"]] and member not in blacklist:
                                    if getattr(existingActionItem,member) != importData["action"][flow["actionID"]][member]:
                                        same = False
                                        break 
                            if same:
                                existingAction = existingActionItem
                                break
                    else:
                        existingAction = None
                    if existingAction == None:
                        _class = classObj.classObject()
                        acl = { "ids" : [ { "accessID" : jimi.api.g.sessionData["primaryGroup"], "read" : True, "write" : True, "delete" : True } ] }
                        newObjectID = _class().new(importData["action"][flow["actionID"]]["name"],acl=acl).inserted_id
                        existingAction = _class().getAsClass(jimi.api.g.sessionData,id=newObjectID)[0]
                        existingAction.acl = conductObj.acl
                        existingAction.update(["acl"])
                    members = [attr for attr in dir(existingAction) if not callable(getattr(existingAction, attr)) and not "__" in attr and attr ]
                    blacklist = ["_id","classID","className","acl","lastCheck"]
                    updateList = []
                    for member in members:
                        if member in importData["action"][flow["actionID"]]:
                            if member not in blacklist:
                                if data["duplicateObjects"] and member == "name":
                                    setattr(existingAction,member,"{0}-{1}".format(importData["action"][flow["actionID"]][member],existingAction._id))
                                else:
                                    setattr(existingAction,member,importData["action"][flow["actionID"]][member])
                                updateList.append(member)
                    existingAction.update(updateList,sessionData=jimi.api.g.sessionData)
                    flow["actionID"] = existingAction._id
    conductObj.update(["flow"],sessionData=jimi.api.g.sessionData)
    return {}, 200

@jimi.api.webServer.route("/conductEditor/<conductID>/codify/", methods=["GET"])
def getConductFlowCodify(conductID):
    def generateFlow(currentFlow,flowDict,triggers,actions):
        flowCode = ""
        processQueue = []
        indentLevel = 0
        logic = None
        backLoopDetectionList = []
        while True:
            if currentFlow:
                backLoopDetectionList.append(currentFlow["flowID"])
                obj = None
                if currentFlow["type"] == "trigger":
                    for t in triggers:
                        if flow["triggerID"] == t._id:
                            obj = t
                            break
                    for nextFlow in currentFlow["next"]:
                        if nextFlow["flowID"] not in backLoopDetectionList:
                            processQueue.append({ "flowID" : nextFlow["flowID"], "indentLevel": indentLevel+1, "logic" : nextFlow["logic"] })
                elif currentFlow["type"] == "action":
                    for a in actions:
                        if currentFlow["actionID"] == a._id:
                            obj = a
                            break
                    for nextFlow in currentFlow["next"]:
                        if nextFlow["flowID"] not in backLoopDetectionList:
                            processQueue.append({ "flowID" : nextFlow["flowID"], "indentLevel": indentLevel+1, "logic" : nextFlow["logic"] })
                if obj:
                    classObj = _class = jimi.model._model().getAsClass(id=obj.classID)
                    classObj = classObj[0]
                    blacklist = ["_id","acl","classID","workerID","startCheck","nextCheck","lastUpdateTime","lastCheck","clusterSet","concurrency","creationTime","schedule","systemID"]
                    typeList = [str,int,float,dict,list,bool]
                    members = [attr for attr in dir(obj) if not callable(getattr(obj, attr)) and not "__" in attr and attr ]
                    params={}
                    for member in members:
                        if member not in blacklist:
                            value = getattr(obj,member)
                            if type(value) in typeList:
                                params[member] = value
                    
                    if currentFlow["type"] == "action":
                        flowCode+="\r\n{0}logic({1})->{2}{3}".format(("\t"*indentLevel),logic,classObj.name,json.dumps(params))
                    else:
                        if len(flowCode) > 0:
                            flowCode+="\r\n{0}{1}{2}".format(("\t"*indentLevel),classObj.name,json.dumps(params))
                        else:
                            flowCode="{0}{1}".format(classObj.name,json.dumps(params))
            if len(processQueue) == 0:
                break
            else:
                nextFlowID = processQueue[-1]["flowID"]
                indentLevel = processQueue[-1]["indentLevel"]
                logic = processQueue[-1]["logic"]
                processQueue.pop()
                if nextFlowID in flowDict:
                    currentFlow = flowDict[nextFlowID]
                else:
                    currentFlow = None
        return flowCode

    data = request.args

    conductObj = jimi.conduct._conduct().getAsClass(jimi.api.g.sessionData,id=conductID)
    if len(conductObj) == 1:
        conductObj = conductObj[0]
    else:
        return { }, 404

    # Getting all UI flow details for flows in this conduct
    flows = [ x for x in conductObj.flow ]
    flowDict = {}
    for flow in flows:
        flowDict[flow["flowID"]] = flow
    flowTriggers = [ jimi.db.ObjectId(x["triggerID"]) for x in flows if x["type"] == "trigger" ]
    flowActions = [ jimi.db.ObjectId(x["actionID"]) for x in flows if x["type"] == "action" ]

    actions = jimi.action._action(False).getAsClass(jimi.api.g.sessionData,query={ "_id" : { "$in" : flowActions } })
    triggers = jimi.trigger._trigger(False).getAsClass(jimi.api.g.sessionData,query={ "_id" : { "$in" : flowTriggers } })

    flowID = None
    if data:
        if "flowID" in data:
            flowID = data["flowID"]
    flowCode = ""
    for flow in flows:
        if flow["type"] == "trigger":
            if flowID:
                if flowID == flow["flowID"]:
                    flowCode+=generateFlow(flow,flowDict,triggers,actions)
                    break
            else:
                flowCode+="\n{0}".format(generateFlow(flow,flowDict,triggers,actions))
    
    flowCode=flowCode.strip()
    if data:
        if "json" in data:
            return { "result" : flowCode, "CSRF" : jimi.api.g.sessionData["CSRF"] }, 200

    tempFilename = "data/temp/{0}".format(str(uuid.uuid4()))
    if jimi.helpers.safeFilepath(tempFilename,"data/temp"):
        with open(Path(tempFilename), "w") as f:
            f.write(flowCode)
        return send_file(Path(tempFilename), attachment_filename=conductObj.name+".json")
    return { }, 404

@jimi.api.webServer.route("/conductEditor/<conductID>/flow/<flowID>/", methods=["DELETE"])
def deleteFlow(conductID,flowID):
    conductObj = jimi.conduct._conduct().getAsClass(jimi.api.g.sessionData,id=conductID)
    if len(conductObj) == 1:
        conductObj = conductObj[0]
    else:
        return { }, 404
    access = jimi.db.ACLAccess(jimi.api.g.sessionData,conductObj.acl,"write")
    if access:
        if jimi.db.fieldACLAccess(jimi.api.g.sessionData,conductObj.acl,"flow","delete"):
            if flowID == "multiple":
                data = json.loads(jimi.api.request.data)
                flows = [{"id":x["id"]} for x in data["nodes"]]
            else:
                flows = [{"id":flowID}]
            for flowID in flows:
                flow = [ x for x in conductObj.flow if x["flowID"] == flowID["id"]]
                if len(flow) == 1:
                    flow = flow[0]
                    for flowItemsValue in conductObj.flow:
                        for nextflowValue in flowItemsValue["next"]:
                            if nextflowValue["flowID"] == flowID["id"]:
                                conductObj.flow[conductObj.flow.index(flowItemsValue)]["next"].remove(nextflowValue)
                    conductObj.flow.remove(flow)
                    if "_id" in jimi.api.g.sessionData:
                        jimi.audit._audit().add("flow","delete",{ "_id" : jimi.api.g.sessionData["_id"], "user" : jimi.api.g.sessionData["user"], "conductID" : conductID, "flowID" : flowID["id"] })
                    else:
                        jimi.audit._audit().add("flow","delete",{ "user" : "system", "conductID" : conductID, "flowID" : flowID["id"] })
            conductObj.update(["flow"],sessionData=jimi.api.g.sessionData)
            return { "flowIDs" : flows }, 200
        else:
            return { }, 404
    else:
        return { }, 404

@jimi.api.webServer.route("/conductEditor/<conductID>/flow/", methods=["PUT"])
def newFlow(conductID):
    conductObj = jimi.conduct._conduct().getAsClass(jimi.api.g.sessionData,id=conductID)
    if len(conductObj) == 1:
        conductObj = conductObj[0]
    else:
        return { }, 404

    access = jimi.db.ACLAccess(jimi.api.g.sessionData,conductObj.acl,"write")
    if access:
        data = json.loads(jimi.api.request.data)
        # Get new UUID store within current conduct flow and return UUID
        newFlowID = str(uuid.uuid4())
        flow = {
            "flowID" : newFlowID, 
            "next" : []
        }
        # Creating new object of model type
        _class = jimi.model._model().getAsClass(jimi.api.g.sessionData,id=data["classID"])
        if _class:
            subtype = _class[0].name
            _class = _class[0].classObject()
            acl = { "ids" : [ { "accessID" : jimi.api.g.sessionData["primaryGroup"], "read" : True, "write" : True, "delete" : True } ] }
            newFlowObjectID = _class().new(flow["flowID"],acl=acl).inserted_id
            # Working out by bruteforce which type this is ( try and load it by parent class and check for error) - get on trigger if it does not exist will return None
            modelFlowObjectType = "action"
            if len(jimi.trigger._trigger(False).getAsClass(jimi.api.g.sessionData,id=newFlowObjectID)) > 0:
                modelFlowObjectType = "trigger"
            modelFlowObject = _class().getAsClass(jimi.api.g.sessionData,id=newFlowObjectID)
            if len(modelFlowObject) == 1:
                modelFlowObject = modelFlowObject[0]
            else:
                return { }, 404
            flow["type"] = modelFlowObjectType
            if subtype != "action" and subtype != "trigger":
                flow["subtype"] = subtype
            flow["{0}{1}".format(modelFlowObjectType,"ID")] = str(newFlowObjectID)
            # Adding UI position for cloned object
            jimi.webui._modelUI().new(conductID,conductObj.acl,flow["flowID"],data["x"],data["y"],modelFlowObject.name)
            # Appending new object to conduct
            conductObj.flow.append(flow)
            if "_id" in jimi.api.g.sessionData:
                jimi.audit._audit().add("flow","create",{ "_id" : jimi.api.g.sessionData["_id"], "user" : jimi.api.g.sessionData["user"], "conductID" : conductID, "newFlowID" : newFlowID })
            else:
                jimi.audit._audit().add("flow","create",{ "user" : "system", "conductID" : conductID, "newFlowID" : newFlowID })
            conductObj.update(["flow"],sessionData=jimi.api.g.sessionData)
            return { }, 201
    else:
        return { }, 403

    return { }, 404
    
@jimi.api.webServer.route("/conductEditor/<conductID>/flow/", methods=["POST"])
def dropExistingObject(conductID):
    conductObj = jimi.conduct._conduct().getAsClass(jimi.api.g.sessionData,id=conductID)
    if len(conductObj) == 1:
        conductObj = conductObj[0]
    else:
        return { }, 404
    access = jimi.db.ACLAccess(jimi.api.g.sessionData,conductObj.acl,"write")
    if access:
        data = json.loads(jimi.api.request.data)
        if data["action"] == "drop":
            newFlowID = str(uuid.uuid4())
            flow = {
                "flowID" : newFlowID, 
                "type" : data["flowType"],
                "{0}{1}".format(data["flowType"],"ID") : data["_id"],
                "next" : []
            }
            modelFlowObject = None
            if data["flowType"] == "trigger":
                modelFlowObject = jimi.trigger._trigger(False).getAsClass(jimi.api.g.sessionData,id=data["_id"])[0]
            elif data["flowType"] == "action":
                modelFlowObject = jimi.action._action(False).getAsClass(jimi.api.g.sessionData,id=data["_id"])[0]
            if modelFlowObject:
                name = modelFlowObject.name
            else:
                name = flow["flowID"]

            jimi.webui._modelUI().new(conductID,conductObj.acl,flow["flowID"],data["x"],data["y"],name)
            if "_id" in jimi.api.g.sessionData:
                jimi.audit._audit().add("flow","drop",{ "_id" : jimi.api.g.sessionData["_id"], "user" : jimi.api.g.sessionData["user"], "conductID" : conductID, "objectID" : data["_id"], "newFlowID" : newFlowID })
            else:
                jimi.audit._audit().add("flow","drop",{ "user" : "system", "conductID" : conductID, "objectID" : data["_id"], "newFlowID" : newFlowID })
            conductObj.flow.append(flow)
            conductObj.update(["flow"],sessionData=jimi.api.g.sessionData)
            return { }, 201
    return { }, 404

@jimi.api.webServer.route("/conductEditor/<conductID>/flow/<flowID>/", methods=["POST"])
def updateFlow(conductID,flowID):
    conductObj = jimi.conduct._conduct().getAsClass(jimi.api.g.sessionData,id=conductID)
    if len(conductObj) == 1:
        conductObj = conductObj[0]
    else:
        return { }, 404

    flow = [ x for x in conductObj.flow if x["flowID"] ==  flowID]
    if len(flow) == 1:
        flow = flow[0]
        data = json.loads(jimi.api.request.data)
        if data["action"] == "update":
            access = jimi.db.ACLAccess(jimi.api.g.sessionData,conductObj.acl,"write")
            if access:
                if "x" in data and "y" in data:
                    try:
                        x = int(data["x"])
                        y = int(data["y"])
                    except:
                        return { }, 403
                flowUI = jimi.webui._modelUI().getAsClass(jimi.api.g.sessionData,query={ "flowID" : flow["flowID"], "conductID" : conductID })
                if len(flowUI) == 1:
                    flowUI = flowUI[0]
                    if "x" in data and "y" in data:
                        flowUI.x = x
                        flowUI.y = y
                        if "_id" in jimi.api.g.sessionData:
                            jimi.audit._audit().add("flow","update",{ "_id" : jimi.api.g.sessionData["_id"], "user" : jimi.api.g.sessionData["user"], "conductID" : conductID, "flowID" : flowID, "x" : x, "y" : y })
                        else:
                            jimi.audit._audit().add("flow","update",{ "user" : "system", "conductID" : conductID, "flowID" : flowID, "x" : x, "y" : y })
                        flowUI.update(["x","y"],sessionData=jimi.api.g.sessionData)
                    if "title" in data:
                        flowUI.title = data["title"]
                        if "_id" in jimi.api.g.sessionData:
                            jimi.audit._audit().add("flow","update",{ "_id" : jimi.api.g.sessionData["_id"], "user" : jimi.api.g.sessionData["user"], "conductID" : conductID, "flowID" : flowID, "title" :data["title"] })
                        else:
                            jimi.audit._audit().add("flow","update",{ "user" : "system", "conductID" : conductID, "flowID" : flowID, "title" :data["title"] })
                        flowUI.update(["title"],sessionData=jimi.api.g.sessionData)
                    return { }, 200
                else:
                    jimi.webui._modelUI().new(conductID,conductObj.acl,flow["flowID"],x,y)
                    return { }, 201
        elif data["action"] == "unlink":
            access = jimi.db.ACLAccess(jimi.api.g.sessionData,conductObj.acl,"write")
            if access:
                flow = [ x for x in conductObj.flow if x["flowID"] ==  data["operatorId"]]
                if len(flow) == 1:
                    flow = flow[0]
                    data = json.loads(jimi.api.request.data)
                    modelFlowObject = None
                    # Check if the modelType and object are unchanged
                    if "type" in flow:
                        if flow["type"] == "trigger":
                            modelFlowObject = jimi.trigger._trigger(False).getAsClass(jimi.api.g.sessionData,id=flow["{0}{1}".format(flow["type"],"ID")])
                            if len(modelFlowObject) == 1:
                                modelFlowObject = modelFlowObject[0]
                            modelFlowObjectType = "trigger"
                        if flow["type"] == "action":
                            modelFlowObject = jimi.action._action(False).getAsClass(jimi.api.g.sessionData,id=flow["{0}{1}".format(flow["type"],"ID")])
                            if len(modelFlowObject) == 1:
                                modelFlowObject = modelFlowObject[0]
                            modelFlowObjectType = "action"
                        # Was it possible to load an existing object
                        if modelFlowObject:
                            # New object required
                            _class = jimi.model._model().getAsClass(jimi.api.g.sessionData,id=modelFlowObject.classID)
                            if _class:
                                _class = _class[0].classObject()
                                # All class models used as objects within a flow must have a name field
                                acl = { "ids" : [ { "accessID" : jimi.api.g.sessionData["primaryGroup"], "read" : True, "write" : True, "delete" : True } ] }
                                newFlowObjectID = str(_class().new(modelFlowObject.name,acl=acl).inserted_id)

                                modelFlowObjectClone = _class().getAsClass(jimi.api.g.sessionData,id=newFlowObjectID)
                                if len(modelFlowObjectClone) == 1:
                                    modelFlowObjectClone = modelFlowObjectClone[0]
                                else:
                                    return { }, 404

                                # Setting values in cloned object
                                members = [attr for attr in dir(modelFlowObject) if not callable(getattr(modelFlowObject, attr)) and not "__" in attr and attr ]
                                dontCopy=["_id"]
                                validTypes = [str,int,bool,float,list,dict]
                                updateList = []
                                for member in members:
                                    if member not in dontCopy:
                                        if type(getattr(modelFlowObject,member)) in validTypes:
                                            setattr(modelFlowObjectClone,member,getattr(modelFlowObject,member))
                                            updateList.append(member)
                                modelFlowObjectClone.update(updateList,sessionData=jimi.api.g.sessionData)

                                # Set conduct flow to correct type and objectID
                                flow["{0}{1}".format(flow["type"],"ID")] = str(newFlowObjectID)
                                conductObj.update(["flow"],sessionData=jimi.api.g.sessionData)
                                if "_id" in jimi.api.g.sessionData:
                                    jimi.audit._audit().add("flow","unlink",{ "_id" : jimi.api.g.sessionData["_id"], "user" : jimi.api.g.sessionData["user"], "conductID" : conductID, "flowID" : flowID, "oldFlowObjectID" : modelFlowObject._id, "newFlowObjectID" : newFlowObjectID })
                                else:
                                    jimi.audit._audit().add("flow","unlink",{ "user" : "system", "conductID" : conductID, "flowID" : flowID, "oldFlowObjectID" : modelFlowObject._id, "newFlowObjectID" : newFlowObjectID })
                                return { "objectID" : newFlowObjectID }, 200
        elif data["action"] == "copy":
            access = jimi.db.ACLAccess(jimi.api.g.sessionData,conductObj.acl,"write")
            if access:
                flow = [ x for x in conductObj.flow if x["flowID"] ==  data["operatorId"]]
                if len(flow) == 1:
                    flow = flow[0]
                    newFlowID = str(uuid.uuid4())
                    newFlow = {
                        "flowID" : newFlowID, 
                        "type" : flow["type"],
                        "{0}{1}".format(flow["type"],"ID") : flow["{0}{1}".format(flow["type"],"ID")],
                        "next" : []
                    }
                    if "_id" in jimi.api.g.sessionData:
                        jimi.audit._audit().add("flow","copy",{ "_id" : jimi.api.g.sessionData["_id"], "user" : jimi.api.g.sessionData["user"], "conductID" : conductID, "flowID" : flowID })
                    else:
                        jimi.audit._audit().add("flow","copy",{ "user" : "system", "conductID" : conductID, "flowID" : flowID })
                    flowUI = jimi.webui._modelUI().getAsClass(jimi.api.g.sessionData,query={ "flowID" : flow["flowID"], "conductID" : conductID })[0]
                    jimi.webui._modelUI().new(conductID,conductObj.acl,newFlow["flowID"],data["x"],data["y"],flowUI.title)
                    conductObj.flow.append(newFlow)
                    conductObj.update(["flow"],sessionData=jimi.api.g.sessionData)
                    return { }, 201
        elif data["action"] == "clone":
            access = jimi.db.ACLAccess(jimi.api.g.sessionData,conductObj.acl,"write")
            if access:
                flow = [ x for x in conductObj.flow if x["flowID"] ==  data["operatorId"]]
                if len(flow) == 1:
                    flow = flow[0]
                    data = json.loads(jimi.api.request.data)
                    modelFlowObject = None
                    # Check if the modelType and object are unchanged
                    if "type" in flow:
                        if flow["type"] == "trigger":
                            modelFlowObject = jimi.trigger._trigger(False).getAsClass(jimi.api.g.sessionData,id=flow["{0}{1}".format(flow["type"],"ID")])
                            if len(modelFlowObject) == 1:
                                modelFlowObject = modelFlowObject[0]
                            modelFlowObjectType = "trigger"
                        if flow["type"] == "action":
                            modelFlowObject = jimi.action._action(False).getAsClass(jimi.api.g.sessionData,id=flow["{0}{1}".format(flow["type"],"ID")])
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
                            _class = jimi.model._model().getAsClass(jimi.api.g.sessionData,id=modelFlowObject.classID)
                            if _class:
                                _class = _class[0].classObject()
                                # Bug exists as name value is not requried by db class but is for core models - this could result in an error if new model is added that does not accept name within new function override
                                acl = { "ids" : [ { "accessID" : jimi.api.g.sessionData["primaryGroup"], "read" : True, "write" : True, "delete" : True } ] }
                                newFlowObjectID = _class().new(flow["flowID"],acl=acl).inserted_id

                                # Working out by bruteforce which type this is ( try and load it by parent class and check for error) - get on trigger if it does not exist will return None
                                modelFlowObjectClone = _class().getAsClass(jimi.api.g.sessionData,id=newFlowObjectID)
                                if len(modelFlowObjectClone) == 1:
                                    modelFlowObjectClone = modelFlowObjectClone[0]
                                else:
                                    return { }, 404

                                # Setting values in cloned object
                                members = [attr for attr in dir(modelFlowObject) if not callable(getattr(modelFlowObject, attr)) and not "__" in attr and attr ]
                                dontCopy=["_id","name"]
                                validTypes = [str,int,bool,float,list,dict]
                                updateList = []
                                for member in members:
                                    if member not in dontCopy:
                                        if type(getattr(modelFlowObject,member)) in validTypes:
                                            setattr(modelFlowObjectClone,member,getattr(modelFlowObject,member))
                                            updateList.append(member)
                                modelFlowObjectClone.update(updateList,sessionData=jimi.api.g.sessionData)

                                # Set conduct flow to correct type and objectID
                                flow["{0}{1}".format(flow["type"],"ID")] = str(newFlowObjectID)
                                conductObj.flow.append(flow)

                                # Adding UI position for cloned object
                                flowUI = jimi.webui._modelUI().getAsClass(jimi.api.g.sessionData,query={ "flowID" : flowID, "conductID" : conductID })[0]
                                jimi.webui._modelUI().new(conductID,conductObj.acl,flow["flowID"],data["x"],data["y"],"Copy - {0}".format(flowUI.title))
                                conductObj.update(["flow"],sessionData=jimi.api.g.sessionData)
                                if "_id" in jimi.api.g.sessionData:
                                    jimi.audit._audit().add("flow","duplicate",{ "_id" : jimi.api.g.sessionData["_id"], "user" : jimi.api.g.sessionData["user"], "conductID" : conductID, "flowID" : flowID, "newFlowID" : newFlowID })
                                else:
                                    jimi.audit._audit().add("flow","duplicate",{ "user" : "system", "conductID" : conductID, "flowID" : flowID, "newFlowID" : newFlowID })
                                return { "result" : True}, 201
    return { }, 404

@jimi.api.webServer.route("/conductEditor/<conductID>/flowLink/<fromFlowID>/<toFlowID>/", methods=["PUT"])
def newFlowLink(conductID,fromFlowID,toFlowID):
    conductObj = jimi.conduct._conduct().getAsClass(jimi.api.g.sessionData,id=conductID)
    if len(conductObj) == 1:
        conductObj = conductObj[0]
    else:
        return { }, 404
    access = jimi.db.ACLAccess(jimi.api.g.sessionData,conductObj.acl,"write")
    if access:
        fromFlow = [ x for x in conductObj.flow if x["flowID"] ==  fromFlowID][0]
        toFlow = [ x for x in conductObj.flow if x["flowID"] ==  toFlowID][0]
        nextFlows = [ x for x in fromFlow["next"] if x["flowID"] ==  toFlowID]
        if len(nextFlows) == 0:
            if toFlow["type"] != "trigger":
                fromFlow["next"].append({ "flowID" : toFlowID, "logic": True, "order" : 0, "tag" : "" })
                # Sorting the list so we dont need to do this at flow runtime
                try:
                    fromFlow["next"] = sorted(fromFlow["next"], key=itemgetter("order"), reverse=False) 
                except KeyError:
                    for value in fromFlow["next"]:
                        if "order" not in value:
                            value["order"] = 0
                    fromFlow["next"] = sorted(fromFlow["next"], key=itemgetter("order"), reverse=False) 
                if "_id" in jimi.api.g.sessionData:
                    jimi.audit._audit().add("flow","new link",{ "_id" : jimi.api.g.sessionData["_id"], "user" : jimi.api.g.sessionData["user"], "conductID" : conductID, "fromFlowID" : fromFlowID, "toFlowID": toFlowID })
                else:
                    jimi.audit._audit().add("flow","new link",{ "user" : "system", "conductID" : conductID, "fromFlowID" : fromFlowID, "toFlowID": toFlowID })
                conductObj.update(["flow"],sessionData=jimi.api.g.sessionData)
                return { }, 201
            else:
                return { }, 403
        return { }, 200
    else:
        return { }, 403

@jimi.api.webServer.route("/conductEditor/<conductID>/flowLink/<fromFlowID>/<toFlowID>/", methods=["DELETE"])
def deleteFlowLink(conductID,fromFlowID,toFlowID):
    conductObj = jimi.conduct._conduct().getAsClass(jimi.api.g.sessionData,id=conductID)
    if len(conductObj) == 1:
        conductObj = conductObj[0]
    else:
        return { }, 404
    access = jimi.db.ACLAccess(jimi.api.g.sessionData,conductObj.acl,"write")
    if access:
        fromFlow = [ x for x in conductObj.flow if x["flowID"] == fromFlowID]
        if len(fromFlow) > 0:
            fromFlow = fromFlow[0]
            for nextflow in fromFlow["next"]:
                if nextflow["flowID"] == toFlowID:
                    if jimi.db.fieldACLAccess(jimi.api.g.sessionData,conductObj.acl,"flow","delete"):
                        conductObj.flow[conductObj.flow.index(fromFlow)]["next"].remove(nextflow)
                        if "_id" in jimi.api.g.sessionData:
                            jimi.audit._audit().add("flow","delete link",{ "_id" : jimi.api.g.sessionData["_id"], "user" : jimi.api.g.sessionData["user"], "conductID" : conductID, "fromFlowID" : fromFlowID, "toFlowID": toFlowID })
                        else:
                            jimi.audit._audit().add("flow","delete link",{ "user" : "system", "conductID" : conductID, "fromFlowID" : fromFlowID, "toFlowID": toFlowID })
                        conductObj.update(["flow"])
                        return { }, 200
                    return {}, 403
        return { }, 404
    else:
        return {}, 403

@jimi.api.webServer.route("/conductEditor/<conductID>/editACL/<flowID>", methods=["GET"])
def getACL(conductID,flowID):
    conductObj = jimi.conduct._conduct().getAsClass(jimi.api.g.sessionData,id=conductID)
    if len(conductObj) == 1:
        conductObj = conductObj[0]
    else:
        return { }, 404

    flow = [ x for x in conductObj.flow if x["flowID"] == flowID]
    if len(flow) == 1:
        flow = flow[0]
        if "type" in flow:
            if flow["type"] == "trigger":
                modelFlowObject = jimi.trigger._trigger(False).getAsClass(jimi.api.g.sessionData,id=flow["{0}{1}".format(flow["type"],"ID")])
                if len(modelFlowObject) == 1:
                    modelFlowObject = modelFlowObject[0]
            if flow["type"] == "action":
                modelFlowObject = jimi.action._action(False).getAsClass(jimi.api.g.sessionData,id=flow["{0}{1}".format(flow["type"],"ID")])
                if len(modelFlowObject) == 1:
                    modelFlowObject = modelFlowObject[0]
    acl = None
    if modelFlowObject:
        acl = modelFlowObject.acl

    uiAcl = None
    webObj = jimi.webui._modelUI().getAsClass(jimi.api.g.sessionData,query={"conductID" : conductID, "flowID" : flowID})
    if len(webObj) == 1:
        webObj = webObj[0]
        uiAcl = webObj.acl

    return {"acl":acl, "uiAcl" : uiAcl}, 200

@jimi.api.webServer.route("/conductEditor/<conductID>/editACL/<flowID>", methods=["POST"])
def editACL(conductID,flowID):
    conductObj = jimi.conduct._conduct().getAsClass(jimi.api.g.sessionData,id=conductID)
    if len(conductObj) == 1:
        conductObj = conductObj[0]
    else:
        return { }, 404

    data = json.loads(jimi.api.request.data)

    flow = [ x for x in conductObj.flow if x["flowID"] == flowID]
    if len(flow) == 1:
        flow = flow[0]
        if "type" in flow:
            if flow["type"] == "trigger":
                modelFlowObject = jimi.trigger._trigger(False).getAsClass(jimi.api.g.sessionData,id=flow["{0}{1}".format(flow["type"],"ID")])
                if len(modelFlowObject) == 1:
                    modelFlowObject = modelFlowObject[0]
            if flow["type"] == "action":
                modelFlowObject = jimi.action._action(False).getAsClass(jimi.api.g.sessionData,id=flow["{0}{1}".format(flow["type"],"ID")])
                if len(modelFlowObject) == 1:
                    modelFlowObject = modelFlowObject[0]

    objectResult = True
    if modelFlowObject:
        acl = json.loads(data["acl"])
        if acl != modelFlowObject.acl:
            if jimi.db.fieldACLAccess(jimi.api.g.sessionData,modelFlowObject.acl,"acl","write"):
                modelFlowObject.acl = acl
                if "_id" in jimi.api.g.sessionData:
                    jimi.audit._audit().add("flow","update",{ "_id" : jimi.api.g.sessionData["_id"], "user" : jimi.api.g.sessionData["user"], "conductID" : conductID, "flowID" : flowID, "acl" : data["acl"] })
                else:
                    jimi.audit._audit().add("flow","update",{ "user" : "system", "conductID" : conductID, "flowID" : flowID, "acl" : data["acl"] })
                modelFlowObject.update(["acl"])
            else:
                objectResult=False
            
    uiResult = True
    webObj = jimi.webui._modelUI().getAsClass(jimi.api.g.sessionData,query={"conductID" : conductID, "flowID" : flowID})
    if len(webObj) == 1:
        webObj = webObj[0]
        uiAcl = json.loads(data["uiAcl"])
        if webObj.acl != uiAcl:
            if jimi.db.fieldACLAccess(jimi.api.g.sessionData,webObj.acl,"acl","write"):
                webObj.acl = uiAcl
                if "_id" in jimi.api.g.sessionData:
                    jimi.audit._audit().add("flow","update",{ "_id" : jimi.api.g.sessionData["_id"], "user" : jimi.api.g.sessionData["user"], "conductID" : conductID, "flowID" : flowID, "uiAcl" : data["uiAcl"] })
                else:
                    jimi.audit._audit().add("flow","update",{ "user" : "system", "conductID" : conductID, "flowID" : flowID, "uiAcl" : data["uiAcl"] })
                webObj.update(["acl"])
            else:
                uiResult = False

    if not objectResult or not uiResult:
        return { }, 403

    return { }, 200

@jimi.api.webServer.route("/conductEditor/existingObjects/triggers/", methods=["GET"])
def getExistingObjectsTriggers():
    triggers = jimi.trigger._trigger(False).query(sessionData=jimi.api.g.sessionData,query={ "scope" : { "$gt" : 0 } })["results"]
    return { "results" : triggers}, 200

@jimi.api.webServer.route("/conductEditor/existingObjects/actions/", methods=["GET"])
def getExistingObjectsActions():
    actions = jimi.action._action(False).query(sessionData=jimi.api.g.sessionData,query={ "scope" : { "$gt" : 0 } })["results"]
    return { "results" : actions}, 200

@jimi.api.webServer.route("/conductEditor/<conductID>/editObjectSystemSettings/<flowID>/", methods=["GET"])
def getObjectSystemSettings(conductID,flowID):
    conductObj = jimi.conduct._conduct().getAsClass(jimi.api.g.sessionData,id=conductID)
    if len(conductObj) == 1:
        conductObj = conductObj[0]
    else:
        return { }, 404

    flow = [ x for x in conductObj.flow if x["flowID"] == flowID]
    if len(flow) == 1:
        flow = flow[0]
        if "type" in flow:
            if flow["type"] == "trigger":
                modelFlowObject = jimi.trigger._trigger(False).getAsClass(jimi.api.g.sessionData,id=flow["{0}{1}".format(flow["type"],"ID")])
                if len(modelFlowObject) == 1:
                    modelFlowObject = modelFlowObject[0]
            if flow["type"] == "action":
                modelFlowObject = jimi.action._action(False).getAsClass(jimi.api.g.sessionData,id=flow["{0}{1}".format(flow["type"],"ID")])
                if len(modelFlowObject) == 1:
                    modelFlowObject = modelFlowObject[0]
    if modelFlowObject:
        return { "scope" : modelFlowObject.scope }, 200
    return { }, 404

@jimi.api.webServer.route("/conductEditor/<conductID>/editObjectSystemSettings/<flowID>/", methods=["POST"])
def editObjectSystemSettings(conductID,flowID):
    conductObj = jimi.conduct._conduct().getAsClass(jimi.api.g.sessionData,id=conductID)
    if len(conductObj) == 1:
        conductObj = conductObj[0]
    else:
        return { }, 404

    data = json.loads(jimi.api.request.data)

    flow = [ x for x in conductObj.flow if x["flowID"] == flowID]
    if len(flow) == 1:
        flow = flow[0]
        if "type" in flow:
            if flow["type"] == "trigger":
                modelFlowObject = jimi.trigger._trigger(False).getAsClass(jimi.api.g.sessionData,id=flow["{0}{1}".format(flow["type"],"ID")])
                if len(modelFlowObject) == 1:
                    modelFlowObject = modelFlowObject[0]
            if flow["type"] == "action":
                modelFlowObject = jimi.action._action(False).getAsClass(jimi.api.g.sessionData,id=flow["{0}{1}".format(flow["type"],"ID")])
                if len(modelFlowObject) == 1:
                    modelFlowObject = modelFlowObject[0]

    if modelFlowObject:
        scope = data["scope"]
        if scope != modelFlowObject.scope:
            if jimi.db.fieldACLAccess(jimi.api.g.sessionData,modelFlowObject.acl,"scope","write"):
                modelFlowObject.scope = scope
                if "_id" in jimi.api.g.sessionData:
                    jimi.audit._audit().add("flow","update",{ "_id" : jimi.api.g.sessionData["_id"], "user" : jimi.api.g.sessionData["user"], "conductID" : conductID, "flowID" : flowID, "scope" : data["scope"] })
                else:
                    jimi.audit._audit().add("flow","update",{ "user" : "system", "conductID" : conductID, "flowID" : flowID, "scope" : data["scope"] })
                modelFlowObject.update(["scope"])
                return { }, 200
    return { }, 404

@jimi.api.webServer.route("/conductEditor/<conductID>/copyObjects/", methods=["POST"])
def copyConductObjects(conductID):
    data = json.loads(jimi.api.request.data)
    webObjects = jimi.webui._modelUI().getAsClass(query={"conductID" : conductID})
    conductObj = jimi.conduct._conduct().getAsClass(id=conductID)[0]
    nodes = []
    nodeDict = {}
    for node in data["nodes"]:
        nodeData = [x for x in webObjects if x.flowID == node["id"]][0]
        if jimi.db.ACLAccess(jimi.api.g.sessionData,nodeData.acl,"write"):
            node["links"] = []
            nodeDict[node["id"]] = node
        nodeIDList = [x["id"] for x in nodes]
    for edge in data["edges"]:
        if edge["from"] in nodeDict and edge["to"] in nodeDict:
            for flow in conductObj.flow:
                if edge["from"] == flow["flowID"] and flow["type"] == nodeDict[edge["from"]]["flowType"] and flow["{0}ID".format(flow["type"])] == nodeDict[edge["from"]]["objID"]:
                    for link in flow["next"]:
                        if link["flowID"] == edge["to"]:
                            nodeDict[edge["from"]]["links"].append(link)
    for node in nodeDict:
        nodes.append(nodeDict[node])
    if len(nodes) > 0:
        user = jimi.auth._user().getAsClass(id=jimi.api.g.sessionData["_id"])[0]
        user.clipboard = {"nodes":nodes,"originalConductID":conductID,"copyTime":time.time()}
        user.update(["clipboard"])
        return {}, 200
    return {}, 403

@jimi.api.webServer.route("/conductEditor/<conductID>/pasteObjects/", methods=["POST"])
def pasteConductObjects(conductID):
    conductObj = jimi.conduct._conduct().getAsClass(id=conductID)[0]
    access = jimi.db.ACLAccess(jimi.api.g.sessionData,conductObj.acl,"write")
    if access:
        data = json.loads(jimi.api.request.data)
        user = jimi.auth._user().getAsClass(id=jimi.api.g.sessionData["_id"])[0]
        clipboard = user.clipboard
        if clipboard["copyTime"] < time.time() - 900 and not data["forcePaste"]:
            return "Your last copy was over 15 minutes ago, are you sure you want to paste?", 302
        if len(clipboard) > 0:
            #Generate new node IDs so we can link later
            newNodeDict = {}
            for node in clipboard["nodes"]:
                newNodeDict[node["id"]] = str(uuid.uuid4())

            #Calculate new positions for objects
            clipboard["nodes"] = jimi.helpers.getCentreOffset(clipboard["nodes"],data["centre"])

            for node in clipboard["nodes"]:
                newFlowID = newNodeDict[node["id"]]
                flow = {
                    "flowID" : newFlowID, 
                    "type" : node["flowType"],
                    "next" : node["links"],
                    "{0}{1}".format(node["flowType"],"ID") : node["objID"]
                }
                for edge in flow["next"]:
                    edge["flowID"] = newNodeDict[edge["flowID"]]
                if "_id" in jimi.api.g.sessionData:
                    jimi.audit._audit().add("flow","copy",{ "_id" : jimi.api.g.sessionData["_id"], "user" : jimi.api.g.sessionData["user"], "conductID" : conductID, "flowID" : node["id"] })
                else:
                    jimi.audit._audit().add("flow","copy",{ "user" : "system", "conductID" : conductID, "flowID" : node["id"] })
                flowUI = jimi.webui._modelUI().getAsClass(jimi.api.g.sessionData,query={ "flowID" : node["id"], "conductID" : clipboard["originalConductID"] })[0]
                jimi.webui._modelUI().new(conductID,conductObj.acl,flow["flowID"],node["x"],node["y"],flowUI.title)
                conductObj.flow.append(flow)                      
            conductObj.update(["flow"],sessionData=jimi.api.g.sessionData)
            return "Pasted", 201 
        return "Could not find some of the objects to be pasted", 404
    return "You don't have write permissions to this conduct and can't paste here!", 401
