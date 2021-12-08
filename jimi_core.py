import multiprocessing
import threading
import logging

logging.basicConfig(level=logging.INFO)

def startWorker(systemId,systemIndex):
    def healthChecker(scheduler):
        import os
        import time
        logging.info("Starting health checker")
        logging.debug("Garbage Collector %s",jimi.settings.getSetting("cache","garbageCollector"))
        # Waiting for startup i.e. scheduler to poll atleast once
        time.sleep(10)
        while True:
            if jimi.settings.getSetting("cache","garbageCollector"):
                logging.debug("Running cache garbage collector")
                jimi.cache.globalCache.cleanCache()
            if scheduler.lastHandle < time.time() - 60:
                logging.error("Scheduler on index %i has failed",systemIndex)
                jimi.audit._audit().add("system","health_checker",{ "systemID" : systemId, "systemIndex" : systemIndex, "msg" : "Scheduler service has failed." })
                os._exit(5)
            if jimi.workers.workers.lastHandle < time.time() - 60:
                logging.error("Workers on index %i has failed",systemIndex)
                jimi.audit._audit().add("system","health_checker",{ "systemID" : systemId, "systemIndex" : systemIndex, "msg" : "Worker service has failed." })
                os._exit(10)
            time.sleep(10)
    from core import api
    api.createServer("jimi_worker")
    import jimi
    # Load RSA information post jimi import / upgrade ( required for upgraded from 3.0 -> 3.1, should remove in future back to none function )
    jimi.auth.RSAinitialization()
    workerAPISettings = jimi.config["api"]["worker"]
    jimi.function.load()
    api.startServer(True,{'server.socket_host': workerAPISettings["bind"], 'server.socket_port': workerAPISettings["startPort"]+systemIndex, 'engine.autoreload.on': False, 'server.thread_pool' : 1})
    logging.info("Index %i booting on system %i",systemIndex,systemId)
    logging.info("Starting worker handler")
    jimi.workers.workers = jimi.workers.workerHandler()
    logging.debug("Garbage Collector %s",jimi.settings.getSetting("cache","garbageCollector"))
    scheduler = jimi.scheduler._scheduler(systemId,systemIndex)
    IndexHealthChecker = jimi.workers._threading(target=healthChecker,args=(scheduler,))
    IndexHealthChecker.start()
    logging.info("Starting scheduler")
    scheduler.handler()

if __name__ == "__main__":
    def startProcess(systemIndex):
        logging.debug("Starting index %i",systemIndex["systemIndex"])
        p = multiprocessing.Process(target=startWorker,args=(systemId,systemIndex["systemIndex"]))
        p.name = "jimi_worker"
        p.start()
        systemIndex["process"] = p
        systemIndex["pid"] = p.pid
        systemIndex["apiAddress"] = "http://{0}:{1}".format(workerAPISettings["bind"],workerAPISettings["startPort"]+systemIndex["systemIndex"])
        logging.debug("Started index %i, PID=%i API=%s:%i",systemIndex["systemIndex"],p.pid,workerAPISettings["bind"],workerAPISettings["startPort"]+systemIndex["systemIndex"])

    def healthChecker(cluster,systemIndexes):
        import os
        import time
        import psutil
        logging.info("Starting health checker")
        logging.debug("Garbage Collector %s",jimi.settings.getSetting("cache","garbageCollector"))
        # Waiting for startup
        time.sleep(10)
        while True:
            if jimi.settings.getSetting("cache","garbageCollector"):
                logging.debug("Running cache garbage collector")
                jimi.cache.globalCache.cleanCache()
            if jimi.workers.workers.lastHandle < time.time() - 60:
                logging.error("Workers on systemID %i has failed restarting",systemId)
                jimi.audit._audit().add("system","health_checker",{ "systemID" : systemId, "msg" : "Worker service has failed restarting." })
                jimi.workers.workers.stop()
                time.sleep(15)
                jimi.workers.workers.start()
                workerRestartSuccessful = False
                now = time.time() + 30
                while now > time.time():
                    if jimi.workers.workers.lastHandle > time.time() - 60:
                        workerRestartSuccessful = True
                        break
                    time.sleep(1)
                if not workerRestartSuccessful:
                    logging.error("Workers on systemID %i has failed and could not be restarted",systemId)
                    jimi.audit._audit().add("system","health_checker",{ "systemID" : systemId, "msg" : "Worker service has failed and could not be restarted." })
                    os._exit(10)
            if cluster.lastHandle < time.time() - 60:
                logging.error("Cluster service has failed")
                jimi.audit._audit().add("system","health_checker",{ "systemID" : systemId, "systemIndex" : systemIndex["systemIndex"], "msg" : "Cluster service has failed." })
                os._exit(25)
            auditData = []
            for systemIndex in systemIndexes:
                if not systemIndex["process"].is_alive(): 
                    logging.error("Index %i process has exitied, PID=%i",systemIndex["systemIndex"],systemIndex["pid"])
                    jimi.audit._audit().add("system","health_checker",{ "systemID" : systemId, "systemIndex" : systemIndex["systemIndex"], "pid" :systemIndex["pid"], "msg" : "Process has exitied and is being restarted." })
                    startProcess(systemIndex)
                else:
                    p = psutil.Process(pid=systemIndex["pid"])
                    cpu = p.cpu_percent(interval=1)
                    memory = p.memory_percent()
                    auditData.append({ "systemID" : systemId, "systemIndex" : systemIndex["systemIndex"], "pid" : systemIndex["pid"], "cpu" : cpu, "memory" : memory })
            jimi.audit._audit().add("system","performance",auditData)
            time.sleep(10)
    # Loading API - Has to be done before jimi import or the pages will not be loaded
    from core import api
    api.createServer("jimi_core")

    import os
    import jimi

    # Running installers
    logging.info("Running system startup installers")
    from system import install
    install.setup()

    # Load RSA information post jimi import / upgrade ( required for upgraded from 3.0 -> 3.1, should remove in future back to none function )
    jimi.auth.RSAinitialization()

    apiSettings = jimi.config["api"]["core"]
    workerAPISettings = jimi.config["api"]["worker"]

    systemId = jimi.cluster.getSystemId()
    logging.info("System starting system_id is %i",systemId)

    # File system integrity
    logging.info("Checking cluster integrity")
    checksum = jimi.system.fileIntegrityRegister()
    logging.debug("System integrity hash generated. hash=%s",checksum)
    masterId = jimi.cluster.getMasterId()
    clusterMember = jimi.cluster.getClusterMemberById(systemId)
    masterMember = jimi.cluster.getClusterMemberById(masterId)
    logging.info("Current jimi master is on %i",masterId)
    if masterMember and masterId != systemId and checksum != masterMember.checksum:
        logging.error("Checksum mismatch between system %i and master %i",systemId,masterId)
    if clusterMember:
        clusterMember.supportedModels = jimi.model.getLoadableModels()
        clusterMember.checksum = checksum
        clusterMember.update(["checksum","supportedModels"])

    # Starting API
    logging.info("Starting API interface")
    api.startServer(True,{'server.socket_host': apiSettings["bind"], 'server.socket_port': apiSettings["port"], 'engine.autoreload.on': False, 'server.thread_pool' : 10, 'server.max_request_body_size' : jimi.config["api"]["maxFileSize"], 'server.socket_timeout' : jimi.config["api"]["maxRequestTime"]})

    # Starting workers for API based calls - i.e. debug and triggering flows that are run on the master node
    logging.info("Starting cluster worker handler for API based calls")
    jimi.workers.workers = jimi.workers.workerHandler()

    # Starting workers
    try:
        cpuCount = jimi.config["system"]["max_workers"]
    except KeyError:
        cpuCount = os.cpu_count()
    jimi.cluster.systemIndexes = []
    logging.debug("Detected %i CPU",cpuCount)
    if cpuCount == 1:
        logging.info("Selected single cluster mode")
        jimi.cluster.systemIndexes.append({ "systemIndex" : 0 })
    else:
        logging.info("Selected multi cluster mode")
        for index in range(0,cpuCount):
            jimi.cluster.systemIndexes.append({ "systemIndex" : index })
    for systemIndex in jimi.cluster.systemIndexes:
        startProcess(systemIndex)

    cluster = jimi.cluster._cluster()
    SystemHealthChecker = jimi.workers._threading(target=healthChecker,args=(cluster,jimi.cluster.systemIndexes))
    SystemHealthChecker.start()
    logging.info("Starting cluster processing")
    cluster.handler()
else:
    if multiprocessing.current_process().name != "jimi_worker":
        import jimi
        # Load RSA information post jimi import / upgrade ( required for upgraded from 3.0 -> 3.1, should remove in future back to none function )
        jimi.auth.RSAinitialization()
        jimi.function.load()
        jimi.settings.cpuSaver["enabled"] = False
