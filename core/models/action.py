from math import log
import time

import jimi

# Model Class
class _action(jimi.db._document):
    name = str()
    enabled = bool()
    log = bool()
    comment = str()
    logicString = str()
    varDefinitions = dict()
    scope = int()
    systemCrashHandler = False

    _dbCollection = jimi.db.db["actions"]

    # Override parent new to include name var, parent class new run after class var update
    def new(self,name="",acl=None):
        self.enabled = True
        if acl:
            self.acl = acl
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
        jimi.cache.globalCache.newCache("modelCache",sessionData=sessionData)
        # Loading json data into class
        for jsonItem in jsonList:
            try:
                _class = jimi.cache.globalCache.get("modelCache",jsonItem["classID"],getClassObject,sessionData=sessionData)
                _class = _class[0].classObject()
                result.append(jimi.helpers.jsonToClass(_class(),jsonItem))
            except:
                pass
        return result

    def runHandler(self,data=None,debug=False):
        ####################################
        #              Header              #
        ####################################
        if self.log:
            startTime = 0
            startTime = time.time()
            jimi.audit._audit().add("action","start",{ "action_id" : self._id, "action_name" : self.name })
        ####################################

        if self.logicString:
            logicResult = jimi.logic.ifEval(self.logicString, { "data" : data["flowData"], "eventData" : data["eventData"], "conductData" : data["conductData"], "persistentData" : data["persistentData"]}, debug=debug)
            if debug:
                evalLogic = logicResult[1]
                explainLogic = logicResult[2]
                logicResult = logicResult[0]
            if logicResult:
                actionResult = self.doAction(data)
                if debug:
                    actionResult["logic_eval"] = evalLogic
                    actionResult["logic_explain"] = explainLogic
                if self.varDefinitions:
                    data["flowData"]["var"] = jimi.variable.varEval(self.varDefinitions,data["flowData"]["var"],{ "data" : data["flowData"], "eventData" : data["eventData"], "conductData" : data["conductData"], "persistentData" : data["persistentData"], "action" : actionResult},0)
                    data["eventData"]["var"] = jimi.variable.varEval(self.varDefinitions,data["eventData"]["var"],{ "data" : data["flowData"], "eventData" : data["eventData"], "conductData" : data["conductData"], "persistentData" : data["persistentData"], "action" : actionResult},1)
                    data["conductData"]["var"] = jimi.variable.varEval(self.varDefinitions,data["conductData"]["var"],{ "data" : data["flowData"], "eventData" : data["eventData"], "conductData" : data["conductData"], "persistentData" : data["persistentData"], "action" : actionResult},2)
                    data["persistentData"]["var"] = jimi.variable.varEval(self.varDefinitions,data["persistentData"]["var"],{ "data" : data["flowData"], "eventData" : data["eventData"], "conductData" : data["conductData"], "persistentData" : data["persistentData"], "action" : actionResult},3)
            else:
                if debug:
                    actionResult = { "result" : False, "rc" : -100, "msg" : "Logic returned: False", "logic_string" : self.logicString, "logic_eval" : evalLogic, "logic_explain" : explainLogic }
                else:
                    actionResult = { "result" : False, "rc" : -100, "msg" : "Logic returned: False", "logic_string" : self.logicString }
        else:
            actionResult = self.doAction(data)
            if self.varDefinitions:
                data["flowData"]["var"] = jimi.variable.varEval(self.varDefinitions,data["flowData"]["var"],{ "data" : data["flowData"], "eventData" : data["eventData"], "conductData" : data["conductData"], "persistentData" : data["persistentData"], "action" : actionResult},0)
                data["eventData"]["var"] = jimi.variable.varEval(self.varDefinitions,data["eventData"]["var"],{ "data" : data["flowData"], "eventData" : data["eventData"], "conductData" : data["conductData"], "persistentData" : data["persistentData"], "action" : actionResult},1)
                data["conductData"]["var"] = jimi.variable.varEval(self.varDefinitions,data["conductData"]["var"],{ "data" : data["flowData"], "eventData" : data["eventData"], "conductData" : data["conductData"], "persistentData" : data["persistentData"], "action" : actionResult},2)
                data["persistentData"]["var"] = jimi.variable.varEval(self.varDefinitions,data["persistentData"]["var"],{ "data" : data["flowData"], "eventData" : data["eventData"], "conductData" : data["conductData"], "persistentData" : data["persistentData"], "action" : actionResult},3)

        ####################################
        #              Footer              #
        ####################################
        if self.log:
            jimi.audit._audit().add("action","end",{ "action_id" : self._id, "action_name" : self.name, "action_result" : actionResult, "duration" : (time.time() - startTime) })
        ####################################
        
        return actionResult

    def doAction(self,data):
        actionResult = self.run(data["flowData"],data["persistentData"], { "result" : False, "rc" : -1, "actionID" : self._id, "data" : {} })
        return actionResult

    def run(self,data,persistentData,actionResult):
        actionResult["result"] = True
        actionResult["rc"] = 0
        return actionResult

    def postRun(self):
        pass

    def __del__(self):
        self.postRun()

    def whereUsed(self):
        conductsWhereUsed = jimi.conduct._conduct().query(query={ "flow.actionID" : self._id },fields=["_id","name","flow"])["results"]
        usedIn = []
        for conductWhereUsed in conductsWhereUsed:
            for flow in conductWhereUsed["flow"]:
                try:
                    if flow["actionID"] == self._id:
                        usedIn.append({ "conductID" :  conductWhereUsed["_id"], "conductName" : conductWhereUsed["name"] })
                except:
                    pass
        return usedIn

def getClassObject(classID,sessionData):
    return jimi.model._model().getAsClass(id=classID)
