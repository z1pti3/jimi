from core.models import trigger
from core.models import webui

class _failedTriggers(trigger._trigger):
    enabled = True
    scope = 3

class _failedActions(trigger._trigger):
    enabled = True
    scope = 3

from core import model, audit, workers

def failedTrigger(workerName,workerID,failureType,msg=""):
    triggers = trigger._trigger().query(query={"name" : "failedTriggers"})["results"]
    if len(triggers) > 0:
        trigger_ = triggers[0]
        _class = model._model().getAsClass(id=trigger_["classID"])
        if len(_class) == 1:
            _class = _class[0].classObject()
        if _class:
            triggerClass = _class().getAsClass(id=trigger_["_id"])
            if len(triggerClass) == 1:
                triggerClass = triggerClass[0]
            if triggerClass:
                events = [{"type" : "systemEvent", "eventType" : failureType, "workerName" : workerName, "workerID" : workerID, "msg" : msg }]
                audit._audit().add("trigger","trigger_failure",events[0])
                workers.workers.new("trigger:{0}".format(trigger_["_id"]),triggerClass.notify,(events,))

def failedAction(actionID,actionName,failureType,msg=""):
    failedActionClass = trigger._trigger().query(query={"name" : "failedActions"})["results"]
    if len(failedActionClass) > 0:
        failedActionClass = failedActionClass[0]
        _class = model._model().getAsClass(id=failedActionClass["classID"])
        if len(_class) == 1:
            _class = _class[0].classObject()
        if _class:
            triggerClass = _class().getAsClass(id=failedActionClass["_id"])
            if len(triggerClass) == 1:
                triggerClass = triggerClass[0]
            if triggerClass:
                events = [{"type" : "systemEvent", "eventType" : failureType, "actionID" : actionID, "actionName" : actionName, "msg" : msg }]     
                audit._audit().add("action","action_failure",events[0])               
                workers.workers.new("trigger:{0}".format(failedActionClass["_id"]),triggerClass.notify,(events,))
                    