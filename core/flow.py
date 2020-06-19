import json

from core import api

def executeFlow(events,codifyData):
    outputText = ""
    
    return outputText

######### --------- API --------- #########
if api.webServer:
    if not api.webServer.got_first_request:
        @api.webServer.route(api.base+"codify/run/", methods=["POST"])
        def codifyRun():
            data = json.loads(api.request.data)
            result = executeFlow(data["events"],data["code"])
            return { "result" : result }, 200

