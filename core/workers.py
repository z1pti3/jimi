from multiprocessing import Process, Queue
import multiprocessing
import threading
import time
import uuid
import ctypes
import json
import traceback
import copy
import sys

import jimi

class _threading(threading.Thread):
    def __init__(self, *args, **keywords):
        threading.Thread.__init__(self, *args, **keywords)

    def get_id(self):
        for id, thread in threading._active.items(): 
            if thread is self: 
                return id

    def kill(self): 
        thread_id = self.get_id() 
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(thread_id), ctypes.py_object(SystemExit))
        if res == 0:
            if jimi.logging.debugEnabled:
                jimi.logging.debug("Exception raise failure - invalid thread ID")
        if res > 1: 
            ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(thread_id), 0)

class workerHandler:
    class _worker:
        def __init__(self, name, call, args, delete, maxDuration, multiprocessing, raiseException):
            self.name = name
            self.call = call
            self.id = str(uuid.uuid4())
            self.createdTime = int(time.time())
            self.startTime = 0
            self.endTime = 0
            self.duration = 0
            self.result = None
            self.resultException = None
            self.raiseException = raiseException
            self.running = None
            self.crash = False
            self.args = args
            self.multiprocessing = multiprocessing
            if not self.multiprocessing:
                self.thread = _threading(target=self.threadCall)
            else:
                self.thread = _threading(target=self.multiprocessingThreadCall)
            self.maxDuration = maxDuration
            self.delete = delete

        def start(self):
            self.thread.start()

        def multiprocessingThreadCall(self):
            self.startTime = int(time.time())
            self.running = True
            if jimi.logging.debugEnabled:
                jimi.logging.debug("Threaded process worker started, workerID={0}".format(self.id))

            Q = Queue()
            p = Process(target=multiprocessingThreadStart, args=(Q,self.call,self.args)) # Taking an entire copy of cache is not effient review bug
            try:
                p.start()
                try:
                    rc, e = Q.get(timeout=self.maxDuration)
                    p.join(timeout=self.maxDuration)
                except:
                    raise SystemExit

                if rc != 0:
                    self.crash = True
                    if jimi.logging.debugEnabled:
                        jimi.logging.debug("Threaded process worker crashed, workerID={0}".format(self.id))
                    systemTrigger.failedTrigger(self.id,"triggerCrashed",''.join(traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__)))

                # Ensure cache is updated with any new items
                #cache.globalCache.sync(globalCacheObjects)
            except SystemExit as e:
                if self.raiseException:
                    self.crash = True
                    jimi.logging.debug("Error: Worker Killed. workerID={0}".format(self.id,),-1)
                    systemTrigger.failedTrigger(self.id,"triggerKilled")
                else:
                    self.resultException = e
            except Exception as e:
                if self.raiseException:
                    self.crash = True
                    jimi.logging.debug("Error: Worker Crashed. workerID={0}, error={1}".format(self.id,''.join(traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__))),-1)
                    systemTrigger.failedTrigger(self.id,"triggerCrashed",''.join(traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__)))
                else:
                    self.resultException = e
            finally:
                if p.exitcode == None:
                    p.terminate()
                #Q.close()
            
            if jimi.logging.debugEnabled:
                jimi.logging.debug("Threaded process worker completed, workerID={0}".format(self.id))
            self.running = False
            self.endTime = int(time.time())
            self.duration = (self.endTime - self.startTime)

        def threadCall(self):
            self.startTime = int(time.time())
            self.running = True
            if jimi.logging.debugEnabled:
                jimi.logging.debug("Threaded worker started, workerID={0}".format(self.id))
            # Handle thread raise exception kill
            try:
                if self.args:
                    self.result = self.call(*self.args)
                else:
                    self.result = self.call()
            except SystemExit as e:
                if self.raiseException:
                    self.crash = True
                    jimi.logging.debug("Error: Worker Killed. workerID={0}".format(self.id,),-1)
                    systemTrigger.failedTrigger(self.id,"triggerKilled")
                else:
                    self.resultException = e
            except Exception as e:
                if self.raiseException:
                    self.crash = True
                    jimi.logging.debug("Error: Worker Crashed. workerID={0}, error={1}".format(self.id,''.join(traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__))),-1)
                    systemTrigger.failedTrigger(self.id,"triggerCrashed",''.join(traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__)))
                else:
                    self.resultException = e
            if jimi.logging.debugEnabled:
                jimi.logging.debug("Threaded worker completed, workerID={0}".format(self.id))
            self.running = False
            self.endTime = int(time.time())
            self.duration = (self.endTime - self.startTime)

    def __init__(self,concurrent=15,autoStart=True,cleanUp=True):
        self.concurrent = concurrent
        self.workerList = []
        self.stopped = False
        self.cleanUp = cleanUp
        self.backlog = False
        self.failures = False
        
        # Autostarting worker handler thread
        workerThread = self._worker("workerThread",self.handler,None,True,0,False,True)
        workerThread.start()
        self.workerList.append(workerThread)
        self.workerID = workerThread.id

    def handler(self):
        tick = 0
        loops = 0
        underConcurrent = self.concurrent # Used to limit list looping to find active workers
        workersStillWaiting = [] # Cache waiting workers to limit list looping to find waiting workers
        while not self.stopped:
            now = int(time.time())
            self.lastHandle = now

            # Any room to start another worker?
            if underConcurrent < 1:
                activeWorkerCount = len([ x for x in self.workerList if x.running == True ])
                underConcurrent = ( self.concurrent - activeWorkerCount )
            if underConcurrent > 0:
                if len(workersStillWaiting) == 0:
                    workersStillWaiting = [ x for x in self.workerList if x.running == None ]
                if len(workersStillWaiting) > 0:
                    self.backlog = True
                    # Check if number of workersWaiting is above the number of available concurrent threads and select mx available
                    workersWaiting = workersStillWaiting
                    if len(workersWaiting) > underConcurrent:
                        workersWaiting = workersWaiting[0:underConcurrent]
                    # Start all workers possible up to the concurrent limit
                    for workerWaiting in workersWaiting:
                        if jimi.logging.debugEnabled:
                            jimi.logging.debug("Starting threaded worker, workerID={0}".format(workerWaiting.id))
                        workerWaiting.start()
                        underConcurrent-=1
                        del workersStillWaiting[workersStillWaiting.index(workerWaiting)]
                else:
                    self.backlog = False
            else:
                self.backlog = False

            # Execute worker cleanup every 5ish seconds
            if (tick + 5) < now:
                # Any workers need clearning up due to overrun or stopped?
                cleanupWorkers = [ x for x in self.workerList if (x.running == False and x.delete) or (x.startTime > 0 and x.maxDuration > 0 and (now - x.startTime ) > x.maxDuration) ]
                for worker in cleanupWorkers:
                    if worker.running != False:
                        worker.thread.kill()
                    if not self.failures and worker.resultException != None and worker.endTime != 0:
                        self.failures = True
                    if self.cleanUp:
                        # Making sure that only completed workers i.e. endTime!=0 are clearned
                        if worker.resultException == None and worker.endTime != 0 or (( worker.endTime + 60 < now ) and worker.endTime != 0):
                            self.workerList.remove(worker)
                tick = now

            # CPU saver
            loops+=1
            if ((underConcurrent == 0) or (underConcurrent > 0 and len(workersStillWaiting) == 0)):
                loops = 0
                time.sleep(workerSettings["loopT1"])
            elif (loops > workerSettings["loopL"]):
                loops = 0
                time.sleep(workerSettings["loopT"])
            
    def new(self, name, call, args=None, delete=True, maxDuration=60, multiprocessing=False, raiseException=True):
        workerThread = self._worker(name, call, args, delete, maxDuration, multiprocessing, raiseException)
        self.workerList.append(workerThread)
        if jimi.logging.debugEnabled:
            jimi.logging.debug("Created new worker, workerID={0}".format(workerThread.id))
        return workerThread.id

    def get(self, id):
        worker = [x for x in self.workerList if x.id == id]
        if worker:
            worker = worker[0]
        if jimi.logging.debugEnabled:
            jimi.logging.debug("Got data for worker, workerID={0}".format(id))
        return worker

    def getAll(self):
        result = []
        for worker in self.workerList:
            result.append(worker)
        return result

    def getActive(self):
        result = []
        workersRunning = [x for x in self.workerList if x.running == True]
        for worker in workersRunning:
            result.append(worker)
        return result

    def getError(self, id):
        result = None
        worker = [x for x in self.workerList if x.id == id]
        if worker:
            worker = worker[0]
            result = worker.resultException
            worker.resultException = None
        return result
    
    def delete(self, id):
        worker = [x for x in self.workerList if x.id == id]
        if worker:
            worker = worker[0]
            if jimi.logging.debugEnabled:
                jimi.logging.debug("Deleted worker, workerID={0}".format(id))
            del worker
        else:
            if jimi.logging.debugEnabled:
                jimi.logging.debug("Unable to locate worker, workerID={0}".format(id))

    def kill(self, id):
        worker = [x for x in self.workerList if x.id == id]
        if worker:
            worker = worker[0]
            worker.thread.kill()
            if jimi.logging.debugEnabled:
                jimi.logging.debug("Killed worker, workerID={0}".format(id))
        else:
            if jimi.logging.debugEnabled:
                jimi.logging.debug("Unable to locate worker, workerID={0}".format(id))

    def wait(self, jid):
        worker = [x for x in self.workerList if x.id == jid][0]
        if jimi.logging.debugEnabled:
            jimi.logging.debug("Waiting for worker, workerID={0}".format(id))
        if worker:
            while (worker.running != False ):
                time.sleep(0.1)

    def waitAll(self):
        while (self.queue() > 0 or len(self.active()) > 0):
            time.sleep(0.1)

    def activeCount(self):
        workersRunning = [x for x in self.workerList if x.id != self.workerID and x.running == True]
        return len(workersRunning)

    def failureCount(self):
        crashedWorkers = [x for x in self.workerList if x.id != self.workerID and x.crash == True]
        return len(crashedWorkers)

    def active(self):
        result = []
        workersRunning = [x for x in self.workerList if x.id != self.workerID and x.running == True]
        for workerRunning in workersRunning:
            result.append(workerRunning.name)
        return result

    def count(self):
        return len(self.workerList)

    def countIncomplete(self):
        return len([x for x in self.workerList if x.id != self.workerID and (x.running == True or x.running == None) ])

    def queue(self):
        workersWaiting = [x for x in self.workerList if x.running == None]
        return len(workersWaiting)

    def stop(self):
        self.stopped = True
        # Waiting 1 second for handler to finsh gracefuly otherwise force by systemExit
        time.sleep(1)
        for runningJob in self.getActive():
            self.kill(runningJob.id)
        for job in self.getAll():
            self.delete(job.id)

    # API Calls
    def api_get(self,id=None,action=None):
        result = { "results" : []}
        if not id and not action:
            workers = self.getAll()
        elif id and not action:
            workers = [self.get(id)]
        elif not id and action == "active":
            workers = self.getActive()

        for worker in workers:
            if worker:
                result["results"].append({ "id" : worker.id, "name": worker.name, "startTime" : worker.startTime, "createdTime" : worker.createdTime })
        
        return result

    def api_delete(self,id=None):
        if not id:
            workers = self.getAll()
        else:
            workers = [self.get(id)]

        for worker in workers:
            worker.thread.kill()

        return { "result" : True }

from system.models import trigger as systemTrigger

workerSettings = jimi.settings.config["workers"]

multiprocessing.set_start_method("spawn",force=True)

def start():
    global workers
    # Creating instance of workers
    try:
        if workers:
            workers.kill(workers.workerID)
            if logging.debugEnabled:
                logging.debug("Workers start requested, Existing thread kill attempted, workerID='{0}'".format(workers.workerID),6)
            workers = None
    except NameError:
        pass
    workers = workerHandler(workerSettings["concurrent"])
    if jimi.logging.debugEnabled:
        jimi.logging.debug("Workers started, workerID='{0}'".format(workers.workerID),6)
    return True

def multiprocessingThreadStart(Q,threadCall,args):
    #cache.globalCache.sync(globalCache)
    rc = 0
    error = None
    try:
        threadCall(*args)
    except Exception as e:
        error = e
        rc = 1
    Q.put((rc,error))

######### --------- API --------- #########
if jimi.api.webServer:
    if not jimi.api.webServer.got_first_request:
        if jimi.api.webServer.name == "jimi_core":
            @jimi.api.webServer.route(jimi.api.base+"workers/", methods=["GET"])
            @jimi.auth.adminEndpoint
            def getWorkers():
                result = workers.api_get()
                if result["results"]:
                    return result, 200
                else:
                    return {}, 404

            @jimi.api.webServer.route(jimi.api.base+"workers/", methods=["DELETE"])
            @jimi.auth.adminEndpoint
            def deleteWorkers():
                result = workers.api_delete()
                if result["result"]:
                    return result, 200
                else:
                    return {}, 404

            @jimi.api.webServer.route(jimi.api.base+"workers/", methods=["POST"])
            @jimi.auth.adminEndpoint
            def updateWorkers():
                data = json.loads(jimi.api.request.data)
                if data["action"] == "start":
                    result = start()
                    return { "result" : result }, 200
                elif data["action"] == "settings":
                    if "concurrent" in data:
                        workerSettings["concurrent"] = int(data["concurrent"])
                        workers.concurrent = workerSettings["concurrent"]
                    if "loopT" in data:
                        workerSettings["loopT"] = float(data["loopT"])
                    if "loopL" in data:
                        workerSettings["loopL"] = float(data["loopL"])
                    return { }, 200
                else:
                    return { }, 404

            @jimi.api.webServer.route(jimi.api.base+"workers/<workerID>/", methods=["GET"])
            @jimi.auth.adminEndpoint
            def getWorker(workerID):
                if workerID == "0":
                    result = workers.api_get(workers.workerID)
                    result["results"][0]["lastHandle"] = workers.lastHandle
                    result["results"][0]["workerID"] = workers.workerID
                else:
                    result = workers.api_get(workerID)

                if result["results"]:
                    return result, 200
                else:
                    return {}, 404

            @jimi.api.webServer.route(jimi.api.base+"workers/<workerID>/", methods=["DELETE"])
            @jimi.auth.adminEndpoint
            def deleteWorker(workerID):
                result = workers.api_delete(workerID)
                if result["result"]:
                    return result, 200
                else:
                    return {}, 404

            @jimi.api.webServer.route(jimi.api.base+"workers/stats/", methods=["GET"])
            @jimi.auth.adminEndpoint
            def getWorkerStats():
                result = {}
                result["results"] = []
                result["results"].append({ "activeCount" : workers.activeCount(), "queueLength" : workers.queue(), "workers" : workers.active() })
                return result, 200

            @jimi.api.webServer.route(jimi.api.base+"workers/settings/", methods=["GET"])
            @jimi.auth.adminEndpoint
            def getWorkerSettings():
                result = {}
                result["results"] = []
                result["results"].append(workerSettings)
                return result, 200
