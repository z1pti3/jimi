import requests
from pathlib import Path
import os
import json
import logging

import jimi
from system import install

class _systemFiles(jimi.db._document):
	name = str()
	systemID = int()
	filename = str()
	fileHash = str()

	_dbCollection = jimi.db.db["systemFiles"]

	def new(self,name,systemID,filename,fileHash):
		self.acl = { "ids":[ { "accessID":"0","delete": True,"read": True,"write": True } ] }
		self.name = name
		self.systemID = systemID
		self.filename = filename
		self.fileHash = fileHash
		return super(_systemFiles, self).new()

	def bulkNew(self,name,systemID,filename,fileHash,bulkClass):
		self.acl = { "ids":[ { "accessID":"0","delete": True,"read": True,"write": True } ] }
		self.name = name
		self.systemID = systemID
		self.filename = filename
		self.fileHash = fileHash
		return super(_systemFiles, self).bulkNew(bulkClass)

systemSettings = jimi.config["system"]

def fileIntegrityRegister():
	knownFiles = _systemFiles().getAsClass(query={ "systemID" : systemSettings["systemID"] })
	knownFilesHash = {}
	for knownFile in knownFiles:
		knownFilesHash[knownFile.filename] = knownFile

	# Updating storage before getting and updating system files - this will pull from systems if the file does not exist locally
	storageFiles = jimi.storage._storage().getAsClass(query={ "systemStorage" : True })
	for storageFile in storageFiles:
		if not storageFile.getLocalFilePath():
			jimi.logging.debug("Error: System integrity register could not find or get storage file. storageID={0}".format(storageFile._id),-1)

	bulkClass = jimi.db._bulk()
	checksumHash = []
	registerRoots = ["system","core","web","screens","tools","plugins","data/storage"]
	for registerRoot in registerRoots:
		for root, dirs, files in os.walk(Path(registerRoot),followlinks=True):
			for _file in files:
				if "__pycache__" not in root and ".git" not in root:
					filename = os.path.join(root, _file)
					if registerRoot == "data/storage":
						fileHash = jimi.helpers.getFileHash(filename,insecure=True)
					else:
						fileHash = jimi.helpers.getFileHash(filename)
					checksumHash.append(fileHash)
					try:
						if knownFilesHash[filename].fileHash != fileHash:
							knownFilesHash[filename].fileHash = fileHash
							knownFilesHash[filename].bulkUpdate(["fileHash"],bulkClass)
						del knownFilesHash[filename]
					except KeyError:
						_systemFiles().bulkNew(_file,systemSettings["systemID"],filename,fileHash,bulkClass)

	# Remove old files
	for knownFile in knownFilesHash:
		knownFilesHash[knownFile].delete()
	checksumHash.sort()
	checksum = jimi.helpers.getStringHash(",".join(checksumHash))
	system = jimi.cluster.getSystem()
	if system is not None:
		system.checksum = checksum
		system.update(["checksum"])

	jimi.logging.debug("Info: System integrity hash. hash={0}".format(checksum),-1)
	return checksum

def getSystemFile(url,fileID,filename,fileHash):
	filename = str(Path(filename))
	filepath = str(Path(filename).parent)
	if not jimi.helpers.safeFilepath(filename,filepath):
		return False
	headers = { "x-api-token" : jimi.auth.generateSystemSession() }
	try:
		with requests.get("{0}{1}system/file/{2}/".format(url,jimi.api.base,fileID), headers=headers, stream=True, timeout=60) as r:
			r.raise_for_status()
			tempFilename = str(Path("data/temp/{0}".format(fileID)))
			if not jimi.helpers.safeFilepath(tempFilename,"data/temp"):
				return False
			with open(tempFilename, 'wb') as f:
				for chunk in r.iter_content(chunk_size=8192):
					f.write(chunk)
			if jimi.helpers.getFileHash(tempFilename) == fileHash:
				if os.path.isfile(filename):
					os.remove(filename)
				if not os.path.isdir(filepath):
					os.makedirs(filepath)
				os.rename(tempFilename,filename)
				return True
			else:
				jimi.logging.debug("Error: File obtained from master failed integrity checks. fileID={0}, filename={1}".format(fileID,filename),-1)
			os.remove(tempFilename)
	except:
		jimi.logging.debug("Error: File could not be obtained from master. fileID={0}, filename={1}".format(fileID,filename),-1)
	return False

def fixChecksum(pullFromSystemID):
	masterSystemFiles = _systemFiles().getAsClass(query={ "systemID" : pullFromSystemID })
	ourSystemFiles = _systemFiles().getAsClass(query={ "systemID" : systemSettings["systemID"] })

	ourSystemFilesHash = {}
	for ourSystemFileHash in ourSystemFiles:
		ourSystemFilesHash[str(Path(ourSystemFileHash.filename))] = ourSystemFileHash

	masterURL = jimi.cluster.getclusterMemberURLById(pullFromSystemID)
	for masterSystemFile in masterSystemFiles:
		try:
			if ourSystemFilesHash[str(Path(masterSystemFile.filename))].fileHash != masterSystemFile.fileHash:
				jimi.logging.debug("Info: File integrity mismatch with master - Updating. filename={0}".format(str(Path(masterSystemFile.filename))),-1)
				if not getSystemFile(masterURL,masterSystemFile._id,str(Path(masterSystemFile.filename)),masterSystemFile.fileHash):
					jimi.logging.debug("Error: File could not be obtained from master. filename={0}".format(masterSystemFile.filename),-1)
					return None
			del ourSystemFilesHash[str(Path(masterSystemFile.filename))]
		except KeyError:
			jimi.logging.debug("Info: File not present but is on master - Downloading. filename={0}".format(str(Path(masterSystemFile.filename))),-1)
			if not getSystemFile(masterURL,masterSystemFile._id,str(Path(masterSystemFile.filename)),masterSystemFile.fileHash):
				jimi.logging.debug("Error: File could not be obtained from master. filename={0}".format(masterSystemFile.filename),-1)
				return None
	for ourSystemFile in ourSystemFilesHash:
		jimi.logging.debug("Info: File does not exist on master - Deleting. filename={0}".format(str(Path(ourSystemFile))),-1)
		if jimi.helpers.safeFilepath(ourSystemFile):
			os.remove(ourSystemFile)

	# Regenerate checksum now we have pulled all of the files
	checksum = fileIntegrityRegister()
	return checksum

# API
if jimi.api.webServer:
	if not jimi.api.webServer.got_first_request:	
		if jimi.api.webServer.name == "jimi_core":
			@jimi.api.webServer.route(jimi.api.base+"system/file/<fileID>/", methods=["GET"])
			@jimi.auth.systemEndpoint
			def sendSystemFile(fileID):
				systemFile = jimi.system._systemFiles().getAsClass(sessionData=jimi.api.g.sessionData,id=fileID)
				if len(systemFile) != 1:
					return {}, 404
				systemFile = systemFile[0]
				if not jimi.helpers.safeFilepath(systemFile.filename):
					return {}, 403
				return jimi.api.send_file(systemFile.filename,attachment_filename=systemFile.name)

			@jimi.api.webServer.route(jimi.api.base+"system/update/<pullFromSystemID>/", methods=["GET"])
			@jimi.auth.adminEndpoint
			def updateSystem(pullFromSystemID):
				if fixChecksum(int(pullFromSystemID)):
					return {}, 200
				else:
					return { "error" : "An error occurred while pulling files form master." }, 503

			@jimi.api.webServer.route(jimi.api.base+"system/checksum/", methods=["GET"])
			@jimi.auth.adminEndpoint
			def regenerateSystemFileIntegrity():
				jimi.cluster.getSystem().checksum = fileIntegrityRegister()
				jimi.cluster.getSystem().update(["checksum"])
				return {}, 200

			@jimi.api.webServer.route(jimi.api.base+"system/reload/module/<moduleName>/", methods=["GET"])
			@jimi.auth.adminEndpoint
			def reloadModule(moduleName):
				jimi.helpers.reloadModulesWithinPath(moduleName)
				results = [{ "system" : jimi.cluster.getSystemId(), "status_code" : 200 }]
				apiToken = jimi.auth.generateSystemSession()
				headers = { "X-api-token" : apiToken }
				for systemIndex in jimi.cluster.systemIndexes:
					url = systemIndex["apiAddress"]
					apiEndpoint = "system/reload/module/{0}/".format(moduleName)
					try:
						response = requests.get("{0}{1}{2}".format(url,jimi.api.base,apiEndpoint),headers=headers, timeout=10)
						if response.status_code == 200:
							results.append({ "system" : jimi.cluster.getSystemId(), "index" : systemIndex["systemIndex"], "status_code" : response.status_code })
					except:
						logging.warning("Unable to access {0}{1}{2}".format(url,jimi.api.base,apiEndpoint))
				return { "results" : results }, 200

		if jimi.api.webServer.name == "jimi_worker":
			@jimi.api.webServer.route(jimi.api.base+"system/reload/module/<moduleName>/", methods=["GET"])
			@jimi.auth.systemEndpoint
			def reloadModule(moduleName):
				jimi.helpers.reloadModulesWithinPath(moduleName)
				return { }, 200
		
		if jimi.api.webServer.name == "jimi_web":
			@jimi.api.webServer.route(jimi.api.base+"system/update/<systemID>/<pullFromSystemID>/", methods=["GET"])
			@jimi.auth.adminEndpoint
			def updateSystem(systemID,pullFromSystemID):
				url = jimi.cluster.getclusterMemberURLById(int(systemID))
				if not url:
					return {}, 404
				apiEndpoint = "system/update/{0}/".format(pullFromSystemID)
				response = jimi.helpers.apiCall("GET",apiEndpoint,token=jimi.api.g.sessionToken,overrideURL=url,timeout=300)
				if not response or response.status_code != 200:
					return { "error" : "Error response from {0}".format(url) }, 503
				return { }, 200

			@jimi.api.webServer.route(jimi.api.base+"system/checksum/<systemID>/", methods=["GET"])
			@jimi.auth.adminEndpoint
			def regenerateSystemFileIntegrity(systemID):
				url = jimi.cluster.getclusterMemberURLById(int(systemID))
				if not url:
					return {}, 404
				apiEndpoint = "system/checksum/"
				response = jimi.helpers.apiCall("GET",apiEndpoint,token=jimi.api.g.sessionToken,overrideURL=url,timeout=300)
				if not response or response.status_code != 200:
					return { "error" : "Error response from {0}".format(url) }, 503
				return { }, 200

			@jimi.api.webServer.route(jimi.api.base+"system/checksum/<sourceSystemID>/<targetSystemID>/", methods=["GET"])
			@jimi.auth.adminEndpoint
			def compareSystemFileIntegrity(sourceSystemID,targetSystemID):
				sourceSystemID = int(sourceSystemID)
				targetSystemID = int(targetSystemID)
				sourceFiles = _systemFiles().getAsClass(query={ "systemID" : { "$in" : [sourceSystemID,targetSystemID] } })
				sourceFilesHash = {}
				for sourceFile in sourceFiles:
					if sourceFile.filename not in sourceFilesHash:
						sourceFilesHash[sourceFile.filename] = {}
					sourceFilesHash[sourceFile.filename][sourceFile.systemID] = sourceFile.fileHash
				differences = { "remove" : [], "new" : [], "mismatch" : [] }
				for key, value in sourceFilesHash.items():
					try:
						if value[sourceSystemID] != value[targetSystemID]:
							differences["mismatch"].append(key)
					except KeyError:
						if sourceSystemID in value:
							differences["new"].append(key)
						else:
							differences["remove"].append(key)
				return { "results" : sourceFilesHash, "differences" : differences }, 200

			@jimi.api.webServer.route(jimi.api.base+"system/reload/module/<moduleName>/", methods=["GET"])
			@jimi.auth.adminEndpoint
			def reloadModule(moduleName):
				jimi.helpers.reloadModulesWithinPath(moduleName)
				apiEndpoint = "system/reload/module/{0}/".format(moduleName)
				servers = jimi.cluster.getAll()
				for url in servers:
					response = jimi.helpers.apiCall("GET",apiEndpoint,token=jimi.api.g.sessionToken,overrideURL=url,timeout=60)
					if not response or response.status_code != 200:
						return { "error" : "Error response from {0}".format(url) }, 503
				return { }, 200


