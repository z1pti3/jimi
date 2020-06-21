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
        self.conductID = conductID
        self.acl = acl
        self.flowID = flowID
        self.x = x
        self.y = y
        self.title = title
        # Run parent class function ( altunative to end decorator for the new function within a class )
        return super(_modelUI, self).new()

# Class used to generate UI properties form
class _properties():
    def generate(self,classObject):
        def validate(text):
            return text
        def label(text):
            return "<label>{0}</label>".format(text)
        def textbox(id,value):
            return "<input class='inputFullWidth' type='text' id='properties_items{0}' value='{1}'></input>".format(id,value)
        def textarea(id,value):
            return "<input class='inputFullWidth' type='textarea' id='properties_items{0}' value='{1}'></input>".format(id,value)
        def checkbox(id,value):
            if value:
                return "<input type='checkbox' id='properties_items{0}' checked='{1}'></input>".format(id,value)
            return "<input type='checkbox' id='properties_items{0}'></input>".format(id)

        formData = []
        blacklist = ["acl","classID","workerID"]
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