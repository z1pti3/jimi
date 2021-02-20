import time
import uuid
import json
from functools import wraps

import jimi

class _flowDebug():

    def __init__(self,acl):
        self.flowList = {}
        self.acl = acl
        self.preserveData = []
        self.id = str(uuid.uuid4())

    def getEvent(self,eventID):
        return self.flowList[eventID]

    def startEvent(self,event,data):
        uid = str(uuid.uuid4())
        self.flowList[uid] = { "id" : uid, "type" : "event", "event" : event, "startTime" : time.time(), "endTime" : 0, "execution" : {}, "preserveDataID" : len(self.preserveData) }
        self.preserveData.append([data["persistentData"],data["eventData"]])
        return uid

    def endEvent(self,eventID):
        self.flowList[eventID]["endTime"] = time.time()

    def getLinkLogic(self,eventID,logicID):
        return self.flowList[eventID]["execution"][logicID]

    def startLinkLogic(self,eventID,logicString):
        uid = str(uuid.uuid4())
        self.flowList[eventID]["execution"][uid] = { "id" : uid, "type" : "linkLogic", "logicString" : logicString, "startTime" : time.time(), "endTime" : 0, "logicResult" : None }
        return uid
    
    def endLinkLogic(self,eventID,logicID,logicResult):
        self.flowList[eventID]["execution"][logicID]["logicResult"] = logicResult
        self.flowList[eventID]["execution"][logicID]["endTime"] = time.time()

    def getAction(self,eventID,actionID):
        return self.flowList[eventID]["execution"][actionID]

    def startAction(self,eventID,flowID,actionName,data):
        uid = str(uuid.uuid4())
        self.flowList[eventID]["execution"][uid] = { "id" : uid, "type" : "action", "flowID" : flowID, "name" : actionName, "dataIn" : data, "startTime" : time.time(), "endTime" : 0, "dataOut" : None }
        return uid

    def endAction(self,eventID,actionID,data):
        self.flowList[eventID]["execution"][actionID]["dataOut"] = data
        self.flowList[eventID]["execution"][actionID]["endTime"] = time.time()

    def getVar(self,eventID,varID):
        return self.flowList[eventID]["execution"][varID]

    def setVar(self,eventID,actionID,varName,varValue):
        uid = str(uuid.uuid4())
        self.flowList[eventID]["execution"][uid] = { "id" : uid, "type" : "var", "actionID" : actionID, "varName" : varName, "varValue" : varValue, "startTime" : time.time(), "endTime" : time.time() }
        return uid

def newFlowDebugSession(acl={ "ids":[ { "accessID":"0","delete": True,"read": True,"write": True } ] }):
    global flowDebugSession
    try:
        if not flowDebugSession:
            flowDebugSession = {}
    except NameError:
        flowDebugSession = {}
    newSession = _flowDebug(acl)
    flowDebugSession[newSession.id] = newSession
    return newSession.id

def deleteFlowDebugSession(sessionID):
    global flowDebugSession
    del flowDebugSession[sessionID]

def fn_timer(function):
    @wraps(function)
    def function_timer(*args, **kwargs):
        t0 = time.time()
        result = function(*args, **kwargs)
        t1 = time.time()
        print ("Total time running %s: %s seconds" %
               (function.__name__, str(t1-t0))
               )
        return result
    return function_timer

def debugEventHandler(sessionID,conduct,trigger,flowID,events,data=None,preserveDataID=-1):
    if data and preserveDataID > -1:
        data["persistentData"] = flowDebugSession[sessionID].preserveData[preserveDataID][0]
        data["eventData"] =  flowDebugSession[sessionID].preserveData[preserveDataID][1]
    data = jimi.conduct.dataTemplate(data)
    data["persistentData"]["system"]["trigger"] = trigger
    data["flowData"]["trigger_id"] = trigger._id
    data["flowData"]["trigger_name"] = trigger.name
    for index, event in enumerate(events):
        first = True if index == 0 else False
        last = True if index == len(events) - 1 else False
        eventStat = { "first" : first, "current" : index + 1, "total" : len(events), "last" : last }

        tempData = jimi.conduct.copyData(data)
        tempData["flowData"]["event"] = event
        tempData["flowData"]["eventStats"] = eventStat

        conduct.triggerHandler(flowID,tempData,flowIDType=True,flowDebugSession={ "sessionID" : sessionID })


######### --------- API --------- #########
if jimi.api.webServer:
    if not jimi.api.webServer.got_first_request:
        if jimi.api.webServer.name == "jimi_core":
            @jimi.api.webServer.route(jimi.api.base+"debug/", methods=["PUT"])
            def startFlowDebugSession():
                sessionID = newFlowDebugSession( { "ids" : [ { "accessID" : jimi.api.g.sessionData["primaryGroup"], "read" : True, "write" : True, "delete" : True } ] })
                return { "sessionID" : sessionID }, 200

            @jimi.api.webServer.route(jimi.api.base+"debug/<sessionID>/<conductID>/<flowID>/", methods=["POST"])
            def startDebuggerTrigger(sessionID,conductID,flowID):
                if jimi.db.ACLAccess(jimi.api.g.sessionData, flowDebugSession[sessionID].acl):
                    requestData = json.loads(jimi.api.request.data)
                    try:
                        dataIn = json.loads(requestData["dataIn"])
                    except KeyError:
                        dataIn = None
                    data = None
                    try:
                        preserveData = int(requestData["preserveDataID"])
                    except KeyError:
                        preserveData = -1

                    c = jimi.conduct._conduct().getAsClass(sessionData=jimi.api.g.sessionData,id=conductID)[0]
                    flow = [ x for x in c.flow if x["flowID"] == flowID ][0]
                    if "triggerID" in flow:
                        t = jimi.trigger._trigger().getAsClass(sessionData=jimi.api.g.sessionData,id=flow["triggerID"])[0]
                        if dataIn:
                            if type(dataIn) is list:
                                events = dataIn
                            elif type(dataIn) is dict:
                                events = [dataIn["flowData"]["event"]]
                                data = dataIn
                        else:
                            t.data = { "flowData" : { "var" : {}, "plugin" : {} } }
                            events = t.doCheck()
                    else:
                        t = jimi.action._action().getAsClass(sessionData=jimi.api.g.sessionData,id=flow["actionID"])[0]
                        if dataIn:
                            if type(dataIn) is list:
                                events = dataIn
                            elif type(dataIn) is dict:
                                events = [dataIn["flowData"]["event"]]
                                data = dataIn
                        else:
                            events = [1]
                    jimi.workers.workers.new("debug{0}".format(sessionID),debugEventHandler,(sessionID,c,t,flowID,events,data,preserveData))
                    return {}, 200
                return (), 404
                
            @jimi.api.webServer.route(jimi.api.base+"debug/<sessionID>/", methods=["GET"])
            def getFlowDebugSession(sessionID):
                if jimi.db.ACLAccess(jimi.api.g.sessionData, flowDebugSession[sessionID].acl):
                    return flowDebugSession[sessionID].flowList, 200
                return {}, 404

            @jimi.api.webServer.route(jimi.api.base+"debug/<sessionID>/list/", methods=["GET"])
            def getFlowDebugSessionList(sessionID):
                if jimi.db.ACLAccess(jimi.api.g.sessionData, flowDebugSession[sessionID].acl):
                    result = []
                    for flowKey, flowValue  in flowDebugSession[sessionID].flowList.items():
                        event = flowValue["event"]
                        if type(event) is dict or type(event) is list:
                            event = jimi.helpers.dictToJson(event)
                        result.append({ "id" : flowKey, "event" : event, "preserveDataID" : flowValue["preserveDataID"] })
                    return {"flowList" : result }, 200
                return {}, 404

            @jimi.api.webServer.route(jimi.api.base+"debug/<sessionID>/<eventID>/", methods=["GET"])
            def getFlowDebugSessionFlow(sessionID,eventID):
                if jimi.db.ACLAccess(jimi.api.g.sessionData, flowDebugSession[sessionID].acl):
                    return jimi.helpers.dictToJson(flowDebugSession[sessionID].flowList[eventID]), 200
                return {}, 404

            @jimi.api.webServer.route(jimi.api.base+"debug/<sessionID>/<eventID>/executionList/", methods=["GET"])
            def getFlowDebugSessionFlowExecutionList(sessionID,eventID):
                if jimi.db.ACLAccess(jimi.api.g.sessionData, flowDebugSession[sessionID].acl):
                    result = []
                    for executionKey, executionValue  in flowDebugSession[sessionID].flowList[eventID]["execution"].items():
                        result.append({ "id" : executionKey, "name" : executionValue["name"] })
                    return {"executionList" : result}, 200
                return {}, 404

            @jimi.api.webServer.route(jimi.api.base+"debug/<sessionID>/<eventID>/<executionID>/", methods=["GET"])
            def getFlowDebugSessionFlowExecution(sessionID,eventID,executionID):
                if jimi.db.ACLAccess(jimi.api.g.sessionData, flowDebugSession[sessionID].acl):
                    return jimi.helpers.dictToJson(flowDebugSession[sessionID].flowList[eventID]["execution"][executionID]), 200
                return {}, 404

            @jimi.api.webServer.route(jimi.api.base+"debug/<sessionID>/<eventID>/<flowID>/flowID/", methods=["GET"])
            def getFlowDebugSessionFlowExecutionByFlowID(sessionID,eventID,flowID):
                if jimi.db.ACLAccess(jimi.api.g.sessionData, flowDebugSession[sessionID].acl):
                    keys = list(flowDebugSession[sessionID].flowList[eventID]["execution"].keys())
                    if len(keys) > 1:
                        keys.reverse()
                    for executionID in keys:
                        if flowDebugSession[sessionID].flowList[eventID]["execution"][executionID]["flowID"] == flowID:
                            return jimi.helpers.dictToJson(flowDebugSession[sessionID].flowList[eventID]["execution"][executionID]), 200
                return {}, 404

            @jimi.api.webServer.route(jimi.api.base+"debug/<sessionID>/", methods=["DELETE"])
            def removeFlowDebugSession(sessionID):
                if jimi.db.ACLAccess(jimi.api.g.sessionData, flowDebugSession[sessionID].acl, "delete"):
                    try:
                        del flowDebugSession[sessionID]
                        return {}, 200
                    except KeyError:
                        return {}, 404
                return {}, 404

        if jimi.api.webServer.name == "jimi_web":
            @jimi.api.webServer.route(jimi.api.base+"debug/", methods=["PUT"])
            def startFlowDebugSession():
                apiEndpoint = "debug/"
                # NOTE - sessions can only persist on the same server so if the master changes debug will stop
                url = jimi.cluster.getMaster()
                response = jimi.helpers.apiCall("PUT",apiEndpoint,token=jimi.api.g.sessionToken,overrideURL=url)
                return json.loads(response.text), 200

            @jimi.api.webServer.route(jimi.api.base+"debug/<sessionID>/<conductID>/<flowID>/", methods=["POST"])
            def startDebuggerTrigger(sessionID,conductID,flowID):
                apiEndpoint = "debug/{0}/{1}/{2}/".format(sessionID,conductID,flowID)
                try:
                    data = json.loads(jimi.api.request.data)
                except:
                    data = {}
                url = jimi.cluster.getMaster()
                response = jimi.helpers.apiCall("POST",apiEndpoint,token=jimi.api.g.sessionToken,overrideURL=url,jsonData=data)
                return json.loads(response.text), 200

            @jimi.api.webServer.route(jimi.api.base+"debug/<sessionID>/list/", methods=["GET"])
            def getFlowDebugSessionList(sessionID):
                apiEndpoint = "debug/{0}/list/".format(sessionID)
                url = jimi.cluster.getMaster()
                response = jimi.helpers.apiCall("GET",apiEndpoint,token=jimi.api.g.sessionToken,overrideURL=url)
                return json.loads(response.text), 200

            @jimi.api.webServer.route(jimi.api.base+"debug/<sessionID>/<eventID>/executionList/", methods=["GET"])
            def getFlowDebugSessionFlowExecutionList(sessionID,eventID):
                apiEndpoint = "debug/{0}/{1}/executionList/".format(sessionID,eventID)
                url = jimi.cluster.getMaster()
                response = jimi.helpers.apiCall("GET",apiEndpoint,token=jimi.api.g.sessionToken,overrideURL=url)
                return json.loads(response.text), 200

            @jimi.api.webServer.route(jimi.api.base+"debug/<sessionID>/<eventID>/<executionID>/", methods=["GET"])
            def getFlowDebugSessionFlowExecution(sessionID,eventID,executionID):
                apiEndpoint = "debug/{0}/{1}/{2}/".format(sessionID,eventID,executionID)
                url = jimi.cluster.getMaster()
                response = jimi.helpers.apiCall("GET",apiEndpoint,token=jimi.api.g.sessionToken,overrideURL=url)
                return json.loads(response.text), 200

            @jimi.api.webServer.route(jimi.api.base+"debug/<sessionID>/<eventID>/<flowID>/flowID/", methods=["GET"])
            def getFlowDebugSessionFlowExecutionByFlowID(sessionID,eventID,flowID):
                apiEndpoint = "debug/{0}/{1}/{2}/flowID/".format(sessionID,eventID,flowID)
                url = jimi.cluster.getMaster()
                response = jimi.helpers.apiCall("GET",apiEndpoint,token=jimi.api.g.sessionToken,overrideURL=url)
                return json.loads(response.text), 200