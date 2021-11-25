import os
import requests
from pathlib import Path
import json
import time
import secrets

import jimi

class _storage(jimi.db._document):
    fileData = str()
    systemStorage = bool()
    fileHash = str()
    source = str()
    accessTokens = list()
    comment = str()

    _dbCollection = jimi.db.db["storage"]

    def new(self,acl,source,fileData,systemStorage=False,comment=""):
        self.source = source
        self.fileData = fileData
        self.systemStorage = systemStorage
        self.acl = acl
        self.accessTokens = []
        self.comment = comment
        return super(_storage, self).new()

    def getFullFilePath(self):
        return os.path.abspath(str(Path("data/storage/{0}".format(self._id))))

    def getLocalFilePath(self):
        idFilePath = "data/storage/{0}".format(self._id)
        if not jimi.helpers.safeFilepath(idFilePath,"data/storage"):
            return None
        if not os.path.isfile(idFilePath) or self.fileHash != jimi.helpers.getFileHash(idFilePath):
            jimi.logging.debug("Info: Storage file not found locally. storageID={0}".format(self._id),-1)
            # File not found on this server node, attempt to pull it from online servers within cluster
            for clusterMemeberURL in jimi.cluster.getAll():
                if clusterMemeberURL != jimi.cluster.getclusterMemberURLById(jimi.cluster._clusterMember.systemID):
                    try:
                        headers = { "x-api-token" : jimi.auth.generateSystemSession() }
                        with requests.get("{0}{1}storage/file/{2}/".format(clusterMemeberURL,jimi.api.base,self._id), headers=headers, stream=True, timeout=60) as r:
                            r.raise_for_status()
                            if r.status_code == 200:
                                with open(idFilePath, 'wb') as f:
                                    for chunk in r.iter_content(chunk_size=8192):
                                        f.write(chunk)
                                if jimi.helpers.getFileHash(idFilePath) == self.fileHash:
                                    return idFilePath
                                else:
                                    os.remove(idFilePath)
                    except:
                        pass
        else:
            return idFilePath
        jimi.logging.debug("ERROR: Storage file could not be found on any available server. storageID={0}".format(self._id),-1)
        return None

    def calculateHash(self):
        idFilePath = "data/storage/{0}".format(self._id)
        if os.path.isfile(idFilePath):
            self.fileHash = jimi.helpers.getFileHash(idFilePath)
            self.update(["fileHash"])

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
                idFilePath = "data/storage/{0}".format(storageFile._id)
                if storageFile.systemStorage:
                    if not jimi.helpers.safeFilepath(idFilePath,"data/storage"):
                        return {}, 403
                    return jimi.api.send_file(idFilePath,attachment_filename=storageFile._id)
                return {}, 404

            @jimi.api.webServer.route(jimi.api.base+"storage/file/<filename>/", methods=["PUT"])
            def uploadStorageFile(filename):
                storageFile = jimi.storage._storage()
                formData = jimi.api.request.form.to_dict()
                acl = { "ids" : [ { "accessID" : jimi.api.g.sessionData["primaryGroup"], "read" : True, "write" : True, "delete" : True } ] }
                storageFile.new(acl,"user",filename,systemStorage=True,comment=formData["comment"])
                if storageFile._id:
                    fullFilename = str(Path("data/storage/{0}".format(storageFile._id)))
                    if not jimi.helpers.safeFilepath(fullFilename,"data/storage"):
                        return {}, 403
                    f = jimi.api.request.files['file']
                    f.save(fullFilename)
                    storageFile.fileHash = jimi.helpers.getFileHash(fullFilename)
                    storageFile.update(["fileHash"])
                    return {  }, 200
                return { }, 404

            @jimi.api.webServer.route(jimi.api.base+"storage/file/<storageID>/", methods=["POST"])
            def updateStorageFile(storageID):
                storageItem = jimi.storage._storage().getAsClass(sessionData=jimi.api.g.sessionData,id=storageID)[0]
                if jimi.db.ACLAccess(jimi.api.g.sessionData,storageItem.acl,"write"):
                    fullFilename = str(Path("data/storage/{0}".format(storageID)))
                    if not jimi.helpers.safeFilepath(fullFilename,"data/storage"):
                        return {}, 403
                    f = jimi.api.request.files['file']
                    f.save(fullFilename)
                    storageItem.fileHash = jimi.helpers.getFileHash(fullFilename)
                    storageItem.update(["fileHash"])
                    return {  }, 200
                return { }, 404

        if jimi.api.webServer.name == "jimi_web":
            from flask import Flask, request, render_template, redirect

            @jimi.api.webServer.route("/storage/", methods=["GET"])
            def storagePage():
                storageFiles = _storage().query(sessionData=jimi.api.g.sessionData,query={ "systemStorage" : True },fields=["_id","fileData","fileHash","comment","accessTokens"])["results"]
                return render_template("storage.html",storage=storageFiles,CSRF=jimi.api.g.sessionData["CSRF"])

            @jimi.api.webServer.route(jimi.api.base+"storage/", methods=["POST"])
            def uploadStorageFile():
                formData = jimi.api.request.form.to_dict()
                if formData["name"]:
                    filename = formData["name"]
                else:
                    filename = formData["file"]
                tempFilename = str(Path("data/temp/{0}".format(filename)))
                if not jimi.helpers.safeFilepath(tempFilename,"data/temp"):
                    return {}, 403
                f = jimi.api.request.files['storageFile']
                f.save(tempFilename)
                headers = { "X-api-token" : jimi.api.g.sessionToken }
                url = jimi.cluster.getMaster()
                apiEndpoint = "storage/file/{0}/".format(filename)
                with open(tempFilename, 'rb') as f:
                    response = requests.put("{0}{1}{2}".format(url,jimi.api.base,apiEndpoint), headers=headers, data={ "comment" : formData["comment"] }, files={"file" : f.read() }, timeout=60)
                os.remove(tempFilename)
                return jimi.api.make_response(redirect("/storage/"))

            @jimi.api.webServer.route(jimi.api.base+"storage/file/<storageID>/", methods=["POST"])
            def updateStorageFile(storageID):
                storageItem = jimi.storage._storage().getAsClass(sessionData=jimi.api.g.sessionData,id=storageID)[0]
                if jimi.db.ACLAccess(jimi.api.g.sessionData,storageItem.acl,"write"):
                    formData = jimi.api.request.form.to_dict()
                    update = False
                    if formData["name"] != storageItem.fileData:
                        storageItem.fileData = formData["name"]
                        update = True
                    if formData["comment"] != storageItem.comment:
                        storageItem.comment = formData["comment"]
                        update = True
                    if update:
                        storageItem.update(["fileData","comment"])
                    if jimi.api.request.files['storageFile']:
                        filename = storageItem.fileData
                        tempFilename = str(Path("data/temp/{0}".format(filename)))
                        if not jimi.helpers.safeFilepath(tempFilename,"data/temp"):
                            return {}, 403
                        f = jimi.api.request.files['storageFile']
                        f.save(tempFilename)
                        headers = { "X-api-token" : jimi.api.g.sessionToken }
                        url = jimi.cluster.getMaster()
                        apiEndpoint = "storage/file/{0}/".format(storageID)
                        with open(tempFilename, 'rb') as f:
                            response = requests.post("{0}{1}{2}".format(url,jimi.api.base,apiEndpoint), headers=headers, files={"file" : f.read() }, timeout=60)
                        os.remove(tempFilename)
                    return jimi.api.make_response(redirect("/storage/"))
                return { }, 400

            @jimi.api.webServer.route(jimi.api.base+"storage/file/", methods=["GET"])
            def getStorageFiles():
                storageFiles = jimi.storage._storage().query(sessionData=jimi.api.g.sessionData,query={"systemStorage" : True},fields=["_id","source","fileData"])["results"]
                for storageFile in storageFiles:
                    del storageFile["acl"]
                    del storageFile["classID"]
                return { "results" : storageFiles }, 200

            @jimi.api.webServer.route(jimi.api.base+"storage/file/<storageID>/", methods=["DELETE"])
            def deleteStorageFile(storageID):
                storageItem = jimi.storage._storage().getAsClass(sessionData=jimi.api.g.sessionData,id=storageID)[0]
                if jimi.db.ACLAccess(jimi.api.g.sessionData,storageItem.acl,"delete"):
                    if storageItem.delete()["result"]:
                        return { }, 200
                return { }, 404

            @jimi.api.webServer.route(jimi.api.base+"storage/file/<storageID>/accessToken/<expiry>/", methods=["PUT"])
            def createStorageFileAccessToken(storageID,expiry):
                storageItem = jimi.storage._storage().getAsClass(sessionData=jimi.api.g.sessionData,id=storageID)[0]
                if jimi.db.ACLAccess(jimi.api.g.sessionData,storageItem.acl,"write"):
                    token = secrets.token_hex(128)
                    storageItem.accessTokens.append({ "token" : token, "expiry" : int(time.time()+int(expiry)) })
                    storageItem.update(["accessTokens"],sessionData=jimi.api.g.sessionData)
                    return { "accessToken" : token }, 200
                return { }, 404

            @jimi.api.webServer.route(jimi.api.base+"storage/file/<storageID>/<accessToken>/", methods=["DELETE"])
            def deleteStorageFileAccessToken(storageID,accessToken):
                storageItem = jimi.storage._storage().getAsClass(sessionData=jimi.api.g.sessionData,id=storageID)[0]
                if jimi.db.ACLAccess(jimi.api.g.sessionData,storageItem.acl,"delete"):
                    for accessTokenItem in storageItem.accessTokens:
                        if accessTokenItem["token"] == accessToken:
                            storageItem.accessTokens.remove(accessTokenItem)
                            break
                    storageItem.update(["accessTokens"],sessionData=jimi.api.g.sessionData)
                    return { }, 200
                return { }, 404

            def getFileFromMaster(storageID,filePath):
                apiToken = jimi.auth.generateSystemSession()
                url = jimi.cluster.getMaster()
                apiEndpoint = "storage/file/{0}/".format(storageID)
                headers = { "X-api-token" : apiToken }
                with requests.get("{0}{1}{2}".format(url,jimi.api.base,apiEndpoint), headers=headers, stream=True) as r:
                    r.raise_for_status()
                    with open(filePath, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)

            @jimi.api.webServer.route("/storage/file/<storageID>/", methods=["GET"])
            def getStorageFile(storageID):
                storageItem = jimi.storage._storage().query(sessionData=jimi.api.g.sessionData,id=storageID)["results"][0]
                idFilePath = "data/temp/{0}".format(storageItem["_id"])
                if not jimi.helpers.safeFilepath(idFilePath,"data/temp"):
                    return {}, 404
                fileWithinTemp = False
                if os.path.exists(Path(idFilePath)):
                    if jimi.helpers.getFileHash(idFilePath) == storageItem["fileHash"]:
                        fileWithinTemp = True
                if fileWithinTemp == False:
                    getFileFromMaster(storageItem["_id"],idFilePath)
                return jimi.api.send_file(idFilePath,attachment_filename=storageItem["fileData"],as_attachment=True)

            @jimi.api.webServer.route(jimi.api.base+"storage/file/<accessToken>/", methods=["GET"])
            def __PUBLIC__getStorageFile(accessToken):
                storageFile = jimi.storage._storage().query(query={"accessTokens.token" : accessToken, "accessTokens.expiry" : { "$gt" : int(time.time()) }},fields=["_id","fileHash"])["results"]
                if len(storageFile) == 1:
                    storageFile = storageFile[0]
                    idFilePath = "data/temp/{0}".format(storageFile["_id"])
                    if not jimi.helpers.safeFilepath(idFilePath,"data/temp"):
                        return {}, 404
                    fileWithinTemp = False
                    if os.path.exists(Path(idFilePath)):
                        if jimi.helpers.getFileHash(idFilePath) == storageFile["fileHash"]:
                            fileWithinTemp = True
                    if fileWithinTemp == False:
                        getFileFromMaster(storageFile["_id"],idFilePath)
                    return jimi.api.send_file(idFilePath,attachment_filename=storageFile["fileData"],as_attachment=True)
                return {}, 404
