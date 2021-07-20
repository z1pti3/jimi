import jimi

class _settings(jimi.db._document):
	name = str()
	values = dict()
	
	_dbCollection = jimi.db.db["settings"]

	def new(self,name,values):
		self.name = name
		self.values = values
		self.acl = { "ids":[ { "accessID":"0","delete": True,"read": True,"write": True } ] } 
		return super(_settings, self).new()

jimi.cache.globalCache.newCache("settingsCache",cacheExpiry=3600)
def getSetting(name,settingName):
	return jimi.cache.globalCache.get("settingsCache","{0}:{1}".format(name,settingName),getSettingValue,name,settingName)

def getSettingValue(uid,sessionData,name,settingName):
	setting = _settings().query(sessionData,query={ "name" : name })["results"][0]
	return setting["values"][settingName]
