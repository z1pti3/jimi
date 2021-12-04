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
    clusterSet = int()
    systemID = int()
    systemIndex = int()
    comment = str()
    maxDuration = 60
    logicString = str()
    varDefinitions = dict()
    concurrency = 0  
    threaded = False
    failOnActionFailure = True
    attemptCount = int()
    autoRestartCount = 3
    autoRestartDelay = 0
    executionCount = int()
    scope = int()
    executionSnapshot = False
    partialResults = False

    _dbCollection = jimi.db.db["triggers"]

    def __init__(self,restrictClass=True):
        jimi.cache.globalCache.newCache("conductCache")
        return super(_trigger, self).__init__(restrictClass)

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

    # yeld capabiltiy trigger
    def checkAndNotify(self,data=None):
        notifyStartTime = time.time()
        self.startTime = notifyStartTime

        cpuSaver = jimi.helpers.cpuSaver()
        maxDuration = 60
        if self.maxDuration > 0:
            maxDuration = self.maxDuration

        data = jimi.conduct.dataTemplate(data=data)
        data["persistentData"]["system"]["trigger"] = self
        if self.executionSnapshot:
            if "flowDebugSession" not in data["persistentData"]["system"]:
                data["persistentData"]["system"]["flowDebugSession"] = { "sessionID" : jimi.debug.newFlowDebugSession(self.acl,self.name) }
                data["persistentData"]["system"]["flowDebugSnapshot"] = True
        data["flowData"]["trigger_id"] = self._id
        data["flowData"]["trigger_name"] = self.name

        conducts = jimi.cache.globalCache.get("conductCache",self._id,getTriggerConducts)
        try:
            if conducts:
                conductData = {}
                for loadedConduct in conducts:
                    conductData[loadedConduct._id] = jimi.conduct.copyData(data,copyConductData=True)

                eventIndex = 1
                for events in self.doCheck():
                    if type(events) is not list:
                        events = [events]
                    for loadedConduct in conducts: 
                        eventHandler = None
                        if self.concurrency > 0:
                            eventHandler = jimi.workers.workerHandler(self.concurrency)
                            concurrentEvents = []
                        for event in events:
                            conductData[loadedConduct._id]["flowData"]["conduct_id"] = loadedConduct._id
                            conductData[loadedConduct._id]["flowData"]["conduct_name"] = loadedConduct.name
                            first = True if eventIndex == 0 else False
                            last = True if eventIndex > 0 else False
                            eventStats = { "first" : first, "current" : eventIndex, "total" : eventIndex + 1, "last" : last }
                            data = jimi.conduct.copyData(conductData[loadedConduct._id],copyEventData=True)
                            data["flowData"]["event"] = event
                            data["flowData"]["eventStats"] = eventStats
                            if eventHandler:
                                concurrentEvents.append(data)
                            else:
                                try:
                                    loadedConduct.triggerHandler(self._id,data,False,False)
                                except jimi.exceptions.endFlow:
                                    pass
                        if eventHandler:
                            eventBatches = jimi.helpers.splitList(concurrentEvents,int(len(concurrentEvents)/self.concurrency))
                            for events in eventBatches:
                                durationRemaining = ( self.startTime + maxDuration ) - time.time()
                                eventHandler.new("trigger:{0}".format(self._id),loadedConduct.triggerBatchHandler,(self._id,events,False,False),maxDuration=durationRemaining)
                            eventHandler.waitAll()
                            if eventHandler.failures or eventHandler.failureCount() > 0:
                                raise jimi.exceptions.triggerConcurrentCrash(self._id,self.name,eventHandler.failures)
                            eventHandler.stop()
                    cpuSaver.tick()
                    eventIndex+=1
            else:
                jimi.audit._audit().add("trigger","auto_disable",{ "trigger_id" : self._id, "trigger_name" : self.name })
                self.enabled = False
                self.update(["enabled"])
        except jimi.exceptions.endWorker as e:
            self.startCheck = 0
            self.attemptCount = 0
            self.lastCheck = time.time()
            self.nextCheck = jimi.scheduler.getSchedule(self.schedule)
            self.update(["startCheck","lastCheck","nextCheck","attemptCount"])
            raise jimi.exceptions.endWorker(e.data)
        finally:
            try:
                if "flowDebugSnapshot" in data["persistentData"]["system"]:
                    if data["persistentData"]["system"]["flowDebugSnapshot"]:
                        if len(jimi.debug.flowDebugSession[data["persistentData"]["system"]["flowDebugSession"]["sessionID"]].flowList) > 0:
                            jimi.audit._audit().add("trigger","snapshot_created",{ "trigger_id" : self._id, "trigger_name" : self.name, "sessionID" : data["persistentData"]["system"]["flowDebugSession"]["sessionID"] })
                        jimi.debug.deleteFlowDebugSession(data["persistentData"]["system"]["flowDebugSession"]["sessionID"])
            except KeyError:
                pass
        self.startCheck = 0
        self.attemptCount = 0
        self.lastCheck = time.time()
        self.nextCheck = jimi.scheduler.getSchedule(self.schedule)
        self.update(["startCheck","lastCheck","nextCheck","attemptCount"])
        # Return the final data value
        return data

    def notify(self,events=[],data=None):
        notifyStartTime = time.time()
        self.startTime = notifyStartTime

        data = jimi.conduct.dataTemplate(data=data)
        data["persistentData"]["system"]["trigger"] = self
        if self.executionSnapshot and len(events) > 0:
            if "flowDebugSession" not in data["persistentData"]["system"]:
                data["persistentData"]["system"]["flowDebugSession"] = { "sessionID" : jimi.debug.newFlowDebugSession(self.acl,self.name) }
                data["persistentData"]["system"]["flowDebugSnapshot"] = True
        data["flowData"]["trigger_id"] = self._id
        data["flowData"]["trigger_name"] = self.name
        tempData = data

        conducts = jimi.cache.globalCache.get("conductCache",self._id,getTriggerConducts)
        maxDuration = 60
        if self.maxDuration > 0:
            maxDuration = self.maxDuration
        try:
            if conducts:
                cpuSaver = jimi.helpers.cpuSaver()
                for loadedConduct in conducts:
                    eventHandler = None
                    if self.concurrency > 0:
                        eventHandler = jimi.workers.workerHandler(self.concurrency)
                        concurrentEvents = []

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

                        if eventHandler:
                            concurrentEvents.append(data)
                        else:
                            try:
                                loadedConduct.triggerHandler(self._id,data,False,False)
                            except jimi.exceptions.endFlow:
                                pass

                        # CPU saver
                        cpuSaver.tick()

                    # Waiting for all jobs to complete
                    if eventHandler:
                        eventBatches = jimi.helpers.splitList(concurrentEvents,int(len(concurrentEvents)/self.concurrency))
                        for events in eventBatches:
                            durationRemaining = ( self.startTime + maxDuration ) - time.time()
                            eventHandler.new("trigger:{0}".format(self._id),loadedConduct.triggerBatchHandler,(self._id,events,False,False),maxDuration=durationRemaining)
                        eventHandler.waitAll()
                        if eventHandler.failures or eventHandler.failureCount() > 0:
                            raise jimi.exceptions.triggerConcurrentCrash(self._id,self.name,eventHandler.failures)
                        eventHandler.stop()
            else:
                jimi.audit._audit().add("trigger","auto_disable",{ "trigger_id" : self._id, "trigger_name" : self.name })
                self.enabled = False
                self.update(["enabled"])
        except jimi.exceptions.endWorker as e:
            self.startCheck = 0
            self.attemptCount = 0
            self.lastCheck = time.time()
            self.nextCheck = jimi.scheduler.getSchedule(self.schedule)
            self.update(["startCheck","lastCheck","nextCheck","attemptCount"])
            raise jimi.exceptions.endWorker(e.data)
        finally:
            try:
                if "flowDebugSnapshot" in data["persistentData"]["system"]:
                    if data["persistentData"]["system"]["flowDebugSnapshot"]:
                        if len(jimi.debug.flowDebugSession[data["persistentData"]["system"]["flowDebugSession"]["sessionID"]].flowList) > 0:
                            jimi.audit._audit().add("trigger","snapshot_created",{ "trigger_id" : self._id, "trigger_name" : self.name, "sessionID" : data["persistentData"]["system"]["flowDebugSession"]["sessionID"] })
                        jimi.debug.deleteFlowDebugSession(data["persistentData"]["system"]["flowDebugSession"]["sessionID"])
            except KeyError:
                pass
        self.startCheck = 0
        self.attemptCount = 0
        self.lastCheck = time.time()
        self.nextCheck = jimi.scheduler.getSchedule(self.schedule)
        self.update(["startCheck","lastCheck","nextCheck","attemptCount"])

        # Return the final data value
        return data

    def checkHandler(self,data=None):
        ####################################
        #              Header              #
        ####################################
        startTime = time.time()
        jimi.audit._audit().add("trigger","start",{ "trigger_id" : self._id, "trigger_name" : self.name })
        ####################################

        if not data:
            data = { "flowData" : { "var" : {}, "plugin" : {} } }
        elif "flowData" not in data:
            data["flowData"] = { "flowData" : { "var" : {}, "plugin" : {} } }
        self.data = data

        if self.partialResults:
            self.checkAndNotify(data=data)
        else:
            events = self.doCheck()
            if self.data["flowData"]["var"] or self.data["flowData"]["plugin"]:
                data["flowData"]["var"] = self.data["flowData"]["var"]
                data["flowData"]["plugin"] = self.data["flowData"]["plugin"]
            self.notify(events=events,data=data)
        ####################################
        #              Footer              #
        ####################################
        jimi.audit._audit().add("trigger","end",{ "trigger_id" : self._id, "trigger_name" : self.name, "duration" : ( time.time() - startTime ) })
        ####################################

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
        conductsWhereUsed = jimi.conduct._conduct(False).query(query={ "flow.triggerID" : self._id },fields=["_id","name","flow"])["results"]
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
    return jimi.model._model().getAsClass(id=classID)

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
