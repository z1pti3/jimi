import os
import requests
from pathlib import Path
import json

import jimi

class _storage(jimi.db._document):
    fileData = str()
    systemStorage = bool()
    systemHash = str()
    source = str()

    _dbCollection = jimi.db.db["storage"]

    def new(self,acl,source,fileData,systemStorage=False):
        self.source = source
        self.fileData = fileData
        self.systemStorage = systemStorage
        self.acl = acl
        return super(_storage, self).new()

    def getFullFilePath(self):
        return os.path.abspath(str(Path("data/storage/{0}".format(self._id))))

    def getLocalFilePath(self):
        idFilePath = "data/storage/{0}".format(self._id)
        if not jimi.helpers.safeFilepath(idFilePath,"data/storage"):
            return None
        if not os.path.isfile(idFilePath) or self.systemHash != jimi.helpers.getFileHash(idFilePath):
            # File not found on this server node, attempt to pull it from online servers within cluster
            for clusterMemeberURL in jimi.cluster.getAll():
                if clusterMemeberURL != jimi.cluster.getclusterMemberURLById(jimi.cluster._clusterMember.systemID):
                    headers = { "x-api-token" : jimi.auth.generateSystemSession() }
                    with requests.get("{0}{1}storage/file/{2}/".format(clusterMemeberURL,jimi.api.base,self._id), headers=headers, stream=True, timeout=60) as r:
                        r.raise_for_status()
                        if r.status_code == 200:
                            with open(idFilePath, 'wb') as f:
                                for chunk in r.iter_content(chunk_size=8192):
                                    f.write(chunk)
                            if jimi.helpers.getFileHash(idFilePath) == self.systemHash:
                                return idFilePath
                            else:
                                os.remove(idFilePath)
        else:
            return idFilePath
        return None

    def calculateHash(self):
        idFilePath = "data/storage/{0}".format(self._id)
        if os.path.isfile(idFilePath):
            self.systemHash = jimi.helpers.getFileHash(idFilePath)
            self.update(["systemHash"])

# API
if jimi.api.webServer:
    if not jimi.api.webServer.got_first_request:	
        if jimi.api.webServer.name == "jimi_core":
            @jimi.api.webServer.route(jimi.api.base+"storage/file/<fileID>/", methods=["GET"])
            @jimi.auth.systemEndpoint
            def sendStorageFile(fileID):
                storageFile = jimi.storage._storage().getAsClass(sessionData=jimi.api.g.sessionData,id=fileID)
                if len(storageFile) != 1:
                    return {}, 404
                storageFile = storageFile[0]
                if storageFile.systemStorage:
                    if not jimi.helpers.safeFilepath("data/storage/{0}".format(storageFile._id),"data/storage"):
                        return {}, 403
                    return jimi.api.send_file(storageFile._id,attachment_filename=storageFile._id)
                return {}, 404

            @jimi.api.webServer.route(jimi.api.base+"storage/file/<filename>/", methods=["POST"])
            def uploadStorageFile(filename):
                storageFile = jimi.storage._storage()
                acl = { "ids" : [ { "accessID" : jimi.api.g.sessionData["primaryGroup"], "read" : True, "write" : True, "delete" : True } ] }
                storageFile.new(acl,"user",filename,systemStorage=True)
                if storageFile._id:
                    fullFilename = str(Path("data/storage/{0}".format(storageFile._id)))
                    if not jimi.helpers.safeFilepath(fullFilename,"data/storage"):
                        return {}, 403
                    f = jimi.api.request.files['file']
                    f.save(fullFilename)
                    return {  }, 200
                return { }, 404

        if jimi.api.webServer.name == "jimi_web":
            @jimi.api.webServer.route(jimi.api.base+"storage/file/<filename>/", methods=["PUT"])
            def uploadStorageFile(filename):
                tempFilename = str(Path("data/temp/{0}".format(filename)))
                if not jimi.helpers.safeFilepath(tempFilename,"data/temp"):
                    return {}, 403
                f = jimi.api.request.files['file']
                f.save(tempFilename)
                headers = { "X-api-token" : jimi.api.g.sessionToken }
                url = jimi.cluster.getMaster()
                apiEndpoint = "storage/file/{0}/".format(filename)
                with open(tempFilename, 'rb') as f:
                    response = requests.post("{0}{1}{2}".format(url,jimi.api.base,apiEndpoint), headers=headers, files={"file" : f.read() }, timeout=60)
                os.remove(tempFilename)
                return { "status_code" : response.status_code }, 200

            @jimi.api.webServer.route(jimi.api.base+"storage/file/", methods=["GET"])
            def getStorageFiles():
                storageFiles = jimi.storage._storage().query(sessionData=jimi.api.g.sessionData,query={"systemStorage" : True},fields=["_id","source","fileData"])["results"]
                for storageFile in storageFiles:
                    del storageFile["acl"]
                    del storageFile["classID"]
                return { "results" : storageFiles }, 200
  