import time
import uuid
import json
import traceback
from functools import wraps

import jimi

flowDebugSession = {}

class _flowDebugSnapshot(jimi.db._document):
    flowListEventUID = str()
    flowListExecutionUID = str()
    flowListExecutionData = dict()

    _dbCollection = jimi.db.db["flowDebugSnapshot"]

    def new(self,acl,flowListEventUID,flowListExecutionUID,flowListExecutionData,sessionData=None):
        self.acl = acl
        self.flowListEventUID = flowListEventUID
        self.flowListExecutionUID = flowListExecutionUID
        self.flowListExecutionData = flowListExecutionData
        super(_flowDebugSnapshot, self).new(sessionData=sessionData)

    def bulkNew(self,bulkClass,acl,flowListEventUID,flowListExecutionUID,flowListExecutionData,sessionData=None):
        self.acl = acl
        self.flowListEventUID = flowListEventUID
        self.flowListExecutionUID = flowListExecutionUID
        self.flowListExecutionData = flowListExecutionData
        super(_flowDebugSnapshot, self).bulkNew(bulkClass,sessionData=sessionData)

    def rebuildDebug(self,sessionData,debugSession,sessionID):
        events = self.query(sessionData=sessionData,query={ "flowListEventUID" : sessionID })["results"]
        for event in events:
            event["flowListExecutionData"]["execution"] = {}
            executions = self.query(sessionData=sessionData,query={ "flowListEventUID" : event["flowListExecutionUID"], "flowListExecutionUID" : { "$in" : event["flowListExecutionData"]["executionIDs"] } })["results"]
            for execution in executions:
                event["flowListExecutionData"]["execution"][execution["flowListExecutionUID"]] = execution["flowListExecutionData"]
            debugSession.flowList[event["flowListExecutionUID"]] = event["flowListExecutionData"]

class _flowDebug():

    def __init__(self,acl,createdBy):
        self.flowList = {}
        self.acl = acl
        self.createdBy = createdBy
        self.createdDate = time.time()
        self.preserveData = []
        self.id = str(uuid.uuid4())

    def getEvent(self,eventID):
        return self.flowList[eventID]

    def startEvent(self,eventName,event,data):
        uid = str(uuid.uuid4())
        if not eventName:
            eventName = uid
        self.flowList[uid] = { "id" : uid, "type" : "event", "name" : eventName, "event" : event, "startTime" : time.time(), "endTime" : 0, "execution" : {}, "preserveDataID" : len(self.preserveData) }
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

def newFlowDebugSession(acl={ "ids":[ { "accessID":"0","delete": True,"read": True,"write": True } ] },createdBy=None):
    global flowDebugSession
    newSession = _flowDebug(acl,createdBy)
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
    if hasattr(trigger, "startCheck"):
        if trigger.startCheck > 0 and trigger.enabled:
            return
        else:
            trigger.startCheck = time.time()
            trigger.update(["startCheck"])
    jimi.cache.globalCache.clearCache("ALL")
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

        try:
            conduct.triggerHandler(flowID,tempData,flowIDType=True,flowDebugSession={ "sessionID" : sessionID })
        except Exception as e:
            flowDebugSession[sessionID].startEvent("Exception Raised",''.join(traceback.format_exception(type(e), e, e.__traceback__)),tempData)
    if hasattr(trigger, "startCheck"):
        trigger.startCheck = 0
        trigger.update(["startCheck"])


######### --------- API --------- #########
if jimi.api.webServer:
    if not jimi.api.webServer.got_first_request:
        if jimi.api.webServer.name == "jimi_core":
            @jimi.api.webServer.route(jimi.api.base+"debug/", methods=["PUT"])
            def startFlowDebugSession():
                sessionID = newFlowDebugSession( { "ids" : [ { "accessID" : jimi.api.g.sessionData["primaryGroup"], "read" : True, "write" : True, "delete" : True } ] },jimi.api.g.sessionData["user"])
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
                    maxDuration = 60
                    if "triggerID" in flow:
                        t = jimi.trigger._trigger(False).getAsClass(sessionData=jimi.api.g.sessionData,id=flow["triggerID"])[0]
                        if dataIn:
                            if type(dataIn) is list:
                                events = dataIn
                                data = jimi.conduct.dataTemplate()
                            elif type(dataIn) is dict:
                                try:
                                    events = [dataIn["flowData"]["event"]]
                                    data = jimi.conduct.dataTemplate(dataIn)
                                except KeyError:
                                    events = [dataIn]
                                    data = jimi.conduct.dataTemplate()
                        else:
                            t.data = { "flowData" : { "var" : {}, "plugin" : {} } }
                            if t.partialResults:
                                events = []
                                for event in t.doCheck():
                                    events.append(event)
                            else:
                                events = t.doCheck()
                        maxDuration = t.maxDuration
                    else:
                        t = jimi.action._action(False).getAsClass(sessionData=jimi.api.g.sessionData,id=flow["actionID"])[0]
                        if dataIn:
                            if type(dataIn) is list:
                                events = dataIn
                            elif type(dataIn) is dict:
                                events = [dataIn["flowData"]["event"]]
                                data = dataIn
                        else:
                            events = [1]
                    jimi.workers.workers.new("debug{0}".format(sessionID),debugEventHandler,(sessionID,c,t,flowID,events,data,preserveData),maxDuration=maxDuration,raiseException=False,debugSession=sessionID)
                    return {}, 200
                return (), 404
                
            @jimi.api.webServer.route(jimi.api.base+"debug/", methods=["GET"])
            def getFlowDebugSessions():
                results = []
                try:
                    for key, session in flowDebugSession.items():
                        if jimi.db.ACLAccess(jimi.api.g.sessionData, session.acl):
                            results.append({ "id" : key, "createdBy" : session.createdBy, "createdDate" : session.createdDate })
                except:
                    pass
                return { "results" : results }, 200

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
                        if type(event) is dict:
                            event = jimi.helpers.dictToJson(event)
                        elif type(event) is list:
                            event = jimi.helpers.listToJson(event)
                        result.append({ "id" : flowKey, "event" : event, "name" : flowValue["name"], "preserveDataID" : flowValue["preserveDataID"] })
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

            @jimi.api.webServer.route(jimi.api.base+"debug/clear/", methods=["GET"])
            @jimi.auth.adminEndpoint
            def clearFlowDebugSessions():
                global flowDebugSession
                flowDebugSession = {}
                return {}, 200

            @jimi.api.webServer.route(jimi.api.base+"debug/clear/<sessionID>/", methods=["GET"])
            @jimi.auth.adminEndpoint
            def clearFlowDebugSession(sessionID):
                global flowDebugSession
                if jimi.db.ACLAccess(jimi.api.g.sessionData, flowDebugSession[sessionID].acl, "read"):
                    flowDebugSession[sessionID].flowList = {}
                    flowDebugSession[sessionID].preserveData = []
                    return {}, 200
                return {}, 403

            @jimi.api.webServer.route(jimi.api.base+"debug/snapshot/<sessionID>/", methods=["PUT"])
            def createDebugSessionFromSnapshot(sessionID):
                global flowDebugSession
                debugSessionID = newFlowDebugSession( { "ids" : [ { "accessID" : jimi.api.g.sessionData["primaryGroup"], "read" : True, "write" : True, "delete" : True } ] },jimi.api.g.sessionData["user"])
                _flowDebugSnapshot().rebuildDebug(jimi.api.g.sessionData,flowDebugSession[debugSessionID],sessionID)
                return { "sessionID" : debugSessionID }, 200

        if jimi.api.webServer.name == "jimi_web":
            @jimi.api.webServer.route(jimi.api.base+"debug/", methods=["GET"])
            def getFlowDebugSessions():
                apiEndpoint = "debug/"
                # NOTE - sessions can only persist on the same server so if the master changes debug will stop
                url = jimi.cluster.getMaster()
                response = jimi.helpers.apiCall("GET",apiEndpoint,token=jimi.api.g.sessionToken,overrideURL=url)
                return json.loads(response.text), response.status_code

            @jimi.api.webServer.route(jimi.api.base+"debug/", methods=["PUT"])
            def startFlowDebugSession():                
                apiEndpoint = "debug/"
                url = jimi.cluster.getMaster()                
                response = jimi.helpers.apiCall("PUT",apiEndpoint,token=jimi.api.g.sessionToken,overrideURL=url)
                return json.loads(response.text), response.status_code

            @jimi.api.webServer.route(jimi.api.base+"debug/<sessionID>/<conductID>/<flowID>/", methods=["POST"])
            def startDebuggerTrigger(sessionID,conductID,flowID):
                apiEndpoint = "debug/{0}/{1}/{2}/".format(sessionID,conductID,flowID)
                try:
                    data = json.loads(jimi.api.request.data)
                except:
                    data = {}
                url = jimi.cluster.getMaster()
                response = jimi.helpers.apiCall("POST",apiEndpoint,token=jimi.api.g.sessionToken,overrideURL=url,jsonData=data)
                return json.loads(response.text), response.status_code

            @jimi.api.webServer.route(jimi.api.base+"debug/<sessionID>/list/", methods=["GET"])
            def getFlowDebugSessionList(sessionID):
                apiEndpoint = "debug/{0}/list/".format(sessionID)
                url = jimi.cluster.getMaster()
                response = jimi.helpers.apiCall("GET",apiEndpoint,token=jimi.api.g.sessionToken,overrideURL=url)
                return json.loads(response.text), response.status_code

            @jimi.api.webServer.route(jimi.api.base+"debug/<sessionID>/<eventID>/executionList/", methods=["GET"])
            def getFlowDebugSessionFlowExecutionList(sessionID,eventID):
                apiEndpoint = "debug/{0}/{1}/executionList/".format(sessionID,eventID)
                url = jimi.cluster.getMaster()
                response = jimi.helpers.apiCall("GET",apiEndpoint,token=jimi.api.g.sessionToken,overrideURL=url)
                return json.loads(response.text), response.status_code

            @jimi.api.webServer.route(jimi.api.base+"debug/<sessionID>/<eventID>/<executionID>/", methods=["GET"])
            def getFlowDebugSessionFlowExecution(sessionID,eventID,executionID):
                apiEndpoint = "debug/{0}/{1}/{2}/".format(sessionID,eventID,executionID)
                url = jimi.cluster.getMaster()
                response = jimi.helpers.apiCall("GET",apiEndpoint,token=jimi.api.g.sessionToken,overrideURL=url)
                return json.loads(response.text), response.status_code

            @jimi.api.webServer.route(jimi.api.base+"debug/<sessionID>/<eventID>/<flowID>/flowID/", methods=["GET"])
            def getFlowDebugSessionFlowExecutionByFlowID(sessionID,eventID,flowID):
                apiEndpoint = "debug/{0}/{1}/{2}/flowID/".format(sessionID,eventID,flowID)
                url = jimi.cluster.getMaster()
                response = jimi.helpers.apiCall("GET",apiEndpoint,token=jimi.api.g.sessionToken,overrideURL=url)
                return json.loads(response.text), response.status_code

            @jimi.api.webServer.route(jimi.api.base+"debug/clear/", methods=["GET"])
            @jimi.auth.adminEndpoint
            def clearFlowDebugSessions():
                apiEndpoint = "debug/clear/"
                for url in jimi.cluster.getAll():
                    response = jimi.helpers.apiCall("GET",apiEndpoint,token=jimi.api.g.sessionToken,overrideURL=url)
                    if not response or response.status_code != 200:
                        return { "error" : "Error response from {0}".format(url) }, 503
                return { }, 200

            @jimi.api.webServer.route(jimi.api.base+"debug/clear/<sessionID>/", methods=["GET"])
            def clearFlowDebugSession(sessionID):
                apiEndpoint = "debug/clear/{0}/".format(sessionID)
                url = jimi.cluster.getMaster()
                response = jimi.helpers.apiCall("GET",apiEndpoint,token=jimi.api.g.sessionToken,overrideURL=url)
                return json.loads(response.text), response.status_code

            @jimi.api.webServer.route(jimi.api.base+"debug/<sessionID>/", methods=["DELETE"])
            def deleteFlowDebugSession(sessionID):
                apiEndpoint = "debug/{0}/".format(sessionID)
                url = jimi.cluster.getMaster()
                response = jimi.helpers.apiCall("DELETE",apiEndpoint,token=jimi.api.g.sessionToken,overrideURL=url)
                return json.loads(response.text), response.status_code

            @jimi.api.webServer.route(jimi.api.base+"debug/snapshot/<eventUID>/", methods=["PUT"])
            def createDebugSessionFromSnapshot(eventUID):
                apiEndpoint = "debug/snapshot/{0}/".format(eventUID)
                url = jimi.cluster.getMaster()
                response = jimi.helpers.apiCall("PUT",apiEndpoint,token=jimi.api.g.sessionToken,overrideURL=url)
                return json.loads(response.text), response.status_code

            @jimi.api.webServer.route(jimi.api.base+"debug/snapshot/<triggerID>/", methods=["GET"])
            def listDebugSessionSnapshots(triggerID):
                results = []
                snapshots = jimi.audit._audit().query(query={ "source" : "trigger", "type" : "snapshot_created", "data.trigger_id" : triggerID },limit=100,sort=[("_id",-1)])["results"]
                for snapshot in snapshots:
                    results.append({ "time" : snapshot["time"], "eventUID" : snapshot["data"]["sessionID"] })
                return { "results" : results }, 200