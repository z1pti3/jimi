import time
import json
import  uuid

from flask import Flask, request, render_template, make_response, redirect

from core import api, model, db, cache, audit, helpers

from core.models import trigger, action, conduct, webui

@api.webServer.route("/conductEditor/", methods=["GET"])
def editConduct():
    return render_template("conductEditor.html", CSRF=api.g.sessionData["CSRF"])

@api.webServer.route("/conductEditor/<conductID>/", methods=["POST"])
def conductFlowchartPoll(conductID):
    conductObj = conduct._conduct().query(api.g.sessionData,id=conductID)["results"]
    if len(conductObj) == 1:
        conductObj = conductObj[0]
    else:
        return {},404
    data = json.loads(api.request.data)

    flowchartOperators = data["operators"]
    flowchartLinks = data["links"]

    flowchartResponse = { "operators" : { "delete" : {}, "create" : {}, "update" : {} }, "links" : { "delete" : {}, "create" : {}, "update" : {} } }

    # Getting all UI flow details for flows in this conduct
    flows = [ x for x in conductObj["flow"] ]
    flowTriggers = [ db.ObjectId(x["triggerID"]) for x in flows if x["type"] == "trigger" ]
    flowActions = [ db.ObjectId(x["actionID"]) for x in flows if x["type"] == "action" ]
    flowsList = [ x["flowID"] for x in flows ]
    linksList = []

    # For every refresh the entire flow object and UI is loaded from the database - this may need improvment for speed in future
    flowsUI = webui._modelUI().getAsClass(api.g.sessionData,query={ "flowID" : { "$in" :flowsList }, "conductID" : conductID })
    actions = action._action().getAsClass(api.g.sessionData,query={ "_id" : { "$in" : flowActions } })
    triggers = trigger._trigger().getAsClass(api.g.sessionData,query={ "_id" : { "$in" : flowTriggers } })
    cache.globalCache.newCache("modelCache",sessionData=api.g.sessionData)

    for flow in flows:
        if "type" in flow:
            flowType = flow["type"]
            if "subtype" in flow:
                flowSubtype = flow["subtype"]
            else:
                flowSubtype = ""
            if "{0}{1}".format(flowType,"ID") in flow:
                objectID = "{0}{1}".format(flowType,"ID")
                flowID = flow["flowID"]
                # Default to create
                flowchartResponseType = "create"
                if flowID in flowchartOperators:
                    # If it already exits then its an update
                    flowchartResponseType = "update"
                # Setting position if it has changed since last pollTime
                foundFlowUI = False
                foundObject = False
                name = flow["flowID"]
                node = {}
                for flowUI in flowsUI:
                    if flow["flowID"] == flowUI.flowID:
                        foundFlowUI = True
                        if flowchartResponseType == "create":
                            node["x"] = flowUI.x
                            node["y"] = flowUI.y
                            node["shape"] = "box"
                            node["widthConstraint"] = { "minimum": 75, "maximum": 275 }
                            node["heightConstraint"] = { "minimum": 35, "maximum": 75 }
                            node["borderWidth"] = 1
                            node["borderWidthSelected"] = 2.5
                            node["font"] = { "color" : "#ddd", "multi": True }
                        elif flowUI.x != flowchartOperators[flowID]["node"]["x"] or flowUI.y != flowchartOperators[flowID]["node"]["y"]:
                            node["x"] = flowUI.x
                            node["y"] = flowUI.y
                        if flow["type"] == "trigger":
                            for t in triggers:
                                if flow["triggerID"] == t._id:
                                    name = t.name
                                    modeClass = cache.globalCache.get("modelCache",t.classID,model.getClassObject,sessionData=api.g.sessionData)[0]
                                    color = None
                                    if t.enabled:
                                        color = "#0a0a0a"
                                    duration = t.maxDuration
                                    if duration == 0:
                                        duration = 60
                                    if (((t.startCheck != 0) and (t.startCheck + duration > time.time())) or (t.lastCheck > time.time()-2.5)):
                                        color = "green"
                                    if ((t.startCheck != 0) and (t.startCheck + duration < time.time())):
                                        color = "red"
                                    if not t.enabled:
                                        color = "gray"

                                    label = "({0},{1})\n<b>{2}</b>\n{3}".format(t.systemID,t.clusterSet,t.name,modeClass.name)
                                    if flowchartResponseType == "create":
                                        node["label"] = label
                                        node["color"] = { "border" : "#2e6da4", "background" : color, "highlight" : { "background" : color } }
                                    else:
                                        if color != flowchartOperators[flowID]["node"]["color"]:
                                            node["color"] = { "border" : "#2e6da4", "background" : color, "highlight" : { "background" : color } }
                                        if label != flowchartOperators[flowID]["node"]["label"]:
                                            node["label"] = label
                                    foundObject = True
                                    break
                        elif flow["type"] == "action":
                            for a in actions:
                                if flow["actionID"] == a._id:
                                    name = a.name
                                    modeClass = cache.globalCache.get("modelCache",a.classID,model.getClassObject,sessionData=api.g.sessionData)[0]

                                    #if modeClass.name == "action":
                                    #    node["shape"] = "diamond"
                                    #    node["size"] = 35

                                    color = None
                                    if a.enabled:
                                        color = "#0a0a0a"
                                    if not a.enabled:
                                        color = "gray"

                                    label = "<b>{0}</b>\n{1}".format(a.name,modeClass.name)
                                    if flowchartResponseType == "create":
                                        node["label"] = label
                                        node["color"] = { "border" : "#2e6da4", "background" : color, "highlight" : { "background" : color } }
                                    else:
                                        if color != flowchartOperators[flowID]["node"]["color"]:
                                            node["color"] = { "border" : "#2e6da4", "background" : color, "highlight" : { "background" : color } }
                                        if label != flowchartOperators[flowID]["node"]["label"]:
                                            node["label"] = label
                                    foundObject = True
                                    break
                        if node:
                            if not foundObject:
                                node["label"] = "Unknown Object"
                                node["color"] = { "background" : "black" }
                            flowchartResponse["operators"][flowchartResponseType][flowID] = { "_id" : flow[objectID], "flowID" : flowID, "flowType" : flowType, "flowSubtype" : flowSubtype, "name" : name, "node" : node }
                        break
                if not foundFlowUI:
                    node["x"] = 0
                    node["y"] = 0
                    node["shape"] = "dot"
                    node["borderWidth"] = 1
                    node["label"] = "Unknown Object"
                    node["color"] = { "background" : "black" }
                    flowchartResponse["operators"][flowchartResponseType][flowID] = { "_id" : flow[objectID], "flowID" : flowID, "flowType" : flowType, "flowSubtype" : flowSubtype, "node" : node }
 
                # Do any links need to be created
                for nextFlow in flow["next"]:
                    linkName = "{0}->{1}".format(flowID,nextFlow["flowID"])
                    color = "green"
                    if type(nextFlow["logic"]) is bool:
                        if nextFlow["logic"] == True:
                            color = "#3dbeff"
                        else:
                            color = "#ff2c10"
                    elif type(nextFlow["logic"]) is str:
                        if nextFlow["logic"].startswith("if "):
                            color = "purple"
                    linksList.append(linkName)
                    if linkName not in flowchartLinks.keys():
                        flowchartResponse["links"]["create"][linkName] = { "from" : flowID, "to" : nextFlow["flowID"], "logic" : nextFlow["logic"], "color" : color }
                    elif flowchartLinks[linkName]["color"] != color:
                        flowchartResponse["links"]["update"][linkName] = { "from" : flowID, "to" : nextFlow["flowID"], "logic" : nextFlow["logic"], "color" : color }

    # Checking for deleted operators
    for flowchartOperator in flowchartOperators:
        if flowchartOperator not in flowsList:
            flowchartResponse["operators"]["delete"][flowchartOperator] = { "flowID" : flowchartOperator }
    # Checking for deleted links
    for flowchartLink in flowchartLinks.keys():
        if flowchartLink not in linksList:
            flowchartResponse["links"]["delete"][flowchartLink] = { "linkName" : flowchartLink }

    return flowchartResponse, 200

@api.webServer.route("/conductEditor/<conductID>/export/", methods=["GET"])
def conductExport(conductID):
    conductObj = conduct._conduct().getAsClass(api.g.sessionData,id=conductID)
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
                if flow["flowID"] == currentFlowID:
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

    # Regenerate flowIDs
    flowLookup = {}
    flowLookupReverse = {}
    for flow in flows:
        if flow["flowID"] not in flowLookup:
            flowLookup[flow["flowID"]] = str(uuid.uuid4())
            flowLookupReverse[flowLookup[flow["flowID"]]] = flow["flowID"]
        flow["flowID"] = flowLookup[flow["flowID"]]
        for nextFlow in flow["next"]:
            if nextFlow["flowID"] not in flowLookup:
                flowLookup[nextFlow["flowID"]] = str(uuid.uuid4())
                flowLookupReverse[flowLookup[nextFlow["flowID"]]] = nextFlow["flowID"]
            nextFlow["flowID"] = flowLookup[nextFlow["flowID"]]

    flowTriggers = [ db.ObjectId(x["triggerID"]) for x in flows if x["type"] == "trigger" ]
    flowActions = [ db.ObjectId(x["actionID"]) for x in flows if x["type"] == "action" ]
    actions = action._action().getAsClass(api.g.sessionData,query={ "_id" : { "$in" : flowActions } })
    triggers = trigger._trigger().getAsClass(api.g.sessionData,query={ "_id" : { "$in" : flowTriggers } })
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
            classObj = _class = model._model().getAsClass(api.g.sessionData,id=obj.classID)
            classObj = classObj[0]
            if obj._id not in result[flow["type"]]:
                result[flow["type"]][obj._id] = { "className" : classObj.name }
                blacklist = ["acl","classID","workerID","startCheck","nextCheck","lastUpdateTime","creationTime","systemID"]
                typeList = [str,int,float,dict,list]
                members = [attr for attr in dir(obj) if not callable(getattr(obj, attr)) and not "__" in attr and attr ]
                for member in members:
                    if member not in blacklist:
                        value = getattr(obj,member)
                        if type(value) in typeList:
                            result[flow["type"]][obj._id][member] = value
            if flow["flowID"] not in result["ui"]:
                result["ui"][flow["flowID"]] = { "x" : 0, "y" : 0, "title" : "" }
                flowUI = webui._modelUI().getAsClass(api.g.sessionData,query={ "flowID" : flowLookupReverse[flow["flowID"]], "conductID" : conductID })
                if len(flowUI) > 0:
                    flowUI = flowUI[0]
                    result["ui"][flow["flowID"]]["x"] = flowUI.x
                    result["ui"][flow["flowID"]]["y"] = flowUI.y
                    result["ui"][flow["flowID"]]["title"] = flowUI.title
    return render_template("blank.html",content=result, CSRF=api.g.sessionData["CSRF"]), 200

@api.webServer.route("/conductEditor/<conductID>/import/", methods=["GET"])
def conductImport(conductID):
    return render_template("import.html", CSRF=api.g.sessionData["CSRF"]), 200

@api.webServer.route("/conductEditor/<conductID>/import/", methods=["POST"])
def conductImportData(conductID):
    conductObj = conduct._conduct().getAsClass(api.g.sessionData,id=conductID)
    if len(conductObj) == 1:
        conductObj = conductObj[0]
    else:
        return { }, 404
    access, accessIDs, adminBypass = db.ACLAccess(api.g.sessionData,conductObj.acl,"write")
    if access:
        data = json.loads(api.request.data)
        importData = helpers.typeCast(data["importData"])
        if data["appendObjects"]:
            conductObj.flow = conductObj.flow + importData["flow"]
        else:
            conductObj.flow=importData["flow"]
        for flow in importData["flow"]:
            flowUI = webui._modelUI().getAsClass(api.g.sessionData,query={ "flowID" : flow["flowID"], "conductID" : conductID })
            if len(flowUI) > 0:
                flowUI = flowUI[0]
                flowUI.x = importData["ui"][flow["flowID"]]["x"] + int(data["offsetX"])
                flowUI.y = importData["ui"][flow["flowID"]]["y"] + int(data["offsetY"])
                flowUI.title = importData["ui"][flow["flowID"]]["title"]
                flowUI.update(["x","y","title"])
            else:
                webui._modelUI().new(conductObj._id,conductObj.acl,flow["flowID"],importData["ui"][flow["flowID"]]["x"],importData["ui"][flow["flowID"]]["y"],importData["ui"][flow["flowID"]]["title"])
            if flow["type"] == "trigger":
                classObj = _class = model._model().getAsClass(api.g.sessionData,query={ "name" : importData["trigger"][flow["triggerID"]]["className"] })
                if len(classObj) > 0:
                    classObj = classObj[0]
                    existingTrigger = []
                    if data["duplicateObjects"] == False:
                        existingTrigger = trigger._trigger().getAsClass(api.g.sessionData,query={ "name" : importData["trigger"][flow["triggerID"]]["name"], "classID" : classObj._id })
                    if len(existingTrigger) > 0:
                        existingTrigger = existingTrigger[0]
                    else:
                        _class = classObj.classObject()
                        newObjectID = _class().new(importData["trigger"][flow["triggerID"]]["name"]).inserted_id
                        existingTrigger = _class().getAsClass(api.g.sessionData,id=newObjectID)[0]
                        existingTrigger.acl = conductObj.acl
                        existingTrigger.update(["acl"])
                    members = [attr for attr in dir(existingTrigger) if not callable(getattr(existingTrigger, attr)) and not "__" in attr and attr ]
                    blacklist = ["_id","classID","className","acl","lastCheck"]
                    updateList = []
                    for member in members:
                        if member in importData["trigger"][flow["triggerID"]]:
                            if member not in blacklist:
                                if data["duplicateObjects"] and member == "name":
                                    setattr(existingTrigger,member,"{0}-{1}".format(importData["trigger"][flow["triggerID"]][member],existingTrigger._id))
                                else:
                                    setattr(existingTrigger,member,importData["trigger"][flow["triggerID"]][member])
                                updateList.append(member)
                    existingTrigger.update(updateList,sessionData=api.g.sessionData)
                    flow["triggerID"] = existingTrigger._id
            elif flow["type"] == "action":
                classObj = _class = model._model().getAsClass(api.g.sessionData,query={ "name" : importData["action"][flow["actionID"]]["className"] })
                if len(classObj) > 0:
                    classObj = classObj[0]
                    existingAction = []
                    if data["duplicateObjects"] == False:
                        existingAction = action._action().getAsClass(api.g.sessionData,query={ "name" : importData["action"][flow["actionID"]]["name"], "classID" : classObj._id })
                    if len(existingAction) > 0:
                        existingAction = existingAction[0]
                    else:
                        _class = classObj.classObject()
                        newObjectID = _class().new(importData["action"][flow["actionID"]]["name"]).inserted_id
                        existingAction = _class().getAsClass(api.g.sessionData,id=newObjectID)[0]
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
                    existingAction.update(updateList,sessionData=api.g.sessionData)
                    flow["actionID"] = existingAction._id
    conductObj.update(["flow"],sessionData=api.g.sessionData)
    return {}, 200

@api.webServer.route("/conductEditor/<conductID>/codify/", methods=["GET"])
def getConductFlowCodify(conductID):
    def generateFlow(currentFlow,flowDict,triggers,actions):
        flowCode = ""
        processQueue = []
        indentLevel = 0
        logic = None
        while True:
            if currentFlow:
                obj = None
                if currentFlow["type"] == "trigger":
                    for t in triggers:
                        if flow["triggerID"] == t._id:
                            obj = t
                            break
                    for nextFlow in currentFlow["next"]:
                        processQueue.append({ "flowID" : nextFlow["flowID"], "indentLevel": indentLevel+1, "logic" : nextFlow["logic"] })
                elif currentFlow["type"] == "action":
                    for a in actions:
                        if currentFlow["actionID"] == a._id:
                            obj = a
                            break
                    for nextFlow in currentFlow["next"]:
                        processQueue.append({ "flowID" : nextFlow["flowID"], "indentLevel": indentLevel+1, "logic" : nextFlow["logic"] })
                if obj:
                    classObj = _class = model._model().getAsClass(api.g.sessionData,id=obj.classID)
                    classObj = classObj[0]
                    blacklist = ["_id","acl","classID","workerID","startCheck","nextCheck","lastUpdateTime","lastCheck","clusterSet","concurrency","creationTime","schedule","systemID"]
                    typeList = [str,int,float,dict,list]
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

    conductObj = conduct._conduct().getAsClass(api.g.sessionData,id=conductID)
    if len(conductObj) == 1:
        conductObj = conductObj[0]
    else:
        return { }, 404

    # Getting all UI flow details for flows in this conduct
    flows = [ x for x in conductObj.flow ]
    flowDict = {}
    for flow in flows:
        flowDict[flow["flowID"]] = flow
    flowTriggers = [ db.ObjectId(x["triggerID"]) for x in flows if x["type"] == "trigger" ]
    flowActions = [ db.ObjectId(x["actionID"]) for x in flows if x["type"] == "action" ]

    actions = action._action().getAsClass(api.g.sessionData,query={ "_id" : { "$in" : flowActions } })
    triggers = trigger._trigger().getAsClass(api.g.sessionData,query={ "_id" : { "$in" : flowTriggers } })

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
            return { "result" : flowCode, "CSRF" : api.g.sessionData["CSRF"] }, 200

    return render_template("blank.html",content=flowCode, CSRF=api.g.sessionData["CSRF"]), 200

@api.webServer.route("/conductEditor/<conductID>/flow/<flowID>/", methods=["DELETE"])
def deleteFlow(conductID,flowID):
    conductObj = conduct._conduct().getAsClass(api.g.sessionData,id=conductID)
    if len(conductObj) == 1:
        conductObj = conductObj[0]
    else:
        return { }, 404
    access, accessIDs, adminBypass = db.ACLAccess(api.g.sessionData,conductObj.acl,"write")
    if access:
        if db.fieldACLAccess(api.g.sessionData,conductObj.acl,"flow","delete"):
            flow = [ x for x in conductObj.flow if x["flowID"] ==  flowID]
            if len(flow) == 1:
                flow = flow[0]
                for flowItemsValue in conductObj.flow:
                    for nextflowValue in flowItemsValue["next"]:
                        if nextflowValue["flowID"] == flowID:
                            conductObj.flow[conductObj.flow.index(flowItemsValue)]["next"].remove(nextflowValue)
                conductObj.flow.remove(flow)
                if "_id" in api.g.sessionData:
                    audit._audit().add("flow","delete",{ "_id" : api.g.sessionData["_id"], "user" : api.g.sessionData["user"], "conductID" : conductID, "flowID" : flowID })
                else:
                    audit._audit().add("flow","delete",{ "user" : "system", "conductID" : conductID, "flowID" : flowID })
                conductObj.update(["flow"],sessionData=api.g.sessionData)
            return { }, 200
        else:
            return { }, 404
    else:
        return { }, 404

@api.webServer.route("/conductEditor/<conductID>/flow/", methods=["PUT"])
def newFlow(conductID):
    conductObj = conduct._conduct().getAsClass(api.g.sessionData,id=conductID)
    if len(conductObj) == 1:
        conductObj = conductObj[0]
    else:
        return { }, 404

    access, accessIDs, adminBypass = db.ACLAccess(api.g.sessionData,conductObj.acl,"write")
    if access:
        data = json.loads(api.request.data)
        # Get new UUID store within current conduct flow and return UUID
        newFlowID = str(uuid.uuid4())
        flow = {
            "flowID" : newFlowID, 
            "next" : []
        }
        # Creating new object of model type
        _class = model._model().getAsClass(api.g.sessionData,id=data["classID"])
        if _class:
            subtype = _class[0].name
            _class = _class[0].classObject()
            newFlowObjectID = _class().new(flow["flowID"]).inserted_id
            # Working out by bruteforce which type this is ( try and load it by parent class and check for error) - get on trigger if it does not exist will return None
            modelFlowObjectType = "action"
            if len(trigger._trigger().getAsClass(api.g.sessionData,id=newFlowObjectID)) > 0:
                modelFlowObjectType = "trigger"
            modelFlowObject = _class().getAsClass(api.g.sessionData,id=newFlowObjectID)
            if len(modelFlowObject) == 1:
                modelFlowObject = modelFlowObject[0]
            else:
                return { }, 404
            modelFlowObject.acl = { "ids" : [ { "accessID" : api.g.sessionData["primaryGroup"], "read" : True, "write" : True, "delete" : True } ] }
            modelFlowObject.update(["acl"],sessionData=api.g.sessionData)
            flow["type"] = modelFlowObjectType
            if subtype != "action" and subtype != "trigger":
                flow["subtype"] = subtype
            flow["{0}{1}".format(modelFlowObjectType,"ID")] = str(newFlowObjectID)
            # Adding UI position for cloned object
            webui._modelUI().new(conductID,conductObj.acl,flow["flowID"],data["x"],data["y"],modelFlowObject.name)
            # Appending new object to conduct
            conductObj.flow.append(flow)
            if "_id" in api.g.sessionData:
                audit._audit().add("flow","create",{ "_id" : api.g.sessionData["_id"], "user" : api.g.sessionData["user"], "conductID" : conductID, "newFlowID" : newFlowID })
            else:
                audit._audit().add("flow","create",{ "user" : "system", "conductID" : conductID, "newFlowID" : newFlowID })
            conductObj.update(["flow"],sessionData=api.g.sessionData)
            return { }, 201
    else:
        return { }, 403

    return { }, 404
    
@api.webServer.route("/conductEditor/<conductID>/flow/", methods=["POST"])
def dropExistingObject(conductID):
    conductObj = conduct._conduct().getAsClass(api.g.sessionData,id=conductID)
    if len(conductObj) == 1:
        conductObj = conductObj[0]
    else:
        return { }, 404
    access, accessIDs, adminBypass = db.ACLAccess(api.g.sessionData,conductObj.acl,"write")
    if access:
        data = json.loads(api.request.data)
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
                modelFlowObject = trigger._trigger().getAsClass(api.g.sessionData,id=data["_id"])[0]
            elif data["flowType"] == "action":
                modelFlowObject = action._action().getAsClass(api.g.sessionData,id=data["_id"])[0]
            if modelFlowObject:
                name = modelFlowObject.name
            else:
                name = flow["flowID"]

            webui._modelUI().new(conductID,conductObj.acl,flow["flowID"],data["x"],data["y"],name)
            if "_id" in api.g.sessionData:
                audit._audit().add("flow","drop",{ "_id" : api.g.sessionData["_id"], "user" : api.g.sessionData["user"], "conductID" : conductID, "objectID" : data["_id"], "newFlowID" : newFlowID })
            else:
                audit._audit().add("flow","drop",{ "user" : "system", "conductID" : conductID, "objectID" : data["_id"], "newFlowID" : newFlowID })
            conductObj.flow.append(flow)
            conductObj.update(["flow"],sessionData=api.g.sessionData)
            return { }, 201
    return { }, 404

@api.webServer.route("/conductEditor/<conductID>/flow/<flowID>/", methods=["POST"])
def updateFlow(conductID,flowID):
    conductObj = conduct._conduct().getAsClass(api.g.sessionData,id=conductID)
    if len(conductObj) == 1:
        conductObj = conductObj[0]
    else:
        return { }, 404

    flow = [ x for x in conductObj.flow if x["flowID"] ==  flowID]
    if len(flow) == 1:
        flow = flow[0]
        data = json.loads(api.request.data)
        if data["action"] == "update":
            access, accessIDs, adminBypass = db.ACLAccess(api.g.sessionData,conductObj.acl,"write")
            if access:
                if "x" in data and "y" in data:
                    try:
                        x = int(data["x"])
                        y = int(data["y"])
                    except:
                        return { }, 403
                flowUI = webui._modelUI().getAsClass(api.g.sessionData,query={ "flowID" : flow["flowID"], "conductID" : conductID })
                if len(flowUI) == 1:
                    flowUI = flowUI[0]
                    if "x" in data and "y" in data:
                        flowUI.x = x
                        flowUI.y = y
                        if "_id" in api.g.sessionData:
                            audit._audit().add("flow","update",{ "_id" : api.g.sessionData["_id"], "user" : api.g.sessionData["user"], "conductID" : conductID, "flowID" : flowID, "x" : x, "y" : y })
                        else:
                            audit._audit().add("flow","update",{ "user" : "system", "conductID" : conductID, "flowID" : flowID, "x" : x, "y" : y })
                        flowUI.update(["x","y"],sessionData=api.g.sessionData)
                    if "title" in data:
                        flowUI.title = data["title"]
                        if "_id" in api.g.sessionData:
                            audit._audit().add("flow","update",{ "_id" : api.g.sessionData["_id"], "user" : api.g.sessionData["user"], "conductID" : conductID, "flowID" : flowID, "title" :data["title"] })
                        else:
                            audit._audit().add("flow","update",{ "user" : "system", "conductID" : conductID, "flowID" : flowID, "title" :data["title"] })
                        flowUI.update(["title"],sessionData=api.g.sessionData)
                    return { }, 200
                else:
                    webui._modelUI().new(conductID,conductObj.acl,flow["flowID"],x,y)
                    return { }, 201
        elif data["action"] == "copy":
            access, accessIDs, adminBypass = db.ACLAccess(api.g.sessionData,conductObj.acl,"write")
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
                    if "_id" in api.g.sessionData:
                        audit._audit().add("flow","copy",{ "_id" : api.g.sessionData["_id"], "user" : api.g.sessionData["user"], "conductID" : conductID, "flowID" : flowID })
                    else:
                        audit._audit().add("flow","copy",{ "user" : "system", "conductID" : conductID, "flowID" : flowID })
                    flowUI = webui._modelUI().getAsClass(api.g.sessionData,query={ "flowID" : flow["flowID"], "conductID" : conductID })[0]
                    webui._modelUI().new(conductID,conductObj.acl,newFlow["flowID"],data["x"],data["y"],flowUI.title)
                    conductObj.flow.append(newFlow)
                    conductObj.update(["flow"],sessionData=api.g.sessionData)
                    return { }, 201
        elif data["action"] == "clone":
            access, accessIDs, adminBypass = db.ACLAccess(api.g.sessionData,conductObj.acl,"write")
            if access:
                flow = [ x for x in conductObj.flow if x["flowID"] ==  data["operatorId"]]
                if len(flow) == 1:
                    flow = flow[0]
                    data = json.loads(api.request.data)
                    modelFlowObject = None
                    # Check if the modelType and object are unchanged
                    if "type" in flow:
                        if flow["type"] == "trigger":
                            modelFlowObject = trigger._trigger().getAsClass(api.g.sessionData,id=flow["{0}{1}".format(flow["type"],"ID")])
                            if len(modelFlowObject) == 1:
                                modelFlowObject = modelFlowObject[0]
                            modelFlowObjectType = "trigger"
                        if flow["type"] == "action":
                            modelFlowObject = action._action().getAsClass(api.g.sessionData,id=flow["{0}{1}".format(flow["type"],"ID")])
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
                            _class = model._model().getAsClass(api.g.sessionData,id=modelFlowObject.classID)
                            if _class:
                                _class = _class[0].classObject()
                                # Bug exists as name value is not requried by db class but is for core models - this could result in an error if new model is added that does not accept name within new function override
                                newFlowObjectID = _class().new(flow["flowID"]).inserted_id

                                # Working out by bruteforce which type this is ( try and load it by parent class and check for error) - get on trigger if it does not exist will return None
                                modelFlowObjectClone = _class().getAsClass(api.g.sessionData,id=newFlowObjectID)
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
                                modelFlowObjectClone.update(updateList,sessionData=api.g.sessionData)

                                # Set conduct flow to correct type and objectID
                                flow["{0}{1}".format(flow["type"],"ID")] = str(newFlowObjectID)
                                conductObj.flow.append(flow)

                                # Adding UI position for cloned object
                                flowUI = webui._modelUI().getAsClass(api.g.sessionData,query={ "flowID" : flowID, "conductID" : conductID })[0]
                                webui._modelUI().new(conductID,conductObj.acl,flow["flowID"],data["x"],data["y"],"Copy - {0}".format(flowUI.title))
                                conductObj.update(["flow"],sessionData=api.g.sessionData)
                                if "_id" in api.g.sessionData:
                                    audit._audit().add("flow","duplicate",{ "_id" : api.g.sessionData["_id"], "user" : api.g.sessionData["user"], "conductID" : conductID, "flowID" : flowID, "newFlowID" : newFlowID })
                                else:
                                    audit._audit().add("flow","duplicate",{ "user" : "system", "conductID" : conductID, "flowID" : flowID, "newFlowID" : newFlowID })
                                return { "result" : True}, 201
    return { }, 404

@api.webServer.route("/conductEditor/<conductID>/flowLink/<fromFlowID>/<toFlowID>/", methods=["PUT"])
def newFlowLink(conductID,fromFlowID,toFlowID):
    conductObj = conduct._conduct().getAsClass(api.g.sessionData,id=conductID)
    if len(conductObj) == 1:
        conductObj = conductObj[0]
    else:
        return { }, 404
    access, accessIDs, adminBypass = db.ACLAccess(api.g.sessionData,conductObj.acl,"write")
    if access:
        fromFlow = [ x for x in conductObj.flow if x["flowID"] ==  fromFlowID][0]
        toFlow = [ x for x in conductObj.flow if x["flowID"] ==  toFlowID][0]
        nextFlows = [ x for x in fromFlow["next"] if x["flowID"] ==  toFlowID]
        if len(nextFlows) == 0:
            if toFlow["type"] != "trigger":
                fromFlow["next"].append({ "flowID" : toFlowID, "logic": True })
                if "_id" in api.g.sessionData:
                    audit._audit().add("flow","new link",{ "_id" : api.g.sessionData["_id"], "user" : api.g.sessionData["user"], "conductID" : conductID, "fromFlowID" : fromFlowID, "toFlowID": toFlowID })
                else:
                    audit._audit().add("flow","new link",{ "user" : "system", "conductID" : conductID, "fromFlowID" : fromFlowID, "toFlowID": toFlowID })
                conductObj.update(["flow"],sessionData=api.g.sessionData)
                return { }, 201
            else:
                return { }, 403
        return { }, 200
    else:
        return { }, 403

@api.webServer.route("/conductEditor/<conductID>/flowLink/<fromFlowID>/<toFlowID>/", methods=["DELETE"])
def deleteFlowLink(conductID,fromFlowID,toFlowID):
    conductObj = conduct._conduct().getAsClass(api.g.sessionData,id=conductID)
    if len(conductObj) == 1:
        conductObj = conductObj[0]
    else:
        return { }, 404
    access, accessIDs, adminBypass = db.ACLAccess(api.g.sessionData,conductObj.acl,"write")
    if access:
        fromFlow = [ x for x in conductObj.flow if x["flowID"] ==  fromFlowID]
        if len(fromFlow) > 0:
            fromFlow = fromFlow[0]
            for nextflow in fromFlow["next"]:
                if nextflow["flowID"] == toFlowID:
                    if db.fieldACLAccess(api.g.sessionData,conductObj.acl,"flow","delete"):
                        conductObj.flow[conductObj.flow.index(fromFlow)]["next"].remove(nextflow)
                        if "_id" in api.g.sessionData:
                            audit._audit().add("flow","delete link",{ "_id" : api.g.sessionData["_id"], "user" : api.g.sessionData["user"], "conductID" : conductID, "fromFlowID" : fromFlowID, "toFlowID": toFlowID })
                        else:
                            audit._audit().add("flow","delete link",{ "user" : "system", "conductID" : conductID, "fromFlowID" : fromFlowID, "toFlowID": toFlowID })
                        conductObj.update(["flow"])
                        return { }, 200
                    return {}, 403
        return { }, 404
    else:
        return {}, 403


@api.webServer.route("/conduct/<conductID>/editACL/<flowID>", methods=["GET"])
def getACL(conductID,flowID):
    conductObj = conduct._conduct().getAsClass(api.g.sessionData,id=conductID)
    if len(conductObj) == 1:
        conductObj = conductObj[0]
    else:
        return { }, 404

    flow = [ x for x in conductObj.flow if x["flowID"] == flowID]
    if len(flow) == 1:
        flow = flow[0]
        if "type" in flow:
            if flow["type"] == "trigger":
                modelFlowObject = trigger._trigger().getAsClass(api.g.sessionData,id=flow["{0}{1}".format(flow["type"],"ID")])
                if len(modelFlowObject) == 1:
                    modelFlowObject = modelFlowObject[0]
            if flow["type"] == "action":
                modelFlowObject = action._action().getAsClass(api.g.sessionData,id=flow["{0}{1}".format(flow["type"],"ID")])
                if len(modelFlowObject) == 1:
                    modelFlowObject = modelFlowObject[0]
    acl = None
    if modelFlowObject:
        acl = modelFlowObject.acl

    uiAcl = None
    webObj = webui._modelUI().getAsClass(api.g.sessionData,query={"conductID" : conductID, "flowID" : flowID})
    if len(webObj) == 1:
        webObj = webObj[0]
        uiAcl = webObj.acl

    return {"acl":acl, "uiAcl" : uiAcl}, 200

@api.webServer.route("/conduct/<conductID>/editACL/<flowID>", methods=["POST"])
def editACL(conductID,flowID):
    conductObj = conduct._conduct().getAsClass(api.g.sessionData,id=conductID)
    if len(conductObj) == 1:
        conductObj = conductObj[0]
    else:
        return { }, 404

    data = json.loads(api.request.data)

    flow = [ x for x in conductObj.flow if x["flowID"] == flowID]
    if len(flow) == 1:
        flow = flow[0]
        if "type" in flow:
            if flow["type"] == "trigger":
                modelFlowObject = trigger._trigger().getAsClass(api.g.sessionData,id=flow["{0}{1}".format(flow["type"],"ID")])
                if len(modelFlowObject) == 1:
                    modelFlowObject = modelFlowObject[0]
            if flow["type"] == "action":
                modelFlowObject = action._action().getAsClass(api.g.sessionData,id=flow["{0}{1}".format(flow["type"],"ID")])
                if len(modelFlowObject) == 1:
                    modelFlowObject = modelFlowObject[0]

    objectResult = True
    if modelFlowObject:
        acl = json.loads(data["acl"])
        if acl != modelFlowObject.acl:
            if db.fieldACLAccess(api.g.sessionData,modelFlowObject.acl,"acl","write"):
                modelFlowObject.acl = acl
                if "_id" in api.g.sessionData:
                    audit._audit().add("flow","update",{ "_id" : api.g.sessionData["_id"], "user" : api.g.sessionData["user"], "conductID" : conductID, "flowID" : flowID, "acl" : data["acl"] })
                else:
                    audit._audit().add("flow","update",{ "user" : "system", "conductID" : conductID, "flowID" : flowID, "acl" : data["acl"] })
                modelFlowObject.update(["acl"])
            else:
                objectResult=False
            
    uiResult = True
    webObj = webui._modelUI().getAsClass(api.g.sessionData,query={"conductID" : conductID, "flowID" : flowID})
    if len(webObj) == 1:
        webObj = webObj[0]
        uiAcl = json.loads(data["uiAcl"])
        if webObj.acl != uiAcl:
            if db.fieldACLAccess(api.g.sessionData,webObj.acl,"acl","write"):
                webObj.acl = uiAcl
                if "_id" in api.g.sessionData:
                    audit._audit().add("flow","update",{ "_id" : api.g.sessionData["_id"], "user" : api.g.sessionData["user"], "conductID" : conductID, "flowID" : flowID, "uiAcl" : data["uiAcl"] })
                else:
                    audit._audit().add("flow","update",{ "user" : "system", "conductID" : conductID, "flowID" : flowID, "uiAcl" : data["uiAcl"] })
                webObj.update(["acl"])
            else:
                uiResult = False

    if not objectResult or not uiResult:
        return { }, 403

    return { }, 200   