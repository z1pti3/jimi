import time
import copy

import jimi

# Model Class
class _conduct(jimi.db._document):
    name = str()
    flow = list()
    enabled = True
    log = bool()
    comment = str()

    _dbCollection = jimi.db.db["conducts"]

    def __init__(self):
        # Cached lookups to limit reloading the same actions
        jimi.cache.globalCache.newCache("actionCache")
        jimi.cache.globalCache.newCache("triggerCache")
        jimi.cache.globalCache.newCache("triggeredFlowTriggers")
        jimi.cache.globalCache.newCache("triggeredFlowActions")
        jimi.cache.globalCache.newCache("triggeredFlowFlows")
        jimi.cache.globalCache.newCache("flowDict")

    # Override parent new to include name var, parent class new run after class var update
    def new(self,name=""):
        # Confirming that the given name is not alrady in use
        results = self.query(query={"name" : name})["results"]
        if len(results) == 0:
            # Run parent class function ( alternative to end decorator for the new function within a class )
            result = super(_conduct, self).new()
            if name == "":
                self.name = self._id
            else:
                self.name = name
            self.update(["name"])
            return result
        else:
            return None

    def setAttribute(self,attr,value,sessionData=None):
        if attr == "name":
            results = self.query(query={"name" : value, "_id" : { "$ne" : jimi.db.ObjectId(self._id) }})["results"]
            if len(results) != 0:
                return False
        setattr(self,attr,value)
        return True

    # actionIDType=True uses actionID instead of triggerID
    def triggerHandler(self,triggerID,data,actionIDType=False,flowIDType=False,flowDebugSession=None):
        ####################################
        #              Header              #
        ####################################
        startTime = 0
        if self.log:
            startTime = time.time()
            jimi.audit._audit().add("conduct","trigger_start",{ "conduct_id" : self._id, "conduct_name" : self.name, "trigger_id" : triggerID })
        data["persistentData"]["system"]["conduct"] = self
        ####################################

        flowDict = jimi.cache.globalCache.get("flowDict",self._id,getFlowDict,self.flow)

        if actionIDType:
            triggeredFlows = jimi.cache.globalCache.get("triggeredFlowActions",triggerID,getTriggeredFlowActions,self.flow)
        elif flowIDType:
            triggeredFlows = jimi.cache.globalCache.get("triggeredFlowFlows",triggerID,getTriggeredFlowFlows,self.flow)
        else:
            triggeredFlows = jimi.cache.globalCache.get("triggeredFlowTriggers",triggerID,getTriggeredFlowTriggers,self.flow)

        for triggeredFlow in triggeredFlows:
            self.flowHandler(triggeredFlow,flowDict,data,flowDebugSession=flowDebugSession)

        ####################################
        #              Footer              #
        ####################################
        if self.log:
            jimi.audit._audit().add("conduct","trigger_end",{ "conduct_id" : self._id, "conduct_name" : self.name, "trigger_id" : triggerID, "duration" : ( time.time() - startTime ) })
        ####################################

    # Eval logic between links 
    def flowLogicEval(self,data,logicVar):
        if type(logicVar) is bool:
            try:
                if logicVar == data["action"]["result"]:
                    return True
            except:
                pass
        elif type(logicVar) is int:
            try:
                if logicVar == data["action"]["rc"]:
                    return True
            except:
                pass
        elif type(logicVar) is str:
            if logicVar.startswith("if"):
                if jimi.logic.ifEval(logicVar, { "data" : data }):
                    return True
        return False

    def flowHandler(self,currentFlow,flowDict,data,flowDebugSession=None):
        if flowDebugSession:
            flowDebugSession["eventID"] = jimi.debug.flowDebugSession[flowDebugSession["sessionID"]].startEvent(data["flowData"]["event"])
        processQueue = []
        data["flowData"]["conductID"] = self._id
        data["flowData"]["action"] = { "result" : True, "rc" : 1337 }
        flowObjectsUsed = []
        codifyFlow = True if "classObject" in currentFlow else False
        cpuSaver = jimi.helpers.cpuSaver()
        while True:
            if currentFlow:
                flowObjectsUsed.append(currentFlow["flowID"])
                if currentFlow["type"] == "trigger":
                    try:
                        if not codifyFlow:
                            currentTrigger = jimi.cache.globalCache.get("triggerCache",currentFlow["triggerID"]+currentFlow["flowID"],getTrigger,currentFlow)[0]
                        else:
                            currentTrigger = currentFlow["classObject"]
                        # Logic and var defintion
                        triggerContinue = True
                        if currentTrigger.logicString:
                            if jimi.logic.ifEval(currentTrigger.logicString,{ "data" : data["flowData"]}):
                                if currentTrigger.varDefinitions:
                                    data["flowData"]["var"] = jimi.variable.varEval(currentTrigger.varDefinitions,data["flowData"]["var"],{ "data" : data["flowData"]})
                            else:
                                triggerContinue = False
                        else:
                            if currentTrigger.varDefinitions:
                                data["flowData"]["var"] = jimi.variable.varEval(currentTrigger.varDefinitions,data["flowData"]["var"],{ "data" : data["flowData"]})
                        # If logic has said yes or no logic defined then move onto actions
                        if triggerContinue == True:
                            passData = data
                            for nextFlow in currentFlow["next"]:
                                if passData == None:
                                    passData = copyData(data)
                                if self.flowLogicEval(data["flowData"],nextFlow["logic"]):
                                    processQueue.append({ "flowID" : nextFlow["flowID"], "data" : passData })
                                passData = None
                    except IndexError:
                        pass
                elif currentFlow["type"] == "action":
                    try:
                        if not codifyFlow:
                            class_ = jimi.cache.globalCache.get("actionCache",currentFlow["actionID"]+currentFlow["flowID"],getAction,currentFlow)[0]
                        else:
                            class_ = currentFlow["classObject"]
                        if class_.enabled:
                            data["flowData"]["flow_id"] = currentFlow["flowID"]
                            if flowDebugSession:
                                flowDebugSession["actionID"] = jimi.debug.flowDebugSession[flowDebugSession["sessionID"]].startAction(flowDebugSession["eventID"],data["flowData"]["flow_id"],data)
                            data["flowData"]["action"] = class_.runHandler(data=data)
                            data["flowData"]["action"]["action_id"] = class_._id
                            data["flowData"]["action"]["action_name"] = class_.name
                            if flowDebugSession:
                                jimi.debug.flowDebugSession[flowDebugSession["sessionID"]].endAction(flowDebugSession["eventID"],flowDebugSession["actionID"],data)
                            passData = data
                            for nextFlow in currentFlow["next"]:
                                if passData == None:
                                    passData = copyData(data)
                                if self.flowLogicEval(data["flowData"],nextFlow["logic"]):
                                    processQueue.append({ "flowID" : nextFlow["flowID"], "data" : passData })
                                passData = None
                    except IndexError:
                        pass
            if len(processQueue) == 0:
                break
            else:
                nextFlowID = processQueue[-1]["flowID"]
                data = processQueue[-1]["data"]
                processQueue.pop()
                try:
                    currentFlow = flowDict[nextFlowID]
                except KeyError:
                    currentFlow = None
            # CPU saver
            cpuSaver.tick()
        # Post processing for all event postRun actions
        if data["flowData"]["eventStats"]["last"]:
            for flow in flowDict:
                if flowDict[flow]["type"] == "action" and flowDict[flow]["flowID"] in flowObjectsUsed:
                    if not codifyFlow:
                        class_ = jimi.cache.globalCache.get("actionCache",flowDict[flow]["actionID"]+flowDict[flow]["flowID"],getAction,flowDict[flow],dontCheck=True)
                    else:
                        class_ = [flowDict[flow]["classObject"]]
                    if class_:
                        if len(class_) > 0:
                            class_ = class_[0]
                            class_.postRun()

        if flowDebugSession:
            jimi.debug.flowDebugSession[flowDebugSession["sessionID"]].endEvent(flowDebugSession["eventID"])

def dataTemplate(data=None):
    if data != None and type(data) is dict():
        try:
            if "event" in data["flowData"]:
                del data["flowData"]["event"]
            if "var" not in data["flowData"]:
                data["flowData"]["var"] = {}
            if "plugin" not in data["flowData"]:
                data["flowData"]["plugin"] = {}
        except KeyError:
            data["flowData"] = { "var" : {}, "plugin" : {} }
        if "persistentData" not in data:
            data["persistentData"] = { "system" : { "trigger" : None, "conduct" : None }, "plugin" : { } }
        else:
            if "system" not in data["persistentData"]:
                data["persistentData"] = { "system" : { "trigger" : None, "conduct" : None } }
            if "plugin" not in data["persistentData"]:
                data["persistentData"]["plugin"] = { }
    else:
        data = { "flowData" : { "var" : {}, "plugin" : {} }, "persistentData" : { "system" : { "trigger" : None, "conduct" : None }, "plugin" : { } } }
    return data

def copyData(data):
    copyOfData = {}
    copyOfData["persistentData"] = data["persistentData"]
    copyOfData["flowData"] = data["flowData"].copy()
    try:
        copyOfData["flowData"]["var"] = copy.deepcopy(data["flowData"]["var"])
    except KeyError:
        copyOfData["flowData"]["var"] = {}
    try:
        copyOfData["flowData"]["plugin"] = copy.deepcopy(data["flowData"]["plugin"])
    except KeyError:
        copyOfData["flowData"]["plugin"] = {}
    return copyOfData

def getAction(match,sessionData,currentflow):
    return jimi.action._action().getAsClass(id=currentflow["actionID"])

def getTrigger(match,sessionData,currentflow):
    return jimi.trigger._trigger().getAsClass(id=currentflow["triggerID"])

def getTriggeredFlowTriggers(triggerID,sessionData,flowData):
    return [ x for x in flowData if "triggerID" in x and x["triggerID"] == triggerID and x["type"] == "trigger" ]

def getTriggeredFlowActions(actionID,sessionData,flowData):
    return [ x for x in flowData if "actionID" in x and x["actionID"] == actionID and x["type"] == "action" ]

def getTriggeredFlowFlows(flowID,sessionData,flowData):
    # prevent cache when running as testTrigger
    try:
        classObject = flowData[0]["classObject"]
        return (False, [ x for x in flowData if "flowID" in x and x["flowID"] == flowID ])
    except:
        return [ x for x in flowData if "flowID" in x and x["flowID"] == flowID ]

def getFlowDict(uid,sessionData,flowData):
    result = {}
    for flow in flowData:
        result[flow["flowID"]] = flow
    # prevent cache when running as testTrigger
    try:
        classObject = flowData[0]["classObject"]
        return (False, result)
    except:
        return result