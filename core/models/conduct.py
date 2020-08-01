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
        results = self.query(query={"name" : self.name})["results"]
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
        startTime=time.time()
        self.triggerHeader(triggerID,data)
        self.trigger(triggerID,actionIDType,flowIDType,data,persistentData=persistentData)
        self.triggerFooter(triggerID,data,startTime)
    
    def triggerHeader(self,triggerID,data):
        if self.log:
            audit._audit().add("conduct","trigger start",{ "conductID" : self._id, "conductName" : self.name, "triggerID" : triggerID, "data" : data })
        data["conductID"] = self._id
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
        logging.debug("Conduct triggered, conductID='{0}', triggerID='{1}' data='{2}'".format(self._id,triggerID,data),5)

    # Eval logic between links 
    def flowLogicEval(self,data,logicVar):
        if type(logicVar) is bool:
            try:
                if "action" in data:
                    if logicVar == data["action"]["result"]:
                        return True
                #No action so must be a trigger, thus it's always true!
                else:
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
            persistentData = {}
        data["conductID"] = self._id
        cpuSaver = helpers.cpuSaver()
        while True:
            if currentFlow:
                if currentFlow["type"] == "trigger":
                    currentTrigger = cache.globalCache.get("triggerCache",currentFlow["triggerID"],getTrigger)
                    if currentTrigger:
                        if len(currentTrigger) > 0:
                            currentTrigger = currentTrigger[0]
                            # Logic and var defintion
                            triggerContinue = True
                            if currentTrigger.logicString.startswith("if"):
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
                                    if not passData:
                                        passData = copy.deepcopy(data)
                                    if type(nextFlow) is dict:
                                        if self.flowLogicEval(data,nextFlow["logic"]):
                                            processQueue.append({ "flowID" : nextFlow["flowID"], "data" : passData })
                                    elif type(nextFlow) is str:
                                        processQueue.append({ "flowID" : nextFlow, "data" : passData })
                                    passData = None
                elif currentFlow["type"] == "action":
                    class_ = cache.globalCache.get("actionCache",currentFlow["actionID"],getAction)
                    if class_:
                        if len(class_) > 0:
                            class_ = class_[0]
                            if class_.enabled:
                                data["flowID"] = currentFlow["flowID"]
                                data["action"] = class_.runHandler(data,persistentData)
                                passData = data
                                for nextFlow in currentFlow["next"]:
                                    if not passData:
                                        passData = copy.deepcopy(data)
                                    # dict ( new format ) or string ( legacy )
                                    if type(nextFlow) is dict:
                                        if self.flowLogicEval(data,nextFlow["logic"]):
                                            processQueue.append({ "flowID" : nextFlow["flowID"], "data" : passData })
                                    elif type(nextFlow) is str:
                                        if class_.errorContinue or data["action"]["result"]:
                                            processQueue.append({ "flowID" : nextFlow, "data" : passData })
                                    passData = None
            if len(processQueue) == 0:
                break
            else:
                nextFlowID = processQueue[-1]["flowID"]
                data = processQueue[-1]["data"]
                data["flowID"] = processQueue[-1]["flowID"]
                processQueue.pop()
                if nextFlowID in flowDict:
                    currentFlow = flowDict[nextFlowID]
                else:
                    currentFlow = None
            # CPU saver
            cpuSaver.tick()
        # Post processing for all event postRun actions
        if "eventStats" in data:
            if data["eventStats"]["last"]:
                for flow in flowDict:
                    if flowDict[flow]["type"] == "action":
                        class_ = cache.globalCache.get("actionCache",flowDict[flow]["actionID"],getAction)
                        if class_:
                            if len(class_) > 0:
                                class_ = class_[0]
                                class_.postRun()

from core import helpers, logging, model, audit, settings, cache
from core.models import action, trigger
from system import variable, logic


def getAction(actionID,sessionData):
    return action._action().getAsClass(id=actionID)

def getTrigger(triggerID,sessionData):
    return trigger._trigger().getAsClass(id=triggerID)

def getTriggeredFlowTriggers(triggerID,sessionData,flowData):
    return [ x for x in flowData if "triggerID" in x and x["triggerID"] == triggerID and x["type"] == "trigger" ]

def getTriggeredFlowActions(actionID,sessionData,flowData):
    return [ x for x in flowData if "actionID" in x and x["actionID"] == actionID and x["type"] == "action" ]

def getTriggeredFlowFlows(flowID,sessionData,flowData):
    return [ x for x in flowData if "flowID" in x and x["flowID"] == flowID and x["type"] == "action" ]

def getFlowDict(uid,sessionData,flowData):
    result = {}
    for flow in flowData:
        result[flow["flowID"]] = flow
    return result