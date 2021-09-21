import time
import copy
import logging

import jimi

class _cache:
    objects = dict()

    def __init__(self,maxSize=10485760,cacheExpiry=60):
        self.maxSize = maxSize
        self.cacheExpiry = cacheExpiry

    # Max size not implimented yet
    def newCache(self,cacheName,maxSize=None,cacheExpiry=None,sessionData=None):
        if maxSize == None:
            maxSize = self.maxSize
        if cacheExpiry == None:
            cacheExpiry = self.cacheExpiry
        userID = None
        if sessionData:
            if "_id" in sessionData:
                userID = sessionData["_id"]
                cacheName = "{0},-,{1}".format(userID,cacheName)
        if cacheName not in self.objects:
            self.objects[cacheName] = { "objects" : {}, "maxSize" : maxSize, "cacheExpiry" : cacheExpiry, "userID" : userID }
            logging.debug("New cache store created, name={0}, maxSize={1}, cacheExpry={2}, userID={3}".format(cacheName,maxSize,cacheExpiry,userID))

    def updateCacheSettings(self,cacheName,maxSize=None,cacheExpiry=None,sessionData=None):
        if cacheName in self.objects:
            if maxSize:
                self.objects[cacheName]["maxSize"] = maxSize
            if cacheExpiry:
                self.objects[cacheName]["cacheExpiry"] = cacheExpiry
        else:
            self.newCache(cacheName,maxSize,cacheExpiry,sessionData)

    def clearCache(self,cacheName,sessionData=None):
        authedCacheName = self.checkSessionData(cacheName,sessionData)
        if authedCacheName == None:
            return
        if cacheName == "ALL":
            for cacheName, cacheValue in self.objects.items():
                self.objects[cacheName]["objects"].clear()
        elif authedCacheName in self.objects:
            self.objects[authedCacheName]["objects"].clear()
            logging.debug("Cache store cleared, name={0}".format(authedCacheName))

    def cleanCache(self):
        now = time.time()
        index = 0
        keys = list(self.objects.keys())
        while index < len(self.objects):
            try:
                cacheItem = self.objects[keys[index]]
                popList = []
                for cacheObjectItem in cacheItem["objects"].items():
                    if cacheObjectItem[1]["cacheExpiry"] < now:
                        popList.append(cacheObjectItem[0])
                for popItem in popList:
                        del cacheItem["objects"][popItem]
            except IndexError:
                pass
            index += 1
        
    # BUG this function does not check for size so it would be possible to go over the defined max memory size -- Add this at a later date
    def sync(self,objects):
        for cacheKey, cacheValue in objects.items():
                if cacheKey not in self.objects:
                    self.objects[cacheKey] = cacheValue
                else:
                    for objectKey, objectValue in objects[cacheKey].items():
                        if objectKey not in self.objects:
                            objects[cacheKey][objectKey] = objectValue

    def export(self):
        c = copy.deepcopy(self.objects)
        return c
    
    def getAll(self,cacheName,sessionData=None):
        authedCacheName = self.checkSessionData(cacheName,sessionData)
        if authedCacheName == None:
            return
        return self.objects[authedCacheName]["objects"]

    def delete(self,cacheName,uid,sessionData=None):
        authedCacheName = self.checkSessionData(cacheName,sessionData)
        if authedCacheName == None:
            return
        if uid in self.objects[authedCacheName]["objects"]:
            del self.objects[authedCacheName]["objects"][uid]

    def update(self,cacheName,uid,objectValue,sessionData=None):
        authedCacheName = self.checkSessionData(cacheName,sessionData)
        if authedCacheName == None:
            return
        if uid in self.objects[authedCacheName]["objects"]:
            self.objects[authedCacheName]["objects"][uid]["objectValue"] = objectValue

    def insert(self,cacheName,uid,objectValue,sessionData=None,customCacheTime=None):
        authedCacheName = self.checkSessionData(cacheName,sessionData)
        if authedCacheName == None:
            return
        now = time.time()
        if authedCacheName not in self.objects:
            self.newCache(authedCacheName)
        cacheExpiry = self.objects[authedCacheName]["cacheExpiry"]
        if customCacheTime != None:
            cacheExpiry = customCacheTime
        self.objects[authedCacheName]["objects"][uid] = { "objectValue" : objectValue, "accessCount" : 0, "cacheExpiry" : (now + cacheExpiry) }
        return True

    def append(self,cacheName,uid,appendValue,sessionData=None):
        authedCacheName = self.checkSessionData(cacheName,sessionData)
        if authedCacheName == None:
            return
        if uid in self.objects[authedCacheName]["objects"]:
            self.objects[authedCacheName]["objects"][uid]["objectValue"].append(appendValue)

    def appendDict(self,cacheName,uid,appendKey,appendValue,sessionData=None):
        authedCacheName = self.checkSessionData(cacheName,sessionData)
        if authedCacheName == None:
            return
        if uid in self.objects[authedCacheName]["objects"]:
            self.objects[authedCacheName]["objects"][uid]["objectValue"][appendKey] = appendValue

    def get(self,cacheName,uid,setFunction,*args,sessionData=None,extendCacheTime=False,customCacheTime=None,forceUpdate=False,nullUpdate=False,dontCheck=False):
        authedCacheName = self.checkSessionData(cacheName,sessionData)
        if authedCacheName == None:
            return
        now = time.time()
        if not forceUpdate:
            try:
                objectCache = self.objects[authedCacheName]["objects"][uid]
                if ((objectCache["cacheExpiry"] > now) or (extendCacheTime)):
                    if extendCacheTime:
                        if not customCacheTime:
                            objectCache["cacheFor"] = ( now + self.objects[authedCacheName]["cacheExpiry"] )
                        else:
                            objectCache["cacheFor"] = ( now + customCacheTime )
                    return objectCache["objectValue"]
            except KeyError:
                self.newCache(cacheName,sessionData=sessionData)
        if not dontCheck:
            cache, objectValue = self.getObjectValue(cacheName,uid,setFunction,*args,sessionData=sessionData)
            if cache and ( objectValue or nullUpdate ):
                cacheExpiry = self.objects[authedCacheName]["cacheExpiry"]
                if customCacheTime != None:
                    cacheExpiry = customCacheTime
                if uid in self.objects[authedCacheName]["objects"]:
                    objectCache = self.objects[authedCacheName]["objects"][uid]
                    objectCache["objectValue"] = objectValue
                    objectCache["cacheExpiry"] = (now + cacheExpiry)
                    objectCache["accessCount"] += 1
                else:
                    self.objects[authedCacheName]["objects"][uid] = { "objectValue" : objectValue, "accessCount" : 0, "cacheExpiry" : (now + cacheExpiry) }
            if objectValue:
                return objectValue
            else:
                return None
        else:
            return None

    def getDisabled(self,cacheName,uid,setFunction,*args,sessionData=None,extendCacheTime=False,customCacheTime=None,forceUpdate=False,nullUpdate=False,dontCheck=False):
        cache, objectValue = self.getObjectValue(cacheName,uid,setFunction,*args,sessionData=sessionData)
        return objectValue

    def getObjectValue(self,cacheName,uid,setFunction,*args,sessionData=None):
        authedCacheName = self.checkSessionData(cacheName,sessionData)
        if authedCacheName == None:
            return
        if cacheName == None:
            return
        if len(args) > 0:
            newObject = setFunction(uid,sessionData,*args)
        else:
            newObject = setFunction(uid,sessionData)
        if type(newObject) is tuple:
            return (False, newObject[1])
        return (True, newObject)

    def reduceSize(self,cacheName,amountToFree,sessionData=None):
        authedCacheName = self.checkSessionData(cacheName,sessionData)
        if authedCacheName == None:
            return
        logging.debug("Cache store attempting to reduce memory, name={0}, amount={1}".format(authedCacheName,amountToFree))
        # No objects to clear
        if len(self.objects[authedCacheName]["objects"]) == 0:
            return False
        
        now = time.time()
        amountReduced = 0
        poplist = []
        accessCount = {}
        for cacheObjectKey, cacheObjectValue in self.objects[authedCacheName]["objects"].items():
            if cacheObjectValue["cacheExpiry"] < now:
                amountReduced += jimi.helpers.getObjectMemoryUsage(cacheObjectValue)
                poplist.append(cacheObjectKey)
            else:
                if cacheObjectValue["accessCount"] not in accessCount:
                    accessCount[cacheObjectValue["accessCount"]] = []
                accessCount[cacheObjectValue["accessCount"]].append(cacheObjectKey)
            if amountReduced >= amountToFree:
                break
        if amountReduced < amountToFree:
            for count in accessCount.keys():
                for item in accessCount[count]:
                    amountReduced += jimi.helpers.getObjectMemoryUsage(self.objects[authedCacheName]["objects"][item])
                    poplist.append(item)
                    if amountReduced >= amountToFree:
                        break
                if amountReduced >= amountToFree:
                    break

        for item in poplist:
            try:
                del self.objects[authedCacheName]["objects"][item]
            except:
                pass

        if amountReduced >= amountToFree:
            return True

        return False

    def checkSessionData(self,cacheName,sessionData):
        if sessionData:
            authedCacheName = "{0},-,{1}".format(sessionData["_id"],cacheName)
            try:
                if sessionData["_id"] == self.objects[authedCacheName]["userID"]:
                    return authedCacheName
                else:
                    logging.debug("ERROR - Cache store access denied due to mismatched ID, name={0}, userID={1}".format(cacheName,sessionData["_id"]))
                    return None
            except KeyError:
                return authedCacheName
        else:
            return cacheName
        return None

    def getSummary(self):
        result = ""
        totalSize = 0
        for cacheName, cacheValue in self.objects.items():
            cacheSzie = jimi.helpers.getObjectMemoryUsage(cacheValue)
            totalSize+=cacheSzie
            result+="name='{0}', size='{1}'\r\n".format(cacheName,cacheSzie)
        result+="\r\n\r\nTotal Size='{0}'".format(totalSize)
        return result

try:
    cacheSettings = jimi.settings.getSetting("cache",None)
    globalCache = _cache(maxSize=cacheSettings["maxSize"],cacheExpiry=cacheSettings["cacheExpiry"])
    if cacheSettings["enabled"] == False:
        globalCache.get = globalCache.getDisabled
except:
    globalCache = _cache()