import logging
import requests

import jimi

######### --------- API --------- #########
if jimi.api.webServer:
    if not jimi.api.webServer.got_first_request:
        if jimi.api.webServer.name == "jimi_core":
            @jimi.api.webServer.route(jimi.api.base+"admin/clearCache/", methods=["GET"])
            @jimi.auth.adminEndpoint
            def api_clearCache():
                jimi.cache.globalCache.clearCache("ALL")
                results = [{ "system" : jimi.cluster.getSystemId(), "status_code" : 200 }]
                apiToken = jimi.auth.generateSystemSession()
                headers = { "X-api-token" : apiToken }
                for systemIndex in jimi.cluster.systemIndexes:
                    url = systemIndex["apiAddress"]
                    apiEndpoint = "admin/clearCache/"
                    try:
                        response = requests.get("{0}{1}{2}".format(url,jimi.api.base,apiEndpoint),headers=headers, timeout=10)
                        if response.status_code == 200:
                            results.append({ "system" : jimi.cluster.getSystemId(), "index" : systemIndex["systemIndex"], "status_code" : response.status_code })
                    except:
                        logging.warning("Unable to access {0}{1}{2}".format(url,jimi.api.base,apiEndpoint))
                return { "results" : results }, 200

            @jimi.api.webServer.route(jimi.api.base+"admin/clearStartChecks/", methods=["GET"])
            @jimi.auth.adminEndpoint
            def api_clearStartChecks():
                from system import install
                install.resetTriggers()
                return { "result" : True }, 200

        if jimi.api.webServer.name == "jimi_worker":
            @jimi.api.webServer.route(jimi.api.base+"admin/clearCache/", methods=["GET"])
            @jimi.auth.systemEndpoint
            def api_clearCache():
                jimi.cache.globalCache.clearCache("ALL")
                return { "result" : True }, 200
