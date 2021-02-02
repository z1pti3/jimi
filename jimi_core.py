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
        if jimi.workers.workers.lastHandle + 60 < now:
            jimi.audit._audit().add("core","crash",{ "action" : "restart", "type" : "workers" })
            print("worker thread has crashed!")
            apiEndpoint = "workers/"
            apiToken = jimi.auth.generateSystemSession()
            jimi.helpers.apiCall("POST",apiEndpoint,{"action" : "start"},token=apiToken)
        if jimi.scheduler.scheduler.lastHandle + 60 < now:
            jimi.audit._audit().add("core","crash",{ "action" : "restart", "type" : "scheduler" })
            print("scheduler thread has crashed!")
            apiEndpoint = "scheduler/"
            apiToken = jimi.auth.generateSystemSession()
            jimi.helpers.apiCall("POST",apiEndpoint,{"action" : "start"},token=apiToken)
        if jimi.cluster.cluster.lastHandle + 60 < now:
            jimi.audit._audit().add("core","crash",{ "action" : "restart", "type" : "cluster" })
            print("cluster thread has crashed!")
            apiEndpoint = "cluster/"
            apiToken = jimi.auth.generateSystemSession()
            jimi.helpers.apiCall("POST",apiEndpoint,{"action" : "start"},token=apiToken)
        time.sleep(10)