from core import api, cache

######### --------- API --------- #########
if api.webServer:
    if not api.webServer.got_first_request:
        @api.webServer.route(api.base+"admin/clearCache/", methods=["GET"])
        def api_clearCache():
            if api.g.sessionData["admin"]:
                cache.globalCache.clearCache("ALL")
                return { "result" : True }, 200
            return { "result" : False }, 403
