import requests
from pathlib import Path
import os

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

systemSettings = jimi.settings.config["system"]

def fileIntegrityRegister():
	knownFiles = _systemFiles().getAsClass(query={ "systemID" : systemSettings["systemID"] })
	knownFilesHash = {}
	for knownFile in knownFiles:
		knownFilesHash[knownFile.filename] = knownFile

	checksumHash = ""
	registerRoots = ["system","core","plugins"]
	for registerRoot in registerRoots:
		for root, dirs, files in os.walk(registerRoot, topdown=False):
			for _file in files:
				if "__pycache__" not in root and ".git" not in root:
					filename = os.path.join(root, _file)
					fileHash = jimi.helpers.getFileHash(filename)
					checksumHash+=fileHash
					try:
						if knownFilesHash[filename].fileHash != fileHash:
							knownFilesHash[filename].fileHash = fileHash
							knownFilesHash[filename].update(["fileHash"])
						del knownFilesHash[filename]
					except KeyError:
						_systemFiles().new(_file,systemSettings["systemID"],filename,fileHash)
	# Remove old files
	for knownFile in knownFilesHash:
		knownFilesHash[knownFile].delete()
	
	checksum = jimi.helpers.getStringHash(checksumHash)
	jimi.logging.debug("Info: System integrity hash. hash={0}".format(checksum),-1)
	return checksum

def getSystemFile(url,fileID,filename,fileHash):
	headers = { "x-api-token" : jimi.auth.generateSystemSession() }
	with requests.get("{0}{1}system/file/{2}/".format(url,jimi.api.base,fileID), headers=headers, stream=True, timeout=60) as r:
		r.raise_for_status()
		filename = str(Path(filename))
		filepath = str(Path(filename).parent)
		tempFilename = str(Path("data/temp/{0}".format(fileID)))
		with open(tempFilename, 'wb') as f:
			for chunk in r.iter_content(chunk_size=8192):
				f.write(chunk)
		if jimi.helpers.getFileHash(tempFilename) == fileHash:
			if os.path.isfile(filename):
				os.remove(filename)
			if not os.path.isdir(filepath):
				os.makedirs(filepath)
			os.rename(tempFilename,filename)
			jimi.helpers.reload()
			return True
		else:
			jimi.logging.debug("Error: File obtained from master failed integrity checks. fileID={0}, filename={1}".format(fileID,filename),-1)
		os.remove(tempFilename)
	return False

def fixChecksum(pullFromSystemID):
	masterSystemFiles = _systemFiles().getAsClass(query={ "systemID" : pullFromSystemID })
	ourSystemFiles = _systemFiles().getAsClass(query={ "systemID" : systemSettings["systemID"] })

	ourSystemFilesHash = {}
	for ourSystemFileHash in ourSystemFiles:
		ourSystemFilesHash[str(Path(ourSystemFileHash.filename))] = ourSystemFileHash

	masterURL = jimi.cluster.getMaster()
	for masterSystemFile in masterSystemFiles:
		try:
			if ourSystemFilesHash[str(Path(masterSystemFile.filename))].fileHash != masterSystemFile.fileHash:
				jimi.logging.debug("Info: File integrity mismatch with master - Updating. filename={0}".format(str(Path(masterSystemFile.filename))),-1)
				getSystemFile(masterURL,masterSystemFile._id,str(Path(masterSystemFile.filename)),masterSystemFile.fileHash)
			del ourSystemFilesHash[str(Path(masterSystemFile.filename))]
		except KeyError:
			jimi.logging.debug("Info: File not present but is on master - Downloading. filename={0}".format(str(Path(masterSystemFile.filename))),-1)
			getSystemFile(masterURL,masterSystemFile._id,str(Path(masterSystemFile.filename)),masterSystemFile.fileHash)
	for ourSystemFile in ourSystemFilesHash:
		jimi.logging.debug("Info: File does not exist on master - Deleting. filename={0}".format(str(Path(masterSystemFile.filename))),-1)
		os.remove(ourSystemFile)
	jimi.cluster.clusterMember.checksum = fileIntegrityRegister()
	jimi.cluster.clusterMember.update(["checksum"])
	return True

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
				return jimi.api.send_file(systemFile.filename,attachment_filename=systemFile.name)

			@jimi.api.webServer.route(jimi.api.base+"system/update/<pullFromSystemID>/", methods=["GET"])
			@jimi.auth.adminEndpoint
			def updateSystem(pullFromSystemID):
				fixChecksum(pullFromSystemID)
				return {}, 200

			@jimi.api.webServer.route(jimi.api.base+"system/checksum/", methods=["GET"])
			@jimi.auth.adminEndpoint
			def regenerateSystemFileIntegrity():
				fileIntegrityRegister()
				return {}, 200