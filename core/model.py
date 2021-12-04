import os
import json
from pathlib import Path

import jimi

# Initialize
dbCollectionName = "model"

class _model(jimi.db._document):
    name = str()
    className = str()
    classType = str()
    location = str()
    hidden = bool()
    manifest = dict()

    _dbCollection = jimi.db.db[dbCollectionName]

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
            jimi.logging.debug("Error unable to find class='{0}', className='{1}', classType='{2}', location='{3}'".format(self.classID,self.className,self.classType,self.location),-1)
            if self.classType == "_action":
                return jimi.action._action
            elif self.classType == "_trigger":
                return jimi.trigger._trigger
            else:
                return jimi.db._document
            
        class_ = getattr(mod, "{0}".format(self.className))
        # Injecting manifest from model into the loaded class - this is only held in memory and never committed to the database
        class_.manifest__ = self.manifest
        return class_

def registerModel(name,className,classType,location,hidden=False):
    # Checking that a model with the same name does not already exist ( this is due to identification within GUI, future changes could be made to allow this?? )
    results = _model(False).query(query={ "name" : name })["results"]
    if len(results) == 0:
        return _model().new(name,className,classType,location,hidden)
    else:
        if jimi.logging.debugEnabled:
            jimi.logging.debug("Register model failed as it already exists modelName='{0}', className='{1}', classType='{2}', location='{3}'".format(name,className,classType,location),4)

def deregisterModel(name,className,classType,location):
    loadModels = _model(False).query(query={ "name" : name})["results"]
    if loadModels:
        loadModels = loadModels[0]
        # This really does need to clean up the models objects that are left
        #from core.models import trigger, action
        #trigger._action().api_delete(query={"classID" : ObjectId(loadModels["_id"]) })
        #action._action().api_delete(query={"classID" : ObjectId(loadModels["_id"]) })
        results = _model().api_delete(query={ "name" : name, "classType" : classType })
        if results["result"]:
            return True
    if jimi.logging.debugEnabled:
        jimi.logging.debug("deregister model failed modelName='{0}', className='{1}', classType='{2}', location='{3}'".format(name,className,classType,location),4)

def getLoadableModels():
    loadableModels = []
    models = _model(False).getAsClass(query={})
    for modelObject in models:
        try:
            mod = __import__("{0}".format(modelObject.location), fromlist=["{0}".format(modelObject.className)])
            class_ = getattr(mod, "{0}".format(modelObject.className))
            if class_:
                loadableModels.append(modelObject._id)
        except:
            pass
    return loadableModels

def getClassID(name):
    loadModels = _model(False).query(query={ "name" : name})["results"]
    if loadModels:
        loadModels = loadModels[0]
        return loadModels["_id"]
    return None

def loadModel(modelName):
    results = _model(False).query(query={ "name" : modelName })["results"]
    if len(results) == 1:
        results = results[0]
        _class = _model().get(results["_id"])
        return _class
    return None

def getClassObject(classID,sessionData):
    return _model().getAsClass(id=classID)

######### --------- API --------- #########
if jimi.api.webServer:
    if not jimi.api.webServer.got_first_request:
        if jimi.api.webServer.name == "jimi_web":
            @jimi.api.webServer.route(jimi.api.base+"models/", methods=["GET"])
            def getModels():
                result = []
                jimi.api.g.sessionData
                models = _model(False).query(jimi.api.g.sessionData,query={ "_id" : { "$exists": True } })["results"]
                for model in models:
                    result.append(model["name"])
                return { "models" : result }, 200

            @jimi.api.webServer.route(jimi.api.base+"models/<modelName>/", methods=["GET"])
            def getModel(modelName):
                class_ = loadModel(modelName).classObject()
                if class_:
                    results = _model(False).query(jimi.api.g.sessionData,query={ "className" : class_.__name__ })["results"]
                    if len(results) == 1:
                        results = results[0]
                        return class_().query(jimi.api.g.sessionData,query={ "classID" : results["_id"] },fields=["_id","name","classType"]), 200
                return {}, 404

            @jimi.api.webServer.route(jimi.api.base+"models/<modelName>/extra/", methods=["GET"])
            def getModelExtra(modelName):
                class_ = loadModel(modelName).classObject()
                if class_:
                    results = _model(False).query(jimi.api.g.sessionData,query={ "className" : class_.__name__ })["results"]
                    if len(results) == 1:
                        results = results[0]
                        results = class_(False).query(jimi.api.g.sessionData,query={ "classID" : results["_id"] },fields=["_id","name","classType","lastUpdateTime"])["results"]
                        ids = [ x["_id"] for x in results ]
                        # Possible for ID trigger and action to be the same ( although unlikey but keep in mind this could be an issue in future )
                        ConductsCache = jimi.conduct._conduct().query(query={ "$or" : [ { "flow.triggerID" : { "$in" : ids } }, { "flow.actionID" : { "$in" : ids } } ] },fields=["_id","name","flow"])["results"]
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

            @jimi.api.webServer.route(jimi.api.base+"models/<modelName>/all/", methods=["GET"])
            def getModelAndChildren(modelName):
                class_ = loadModel(modelName).classObject()
                classIDs = []
                if class_:
                    results = _model(False).query(jimi.api.g.sessionData,query={ "className" : class_.__name__ })["results"]
                    if len(results) == 1:
                        results = results[0]
                        classIDs.append(results["_id"])
                        results = _model(False).query(jimi.api.g.sessionData,query={ "classType" : results["className"] })["results"]
                        for result in results:
                            classIDs.append(result["_id"])

                        result = []
                        for classID in classIDs:
                            for foundObject in class_(False).query(jimi.api.g.sessionData,query={ "classID" : classID })["results"]:
                                result.append(foundObject)

                        return { "results" : result}, 200
                else:
                    return {}, 404

            @jimi.api.webServer.route(jimi.api.base+"models/<modelName>/schema/", methods=["GET"])
            def getModelSchema(modelName):
                class_ = loadModel(modelName)
                if class_:
                    access = jimi.db.ACLAccess(jimi.api.g.sessionData,class_.acl,"read")
                    if access:
                        return class_.classObject()(False).api_getSchema(), 200
                    else:
                        return {}, 403
                else:
                    return {}, 404

            @jimi.api.webServer.route(jimi.api.base+"models/<modelName>/<objectID>/", methods=["GET"])
            def getModelObject(modelName,objectID):
                class_ = loadModel(modelName).classObject()
                if class_:
                    classObject = class_(False).getAsClass(jimi.api.g.sessionData,id=objectID)
                    if classObject:
                        classObject = classObject[0]
                        members = jimi.helpers.classToJson(classObject)
                        return members, 200
                    else:
                        return {}, 404
                else:
                    return {}, 404

            @jimi.api.webServer.route(jimi.api.base+"models/<modelName>/<objectID>/", methods=["DELETE"])
            def deleteModelObject(modelName,objectID):
                class_ = loadModel(modelName)
                if class_:
                    _class = class_.classObject()(False).getAsClass(jimi.api.g.sessionData,id=objectID)
                    if len(_class) == 1:
                        _class = _class[0]
                        access = jimi.db.ACLAccess(jimi.api.g.sessionData,_class.acl,"delete")
                        if access:
                            if "_id" in jimi.api.g.sessionData:
                                jimi.audit._audit().add("model","delete",{ "_id" : jimi.api.g.sessionData["_id"], "user" : jimi.api.g.sessionData["user"], "modelName" : modelName, "objectID" : objectID })
                            else:
                                jimi.audit._audit().add("model","delete",{ "user" : "system", "objectID" : objectID })
                            result = class_.classObject()(False).api_delete(id=objectID)
                            if result["result"]:
                                return result, 200
                        else:
                            return {}, 403
                return {}, 404

            @jimi.api.webServer.route(jimi.api.base+"models/<modelName>/", methods=["PUT"])
            def newModelObject(modelName):
                class_ = loadModel(modelName)
                if class_:
                    access = jimi.db.ACLAccess(jimi.api.g.sessionData,class_.acl,"read")
                    if access:
                        class_ = class_.classObject()(False)
                        if jimi.api.g.sessionData:
                            class_.acl = { "ids" : [ { "accessID" : jimi.api.g.sessionData["primaryGroup"], "read" : True, "write" : True, "delete" : True } ] }
                        newObjectID = super(type(class_), class_).new().inserted_id
                        if "_id" in jimi.api.g.sessionData:
                            jimi.audit._audit().add("model","create",{ "_id" : jimi.api.g.sessionData["_id"], "user" : jimi.api.g.sessionData["user"], "modelName" : modelName, "objectID" : str(newObjectID) })
                        else:
                            jimi.audit._audit().add("model","create",{ "user" : "system", "objectID" : str(newObjectID) })
                        return { "_id" : str(newObjectID) }, 200
                return {}, 404

            @jimi.api.webServer.route(jimi.api.base+"models/<modelName>/<objectID>/", methods=["POST"])
            def updateModelObject(modelName,objectID):
                class_ = loadModel(modelName)
                if class_:
                    data = json.loads(jimi.api.request.data)
                    updateItemsList = []
                    changeLog = {}
                    _class = class_.classObject()(False).getAsClass(jimi.api.g.sessionData,id=objectID)
                    if len(_class) == 1:
                        _class = _class[0]
                        # Builds list of permitted ACL
                        access = jimi.db.ACLAccess(jimi.api.g.sessionData,_class.acl,"write")
                        adminBypass = False
                        if "admin" in jimi.api.g.sessionData:
                            if jimi.api.g.sessionData["admin"]:
                                adminBypass = True
                        if access:
                            for dataKey, dataValue in data.items():
                                fieldAccessPermitted = True
                                # Checking if sessionData is permitted field level access
                                
                                if _class.acl != {} and not adminBypass:
                                    fieldAccessPermitted = jimi.db.fieldACLAccess(jimi.api.g.sessionData,_class.acl,dataKey,"write")

                                if fieldAccessPermitted:
                                    # _id is a protected mongodb object and cant be updated
                                    if dataKey != "_id":
                                        if hasattr(_class, dataKey):
                                            changeLog[dataKey] = {}
                                            changeLog[dataKey]["currentValue"] = getattr(_class, dataKey)
                                            if type(getattr(_class, dataKey)) is str:
                                                if _class.setAttribute(dataKey, str(dataValue),sessionData=jimi.api.g.sessionData):
                                                    updateItemsList.append(dataKey)
                                                    changeLog[dataKey]["newValue"] = getattr(_class, dataKey)
                                            elif type(getattr(_class, dataKey)) is int:
                                                try:
                                                    if _class.setAttribute(dataKey, int(dataValue),sessionData=jimi.api.g.sessionData):
                                                        updateItemsList.append(dataKey)
                                                        changeLog[dataKey]["newValue"] = getattr(_class, dataKey)
                                                except ValueError:
                                                    if _class.setAttribute(dataKey, 0,sessionData=jimi.api.g.sessionData):
                                                        updateItemsList.append(dataKey)
                                                        changeLog[dataKey]["newValue"] = getattr(_class, dataKey)
                                            elif type(getattr(_class, dataKey)) is float:
                                                try:
                                                    if _class.setAttribute(dataKey, float(dataValue),sessionData=jimi.api.g.sessionData):
                                                        updateItemsList.append(dataKey)
                                                        changeLog[dataKey]["newValue"] = getattr(_class, dataKey)
                                                except ValueError:
                                                    if _class.setAttribute(dataKey, 0,sessionData=jimi.api.g.sessionData):
                                                        updateItemsList.append(dataKey)
                                                        changeLog[dataKey]["newValue"] = getattr(_class, dataKey)
                                            elif type(getattr(_class, dataKey)) is bool:
                                                # Convert string object to bool
                                                if type(dataValue) is str:
                                                    if dataValue.lower() == "true":
                                                        dataValue = True
                                                    else:
                                                        dataValue = False
                                                if _class.setAttribute(dataKey, dataValue,sessionData=jimi.api.g.sessionData):
                                                    updateItemsList.append(dataKey)
                                                    changeLog[dataKey]["newValue"] = getattr(_class, dataKey)
                                            elif type(getattr(_class, dataKey)) is dict or type(getattr(_class, dataKey)) is list:
                                                if dataValue:
                                                    if _class.setAttribute(dataKey, json.loads(dataValue),sessionData=jimi.api.g.sessionData):
                                                        updateItemsList.append(dataKey)
                                                        changeLog[dataKey]["newValue"] = getattr(_class, dataKey)
                            # Commit back to database
                            if updateItemsList:
                                # Adding audit record
                                if "_id" in jimi.api.g.sessionData:
                                    jimi.audit._audit().add("model","update",{ "_id" : jimi.api.g.sessionData["_id"], "user" : jimi.api.g.sessionData["user"], "objects" : changeLog, "modelName" : modelName, "objectID" : objectID })
                                else:
                                    jimi.audit._audit().add("model","update",{ "user" : "system", "objects" : changeLog, "modelName" : modelName, "objectID" : objectID })
                                _class.update(updateItemsList,sessionData=jimi.api.g.sessionData,revisioning=True)
                            return {}, 200
                        else:
                            return {}, 403
                return {}, 404
