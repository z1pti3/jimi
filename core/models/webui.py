from core import db

# Model Class
class _flowData(db._document):
    conductID = str()
    flowData = dict()

    _dbCollection = db.db["webui"]

    def new(self,conductID,flowData):
        self.conductID = conductID
        self.flowData = flowData
        # Run parent class function ( altunative to end decorator for the new function within a class )
        return super(_flowData, self).new()

# Model UI class
class _modelUI(db._document):
    conductID = str()
    flowID = str()
    x = int()
    y = int()
    title = str()

    _dbCollection = db.db["modelUI"]

    def new(self,conductID,acl,flowID,x,y,title=""):
        if len(_modelUI().query(query={"conductID" : conductID, "flowID" : flowID})["results"]) < 1:
            self.conductID = conductID
            self.acl = acl
            self.flowID = flowID
            self.x = x
            self.y = y
            self.title = title
            # Run parent class function ( altunative to end decorator for the new function within a class )
            return super(_modelUI, self).new()
        return False

# Class used to generate UI properties form
class _properties():
    def generate(self,classObject):
        def validate(text):
            return text

        formData = []
        blacklist = ["classID","workerID"]
        members = [attr for attr in dir(classObject) if not callable(getattr(classObject, attr)) and not "__" in attr and attr ]
        for member in members:
            if member not in blacklist:
                value = getattr(classObject,member)
                if type(value) == str or type(value) == int or type(value) == float:
                    formData.append({"type" : "input", "schemaitem" : member, "textbox" : value})
                elif type(value) == bool:
                    formData.append({"type" : "checkbox", "schemaitem" : member, "checked" : value})
                elif type(value) == dict or type(value) == list:
                    formData.append({"type" : "json-input", "schemaitem" : member, "textbox" : value})
        return formData

from core import helpers, logging