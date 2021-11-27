import datetime
import time, json
from pathlib import Path
from bson import json_util,ObjectId

import jimi

# audit Class
class _audit(jimi.db._document):
    _dbCollection = jimi.db.db["audit"]

    def add(self, eventSource, eventType, data):
        auditData = { "time" : time.time(), "systemID" : systemSettings["systemID"], "source" : eventSource, "type" : eventType, "data" : data }
        try:
            if auditSettings["db"]["enabled"]:
                self._dbCollection.insert_one(jimi.helpers.unicodeEscapeDict(auditData))
        except KeyError:
            self._dbCollection.insert_one(jimi.helpers.unicodeEscapeDict(auditData))
        try:
            if auditSettings["file"]["enabled"]:
                filename = "{0}{1}{2}.txt".format(datetime.date.today().day,datetime.date.today().month,datetime.date.today().year)
                logFile = Path("{0}/{1}".format(auditSettings["file"]["logdir"],filename))
                with open(logFile, "a") as logFile:
                    logLine = "{0}\r\n".format(json.loads(json_util.dumps(auditData))).replace(": True",": true").replace(": False",": false").replace(": None",": null")
                    logFile.write(logLine)
        except KeyError:
            pass

auditSettings = jimi.settings.getSetting("audit",None)
systemSettings = jimi.config["system"]