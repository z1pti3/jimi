from core.models import trigger
from core.models import webui

class _failedTriggers(trigger._trigger):
    enabled = True
    scope = 3

class _failedActions(trigger._trigger):
    enabled = True
    scope = 3

from core import model, audit, workers

def failedTrigger(workerID,failureType,msg="",triggerID=None,triggerName=None):
    triggers = trigger._trigger().query(query={"name" : "failedTriggers"})["results"]
    if len(triggers) > 0:
        trigger_ = triggers[0]
        if workerID != None:
            _class = model._model().getAsClass(id=trigger_["classID"])
            if len(_class) == 1:
                _class = _class[0].classObject()
            if _class:
                triggerClass = _class().getAsClass(id=trigger_["_id"])
                if len(triggerClass) == 1:
                    triggerClass = triggerClass[0]
                if triggerClass:
                    events = [{"type" : "systemEvent", "eventType" : failureType, "workerID" : workerID, "msg" : msg }]                    
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
                workers.workers.new("trigger:{0}".format(failedActionClass["_id"]),triggerClass.notify,(events,))
                    