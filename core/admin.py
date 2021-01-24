import jimi

######### --------- API --------- #########
if jimi.api.webServer:
    if not jimi.api.webServer.got_first_request:
        if jimi.api.webServer.name == "jimi_core":
            @jimi.api.webServer.route(jimi.api.base+"admin/clearCache/", methods=["GET"])
            @jimi.auth.adminEndpoint
            def api_clearCache():
                jimi.cache.globalCache.clearCache("ALL")
                return { "result" : True }, 200

            @jimi.api.webServer.route(jimi.api.base+"admin/clearStartChecks/", methods=["GET"])
            @jimi.auth.adminEndpoint
            def api_clearStartChecks():
                from system import install
                install.resetTriggers()
                return { "result" : True }, 200
