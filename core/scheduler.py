import time
import random
import re
import datetime
import croniter
import uuid

import jimi

class _scheduler:
    stopped = False
    startTime = None
    lastHandle = None
    workerHandler = None
    systemId = None
    systemIndex = None

    def __init__(self,systemId,systemIndex):
        self.systemId = systemId
        self.systemIndex = systemIndex

    def handler(self):
        self.startTime = int(time.time())
        while not self.stopped:
            now = int(time.time())
            self.lastHandle = now
            for t in jimi.trigger._trigger(False).getAsClass(query={ "systemID" : self.systemId, "systemIndex" : self.systemIndex, "$or" : [ {"nextCheck" : { "$lt" :  now}}, {"$or" : [ {"nextCheck" : { "$eq" : ""}} , {"nextCheck" : {"$eq" : None }} ] } ], "enabled" : True, "startCheck" :  0, "$and":[{"schedule" : {"$ne" : None}} , {"schedule" : {"$ne" : ""}} ] }):
                if t.nextCheck == 0:
                    t.nextCheck = getSchedule(t.schedule)
                    t.update(["nextCheck"])
                else:
                    if jimi.workers.workers.activeCount() < jimi.workers.workers.concurrent:
                        t.startCheck = time.time()
                        t.attemptCount += 1
                        t.executionCount += 1
                        maxDuration = 60
                        if type(t.maxDuration) is int and t.maxDuration > 0:
                            maxDuration = t.maxDuration
                        t.workerID = jimi.workers.workers.new("trigger:'{0}','{1}'".format(t._id,t.name),t.checkHandler,(),maxDuration=maxDuration,multiprocessing=t.threaded)
                        t.update(["startCheck","workerID","attemptCount","executionCount"])      
                    else:
                        if jimi.logging.debugEnabled:
                            jimi.logging.debug("Scheduler trigger start cannot requested, as the max conncurrent workers are already active. Will try again shortly",3)
            # pause
            time.sleep(jimi.settings.getSetting("scheduler","loopP"))

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
