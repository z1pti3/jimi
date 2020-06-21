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

    def runHandler(self,data,persistentData):
        startTime = time.time()
        actionResult = { "result" : False, "rc" : -1, "actionID" : self._id, "data" : {} }
        self.runHeader(data,persistentData,actionResult)
        if self.logicString.startswith("if"):
            if logic.ifEval(self.logicString, { "data" : data }):
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
        return actionResult

    def runHeader(self,data,persistentData,actionResult):
        if self.log:
            audit._audit().add("action","action start",{ "actionID" : self._id, "actionName" : self.name, "data" : data, "persistentData" : persistentData, "actionResult" : actionResult })
        logging.debug("Action run started, actionID='{0}', data='{1}'".format(self._id,data),7)

    def run(self,data,persistentData,actionResult):
        actionResult["result"] = True
        actionResult["rc"] = 0

    def runFooter(self,data,persistentData,actionResult,startTime):
        if self.log:
            audit._audit().add("action","action end",{ "actionID" : self._id, "actionName" : self.name, "data" : data, "persistentData" : persistentData, "actionResult" : actionResult, "duration" : (time.time() - startTime) })
        logging.debug("Action run complete, actionID='{0}', data='{1}'".format(self._id,data),7)

    def logicEval(self, logicString, data):
        def logicProcess(statement):
            try:
                if statement[2] == "==":
                    return (statement[0] == statement[1])
                elif statement[2] == "!=":
                    return (statement[0] != statement[1])
                elif statement[2] == ">":
                    return (statement[0] > statement[1])
                elif statement[2] == ">=":
                    return (statement[0] >= statement[1])
                elif statement[2] == "<":
                    return (statement[0] < statement[1])
                elif statement[2] == "<=":
                    return (statement[0] <= statement[1])
                elif statement[2] == "in":
                    return (statement[0] in statement[1])
                elif statement[2] == "not in":
                    return (statement[0] not in statement[1])
                elif statement[2].startswith("match"):
                    statement[1] = statement[2].split("\"")[1]
                    if re.search(statement[1],statement[0]):
                        return True
                    else:
                        return False
                elif statement[2].startswith("not match"):
                    statement[1] = statement[2].split("\"")[1]
                    if re.search(statement[1],statement[0]):
                        return False
                    else:
                        return True
            except:
                logging.debug("Action logicEval process failed, statement='{0}'".format(statement),5)
                return False

        logging.debug("Action logicEval started, actionID='{0}', logicString='{1}'".format(self._id,logicString),9)

        if "if" == logicString[:2]:
            tempLogic = logicString[2:]
            logicMatches = regexIf.finditer(tempLogic)
            for index, logicMatch in enumerate(logicMatches, start=1):
                statement = [logicMatch.group(1).strip(),logicMatch.group(14).strip(),logicMatch.group(13).strip()]
                # Cast typing statement vars
                for x in range(0,2):
                    statement[x] = helpers.typeCast(statement[x],{"data" : data})

                tempLogic = tempLogic.replace(logicMatch.group(0),str(logicProcess(statement)))

            # Checking that result only includes True, False, ( ), or, and,
            if regexLogic.search(tempLogic):
                result = eval(tempLogic) # Can be an unsafe call be very careful with this!
                logging.debug("Action logicEval completed, result='{0}'".format(result),10)
                return result
            else:
                logging.debug("Action logicEval tempLogic contains unsafe items, tempLogic='{0}'".format(tempLogic),3)

        logging.debug("Action logicEval completed, result='{0}'".format(False),10)
        return False


from core import helpers, logging, model, audit
from system.functions import network
from system import logic, variable

def getClassObject(classID,sessionData):
    return model._model().getAsClass(sessionData,id=classID)
