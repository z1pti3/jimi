from core.models import action
from core import helpers, db

class _global(db._document):
	name = str()
	globalValue = str()
	
	_dbCollection = db.db["global"]

	def new(self, acl, name, globalValue):
		self.acl = acl
		self.name = name
		self.globalValue = globalValue
		return super(_global, self).new()

class _globalSet(action._action):
	globalName = str()
	globalValue = str()

	def run(self,data,persistentData,actionResult):
		globalName = helpers.evalString(self.globalName,{"data" : data})
		globalValue = helpers.evalString(self.globalValue,{"data" : data})
		try:
			var =  _global().getAsClass(query={"name" : globalName})[0]
			if globalValue != var.globalValue:
				var.globalValue = globalValue
				var.update(["globalValue"])
		except:
			_global().new(self.acl,globalName,globalValue)
		data["var"]["global."+globalName] = helpers.typeCast(globalValue,{ "data" : data })
		actionResult["result"] = True
		actionResult["rc"] = 0
		return actionResult

class _globalGet(action._action):
	globalName = str()

	def run(self,data,persistentData,actionResult):
		globalName = helpers.evalString(self.globalName,{"data" : data})
		try:
			var =  _global().getAsClass(query={"name" : globalName})[0]
			data["var"]["global."+globalName] = helpers.typeCast(var.globalValue,{ "data" : data })
			actionResult["result"] = True
			actionResult["rc"] = 0
		except Exception as e:
			actionResult["result"] = False
			actionResult["rc"] = 100
		return actionResult
