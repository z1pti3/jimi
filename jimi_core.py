import multiprocessing
import logging

logging.basicConfig(level=logging.WARNING)

def startWorker(systemId,systemIndex):
    def healthChecker(scheduler):
        import os
        logging.info("Starting health checker")
        try:
            cacheSettings = jimi.settings.config["cache"]
            garbageCollector = cacheSettings["garbageCollector"]
        except:
            garbageCollector = False
        logging.debug("Garbage Collector %s",garbageCollector)
        import time
        while True:
            if garbageCollector:
                logging.debug("Running cache garbage collector")
                jimi.cache.globalCache.cleanCache()
            if scheduler.lastHandle < time.time() - 60:
                logging.error("Scheduler on index %i has failed",systemIndex)
                os._exit(5)
            if jimi.workers.workers.lastHandle < time.time() - 60:
                logging.error("Workers on index %i has failed",systemIndex)
                os._exit(10)
            time.sleep(10)
    from core import settings, api
    workerAPISettings = settings.config["api"]["worker"]
    api.createServer("jimi_worker")
    import jimi
    jimi.function.load()
    api.startServer(True, host=workerAPISettings["bind"], port=workerAPISettings["startPort"]+systemIndex, threads=1)
    logging.info("Index %i booting on system %i",systemIndex,systemId)
    logging.info("Starting worker handler")
    jimi.workers.workers = jimi.workers.workerHandler()
    try:
        cacheSettings = jimi.settings.config["cache"]
        garbageCollector = cacheSettings["garbageCollector"]
    except:
        garbageCollector = False
    logging.debug("Garbage Collector %s",garbageCollector)
    scheduler = jimi.scheduler._scheduler(systemId,systemIndex)
    jimi.workers.workers.new("healthChecker",healthChecker,(scheduler,),True,0)
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
        logging.info("Starting health checker")
        try:
            cacheSettings = jimi.settings.config["cache"]
            garbageCollector = cacheSettings["garbageCollector"]
        except:
            garbageCollector = False
        logging.debug("Garbage Collector %s",garbageCollector)
        import time
        import psutil
        while True:
            if garbageCollector:
                logging.debug("Running cache garbage collector")
                jimi.cache.globalCache.cleanCache()
            if cluster.lastHandle < time.time() - 60:
                logging.error("Cluster service has failed")
                os._exit(25)
            for systemIndex in systemIndexes:
                if not systemIndex["process"].is_alive(): 
                    logging.error("Index %i process has exitied, PID=%i",systemIndex["systemIndex"],systemIndex["pid"])
                    startProcess(systemIndex)
                else:
                    p = psutil.Process(pid=systemIndex["pid"])
                    print("Index {0}, PID={1}, CPU={2}, MEM={3}".format(systemIndex["systemIndex"],systemIndex["pid"],p.cpu_percent(interval=1),p.memory_percent()))
            time.sleep(10)
    # Loading API - Has to be done before jimi import or the pages will not be loaded
    from core import settings, api
    apiSettings = settings.config["api"]["core"]
    workerAPISettings = settings.config["api"]["worker"]
    api.createServer("jimi_core")

    import os
    import jimi

    systemId = jimi.cluster.getSystemId()
    logging.info("System starting system_id is %i",systemId)

    # Running installers
    logging.info("Running system startup installers")
    from system import install
    install.setup()

    # File system integrity
    logging.info("Checking cluster integrity")
    checksum = jimi.system.fileIntegrityRegister()
    logging.debug("System integrity hash generated. hash=%s",checksum)
    masterId = jimi.cluster.getMasterId()
    clusterMember = jimi.cluster.getClusterMemberById(systemId)
    masterMember = jimi.cluster.getClusterMemberById(jimi.cluster.getMasterId())
    logging.info("Current jimi master is on %i",masterId)
    if masterId != systemId and checksum != masterMember.checksum:
        logging.debug("Fixing file integrity mismatch using master")
        checksum = jimi.system.fixChecksum(masterId)
        if checksum != masterMember.checksum:
            logging.error("Checksum mismatch between system %i and master %i",systemId,masterId)
    clusterMember.checksum = checksum
    clusterMember.update(["checksum"])

    # Starting API
    logging.info("Starting API interface")
    api.startServer(True,host=apiSettings["bind"], port=apiSettings["port"])

    # Starting workers for API based calls - i.e. debug and triggering flows that are run on the master node
    logging.info("Starting cluster worker handler for API based calls")
    jimi.workers.workers = jimi.workers.workerHandler()

    # Starting workers
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
    jimi.workers.workers.new("healthChecker",healthChecker,(cluster,jimi.cluster.systemIndexes),True,0)
    logging.info("Starting cluster processing")
    cluster.handler()
else:
    if multiprocessing.current_process().name != "jimi_worker":
        import jimi
        jimi.function.load()
        jimi.settings.config["cpuSaver"]["enabled"] = False
