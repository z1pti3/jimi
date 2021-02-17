import time
import uuid
from functools import wraps

import jimi

class _flowDebug():
    flowList = {}

    def __init__(self):
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

    def startAction(self,eventID,data):
        uid = str(uuid.uuid4())
        self.flowList[eventID]["execution"][uid] = { "id" : uid, "type" : "action", "dataIn" : jimi.helpers.dictToJson(data), "startTime" : time.time(), "endTime" : 0, "dataOut" : None }
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

def newFlowDebugSession():
    global flowDebugSession
    try:
        if not flowDebugSession:
            flowDebugSession = {}
    except NameError:
        flowDebugSession = {}
    newSession = _flowDebug()
    flowDebugSession[newSession.id] = newSession
    return newSession.id
    
def deleteFlowDebugSession(sessionID):
    global flowDebugSession
    try:
        del flowDebugSession[sessionID]
        return True
    except KeyError:
        return False

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
            @jimi.auth.adminEndpoint
            def startFlowDebugSession():
                return { "sessionID" : newFlowDebugSession() }, 200

            @jimi.api.webServer.route(jimi.api.base+"debug/<sessionID>/", methods=["DELETE"])
            @jimi.auth.adminEndpoint
            def removeFlowDebugSession(sessionID):
                if deleteFlowDebugSession(sessionID):
                    return {}, 200
                return {}, 404
