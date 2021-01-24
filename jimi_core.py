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

    # Added self healing for core threads into this
    import time
    while True:
        time.sleep(1)