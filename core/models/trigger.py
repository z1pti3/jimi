import time
import copy

import jimi

# Model Class
class _trigger(jimi.db._document):
    name = str()
    schedule = str()
    lastCheck = float()
    nextCheck = int()
    startCheck = float()
    startTime = float() # Hidden runtime value that represents the actural startTime of notify 
    workerID = str()
    enabled = bool()
    log = bool()
    clusterSet = int()
    systemID = int()
    comment = str()
    maxDuration = 60
    logicString = str()
    varDefinitions = dict()
    concurrency = 0  
    threaded = False
    failOnActionFailure = False
    attemptCount = int()
    autoRestartCount = 3
    scope = int()

    _dbCollection = jimi.db.db["triggers"]

    def __init__(self):
        jimi.cache.globalCache.newCache("conductCache")

    # Override parent new to include name var, parent class new run after class var update
    def new(self,name="",acl=None):
        if acl:
            self.acl = acl
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
        jimi.cache.globalCache.newCache("modelCache",sessionData=sessionData)
        # Loading json data into class
        for jsonItem in jsonList:
            try:
                _class = jimi.cache.globalCache.get("modelCache",jsonItem["classID"],getClassObject,sessionData=sessionData)
                _class = _class[0].classObject()
                result.append(jimi.helpers.jsonToClass(_class(),jsonItem))
            except:
                pass
        return result

    def setAttribute(self,attr,value,sessionData=None):
        # Resets startCheck to 0 each time a trigger is enabled
        if attr == "enabled" and value == True and self.enabled == False:
            self.startCheck = 0
            self.attemptCount = 0
            self.update(["startCheck","attemptCount"])
        setattr(self,attr,value)
        return True

    def notify(self,events=[],data=None):
        notifyStartTime = time.time()
        self.startTime = notifyStartTime
        if self.log:
            jimi.audit._audit().add("trigger","notify_start",{ "trigger_id" : self._id, "trigger_name" : self.name })

        data = jimi.conduct.dataTemplate(data=data)
        data["persistentData"]["system"]["trigger"] = self
        data["flowData"]["trigger_id"] = self._id
        data["flowData"]["trigger_name"] = self.name
        tempData = data

        conducts = jimi.cache.globalCache.get("conductCache",self._id,getTriggerConducts)
        if conducts:
            cpuSaver = jimi.helpers.cpuSaver()
            for loadedConduct in conducts:
                maxDuration = 60
                if self.maxDuration > 0:
                    maxDuration = self.maxDuration
                eventHandler = None
                if self.concurrency > 0:
                    eventHandler = jimi.workers.workerHandler(self.concurrency)

                dataCopy = jimi.conduct.copyData(tempData,copyConductData=True)
                dataCopy["flowData"]["conduct_id"] = loadedConduct._id
                dataCopy["flowData"]["conduct_name"] = loadedConduct.name

                eventCount = len(events)
                for index, event in enumerate(events):
                    first = True if index == 0 else False
                    last = True if index == eventCount - 1 else False
                    eventStats = { "first" : first, "current" : index, "total" : eventCount, "last" : last }

                    data = jimi.conduct.copyData(dataCopy,copyEventData=True)
                    data["flowData"]["event"] = event
                    data["flowData"]["eventStats"] = eventStats

                    if self.log and (first or last):
                        jimi.audit._audit().add("trigger","notify_call",{ "trigger_id" : self._id, "trigger_name" : self.name, "conduct_id" : loadedConduct._id, "conduct_name" : loadedConduct.name, "flowData" : data["flowData"] })

                    if eventHandler:
                        while eventHandler.countIncomplete() >= self.concurrency:
                            cpuSaver.tick(ignoreEnabledState=True)
                        if eventHandler.failures:
                            jimi.audit._audit().add("trigger","conccurent_crash",{ "trigger_id" : self._id, "trigger_name" : self.name })
                            eventHandler.stop()
                            raise jimi.exceptions.concurrentCrash
                        
                        durationRemaining = ( self.startTime + maxDuration ) - time.time()
                        eventHandler.new("trigger:{0}".format(self._id),loadedConduct.triggerHandler,(self._id,data,False,False),maxDuration=durationRemaining)
                    else:
                        loadedConduct.triggerHandler(self._id,data,False,False)

                    # CPU saver
                    cpuSaver.tick()

                # Waiting for all jobs to complete
                if eventHandler:
                    eventHandler.waitAll()
                    if eventHandler.failures > 0:
                        jimi.audit._audit().add("trigger","conccurent_crash",{ "trigger_id" : self._id, "trigger_name" : self.name })
                        raise jimi.exceptions.triggerConcurrentCrash
                    eventHandler.stop()
        else:
            jimi.audit._audit().add("trigger","auto_disable",{ "trigger_id" : self._id, "trigger_name" : self.name })
            self.enabled = False
            self.update(["enabled"])
        
        if self.log:
            notifyEndTime = time.time()
            jimi.audit._audit().add("trigger","notify_end",{ "trigger_id" : self._id, "trigger_name" : self.name, "duration" : ( notifyEndTime - notifyStartTime ) })

        self.startCheck = 0
        self.attemptCount = 0
        self.lastCheck = time.time()
        self.nextCheck = jimi.scheduler.getSchedule(self.schedule)
        self.update(["startCheck","lastCheck","nextCheck","attemptCount"])

        # Return the final data value
        return data

    def checkHandler(self):
        startTime = 0
        if self.log:
            startTime = time.time()
        ####################################
        #              Header              #
        ####################################
        if self.log:
            jimi.audit._audit().add("trigger","check_start",{ "trigger_id" : self._id, "trigger_name" : self.name })
        ####################################

        self.data = { "flowData" : { "var" : {}, "plugin" : {} } }
        events = self.doCheck()
        data = None
        if self.data["flowData"]["var"] or self.data["flowData"]["plugin"]:
            data = self.data

        ####################################
        #              Footer              #
        ####################################
        if self.log:
            jimi.audit._audit().add("trigger","check_end",{ "trigger_id" : self._id, "trigger_name" : self.name, "duration" : ( time.time() - startTime ) })
        ####################################
        self.notify(events=self.result["events"],data=data)

    def doCheck(self):
        self.result = { "events" : [], "var" : {}, "plugin" : {} }
        self.check()
        self.data["flowData"]["var"] = self.result["var"]
        self.data["flowData"]["plugin"] = self.result["plugin"]
        return self.result["events"]

    # Main function called to determine if a trigger is triggered
    def check(self):
        self.result["events"].append({ "tick" : True })

    def whereUsed(self):
        conductsWhereUsed = jimi.conduct._conduct().query(query={ "flow.triggerID" : self._id },fields=["_id","name","flow"])["results"]
        usedIn = []
        for conductWhereUsed in conductsWhereUsed:
            for flow in conductWhereUsed["flow"]:
                try:
                    if flow["triggerID"] == self._id:
                        usedIn.append({ "conductID" :  conductWhereUsed["_id"], "conductName" : conductWhereUsed["name"] })
                except:
                    pass
        return usedIn


def getClassObject(classID,sessionData):
    return jimi.model._model().getAsClass(sessionData,id=classID)

def getTriggerConducts(triggerID,sessionData):
    return jimi.conduct._conduct().getAsClass(query={"flow.triggerID" : triggerID, "enabled" : True})


######### --------- API --------- #########
if jimi.api.webServer:
    if not jimi.api.webServer.got_first_request:
        if jimi.api.webServer.name == "jimi_web":
            @jimi.api.webServer.route(jimi.api.base+"trigger/<triggerID>/whereUsed/", methods=["GET"])
            def getTriggerWhereUsed(triggerID):
                try:
                    conducts = jimi.conduct._conduct().query(jimi.api.g.sessionData,query={ "flow.triggerID" : triggerID },fields=["_id"])["results"]
                    return { "results" : conducts }
                except:
                    return { "results" : [] }
