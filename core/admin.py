import jimi

######### --------- API --------- #########
if jimi.api.webServer:
    if not jimi.api.webServer.got_first_request:
        if jimi.api.webServer.name == "jimi_core":
            @jimi.api.webServer.route(jimi.api.base+"admin/clearCache/", methods=["GET"])
            @jimi.auth.systemEndpoint
            def api_clearCache():
                if jimi.api.g.sessionData["admin"]:
                    jimi.cache.globalCache.clearCache("ALL")
                    return { "result" : True }, 200
                return { "result" : False }, 403
