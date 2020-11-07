import time

from core import db

class triggerConcurrentCrash(Exception):
    """Trigger concurrent crash"""
    pass

# Model Class
class _trigger(db._document):
    name = str()
    schedule = str()
    lastCheck = float()
    nextCheck = int()
    startCheck = float()
    workerID = str()
    enabled = bool()
    log = bool()
    clusterSet = int()
    systemID = int()
    comment = str()
    maxDuration = int()
    logicString = str()
    varDefinitions = dict()
    concurrency = int()  
    threaded = bool()
    attemptCount = int()
    autoRestartCount = int()

    _dbCollection = db.db["triggers"]

    def __init__(self):
        cache.globalCache.newCache("conductCache")

    # Override parent new to include name var, parent class new run after class var update
    def new(self,name=""):
        result = super(_trigger, self).new()
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
                    if logging.debugEnabled:
                        logging.debug("Error unable to locate class, disabling trigger: triggerID={0} classID={1}, models={2}".format(jsonItem["_id"],jsonItem["classID"],[_trigger,db._document]))
                    _trigger().api_update(query={ "_id" : db.ObjectId(jsonItem["_id"]) },update={ "$set" : { "enabled" : False } } )
                    systemTrigger.failedTrigger(None,"noTriggerClass")
        return result

    def setAttribute(self,attr,value,sessionData=None):
        # Resets startCheck to 0 each time a trigger is enabled
        if attr == "enabled" and value == True and self.enabled == False:
            self.startCheck = 0
            self.update(["startCheck"])
        setattr(self,attr,value)
        return True

    def notify(self,events=[],var=None,plugin=None,callingTriggerID=None):
        if events:
            if self.log:
                notifyStartTime = time.time()
                audit._audit().add("trigger","notify start",{ "triggerID" : self._id, "name" : self.name })

            conducts = cache.globalCache.get("conductCache",self._id,getTriggerConducts)
            if conducts:
                cpuSaver = helpers.cpuSaver()
                for loadedConduct in conducts:
                    maxDuration = 60
                    if type(self.maxDuration) is int and self.maxDuration > 0:
                        maxDuration = self.maxDuration
                    eventHandler = None
                    if self.concurrency > 0:
                        eventHandler = workers.workerHandler(self.concurrency,cleanUp=False)

                    tempData = conduct.flowDataTemplate(conduct=loadedConduct,trigger=self,var=var,plugin=plugin)
                    if callingTriggerID:
                        tempData["callingTriggerID"] = callingTriggerID

                    for index, event in enumerate(events):
                        first = True if index == 0 else False
                        last = True if index == len(events) - 1 else False
                        eventStats = { "first" : first, "current" : index, "total" : len(events), "last" : last }

                        data = conduct.copyFlowData(tempData)
                        data["event"] = event
                        data["eventStats"] = eventStats
                        if self.log and (first or last):
                            audit._audit().add("trigger","notify call",{ "triggerID" : self._id, "conductID" : loadedConduct._id, "conductName" : loadedConduct.name, "name" : self.name, "data" : data })

                        if eventHandler:
                            eventHandler.new("trigger:{0}".format(self._id),loadedConduct.triggerHandler,(self._id,data),maxDuration=maxDuration)
                        else:
                            loadedConduct.triggerHandler(self._id,data)

                        # CPU saver
                        cpuSaver.tick()

                    # Waiting for all jobs to complete
                    if eventHandler:
                        eventHandler.waitAll()
                        if eventHandler.failureCount() > 0:
                            if logging.debugEnabled:
                                logging.debug("Trigger concurrent crash: triggerID={0}".format(self._id),5)
                            audit._audit().add("trigger","conccurent crash",{ "triggerID" : self._id, "name" : self.name })
                            raise triggerConcurrentCrash
                        eventHandler.stop()
            else:
                if logging.debugEnabled:
                    logging.debug("Error trigger has no conducts, automaticly disabling: triggerID={0}".format(self._id))
                audit._audit().add("trigger","autho disable",{ "triggerID" : self._id, "name" : self.name })
                self.enabled = False
                self.update(["enabled"])
            
            
            if self.log:
                notifyEndTime = time.time()
                audit._audit().add("trigger","notify end",{ "triggerID" : self._id, "name" : self.name, "duration" : (notifyEndTime-notifyStartTime) })

        self.startCheck = 0
        self.attemptCount = 0
        self.lastCheck = time.time()
        self.nextCheck = scheduler.getSchedule(self.schedule)
        self.update(["startCheck","lastCheck","nextCheck","attemptCount"])

    def checkHandler(self):
        startTime = 0
        if self.log:
            startTime = time.time()
        self.checkHeader()
        self.check()
        self.checkFooter(startTime)
        self.notify(events=self.result["events"],var=self.result["var"],plugin=self.result["plugin"])

    def checkHeader(self):
        if self.log:
            audit._audit().add("trigger","check start",{ "triggerID" : self._id, "name" : self.name })
        if logging.debugEnabled:
            logging.debug("Trigger check started, triggerID='{0}'".format(self._id),7)
        self.result = { "events" : [], "var" : {}, "plugin" : {} }

    # Main function called to determine if a trigger is triggered
    def check(self):
        self.result["events"].append({ "tick" : True })

    def checkFooter(self,startTime):
        if self.log:
            audit._audit().add("trigger","check end",{ "triggerID" : self._id, "name" : self.name, "duration" : (time.time()-startTime) })
        if logging.debugEnabled:
            logging.debug("Trigger check complete, triggerID='{0}'".format(self._id),7)

from core import helpers, logging, model, audit, workers, scheduler, cache, settings, helpers
from core.models import conduct
from system.models import trigger as systemTrigger

def getClassObject(classID,sessionData):
    return model._model().getAsClass(sessionData,id=classID)

def getTriggerConducts(triggerID,sessionData):
    return conduct._conduct().getAsClass(query={"flow.triggerID" : triggerID, "enabled" : True})