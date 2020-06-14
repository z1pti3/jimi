import uuid
import time
import json

from core import db

# Initialize
dbCollectionName = "clusterMembers"

class _clusterMember(db._document):
    systemID = int()
    systemUID = str()
    bindAddress = str()
    bindPort = int()
    master = bool()
    syncCount = int()
    lastSyncTime = int()

    _dbCollection = db.db[dbCollectionName]

    def new(self,systemID):
        self.systemID = systemID
        self.master = False
        self.acl = { "ids":[ { "accessID":"0","delete": True,"read": True,"write": True } ] } 
        return super(_clusterMember, self).new()

    def sync(self):
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
                    logging.debug("ERROR: Duplicated systemID detected during sync.",-1)
                    return False
                if clusterMember.master:
                    self.master = True
                else:
                    self.master = False

            if clusterMember.master:
                masters.append(clusterMember)
            if clusterMember.lastSyncTime > now - clusterSettings["deadTimer"]:
                active.append(clusterMember.systemID)

            if ((clusterMember.master) and (clusterMember.lastSyncTime < now - clusterSettings["deadTimer"])):
                clusterMember.master = False
                clusterMember.update(["master"])
                deadMaster = True
            else:
                if lowestMaster[1] > clusterMember.systemID:
                    lowestMaster[0] = clusterMember
                    lowestMaster[1] = clusterMember.systemID

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

        if self.master:
            # Reset systemID for all non-active systems
            result = trigger._trigger().api_update(query={ "systemID" : { "$nin" : active } },update={ "$set" : { "systemID" : None } })
            if result:
                logging.debug("Reset {0} triggers from inactive cluster members".format(result["count"]),6)
            else:
                logging.debug("Unable to reset triggers from inactive cluster members - active='{0}'".format(active),2)

            if len(active) > 0:
                inactiveTriggers = trigger._trigger().getAsClass(query={ "systemID" : { "$nin" : active }, "enabled" : True })
                if len(inactiveTriggers) > 0:
                    logging.debug("Moving triggers from inactive cluster member to active members",2)
                    clusterMembersDetails = {}
                    for activeMember in active:
                        count = trigger._trigger().getAsClass(query={ "systemID" : activeMember, "enabled" : True })
                        clusterMembersDetails[str(activeMember)] = { "count" : len(count) }
                    groups = {}
                    for inactiveTrigger in inactiveTriggers:
                        lowestMember = [active[-1],clusterMembersDetails[str(active[-1])]["count"]]
                        for activeMember in active:
                            if clusterMembersDetails[str(activeMember)]["count"] < lowestMember[1]:
                                lowestMember[0] = activeMember
                                lowestMember[1] = clusterMembersDetails[str(activeMember)]["count"]
                        member = lowestMember[0]
                        if inactiveTrigger.clusterSet != 0:
                            if str(inactiveTrigger.clusterSet) not in groups:
                                groups[str(inactiveTrigger.clusterSet)] = lowestMember[0]
                            else:
                                member = groups[str(inactiveTrigger.clusterSet)]
                        inactiveTrigger.systemID = member
                        inactiveTrigger.startCheck = 0
                        inactiveTrigger.update(["systemID","startCheck"])
                        clusterMembersDetails[str(member)]["count"]+=1
                        logging.debug("Set triggerID='{0}' triggers to systemID='{1}', new trigger count='{2}'".format(inactiveTrigger._id,member,clusterMembersDetails[str(member)]["count"]),6)
                        audit._audit().add("cluster","set trigger",{ "triggerID" : inactiveTrigger._id, "triggerName" : inactiveTrigger.name, "systemID" : member, "clusterSet" : inactiveTrigger.clusterSet, "masterID" : self.systemID, "masterUID" : self.systemUID })

        return True

class _cluster:
    stopped = False
    startTime = None
    lastHandle = None

    def __init__(self):
        self.workerID = workers.workers.new("cluster",self.handler,maxDuration=0)
        self.startTime = int(time.time())

    def handler(self):
        clusterMember = loadClusterMember()
        while not self.stopped:
            now = int(time.time())
            self.lastHandle = now
            if not clusterMember.sync():
                self.stopped = True
            # pause
            time.sleep(clusterSettings["loopP"])
            

from core import settings, api, helpers, logging, workers, audit

from core.models import trigger

systemSettings = settings.config["system"]
clusterSettings = settings.config["cluster"]
apiSettings = settings.config["api"]

def loadClusterMember():
    clusterMember = _clusterMember().getAsClass(query={ "systemID" : systemSettings["systemID"] })
    if len(clusterMember) == 1:
        clusterMember = clusterMember[0]
    elif len(clusterMember) > 1:
        logging.debug("ERROR: Duplicated systemID found.",-1)
        return None
    else:
        clusterMember = _clusterMember().new(systemSettings["systemID"]).inserted_id
        clusterMember = _clusterMember().getAsClass(id=clusterMember)
        clusterMember = clusterMember[0]
    
    clusterMember.syncCount = 0
    clusterMember.bindAddress = apiSettings["core"]["bind"]
    clusterMember.bindPort = apiSettings["core"]["port"]
    clusterMember.systemUID = str(uuid.uuid4())
    clusterMember.update(["syncCount","systemUID","bindAddress","bindPort"])
    return clusterMember

def start():
    global cluster
    try:
        if workers.workers:
            try:
                # Creating instance of cluster
                if cluster:
                    workers.workers.kill(cluster.workerID)
                    logging.debug("Cluster start requested, Existing thread kill attempted, workerID='{0}'".format(cluster.workerID),6)
                    cluster = None
            except NameError:
                pass
            cluster = _cluster()
            logging.debug("Cluster started, workerID='{0}'".format(cluster.workerID),6)
            return True
    except AttributeError:
        logging.debug("Cluster start requested, No valid worker class loaded",4)
        return False


######### --------- API --------- #########
if api.webServer:
    if not api.webServer.got_first_request:
        @api.webServer.route(api.base+"cluster/", methods=["GET"])
        def getCluster():
            result = None
            if cluster:
                result = { "stopped" : cluster.stopped, "startTime" : cluster.startTime, "lastHandle" : cluster.lastHandle, "workerID" : cluster.workerID }
            results = _clusterMember().query()["results"]
            return { "self" : result, "cluster" : results }, 200

        @api.webServer.route(api.base+"cluster/", methods=["POST"])
        def updateCluster():
            data = json.loads(api.request.data)
            if data["action"] == "start":
                result = start()
                return { "result" : result }, 200
            else:
                return { }, 404
