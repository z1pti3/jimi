if __name__ == "__main__":
    # Setup and define API ( required before other modules )
    from core import api, settings
    apiSettings = settings.config["api"]["core"]
    api.createServer("jimi_core")

    # Core imports
    from core import workers, plugin, scheduler, cluster, settings, screen, model, helpers, auth, flow

    api.startServer(debug=True, use_reloader=False, host=apiSettings["bind"], port=apiSettings["port"], threaded=True)

    import time
    time.sleep(1)

    # Running setup
    from system import install
    install.setup()
    install.resetTriggers()

    # Auto start the application using its API
    apiEndpoint = "workers/"
    apiToken = auth.generateSystemSession()
    helpers.apiCall("POST",apiEndpoint,{"action" : "start"},token=apiToken)
    apiEndpoint = "scheduler/"
    helpers.apiCall("POST",apiEndpoint,{"action" : "start"},token=apiToken)
    apiEndpoint = "cluster/"
    helpers.apiCall("POST",apiEndpoint,{"action" : "start"},token=apiToken)

    # Loading main screen
    from core.screens import mainScreen
    screen = mainScreen.mainScreen()
else:
    # Prevent circular import of DB
    from core import model
    