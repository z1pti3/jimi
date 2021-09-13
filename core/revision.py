import datetime
import jimi

class _revision(jimi.db._document):
    classID = str()
    objectID = str()
    objectData = dict()

    _dbCollection = jimi.db.db["revisions"]

    def new(self,object,fields=[],sessionData=None):
        # Force ACL for admin only
        self.acl = { "ids":[ { "accessID":"0","delete": True,"read": True,"write": True } ] }
        try:
            objectData = object.query(sessionData=sessionData,id=object._id,fields=fields)["results"][0]
            self.objectID = object._id
            self.objectData = objectData
            self.classID = object.classID
            super(_revision, self).new(sessionData=sessionData)
            return True
        except:
            return False

    def newCustomData(self,objectID,classID,objectData,sessionData=None):
        # Force ACL for admin only
        self.acl = { "ids":[ { "accessID":"0","delete": True,"read": True,"write": True } ] }
        self.objectID = objectID
        self.classID = classID
        self.objectData = objectData
        super(_revision, self).new(sessionData=sessionData)
        return True

    def gotRecent(self,objectID,classID,maxAge=300):
        dt = datetime.datetime.now() - datetime.timedelta(seconds=maxAge)
        if len(self.query(query={ "_id" : { "$gt" : jimi.db.ObjectId.from_datetime(generation_time=dt) }, "objectID" : objectID, "classID" : classID },fields=["_id"])["results"]) > 0:
            return True
        return False


######### --------- API --------- #########
if jimi.api.webServer:
    if not jimi.api.webServer.got_first_request:
        if jimi.api.webServer.name == "jimi_web":
            @jimi.api.webServer.route(jimi.api.base+"revisions/<classID>/<objectID>/", methods=["GET"])
            def getRevisions(classID,objectID):
                try:
                    # Checking that the requesting user has access to the object
                    objectClass = jimi.model._model().getAsClass(sessionData=jimi.api.g.sessionData,id=classID)[0].classObject()
                    objectClass = objectClass().getAsClass(sessionData=jimi.api.g.sessionData,id=objectID)[0]
                    if objectClass:
                        # No ACL check needed as we check the objects ACL
                        revisions = _revision().query(query={ "classID" : classID, "objectID" : objectID },sort=[("_id", -1)],limit=100,fields=["_id","creationTime","createdBy"])["results"]
                        # Get users from createdBy
                        userIDs = []
                        for revision in revisions:
                            if jimi.db.ObjectId(revision["createdBy"]) not in userIDs:
                                userIDs.append(jimi.db.ObjectId(revision["createdBy"]))
                        users = jimi.auth._user().query(query={ "_id" : { "$in" : userIDs } })["results"]
                        userHash = {}
                        for user in users:
                            userHash[user["_id"]] = user["name"]
                        for revision in revisions:
                            try:
                                revision["createdBy"] = userHash[revision["createdBy"]]
                            except KeyError:
                                revision["createdBy"] = "Unknown"
                        return { "revisions" : revisions }, 200
                except:
                    pass
                return { }, 404

            @jimi.api.webServer.route(jimi.api.base+"revisions/<classID>/<objectID>/<revisionID>/", methods=["GET"])
            def restoreRevision(classID,objectID,revisionID):
                try:
                    # Checking that the requesting user has access to the object
                    objectClass = jimi.model._model().getAsClass(sessionData=jimi.api.g.sessionData,id=classID)[0].classObject()
                    objectClass = objectClass().getAsClass(sessionData=jimi.api.g.sessionData,id=objectID)[0]
                    if objectClass:
                        if objectClass.__class__.__name__ != "_conduct":
                            # No ACL check needed as we check the objects ACL
                            revisionsToRestore = _revision().query(query={ "_id" : { "$gte" : jimi.db.ObjectId(revisionID) }, "classID" : classID, "objectID" : objectID },fields=["objectData"],sort=[("_id",-1)])["results"]
                            blacklist = ["classID","_id","acl"]
                            members = [attr for attr in dir(objectClass) if not callable(getattr(objectClass, attr)) and not "__" in attr and attr ]
                            fieldsUpdated = []
                            for revisionToRestore in revisionsToRestore:
                                for member in members:
                                    if member in revisionToRestore["objectData"] and member not in blacklist:
                                        if type(getattr(objectClass,member) == type(revisionToRestore["objectData"][member])):
                                            setattr(objectClass,member,revisionToRestore["objectData"][member])
                                            if member not in fieldsUpdated:
                                                fieldsUpdated.append(member)
                            objectClass.update(fieldsUpdated,sessionData=jimi.api.g.sessionData,revisioning=True)
                            return { }, 200
                except:
                    pass
                return { }, 404

            @jimi.api.webServer.route(jimi.api.base+"revisions/<classID>/<objectID>/<revisionID>/view/", methods=["GET"])
            def viewRevision(classID,objectID,revisionID):
                try:
                    # Checking that the requesting user has access to the object
                    objectClass = jimi.model._model().getAsClass(sessionData=jimi.api.g.sessionData,id=classID)[0].classObject()
                    objectClass = objectClass().getAsClass(sessionData=jimi.api.g.sessionData,id=objectID)[0]
                    if objectClass:
                        if objectClass.__class__.__name__ != "_conduct":
                            # No ACL check needed as we check the objects ACL
                            revisionsToRestore = _revision().query(query={ "_id" : { "$gte" : jimi.db.ObjectId(revisionID) }, "classID" : classID, "objectID" : objectID },fields=["objectData"],sort=[("_id",-1)])["results"]
                            blacklist = ["classID","_id","acl"]
                            members = [attr for attr in dir(objectClass) if not callable(getattr(objectClass, attr)) and not "__" in attr and attr ]
                            for revisionToRestore in revisionsToRestore:
                                for member in members:
                                    if member in revisionToRestore["objectData"] and member not in blacklist:
                                        if type(getattr(objectClass,member) == type(revisionToRestore["objectData"][member])):
                                            setattr(objectClass,member,revisionToRestore["objectData"][member])
                            return { "formData" : jimi.webui._properties().generate(objectClass) }, 200
                except:
                    pass
                return { }, 404