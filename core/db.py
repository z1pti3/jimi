import pymongo
import time
import functools
import copy
from bson.objectid import ObjectId
from threading import Lock

import jimi

# NOTE
# db class is a helper to expose some functions of mongoDB in an easy to use rapid dev way, this does not mean you
# have to use this helper for everything as the mongoDB driver is also exposed as self._dbcollection for your raw access needs.
# Remember if you go down the raw route you have to handle ACL yourself!!

# TODO
# Enable paging by default
# Support mongoDB sub document field selection i.e. data.type.name
# Add partial class loading and partial dict update support e.g. $pull, $push   

# DB Document Class
class _document():
    _id = str()
    classID = str()
    acl = dict()
    lastUpdateTime = int()
    creationTime = int()
    createdBy = str()

    def __init__(self):
        jimi.cache.globalCache.newCache("dbModelCache")

    # Wrapped mongo call that catches and retrys on error
    def mongoConnectionWrapper(func):
        @functools.wraps(func)
        def wrapper(inst, *args, **kwargs):
            while True:
                try:
                    return func(inst, *args, **kwargs)
                except (pymongo.errors.AutoReconnect, pymongo.errors.ServerSelectionTimeoutError) as e:
                    jimi.logging.debug("PyMongo auto-reconnecting... {0}. Waiting 1 second.".format(e),-10)
                    time.sleep(1)
        return wrapper

    # Create new object
    @mongoConnectionWrapper
    def new(self,sessionData=None):
        result = jimi.cache.globalCache.get("dbModelCache",self.__class__.__name__,getClassByName,sessionData=sessionData,extendCacheTime=True)
        if len(result) == 1:
            result = result[0]
            self.classID = result["_id"]
            self.creationTime = int(time.time())
            if sessionData:
                if not self.acl:
                    self.acl = { "ids" : [ { "accessID" : sessionData["primaryGroup"], "read" : True, "write" : True, "delete" : True } ] }
                self.createdBy = sessionData["_id"]
            result = self._dbCollection.insert_one(jimi.helpers.unicodeEscapeDict(self.parse()))
            self._id = result.inserted_id
            return result
        else:
            if jimi.logging.debugEnabled:
                jimi.logging.debug("Cannot create new document className='{0}' not found".format(self.__class__.__name__),3)
            return False

    def bulkNew(self,bulkClass,sessionData=None):
        result = jimi.cache.globalCache.get("dbModelCache",self.__class__.__name__,getClassByName,sessionData=sessionData,extendCacheTime=True)
        if len(result) == 1:
            result = result[0]
            self.classID = result["_id"]
            self.creationTime = int(time.time())
            bulkClass.newBulkOperaton(self._dbCollection.name,"insert",self)
            return self
        else:
            if jimi.logging.debugEnabled:
                jimi.logging.debug("Cannot create new document className='{0}' not found".format(self.__class__.__name__),3)
            return None

    # Converts jsonList into class - Seperate function to getAsClass so it can be overridden to support plugin loading for child classes
    def loadAsClass(self,jsonList,sessionData=None):
        result = []
        # Loading json data into class
        for jsonItem in jsonList:
            _class = copy.copy(self)
            result.append(jimi.helpers.jsonToClass(_class,jsonItem))
        return result

    # Get objects and return list as loaded class
    @mongoConnectionWrapper
    def getAsClass(self,sessionData=None,fields=[],query=None,id=None,limit=None,sort=None,skip=None):
        jsonResults = self.query(sessionData,fields,query,id,limit,sort,skip)["results"]
        return self.loadAsClass(jsonResults,sessionData=sessionData)
    
    # Get a object by ID
    def get(self,id):
        result = self.load(id)
        if not result:
            return None
        return self

    # Refresh data from database
    def refresh(self):
        queryResults = findDocumentByID(self._dbCollection,self._id)
        if queryResults:
            jimi.helpers.jsonToClass(self,queryResults)

    # Updated DB with latest values
    @mongoConnectionWrapper
    def update(self,fields,sessionData=None):
        if self._id != "" and "000000000001010000000000" not in str(self._id):
            if sessionData:
                for field in fields:
                    if not fieldACLAccess(sessionData,self.acl,field,"write"):
                        return False
            # Appendingh last update time to every update
            fields.append("lastUpdateTime")
            self.lastUpdateTime = time.time()

            update = { "$set" : {} }
            for field in fields:
                value = getattr(self,field)
                if type(value) is dict:
                    value = jimi.helpers.unicodeEscapeDict(value)
                update["$set"][field] = value

            result = updateDocumentByID(self._dbCollection,self._id,update)
            return result
        return False

    # Updated DB with latest values
    @mongoConnectionWrapper
    def bulkUpdate(self,fields,bulkClass,sessionData=None):
        if sessionData:
            for field in fields:
                if not fieldACLAccess(sessionData,self.acl,field,"write"):
                    return False
        # Appendingh last update time to every update
        fields.append("lastUpdateTime")
        self.lastUpdateTime = time.time()

        update = { "$set" : {} }
        for field in fields:
            value = getattr(self,field)
            if type(value) is dict:
                value = jimi.helpers.unicodeEscapeDict(value)
            update["$set"][field] = value

        bulkClass.newBulkOperaton(self._dbCollection.name,"update",{"_id" : self._id, "update" : update})

        # Updated DB with latest values
    @mongoConnectionWrapper
    def bulkUpsert(self,query,fields,bulkClass,sessionData=None,customUpdate=False):
        result = jimi.cache.globalCache.get("dbModelCache",self.__class__.__name__,getClassByName,sessionData=sessionData,extendCacheTime=True)
        if len(result) == 1:
            result = result[0]
            self.classID = result["_id"]
        else:
            return False
        if sessionData:
            for field in fields:
                if not fieldACLAccess(sessionData,self.acl,field,"write"):
                    return False

        if not customUpdate:
            # Appending last update time to every update
            fields.append("lastUpdateTime")
            self.lastUpdateTime = time.time()
            update = { "$set" : {} }
            for field in fields:
                value = getattr(self,field)
                if type(value) is dict:
                    value = jimi.helpers.unicodeEscapeDict(value)
                update["$set"][field] = value
        else:
            update = fields

        bulkClass.newBulkOperaton(self._dbCollection.name,"upsert",[query,update])
        
    # Parse class into json dict
    def parse(self,hidden=False):
        result = jimi.helpers.classToJson(self,hidden)
        return result

    # Parse DB dict into class
    @mongoConnectionWrapper
    def load(self,id):
        queryResults = findDocumentByID(self._dbCollection,id)
        if queryResults:
            jimi.helpers.jsonToClass(self,queryResults)
            return self
        else:
            return None

    # Delete loaded class from DB
    @mongoConnectionWrapper
    def delete(self):
        query = { "_id" : ObjectId(self._id) }
        result = self._dbCollection.delete_one(query)
        if result.deleted_count == 1:
            return { "result" : True, "count" : result.deleted_count }
        return { "result" : False, "count" : 0 }        

    @mongoConnectionWrapper
    def insert_one(self,data):
        self._dbCollection.insert_one(jimi.helpers.unicodeEscapeDict(data))

    def getAttribute(self,attr,sessionData=None):
        if not sessionData or fieldACLAccess(sessionData,self.acl,attr,accessType="read"):
            return getattr(self,attr)
        return None

    def setAttribute(self,attr,value,sessionData=None):
        if not sessionData or fieldACLAccess(sessionData,self.acl,attr,accessType="write"):
            setattr(self,attr,value)
            return True
        return False

    # API Calls - NONE LOADED CLASS OBJECTS <<<<<<<<<<<<<<<<<<<<<< Will need to support decorators to enable plugin support?
    @mongoConnectionWrapper
    def query(self,sessionData=None,fields=[],query=None,id=None,limit=None,sort=None,skip=None):
        result = { "results" : [] }
        if fields is None:
            fields = []
        # Ensure we pull required fields
        if len(fields) > 0:
            if "_id" not in fields:
                fields.append("_id")
            if "classID" not in fields:
                fields.append("classID")
            if "acl" not in fields:
                fields.append("acl")
        if id and not query:
            try:
                query = { "_id" : ObjectId(id) }
            except Exception as e:
                if jimi.logging.debugEnabled:
                    jimi.logging.debug("Error {0}".format(e))
                return result
        if not query:
            query = {}
        # Builds list of permitted ACL
        accessIDs = []
        adminBypass = False
        if sessionData and authSettings["enabled"]:
            if "admin" in sessionData:
                if sessionData["admin"]:
                    adminBypass = True
            if not adminBypass:
                accessIDs = sessionData["accessIDs"]
                # Adds ACL check to provided query to ensure requester is authorised and had read acess
                aclQuery = { "$or" : [ { "acl.ids.accessID" : { "$in" : accessIDs }, "acl.ids.read" : True }, { "acl.fields.ids.accessID" : { "$in" : accessIDs } }, { "acl" : { "$exists" : False } }, { "acl" : {} } ] }
                if "$and" in query:
                    query["$and"].append(aclQuery)
                elif "$or" in query:
                    query["$and"] = [ aclQuery ]
                else: 
                    query["$or"] = [ aclQuery ]
        # Base query
        docs = self._dbCollection.find(query)
        # Apply sorting
        if sort:
            docs.sort(sort)
        # Apply limits
        if limit:
            docs.limit(limit)    
        if skip:
            docs.skip(skip)                    
        # Sort returned data into json API response
        for doc in docs:
            resultItem = {}
            if len(fields) > 0:
                for field in fields:
                    if field in doc:
                        fieldAccessPermitted = True
                        # Checking if sessionData is permitted field level access
                        if "acl" in doc and not adminBypass and sessionData and authSettings["enabled"] and field not in ["classID","acl"]:
                            fieldAccessPermitted = fieldACLAccess(sessionData,doc["acl"],field)
                        # Allow field data to be returned if access is permitted
                        if fieldAccessPermitted:
                            value = jimi.helpers.handelTypes(doc[field])
                            if type(value) is dict:
                                value = jimi.helpers.unicodeUnescapeDict(value)
                            resultItem[jimi.helpers.unicodeUnescape(field)] = value
            else:
                for field in list(doc):
                    fieldAccessPermitted = True
                    # Checking if sessionData is permitted field level access
                    if "acl" in doc and not adminBypass and sessionData and authSettings["enabled"] and field not in ["classID","acl"]:
                        fieldAccessPermitted = fieldACLAccess(sessionData,doc["acl"],field)
                    # Allow field data to be returned if access is permitted
                    if fieldAccessPermitted:
                        value = jimi.helpers.handelTypes(doc[field])
                        if type(value) is dict:
                            value = jimi.helpers.unicodeUnescapeDict(value)
                        resultItem[jimi.helpers.unicodeUnescape(field)] = value
            if "_id" in resultItem:
                result["results"].append(resultItem)
        docs.close()
        return result

    @mongoConnectionWrapper
    def count(self,sessionData=None,query=None,id=None):
        result = { "results" : [] }
        if id and not query:
            try:
                query = { "_id" : ObjectId(id) }
            except Exception as e:
                if jimi.logging.debugEnabled:
                    jimi.logging.debug("Error {0}".format(e))
                return result
        if not query:
            query = {}
        # Builds list of permitted ACL
        accessIDs = []
        adminBypass = False
        if sessionData and authSettings["enabled"]:
            if "admin" in sessionData:
                if sessionData["admin"]:
                    adminBypass = True
            if not adminBypass:
                accessIDs = sessionData["accessIDs"]
                # Adds ACL check to provided query to ensure requester is authorised and had read acess
                aclQuery = { "$or" : [ { "acl.ids.accessID" : { "$in" : accessIDs }, "acl.ids.read" : True }, { "acl" : { "$exists" : False } }, { "acl" : {} } ] }
                if "$and" in query:
                    query["$and"].append(aclQuery)
                elif "$or" in query:
                    query["$and"] = [ aclQuery ]
                else: 
                    query["$or"] = [ aclQuery ]
        # Base query
        count = self._dbCollection.count(query)    
        #return count           
        result["results"].append({"count" : count})
        return result

    @mongoConnectionWrapper
    def api_getByModelName(self,modelName):
        classID = jimi.model.getClassID(modelName)
        if classID:
            return self.query(query={ "classID" : classID })
        return { "results" : [] }

    @mongoConnectionWrapper
    def api_delete(self,query=None,id=None):
        if id and not query:
            try:
                query = { "_id" : ObjectId(id) }
                result = self._dbCollection.delete_one(query)
                if result.deleted_count == 1:
                    return { "result" : True, "count" : result.deleted_count }
            except Exception as e:
                if jimi.logging.debugEnabled:
                    jimi.logging.debug("Error {0}".format(e))
        elif query and not id:
            try:
                result = self._dbCollection.delete_many(query)
                if result.deleted_count > 0:
                    return { "result" : True, "count" : result.deleted_count }
            except Exception as e:
                if jimi.logging.debugEnabled:
                    jimi.logging.debug("Error {0}".format(e))
        return { "result" : False, "count" : 0 }

    @mongoConnectionWrapper
    def api_update(self,query={},update={}):
        if "_id" in query:
            try:
                query["_id"] = ObjectId(query["_id"])
            except Exception as e:
                if jimi.logging.debugEnabled:
                    jimi.logging.debug("Error {0}".format(e))

        result = self._dbCollection.update_many(query,update)
        return { "result" : True, "count" :  result.modified_count }

    @mongoConnectionWrapper
    def api_add(self,postData):
        newObj = {}
        schema = self.api_getSchema()
        for key, value in schema.items():
            if key in postData:
                if type(postData[key]).__name__ == value:
                    newObj[key] == postData[key]
        if newObj != {}:
            result = _dbCollection.insert_one(newObj)
            return { "result" : True, "id" : result.inserted_id }

        return { "result" : False }

    @mongoConnectionWrapper
    def api_getSchema(self):
        result = {}
        for key, value in self.parse(True).items():
            result[key] = type(value).__name__
        return result

class _paged():
    def __init__(self,dbClass,sessionData=None,fields=[],query=None,sort=None,maxResults=100):
        self.dbClass = dbClass
        self.sessionData = sessionData
        self.fields = fields
        self.query = query
        self.sort = sort
        self.maxResults = maxResults
        self.total = self.count()
        self.pages = int(self.total / self.maxResults)
        
    def count(self):
        return self.dbClass().count(sessionData=self.sessionData,query=self.query)

    def get(self,page=0):
        return self.dbClass().getAsClass(sessionData=self.sessionData,query=self.query,sort=self.sort,limit=self.maxResults,skip=int(page*self.maxResults))

class _bulk():
    def __init__(self,processPollTime=10):
        self.bulkOperatons = {}
        self.processPollTime = processPollTime
        self.nextPoll = time.time() + self.processPollTime
        self.lock = Lock()

    def __del__(self):
        self.bulkOperatonProcessing()

    def tick(self):
        if self.nextPoll < time.time():
            self.bulkOperatonProcessing()
            self.nextPoll = time.time() + self.processPollTime

    def bulkOperatonProcessing(self):
        self.lock.acquire()
        cpuSaver = jimi.helpers.cpuSaver()
        for bulkOperatonCollection, bulkOperatonMethod in self.bulkOperatons.items():
            # Insert
            bulkInsert = []
            for insert in bulkOperatonMethod["insert"]:
                bulkInsert.append(jimi.helpers.unicodeEscapeDict(insert.parse()))
                cpuSaver.tick()
            if len(bulkInsert) > 0:
                collection = db[bulkOperatonCollection]
                results = collection.insert_many(bulkInsert)
                for index,item in enumerate(results.inserted_ids):
                    bulkOperatonMethod["insert"][index]._id = str(item)
                    cpuSaver.tick()
                bulkOperatonMethod["insert"] = []
            # Update
            if len(bulkOperatonMethod["update"]) > 0:
                bulkUpdate = db[bulkOperatonCollection].initialize_unordered_bulk_op()
                for update in bulkOperatonMethod["update"]:
                    bulkUpdate.find({ "_id" : ObjectId(update["_id"]) }).update_one(update["update"])
                    cpuSaver.tick()
                bulkUpdate.execute()
                bulkOperatonMethod["insert"] = []
            # Upsert
            if len(bulkOperatonMethod["upsert"]) > 0:
                upsertArray = []
                for upsert in bulkOperatonMethod["upsert"]:
                    upsertArray.append(pymongo.UpdateOne(upsert[0], upsert[1], upsert=True))
                    cpuSaver.tick()
                bulkUpdate = db[bulkOperatonCollection].bulk_write(upsertArray)
                bulkOperatonMethod["upsert"] = []
        self.lock.release()

    def newBulkOperaton(self,collection,method,value):
        self.lock.acquire()
        if collection not in self.bulkOperatons:
            self.bulkOperatons[collection] = { "insert" : [], "update" : [], "upsert" : [] }
        self.bulkOperatons[collection][method].append(value)
        self.lock.release()


mongodbSettings = jimi.settings.config["mongodb"]
authSettings = jimi.settings.config["auth"]

dbClient = pymongo.MongoClient(mongodbSettings["hosts"],username=mongodbSettings["username"],password=mongodbSettings["password"])

db = dbClient[mongodbSettings["db"]]

# DB Helper Functions
def list_collection_names():
    return db.list_collection_names()

# Checks if access to a field is permitted by the object ACL
def fieldACLAccess(sessionData,acl,field,accessType="read"):
    if not authSettings["enabled"]:
        return True
    accessIDs= []
    access = False
    adminBypass = False
    if sessionData:
        adminBypass = False
        if "admin" in sessionData:
            if sessionData["admin"]:
                adminBypass = True
                access = True
        if not adminBypass:
            accessIDs = sessionData["accessIDs"]
        if "fields" in acl:
            fieldAcls = []
            for fieldAcl in acl["fields"]:
                for aclId in fieldAcl["ids"]:
                    if aclId["accessID"] in accessIDs:
                        fieldAcls.append(fieldAcl)        
            if len(fieldAcls) == 0:
                return True
            # Checking if the sessionData permits access to the given ACL
            for fieldAcl in fieldAcls:
                if fieldAcl["field"] == field:
                    for accessID in fieldAcl["ids"]:
                        if accessID["accessID"] in accessIDs and accessID[accessType]:
                            return True
        else:
            if not acl and not adminBypass:
                return False
            access, accessIDs, adminBypass = ACLAccess(sessionData,acl,accessType)
            return access
    return False

# Checks if access to the object is permitted by the object ACL
def ACLAccess(sessionData,acl,accessType="read"):
    if not authSettings["enabled"]:
        return [ True, [], False ]
    accessIDs = []
    access = False
    adminBypass = False
    if sessionData:
        adminBypass = False
        if "admin" in sessionData:
            if sessionData["admin"]:
                adminBypass = True
                access = True
        if not adminBypass:
            accessIDs = sessionData["accessIDs"]
            if acl:
                if "ids" in acl:
                    for aclItem in acl["ids"]:
                        for accessID in accessIDs:
                            if aclItem["accessID"] == accessID:
                                access = aclItem[accessType]
    return [ access, accessIDs, adminBypass ]


# Update DB item within giben collection by ID
def updateDocumentByID(dbCollection,id,update):
    query = { "_id" : ObjectId(id) }
    queryResults = dbCollection.update_one(query, update)
    return queryResults

# Get DB item within given collection by ID
def findDocumentByID(dbCollection,id):
    query = { "_id" : ObjectId(id) }
    queryResults = dbCollection.find_one(query)
    return queryResults

# Delete database
def delete():
    dbClient.drop_database(mongodbSettings["db"]) 

def getClassByName(match,sessionData):
    return jimi.model._model().query(query={"className" : match})["results"]
