import time
import copy
import traceback
from core.exceptions import endFlow

import jimi

# Model Class
class _conduct(jimi.db._document):
    name = str()
    flow = list()
    enabled = True
    log = bool()
    comment = str()
    statics = dict()

    _dbCollection = jimi.db.db["conducts"]

    def __init__(self,restrictClass=True):
        # Cached lookups to limit reloading the same actions
        jimi.cache.globalCache.newCache("actionCache")
        jimi.cache.globalCache.newCache("triggerCache")
        jimi.cache.globalCache.newCache("triggeredFlowTriggers")
        jimi.cache.globalCache.newCache("triggeredFlowActions")
        jimi.cache.globalCache.newCache("triggeredFlowFlows")
        jimi.cache.globalCache.newCache("flowDict")
        return super(_conduct, self).__init__(restrictClass)

    # Override parent new to include name var, parent class new run after class var update
    def new(self,name=""):
        # Confirming that the given name is not already in use
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

    def triggerBatchHandler(self,triggerID,dataBatch,actionIDType=False,flowIDType=False,flowDebugSession=None):
        for data in dataBatch:
            self.triggerHandler(triggerID,data,actionIDType,flowIDType,flowDebugSession)

    # actionIDType=True uses actionID instead of triggerID
    def triggerHandler(self,triggerID,data,actionIDType=False,flowIDType=False,flowDebugSession=None):
        ####################################
        #              Header              #
        ####################################
        if self.log:
            startTime = 0
            startTime = time.time()
            jimi.audit._audit().add("conduct","trigger_start",{ "conduct_id" : self._id, "conduct_name" : self.name, "trigger_id" : triggerID })
        ####################################

        data["persistentData"]["system"]["conduct"] = self

        # Feature preload and cache so that we dont have to loop here?
        if self.statics:
            data["flowData"]["var"]["statics"] = {}
            for staticName, staticValue in self.statics.items():
                data["flowData"]["var"]["statics"][staticName] = staticValue

        flowDict = jimi.cache.globalCache.get("flowDict",self._id,getFlowDict,self.flow)
        
        uid = "{0}{1}".format(self._id,triggerID)
        if actionIDType:
            triggeredFlows = jimi.cache.globalCache.get("triggeredFlowActions",uid,getTriggeredFlowActions,self.flow,triggerID)
        elif flowIDType:
            triggeredFlows = jimi.cache.globalCache.get("triggeredFlowFlows",uid,getTriggeredFlowFlows,self.flow,triggerID)
        else:
            triggeredFlows = jimi.cache.globalCache.get("triggeredFlowTriggers",uid,getTriggeredFlowTriggers,self.flow,triggerID)

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
        try:
            if type(logicVar) is bool:
                try:
                    if logicVar == data["flowData"]["action"]["result"]:
                        return True
                except:
                    pass
            elif type(logicVar) is int:
                try:
                    if logicVar == data["flowData"]["action"]["rc"]:
                        return True
                except:
                    pass
            elif type(logicVar) is str:
                if logicVar.startswith("if"):
                    if jimi.logic.ifEval(logicVar, { "data" : data["flowData"], "eventData" : data["eventData"], "conductData" : data["conductData"], "persistentData" : data["persistentData"]}):
                        return True
                elif logicVar == "*":
                    return True
        except Exception as e:
            jimi.logging.debug("Error: Flow Logic Crashed. flowID={0}, error={1}".format(data["flowData"]["flow_id"],''.join(traceback.format_exception(type(e), e, e.__traceback__))),-1)
            try:
                if data["persistentData"]["system"]["trigger"].failOnActionFailure:
                    raise jimi.exceptions.linkCrash(data["flowData"]["flow_id"],e)
            except AttributeError:
                pass
            
        return False
    
    # Eval link tagging
    def flowLogicTag(self,nextFlow,currentFlowTag):
        if currentFlowTag != "" and nextFlow["tag"] != "":
            currentFlowTags = currentFlowTag.split(",")
            nextFlowTags = nextFlow["tag"].split(",")
            for currentFlowTag in currentFlowTags:
                if currentFlowTag in nextFlowTags:
                    return True
        else:
            return True
        return False

    def flowHandler(self,currentFlow,flowDict,data,flowDebugSession=None):
        if flowDebugSession or "flowDebugSession" in data["persistentData"]["system"]:
            if "flowDebugSession" in data["persistentData"]["system"]:
                flowDebugSession = copy.deepcopy(data["persistentData"]["system"]["flowDebugSession"])
            else:
                data["persistentData"]["system"]["flowDebugSession"] = flowDebugSession
            flowDebugSession["eventID"] = jimi.debug.flowDebugSession[flowDebugSession["sessionID"]].startEvent(data["flowData"]["trigger_name"],data["flowData"]["event"],data)
        processQueue = []
        currentFlowTag = ""
        data["flowData"]["conduct_id"] = self._id
        data["flowData"]["action"] = { "result" : True, "rc" : 1337 }
        flowObjectsUsed = []
        exitType = None
        codifyFlow = True if "classObject" in currentFlow else False
        cpuSaver = jimi.helpers.cpuSaver()
        try:
            while True:
                if currentFlow:
                    flowObjectsUsed.append(currentFlow["flowID"])
                    if currentFlow["type"] == "trigger":
                        if not codifyFlow:
                            currentTrigger = jimi.cache.globalCache.get("triggerCache",currentFlow["triggerID"]+currentFlow["flowID"],getTrigger,currentFlow)[0]
                        else:
                            currentTrigger = currentFlow["classObject"]
                        # Logic and var defintion
                        triggerContinue = True
                        if currentTrigger.logicString:
                            if jimi.logic.ifEval(currentTrigger.logicString,{ "data" : data["flowData"], "eventData" : data["eventData"], "conductData" : data["conductData"], "persistentData" : data["persistentData"]}):
                                if currentTrigger.varDefinitions:
                                    data["flowData"]["var"] = jimi.variable.varEval(currentTrigger.varDefinitions,data["flowData"]["var"],{ "data" : data["flowData"], "eventData" : data["eventData"], "conductData" : data["conductData"], "persistentData" : data["persistentData"]},0)
                                    data["eventData"]["var"] = jimi.variable.varEval(currentTrigger.varDefinitions,data["eventData"]["var"],{ "data" : data["flowData"], "eventData" : data["eventData"], "conductData" : data["conductData"], "persistentData" : data["persistentData"]},1)
                                    data["conductData"]["var"] = jimi.variable.varEval(currentTrigger.varDefinitions,data["conductData"]["var"],{ "data" : data["flowData"], "eventData" : data["eventData"], "conductData" : data["conductData"], "persistentData" : data["persistentData"]},2)
                                    data["persistentData"]["var"] = jimi.variable.varEval(currentTrigger.varDefinitions,data["persistentData"]["var"],{ "data" : data["flowData"], "eventData" : data["eventData"], "conductData" : data["conductData"], "persistentData" : data["persistentData"]},3)
                            else:
                                triggerContinue = False
                        else:
                            if currentTrigger.varDefinitions:
                                data["flowData"]["var"] = jimi.variable.varEval(currentTrigger.varDefinitions,data["flowData"]["var"],{ "data" : data["flowData"], "eventData" : data["eventData"], "conductData" : data["conductData"], "persistentData" : data["persistentData"]},0)
                                data["eventData"]["var"] = jimi.variable.varEval(currentTrigger.varDefinitions,data["eventData"]["var"],{ "data" : data["flowData"], "eventData" : data["eventData"], "conductData" : data["conductData"], "persistentData" : data["persistentData"]},1)
                                data["conductData"]["var"] = jimi.variable.varEval(currentTrigger.varDefinitions,data["conductData"]["var"],{ "data" : data["flowData"], "eventData" : data["eventData"], "conductData" : data["conductData"], "persistentData" : data["persistentData"]},2)
                                data["persistentData"]["var"] = jimi.variable.varEval(currentTrigger.varDefinitions,data["persistentData"]["var"],{ "data" : data["flowData"], "eventData" : data["eventData"], "conductData" : data["conductData"], "persistentData" : data["persistentData"]},3)
                        # If logic has said yes or no logic defined then move onto actions
                        if triggerContinue == True:
                            passData = data
                            for nextFlow in currentFlow["next"]:
                                if passData == None:
                                    passData = copyData(data)
                                if self.flowLogicEval(data,nextFlow["logic"]):
                                    if self.flowLogicTag(nextFlow,currentFlowTag):
                                        processQueue.append({ "flowID" : nextFlow["flowID"], "tag" : nextFlow["tag"], "data" : passData })
                                passData = None
                    elif currentFlow["type"] == "action":
                        if not codifyFlow:
                            class_ = jimi.cache.globalCache.get("actionCache",currentFlow["actionID"]+currentFlow["flowID"],getAction,currentFlow)[0]
                        else:
                            class_ = currentFlow["classObject"]
                        if class_.enabled:
                            data["flowData"]["flow_id"] = currentFlow["flowID"]
                            debug = False
                            if flowDebugSession:
                                debug = True
                                flowDebugSession["actionID"] = jimi.debug.flowDebugSession[flowDebugSession["sessionID"]].startAction(flowDebugSession["eventID"],data["flowData"]["flow_id"],class_.name,copyData(data,copyEventData=True,copyConductData=True,copyPersistentData=True))
                            try:
                                data["flowData"]["action"] = class_.runHandler(data=data,debug=debug)
                            except jimi.exceptions.endFlow:
                                raise jimi.exceptions.endFlow
                            except jimi.exceptions.endWorker as e:
                                raise jimi.exceptions.endWorker(e.data)
                            except Exception as e:
                                jimi.logging.debug("Error: Action Crashed. actionID={0}, actionName={1}, error={2}".format(class_._id,class_.name,''.join(traceback.format_exception(type(e), e, e.__traceback__))),-1)
                                if flowDebugSession:
                                    raise
                                if data["persistentData"]["system"]["trigger"].failOnActionFailure:
                                    # Force the trigger to be detected as failed due to startCheck + maxDuration time being less than now. jimi uses startCheck + maxDuration to understand the current status of a job.
                                    data["persistentData"]["system"]["trigger"].startCheck = 255
                                    data["persistentData"]["system"]["trigger"].update(["startCheck"])
                                    raise jimi.exceptions.actionCrash(class_._id,class_.name,e)
                                if class_.systemCrashHandler:
                                    jimi.exceptions.actionCrash(class_._id,class_.name,e)
                                data["flowData"]["action"] = { "result" : False, "rc" : -255, "error" : traceback.format_exception(type(e), e, e.__traceback__) }
                            data["flowData"]["action"]["action_id"] = class_._id
                            data["flowData"]["action"]["action_name"] = class_.name
                            if flowDebugSession:
                                jimi.debug.flowDebugSession[flowDebugSession["sessionID"]].endAction(flowDebugSession["eventID"],flowDebugSession["actionID"],copyData(data,copyEventData=True,copyConductData=True,copyPersistentData=True))
                            passData = data
                            for nextFlow in currentFlow["next"]:
                                if passData == None:
                                    passData = copyData(data)
                                if self.flowLogicEval(data,nextFlow["logic"]):
                                    if self.flowLogicTag(nextFlow,currentFlowTag):
                                        processQueue.append({ "flowID" : nextFlow["flowID"], "tag" : nextFlow["tag"], "data" : passData })
                                passData = None
                if len(processQueue) == 0:
                    break
                else:
                    nextFlowID = processQueue[-1]["flowID"]
                    data = processQueue[-1]["data"]
                    currentFlowTag = processQueue[-1]["tag"]
                    processQueue.pop()
                    try:
                        currentFlow = flowDict[nextFlowID]
                    except KeyError:
                        currentFlow = None
                # CPU saver
                cpuSaver.tick()
        finally:
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
                try:
                    if data["persistentData"]["system"]["flowDebugSnapshot"]:
                        jimi.audit._audit().add("trigger","snapshot",{ "trigger_id" : self._id, "trigger_name" : self.name, "event_id" : flowDebugSession["eventID"] })
                        bulkClass = jimi.db._bulk()
                        eventData = copy.deepcopy(jimi.helpers.dictToJson(jimi.debug.flowDebugSession[flowDebugSession["sessionID"]].flowList[flowDebugSession["eventID"]]))
                        eventData["executionIDs"] = list(eventData["execution"].keys())
                        del eventData["execution"]
                        jimi.debug._flowDebugSnapshot().bulkNew(bulkClass,self.acl,flowDebugSession["sessionID"],flowDebugSession["eventID"],eventData)
                        for key,value in jimi.debug.flowDebugSession[flowDebugSession["sessionID"]].flowList[flowDebugSession["eventID"]]["execution"].items():
                            jimi.debug._flowDebugSnapshot().bulkNew(bulkClass,self.acl,flowDebugSession["eventID"],key,value)
                        bulkClass.bulkOperatonProcessing()
                except KeyError:
                    pass


def dataTemplate(data=None,keepEvent=False):
    if data != None and type(data) is dict:
        try:
            if "event" in data["flowData"] and keepEvent != True:
                del data["flowData"]["event"]
            if "var" not in data["flowData"]:
                data["flowData"]["var"] = {}
            if "plugin" not in data["flowData"]:
                data["flowData"]["plugin"] = {}
        except KeyError:
            data["flowData"] = { "var" : {}, "plugin" : {} }
        if "eventData" not in data:
            data["eventData"] = { "var" : {}, "plugin" : {} }
        else:
            if "var" not in data["eventData"]:
                data["eventData"]["var"] = {}
            if "plugin" not in data["eventData"]:
                data["eventData"]["plugin"] = {}
        if "conductData" not in data:
            data["conductData"] = { "var" : {}, "plugin" : {} }
        else:
            if "var" not in data["conductData"]:
                data["conductData"]["var"] = {}
            if "plugin" not in data["conductData"]:
                data["conductData"]["plugin"] = {}
        if "persistentData" not in data:
            data["persistentData"] = { "system" : { "trigger" : None, "conduct" : None }, "plugin" : { }, "var" : {} }
        else:
            if "system" not in data["persistentData"]:
                data["persistentData"] = { "system" : { "trigger" : None, "conduct" : None } }
            if "plugin" not in data["persistentData"]:
                data["persistentData"]["plugin"] = {}
            if "var" not in data["persistentData"]:
                data["persistentData"]["var"] = {}
    else:
        data = { "flowData" : { "var" : {}, "plugin" : {} }, "eventData" : { "var" : {}, "plugin" : {} }, "conductData" : { "var" : {}, "plugin" : {} }, "persistentData" : { "system" : { "trigger" : None, "conduct" : None }, "var" : {}, "plugin" : {} } }
    return data

def copyData(data,copyEventData=False,copyConductData=False,copyPersistentData=False):
    copyOfData = {}
    dataTypes = ["flowData"]
    if copyPersistentData:
        dataTypes.append("persistentData")
    else:
        copyOfData["persistentData"] = data["persistentData"]
    if copyConductData:
        dataTypes.append("conductData")
    else:
        copyOfData["conductData"] = data["conductData"]
    if copyEventData:
        dataTypes.append("eventData")
    else:
        copyOfData["eventData"] = data["eventData"]
    for dataType in dataTypes:
        copyOfData[dataType] = data[dataType].copy()
        if not copyOfData[dataType]["var"]:
            copyOfData[dataType]["var"] = {}
        else:
            copyOfData[dataType]["var"] = copy.deepcopy(data[dataType]["var"])

        if not copyOfData[dataType]["plugin"]:
            copyOfData[dataType]["plugin"] = {}
        else:
            copyOfData[dataType]["plugin"] = copy.deepcopy(data[dataType]["plugin"])

    return copyOfData

def getTriggerUsedModels(triggerID):
    failedTriggerConducts = jimi.conduct._conduct().getAsClass(query={"flow.triggerID" : triggerID, "enabled" : True})
    models = []
    for failedTriggerConduct in failedTriggerConducts:
        conductFlowData = {}
        for flowItem in failedTriggerConduct.flow:
            conductFlowData[flowItem["flowID"]] = flowItem
        triggeredFlows = [ x for x in failedTriggerConduct.flow if "triggerID" in x and x["triggerID"] == triggerID and x["type"] == "trigger" ]
        for triggeredFlow in triggeredFlows:
            currentFlow = triggeredFlow
            processQueue = []
            loopProtection = []
            while True:
                if currentFlow:
                    if currentFlow["flowID"] not in loopProtection:
                        loopProtection.append(currentFlow["flowID"])
                        if currentFlow["type"] == "trigger":
                            if currentFlow["triggerID"] not in models:
                                t = jimi.trigger._trigger().getAsClass(id=currentFlow["triggerID"])[0]
                                models.append(t.classID)
                        elif currentFlow["type"] == "action":
                            if currentFlow["actionID"] not in models:
                                a = jimi.action._action().getAsClass(id=currentFlow["actionID"])[0]
                                models.append(a.classID)
                        for nextFlow in currentFlow["next"]:
                            processQueue.append({ "flowID" : nextFlow["flowID"] })
                if len(processQueue) == 0:
                    break
                else:
                    nextFlowID = processQueue[-1]["flowID"]
                    processQueue.pop()
                    try:
                        currentFlow = conductFlowData[nextFlowID]
                    except KeyError:
                        currentFlow = None
    return models

def getAction(match,sessionData,currentflow):
    return jimi.action._action(False).getAsClass(id=currentflow["actionID"])

def getTrigger(match,sessionData,currentflow):
    return jimi.trigger._trigger(False).getAsClass(id=currentflow["triggerID"])

def getTriggeredFlowTriggers(uid,sessionData,flowData,triggerID):
    return [ x for x in flowData if "triggerID" in x and x["triggerID"] == triggerID and x["type"] == "trigger" ]

def getTriggeredFlowActions(uid,sessionData,flowData,actionID):
    return [ x for x in flowData if "actionID" in x and x["actionID"] == actionID and x["type"] == "action" ]

def getTriggeredFlowFlows(uid,sessionData,flowData,flowID):
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

# API
if jimi.api.webServer:
    if not jimi.api.webServer.got_first_request:
        if jimi.api.webServer.name == "jimi_web":
            from flask import Flask, request, render_template

            @jimi.api.webServer.route("/conducts/", methods=["GET"])
            def conductsPage():
                conducts = jimi.conduct._conduct().query(sessionData=jimi.api.g.sessionData,query={})["results"]
                return render_template("conducts.html",CSRF=jimi.api.g.sessionData["CSRF"],conducts=conducts)
