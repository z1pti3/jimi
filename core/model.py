import os
import json
from pathlib import Path

from core import db

# Initialize
dbCollectionName = "model"

class _model(db._document):
    name = str()
    className = str()
    classType = str()
    location = str()
    hidden = bool()

    _dbCollection = db.db[dbCollectionName]

    def new(self,name,className,classType,location,hidden):
        self.name = name
        self.className = className
        self.classType = classType
        self.location = location
        self.hidden = hidden
        self.acl = { "ids":[ { "accessID":"0","delete": True,"read": True,"write": True } ] }
        return super(_model, self).new()

    def classObject(self):
        # ClassID wont exist if the className is model
        try:
            mod = __import__("{0}".format(self.location), fromlist=["{0}".format(self.className)])
        except ModuleNotFoundError:
            logging.debug("Error unable to find class='{0}', className='{1}', classType='{2}', location='{3}'".format(self.classID,self.className,self.classType,self.location),2)
            return None
        class_ = getattr(mod, "{0}".format(self.className))
        return class_

from core import api, logging, audit, helpers

from core.models import conduct

def registerModel(name,className,classType,location,hidden=False):
    # Checking that a model with the same name does not already exist ( this is due to identification within GUI, future changes could be made to allow this?? )
    results = _model().query(query={ "name" : name })["results"]
    if len(results) == 0:
        return _model().new(name,className,classType,location,hidden)
    else:
        logging.debug("Register model failed as it already exists modelName='{0}', className='{1}', classType='{2}', location='{3}'".format(name,className,classType,location),4)

def deregisterModel(name,className,classType,location):
    loadModels = _model().query(query={ "name" : name})["results"]
    if loadModels:
        loadModels = loadModels[0]
        # This really does need to clean up the models objects that are left
        #from core.models import trigger, action
        #trigger._action().api_delete(query={"classID" : ObjectId(loadModels["_id"]) })
        #action._action().api_delete(query={"classID" : ObjectId(loadModels["_id"]) })
        results = _model().api_delete(query={ "name" : name, "classType" : classType })
        if results["result"]:
            return True
    logging.debug("deregister model failed modelName='{0}', className='{1}', classType='{2}', location='{3}'".format(name,className,classType,location),4)

def getClassID(name):
    loadModels = _model().query(query={ "name" : name})["results"]
    if loadModels:
        loadModels = loadModels[0]
        return loadModels["_id"]
    return None

def loadModel(modelName):
    results = _model().query(query={ "name" : modelName })["results"]
    if len(results) == 1:
        results = results[0]
        _class = _model().get(results["_id"])
        return _class
    return None

def getClassObject(classID,sessionData):
    return _model().getAsClass(sessionData,id=classID)

######### --------- API --------- #########
if api.webServer:
    if not api.webServer.got_first_request:
        @api.webServer.route(api.base+"models/", methods=["GET"])
        def getModels():
            result = []
            api.g.sessionData
            models = _model().query(api.g.sessionData,query={ "_id" : { "$exists": True } })["results"]
            for model in models:
                result.append(model["name"])
            return { "models" : result }, 200

        @api.webServer.route(api.base+"models/<modelName>/", methods=["GET"])
        def getModel(modelName):
            class_ = loadModel(modelName).classObject()
            if class_:
                results = _model().query(query={ "className" : class_.__name__ })["results"]
                if len(results) == 1:
                    results = results[0]
                    return class_().query(api.g.sessionData,query={ "classID" : results["_id"] },fields=["_id","name","classType"]), 200
            return {}, 404

        @api.webServer.route(api.base+"models/<modelName>/extra/", methods=["GET"])
        def getModelExtra(modelName):
            class_ = loadModel(modelName).classObject()
            if class_:
                results = _model().query(query={ "className" : class_.__name__ })["results"]
                if len(results) == 1:
                    results = results[0]
                    results = class_().query(api.g.sessionData,query={ "classID" : results["_id"] },fields=["_id","name","classType","lastUpdateTime"])["results"]
                    ids = [ x["_id"] for x in results ]
                    # Possible for ID trigger and action to be the same ( although unlikey but keep in mind this could be an issue in future )
                    ConductsCache = conduct._conduct().query(query={ "$or" : [ { "flow.triggerID" : { "$in" : ids } }, { "flow.actionID" : { "$in" : ids } } ] },fields=["_id","name","flow"])["results"]
                    for result in results:
                        usedIn = []
                        for ConductCache in ConductsCache:
                            for flow in ConductCache["flow"]:
                                if "triggerID" in flow:
                                    if flow["triggerID"] == result["_id"]:
                                        usedIn.append({ "conductID" :  ConductCache["_id"], "conductName" : ConductCache["name"] })
                                if "actionID" in flow:
                                    if flow["actionID"] == result["_id"]:
                                        usedIn.append({ "conductID" :  ConductCache["_id"], "conductName" : ConductCache["name"] })
                        result["whereUsed"] = usedIn
                    return { "results" : results }, 200
            return {}, 404

        @api.webServer.route(api.base+"models/<modelName>/all/", methods=["GET"])
        def getModelAndChildren(modelName):
            class_ = loadModel(modelName).classObject()
            classIDs = []
            if class_:
                results = _model().query(query={ "className" : class_.__name__ })["results"]
                if len(results) == 1:
                    results = results[0]
                    classIDs.append(results["_id"])
                    results = _model().query(query={ "classType" : results["className"] })["results"]
                    for result in results:
                        classIDs.append(result["_id"])

                    result = []
                    for classID in classIDs:
                        for foundObject in class_().query(api.g.sessionData,query={ "classID" : classID },fields=["_id","name"])["results"]:
                            result.append(foundObject)

                    return { "results" : result}, 200
            else:
                return {}, 404

        @api.webServer.route(api.base+"models/<modelName>/schema/", methods=["GET"])
        def getModelSchema(modelName):
            class_ = loadModel(modelName)
            if class_:
                access, accessIDs, adminBypass = db.ACLAccess(api.g.sessionData,class_.acl,"read")
                if access:
                    return class_.classObject()().api_getSchema(), 200
                else:
                    return {}, 403
            else:
                return {}, 404

        @api.webServer.route(api.base+"models/<modelName>/<objectID>/", methods=["GET"])
        def getModelObject(modelName,objectID):
            class_ = loadModel(modelName).classObject()
            if class_:
                result = class_().query(api.g.sessionData,id=objectID)
                if result["results"]:
                    return result, 200
                else:
                    return {}, 404
            else:
                return {}, 404

        @api.webServer.route(api.base+"models/<modelName>/<objectID>/", methods=["DELETE"])
        def deleteModelObject(modelName,objectID):
            class_ = loadModel(modelName)
            if class_:
                _class = class_.classObject()().getAsClass(api.g.sessionData,id=objectID)
                if len(_class) == 1:
                    _class = _class[0]
                    access, accessIDs, adminBypass = db.ACLAccess(api.g.sessionData,_class.acl,"delete")
                    if access:
                        if "_id" in api.g.sessionData:
                            audit._audit().add("model","delete",{ "_id" : api.g.sessionData["_id"], "user" : api.g.sessionData["user"], "modelName" : modelName, "objectID" : objectID })
                        else:
                            audit._audit().add("model","delete",{ "user" : "system", "objectID" : objectID })
                        result = class_.classObject()().api_delete(id=objectID)
                        if result["result"]:
                            return result, 200
                    else:
                        return {}, 403
            return {}, 404

        @api.webServer.route(api.base+"models/<modelName>/", methods=["PUT"])
        def newModelObject(modelName):
            class_ = loadModel(modelName)
            if class_:
                access, accessIDs, adminBypass = db.ACLAccess(api.g.sessionData,class_.acl,"read")
                if access:
                    class_ = class_.classObject()()
                    if api.g.sessionData:
                        class_.acl = { "ids" : [ { "accessID" : api.g.sessionData["primaryGroup"], "read" : True, "write" : True, "delete" : True } ] }
                    newObjectID = super(type(class_), class_).new().inserted_id
                    if "_id" in api.g.sessionData:
                        audit._audit().add("model","create",{ "_id" : api.g.sessionData["_id"], "user" : api.g.sessionData["user"], "modelName" : modelName, "objectID" : str(newObjectID) })
                    else:
                        audit._audit().add("model","create",{ "user" : "system", "objectID" : str(newObjectID) })
                    return { "result" : { "_id" : str(newObjectID) } }, 200
            return {}, 404

        @api.webServer.route(api.base+"models/<modelName>/<objectID>/", methods=["POST"])
        def updateModelObject(modelName,objectID):
            class_ = loadModel(modelName)
            if class_:
                data = json.loads(api.request.data)
                if data["action"] == "update":
                    updateItemsList = []
                    changeLog = {}
                    data = data["data"]
                    _class = class_.classObject()().getAsClass(api.g.sessionData,id=objectID)
                    if len(_class) == 1:
                        _class = _class[0]
                        # Builds list of permitted ACL
                        access, accessIDs, adminBypass = db.ACLAccess(api.g.sessionData,_class.acl,"write")
                        if access:
                            for dataKey, dataValue in data.items():
                                fieldAccessPermitted = True
                                # Checking if sessionData is permitted field level access
                                if _class.acl != {} and not adminBypass:
                                    fieldAccessPermitted = db.fieldACLAccess(api.g.sessionData,_class.acl,dataKey,"write")

                                if fieldAccessPermitted:
                                    # _id is a protected mongodb object and cant be updated
                                    if dataKey != "_id":
                                        if hasattr(_class, dataKey):
                                            changeLog[dataKey] = {}
                                            changeLog[dataKey]["currentValue"] = getattr(_class, dataKey)
                                            if type(getattr(_class, dataKey)) is str:
                                                if _class.setAttribute(dataKey, str(dataValue),sessionData=api.g.sessionData):
                                                    updateItemsList.append(dataKey)
                                                    changeLog[dataKey]["newValue"] = getattr(_class, dataKey)
                                            elif type(getattr(_class, dataKey)) is int:
                                                try:
                                                    if _class.setAttribute(dataKey, int(dataValue),sessionData=api.g.sessionData):
                                                        updateItemsList.append(dataKey)
                                                        changeLog[dataKey]["newValue"] = getattr(_class, dataKey)
                                                except ValueError:
                                                    if _class.setAttribute(dataKey, 0,sessionData=api.g.sessionData):
                                                        updateItemsList.append(dataKey)
                                                        changeLog[dataKey]["newValue"] = getattr(_class, dataKey)
                                            elif type(getattr(_class, dataKey)) is float:
                                                try:
                                                    if _class.setAttribute(dataKey, float(dataValue),sessionData=api.g.sessionData):
                                                        updateItemsList.append(dataKey)
                                                        changeLog[dataKey]["newValue"] = getattr(_class, dataKey)
                                                except ValueError:
                                                    if _class.setAttribute(dataKey, 0,sessionData=api.g.sessionData):
                                                        updateItemsList.append(dataKey)
                                                        changeLog[dataKey]["newValue"] = getattr(_class, dataKey)
                                            elif type(getattr(_class, dataKey)) is bool:
                                                # Convert string object to bool
                                                if type(dataValue) is str:
                                                    if dataValue.lower() == "true":
                                                        dataValue = True
                                                    else:
                                                        dataValue = False
                                                if _class.setAttribute(dataKey, dataValue,sessionData=api.g.sessionData):
                                                    updateItemsList.append(dataKey)
                                                    changeLog[dataKey]["newValue"] = getattr(_class, dataKey)
                                            elif type(getattr(_class, dataKey)) is dict or type(getattr(_class, dataKey)) is list:
                                                if dataValue:
                                                    if _class.setAttribute(dataKey, json.loads(dataValue),sessionData=api.g.sessionData):
                                                        updateItemsList.append(dataKey)
                                                        changeLog[dataKey]["newValue"] = getattr(_class, dataKey)
                            # Commit back to database
                            if updateItemsList:
                                # Adding audit record
                                if "_id" in api.g.sessionData:
                                    audit._audit().add("model","update",{ "_id" : api.g.sessionData["_id"], "user" : api.g.sessionData["user"], "objects" : helpers.unicodeEscapeDict(changeLog), "modelName" : modelName, "objectID" : objectID })
                                else:
                                    audit._audit().add("model","update",{ "user" : "system", "objects" : helpers.unicodeEscapeDict(changeLog), "modelName" : modelName, "objectID" : objectID })
                                _class.update(updateItemsList)
                            return {}, 200
                        else:
                            return {}, 403
            return {}, 404
