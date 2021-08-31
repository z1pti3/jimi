import datetime
from re import L
import jimi

class _revision(jimi.db._document):
    collection = str()
    objectId = str()
    objectData = dict()

    _dbCollection = jimi.db.db["revisions"]

    def new(self,object,fields=[],sessionData=None):
        # Force ACL for admin only
        self.acl = { "ids":[ { "accessID":"0","delete": True,"read": True,"write": True } ] }
        try:
            objectData = object.query(sessionData=sessionData,id=object._id,fields=fields)["results"][0]
            self.objectId = object._id
            self.objectData = objectData
            self.collection = object._dbCollection.name
            super(_revision, self).new(sessionData=sessionData)
            return True
        except:
            return False

    def newCustomData(self,objectId,collection,objectData,sessionData=None):
        # Force ACL for admin only
        self.acl = { "ids":[ { "accessID":"0","delete": True,"read": True,"write": True } ] }
        self.objectId = objectId
        self.collection = collection
        self.objectData = objectData
        super(_revision, self).new(sessionData=sessionData)
        return True

    def gotRecent(self,objectId,collection,maxAge=300):
        dt = datetime.datetime.now() - datetime.timedelta(seconds=maxAge)
        if len(self.query(query={ "_id" : { "$gt" : jimi.db.ObjectId.from_datetime(generation_time=dt) }, "objectId" : objectId, "collection" : collection },fields=["_id"])["results"]) > 0:
            return True
        return False