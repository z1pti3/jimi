if __name__ == "__main__":
    from core import settings, api

    # Create webserver so we can load all routes before starting
    apiSettings = settings.config["api"]["core"]
    api.createServer("jimi_core")

    import jimi

    # Running setup
    from system import install
    install.setup()

    # Start server now loading is completed
    api.startServer(debug=True, use_reloader=False, host=apiSettings["bind"], port=apiSettings["port"], threaded=True)
    import time
    time.sleep(5)

    # Auto start the application using its API
    apiEndpoint = "workers/"
    apiToken = jimi.auth.generateSystemSession()
    jimi.helpers.apiCall("POST",apiEndpoint,{"action" : "start"},token=apiToken)
    apiEndpoint = "scheduler/"
    jimi.helpers.apiCall("POST",apiEndpoint,{"action" : "start"},token=apiToken)
    apiEndpoint = "cluster/"
    jimi.helpers.apiCall("POST",apiEndpoint,{"action" : "start"},token=apiToken)

    import time
    time.sleep(10)
    if jimi.workers.workers.lastHandle == None:
        print("Failed to start workers")
    if jimi.cluster.cluster.lastHandle == None:
        print("Failed to start cluster")
    if jimi.scheduler.scheduler.lastHandle == None:
        print("Failed to start scheduler")
    while True:
        now = time.time()
        try:
            if jimi.workers.workers.lastHandle + 60 < now:
                print("worker thread has crashed!")
                jimi.audit._audit().add("core","crash",{ "action" : "restart", "type" : "workers" })
                apiEndpoint = "workers/"
                apiToken = jimi.auth.generateSystemSession()
                jimi.helpers.apiCall("POST",apiEndpoint,{"action" : "start"},token=apiToken)
        except ValueError:
            print("worker thread not running!")
            jimi.audit._audit().add("core","notrunning",{ "action" : "restart", "type" : "workers" })
        try:
            if jimi.scheduler.scheduler.lastHandle + 60 < now:
                jimi.audit._audit().add("core","crash",{ "action" : "restart", "type" : "scheduler" })
                print("scheduler thread has crashed!")
                apiEndpoint = "scheduler/"
                apiToken = jimi.auth.generateSystemSession()
                jimi.helpers.apiCall("POST",apiEndpoint,{"action" : "start"},token=apiToken)
        except ValueError:
            print("scheduler thread not running!")
            jimi.audit._audit().add("core","notrunning",{ "action" : "restart", "type" : "scheduler" })
        try:
            if jimi.cluster.cluster.lastHandle + 60 < now:
                jimi.audit._audit().add("core","crash",{ "action" : "restart", "type" : "cluster" })
                print("cluster thread has crashed!")
                apiEndpoint = "cluster/"
                apiToken = jimi.auth.generateSystemSession()
                jimi.helpers.apiCall("POST",apiEndpoint,{"action" : "start"},token=apiToken)
        except ValueError:
            print("cluster thread not running!")
            jimi.audit._audit().add("core","notrunning",{ "action" : "restart", "type" : "cluster" })
        time.sleep(10)
else:
    import jimi
    # Disable CPU saver for multiprocessing
    jimi.settings.config["cpuSaver"]["enabled"] = False