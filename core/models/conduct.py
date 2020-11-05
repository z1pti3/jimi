import time
import copy

from core import db

# Model Class
class _conduct(db._document):
    name = str()
    flow = list()
    enabled = bool()
    log = bool()
    comment = str()

    _dbCollection = db.db["conducts"]

    def __init__(self):
        # Cached lookups to limit reloading the same actions
        cache.globalCache.newCache("actionCache")
        cache.globalCache.newCache("triggerCache")
        cache.globalCache.newCache("triggeredFlowTriggers")
        cache.globalCache.newCache("triggeredFlowActions")
        cache.globalCache.newCache("triggeredFlowFlows")
        cache.globalCache.newCache("flowDict")

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
            results = self.query(query={"name" : value, "_id" : { "$ne" : db.ObjectId(self._id) }})["results"]
            if len(results) != 0:
                return False
        setattr(self,attr,value)
        return True

    # actionIDType=True uses actionID instead of triggerID
    def triggerHandler(self,triggerID,data,actionIDType=False,flowIDType=False,persistentData=None):
        startTime = 0
        if self.log:
            startTime = time.time()
        self.triggerHeader(triggerID,data)
        self.trigger(triggerID,actionIDType,flowIDType,data,persistentData=persistentData)
        self.triggerFooter(triggerID,data,startTime)
    
    def triggerHeader(self,triggerID,data):
        if self.log:
            audit._audit().add("conduct","trigger start",{ "conductID" : self._id, "conductName" : self.name, "triggerID" : triggerID, "data" : data })
        data["conductID"] = self._id
        if logging.debugEnabled:
            logging.debug("Conduct triggered, conductID='{0}', triggerID='{1}' data='{2}'".format(self._id,triggerID,data),5)

    def trigger(self,triggerID,actionIDType,flowIDType,data,persistentData=None):
        flowDict = cache.globalCache.get("flowDict",self._id,getFlowDict,self.flow)

        if actionIDType:
            triggeredFlows = cache.globalCache.get("triggeredFlowActions",triggerID,getTriggeredFlowActions,self.flow)
        elif flowIDType:
            triggeredFlows = cache.globalCache.get("triggeredFlowFlows",triggerID,getTriggeredFlowFlows,self.flow)
        else:
            triggeredFlows = cache.globalCache.get("triggeredFlowTriggers",triggerID,getTriggeredFlowTriggers,self.flow)
 
        # Triggers all found flows
        for triggeredFlow in triggeredFlows:
            self.flowHandler(triggeredFlow,flowDict,data,persistentData)

    def triggerFooter(self,triggerID,data,startTime):
        if self.log:
            audit._audit().add("conduct","trigger end",{ "conductID" : self._id, "conductName" : self.name, "triggerID" : triggerID, "data" : data, "duration" : (time.time() - startTime) })
        if logging.debugEnabled:    
            logging.debug("Conduct triggered, conductID='{0}', triggerID='{1}' data='{2}'".format(self._id,triggerID,data),5)

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
                if logic.ifEval(logicVar, { "data" : data }):
                    return True
        return False

    def flowHandler(self,currentFlow,flowDict,data,persistentData=None):
        processQueue = []
        if not persistentData:
            persistentData = { "system" : { "conduct" : self } }
        data["conductID"] = self._id
        data["action"] = { "result" : True, "rc" : 1337 }
        flowObjectsUsed = []
        codifyFlow = True if "classObject" in currentFlow else False
        cpuSaver = helpers.cpuSaver()
        while True:
            if currentFlow:
                flowObjectsUsed.append(currentFlow["flowID"])
                if currentFlow["type"] == "trigger":
                    try:
                        if not codifyFlow:
                            currentTrigger = cache.globalCache.get("triggerCache",currentFlow["triggerID"]+currentFlow["flowID"],getTrigger,currentFlow)[0]
                        else:
                            currentTrigger = currentFlow["classObject"]
                        # Logic and var defintion
                        triggerContinue = True
                        if currentTrigger.logicString:
                            if logic.ifEval(currentTrigger.logicString,{ "data" : data}):
                                if currentTrigger.varDefinitions:
                                    data["var"] = variable.varEval(currentTrigger.varDefinitions,data["var"],{ "data" : data})
                            else:
                                triggerContinue = False
                        else:
                            if currentTrigger.varDefinitions:
                                data["var"] = variable.varEval(currentTrigger.varDefinitions,data["var"],{ "data" : data})
                        # If logic has said yes or no logic defined then move onto actions
                        if triggerContinue == True:
                            passData = data
                            for nextFlow in currentFlow["next"]:
                                if passData == None:
                                    passData = copyFlowData(data)
                                if self.flowLogicEval(data,nextFlow["logic"]):
                                    processQueue.append({ "flowID" : nextFlow["flowID"], "data" : passData })
                                passData = None
                    except IndexError:
                        pass
                elif currentFlow["type"] == "action":
                    try:
                        if not codifyFlow:
                            class_ = cache.globalCache.get("actionCache",currentFlow["actionID"]+currentFlow["flowID"],getAction,currentFlow)[0]
                        else:
                            class_ = currentFlow["classObject"]
                        if class_.enabled:
                            data["flowID"] = currentFlow["flowID"]
                            data["action"] = class_.runHandler(data,persistentData)
                            passData = data
                            for nextFlow in currentFlow["next"]:
                                if passData == None:
                                    passData = copyFlowData(data)
                                if self.flowLogicEval(data,nextFlow["logic"]):
                                    processQueue.append({ "flowID" : nextFlow["flowID"], "data" : passData })
                                passData = None
                    except IndexError:
                        pass
            if len(processQueue) == 0:
                break
            else:
                nextFlowID = processQueue[-1]["flowID"]
                data = processQueue[-1]["data"]
                data["flowID"] = processQueue[-1]["flowID"]
                processQueue.pop()
                try:
                    currentFlow = flowDict[nextFlowID]
                except KeyError:
                    currentFlow = None
            # CPU saver
            cpuSaver.tick()
        # Post processing for all event postRun actions
        if "eventStats" in data:
            if data["eventStats"]["last"]:
                for flow in flowDict:
                    if flowDict[flow]["type"] == "action" and flowDict[flow]["flowID"] in flowObjectsUsed:
                        if not codifyFlow:
                            class_ = cache.globalCache.get("actionCache",flowDict[flow]["actionID"]+flowDict[flow]["flowID"],getAction,flowDict[flow],dontCheck=True)
                        else:
                            class_ = [flowDict[flow]["classObject"]]
                        if class_:
                            if len(class_) > 0:
                                class_ = class_[0]
                                class_.postRun()

from core import helpers, logging, model, audit, settings, cache
from core.models import action, trigger
from system import variable, logic

def flowDataTemplate(conduct=None,trigger=None,var=None,plugin=None):
    data = {}
    if conduct:
        data["conductID"] = conduct._id
        data["conductName"] = conduct.name
    else:
        data["conductID"] = None
        data["conductName"] = None  
    if trigger:
        data["triggerID"] = trigger._id
        data["triggerName"] = trigger.name
    else:
        data["triggerID"] = None
        data["triggerName"] = None
    if var:
        data["var"] = var
    else:
        data["var"] = None
    if plugin:
        data["plugin"] = plugin
    else:
        data["plugin"] = None
    return data

def copyFlowData(data):
    copyOfData = data.copy()
    if copyOfData["var"]:
        copyOfData["var"] = copy.deepcopy(data["var"])
    else:
        copyOfData["var"] = {}
    if copyOfData["plugin"]:
        copyOfData["plugin"] = copy.deepcopy(data["plugin"])
    else:
        copyOfData["plugin"] = {}
    return copyOfData

def getAction(match,sessionData,currentflow):
    return action._action().getAsClass(id=currentflow["actionID"])

def getTrigger(match,sessionData,currentflow):
    return trigger._trigger().getAsClass(id=currentflow["triggerID"])

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