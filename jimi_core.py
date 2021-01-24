if __name__ == "__main__":
    from core import settings, api

    apiSettings = settings.config["api"]["core"]
    api.createServer("jimi_core")
    api.startServer(debug=True, use_reloader=False, host=apiSettings["bind"], port=apiSettings["port"], threaded=True)

    import jimi

    import time
    time.sleep(1)

    # Running setup
    from system import install
    install.setup()

    # Auto start the application using its API
    apiEndpoint = "workers/"
    apiToken = jimi.auth.generateSystemSession()
    jimi.helpers.apiCall("POST",apiEndpoint,{"action" : "start"},token=apiToken)
    apiEndpoint = "scheduler/"
    jimi.helpers.apiCall("POST",apiEndpoint,{"action" : "start"},token=apiToken)
    apiEndpoint = "cluster/"
    jimi.helpers.apiCall("POST",apiEndpoint,{"action" : "start"},token=apiToken)

    # Loading main screen
    from core.screens import mainScreen
    screen = mainScreen.mainScreen()
    