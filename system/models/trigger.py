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
    triggers = trigger._trigger(False).query(query={"name" : "failedTriggers"})["results"]
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
                # Force the cluster system to identify that a trigger has crashed or failed
                triggerClass.startCheck = triggerClass.startCheck - triggerClass.maxDuration
                triggerClass.update(["startCheck"])
                events = [{"type" : "systemEvent", "eventType" : failureType, "workerName" : workerName, "workerID" : workerID, "msg" : msg }]
                # Excludes threaded triggers as this will be triggered by the thread crashing on the system index not the thread itself
                if workers.workers != None:          
                    workers.workers.new("trigger:{0}".format(trigger_["_id"]),triggerClass.notify,(events,))

def failedAction(actionID,actionName,failureType,msg=""):
    failedActionClass = trigger._trigger(False).query(query={"name" : "failedActions"})["results"]
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
                if workers.workers != None:          
                    workers.workers.new("trigger:{0}".format(failedActionClass["_id"]),triggerClass.notify,(events,))
                else:
                    triggerClass.notify(events)

