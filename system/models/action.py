from core.models import action
from core.models import trigger

import jimi

class _resetTrigger(action._action):
    enabled = True
    scope = 3

    def run(self,data,persistentData,actionResult):
        try:
            if "event" in data:
                if "triggerID" in data["event"]:
                    failedTrigger = trigger._trigger().getAsClass(id=data["event"]["triggerID"])
                    if len(failedTrigger) == 1:
                        failedTrigger = failedTrigger[0]
                        failedTrigger.startCheck = 0
                        failedTrigger.update(["startCheck"])
                        actionResult["result"] = True
                        actionResult["rc"] = 0
                        return actionResult
        except:
            pass
        actionResult["result"] = False
        actionResult["rc"] = 42
        return actionResult

class _getTrigger(action._action):
    triggerID = str()

    def run(self,data,persistentData,actionResult):
        triggerID = jimi.helpers.evalString(self.triggerID,{"data" : data})
        foundTrigger = trigger._trigger().getAsClass(id=triggerID)
        if len(foundTrigger) == 1:
            foundTrigger = foundTrigger[0]
            actionResult["result"] = True
            actionResult["rc"] = 0
            actionResult["trigger"] = jimi.helpers.classToJson(foundTrigger,hidden=True)
            return actionResult
        actionResult["result"] = False
        actionResult["rc"] = 404
        return actionResult

class _setTrigger(action._action):
    triggerID = str()
    field = str()
    value = str()

    def run(self,data,persistentData,actionResult):
        triggerID = jimi.helpers.evalString(self.triggerID,{"data" : data})
        field = jimi.helpers.evalString(self.field,{"data" : data})
        value = jimi.helpers.evalString(self.value,{"data" : data})
        foundTrigger = trigger._trigger().getAsClass(id=triggerID)
        if len(foundTrigger) == 1:
            foundTrigger = foundTrigger[0]
            foundTrigger.setAttribute(field,value)
            foundTrigger.update([field])
            actionResult["result"] = True
            actionResult["rc"] = 0
            return actionResult
        actionResult["result"] = False
        actionResult["rc"] = 404
        return actionResult

class _enableTrigger(action._action):
    triggerID = str()

    def run(self,data,persistentData,actionResult):
        triggerID = jimi.helpers.evalString(self.triggerID,{"data" : data})
        foundTrigger = trigger._trigger().getAsClass(id=triggerID)
        if len(foundTrigger) == 1:
            foundTrigger = foundTrigger[0]
            foundTrigger.enabled = True
            foundTrigger.update(["enabled"])
            actionResult["result"] = True
            actionResult["rc"] = 0
            return actionResult
        actionResult["result"] = False
        actionResult["rc"] = 404
        return actionResult

class _disableTrigger(action._action):
    triggerID = str()

    def run(self,data,persistentData,actionResult):
        triggerID = jimi.helpers.evalString(self.triggerID,{"data" : data})
        foundTrigger = trigger._trigger().getAsClass(id=triggerID)
        if len(foundTrigger) == 1:
            foundTrigger = foundTrigger[0]
            foundTrigger.enabled = False
            foundTrigger.update(["enabled"])
            actionResult["result"] = True
            actionResult["rc"] = 0
            return actionResult
        actionResult["result"] = False
        actionResult["rc"] = 404
        return actionResult

class _getAction(action._action):
    actionID = str()

    def run(self,data,persistentData,actionResult):
        actionID = jimi.helpers.evalString(self.actionID,{"data" : data})
        foundAction = action._action().getAsClass(id=actionID)
        if len(foundAction) == 1:
            foundAction = foundAction[0]
            actionResult["result"] = True
            actionResult["rc"] = 0
            actionResult["action"] = jimi.helpers.classToJson(foundAction,hidden=True)
            return actionResult
        actionResult["result"] = False
        actionResult["rc"] = 404
        return actionResult

class _setAction(action._action):
    actionID = str()
    field = str()
    value = str()

    def run(self,data,persistentData,actionResult):
        actionID = jimi.helpers.evalString(self.actionID,{"data" : data})
        field = jimi.helpers.evalString(self.field,{"data" : data})
        value = jimi.helpers.evalString(self.value,{"data" : data})
        foundAction = action._action().getAsClass(id=actionID)
        if len(foundAction) == 1:
            foundAction = foundAction[0]
            foundAction.setAttribute(field,value)
            foundAction.update([field])
            actionResult["result"] = True
            actionResult["rc"] = 0
            return actionResult
        actionResult["result"] = False
        actionResult["rc"] = 404
        return actionResult

class _enableAction(action._action):
    actionID = str()

    def run(self,data,persistentData,actionResult):
        actionID = jimi.helpers.evalString(self.actionID,{"data" : data})
        foundAction = action._action().getAsClass(id=actionID)
        if len(foundAction) == 1:
            foundAction = foundAction[0]
            foundAction.enabled = True
            foundAction.update(["enabled"])
            actionResult["result"] = True
            actionResult["rc"] = 0
            return actionResult
        actionResult["result"] = False
        actionResult["rc"] = 404
        return actionResult

class _disableAction(action._action):
    actionID = str()

    def run(self,data,persistentData,actionResult):
        actionID = jimi.helpers.evalString(self.actionID,{"data" : data})
        foundAction = action._action().getAsClass(id=actionID)
        if len(foundAction) == 1:
            foundAction = foundAction[0]
            foundAction.enabled = False
            foundAction.update(["enabled"])
            actionResult["result"] = True
            actionResult["rc"] = 0
            return actionResult
        actionResult["result"] = False
        actionResult["rc"] = 404
        return actionResult