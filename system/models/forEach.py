import time

from core.models import action, conduct
from core import helpers, logging, cache, settings

class _forEach(action._action):
	manual=bool()
	eventsField = str()
	events=list()
	skip=int()
	mergeEvents = bool()

	def __init__(self):
		cache.globalCache.newCache("actionConductCache")

	def run(self,data,persistentData,actionResult):
		if "skip" in data:
			actionResult["result"] = True
			actionResult["rc"] = 0
			return actionResult
		else:
			events = []
			if self.manual:
				events = self.events
			else:
				events = helpers.evalString(self.eventsField,{"data" : data})
			if self.skip == 0:
				skip = 1
			else:
				skip = self.skip
			if type(events) is list:
				foundConducts = cache.globalCache.get("actionConductCache",self._id,getConductObject)
				cpuSaver = helpers.cpuSaver()
				for event in events:
					if self.mergeEvents:
						tempData = { "event" : {**data["event"],**event}, "callingTriggerID" : data["triggerID"], "triggerID" : self._id, "var" : data["var"], "skip" : skip, "plugin" : data["plugin"] }
					else:
						tempData = { "event" : event, "callingTriggerID" : data["triggerID"], "triggerID" : self._id, "var" : data["var"], "skip" : skip, "plugin" : data["plugin"] }
					if foundConducts:
						for foundConduct in foundConducts:
							foundConduct.triggerHandler(data["flowID"],tempData,flowIDType=True,persistentData=persistentData)

					cpuSaver.tick()
		# Returning false to stop flow continue
		actionResult["result"] = False
		actionResult["rc"] = 200
		return actionResult

def getConductObject(actionID,sessionData):
	return conduct._conduct().getAsClass(query={"flow.actionID" : actionID, "enabled" : True})
