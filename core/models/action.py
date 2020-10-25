import time
import re

from core import db, function, cache

regexIf = re.compile("((\"(.*?[^\\])\"|([a-zA-Z0-9]+(\[(.*?)\])+)|([a-zA-Z0-9]+(\((.*?)(\)\)|\)))+)|\[(.*?)\]|([a-zA-Z0-9]*)))\s?( not match | match | not in | in |==|!=|>=|>|<=|<)\s?((\"(.*?[^\\])\"|([a-zA-Z0-9]+(\[(.*?)\])+)|([a-zA-Z0-9]+(\((.*?)(\)\)|\)))+)|\[(.*?)\]|([a-zA-Z0-9]*)))")
regexLogic = re.compile("^(True|False|\(|\)| |or|and)*$")

# Model Class
class _action(db._document):
    name = str()
    enabled = bool()
    log = bool()
    errorContinue = bool()
    comment = str()
    logicString = str()
    varDefinitions = dict()

    _dbCollection = db.db["actions"]

    # Override parent new to include name var, parent class new run after class var update
    def new(self,name=""):
        self.enabled = True
        result = super(_action, self).new()
        if result:
            if name == "":
                self.name = self._id
            else:
                self.name = name
            self.update(["name"])
        return result

    # Override parent to support plugin dynamic classes
    def loadAsClass(self,jsonList,sessionData=None):
        result = []
        # Ininilize global cache
        cache.globalCache.newCache("modelCache",sessionData=sessionData)
        # Loading json data into class
        for jsonItem in jsonList:
            _class = cache.globalCache.get("modelCache",jsonItem["classID"],getClassObject,sessionData=sessionData)
            if _class is not None:
                if len(_class) == 1:
                    _class = _class[0].classObject()
                if _class:
                    result.append(helpers.jsonToClass(_class(),jsonItem))
                else:
                    logging.debug("Error unable to locate class: actionID={0} classID={1}".format(jsonItem["_id"],jsonItem["classID"]))
        return result

    def setAttribute(self,attr,value,sessionData=None):
        if attr == "name":
            results = self.query(query={"name" : value, "_id" : { "$ne" :  db.ObjectId(self._id) }})["results"]
            if len(results) != 0:
                return False
        setattr(self,attr,value)
        return True


    def runHandler(self,data,persistentData,debug=False):
        startTime = 0
        if self.log:
            startTime = time.time()
        if debug:
            debugText=""
        actionResult = { "result" : False, "rc" : -1, "actionID" : self._id, "data" : {} }
        self.runHeader(data,persistentData,actionResult)
        if self.logicString:
            if debug:
                debugText=""
                logicDebugText, logicResult = logic.ifEval(self.logicString, { "data" : data }, debug=True)
                debugText+="\n\t[action logic]\n\t\t{0}\n\t\t{1}\n\t\t({2})".format(self.logicString,logicResult,logicDebugText)
            else:
                logicResult = logic.ifEval(self.logicString, { "data" : data })
            if logicResult:
                self.run(data,persistentData,actionResult)
                if self.varDefinitions:
                    data["var"] = variable.varEval(self.varDefinitions,data["var"],{ "data" : data, "action" : actionResult})
            else:
                actionResult["result"] = False
                actionResult["rc"] = -100
        else:
            self.run(data,persistentData,actionResult)
            if self.varDefinitions:
                data["var"] = variable.varEval(self.varDefinitions,data["var"],{ "data" : data, "action" : actionResult})
        self.runFooter(data,persistentData,actionResult,startTime)
        if debug:
            return (debugText, actionResult)
        return actionResult

    def runHeader(self,data,persistentData,actionResult):
        if self.log:
            # Used helpers.dictValue as cant ensure new data is passed by all plugins such as forEach / Subflow - this should be removed once these are updated to include the required template
            audit._audit().add("action","action start",{ "conductID" : helpers.dictValue(data,"conductID"), "conductName" : helpers.dictValue(data,"conductName"), "triggerName" : helpers.dictValue(data,"triggerName"), "triggerID" : helpers.dictValue(data,"triggerID"), "actionID" : self._id, "actionName" : self.name, "var" : helpers.dictValue(data,"var"), "event" : helpers.dictValue(data,"event"), "actionResult" : actionResult })
        if logging.debugEnabled:
            logging.debug("Action run started, actionID='{0}', data='{1}'".format(self._id,data),7)

    def run(self,data,persistentData,actionResult):
        actionResult["result"] = True
        actionResult["rc"] = 0
        return actionResult

    def runFooter(self,data,persistentData,actionResult,startTime):
        if self.log:
            # Used helpers.dictValue as cant ensure new data is passed by all plugins such as forEach / Subflow - this should be removed once these are updated to include the required template
            audit._audit().add("action","action end",{ "conductID" : helpers.dictValue(data,"conductID"), "conductName" : helpers.dictValue(data,"conductName"), "triggerName" : helpers.dictValue(data,"triggerName"), "triggerID" : helpers.dictValue(data,"triggerID"), "actionID" : self._id, "actionName" : self.name, "var" : helpers.dictValue(data,"var"), "event" : helpers.dictValue(data,"event"), "actionResult" : actionResult, "duration" : (time.time() - startTime) })
        if logging.debugEnabled:
            logging.debug("Action run complete, actionID='{0}', data='{1}'".format(self._id,data),7)

    def postRun(self):
        pass

from core import helpers, logging, model, audit
from system.functions import network
from system import logic, variable

def getClassObject(classID,sessionData):
    return model._model().getAsClass(sessionData,id=classID)
