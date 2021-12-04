from math import trunc
import sys
import uuid
import time
import json
import os
from pathlib import Path

import jimi

systemIndexes = []

class _clusterMember(jimi.db._document):
    systemID = int()
    systemUID = str()
    bindAddress = str()
    bindPort = int()
    bindSecure = bool()
    master = bool()
    syncCount = int()
    lastSyncTime = int()
    checksum = str()
    supportedModels = list()

    _dbCollection = jimi.db.db["clusterMembers"]

    def new(self,systemID):
        self.systemID = systemID
        self.master = False
        self.acl = { "ids":[ { "accessID":"0","delete": True,"read": True,"write": True } ] } 
        return super(_clusterMember, self).new()

    def sync(self):
        global systemIndexes
        now = time.time()
        self.syncCount+=1
        self.lastSyncTime = int(now)
        self.update(["syncCount","lastSyncTime"])
        clusterMembers =  _clusterMember().getAsClass()
        masters=[]
        active=[]
        lowestMaster = [None,65535]
        deadMaster = False
        for clusterMember in clusterMembers:
            if clusterMember.systemID == self.systemID:
                if clusterMember.systemUID != self.systemUID:
                    jimi.logging.debug("Error: Duplicated systemID detected during sync.",-1)
                    return False
                if clusterMember.master:
                    self.master = True
                else:
                    self.master = False

            if clusterMember.master:
                masters.append(clusterMember)
            if clusterMember.lastSyncTime > now - clusterSettings["deadTimer"]:
                active.append(clusterMember.systemID)
                if lowestMaster[1] > clusterMember.systemID:
                    lowestMaster[0] = clusterMember
                    lowestMaster[1] = clusterMember.systemID

            if ((clusterMember.master) and (clusterMember.lastSyncTime < now - clusterSettings["deadTimer"])):
                clusterMember.master = False
                clusterMember.update(["master"])
                deadMaster = True

        if len(masters) == 0:
            lowestMaster[0].master = True
            lowestMaster[0].update(["master"])
        elif len(masters) > 1:
            for master in masters:
                master.master = False
                master.update(["master"])
            lowestMaster[0].master = True
            lowestMaster[0].update(["master"])

        if ((not self.master) and (deadMaster)):
            lowestMaster[0].master = True
            lowestMaster[0].update(["master"])

        # Check which system indexes are online
        onlineIndexes = {}
        for systemIndex in systemIndexes:
            # Disabled index dead check
            #if systemIndex["manager"]["lastHandle"] < ( now - clusterSettings["deadTimer"] ):
            onlineIndexes[str(systemIndex["systemIndex"])] = 0
        # Get and check all triggers assigned to this system
        allocatedTriggers = jimi.trigger._trigger(False).getAsClass(query={ "systemID" : self.systemID, "enabled" : True })
        # Building cluster set groups so we can ensure certain triggers are kept together
        groups = {}
        for allocatedTrigger in allocatedTriggers:
            if str(allocatedTrigger.systemIndex) in onlineIndexes.keys():
                onlineIndexes[str(allocatedTrigger.systemIndex)] += 1
                if allocatedTrigger.clusterSet > 0:
                    if str(allocatedTrigger.clusterSet) not in groups:
                        groups[str(allocatedTrigger.clusterSet)] = allocatedTrigger.systemIndex
        for allocatedTrigger in allocatedTriggers:
            if allocatedTrigger.clusterSet > 0:
                if str(allocatedTrigger.clusterSet) in groups:
                    onlineIndexes[str(groups[str(allocatedTrigger.clusterSet)])] += 1
                    allocatedTrigger.systemIndex = int(groups[str(allocatedTrigger.clusterSet)])
                    allocatedTrigger.update(["systemIndex"])
                else:
                    leastAssigned = [1,65535]
                    for systemIndex in onlineIndexes.keys():
                        if onlineIndexes[systemIndex] < leastAssigned[1]:
                            leastAssigned[0] = systemIndex
                            leastAssigned[1] = onlineIndexes[str(systemIndex)]
                    onlineIndexes[leastAssigned[0]] += 1
                    allocatedTrigger.systemIndex = int(leastAssigned[0])
                    allocatedTrigger.update(["systemIndex"])
                    groups[str(allocatedTrigger.clusterSet)] = int(leastAssigned[0])
            # Check that a trigger is assigned to a system index or if the system index is still alive
            elif allocatedTrigger.systemIndex == 0 or str(allocatedTrigger.systemIndex) not in onlineIndexes.keys():
                leastAssigned = [1,65535]
                for systemIndex in onlineIndexes.keys():
                    if onlineIndexes[systemIndex] < leastAssigned[1]:
                        leastAssigned[0] = systemIndex
                        leastAssigned[1] = onlineIndexes[systemIndex]
                onlineIndexes[leastAssigned[0]] += 1
                allocatedTrigger.systemIndex = int(leastAssigned[0])
                allocatedTrigger.update(["systemIndex"])

        if self.master:
            ## Restart ##
            failedTriggers = jimi.trigger._trigger()._dbCollection.aggregate([
                {
                    "$project": 
                    { 
                        "maxEndTime" : { "$add" : ["$startCheck","$maxDuration",clusterSettings["recoveryTime"]] },
                        "startCheck" : 1,
                        "maxDuration" : 1,
                        "nextCheckMaxWait" : { "$add" : [ "$nextCheck", clusterSettings["recoveryTime"] ] },
                        "nextCheck" : 1,
                        "enabled" : 1,
                        "schedule" : 1,
                        "name" : 1,
                        "attemptsLeft" : { "$subtract" : [ "$autoRestartCount", "$attemptCount" ] }
                    }
                },
                {
                    "$match" : 
                    {
                        "$or" : [
                            {
                                "startCheck" : { "$gt" : 0 },
                                "maxEndTime" : { "$lt" :  time.time() }
                            },
                            {
                               "nextCheckMaxWait" : { "$lt" : time.time() },
                               "nextCheck" : { "$gt" : 0 },
                               "startCheck" : 0
                            }
                        ],
                        "enabled" : True
                    }
                }
            ])
            # Getting lowest systemID
            try:
                lowestID = active[0]
            except IndexError:
                lowestID = self.systemID
                active.append(lowestID)
            for systemID in active:
                if systemID < lowestID:
                    lowestID = systemID
            for failedTrigger in failedTriggers:
                if failedTrigger["attemptsLeft"] is None:
                    failedTrigger["attemptsLeft"] = 0
                if failedTrigger["attemptsLeft"] < 1 and failedTrigger["schedule"] != "":
                    jimi.audit._audit().add("cluster","dead trigger",{ "triggerID" : failedTrigger["_id"], "triggerName" : failedTrigger["name"], "attemptsLeft" : failedTrigger["attemptsLeft"], "masterID" : self.systemID, "masterUID" : self.systemUID })
                else:
                    failedTriggerClass = jimi.trigger._trigger().getAsClass(id=failedTrigger["_id"])
                    if len(failedTriggerClass) == 1:
                        failedTriggerClass = failedTriggerClass[0]
                        if failedTriggerClass.startCheck + failedTriggerClass.maxDuration + failedTriggerClass.autoRestartDelay < time.time():
                            availableSystems = getSupportedSystems(failedTriggerClass._id,active)
                            availableSystems.sort()
                            if len(availableSystems) == 0:
                                jimi.audit._audit().add("cluster","restart trigger",{ "triggerID" : failedTriggerClass._id, "triggerName" : failedTriggerClass.name, "triggerAttemptCount" : failedTriggerClass.attemptCount, "triggerSystemID" : failedTriggerClass.systemID, "masterID" : self.systemID, "masterUID" : self.systemUID, "msg" : "No available systems that support the attached flows.", "success" : False })
                            else:
                                try:
                                    index = availableSystems.index(failedTriggerClass.systemID)
                                    failedTriggerClass.systemID = availableSystems[index+1]
                                except:
                                    failedTriggerClass.systemID = availableSystems[0]
                                failedTriggerClass.startCheck = 0
                                failedTriggerClass.systemIndex = 0
                                failedTriggerClass.nextCheck = time.time()
                                failedTriggerClass.update(["systemID","systemIndex","startCheck","nextCheck"])
                                jimi.audit._audit().add("cluster","restart trigger",{ "triggerID" : failedTriggerClass._id, "triggerName" : failedTriggerClass.name, "triggerAttemptCount" : failedTriggerClass.attemptCount, "triggerSystemID" : failedTriggerClass.systemID, "masterID" : self.systemID, "masterUID" : self.systemUID, "success" : True })
                                jimi.exceptions.triggerCrash(failedTriggerClass._id,failedTriggerClass.name,'Restarting failed trigger. triggerSystemID={0}, masterID={1}, attempt={2}'.format(failedTriggerClass.systemID,self.systemID,failedTriggerClass.attemptCount))
                    else:
                        if jimi.logging.debugEnabled:
                            jimi.logging.debug("Unable to load trigger {0} for restarting".format(failedTrigger["_id"]),3)

            ## FAILOVER ##
            # Reset systemID for all non-active systems
            result = jimi.trigger._trigger().api_update(query={ "systemID" : { "$nin" : active } },update={ "$set" : { "systemID" : None } })
            if result:
                if jimi.logging.debugEnabled:
                    jimi.logging.debug("Reset {0} triggers from inactive cluster members".format(result["count"]),6)
            else:
                if jimi.logging.debugEnabled:
                    jimi.logging.debug("Unable to reset triggers from inactive cluster members - active='{0}'".format(active),2)
            if len(active) > 0:
                inactiveTriggers = jimi.trigger._trigger(False).getAsClass(query={ "systemID" : { "$nin" : active }, "enabled" : True })
                if len(inactiveTriggers) > 0:
                    if jimi.logging.debugEnabled:
                        jimi.logging.debug("Moving triggers from inactive cluster member to active members",2)
                    clusterMembersDetails = {}
                    for activeMember in active:
                        count = jimi.trigger._trigger(False).getAsClass(query={ "systemID" : activeMember, "enabled" : True })
                        clusterMembersDetails[str(activeMember)] = { "count" : len(count) }
                    # Building cluster sets
                    groups = {}
                    groupIndex = 0
                    triggerGroups = jimi.trigger._trigger(False).getAsClass(query={ "systemID" : { "$nin" : active }, "clusterSet" : { "$gt" : 0 }, "enabled" : True })
                    for triggerGroup in triggerGroups:
                        if str(triggerGroup.clusterSet) not in groups:
                            if triggerGroup.systemID in active:
                                groups[str(triggerGroup.clusterSet)] = triggerGroup.systemID
                            else:
                                groups[str(triggerGroup.clusterSet)] = active[groupIndex]
                                groupIndex += 1
                                if groupIndex > len(active):
                                    groupIndex = 0

                    for inactiveTrigger in inactiveTriggers:
                        if inactiveTrigger.startCheck + inactiveTrigger.maxDuration + inactiveTrigger.autoRestartDelay < time.time():
                            lowestMember = [active[-1],clusterMembersDetails[str(active[-1])]["count"]]
                            availableSystems = getSupportedSystems(inactiveTrigger._id,active)
                            if len(availableSystems) == 0:
                                jimi.audit._audit().add("cluster","set trigger",{ "triggerID" : inactiveTrigger._id, "triggerName" : inactiveTrigger.name, "clusterSet" : inactiveTrigger.clusterSet, "masterID" : self.systemID, "masterUID" : self.systemUID, "msg" : "No available systems that support the attached flows.", "success" : False })
                            else:
                                for activeMember in availableSystems:
                                    if clusterMembersDetails[str(activeMember)]["count"] < lowestMember[1]:
                                        lowestMember[0] = activeMember
                                        lowestMember[1] = clusterMembersDetails[str(activeMember)]["count"]
                                member = lowestMember[0]
                                if inactiveTrigger.clusterSet != 0:
                                    if str(inactiveTrigger.clusterSet) not in groups:
                                        # Should check others within the group to ensure we put them back on the same member
                                        groups[str(inactiveTrigger.clusterSet)] = lowestMember[0]
                                    else:
                                        member = groups[str(inactiveTrigger.clusterSet)]
                                inactiveTrigger.systemID = member
                                inactiveTrigger.startCheck = 0
                                inactiveTrigger.systemIndex = 0
                                inactiveTrigger.update(["systemID","startCheck","systemIndex"])
                                clusterMembersDetails[str(member)]["count"]+=1
                                if jimi.logging.debugEnabled:
                                    jimi.logging.debug("Set triggerID='{0}' triggers to systemID='{1}', new trigger count='{2}'".format(inactiveTrigger._id,member,clusterMembersDetails[str(member)]["count"]),6)
                                jimi.audit._audit().add("cluster","set trigger",{ "triggerID" : inactiveTrigger._id, "triggerName" : inactiveTrigger.name, "systemID" : member, "clusterSet" : inactiveTrigger.clusterSet, "masterID" : self.systemID, "masterUID" : self.systemUID, "msg" : "Moving trigger from dead node" })
        return True

class _cluster:
    stopped = False
    startTime = None
    lastHandle = 0
    clusterMember = None

    def handler(self):
        self.startTime = int(time.time())
        self.clusterMember = loadClusterMember()
        while not self.stopped:
            jimi.audit._audit().add("cluster","poll",{ "systemID" : self.clusterMember.systemID, "master" : self.clusterMember.master, "systemUID" : self.clusterMember.systemUID })
            now = int(time.time())
            self.lastHandle = now
            if not self.clusterMember.sync():
                self.stopped = True
            # pause
            time.sleep(clusterSettings["loopP"])
            

systemSettings = jimi.config["system"]
clusterSettings = jimi.settings.getSetting("cluster",None)

def loadClusterMember():
    clusterMember = _clusterMember().getAsClass(query={ "systemID" : systemSettings["systemID"] })
    if len(clusterMember) == 1:
        clusterMember = clusterMember[0]
    elif len(clusterMember) > 1:
        clusterMember = clusterMember[0]
        jimi.logging.debug("ERROR: Duplicated systemID found.",-1)
    else:
        clusterMember = _clusterMember().new(systemSettings["systemID"]).inserted_id
        clusterMember = _clusterMember().getAsClass(id=clusterMember)
        clusterMember = clusterMember[0]
    
    clusterMember.syncCount = 0
    clusterMember.bindAddress = systemSettings["accessAddress"]
    clusterMember.bindPort = systemSettings["accessPort"]
    try:
        clusterMember.bindSecure = systemSettings["secure"]
    except KeyError:
        pass
    clusterMember.systemUID = str(uuid.uuid4())
    clusterMember.update(["syncCount","systemUID","bindAddress","bindPort","bindSecure"])
    return clusterMember

def getSystemId():
    return systemSettings["systemID"]

def getSystem():
    return getClusterMemberById(systemSettings["systemID"])

def getClusterMemberById(systemID):
    clusterMember = _clusterMember().getAsClass(query={ "systemID" : systemID })
    if len(clusterMember) == 1:
        clusterMember = clusterMember[0]
        return clusterMember
    return None

def getclusterMemberURLById(systemID):
    clusterMember = _clusterMember().getAsClass(query={ "systemID" : systemID })
    if len(clusterMember) == 1:
        clusterMember = clusterMember[0]
        propcol = "http"
        if clusterMember.bindSecure:
            propcol = "https"
        return "{0}://{1}:{2}".format(propcol,clusterMember.bindAddress, clusterMember.bindPort)
    return None

def getMaster():
    clusterMaster = _clusterMember().getAsClass(query={ "master" : True })
    if len(clusterMaster) > 0:
        clusterMaster = clusterMaster[0]
        propcol = "http"
        if clusterMaster.bindSecure:
            propcol = "https"
        return "{0}://{1}:{2}".format(propcol,clusterMaster.bindAddress, clusterMaster.bindPort)
    return "http://127.0.0.1:5000"

def getMasterId():
    clusterMaster = _clusterMember().getAsClass(query={ "master" : True })
    if len(clusterMaster) > 0:
        clusterMaster = clusterMaster[0]
        return clusterMaster.systemID

def getAll():
    clusterMembers = _clusterMember().getAsClass(query={ "lastSyncTime" : { "$gt" : (time.time()-60) } })
    if len(clusterMembers) > 0:
        result = []
        for clusterMember in clusterMembers:
            propcol = "http"
            if clusterMember.bindSecure:
                propcol = "https"
            result.append("{0}://{1}:{2}".format(propcol,clusterMember.bindAddress, clusterMember.bindPort))
        return result
    return ["http://127.0.0.1:5000"]

def getSupportedSystems(triggerID,activeSystems):
    models = jimi.conduct.getTriggerUsedModels(triggerID)
    availableSystems = []
    for activeMember in activeSystems:
        passed = True
        clusterMemberObject = getClusterMemberById(activeMember)
        for model in models:
            if model not in clusterMemberObject.supportedModels:
                passed = False
                break
        if passed:
            availableSystems.append(activeMember)
    return availableSystems

######### --------- API --------- #########
if jimi.api.webServer:
    if not jimi.api.webServer.got_first_request:
        if jimi.api.webServer.name == "jimi_core":
            pass

        if jimi.api.webServer.name == "jimi_web":
            @jimi.api.webServer.route(jimi.api.base+"cluster/distribute/", methods=["GET"])
            @jimi.auth.adminEndpoint
            def distributeCluster():
                jimi.trigger._trigger().api_update(query={ "startCheck" : 0 },update={ "$set" : { "systemID" : None } })
                return { }, 200
