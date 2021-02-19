import time
import uuid
import json
from functools import wraps

import jimi

class _flowDebug():

    def __init__(self,acl):
        self.flowList = {}
        self.acl = acl
        self.id = str(uuid.uuid4())

    def getEvent(self,eventID):
        return self.flowList[eventID]

    def startEvent(self,event):
        uid = str(uuid.uuid4())
        self.flowList[uid] = { "id" : uid, "type" : "event", "event" : event, "startTime" : time.time(), "endTime" : 0, "execution" : {} }
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

    def startAction(self,eventID,flowID,data):
        uid = str(uuid.uuid4())
        self.flowList[eventID]["execution"][uid] = { "id" : uid, "type" : "action", "flowID" : flowID, "dataIn" : jimi.helpers.dictToJson(data), "startTime" : time.time(), "endTime" : 0, "dataOut" : None }
        return uid

    def endAction(self,eventID,actionID,data):
        self.flowList[eventID]["execution"][actionID]["dataOut"] = jimi.helpers.dictToJson(data)
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

######### --------- API --------- #########
if jimi.api.webServer:
    if not jimi.api.webServer.got_first_request:
        if jimi.api.webServer.name == "jimi_core":
            @jimi.api.webServer.route(jimi.api.base+"debug/", methods=["PUT"])
            def startFlowDebugSession():
                sessionID = newFlowDebugSession( { "ids" : [ { "accessID" : jimi.api.g.sessionData["primaryGroup"], "read" : True, "write" : True, "delete" : True } ] })
                c = jimi.conduct._conduct().getAsClass(id="602040dcfdf684f65480ecf4")[0]
                data = jimi.conduct.dataTemplate()
                eventStat = { "first" : 0, "current" : 0, "total" : 0, "last" : 0 }
                data["flowData"]["event"] = 1
                data["flowData"]["eventStats"] = eventStat
                jimi.workers.workers.new("test",c.triggerHandler,("58d35e89-4ad3-4e43-a66c-012ef7cd294e",data,False,True,{"sessionID" : sessionID}))
                return { "sessionID" : sessionID }, 200

            @jimi.api.webServer.route(jimi.api.base+"debug/<sessionID>/", methods=["GET"])
            def getFlowDebugSession(sessionID):
                if jimi.db.ACLAccess(jimi.api.g.sessionData, flowDebugSession[sessionID].acl):
                    return flowDebugSession[sessionID].flowList, 200
                return {}, 404

            @jimi.api.webServer.route(jimi.api.base+"debug/<sessionID>/list/", methods=["GET"])
            def getFlowDebugSessionList(sessionID):
                if jimi.db.ACLAccess(jimi.api.g.sessionData, flowDebugSession[sessionID].acl):
                    return {"flowList" : list(flowDebugSession[sessionID].flowList.keys()) }, 200
                return {}, 404

            @jimi.api.webServer.route(jimi.api.base+"debug/<sessionID>/<eventID>/", methods=["GET"])
            def getFlowDebugSessionFlow(sessionID,eventID):
                if jimi.db.ACLAccess(jimi.api.g.sessionData, flowDebugSession[sessionID].acl):
                    return flowDebugSession[sessionID].flowList[eventID], 200
                return {}, 404

            @jimi.api.webServer.route(jimi.api.base+"debug/<sessionID>/<eventID>/executionList/", methods=["GET"])
            def getFlowDebugSessionFlowExecutionList(sessionID,eventID):
                if jimi.db.ACLAccess(jimi.api.g.sessionData, flowDebugSession[sessionID].acl):
                    return {"executionList" : list(flowDebugSession[sessionID].flowList[eventID]["execution"].keys())}, 200
                return {}, 404

            @jimi.api.webServer.route(jimi.api.base+"debug/<sessionID>/<eventID>/<executionID>/", methods=["GET"])
            def getFlowDebugSessionFlowExecution(sessionID,eventID,executionID):
                if jimi.db.ACLAccess(jimi.api.g.sessionData, flowDebugSession[sessionID].acl):
                    return flowDebugSession[sessionID].flowList[eventID]["execution"][executionID], 200
                return {}, 404

            @jimi.api.webServer.route(jimi.api.base+"debug/<sessionID>/<eventID>/<flowID>/flowID/", methods=["GET"])
            def getFlowDebugSessionFlowExecutionByFlowID(sessionID,eventID,flowID):
                if jimi.db.ACLAccess(jimi.api.g.sessionData, flowDebugSession[sessionID].acl):
                    keys = list(flowDebugSession[sessionID].flowList[eventID]["execution"].keys())
                    if len(keys) > 1:
                        keys.reverse()
                    for executionID in keys:
                        if flowDebugSession[sessionID].flowList[eventID]["execution"][executionID]["flowID"] == flowID:
                            return flowDebugSession[sessionID].flowList[eventID]["execution"][executionID], 200
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