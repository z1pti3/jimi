import jimi

class _revision(jimi.db._document):
    collection = str()
    objectId = str()
    objectData = dict()

    _dbCollection = jimi.db.db["revisions"]

    def new(self,object,fields=[],sessionData=None):
        try:
            objectData = object.query(sessionData=sessionData,id=object._id,fields=fields)["results"][0]
            self.objectId = object._id
            self.acl = object.acl
            self.objectData = objectData
            self.collection = object._dbCollection.name
            super(_revision, self).new(sessionData=sessionData)
            return True
        except:
            return False
