from core.models import trigger
from core.models import webui

class _failedTriggers(trigger._trigger):
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
                    triggerWorkers = trigger._trigger().getAsClass(query={"workerID" : workerID})
                    if len(triggerWorkers) > 0:
                        worker_ = triggerWorkers[0]
                        if worker_.attemptCount < worker_.autoRestartCount:
                            events = [{"type" : "systemEvent", "eventType" : failureType, "workerID" : workerID, "triggerID" : worker_._id, "triggerName" : worker_.name, "msg" : msg, "autoRecover" : True }]
                            audit._audit().add("Error",failureType,{"type" : "systemEvent", "eventType" : failureType, "workerID" : workerID, "triggerID" : worker_._id, "triggerName" : worker_.name, "msg" : msg, "autoRecover" : True })
                        else:
                            events = [{"type" : "systemEvent", "eventType" : failureType, "workerID" : workerID, "triggerID" : worker_._id, "triggerName" : worker_.name, "msg" : msg, "autoRecover" : False}]
                            audit._audit().add("Error",failureType,{"type" : "systemEvent", "eventType" : failureType, "workerID" : workerID, "triggerID" : worker_._id, "triggerName" : worker_.name, "msg" : msg, "autoRecover" : False })
                        # Notify conducts that have a trigger failure trigger within flow expect if its the failure trigger
                        if worker_.name != "failedTriggers":
                            workers.workers.new("trigger:{0}".format(trigger_["_id"]),triggerClass.notify,(events,))
                    # If no worker was found then log the crash but do not trigger the failed trigger flow
                    else:
                        events = [{"type" : "systemEvent", "eventType" : failureType, "workerID" : workerID, "triggerID" : triggerID, "triggerName" : triggerName, "msg" : msg, "autoRecover" : False}]
                        audit._audit().add("Error",failureType,{"type" : "systemEvent", "eventType" : failureType, "workerID" : workerID, "triggerID" : triggerID, "triggerName" : triggerName, "msg" : msg, "autoRecover" : False })
        else:
            events = [{"type" : "systemEvent", "eventType" : failureType, "workerID" : workerID, "triggerID" : triggerID, "triggerName" : triggerName, "msg" : msg, "autoRecover" : False}]
            audit._audit().add("Error",failureType,{"type" : "systemEvent", "eventType" : failureType, "workerID" : workerID, "triggerID" : triggerID, "triggerName" : triggerName, "msg" : msg, "autoRecover" : False })
