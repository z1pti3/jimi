import traceback

import jimi

class concurrentCrash(Exception):
    def __init__(self,objectID,objectName,exceptions):
        self.objectID = objectID
        self.objectName = objectName
        self.exceptions = exceptions
        jimi.audit._audit().add("trigger","conccurent_crash",{ "object_id" : self.objectID, "object_name" : self.objectName, "exceptions" : self.exceptions })
        
    def __str__(self):
        return "Error: Concurrent crash. object_name='{0}', object_id='{1}' exceptions='{2}'".format(self.objectName,self.objectID,self.exceptions)

class triggerConcurrentCrash(Exception):
    def __init__(self,triggerID,triggerName,exceptions):
        self.triggerID = triggerID
        self.triggerName = triggerName
        self.exceptions = exceptions
        jimi.audit._audit().add("trigger","conccurent_crash",{ "trigger_id" : self.triggerID, "trigger_name" : self.triggerName, "exceptions" : self.exceptions })
        
    def __str__(self):
        return "Error: Trigger concurrent crash. trigger_name='{0}', trigger_id='{1}', exceptions='{2}'".format(self.triggerName,self.triggerID,self.exceptions)

class workerKilled(Exception):
    def __init__(self,workerID,workerName):
        self.workerName = workerName
        self.workerID = workerID
        jimi.logging.debug("Error: Worker killed. workerName='{0}', workerID='{1}'".format(self.workerName,self.workerID),-1)
        jimi.audit._audit().add("trigger","trigger_failure",{"type" : "systemEvent", "eventType" : "WorkerKilled", "workerName" : workerName, "workerID" : workerID, "msg" : "Worker killed by the system" })
        jimi.systemTrigger.failedTrigger(self.workerName,self.workerID,"WorkerKilled","Worker killed by system")
        
    def __str__(self):
        return "Error: Worker killed. worker_name='{0}', worker_id='{1}'".format(self.workerName,self.workerID)

class workerCrash(Exception):
    def __init__(self,workerID,workerName,trace):
        self.workerName = workerName
        self.workerID = workerID
        self.trace = trace
        jimi.logging.debug("Error: Worker crash. workerName='{0}', workerID='{1}', trace='{2}'".format(self.workerName,self.workerID,self.trace),-1)
        jimi.audit._audit().add("trigger","trigger_failure",{"type" : "systemEvent", "eventType" : "WorkerCrash", "workerName" : workerName, "workerID" : workerID, "msg" : self.trace })
        jimi.systemTrigger.failedTrigger(self.workerName,self.workerID,"WorkerCrash",self.trace)

    def __str__(self):
        return "Error: Worker killed. worker_name='{0}', worker_id='{1}', trace='{2}'".format(self.workerName,self.workerID,self.trace)

class triggerCrash(Exception):
    def __init__(self,triggerID,triggerName,trace):
        self.triggerName = triggerName
        self.triggerID = triggerID
        jimi.logging.debug("Error: Trigger Crashed. triggerName='{0}', triggerID='{1}', trace='{2}'".format(self.triggerName,self.triggerID,trace),-1)
        jimi.audit._audit().add("trigger","trigger_failure",{"type" : "systemEvent", "eventType" : "triggerCrash", "triggerName" : self.triggerName, "triggerID" : self.triggerID, "msg" : trace })
        jimi.systemTrigger.failedTrigger(self.triggerName,self.triggerID,"triggerCrash",trace)

    def __str__(self):
        return "Error: Trigger Crashed. triggerName='{0}', triggerID='{1}', trace='{2}'".format(self.triggerName,self.triggerID,self.trace)


class actionCrash(Exception):
    def __init__(self,actionID,actionName,exception):
        self.actionName = actionName
        self.actionID = actionID
        self.trace = ''.join(traceback.format_exception(type(exception), exception, exception.__traceback__))
        jimi.logging.debug("Error: Action Crashed. actionName='{0}', actionID='{1}', trace='{2}'".format(self.actionName,self.actionID,self.trace),-1)
        jimi.audit._audit().add("action","action_failure",{"type" : "systemEvent", "eventType" : "actionCrashed", "actionID" : actionID, "actionName" : actionName, "msg" : self.trace })
        jimi.systemTrigger.failedAction(self.actionName,self.actionID,"actionCrashed",self.trace)

    def __str__(self):
        return "Error: Worker Crashed. worker_name='{0}', worker_id='{1}', trace='{2}'".format(self.actionName,self.actionID,self.trace)

class linkCrash(Exception):
    def __init__(self,flowID,exception):
        self.flowID = flowID
        self.trace = ''.join(traceback.format_exception(type(exception), exception, exception.__traceback__))
        jimi.logging.debug("Error: Link Crashed. flow_id='{0}', trace='{2}'".format(self.flowID,self.trace),-1)

    def __str__(self):
        return "Error: Link Crashed. flowID='{0}', trace='{1}'".format(self.flowID,self.trace)

class functionCallFailure(Exception):
    def __init__(self,functionName,trace):
        self.functionName = functionName
        self.trace = trace
        
    def __str__(self):
        return "Error: Exception during function call. funcation='{0}', trace='{1}'".format(self.functionName,self.trace)

class variableDefineFailure(Exception):
    def __init__(self,varDict,exception):
        self.varDict = varDict
        self.trace = ''.join(traceback.format_exception(type(exception), exception, exception.__traceback__))
        
    def __str__(self):
        return "Error: Exception setting variable. var_dict='{0}', trace='{1}'".format(self.varDict,self.trace)

class endWorker(Exception):
    def __init__(self,data={}):
        self.data = data
        
    def __str__(self):
        return "Worker end exception raised"

class endFlow(Exception):
    def __init__(self,data={}):
        self.data = data
        
    def __str__(self):
        return "Flow end exception raised"