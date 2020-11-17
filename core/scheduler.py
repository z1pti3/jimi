import time
import random
import re
import json
import datetime
import traceback

import croniter

class _scheduler:
    stopped = False
    startTime = None
    lastHandle = None

    def __init__(self):
        self.workerID = workers.workers.new("scheduler",self.handler,maxDuration=0)
        self.startTime = int(time.time())

    def handler(self):
        while not self.stopped:
            now = int(time.time())
            self.lastHandle = now
            # Adds defined delay onto nextCheck so that it can pickup ones that would otherwise wait for after the pause
            for t in trigger._trigger().getAsClass(query={ "systemID" : systemSettings["systemID"], "$or" : [ {"nextCheck" : { "$lt" :  (now + schedulerSettings["loopP"])}}, {"$or" : [ {"nextCheck" : { "$eq" : ""}} , {"nextCheck" : {"$eq" : None }} ] } ], "enabled" : True, "startCheck" :  0, "$and":[{"schedule" : {"$ne" : None}} , {"schedule" : {"$ne" : ""}} ] }):
                if t.nextCheck == 0:
                    t.nextCheck = getSchedule(t.schedule)
                    t.update(["nextCheck"]) 
                else:
                    t.startCheck = time.time()
                    t.attemptCount += 1
                    maxDuration = 60
                    if type(t.maxDuration) is int and t.maxDuration > 0:
                        maxDuration = t.maxDuration
                    t.workerID = workers.workers.new("trigger:{0}".format(t._id),t.checkHandler,(),maxDuration=maxDuration,multiprocessing=t.threaded)
                    t.update(["startCheck","workerID","attemptCount"])       
            # pause
            time.sleep(schedulerSettings["loopP"])

from core import api, workers, db, helpers, logging, model, settings, audit
from core.models import conduct, action, trigger

from system.models import trigger as systemTrigger

systemSettings = settings.config["system"]
schedulerSettings = settings.config["scheduler"]

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

def start():
    global scheduler
    try:
        if workers.workers:
            try:
                # Creating instance of scheduler
                if scheduler:
                    workers.workers.kill(scheduler.workerID)
                    if logging.debugEnabled:
                        logging.debug("Scheduler start requested, Existing thread kill attempted, workerID='{0}'".format(scheduler.workerID),6)
                    scheduler = None
            except NameError:
                pass
            scheduler = _scheduler()
            if logging.debugEnabled:
                logging.debug("Scheduler started, workerID='{0}'".format(scheduler.workerID),6)
            return True
    except AttributeError:
        if logging.debugEnabled:
            logging.debug("Scheduler start requested, No valid worker class loaded",4)
        return False

# Creating instance of scheduler
#scheduler = _scheduler()


######### --------- API --------- #########
if api.webServer:
    if not api.webServer.got_first_request:
        @api.webServer.route(api.base+"scheduler/", methods=["GET"])
        def getScheduler():
            if api.g.sessionData["admin"]:
                if scheduler:
                    return { "result": { "stopped" : scheduler.stopped, "startTime" : scheduler.startTime, "lastHandle" : scheduler.lastHandle, "workerID" : scheduler.workerID } },200
                else:
                    return { } , 404
            else:
                return {},403

        @api.webServer.route(api.base+"scheduler/", methods=["POST"])
        def updateScheduler():
            if api.g.sessionData["admin"]:
                data = json.loads(api.request.data)
                if data["action"] == "start":
                    result = start()
                    return { "result" : result }, 200
                else:
                    return { }, 404
            else:
                return {}, 403

        @api.webServer.route(api.base+"scheduler/<triggerID>/", methods=["POST"])
        def forceTriggers(triggerID):
            data = json.loads(api.request.data)
            if data["action"] == "trigger":
                class_ = trigger._trigger().getAsClass(sessionData=api.g.sessionData,id=triggerID)[0]
                if class_:
                    if class_.startCheck == 0:
                        class_.startCheck = time.time()
                        maxDuration = 60
                        if type(class_.maxDuration) is int and class_.maxDuration > 0:
                            maxDuration = class_.maxDuration
                        try:
                            events = json.loads(data["events"])
                        except json.decoder.JSONDecodeError:
                            events = [data["events"]]
                            # Ensure we run even if no event data was sent
                            if events == [""]:
                                class_.update(["startCheck","workerID"])
                                try:
                                    class_.checkHandler()
                                except Exception as e:
                                    if logging.debugEnabled:
                                        logging.debug("Forced trigger crashed, triggerID={0}, triggerName={1}".format(class_._id,class_.name))
                                    systemTrigger.failedTrigger(None,"forcedTriggerCrashed",''.join(traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__)),triggerID=class_._id,triggerName=class_.name)
                                    return { "result" : False }, 400
                                return { "result" : True }, 200
                        if type(events) != list:
                            events = [events]
                        class_.workerID = workers.workers.new("trigger:{0}".format(triggerID),class_.notify,(events,),maxDuration=maxDuration)
                        class_.update(["startCheck","workerID"])
                        return { "result" : True }, 200
                    else:
                        if logging.debugEnabled:
                            logging.debug("Error unable to force trigger, triggerID={0} as it is already running.".format(triggerID))
                        return { "result" : False, "reason" : "Trigger already running" }, 403
                else:
                    if logging.debugEnabled:
                        logging.debug("Error unable to force trigger, triggerID={0} as its triggerID cannot be loaded.".format(triggerID))
                    return { "result" : False, "reason" : "triggerID could not be loaded" }, 404
            else:
                return {}, 404