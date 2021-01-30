import time
import random
import re
import json
import datetime
import traceback
import croniter

import jimi

class _scheduler:
    stopped = False
    startTime = None
    lastHandle = None

    def __init__(self):
        self.workerID = jimi.workers.workers.new("scheduler",self.handler,maxDuration=0)
        self.startTime = int(time.time())

    def handler(self):
        while not self.stopped:
            now = int(time.time())
            self.lastHandle = now
            # Adds defined delay onto nextCheck so that it can pickup ones that would otherwise wait for after the pause
            for t in jimi.trigger._trigger().getAsClass(query={ "systemID" : systemSettings["systemID"], "$or" : [ {"nextCheck" : { "$lt" :  (now + schedulerSettings["loopP"])}}, {"$or" : [ {"nextCheck" : { "$eq" : ""}} , {"nextCheck" : {"$eq" : None }} ] } ], "enabled" : True, "startCheck" :  0, "$and":[{"schedule" : {"$ne" : None}} , {"schedule" : {"$ne" : ""}} ] }):
                if t.schedule == "*":
                    t.nextCheck == 1  
                if t.nextCheck == 0:
                    t.nextCheck = getSchedule(t.schedule)
                    t.update(["nextCheck"]) 
                else:
                    if jimi.workers.workers.activeCount() < jimi.workers.workers.concurrent:
                        t.startCheck = time.time()
                        t.attemptCount += 1
                        maxDuration = 60
                        if type(t.maxDuration) is int and t.maxDuration > 0:
                            maxDuration = t.maxDuration
                        if t.schedule == "*":
                            t.workerID = jimi.workers.workers.new("continuousTrigger:{0}".format(t._id),continuous,(t,),maxDuration=0,multiprocessing=t.threaded)
                        else:
                            t.workerID = jimi.workers.workers.new("trigger:{0}".format(t._id),t.checkHandler,(),maxDuration=maxDuration,multiprocessing=t.threaded)
                        t.update(["startCheck","workerID","attemptCount"])      
                    else:
                        if jimi.logging.debugEnabled:
                            jimi.logging.debug("Scheduler trigger start cannot requested, as the max conncurrent workers are already active. Will try again shortly",3)
            # pause
            time.sleep(schedulerSettings["loopP"])


from system.models import trigger as systemTrigger

systemSettings = jimi.settings.config["system"]
schedulerSettings = jimi.settings.config["scheduler"]

# Get next run time from schedule string
def getSchedule(scheduleString):
    if scheduleString:
        if scheduleString == "now":
            return int(time.time())
        if re.search("^([-\d]*)([mhs]{1})$",scheduleString):
            m = re.match("^([-\d]*)([mhs]{1})$",scheduleString)
            mesure=m.groups()[1]
            value=m.groups()[0]
            if len(value.split("-"))>1:
                if mesure == "m":
                    value=random.randint(int(value.split("-")[0])*60,int(value.split("-")[1])*60)
                elif mesure == "h":
                    value=random.randint(int(value.split("-")[0])*60*60,int(value.split("-")[1])*60*60)
                elif mesure == "s":
                    value=random.randint(int(value.split("-")[0]),int(value.split("-")[1]))
            else:
                if mesure == "m":
                    value=int(value) * 60
                elif mesure == "h":
                    value=int(value) * (60 * 60)
                elif mesure == "s":
                    value=int(value)
            return int(time.time() + value)
        # Not going to reinvent the wheel - using an existing package for cron support
        elif re.search("^(([^\s]+\s)){4,5}[^\s]+$",scheduleString):
            baseTime = datetime.datetime.now()
            cron = croniter.croniter(scheduleString, baseTime)
            value = cron.get_next(datetime.datetime)
            if (value.timestamp() < time.time()+30):
                return None
            return int(value.timestamp())
    return None

def continuous(t):
    startTime = time.time()
    while t.enabled:
        t.checkHandler()
        if time.time() - startTime > 60:
            t.refresh() 

def start():
    global scheduler
    try:
        if jimi.workers.workers:
            try:
                # Creating instance of scheduler
                if scheduler:
                    jimi.workers.workers.kill(scheduler.workerID)
                    if jimi.logging.debugEnabled:
                        jimi.logging.debug("Scheduler start requested, Existing thread kill attempted, workerID='{0}'".format(scheduler.workerID),6)
                    scheduler = None
            except NameError:
                pass
            scheduler = _scheduler()
            if jimi.logging.debugEnabled:
                jimi.logging.debug("Scheduler started, workerID='{0}'".format(scheduler.workerID),6)
            return True
    except AttributeError:
        if jimi.logging.debugEnabled:
            jimi.logging.debug("Scheduler start requested, No valid worker class loaded",4)
        return False

######### --------- API --------- #########
if jimi.api.webServer:
    if not jimi.api.webServer.got_first_request:
        if jimi.api.webServer.name == "jimi_core":
            @jimi.api.webServer.route(jimi.api.base+"scheduler/", methods=["GET"])
            @jimi.auth.systemEndpoint
            def getScheduler():
                if scheduler:
                    return { "result": { "stopped" : scheduler.stopped, "startTime" : scheduler.startTime, "lastHandle" : scheduler.lastHandle, "workerID" : scheduler.workerID } },200
                else:
                    return { } , 404

            @jimi.api.webServer.route(jimi.api.base+"scheduler/", methods=["POST"])
            @jimi.auth.systemEndpoint
            def updateScheduler():
                data = json.loads(jimi.api.request.data)
                if data["action"] == "start":
                    result = start()
                    return { "result" : result }, 200
                else:
                    return { }, 404
