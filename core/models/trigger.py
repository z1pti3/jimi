import time

from core import db

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
    comment = str()
    maxDuration = int()
    logicString = str()
    varDefinitions = dict()
    concurrency = int()  

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
                    logging.debug("Error unable to locate class, disabling trigger: triggerID={0} classID={1}, models={2}".format(jsonItem["_id"],jsonItem["classID"],[_trigger,db._document]))
                    _trigger().api_update(query={ "_id" : db.ObjectId(jsonItem["_id"]) },update={ "$set" : { "enabled" : False } } )
                    systemTrigger.failedTrigger(None,"noTriggerClass")
        return result

    def setAttribute(self,attr,value):
        if attr == "name":
            results = self.query(query={"name" : value, "_id" : { "$ne" :  db.ObjectId(self._id) }})["results"]
            if len(results) != 0:
                return False
        # Resets startCheck to 0 each time a trigger is enabled
        elif attr == "enabled" and value == True and self.enabled == False:
            self.startCheck = 0
            self.update(["startCheck"])
        setattr(self,attr,value)
        return True

    def notify(self,events=[],var=None,callingTriggerID=None):
        if events:
            notifyStartTime = time.time()
            if self.log:
                audit._audit().add("trigger","notify start",{ "triggerID" : self._id, "name" : self.name })

            for loadedConduct in cache.globalCache.get("conductCache",self._id,getTriggerConducts):
                maxDuration = 60
                if type(self.maxDuration) is int and self.maxDuration > 0:
                    maxDuration = self.maxDuration
                eventHandler = None
                if self.concurrency > 0:
                    eventHandler = workers.workerHandler(self.concurrency)

                loops = 0
                for event in events:
                    if var == None:
                        data = { "event" : event, "triggerID" : self._id, "var" : {}, "plugin" : {} }
                    else: 
                        data = { "event" : event, "triggerID" : self._id, "var" : var, "plugin" : {} }
                    if callingTriggerID != None:
                        if callingTriggerID != "":
                            data["callingTriggerID"] = callingTriggerID
                    if self.log:
                        audit._audit().add("trigger","notify call",{ "triggerID" : self._id, "conductID" : loadedConduct._id, "name" : self.name })
                    if eventHandler:
                        eventHandler.new("trigger:{0}".format(self._id),loadedConduct.triggerHandler,(self._id,data),maxDuration=maxDuration)
                    else:
                        loadedConduct.triggerHandler(self._id,data)

                    # CPU saver
                    loops+=1
                    if cpuSaver:
                        if loops > cpuSaver["loopL"]:
                            loops = 0
                            time.sleep(cpuSaver["loopT"])

                # Waiting for all jobs to complete
                if eventHandler:
                    eventHandler.waitAll()
                    eventHandler.stop()

            notifyEndTime = time.time()
            if self.log:
                audit._audit().add("trigger","notify end",{ "triggerID" : self._id, "name" : self.name, "duration" : (notifyEndTime-notifyStartTime) })

        self.startCheck = 0
        self.lastCheck = time.time()
        self.nextCheck = scheduler.getSchedule(self.schedule)
        self.update(["startCheck","lastCheck","nextCheck"])

    def checkHandler(self):
        startTime = time.time()
        self.checkHeader()
        self.check()
        self.checkFooter(startTime)
        self.notify(self.result["events"])

    def checkHeader(self):
        if self.log:
            audit._audit().add("trigger","check start",{ "triggerID" : self._id, "name" : self.name })
        logging.debug("Trigger check started, triggerID='{0}'".format(self._id),7)
        self.result = { "events" : [], "triggerID" : self._id, "var" : {}, "data" : {} }

    # Main function called to determine if a trigger is triggered
    def check(self):
        self.result["events"].append({ "tick" : True })

    def checkFooter(self,startTime):
        self.lastCheck = time.time()
        self.update(["lastCheck"])
        if self.log:
            audit._audit().add("trigger","check end",{ "triggerID" : self._id, "name" : self.name, "duration" : (self.lastCheck-startTime) })
        logging.debug("Trigger check complete, triggerID='{0}'".format(self._id),7)

from core import helpers, logging, model, audit, workers, scheduler, cache, settings
from core.models import conduct
from system.models import trigger as systemTrigger

cpuSaver = settings.config["cpuSaver"]

def getClassObject(classID,sessionData):
    return model._model().getAsClass(sessionData,id=classID)

def getTriggerConducts(triggerID,sessionData):
    return conduct._conduct().getAsClass(query={"flow.triggerID" : triggerID, "enabled" : True})