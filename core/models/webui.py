import jimi

# Model Class
class _flowData(jimi.db._document):
    conductID = str()
    flowData = dict()

    _dbCollection = jimi.db.db["webui"]

    def new(self,conductID,flowData):
        self.conductID = conductID
        self.flowData = flowData
        # Run parent class function ( alterative to end decorator for the new function within a class )
        return super(_flowData, self).new()

# Editor UI Class
class _editorUI(jimi.db._document):
    currentUsers = dict()
    objectType = str()
    objectId = str()

    _dbCollection = jimi.db.db["editorUI"]

    def new(self,objectId,objectType):
        if len(_editorUI().query(query={"objectId" : objectId, "objectType" : objectType})["results"]) == 0:
            self.objectId = objectId
            self.objectType = objectType
            self.acl = {"ids":[{"accessID":0,"delete":True,"read":True,"write":True}]}
            # Run parent class function ( alterative to end decorator for the new function within a class )
            return super(_editorUI, self).new()
        return False

# Model UI Class - Could be converted into a single DB item per conduct and use mongoDB to handle document updates?
class _modelUI(jimi.db._document):
    conductID = str()
    flowID = str()
    x = int()
    y = int()
    title = str()

    _dbCollection = jimi.db.db["modelUI"]

    def new(self,conductID,acl,flowID,x,y,title=""):
        if len(_modelUI(False).query(query={"conductID" : conductID, "flowID" : flowID})["results"]) < 1:
            self.conductID = conductID
            self.acl = acl
            self.flowID = flowID
            self.x = x
            self.y = y
            self.title = title
            # Run parent class function ( alterative to end decorator for the new function within a class )
            return super(_modelUI, self).new()
        return False

# Class used to generate UI properties form
class _properties():
    def generate(self,classObject):
        formData = []
        if classObject.manifest__:
            if len(classObject.manifest__["fields"]) > 0:
                systemFields = ["_id","name","enabled","log","concurrency","threaded","executionSnapshot","startTime","schedule","maxDuration","logicString","varDefinitions","comment"]
                formData.append({"type" : "break", "schemaitem" : "break", "start" : True, "label" : "System"})
                for field in systemFields:
                    try:
                        value = getattr(classObject,field)
                        if type(value) == str or type(value) == int or type(value) == float:
                            formData.append({"type" : "input", "schemaitem" : field, "textbox" : value, "label" : field})
                        elif type(value) == bool:
                            formData.append({"type" : "checkbox", "schemaitem" : field, "checked" : value, "label" : field})
                        elif type(value) == dict or type(value) == list:
                            formData.append({"type" : "json-input", "schemaitem" : field, "textbox" : value, "label" : field})
                    except AttributeError:
                        pass
                formData.append({"type" : "break", "schemaitem" : "break", "start" : False, "label" : "System"})
                formData.append({"type" : "break", "schemaitem" : "break", "start" : True, "label" : classObject.name})
                for field in classObject.manifest__["fields"]:
                    if field["schema_item"] not in systemFields:
                        if field["schema_value"][-2:] == "()":
                            field["value"] = getattr(classObject, field["schema_value"][:-2])()
                            field["schemaitem"] = field["schema_item"][:-2]
                        else:
                            field["value"] = getattr(classObject,field["schema_value"])
                            field["schemaitem"] = field["schema_item"]
                        if type(field["value"]) is str or type(field["value"]) is int or type(field["value"]) is float:
                            field["textbox"] = field["value"]
                        elif type(field["value"]) is bool:
                            field["checked"] = field["value"]
                        elif type(field["value"]) is dict or type(field["value"]) is list:
                            field["textbox"] = field["value"]
                        elif field["type"] == "dropdown":
                            field["current"] = field["value"]
                        if field["type"] == "unit-input":
                            field["currentunit"] = getattr(classObject,field["unitschema"])
                        field["tooltip"] = field["description"]
                        formData.append(field)
                formData.append({"type" : "break", "schemaitem" : "break", "start" : False, "label" : classObject.name})
                return formData
        
        # Old method
        blacklist = ["classID","workerID","acl","lastUpdateTime","creationTime","createdBy","attemptCount","autoRestartCount","startCheck","scope","clusterSet","lastCheck","startTime","systemIndex","systemID","nextCheck","failOnActionFailure","autoRestartDelay","systemCrashHandler","partialResults"]
        members = [attr for attr in dir(classObject) if not callable(getattr(classObject, attr)) and not "__" in attr and attr ]
        for member in members:
            if member not in blacklist:
                value = getattr(classObject,member)
                if type(value) == str or type(value) == int or type(value) == float:
                    formData.append({"type" : "input", "schemaitem" : member, "textbox" : value, "label" : member})
                elif type(value) == bool:
                    formData.append({"type" : "checkbox", "schemaitem" : member, "checked" : value, "label" : member})
                elif type(value) == dict or type(value) == list:
                    formData.append({"type" : "json-input", "schemaitem" : member, "textbox" : value, "label" : member})
        return formData
