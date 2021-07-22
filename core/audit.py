import datetime
import time, json
from pathlib import Path
from bson import json_util,ObjectId

import jimi

# Initialize 

dbCollectionName = "audit"

# audit Class
class _audit(jimi.db._document):
    _dbCollection = jimi.db.db[dbCollectionName]

    def new():
        pass

    def get():
        pass

    def update():
        pass

    def load():
        pass

    def delete():
        pass

    def parse():
        pass

    def add(self,eventSource, eventType, eventData):
        result = None
        auditData = { "time" : time.time(), "systemID" : systemSettings["systemID"], "source" : eventSource, "type" : eventType, "data" : eventData }
        try:
            if auditSettings["db"]["enabled"]:
                writeLog = True
                if "eventSources" in auditSettings["db"]:
                    if eventSource not in auditSettings["db"]["eventSources"]:
                        writeLog = False
                # Override for testTrigger
                if "000000000001010000000000" in eventData["conductID"]:
                    writeLog = True
                if writeLog:
                    result = self._dbCollection.insert_one(jimi.helpers.unicodeEscapeDict(auditData))
        except KeyError:
            pass
        try:
            if auditSettings["file"]["enabled"]:
                writeLog = True
                if "eventSources" in auditSettings["file"]:
                    if eventSource not in auditSettings["file"]["eventSources"]:
                        writeLog = False

                if writeLog:
                    filename = "{0}{1}{2}.txt".format(datetime.date.today().day,datetime.date.today().month,datetime.date.today().year)
                    logFile = Path("{0}/{1}".format(auditSettings["file"]["logdir"],filename))
                    with open(logFile, "a") as logFile:
                        logLine = "{0}\r\n".format(json.loads(json_util.dumps(auditData))).replace(": True",": true").replace(": False",": false").replace(": None",": null")
                        logFile.write(logLine)
        except KeyError:
            pass
        if result is not None:
            if jimi.logging.debugEnabled:
                jimi.logging.debug("Writing audit item, auditID={0}, auditData='{1}'".format(str(result.inserted_id),auditData))
        return result

auditSettings = jimi.settings.getSetting("audit",None)
systemSettings = jimi.settings.getSetting("system",None)