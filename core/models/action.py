import time

import jimi

# Model Class
class _action(jimi.db._document):
    name = str()
    enabled = bool()
    log = bool()
    errorContinue = bool()
    comment = str()
    logicString = str()
    varDefinitions = dict()
    scope = int()
    systemCrashHandler = False

    _dbCollection = jimi.db.db["actions"]

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
        jimi.cache.globalCache.newCache("modelCache",sessionData=sessionData)
        # Loading json data into class
        for jsonItem in jsonList:
            _class = jimi.cache.globalCache.get("modelCache",jsonItem["classID"],getClassObject,sessionData=sessionData)
            if _class is not None:
                _class = _class[0].classObject()
                result.append(jimi.helpers.jsonToClass(_class(),jsonItem))
        return result

    def runHandler(self,data=None,debug=False):
        ####################################
        #              Header              #
        ####################################
        if self.log:
            startTime = 0
            startTime = time.time()
            jimi.audit._audit().add("action","action_start",{ "action_id" : self._id, "action_name" : self.name })
        ####################################

        if self.logicString:
            logicResult = jimi.logic.ifEval(self.logicString, { "data" : data["flowData"], "eventData" : data["eventData"], "persistentData" : data["persistentData"]})
            if logicResult:
                actionResult = self.doAction(data)
                if self.varDefinitions:
                    data["flowData"]["var"] = jimi.variable.varEval(self.varDefinitions,data["flowData"]["var"],{ "data" : data["flowData"], "eventData" : data["eventData"], "persistentData" : data["persistentData"], "action" : actionResult},0)
                    data["eventData"]["var"] = jimi.variable.varEval(self.varDefinitions,data["eventData"]["var"],{ "data" : data["flowData"], "eventData" : data["eventData"], "persistentData" : data["persistentData"], "action" : actionResult},1)
                    data["persistentData"]["var"] = jimi.variable.varEval(self.varDefinitions,data["persistentData"]["var"],{ "data" : data["flowData"], "eventData" : data["eventData"], "persistentData" : data["persistentData"], "action" : actionResult},2)
            else:
                actionResult = { "result" : False, "rc" : -100, "msg" : "Logic returned: False", "logic_string" : self.logicString }
        else:
            actionResult = self.doAction(data)
            if self.varDefinitions:
                data["flowData"]["var"] = jimi.variable.varEval(self.varDefinitions,data["flowData"]["var"],{ "data" : data["flowData"], "eventData" : data["eventData"], "persistentData" : data["persistentData"], "action" : actionResult},0)
                data["eventData"]["var"] = jimi.variable.varEval(self.varDefinitions,data["eventData"]["var"],{ "data" : data["flowData"], "eventData" : data["eventData"], "persistentData" : data["persistentData"], "action" : actionResult},1)
                data["persistentData"]["var"] = jimi.variable.varEval(self.varDefinitions,data["persistentData"]["var"],{ "data" : data["flowData"], "eventData" : data["eventData"], "persistentData" : data["persistentData"], "action" : actionResult},2)

        ####################################
        #              Footer              #
        ####################################
        if self.log:
            jimi.audit._audit().add("action","action_end",{ "action_id" : self._id, "action_name" : self.name, "action_result" : actionResult, "duration" : (time.time() - startTime) })
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

def getClassObject(classID,sessionData):
    return jimi.model._model().getAsClass(sessionData,id=classID)
