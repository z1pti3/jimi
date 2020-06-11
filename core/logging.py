import time
import json
import uuid
import inspect

from core import settings

debugSettings = settings.config["debug"]
filter = ""
buffer = []
debugClients = []

class _debug():
    _id = str()
    buffer = list()
    filter = str()
    level = int()
    debugExpire = int()
    fullstack = bool()

    def __init__(self):
        self._id = str(uuid.uuid4())
        self.debugExpire = int(time.time()) + 60 # sets debugger for 60 seconds timeout
        self.fullstack = False
        self.level = -1

    def fetch(self):
        self.debugExpire = int(time.time()) + 60 # sets debugger for 60 seconds timeout
        result = self.buffer
        self.buffer = []
        return result

    def log(self,msg):
        self.buffer.insert(0,msg)
        if len(self.buffer) > debugSettings["buffer"]:
            self.buffer.pop()


def debug(msg,level=98,fullstack=True):
    global filter
    global debugClients
    display = False
    if debugSettings["level"] >= level:
        display = True
        if filter:
            if filter in msg:
                display = True
            else:
                display = False
        if display:
            if fullstack:
                print()
                fullstackMsg = "{0} : {1}".format(msg,inspect.stack()[1])
                print(fullstackMsg)
            else:
                print(msg)

    # Sending logs to debug clients
    if len(debugClients) > 0:
        currentTime = time.time()
        poplist = []
        for debugClient in debugClients:
            if debugClient.debugExpire >= currentTime:
                if debugClient.level >= level:
                    display = True
                    if debugClient.filter:
                        if debugClient.filter not in msg:
                            display = False

                    if display and debugClient.fullstack:
                        fullstackMsg = "{0} : {1}".format(msg,inspect.stack()[1])
                        debugClient.log(fullstackMsg)
                    elif display:
                        debugClient.log(msg)
            else:
                poplist.append(debugClient)
        # Deleting expired debugClients
        for pop in poplist:
            debugClients.remove(pop)


from core import api, helpers, settings

######### --------- API --------- #########
# Possible access by non-admin users? - this needs to be checked attmped to use same function for both jimi-web and jimi-core ( maybe a bad idea )
if not api.webServer.got_first_request:
    @api.webServer.route(api.base+"debug/", methods=["POST"])
    def newDebug():
        global debugClients
        if "admin" in api.g["sessionData"]:
            if api.g["sessionData"]["admin"]:
                apiEndpoint = "debug/"
                data = json.loads(api.request.data)
                apiResult = helpers.apiCall("POST",apiEndpoint,jsonData=data).text
                return json.loads(apiResult), 200
        elif api.webServer.name == "jimi_core":
            if not settings.config["auth"]["enabled"]:
                data = json.loads(api.request.data)
                debugClient = _debug()
                if "filter" in data:
                    debugClient.filter = data["filter"]
                if "fullStack" in data:
                    debugClient.fullstack = data["fullStack"]
                if "level" in data:
                    debugClient.level = data["level"]
                debugClients.append(debugClient)
                return { "debugID" : debugClient._id }, 200
        return { }, 404

    @api.webServer.route(api.base+"debug/<debugID>/", methods=["GET"])
    def getDebug(debugID):
        global debugClients
        if "admin" in api.g["sessionData"]:
            if api.g["sessionData"]["admin"]:
                apiEndpoint = "debug/{0}/".format(debugID)
                apiResult = helpers.apiCall("GET",apiEndpoint).text
                return apiResult, 200
        elif api.webServer.name == "jimi_core":
            if not settings.config["auth"]["enabled"]:
                debugClient = None
                for tempDebugClient in debugClients:
                    if tempDebugClient._id == debugID:
                        debugClient = tempDebugClient
                        break
                if debugClient:
                    return { "result" : debugClient.fetch() }, 200
        return { }, 404
